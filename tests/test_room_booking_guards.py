"""Changes to the current API (spec section 12, requirements section 10): private rooms
need an owner, places with future bookings cannot be turned off or moved (B-21), owners of
private rooms cannot leave, a booker turned off loses their bookings (B-27), B-14."""

from datetime import date, time

import pytest
from sqlalchemy import select

from app.constants.booking import BOOKER_OFF_REASON, BookingRoute, BookingStatus
from app.models import Booking, BookingSession
from app.services import room_bookings
from app.services.clock import LOCAL_OFFSET
from tests.booking_helpers import DAY, NOW, error, fields

API = "/api/v1"
TODAY = NOW.date()


@pytest.fixture
def owner(make_user):
    return make_user(roles=["ROOM_OWNER", "STAFF"])


@pytest.fixture
def booker(make_user):
    return make_user(roles=["STAFF"])


@pytest.fixture
def room(make_bookable_room):
    return make_bookable_room()


@pytest.fixture
def private_room(make_bookable_room, owner):
    return make_bookable_room(private=True, owner=owner)


def patch(client, headers, path, body):
    return client.patch(f"{API}/{path}", json=body, headers=headers)


def blocking_flags(db_session, booking_id) -> list[bool]:
    rows = db_session.scalars(
        select(BookingSession.is_blocking).where(BookingSession.booking_id == booking_id)
    )
    return list(rows)


def room_body(room, **overrides) -> dict:
    return {
        "name_en": "Mekong Room",
        "name_kh": "បន្ទប់មេគង្គ",
        "floor_id": room.floor_id,
        "category_id": room.category_id,
        "capacity": 12,
        "start_time": "08:00",
        "end_time": "18:00",
        **overrides,
    }


# --- Private rooms need an owner -------------------------------------------------------


def test_private_room_needs_owner(client, as_admin, room, private_room):
    message = "A private room needs an owner."
    response = client.post(
        f"{API}/rooms", json=room_body(room, is_private=True, room_owner_id=None), headers=as_admin
    )
    assert error(response) == (422, "OWNER_REQUIRED")
    assert response.json()["error"]["message"] == message
    assert fields(response) == {"room_owner_id": message}

    # A shared room with no owner becomes private.
    response = patch(client, as_admin, f"rooms/{room.id}", {"is_private": True})
    assert error(response) == (422, "OWNER_REQUIRED")
    assert fields(response) == {"room_owner_id": message}

    # A private room loses its owner.
    response = patch(client, as_admin, f"rooms/{private_room.id}", {"room_owner_id": None})
    assert error(response) == (422, "OWNER_REQUIRED")
    assert fields(response) == {"room_owner_id": message}

    # Both in one request is fine.
    response = patch(
        client, as_admin, f"rooms/{private_room.id}", {"room_owner_id": None, "is_private": False}
    )
    assert response.status_code == 200


def test_private_room_with_owner_is_saved(client, as_admin, room, owner):
    body = room_body(room, is_private=True, room_owner_id=owner.id)
    response = client.post(f"{API}/rooms", json=body, headers=as_admin)
    assert response.status_code == 201
    assert response.json()["owner"]["id"] == owner.id


# --- Private to shared (B-14) -----------------------------------------------------------


def test_private_to_shared_with_pending_owner(
    client, frozen, as_admin, private_room, booker, make_booking
):
    make_booking(private_room, booker, status=BookingStatus.PENDING_OWNER, route=BookingRoute.R2)
    response = patch(client, as_admin, f"rooms/{private_room.id}", {"is_private": False})
    message = "Resolve 1 bookings waiting for the room owner first."
    assert error(response) == (409, "HAS_PENDING_OWNER_BOOKINGS")
    assert response.json()["error"]["message"] == message
    assert fields(response) == {"is_private": message}


def test_private_to_shared_with_pending_r2(
    client, frozen, as_admin, private_room, booker, make_booking
):
    for _ in range(2):
        make_booking(
            private_room, booker, status=BookingStatus.PENDING_PITIKA, route=BookingRoute.R2
        )
    response = patch(client, as_admin, f"rooms/{private_room.id}", {"is_private": False})
    assert error(response) == (409, "HAS_PENDING_OWNER_BOOKINGS")
    message = "Resolve 2 bookings waiting for the room owner first."
    assert response.json()["error"]["message"] == message


def test_private_to_shared_with_other_bookings(
    client, frozen, as_admin, private_room, booker, make_booking
):
    # Waiting for Pitika on another route, or already past the owner: allowed.
    make_booking(private_room, booker, status=BookingStatus.PENDING_PITIKA, route=BookingRoute.R1)
    make_booking(private_room, booker, status=BookingStatus.CONFIRMED, route=BookingRoute.R2)
    make_booking(
        private_room,
        booker,
        status=BookingStatus.REJECTED,
        route=BookingRoute.R2,
        sessions=((DAY, time(11), time(12)),),
    )
    response = patch(client, as_admin, f"rooms/{private_room.id}", {"is_private": False})
    assert response.status_code == 200
    assert response.json()["is_private"] is False


def test_owner_change_keeps_waiting_bookings(
    client, frozen, as_admin, private_room, booker, make_booking, make_user, auth_headers
):
    """The owner queue reads the room's owner when it is read (BR-OWN-05)."""
    booking = make_booking(
        private_room, booker, status=BookingStatus.PENDING_OWNER, route=BookingRoute.R2
    )
    new_owner = make_user(roles=["ROOM_OWNER"])
    response = patch(client, as_admin, f"rooms/{private_room.id}", {"room_owner_id": new_owner.id})
    assert response.status_code == 200
    queue = client.get(f"{API}/owner/bookings", headers=auth_headers(new_owner)).json()
    assert [item["id"] for item in queue["items"]] == [booking.id]


# --- Turning off ------------------------------------------------------------------------


def test_turn_off_room_with_future_bookings(client, frozen, as_admin, room, booker, make_booking):
    make_booking(room, booker, status=BookingStatus.CONFIRMED)
    response = patch(client, as_admin, f"rooms/{room.id}", {"is_active": False})
    message = "This room has 1 future bookings. Ask the bookers to cancel first."
    assert error(response) == (409, "HAS_FUTURE_BOOKINGS")
    assert response.json()["error"]["message"] == message
    assert fields(response) == {"is_active": message}


def _place(room, place):
    floor = room.floor
    building = floor.building
    return {
        "floor": ("floors", floor.id, "floor"),
        "building": ("buildings", building.id, "building"),
        "location": ("locations", building.location_id, "office"),
    }[place]


@pytest.mark.parametrize("place", ["floor", "building", "location"])
def test_turn_off_place_with_future_bookings(
    client, frozen, as_admin, room, booker, make_booking, make_room, place
):
    # Two sessions of one booking count once; a second room in the same floor counts too.
    two_days = ((DAY, time(9), time(10)), (date(2026, 11, 11), time(9), time(10)))
    make_booking(room, booker, status=BookingStatus.PENDING_PITIKA, sessions=two_days)
    neighbour = make_room(room.floor)
    make_booking(neighbour, booker, status=BookingStatus.SETUP_IN_PROGRESS)
    path, place_id, word = _place(room, place)
    response = patch(client, as_admin, f"{path}/{place_id}", {"is_active": False})
    message = f"This {word} has 2 future bookings. Ask the bookers to cancel first."
    assert error(response) == (409, "HAS_FUTURE_BOOKINGS")
    assert response.json()["error"]["message"] == message
    assert fields(response) == {"is_active": message}


@pytest.mark.parametrize("place", ["room", "floor", "building", "location"])
def test_past_bookings_do_not_block(
    client, frozen, as_admin, room, booker, make_booking, make_user, place
):
    # Ended this morning; a cancelled future one; and one ending exactly now.
    make_booking(
        room, booker, status=BookingStatus.CONFIRMED, sessions=((TODAY, time(6), time(7)),)
    )
    make_booking(room, booker, status=BookingStatus.CANCELLED)
    make_booking(
        room, booker, status=BookingStatus.SETUP_IN_PROGRESS, sessions=((TODAY, time(7), time(8)),)
    )
    path, place_id = ("rooms", room.id) if place == "room" else _place(room, place)[:2]
    response = patch(client, as_admin, f"{path}/{place_id}", {"is_active": False})
    assert response.status_code == 200
    assert response.json()["is_active"] is False


def test_booking_in_progress_blocks(client, frozen, as_admin, room, booker, make_booking):
    make_booking(
        room, booker, status=BookingStatus.CONFIRMED, sessions=((TODAY, time(7), time(9)),)
    )
    response = patch(client, as_admin, f"rooms/{room.id}", {"is_active": False})
    assert error(response) == (409, "HAS_FUTURE_BOOKINGS")


def test_inactive_place_is_not_checked_again(
    client, frozen, as_admin, room, booker, make_booking, db_session
):
    make_booking(room, booker, status=BookingStatus.CONFIRMED)
    room.floor.is_active = False
    db_session.flush()
    response = patch(client, as_admin, f"floors/{room.floor_id}", {"is_active": False})
    assert response.status_code == 200


# --- Moving (B-21) ----------------------------------------------------------------------


@pytest.mark.parametrize(
    "move", ["room.floor_id", "floor.building_id", "building.location_id", "location.province"]
)
def test_move_with_future_bookings(
    client,
    frozen,
    as_admin,
    room,
    booker,
    make_booking,
    make_floor,
    make_building,
    make_location,
    move,
):
    make_booking(room, booker, status=BookingStatus.PENDING_PITIKA)
    floor = room.floor
    building = floor.building
    path, place_id, field, value, word = {
        "room.floor_id": ("rooms", room.id, "floor_id", make_floor().id, "room"),
        "floor.building_id": ("floors", floor.id, "building_id", make_building().id, "floor"),
        "building.location_id": (
            "buildings",
            building.id,
            "location_id",
            make_location().id,
            "building",
        ),
        "location.province": ("locations", building.location_id, "province", "SIEM_REAP", "office"),
    }[move]
    response = patch(client, as_admin, f"{path}/{place_id}", {field: value})
    message = f"This {word} has 1 future bookings. Move it after they end."
    assert error(response) == (409, "HAS_FUTURE_BOOKINGS")
    assert response.json()["error"]["message"] == message
    assert fields(response) == {field: message}


def test_move_without_future_bookings(
    client, frozen, as_admin, room, booker, make_booking, make_floor
):
    make_booking(
        room, booker, status=BookingStatus.CONFIRMED, sessions=((TODAY, time(6), time(7)),)
    )
    target = make_floor()
    response = patch(client, as_admin, f"rooms/{room.id}", {"floor_id": target.id})
    assert response.status_code == 200
    # Sending the same parent again is not a move.
    response = patch(client, as_admin, f"rooms/{room.id}", {"floor_id": target.id})
    assert response.status_code == 200


def test_same_province_is_not_a_move(client, frozen, as_admin, room, booker, make_booking):
    make_booking(room, booker, status=BookingStatus.CONFIRMED)
    location_id = room.floor.building.location_id
    response = patch(client, as_admin, f"locations/{location_id}", {"province": "PHNOM_PENH"})
    assert response.status_code == 200


# --- Users ------------------------------------------------------------------------------


def test_owner_turned_off_with_private_room(
    client, as_admin, owner, private_room, room, db_session, make_bookable_room
):
    make_bookable_room(private=True, owner=owner)
    response = patch(client, as_admin, f"users/{owner.id}", {"is_active": False})
    message = "Assign a new owner for 2 private rooms first."
    assert error(response) == (409, "OWNER_HAS_PRIVATE_ROOMS")
    assert response.json()["error"]["message"] == message
    assert fields(response) == {"is_active": message}
    db_session.refresh(owner)
    db_session.refresh(private_room)
    assert owner.is_active is True
    assert private_room.room_owner_id == owner.id


def test_owner_loses_role_with_private_room(client, as_admin, owner, private_room, db_session):
    response = client.put(
        f"{API}/users/{owner.id}/roles", json={"role_codes": ["STAFF"]}, headers=as_admin
    )
    message = "Assign a new owner for 1 private rooms first."
    assert error(response) == (409, "OWNER_HAS_PRIVATE_ROOMS")
    assert fields(response) == {"role_codes": message}
    db_session.refresh(private_room)
    assert private_room.room_owner_id == owner.id


def test_shared_rooms_still_cleared(client, as_admin, owner, make_bookable_room, db_session):
    shared = make_bookable_room(owner=owner)
    response = client.put(
        f"{API}/users/{owner.id}/roles", json={"role_codes": ["STAFF"]}, headers=as_admin
    )
    assert response.status_code == 200
    body = response.json()
    assert (body["rooms_unassigned"], body["bookings_cancelled"]) == ([shared.id], [])

    other = make_bookable_room(owner=owner)
    response = patch(client, as_admin, f"users/{owner.id}", {"is_active": False})
    assert response.status_code == 200
    assert response.json()["rooms_unassigned"] == [other.id]
    db_session.refresh(other)
    assert other.room_owner_id is None


def test_booker_turned_off_cancels_bookings(
    client, frozen, as_admin, room, booker, make_booking, make_user, db_session
):
    pending = make_booking(room, booker, status=BookingStatus.PENDING_PITIKA)
    confirmed = make_booking(
        room, booker, status=BookingStatus.CONFIRMED, sessions=((DAY, time(11), time(12)),)
    )
    in_progress = make_booking(
        room, booker, status=BookingStatus.CONFIRMED, sessions=((TODAY, time(7), time(9)),)
    )
    completed = make_booking(
        room, booker, status=BookingStatus.CONFIRMED, sessions=((TODAY, time(6), time(7)),)
    )
    rejected = make_booking(
        room, booker, status=BookingStatus.REJECTED, sessions=((DAY, time(13), time(14)),)
    )
    someone_elses = make_booking(
        room,
        make_user(roles=["STAFF"]),
        status=BookingStatus.PENDING_PITIKA,
        sessions=((DAY, time(15), time(16)),),
    )

    response = patch(client, as_admin, f"users/{booker.id}", {"is_active": False})
    assert response.status_code == 200
    cancelled_ids = sorted([pending.id, confirmed.id, in_progress.id])
    assert response.json()["bookings_cancelled"] == cancelled_ids

    for booking_id in cancelled_ids:
        booking = db_session.get(Booking, booking_id, populate_existing=True)
        assert booking.status == BookingStatus.CANCELLED
        assert booking.cancel_reason == BOOKER_OFF_REASON
        assert booking.cancelled_at == NOW - LOCAL_OFFSET  # UTC
        assert booking.version == 2
        assert blocking_flags(db_session, booking_id) == [False]
    for untouched, status in (
        (completed, BookingStatus.CONFIRMED),
        (rejected, BookingStatus.REJECTED),
        (someone_elses, BookingStatus.PENDING_PITIKA),
    ):
        booking = db_session.get(Booking, untouched.id, populate_existing=True)
        assert (booking.status, booking.version) == (status, 1)
    assert blocking_flags(db_session, someone_elses.id) == [True]

    # Turning the user on again restores nothing.
    again = patch(client, as_admin, f"users/{booker.id}", {"is_active": True}).json()
    assert again["bookings_cancelled"] == []
    booking = db_session.get(Booking, pending.id, populate_existing=True)
    assert booking.status == BookingStatus.CANCELLED


def test_owner_check_comes_before_cancelling(
    client, frozen, as_admin, owner, private_room, room, make_booking, db_session
):
    booking = make_booking(room, owner, status=BookingStatus.PENDING_PITIKA)
    response = patch(client, as_admin, f"users/{owner.id}", {"is_active": False})
    assert error(response) == (409, "OWNER_HAS_PRIVATE_ROOMS")
    booking = db_session.get(Booking, booking.id, populate_existing=True)
    assert booking.status == BookingStatus.PENDING_PITIKA


def test_other_user_changes_cancel_nothing(client, frozen, as_admin, room, booker, make_booking):
    make_booking(room, booker, status=BookingStatus.PENDING_PITIKA)
    response = patch(client, as_admin, f"users/{booker.id}", {"name_en": "Renamed"})
    assert response.status_code == 200
    assert response.json()["bookings_cancelled"] == []


# --- Seats and hours --------------------------------------------------------------------


def test_lower_seats_and_hours_keep_bookings(
    client, frozen, as_admin, room, booker, make_booking, db_session
):
    booking = make_booking(room, booker, status=BookingStatus.CONFIRMED, attendees=8)
    body = {"capacity": 2, "start_time": "13:00", "end_time": "17:00"}
    response = patch(client, as_admin, f"rooms/{room.id}", body)
    assert response.status_code == 200
    booking = db_session.get(Booking, booking.id, populate_existing=True)
    assert (booking.status, booking.version, booking.attendees) == (
        BookingStatus.CONFIRMED,
        1,
        8,
    )
    assert blocking_flags(db_session, booking.id) == [True]


# --- Helpers ----------------------------------------------------------------------------


def test_helpers(frozen, db_session, room, private_room, booker, make_booking, make_room):
    make_booking(room, booker, status=BookingStatus.CONFIRMED)
    make_booking(private_room, booker, status=BookingStatus.PENDING_OWNER, route=BookingRoute.R2)
    neighbour = make_room(room.floor)
    assert room_bookings.room_ids_in(db_session, floor_id=room.floor_id) == sorted(
        [room.id, neighbour.id]
    )
    location_id = room.floor.building.location_id
    assert room_bookings.room_ids_in(db_session, location_id=location_id) == sorted(
        [room.id, neighbour.id]
    )
    assert room_bookings.future_booking_count(db_session, [room.id, private_room.id]) == 2
    assert room_bookings.future_booking_count(db_session, []) == 0
    assert room_bookings.pending_owner_count(db_session, private_room.id) == 1
    assert room_bookings.pending_owner_count(db_session, room.id) == 0
    assert room_bookings.private_room_ids_owned_by(db_session, private_room.room_owner_id) == [
        private_room.id
    ]
