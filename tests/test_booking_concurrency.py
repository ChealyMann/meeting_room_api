"""Two requests at the same moment: only one wins (spec 5 "Two people at once", 12.1).

The usual `db_session` runs every test in one connection and rolls it back, so it cannot
show a race. These tests commit real data through `migrated_engine`, run two threads with
their own sessions and connections, and delete every row they made at the end.

Each thread reads the database once before the barrier, so both transactions take their
snapshot before either one writes: the loser must be stopped by the database (the version
guard or the room lock), not by a lucky read of the winner's commit.
"""

import threading
from types import SimpleNamespace

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
from app.schemas.booking import BookingCreate, BookingUpdate
from app.security import CurrentUser, load_role_codes
from app.services import booking, booking_admin, booking_review, it_ticket
from app.services import room as room_service
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


def test_two_admins_one_wins(committed, migrated_engine):
    """B-31 for the Admin (B-33, B-34): an approve and a cancel at the same version."""
    first = factories.make_user(committed, roles=["ADMIN"])
    second = factories.make_user(committed, roles=["ADMIN"])
    owner = factories.make_user(committed, roles=["ROOM_OWNER"])
    room = factories.make_bookable_room(committed, private=True, owner=owner)
    requester = factories.make_user(committed, roles=["STAFF"])
    waiting = factories.make_booking(
        committed, room, requester, status=BookingStatus.PENDING_OWNER, route=BookingRoute.R2
    )
    committed.commit()
    booking_id = waiting.id
    calls = iter(
        [
            lambda s, c: booking_admin.admin_approve(s, c, booking_id, None, 1),
            lambda s, c: booking_admin.admin_cancel(s, c, booking_id, None, 1),
        ]
    )
    chosen = {first.id: next(calls), second.id: next(calls)}

    results = _run_together(
        migrated_engine,
        [first.id, second.id],
        lambda session, current: chosen[current.id](session, current),
    )

    assert sorted(results) == ["STALE_VERSION", "ok"]
    approve_won = results[0] == "ok"  # results follow [first (approves), second (cancels)]
    with _new_session(migrated_engine) as session:
        saved = session.get(Booking, booking_id)
        owner_reviews = [r for r in saved.reviews if r.stage == "OWNER"]
        assert saved.version == 2
        if approve_won:
            # Only the approve wrote: confirmed, one owner review by the first Admin, no cancel.
            assert saved.status == BookingStatus.CONFIRMED
            assert [(r.reviewer_id, r.by_admin) for r in owner_reviews] == [(first.id, True)]
            assert saved.cancelled_at is None
        else:
            # Only the cancel wrote: cancelled by the second Admin, no owner review.
            assert saved.status == BookingStatus.CANCELLED
            assert owner_reviews == []
            assert saved.cancelled_by == second.id


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


def test_two_edits_with_new_participants_one_wins(committed, migrated_engine, settings):
    """Both requests add the same participant at the same version. The booking row is read
    with a lock, so the second waits, sees version 2 and stops with STALE_VERSION; it never
    reaches the participant insert (which would hit the unique key: a 500)."""
    room = factories.make_bookable_room(committed)
    requester = factories.make_user(committed, roles=["STAFF"])
    saved = factories.make_booking(committed, room, requester, status=BookingStatus.CONFIRMED)
    committed.commit()
    booking_id = saved.id
    edit = BookingUpdate(version=1, participant_emails=["guest@company.com"])

    results = _run_together(
        migrated_engine,
        [requester.id, requester.id],
        lambda session, current: booking.update_booking(
            session, current, booking_id, edit, settings
        ),
    )

    assert sorted(results) == ["STALE_VERSION", "ok"]
    with _new_session(migrated_engine) as session:
        row = session.get(Booking, booking_id)
        assert row.version == 2
        assert [p.email for p in row.participants] == ["guest@company.com"]


def test_two_staff_assigns_one_wins(committed, migrated_engine):
    """The same IT Staff assigned twice at the same version: one wins, the other gets
    STALE_VERSION (not a duplicate key on it_ticket_staff)."""
    lead = factories.make_user(committed, roles=["IT_LEAD"])
    helper = factories.make_user(committed, roles=["IT_STAFF"])
    room = factories.make_bookable_room(committed)
    requester = factories.make_user(committed, roles=["STAFF"])
    saved = factories.make_booking(
        committed,
        room,
        requester,
        status=BookingStatus.SETUP_IN_PROGRESS,
        it=True,
        forwarded=True,
    )
    committed.commit()
    booking_id, ticket_id, helper_id = saved.id, saved.it_ticket.id, helper.id

    results = _run_together(
        migrated_engine,
        [lead.id, lead.id],
        lambda session, current: it_ticket.assign_staff(
            session, current, ticket_id, [helper_id], None, 1
        ),
    )

    assert sorted(results) == ["STALE_VERSION", "ok"]
    with _new_session(migrated_engine) as session:
        row = session.get(Booking, booking_id)
        assert row.version == 2
        assert [user.id for user in row.it_ticket.staff] == [helper_id]


# --- Rows read for a write are locked (B-31) ---------------------------------------------


def _statements(conn, call) -> list[str]:
    """The SQL statements `call()` sends, on one line each."""
    seen: list[str] = []

    def remember(_conn, _cursor, statement, *_args):
        seen.append(" ".join(statement.split()))

    event.listen(conn, "before_cursor_execute", remember)
    try:
        call()
    finally:
        event.remove(conn, "before_cursor_execute", remember)
    return seen


def _first_read(statements: list[str], table: str) -> str:
    """The first SELECT whose FROM is `table`."""
    return next(s for s in statements if s.startswith("SELECT") and f"FROM {table} " in s)


def _edit(session, current, ids, settings):
    body = BookingUpdate(version=1, meeting_title="New title")
    booking.update_booking(session, current, ids.booking_id, body, settings)


def _cancel(session, current, ids, _settings):
    booking.cancel_booking(session, current, ids.booking_id, None, 1)


def _pitika_approve(session, current, ids, _settings):
    booking_review.pitika_approve(session, current, ids.booking_id, None, 1)


def _pitika_reject(session, current, ids, _settings):
    booking_review.pitika_reject(session, current, ids.booking_id, "Wrong room.", 1)


def _owner_approve(session, current, ids, _settings):
    booking_review.owner_approve(session, current, ids.booking_id, None, 1)


def _owner_reject(session, current, ids, _settings):
    booking_review.owner_reject(session, current, ids.booking_id, "Wrong room.", 1)


def _it_assign(session, current, ids, _settings):
    it_ticket.assign_staff(session, current, ids.ticket_id, [ids.helper_id], None, 1)


def _it_ready(session, current, ids, _settings):
    it_ticket.mark_ready(session, current, ids.ticket_id, 1)


def _admin_cancel(session, current, ids, _settings):
    booking_admin.admin_cancel(session, current, ids.booking_id, None, 1)


def _admin_approve(session, current, ids, _settings):
    booking_admin.admin_approve(session, current, ids.booking_id, None, 1)


def _admin_reject(session, current, ids, _settings):
    booking_admin.admin_reject(session, current, ids.booking_id, None, 1)


IT = {"it": True, "forwarded": True}
R2 = BookingRoute.R2
# name: (status, route, factory options, who acts, call)
WRITES = {
    "edit": (BookingStatus.CONFIRMED, R2, {}, "booker", _edit),
    "cancel": (BookingStatus.CONFIRMED, R2, {}, "booker", _cancel),
    "pitika_approve": (BookingStatus.PENDING_PITIKA, R2, {}, "pitika", _pitika_approve),
    "pitika_reject": (BookingStatus.PENDING_PITIKA, R2, {}, "pitika", _pitika_reject),
    "owner_approve": (BookingStatus.PENDING_OWNER, R2, {}, "owner", _owner_approve),
    "owner_reject": (BookingStatus.PENDING_OWNER, R2, {}, "owner", _owner_reject),
    "it_assign": (BookingStatus.SETUP_IN_PROGRESS, R2, IT, "lead", _it_assign),
    "it_ready": (BookingStatus.SETUP_IN_PROGRESS, R2, IT, "lead", _it_ready),
    "admin_cancel": (BookingStatus.CONFIRMED, R2, {}, "admin", _admin_cancel),
    "admin_approve": (BookingStatus.PENDING_OWNER, R2, {}, "admin", _admin_approve),
    "admin_reject": (BookingStatus.PENDING_OWNER, R2, {}, "admin", _admin_reject),
}


@pytest.mark.parametrize("name", list(WRITES))
def test_writes_read_the_booking_with_a_lock(frozen, conn, db_session, settings, name):
    """B-31: every booking write reads the booking row FOR UPDATE before the version check,
    so two requests at the same version cannot both reach the child-row writes."""
    status, route, options, who, call = WRITES[name]
    owner = factories.make_user(db_session, roles=["ROOM_OWNER"])
    room = factories.make_bookable_room(db_session, private=True, owner=owner)
    booker = factories.make_user(db_session, roles=["STAFF"])
    helper = factories.make_user(db_session, roles=["IT_STAFF"])
    people = {
        "booker": booker,
        "owner": owner,
        "pitika": factories.make_pitika(db_session),
        "lead": factories.make_user(db_session, roles=["IT_LEAD"]),
        "admin": factories.make_user(db_session, roles=["ADMIN"]),
    }
    staff = (helper,) if name == "it_ready" else ()
    saved = factories.make_booking(
        db_session, room, booker, status=status, route=route, assigned_staff=staff, **options
    )
    ticket_id = saved.it_ticket.id if saved.it_ticket else None
    ids = SimpleNamespace(booking_id=saved.id, ticket_id=ticket_id, helper_id=helper.id)
    user = people[who]
    current = CurrentUser(user=user, role_codes=load_role_codes(db_session, user.id))
    # Plain ids are read before this: touching an expired object would load it first.
    db_session.expire_all()

    statements = _statements(conn, lambda: call(db_session, current, ids, settings))

    assert _first_read(statements, "bookings").endswith("FOR UPDATE"), statements


def test_create_reads_the_room_with_a_lock(frozen, conn, db_session, settings):
    """The room is read FOR UPDATE at the room step, so the checks after it see the room as
    it is now, and the room cannot change until the booking is saved."""
    factories.make_pitika(db_session)
    room = factories.make_bookable_room(db_session)
    user = factories.make_user(db_session, roles=["STAFF"])
    current = CurrentUser(user=user, role_codes=load_role_codes(db_session, user.id))
    request = BookingCreate(**body(room.id))
    db_session.expire_all()

    statements = _statements(
        conn, lambda: booking.create_booking(db_session, current, request, settings)
    )

    assert _first_read(statements, "rooms").endswith("FOR UPDATE"), statements


@pytest.mark.parametrize(
    ("change", "table"),
    [({"is_active": False}, "booking_sessions"), ({"is_private": False}, "bookings")],
)
def test_room_update_locks_the_room_and_reads_bookings_for_share(
    frozen, conn, db_session, change, table
):
    """A room change and a new booking of the room cannot pass each other: the room is
    read FOR UPDATE and the booking counts are locking reads (FOR SHARE)."""
    owner = factories.make_user(db_session, roles=["ROOM_OWNER"])
    room = factories.make_bookable_room(db_session, private=True, owner=owner)
    admin = factories.make_user(db_session, roles=["ADMIN"])
    current = CurrentUser(user=admin, role_codes=load_role_codes(db_session, admin.id))
    room_id = room.id
    db_session.expire_all()

    statements = _statements(
        conn, lambda: room_service.update_room(db_session, room_id, change, current)
    )

    assert _first_read(statements, "rooms").endswith("FOR UPDATE"), statements
    count = next(s for s in statements if s.startswith("SELECT count") and f"FROM {table}" in s)
    assert count.endswith(("FOR SHARE", "LOCK IN SHARE MODE")), count
