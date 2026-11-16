"""GET /room-schedule: every room's blocking sessions on one day (Staff booking pages, 12 Nov 2026).

One request feeds the room cards ("Free until 14:00") and the "Free now" filter; masking is the
same as GET /rooms/{id}/schedule (spec 8.1)."""

from datetime import date, time, timedelta

from app.constants.booking import MASKED_TITLE, BookingStatus
from tests.booking_helpers import error, fields

URL = "/api/v1/room-schedule"


def day(offset):
    """The date `offset` days after the frozen today (2026-11-09)."""
    return date(2026, 11, 9) + timedelta(days=offset)


def one_hour(offset, hour=9):
    return ((day(offset), time(hour), time(hour + 1)),)


def by_room(response):
    return {row["room_id"]: row["items"] for row in response.json()["items"]}


def test_one_request_gives_every_room(
    client, frozen, make_user, make_bookable_room, make_booking, auth_headers
):
    room_a, room_b = make_bookable_room(), make_bookable_room()
    user = make_user(roles=["STAFF"])
    make_booking(room_a, user, status=BookingStatus.CONFIRMED, sessions=one_hour(1))
    response = client.get(f"{URL}?date={day(1)}", headers=auth_headers(user))
    assert response.status_code == 200
    rooms = by_room(response)
    assert [(i["start_time"], i["end_time"]) for i in rooms[room_a.id]] == [("09:00", "10:00")]
    assert rooms[room_b.id] == []


def test_room_ids_filter(client, frozen, make_bookable_room, as_staff):
    room_a, room_b = make_bookable_room(), make_bookable_room()
    response = client.get(f"{URL}?date={day(1)}&room_ids={room_b.id}", headers=as_staff)
    assert list(by_room(response)) == [room_b.id]
    assert room_a.id not in by_room(response)


def test_private_booking_is_masked_like_the_room_schedule(
    client, frozen, make_user, make_bookable_room, make_booking, auth_headers
):
    room = make_bookable_room(private=True)
    booker = make_user(roles=["STAFF"])
    make_booking(room, booker, status=BookingStatus.CONFIRMED, sessions=one_hour(1))
    viewer = auth_headers(make_user(roles=["STAFF"]))
    item = by_room(client.get(f"{URL}?date={day(1)}&room_ids={room.id}", headers=viewer))[room.id][
        0
    ]
    assert item["is_masked"] is True
    assert item["booking_id"] is None
    assert item["title"] == MASKED_TITLE
    same = client.get(f"/api/v1/rooms/{room.id}/schedule?from={day(1)}&to={day(1)}", headers=viewer)
    assert same.json()["items"][0] == item


def test_cancelled_booking_does_not_block(
    client, frozen, make_user, make_bookable_room, make_booking, auth_headers
):
    room = make_bookable_room()
    user = make_user(roles=["STAFF"])
    make_booking(room, user, status=BookingStatus.CANCELLED, sessions=one_hour(1))
    response = client.get(f"{URL}?date={day(1)}&room_ids={room.id}", headers=auth_headers(user))
    assert by_room(response)[room.id] == []


def test_too_many_ids(client, frozen, as_staff):
    ids = ",".join(str(n) for n in range(1, 202))
    response = client.get(f"{URL}?date={day(1)}&room_ids={ids}", headers=as_staff)
    assert error(response) == (422, "VALIDATION_ERROR")
    assert "room_ids" in fields(response)


def test_needs_sign_in(client):
    assert client.get(URL).status_code == 401
