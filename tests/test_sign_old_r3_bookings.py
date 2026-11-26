"""The one-off fix for R3 bookings confirmed at send before 26 Nov 2026: they got no confirm time
and no request slip signers, so their slip's opinion boxes stayed empty."""

from datetime import datetime

from app.constants.booking import BookingRoute, BookingStatus, SignerRole
from app.models import BookingSigner
from scripts.sign_old_r3_bookings import sign_all


def _signer_roles(db_session, booking):
    rows = db_session.query(BookingSigner).filter_by(booking_id=booking.id).all()
    return {row.role for row in rows}


SENT = datetime(2026, 11, 2, 3, 15)  # UTC, a week before the frozen "now"


def _old_r3(db_session, make_bookable_room, make_user, make_booking):
    """A confirmed R3 booking as one sent before the fix: no confirm time, no signers."""
    owner = make_user(roles=["ROOM_OWNER"])
    room = make_bookable_room(private=True, owner=owner)
    booking = make_booking(room, owner, status=BookingStatus.CONFIRMED, route=BookingRoute.R3)
    booking.confirmed_at = None
    booking.created_at = SENT
    db_session.flush()
    return booking


def test_signs_old_r3_bookings_with_their_send_time(
    frozen, db_session, make_bookable_room, make_user, make_booking
):
    booking = _old_r3(db_session, make_bookable_room, make_user, make_booking)
    assert booking.confirmed_at is None

    assert sign_all(db_session) == [booking.id]
    db_session.refresh(booking)
    # An R3 booking is confirmed when it is sent.
    assert booking.confirmed_at == SENT
    assert SignerRole.MAKER in _signer_roles(db_session, booking)


def test_leaves_other_bookings_alone(
    frozen, db_session, make_bookable_room, make_user, make_booking
):
    room = make_bookable_room()
    booker = make_user(roles=["STAFF"])
    waiting = make_booking(room, booker, status=BookingStatus.PENDING_PITIKA)
    cancelled = _old_r3(db_session, make_bookable_room, make_user, make_booking)
    cancelled.status = BookingStatus.CANCELLED
    db_session.flush()

    assert sign_all(db_session) == []
    assert waiting.confirmed_at is None
    assert cancelled.confirmed_at is None


def test_running_it_again_changes_nothing(
    frozen, db_session, make_bookable_room, make_user, make_booking
):
    booking = _old_r3(db_session, make_bookable_room, make_user, make_booking)
    sign_all(db_session)
    assert sign_all(db_session) == []
    rows = db_session.query(BookingSigner).filter_by(booking_id=booking.id).all()
    assert len(rows) == len({row.role for row in rows})
