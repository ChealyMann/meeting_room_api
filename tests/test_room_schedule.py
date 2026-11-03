"""GET /rooms/{id}/schedule: spec 9.2, 8.1."""

from datetime import date, time, timedelta

from sqlalchemy import event

from app.constants.booking import MASKED_TITLE, BookingStatus
from tests.booking_helpers import error, fields


def url(room, **query):
    params = "&".join(f"{key}={value}" for key, value in query.items())
    return f"/api/v1/rooms/{room.id}/schedule" + (f"?{params}" if params else "")


def day(offset):
    """The date `offset` days after the frozen today (2026-11-09)."""
    return date(2026, 11, 9) + timedelta(days=offset)


def one_hour(offset, hour=9):
    return ((day(offset), time(hour), time(hour + 1)),)


def test_default_range_is_7_days(
    client, frozen, make_user, make_bookable_room, make_booking, auth_headers
):
    room = make_bookable_room()
    user = make_user(roles=["STAFF"])
    for offset in (-1, 0, 6, 7):
        make_booking(room, user, status=BookingStatus.CONFIRMED, sessions=one_hour(offset))
    response = client.get(url(room), headers=auth_headers(user))
    assert response.status_code == 200
    dates = [item["date"] for item in response.json()["items"]]
    assert dates == [day(0).isoformat(), day(6).isoformat()]
    assert response.json()["total"] == 2


def test_from_and_to_are_inclusive(
    client, frozen, make_user, make_bookable_room, make_booking, auth_headers
):
    room = make_bookable_room()
    user = make_user(roles=["STAFF"])
    for offset in (9, 10, 11, 12):
        make_booking(room, user, status=BookingStatus.CONFIRMED, sessions=one_hour(offset))
    response = client.get(url(room, **{"from": day(10), "to": day(11)}), headers=auth_headers(user))
    assert [item["date"] for item in response.json()["items"]] == [
        day(10).isoformat(),
        day(11).isoformat(),
    ]


def test_only_from_means_7_days_from_it(
    client, frozen, make_user, make_bookable_room, make_booking, auth_headers
):
    room = make_bookable_room()
    user = make_user(roles=["STAFF"])
    for offset in (9, 10, 16, 17):
        make_booking(room, user, status=BookingStatus.CONFIRMED, sessions=one_hour(offset))
    response = client.get(url(room, **{"from": day(10)}), headers=auth_headers(user))
    assert [item["date"] for item in response.json()["items"]] == [
        day(10).isoformat(),
        day(16).isoformat(),
    ]


def test_31_days_allowed(client, frozen, make_bookable_room, as_staff):
    room = make_bookable_room()
    response = client.get(url(room, **{"from": day(0), "to": day(30)}), headers=as_staff)
    assert response.status_code == 200


def test_32_days_refused(client, frozen, make_bookable_room, as_staff):
    room = make_bookable_room()
    response = client.get(url(room, **{"from": day(0), "to": day(31)}), headers=as_staff)
    assert error(response) == (422, "VALIDATION_ERROR")
    assert fields(response)["to"] == "At most 31 days."


def test_to_before_from(client, frozen, make_bookable_room, as_staff):
    room = make_bookable_room()
    response = client.get(url(room, **{"from": day(5), "to": day(4)}), headers=as_staff)
    assert error(response) == (422, "VALIDATION_ERROR")
    assert "to" in fields(response)


def test_only_to_before_today_refused(client, frozen, make_bookable_room, as_staff):
    room = make_bookable_room()
    response = client.get(url(room, to=day(-1)), headers=as_staff)
    assert error(response) == (422, "VALIDATION_ERROR")
    assert "to" in fields(response)


def test_bad_date_422(client, frozen, make_bookable_room, as_staff):
    room = make_bookable_room()
    response = client.get(url(room, **{"from": "tomorrow"}), headers=as_staff)
    assert error(response) == (422, "VALIDATION_ERROR")
    assert "from" in fields(response)


def test_only_blocking_sorted(
    client, frozen, make_user, make_bookable_room, make_booking, auth_headers
):
    room = make_bookable_room()
    user = make_user(roles=["STAFF"])
    late = make_booking(room, user, status=BookingStatus.CONFIRMED, sessions=one_hour(2, 14))
    early = make_booking(
        room,
        user,
        status=BookingStatus.CONFIRMED,
        sessions=(*one_hour(2, 9), *one_hour(1, 16)),
    )
    make_booking(room, user, status=BookingStatus.CANCELLED, sessions=one_hour(1, 8))
    make_booking(room, user, status=BookingStatus.REJECTED, sessions=one_hour(1, 11))
    pending = make_booking(room, user, status=BookingStatus.PENDING_PITIKA, sessions=one_hour(3))
    items = client.get(url(room), headers=auth_headers(user)).json()["items"]
    assert [(i["date"], i["start_time"], i["end_time"]) for i in items] == [
        (day(1).isoformat(), "16:00", "17:00"),
        (day(2).isoformat(), "09:00", "10:00"),
        (day(2).isoformat(), "14:00", "15:00"),
        (day(3).isoformat(), "09:00", "10:00"),
    ]
    assert [i["booking_id"] for i in items] == [early.id, early.id, late.id, pending.id]
    assert items[3]["status"] == "PENDING_PITIKA"


def test_other_rooms_not_shown(
    client, frozen, make_user, make_bookable_room, make_booking, auth_headers
):
    room = make_bookable_room()
    user = make_user(roles=["STAFF"])
    make_booking(make_bookable_room(), user, status=BookingStatus.CONFIRMED, sessions=one_hour(1))
    response = client.get(url(room), headers=auth_headers(user))
    assert response.json() == {"items": [], "total": 0}


def test_item_shape_in_shared_room(
    client, frozen, make_user, make_bookable_room, make_booking, auth_headers
):
    room = make_bookable_room()
    booker = make_user(roles=["STAFF"])
    booking = make_booking(room, booker, status=BookingStatus.CONFIRMED, sessions=one_hour(1))
    viewer = make_user(roles=["STAFF"])
    item = client.get(url(room), headers=auth_headers(viewer)).json()["items"][0]
    assert item == {
        "date": day(1).isoformat(),
        "start_time": "09:00",
        "end_time": "10:00",
        "booking_id": booking.id,
        "reference_code": booking.reference_code,
        "title": booking.meeting_title,
        "requester_name": booker.name_en,
        "status": "CONFIRMED",
        "is_masked": False,
    }


def test_private_masked_for_staff(
    client, frozen, make_user, make_bookable_room, make_booking, auth_headers
):
    room = make_bookable_room(private=True)
    booker = make_user(roles=["STAFF"])
    make_booking(room, booker, status=BookingStatus.CONFIRMED, sessions=one_hour(1))
    viewer = make_user(roles=["STAFF"])
    item = client.get(url(room), headers=auth_headers(viewer)).json()["items"][0]
    assert item == {
        "date": day(1).isoformat(),
        "start_time": "09:00",
        "end_time": "10:00",
        "booking_id": None,
        "reference_code": None,
        "title": MASKED_TITLE,
        "requester_name": None,
        "status": "CONFIRMED",
        "is_masked": True,
    }


def test_private_visible_to_owner_and_booker(
    client, frozen, make_user, make_bookable_room, make_booking, auth_headers
):
    owner = make_user(roles=["ROOM_OWNER"])
    room = make_bookable_room(private=True, owner=owner)
    booker = make_user(roles=["STAFF"])
    booking = make_booking(room, booker, status=BookingStatus.CONFIRMED, sessions=one_hour(1))
    for viewer in (owner, booker):
        item = client.get(url(room), headers=auth_headers(viewer)).json()["items"][0]
        assert item["is_masked"] is False
        assert item["booking_id"] == booking.id
        assert item["title"] == booking.meeting_title
        assert item["requester_name"] == booker.name_en


def test_shared_never_masked(
    client, frozen, make_user, make_bookable_room, make_booking, auth_headers
):
    room = make_bookable_room(private=False)
    booker = make_user(roles=["STAFF"])
    make_booking(room, booker, status=BookingStatus.CONFIRMED, sessions=one_hour(1))
    viewer = make_user(roles=["STAFF"])
    item = client.get(url(room), headers=auth_headers(viewer)).json()["items"][0]
    assert item["is_masked"] is False
    assert item["title"] != MASKED_TITLE


def test_inactive_room_still_answers(client, frozen, make_bookable_room, as_staff):
    room = make_bookable_room(is_active=False)
    assert client.get(url(room), headers=as_staff).status_code == 200


def test_missing_room_404(client, frozen, as_staff):
    response = client.get("/api/v1/rooms/999999/schedule", headers=as_staff)
    assert error(response) == (404, "NOT_FOUND")


def test_needs_sign_in(client, frozen, make_bookable_room):
    room = make_bookable_room()
    assert client.get(url(room)).status_code == 401


def test_query_count_does_not_grow(
    client, frozen, conn, db_session, make_user, make_bookable_room, make_booking, auth_headers
):
    """The sessions' bookings, rooms and tickets are preloaded: the number of SQL
    statements is the same for 2 or 8 sessions, even when each booking is its own."""
    room = make_bookable_room(private=True)
    headers = auth_headers(make_user(roles=["STAFF"]))

    def add(n):
        for i in range(n):
            booker = make_user(roles=["STAFF"])
            make_booking(
                room, booker, status=BookingStatus.CONFIRMED, it=True, sessions=one_hour(1, 8 + i)
            )
        db_session.expire_all()

    def statements():
        seen = []

        def remember(*_args):
            seen.append(1)

        event.listen(conn, "before_cursor_execute", remember)
        try:
            response = client.get(url(room), headers=headers)
        finally:
            event.remove(conn, "before_cursor_execute", remember)
        assert response.status_code == 200
        return len(seen), response.json()["total"]

    add(2)
    few = statements()
    add(4)
    many = statements()
    assert (few[1], many[1]) == (2, 6)
    assert many[0] == few[0]
