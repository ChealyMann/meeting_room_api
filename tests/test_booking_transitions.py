"""booking_transitions: the version check and the shared status moves (spec 8.5)."""

from datetime import datetime, time, timedelta

import pytest
from sqlalchemy import select, text

from app.constants.booking import (
    BookingRoute,
    BookingStatus,
    DisplayStatus,
    RejectedBy,
    ReviewStage,
)
from app.errors import AppError
from app.models import BookingSession
from app.services import booking_transitions as transitions
from tests.booking_helpers import DAY

NEXT_DAY = DAY + timedelta(days=1)


@pytest.fixture
def booking(make_user, make_bookable_room, make_booking):
    def build(status=BookingStatus.PENDING_PITIKA, **kwargs):
        return make_booking(
            make_bookable_room(), make_user(roles=["STAFF"]), status=status, **kwargs
        )

    return build


def test_times(frozen, booking):
    b = booking(sessions=((NEXT_DAY, time(9), time(10)), (DAY, time(14), time(15))))
    assert transitions.first_start(b) == datetime(2026, 11, 10, 14, 0)
    assert transitions.last_end(b) == datetime(2026, 11, 11, 10, 0)
    assert (transitions.has_started(b), transitions.has_ended(b)) == (False, False)


def test_started_and_ended_at_the_exact_minute(freeze_now, frozen, booking):
    b = booking()  # DAY 09:00-10:00
    freeze_now(datetime(2026, 11, 10, 9, 0))
    assert (transitions.has_started(b), transitions.has_ended(b)) == (True, False)
    freeze_now(datetime(2026, 11, 10, 10, 0))
    assert transitions.has_ended(b) is True


def test_display_status(freeze_now, frozen, booking):
    confirmed = booking(BookingStatus.CONFIRMED)
    pending = booking(BookingStatus.PENDING_PITIKA)
    assert transitions.display_status(confirmed) == DisplayStatus.CONFIRMED
    freeze_now(datetime(2026, 11, 10, 10, 0))
    assert transitions.display_status(confirmed) == DisplayStatus.COMPLETED
    # Only a confirmed booking becomes COMPLETED.
    assert transitions.display_status(pending) == DisplayStatus.PENDING_PITIKA


def test_check_version(frozen, booking):
    b = booking(version=3)
    transitions.check_version(b, 3)
    with pytest.raises(AppError) as caught:
        transitions.check_version(b, 2)
    assert (caught.value.code, caught.value.status) == ("STALE_VERSION", 409)
    assert caught.value.message == "This booking changed. Reload it."


@pytest.mark.parametrize(
    ("status", "message"),
    [
        (BookingStatus.PENDING_PITIKA, "This booking is waiting for Pitika."),
        (BookingStatus.PENDING_OWNER, "This booking is waiting for the room owner."),
        (BookingStatus.SETUP_IN_PROGRESS, "This booking is in IT setup."),
        (BookingStatus.CONFIRMED, "This booking is already confirmed."),
        (BookingStatus.REJECTED, "This booking was rejected."),
        (BookingStatus.CANCELLED, "This booking was cancelled."),
    ],
)
def test_invalid_transition_messages(frozen, booking, status, message):
    error = transitions.invalid_transition(booking(status))
    assert (error.code, error.status, error.message) == ("INVALID_TRANSITION", 409, message)


def test_invalid_transition_completed_and_custom(freeze_now, frozen, booking):
    b = booking(BookingStatus.CONFIRMED)
    freeze_now(datetime(2026, 11, 10, 10, 0))
    assert transitions.invalid_transition(b).message == "This booking is completed."
    custom = transitions.invalid_transition(b, "This booking has ended.")
    assert custom.message == "This booking has ended."


def test_advance_writes_and_bumps_version(freeze_now, frozen, db_session, booking):
    b = booking()
    freeze_now(datetime(2026, 11, 9, 9, 30))
    transitions.advance(db_session, b, 1, status=BookingStatus.PENDING_OWNER)
    assert (b.status, b.version) == ("PENDING_OWNER", 2)
    assert b.updated_at == datetime(2026, 11, 9, 2, 30)  # UTC


def test_advance_with_no_values_only_bumps_version(frozen, db_session, booking):
    b = booking()
    transitions.advance(db_session, b, 1)
    assert (b.status, b.version) == ("PENDING_PITIKA", 2)


def test_advance_stale_changes_nothing(frozen, db_session, booking):
    b = booking()
    # Another request moved the booking on: the database row is at version 2.
    db_session.execute(text("UPDATE bookings SET version = 2 WHERE id = :id"), {"id": b.id})
    with pytest.raises(AppError) as caught:
        transitions.advance(db_session, b, 1, status=BookingStatus.CONFIRMED)
    assert caught.value.code == "STALE_VERSION"
    row = db_session.execute(
        text("SELECT status, version FROM bookings WHERE id = :id"), {"id": b.id}
    ).one()
    assert tuple(row) == ("PENDING_PITIKA", 2)


def test_reject_with_stage(frozen, db_session, booking, make_pitika):
    b = booking(sessions=((DAY, time(9), time(10)), (NEXT_DAY, time(9), time(10))))
    pitika = make_pitika()
    transitions.reject(
        db_session, b, 1, RejectedBy.PITIKA, pitika.id, "Wrong room.", ReviewStage.PITIKA
    )
    assert (b.status, b.version) == ("REJECTED", 2)
    blocking = db_session.scalars(
        select(BookingSession.is_blocking).where(BookingSession.booking_id == b.id)
    ).all()
    assert blocking == [False, False]
    assert (b.rejection.rejected_by, b.rejection.actor_user_id, b.rejection.reason) == (
        "PITIKA",
        pitika.id,
        "Wrong room.",
    )
    assert b.rejection.decided_at == datetime(2026, 11, 9, 1, 0)
    assert [(r.stage, r.decision, r.reviewer_id, r.notes) for r in b.reviews] == [
        ("PITIKA", "REJECTED", pitika.id, "Wrong room.")
    ]


def test_reject_by_system_has_no_review(frozen, db_session, booking):
    b = booking()
    transitions.reject(db_session, b, 1, RejectedBy.SYSTEM, None, "Expired.", None)
    assert (b.rejection.rejected_by, b.rejection.actor_user_id) == ("SYSTEM", None)
    assert b.reviews == []


def test_make_confirmed_adds_door_pass(frozen, db_session, booking):
    b = booking(BookingStatus.PENDING_OWNER, sessions=((NEXT_DAY, time(9), time(11)),))
    transitions.make_confirmed(db_session, b, 1)
    assert (b.status, b.version) == ("CONFIRMED", 2)
    assert b.door_pass.expires_at == datetime(2026, 11, 11, 4, 0)
    assert b.door_pass.passcode.startswith("NBC-")


def test_after_last_review_with_it_forwards(frozen, db_session, booking):
    b = booking(it=True, route=BookingRoute.R1)
    transitions.after_last_review(db_session, b, 1)
    assert (b.status, b.version) == ("SETUP_IN_PROGRESS", 2)
    assert b.it_ticket.forwarded_at == datetime(2026, 11, 9, 1, 0)
    assert b.door_pass is None


def test_after_last_review_without_it_confirms(frozen, db_session, booking):
    b = booking()
    transitions.after_last_review(db_session, b, 1)
    assert b.status == "CONFIRMED"
    assert b.door_pass is not None
