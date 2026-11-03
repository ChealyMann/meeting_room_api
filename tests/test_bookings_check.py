"""POST /bookings/check: spec 9.3. The route, the steps and the first problem; saves nothing."""

from datetime import time

from sqlalchemy import func, select

from app.constants.booking import BookingStatus
from app.models import Booking
from tests.booking_helpers import DAY, error, fields

URL = "/api/v1/bookings/check"


def payload(room_id, start="09:00", end="10:00", **extra):
    session = {"date": DAY.isoformat(), "start_time": start, "end_time": end}
    return {"room_id": room_id, "sessions": [session], **extra}


def test_check_r1_steps(client, frozen, make_user, make_pitika, make_bookable_room, auth_headers):
    make_pitika()
    room = make_bookable_room()
    booker = make_user(roles=["STAFF"])
    response = client.post(URL, json=payload(room.id), headers=auth_headers(booker))
    assert response.status_code == 200
    assert response.json() == {
        "route": "R1",
        "first_status": "PENDING_PITIKA",
        "steps": ["PITIKA", "CONFIRMED"],
        "problem": None,
        "warnings": [],
    }


def test_check_r2_with_it(client, frozen, make_user, make_pitika, make_bookable_room, auth_headers):
    make_pitika()
    room = make_bookable_room(private=True)
    booker = make_user(roles=["STAFF"])
    body = payload(room.id, has_it=True)
    response = client.post(URL, json=body, headers=auth_headers(booker))
    assert response.status_code == 200
    data = response.json()
    assert data["route"] == "R2"
    assert data["first_status"] == "PENDING_PITIKA"
    assert data["steps"] == ["PITIKA", "OWNER", "IT_SETUP", "CONFIRMED"]
    assert data["problem"] is None


def test_check_r3(client, frozen, make_user, make_bookable_room, auth_headers):
    owner = make_user(roles=["ROOM_OWNER"])
    room = make_bookable_room(private=True, owner=owner)
    response = client.post(URL, json=payload(room.id), headers=auth_headers(owner))
    data = response.json()
    assert response.status_code == 200
    assert (data["route"], data["first_status"]) == ("R3", "CONFIRMED")
    assert data["steps"] == ["CONFIRMED"]
    assert data["problem"] is None


def test_check_clash_is_problem_not_error(
    client, frozen, make_user, make_pitika, make_bookable_room, make_booking, auth_headers
):
    make_pitika()
    room = make_bookable_room()
    make_booking(room, make_user(roles=["STAFF"]), status=BookingStatus.CONFIRMED)
    booker = make_user(roles=["STAFF"])
    response = client.post(
        URL, json=payload(room.id, "09:30", "10:30"), headers=auth_headers(booker)
    )
    assert response.status_code == 200
    data = response.json()
    assert data["problem"]["code"] == "SCHEDULE_CONFLICT"
    assert list(data["problem"]["fields"]) == ["sessions.0"]
    assert data["problem"]["message"] == data["problem"]["fields"]["sessions.0"]
    assert (data["route"], data["steps"]) == ("R1", ["PITIKA", "CONFIRMED"])


def test_check_unknown_room(client, frozen, make_user, auth_headers):
    booker = make_user(roles=["STAFF"])
    response = client.post(URL, json=payload(999999), headers=auth_headers(booker))
    assert response.status_code == 200
    data = response.json()
    assert (data["route"], data["first_status"], data["steps"]) == (None, None, None)
    assert data["problem"]["fields"] == {"room_id": "Room not found."}
    assert data["warnings"] == []


def test_check_room_not_bookable(client, frozen, make_user, make_bookable_room, auth_headers):
    room = make_bookable_room(is_active=False)
    booker = make_user(roles=["STAFF"])
    response = client.post(URL, json=payload(room.id), headers=auth_headers(booker))
    data = response.json()
    assert response.status_code == 200
    assert data["problem"]["code"] == "ROOM_NOT_BOOKABLE"
    assert (data["route"], data["first_status"], data["steps"]) == (None, None, None)


def test_check_no_reviewer_keeps_route(
    client, frozen, make_user, make_pitika, make_bookable_room, auth_headers
):
    make_pitika(province="SIEM_REAP")
    room = make_bookable_room(province="PHNOM_PENH")
    booker = make_user(roles=["STAFF"])
    data = client.post(URL, json=payload(room.id), headers=auth_headers(booker)).json()
    assert data["problem"]["code"] == "NO_REVIEWER"
    assert data["route"] == "R1"


def test_check_outside_hours_is_problem(
    client, frozen, make_user, make_bookable_room, auth_headers
):
    room = make_bookable_room(start_time=time(9), end_time=time(17))
    booker = make_user(roles=["STAFF"])
    response = client.post(
        URL, json=payload(room.id, "08:00", "09:30"), headers=auth_headers(booker)
    )
    data = response.json()
    assert response.status_code == 200
    assert data["problem"]["code"] == "OUTSIDE_ROOM_HOURS"
    assert list(data["problem"]["fields"]) == ["sessions.0.start_time"]


def test_check_session_rule_is_problem(client, frozen, make_user, make_bookable_room, auth_headers):
    room = make_bookable_room()
    booker = make_user(roles=["STAFF"])
    response = client.post(
        URL, json=payload(room.id, "10:00", "09:00"), headers=auth_headers(booker)
    )
    data = response.json()
    assert response.status_code == 200
    assert data["problem"]["code"] == "VALIDATION_ERROR"
    assert list(data["problem"]["fields"]) == ["sessions.0.end_time"]
    assert data["route"] is None


def test_check_bad_time_is_422(client, frozen, make_user, make_bookable_room, auth_headers):
    room = make_bookable_room()
    booker = make_user(roles=["STAFF"])
    response = client.post(
        URL, json=payload(room.id, "25:00", "26:00"), headers=auth_headers(booker)
    )
    assert error(response) == (422, "VALIDATION_ERROR")
    assert "sessions.0.start_time" in fields(response)


def test_check_unknown_field_is_422(client, frozen, make_user, make_bookable_room, auth_headers):
    room = make_bookable_room()
    booker = make_user(roles=["STAFF"])
    response = client.post(
        URL, json=payload(room.id, meeting_title="x"), headers=auth_headers(booker)
    )
    assert error(response) == (422, "VALIDATION_ERROR")


def test_check_needs_sign_in(client, frozen, make_bookable_room):
    room = make_bookable_room()
    assert client.post(URL, json=payload(room.id)).status_code == 401


def test_check_holiday_warning(
    client, frozen, make_user, make_pitika, make_bookable_room, make_holiday, auth_headers
):
    make_pitika()
    room = make_bookable_room()
    make_holiday(DAY, name_en="Test Day")
    booker = make_user(roles=["STAFF"])
    data = client.post(URL, json=payload(room.id), headers=auth_headers(booker)).json()
    assert data["problem"] is None
    assert data["warnings"] == [
        {"code": "PUBLIC_HOLIDAY", "date": "2026-11-10", "name": "Test Day"}
    ]


def test_check_saves_nothing(
    client, frozen, db_session, make_user, make_pitika, make_bookable_room, auth_headers
):
    make_pitika()
    room = make_bookable_room()
    booker = make_user(roles=["STAFF"])
    for has_it in (False, True):
        body = payload(room.id, has_it=has_it)
        assert client.post(URL, json=body, headers=auth_headers(booker)).status_code == 200
    assert db_session.scalar(select(func.count()).select_from(Booking)) == 0
