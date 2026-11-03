"""Two requests at the same moment: only one wins (spec 5 "Two people at once", 12.1).

The usual `db_session` runs every test in one connection and rolls it back, so it cannot
show a race. These tests commit real data through `migrated_engine`, run two threads with
their own sessions and connections, and delete every row they made at the end.

Each thread reads the database once before the barrier, so both transactions take their
snapshot before either one writes: the loser must be stopped by the database (the version
guard or the room lock), not by a lucky read of the winner's commit.
"""

import threading

import pytest
from sqlalchemy import delete, event, inspect, select
from sqlalchemy.orm import Session

from app.constants.booking import BookingRoute, BookingStatus
from app.errors import AppError
from app.models import (
    Booking,
    BookingDoorPass,
    BookingParticipant,
    BookingRejection,
    BookingReview,
    BookingSession,
    CateringOrder,
    ITTicket,
    User,
    it_ticket_staff,
    user_roles,
)
from app.schemas.booking import BookingCreate
from app.security import CurrentUser, load_role_codes
from app.services import booking, booking_review
from tests import factories
from tests.booking_helpers import NOW, body

# Booking child tables, deleted before the bookings themselves.
BOOKING_CHILDREN = [
    BookingDoorPass,
    BookingParticipant,
    BookingRejection,
    BookingReview,
    BookingSession,
    CateringOrder,
]


def _new_session(engine) -> Session:
    """A session set up like the app's (app.db.SessionLocal)."""
    return Session(bind=engine, autoflush=False, expire_on_commit=False)


@pytest.fixture
def committed(migrated_engine, freeze_now):
    """A session whose data is committed for real. Every row it saves, and every booking
    made in one of its rooms, is deleted after the test."""
    freeze_now(NOW)
    session = _new_session(migrated_engine)
    made = []  # (table, primary key columns, primary key values) in the order saved

    @event.listens_for(session, "pending_to_persistent")
    def remember(_session, instance):
        state = inspect(instance)
        made.append((state.mapper.local_table, state.mapper.primary_key, state.identity))

    yield session

    session.rollback()
    with migrated_engine.begin() as conn:
        room_ids = [pk[0] for table, _cols, pk in made if table.name == "rooms"]
        booking_ids = select(Booking.id).where(Booking.room_id.in_(room_ids))
        tickets = select(ITTicket.id).where(ITTicket.booking_id.in_(booking_ids))
        conn.execute(delete(it_ticket_staff).where(it_ticket_staff.c.ticket_id.in_(tickets)))
        conn.execute(delete(ITTicket).where(ITTicket.booking_id.in_(booking_ids)))
        for model in BOOKING_CHILDREN:
            conn.execute(delete(model).where(model.booking_id.in_(booking_ids)))
        conn.execute(delete(Booking).where(Booking.room_id.in_(room_ids)))
        user_ids = [pk[0] for table, _cols, pk in made if table.name == "users"]
        conn.execute(delete(user_roles).where(user_roles.c.user_id.in_(user_ids)))
        for table, columns, pk in reversed(made):
            conn.execute(
                delete(table).where(*(col == value for col, value in zip(columns, pk, strict=True)))
            )
    session.close()


def _run_together(engine, user_ids, call) -> list[str]:
    """Run `call(session, current)` in one thread per user, released together. Each thread
    commits on success and rolls back on an AppError. Returns "ok" or the error code each."""
    barrier = threading.Barrier(len(user_ids))
    results: list[str | None] = [None] * len(user_ids)

    def worker(index: int, user_id: int) -> None:
        with _new_session(engine) as session:
            try:
                user = session.get(User, user_id)
                current = CurrentUser(user=user, role_codes=load_role_codes(session, user.id))
                barrier.wait(timeout=10)
                call(session, current)
                session.commit()
                results[index] = "ok"
            except AppError as exc:
                session.rollback()
                results[index] = exc.code.value
            except Exception as exc:  # noqa: BLE001 - shown in the failed assert
                session.rollback()
                results[index] = repr(exc)

    threads = [
        threading.Thread(target=worker, args=(i, user_id)) for i, user_id in enumerate(user_ids)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)
    assert not any(thread.is_alive() for thread in threads), "a thread is stuck"
    return results


def test_two_pitika_one_wins(committed, migrated_engine):
    first = factories.make_pitika(committed)
    second = factories.make_pitika(committed)
    room = factories.make_bookable_room(committed)
    requester = factories.make_user(committed, roles=["STAFF"])
    waiting = factories.make_booking(
        committed, room, requester, status=BookingStatus.PENDING_PITIKA, route=BookingRoute.R1
    )
    committed.commit()
    booking_id = waiting.id

    results = _run_together(
        migrated_engine,
        [first.id, second.id],
        lambda session, current: booking_review.pitika_approve(
            session, current, booking_id, None, 1
        ),
    )

    assert sorted(results) == ["STALE_VERSION", "ok"]
    with _new_session(migrated_engine) as session:
        saved = session.get(Booking, booking_id)
        assert (saved.status, saved.version) == (BookingStatus.CONFIRMED, 2)
        assert len(saved.reviews) == 1
        assert saved.door_pass is not None


def test_two_creates_one_wins(committed, migrated_engine, settings):
    factories.make_pitika(committed)
    room = factories.make_bookable_room(committed)
    first = factories.make_user(committed, roles=["STAFF"])
    second = factories.make_user(committed, roles=["STAFF"])
    committed.commit()
    room_id = room.id
    request = BookingCreate(**body(room_id))

    results = _run_together(
        migrated_engine,
        [first.id, second.id],
        lambda session, current: booking.create_booking(session, current, request, settings),
    )

    assert sorted(results) == ["SCHEDULE_CONFLICT", "ok"]
    with _new_session(migrated_engine) as session:
        saved = session.scalars(select(Booking).where(Booking.room_id == room_id)).all()
        assert len(saved) == 1
        assert len(saved[0].sessions) == 1
