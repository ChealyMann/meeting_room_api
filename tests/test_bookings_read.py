"""GET /bookings/{id} and GET /bookings/mine: spec 9.5, 9.6, B-08, B-10."""

from datetime import datetime, time, timedelta

import pytest

from app.constants.booking import BookingRoute, BookingStatus
from tests.booking_helpers import DAY, URL, error, fields

NEXT_DAY = DAY + timedelta(days=1)


@pytest.fixture
def private_booking(make_user, make_pitika, make_bookable_room, make_booking):
    """An R2 booking with IT, in a private Phnom Penh room, waiting for the owner."""

    def build(forwarded=True):
        owner = make_user(roles=["ROOM_OWNER"])
        room = make_bookable_room(private=True, owner=owner)
        booker = make_user(roles=["STAFF"])
        booking = make_booking(
            room,
            booker,
            status=BookingStatus.PENDING_OWNER,
            route=BookingRoute.R2,
            it=True,
            forwarded=forwarded,
        )
        return booking, booker, owner

    return build


@pytest.mark.parametrize("viewer", ["booker", "admin", "owner", "pitika", "it_lead"])
def test_detail_visible_to_allowed_roles(
    client, frozen, private_booking, make_user, make_pitika, auth_headers, viewer
):
    booking, booker, owner = private_booking()
    users = {
        "booker": lambda: booker,
        "admin": lambda: make_user(roles=["ADMIN"]),
        "owner": lambda: owner,
        "pitika": lambda: make_pitika(province="PHNOM_PENH"),
        "it_lead": lambda: make_user(roles=["IT_LEAD"]),
    }
    response = client.get(f"{URL}/{booking.id}", headers=auth_headers(users[viewer]()))
    assert response.status_code == 200
    data = response.json()
    assert (data["id"], data["meeting_title"]) == (booking.id, booking.meeting_title)
    assert data["status"] == "PENDING_OWNER"


@pytest.mark.parametrize("viewer", ["staff", "other_pitika", "it_lead_before_forward"])
def test_detail_404_for_others(
    client, frozen, private_booking, make_user, make_pitika, auth_headers, viewer
):
    booking, _booker, _owner = private_booking(forwarded=viewer != "it_lead_before_forward")
    users = {
        "staff": lambda: make_user(roles=["STAFF"]),
        "other_pitika": lambda: make_pitika(province="SIEM_REAP"),
        "it_lead_before_forward": lambda: make_user(roles=["IT_LEAD"]),
    }
    response = client.get(f"{URL}/{booking.id}", headers=auth_headers(users[viewer]()))
    assert error(response) == (404, "NOT_FOUND")


def test_detail_missing_404(client, frozen, as_admin):
    assert error(client.get(f"{URL}/999999", headers=as_admin)) == (404, "NOT_FOUND")


def test_detail_shape(client, frozen, make_user, make_bookable_room, make_booking, auth_headers):
    booker = make_user(roles=["STAFF"])
    room = make_bookable_room()
    booking = make_booking(
        room,
        booker,
        status=BookingStatus.PENDING_PITIKA,
        sessions=((NEXT_DAY, time(9), time(10)), (DAY, time(14), time(15))),
        catering=True,
        meeting_purpose="Plan",
    )
    data = client.get(f"{URL}/{booking.id}", headers=auth_headers(booker)).json()
    assert set(data) == {
        "id", "reference_code", "room", "meeting_title", "meeting_type", "route", "status",
        "display_status", "requester", "first_session", "session_count", "attendees",
        "has_catering", "has_it", "created_at", "version", "requester_info", "meeting_purpose",
        "private_justification", "participant_emails", "sessions", "last_end", "catering", "it",
        "reviews", "rejection", "cancelled_at", "cancel_reason", "updated_at",
    }  # fmt: skip
    location = room.floor.building.location
    assert data["room"] == {
        "id": room.id,
        "name_en": room.name_en,
        "name_kh": room.name_kh,
        "is_private": False,
        "location": {"id": location.id, "name_en": location.name_en, "name_kh": location.name_kh},
        "province": {"code": "PHNOM_PENH", "name_en": "Phnom Penh", "name_kh": "ភ្នំពេញ"},
    }
    assert data["first_session"]["date"] == DAY.isoformat()
    assert data["last_end"] == {"date": NEXT_DAY.isoformat(), "time": "10:00"}
    assert data["catering"]["delivery_time"] == "14:00"
    assert data["meeting_purpose"] == "Plan"


def test_mine_newest_first_and_q(
    client, frozen, make_user, make_bookable_room, make_booking, auth_headers
):
    booker = make_user(roles=["STAFF"])
    room = make_bookable_room()
    first = make_booking(room, booker, status=BookingStatus.PENDING_PITIKA, meeting_title="Budget")
    second = make_booking(
        room,
        booker,
        status=BookingStatus.CONFIRMED,
        sessions=((NEXT_DAY, time(9), time(10)),),
        meeting_title="Weekly sync",
    )
    make_booking(room, make_user(roles=["STAFF"]), status=BookingStatus.PENDING_PITIKA,
                 sessions=((DAY, time(11), time(12)),))  # fmt: skip
    headers = auth_headers(booker)

    response = client.get(f"{URL}/mine", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert [item["id"] for item in data["items"]] == [second.id, first.id]
    assert (data["page"], data["size"], data["total"]) == (1, 20, 2)

    data = client.get(f"{URL}/mine", params={"q": "budg"}, headers=headers).json()
    assert [item["id"] for item in data["items"]] == [first.id]

    data = client.get(f"{URL}/mine", params={"q": second.reference_code}, headers=headers).json()
    assert [item["id"] for item in data["items"]] == [second.id]


def test_mine_item_shape(client, frozen, make_user, make_bookable_room, make_booking, auth_headers):
    booker = make_user(roles=["STAFF"])
    booking = make_booking(make_bookable_room(), booker, status=BookingStatus.PENDING_PITIKA)
    item = client.get(f"{URL}/mine", headers=auth_headers(booker)).json()["items"][0]
    assert set(item) == {
        "id", "reference_code", "room", "meeting_title", "meeting_type", "route", "status",
        "display_status", "requester", "first_session", "session_count", "attendees",
        "has_catering", "has_it", "created_at", "version",
    }  # fmt: skip
    assert item["id"] == booking.id


def test_mine_status_completed(
    client, freeze_now, frozen, make_user, make_bookable_room, make_booking, auth_headers
):
    booker = make_user(roles=["STAFF"])
    room = make_bookable_room()
    ended = make_booking(room, booker, status=BookingStatus.CONFIRMED)  # DAY 09:00-10:00
    later = make_booking(
        room, booker, status=BookingStatus.CONFIRMED, sessions=((NEXT_DAY, time(9), time(10)),)
    )
    pending = make_booking(
        room, booker, status=BookingStatus.PENDING_PITIKA, sessions=((DAY, time(11), time(12)),)
    )
    freeze_now(datetime(2026, 11, 10, 10, 0))  # the last end of `ended`
    headers = auth_headers(booker)

    def ids(status):
        response = client.get(f"{URL}/mine", params={"status": status}, headers=headers)
        assert response.status_code == 200
        return [item["id"] for item in response.json()["items"]]

    assert ids("COMPLETED") == [ended.id]
    assert ids("CONFIRMED") == [later.id]
    assert ids("PENDING_PITIKA") == [pending.id]
    assert ids("CANCELLED") == []
    detail = client.get(f"{URL}/{ended.id}", headers=headers).json()
    assert (detail["status"], detail["display_status"]) == ("CONFIRMED", "COMPLETED")
    item = client.get(f"{URL}/mine", headers=headers).json()["items"]
    assert {i["id"]: i["display_status"] for i in item}[later.id] == "CONFIRMED"


def test_mine_unknown_status_422(client, frozen, as_staff):
    response = client.get(f"{URL}/mine", params={"status": "DONE"}, headers=as_staff)
    assert error(response) == (422, "VALIDATION_ERROR")
    assert list(fields(response)) == ["status"]


def test_mine_paging(client, frozen, make_user, make_bookable_room, make_booking, auth_headers):
    booker = make_user(roles=["STAFF"])
    room = make_bookable_room()
    for hour in (9, 11, 13):
        make_booking(room, booker, status=BookingStatus.PENDING_PITIKA,
                     sessions=((DAY, time(hour), time(hour + 1)),))  # fmt: skip
    data = client.get(f"{URL}/mine", params={"size": 2, "page": 2}, headers=auth_headers(booker))
    assert (len(data.json()["items"]), data.json()["total"]) == (1, 3)
