"""Who can see a booking and its door pass (spec 8.1)."""

from types import SimpleNamespace

import pytest

from app.constants.booking import MASKED_TITLE, BookingStatus
from app.errors import AppError, ErrorCode
from app.services import booking_access as access
from app.services import clock
from tests.booking_helpers import current_for


@pytest.fixture
def world(make_bookable_room, make_user, make_pitika, make_booking, db_session):
    """A private room in Phnom Penh with a CONFIRMED booking that has an IT ticket."""
    owner = make_user(roles=["ROOM_OWNER"])
    room = make_bookable_room(private=True, owner=owner)
    booker = make_user(roles=["STAFF"])
    helper = make_user(roles=["IT_STAFF"])
    booking = make_booking(
        room,
        booker,
        status=BookingStatus.CONFIRMED,
        it=True,
        assigned_staff=[helper],
        meeting_title="Budget talk",
    )
    return SimpleNamespace(
        room=room,
        owner=owner,
        booker=booker,
        booking=booking,
        helper=helper,
        other_helper=make_user(roles=["IT_STAFF"]),
        pitika=make_pitika(province="PHNOM_PENH"),
        far_pitika=make_pitika(province="SIEM_REAP"),
        admin=make_user(roles=["ADMIN"]),
        stranger=make_user(roles=["STAFF"]),
        lead=make_user(roles=["IT_LEAD"]),
        current=lambda user: current_for(db_session, user),
    )


def test_booker_can_view(world, db_session):
    assert access.can_view(db_session, world.current(world.booker), world.booking)


def test_admin_can_view(world, db_session):
    assert access.can_view(db_session, world.current(world.admin), world.booking)


def test_room_owner_can_view(world, db_session):
    assert access.can_view(db_session, world.current(world.owner), world.booking)


def test_another_owner_cannot_view(world, make_user, db_session):
    other = make_user(roles=["ROOM_OWNER"])
    assert not access.can_view(db_session, world.current(other), world.booking)


def test_pitika_of_same_province_can_view(world, db_session):
    assert access.can_view(db_session, world.current(world.pitika), world.booking)


def test_pitika_of_other_province_cannot_view(world, db_session):
    assert not access.can_view(db_session, world.current(world.far_pitika), world.booking)


def test_pitika_without_division_cannot_view(world, make_user, db_session):
    nobody = make_user(roles=["PITIKA"])
    assert not access.can_view(db_session, world.current(nobody), world.booking)


def test_stranger_cannot_view(world, db_session):
    assert not access.can_view(db_session, world.current(world.stranger), world.booking)


def test_it_lead_before_and_after_forward(world, db_session):
    current = world.current(world.lead)
    assert not access.can_view(db_session, current, world.booking)
    world.booking.it_ticket.forwarded_at = clock.now_utc()
    db_session.flush()
    assert access.can_view(db_session, current, world.booking)


def test_it_lead_cannot_view_a_booking_without_it(world, make_booking, db_session):
    plain = make_booking(world.room, world.booker, status=BookingStatus.CONFIRMED)
    assert not access.can_view(db_session, world.current(world.lead), plain)


def test_it_staff_assigned_can_view(world, db_session):
    assert access.can_view(db_session, world.current(world.helper), world.booking)


def test_it_staff_not_assigned_cannot_view(world, db_session):
    assert not access.can_view(db_session, world.current(world.other_helper), world.booking)


def test_province_helpers(world):
    assert access.room_province(world.room) == "PHNOM_PENH"
    assert access.pitika_province(world.current(world.far_pitika)) == "SIEM_REAP"
    assert access.pitika_province(world.current(world.stranger)) is None


# --- Door pass -------------------------------------------------------------------------


@pytest.mark.parametrize("who", ["booker", "admin", "owner", "pitika"])
def test_door_pass_viewers(world, who):
    assert access.is_door_pass_viewer(world.current(getattr(world, who)), world.booking)


@pytest.mark.parametrize("who", ["far_pitika", "lead", "helper", "stranger"])
def test_not_door_pass_viewers(world, who):
    assert not access.is_door_pass_viewer(world.current(getattr(world, who)), world.booking)


# --- Loading and masking ---------------------------------------------------------------


def test_load_visible_booking(world, db_session):
    loaded = access.load_visible_booking(db_session, world.current(world.booker), world.booking.id)
    assert loaded.id == world.booking.id


def test_load_visible_booking_hides_what_you_cannot_see(world, db_session):
    with pytest.raises(AppError) as caught:
        access.load_visible_booking(db_session, world.current(world.stranger), world.booking.id)
    assert (caught.value.status, caught.value.code) == (404, ErrorCode.NOT_FOUND)


def test_load_visible_booking_missing(world, db_session):
    with pytest.raises(AppError) as caught:
        access.load_visible_booking(db_session, world.current(world.admin), 999_999)
    assert caught.value.status == 404


def test_private_title_masked_for_others(world, db_session):
    title = access.visible_title(db_session, world.current(world.stranger), world.booking)
    assert title == MASKED_TITLE


@pytest.mark.parametrize("who", ["booker", "owner", "admin", "pitika"])
def test_private_title_shown_to_those_who_can_view(world, who, db_session):
    current = world.current(getattr(world, who))
    assert access.visible_title(db_session, current, world.booking) == "Budget talk"


def test_shared_room_title_never_masked(make_bookable_room, make_user, make_booking, db_session):
    booking = make_booking(
        make_bookable_room(), make_user(), status=BookingStatus.CONFIRMED, meeting_title="Open"
    )
    stranger = current_for(db_session, make_user(roles=["STAFF"]))
    assert access.visible_title(db_session, stranger, booking) == "Open"
