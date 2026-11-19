"""The one-off move of bookings still in IT setup to Confirmed (spec 2026-11-19-it-setup-addon)."""

from app.constants.booking import BookingStatus
from scripts.confirm_it_setup_bookings import confirm_all


def test_confirms_every_booking_still_in_it_setup(
    frozen, db_session, make_bookable_room, make_user, make_booking
):
    room = make_bookable_room()
    booker = make_user(roles=["STAFF"])
    waiting = make_booking(
        room, booker, status=BookingStatus.SETUP_IN_PROGRESS, it=True, forwarded=True
    )
    pending = make_booking(room, booker, status=BookingStatus.PENDING_PITIKA, it=True)

    assert confirm_all(db_session) == [waiting.id]
    assert (waiting.status, waiting.version) == (BookingStatus.CONFIRMED, 2)
    assert waiting.door_pass is not None
    assert waiting.confirmed_at is not None
    assert pending.status == BookingStatus.PENDING_PITIKA


def test_running_it_again_changes_nothing(
    frozen, db_session, make_bookable_room, make_user, make_booking
):
    booking = make_booking(
        make_bookable_room(),
        make_user(roles=["STAFF"]),
        status=BookingStatus.SETUP_IN_PROGRESS,
        it=True,
    )
    confirm_all(db_session)
    assert confirm_all(db_session) == []
    assert booking.version == 2
