"""POST /bookings: spec 9.4 (T1, T2)."""

import re
from datetime import datetime, time, timedelta

import pytest
from sqlalchemy import func, select

from app.constants.booking import BookingStatus
from app.models import Booking, BookingDoorPass, BookingReview, BookingSession
from tests.booking_helpers import DAY, URL, book, error, fields

NEXT_DAY = DAY + timedelta(days=1)


def one_session(day, start="09:00", end="10:00") -> dict:
    return {"date": day.isoformat(), "start_time": start, "end_time": end}


@pytest.fixture
def booker(make_user):
    return make_user(roles=["STAFF"])


@pytest.fixture
def room(make_pitika, make_bookable_room):
    """A shared room in Phnom Penh, with a Pitika there to review."""
    make_pitika()
    return make_bookable_room()


def test_r1_created_pending(client, frozen, room, booker, auth_headers):
    response = book(client, auth_headers(booker), room.id)
    assert response.status_code == 201
    data = response.json()
    assert (data["status"], data["display_status"]) == ("PENDING_PITIKA", "PENDING_PITIKA")
    assert (data["route"], data["version"]) == ("R1", 1)
    assert re.fullmatch(r"NBC-26-\d{5}", data["reference_code"])
    assert data["requester"] == {
        "id": booker.id,
        "name_en": booker.name_en,
        "name_kh": booker.name_kh,
    }
    assert data["room"]["id"] == room.id
    assert data["first_session"]["date"] == DAY.isoformat()
    assert (data["first_session"]["start_time"], data["first_session"]["end_time"]) == (
        "09:00",
        "10:00",
    )
    assert data["last_end"] == {"date": DAY.isoformat(), "time": "10:00"}
    assert (data["session_count"], data["attendees"]) == (1, 5)
    assert (data["has_catering"], data["has_it"]) == (False, False)
    assert (data["catering"], data["it"], data["rejection"]) == (None, None, None)
    assert data["reviews"] == []
    assert data["warnings"] == []
    assert data["created_at"].endswith("Z")


def test_r3_confirmed_with_door_pass(
    client, frozen, db_session, make_user, make_bookable_room, auth_headers
):
    # No Pitika anywhere: R3 needs no reviewer.
    owner = make_user(roles=["ROOM_OWNER"])
    room = make_bookable_room(private=True, owner=owner)
    response = book(client, auth_headers(owner), room.id)
    assert response.status_code == 201
    data = response.json()
    assert (data["route"], data["status"], data["version"]) == ("R3", "CONFIRMED", 1)
    reviews = db_session.scalars(
        select(BookingReview).where(BookingReview.booking_id == data["id"])
    ).all()
    assert [(r.stage, r.decision, r.reviewer_id) for r in reviews] == [
        ("PITIKA", "NOT_REQUIRED", None)
    ]
    assert data["reviews"][0]["reviewer"] is None
    door_pass = db_session.scalar(
        select(BookingDoorPass).where(BookingDoorPass.booking_id == data["id"])
    )
    assert door_pass is not None
    assert re.fullmatch(r"NBC-\d{5}", door_pass.passcode)
    # Last end DAY 10:00 local = 03:00 UTC.
    assert door_pass.expires_at == datetime(2026, 11, 10, 3, 0)


def test_r4_own_private_room_with_food(
    client, frozen, make_user, make_pitika, make_bookable_room, make_catering_package, auth_headers
):
    make_pitika()
    owner = make_user(roles=["ROOM_OWNER"])
    room = make_bookable_room(private=True, owner=owner)
    package = make_catering_package()
    response = book(client, auth_headers(owner), room.id, catering={"package_ids": [package.id]})
    assert response.status_code == 201
    assert (response.json()["route"], response.json()["status"]) == ("R4", "PENDING_PITIKA")


def test_requester_info_copied(
    client,
    frozen,
    db_session,
    room,
    make_user,
    make_division,
    make_department,
    make_location,
    make_position,
    auth_headers,
):
    office = make_location(name_en="Head Office")
    division = make_division(make_department(office, name_en="Finance"), name_en="Budget")
    position = make_position(name_en="Officer")
    booker = make_user(roles=["STAFF"], division=division, position=position, phone="012 345 678")
    data = book(client, auth_headers(booker), room.id).json()
    expected = {
        "name_en": booker.name_en,
        "name_kh": booker.name_kh,
        "staff_id": booker.staff_id,
        "position": "Officer",
        "division": "Budget",
        "department": "Finance",
        "office": "Head Office",
        "email": booker.email,
        "phone": "012 345 678",
    }
    assert data["requester_info"] == expected

    booker.name_en = "New Name"
    booker.phone = None
    db_session.flush()
    detail = client.get(f"{URL}/{data['id']}", headers=auth_headers(booker)).json()
    assert detail["requester_info"] == expected
    assert detail["requester"]["name_en"] == "New Name"


def test_requester_info_without_division(client, frozen, room, booker, auth_headers):
    info = book(client, auth_headers(booker), room.id).json()["requester_info"]
    assert (info["division"], info["department"], info["office"], info["phone"]) == (
        None,
        None,
        None,
        None,
    )


def test_sessions_out_of_order(client, frozen, room, booker, auth_headers):
    sessions = [one_session(NEXT_DAY), one_session(DAY, "14:00", "15:00")]
    response = book(client, auth_headers(booker), room.id, sessions=sessions)
    assert response.status_code == 201
    data = response.json()
    assert data["first_session"]["date"] == DAY.isoformat()
    assert [(s["date"], s["start_time"]) for s in data["sessions"]] == [
        (DAY.isoformat(), "14:00"),
        (NEXT_DAY.isoformat(), "09:00"),
    ]
    assert data["session_count"] == 2
    assert data["last_end"] == {"date": NEXT_DAY.isoformat(), "time": "10:00"}


def test_sessions_block_the_room(client, frozen, db_session, room, booker, auth_headers):
    data = book(client, auth_headers(booker), room.id).json()
    rows = db_session.scalars(
        select(BookingSession).where(BookingSession.booking_id == data["id"])
    ).all()
    assert [(r.room_id, r.is_blocking) for r in rows] == [(room.id, True)]


@pytest.mark.parametrize("attendees", [0, 101])
def test_attendees_out_of_range(client, frozen, room, booker, auth_headers, attendees):
    response = book(client, auth_headers(booker), room.id, attendees=attendees)
    assert error(response) == (422, "VALIDATION_ERROR")
    assert fields(response) == {"attendees": "Must be 1 to 100."}


def test_attendees_rules(client, frozen, room, booker, auth_headers):
    emails = ["a@company.com", "b@company.com"]
    response = book(client, auth_headers(booker), room.id, attendees=2, participant_emails=emails)
    assert error(response) == (422, "VALIDATION_ERROR")
    assert fields(response) == {
        "attendees": "Attendees must be at least the participants plus you."
    }

    response = book(client, auth_headers(booker), room.id, attendees=3, participant_emails=emails)
    assert response.status_code == 201
    assert response.json()["participant_emails"] == emails


def test_own_email_removed(client, frozen, room, booker, auth_headers):
    response = book(
        client, auth_headers(booker), room.id, attendees=1, participant_emails=[booker.email]
    )
    assert response.status_code == 201
    assert response.json()["participant_emails"] == []


def test_repeated_emails_dropped(client, frozen, room, booker, auth_headers):
    emails = ["a@company.com", " A@Company.com ", booker.email.upper()]
    response = book(client, auth_headers(booker), room.id, attendees=2, participant_emails=emails)
    assert response.status_code == 201
    assert response.json()["participant_emails"] == ["a@company.com"]


def test_bad_email_422(client, frozen, room, booker, auth_headers):
    response = book(client, auth_headers(booker), room.id, participant_emails=["not-an-email"])
    assert error(response) == (422, "VALIDATION_ERROR")
    assert list(fields(response)) == ["participant_emails.0"]


def test_51_participants(client, frozen, room, booker, auth_headers):
    emails = [f"p{n}@company.com" for n in range(51)]
    response = book(client, auth_headers(booker), room.id, attendees=100, participant_emails=emails)
    assert error(response) == (422, "VALIDATION_ERROR")
    assert fields(response) == {"participant_emails": "At most 50 emails."}


def test_r2_needs_justification(
    client, frozen, make_pitika, make_bookable_room, booker, auth_headers
):
    make_pitika()
    room = make_bookable_room(private=True)
    response = book(client, auth_headers(booker), room.id)
    assert error(response) == (422, "VALIDATION_ERROR")
    assert fields(response) == {"private_justification": "Explain why you need this private room."}

    response = book(
        client, auth_headers(booker), room.id, private_justification="Board meeting needs privacy."
    )
    assert response.status_code == 201
    data = response.json()
    assert (data["route"], data["status"]) == ("R2", "PENDING_PITIKA")
    assert data["private_justification"] == "Board meeting needs privacy."


def test_inactive_package(
    client, frozen, room, booker, make_catering_package, make_it_service, auth_headers
):
    package = make_catering_package(is_active=False)
    response = book(client, auth_headers(booker), room.id, catering={"package_ids": [package.id]})
    assert error(response) == (409, "INACTIVE_REFERENCE")
    assert fields(response) == {"catering.package_ids": "This package is inactive."}

    response = book(client, auth_headers(booker), room.id, catering={"package_ids": [999999]})
    assert error(response) == (422, "VALIDATION_ERROR")
    assert fields(response) == {"catering.package_ids": "Package not found."}

    service = make_it_service(is_active=False)
    response = book(client, auth_headers(booker), room.id, it={"service_ids": [service.id]})
    assert error(response) == (409, "INACTIVE_REFERENCE")
    assert fields(response) == {"it.service_ids": "This IT service is inactive."}

    response = book(client, auth_headers(booker), room.id, it={"service_ids": [999999]})
    assert error(response) == (422, "VALIDATION_ERROR")
    assert fields(response) == {"it.service_ids": "IT service not found."}


def test_empty_package_list_422(client, frozen, room, booker, auth_headers):
    response = book(client, auth_headers(booker), room.id, catering={"package_ids": []})
    assert error(response) == (422, "VALIDATION_ERROR")
    assert list(fields(response)) == ["catering.package_ids"]


def test_food_and_it_copied(
    client,
    frozen,
    db_session,
    room,
    booker,
    make_catering_package,
    make_it_service,
    auth_headers,
):
    package = make_catering_package(name="Coffee break")
    service = make_it_service(name="Projector")
    response = book(
        client,
        auth_headers(booker),
        room.id,
        catering={"package_ids": [package.id, package.id], "remarks": " 2 vegetarian "},
        it={"service_ids": [service.id], "special_requirements": "Mac HDMI adapter"},
    )
    assert response.status_code == 201
    data = response.json()
    assert (data["has_catering"], data["has_it"]) == (True, True)
    catering = data["catering"]
    assert catering["packages"] == [{"id": package.id, "name": "Coffee break"}]
    assert catering["remarks"] == "2 vegetarian"
    assert (catering["servings"], catering["delivery_date"], catering["delivery_time"]) == (
        5,
        DAY.isoformat(),
        "09:00",
    )
    assert (catering["decided_by"], catering["decided_at"], catering["approver_notes"]) == (
        None,
        None,
        None,
    )
    it = data["it"]
    assert it["items"] == [{"id": service.id, "name": "Projector"}]
    assert it["special_requirements"] == "Mac HDMI adapter"
    assert (it["status"], it["forwarded_at"], it["staff"]) == ("RECEIVED", None, [])
    # Set up 30 minutes before the first session (BR-IT-05).
    assert (it["setup_date"], it["setup_time"]) == (DAY.isoformat(), "08:30")

    # The names are copies: renaming the catalog row does not change the booking.
    package.name = "Renamed"
    db_session.flush()
    detail = client.get(f"{URL}/{data['id']}", headers=auth_headers(booker)).json()
    assert detail["catering"]["packages"] == [{"id": package.id, "name": "Coffee break"}]


def test_one_bad_session_saves_nothing(
    client, frozen, db_session, room, booker, make_user, make_booking, auth_headers
):
    make_booking(
        room,
        make_user(roles=["STAFF"]),
        status=BookingStatus.CONFIRMED,
        sessions=((NEXT_DAY, time(9), time(10)),),
    )
    sessions = [one_session(DAY), one_session(NEXT_DAY, "09:30", "10:30")]
    response = book(client, auth_headers(booker), room.id, sessions=sessions)
    assert error(response) == (409, "SCHEDULE_CONFLICT")
    assert list(fields(response)) == ["sessions.1"]
    count = select(func.count()).select_from(Booking).where(Booking.requester_id == booker.id)
    assert db_session.scalar(count) == 0


@pytest.mark.parametrize(
    ("status", "start", "end", "expected"),
    [
        (BookingStatus.PENDING_PITIKA, "09:30", "10:30", 409),
        (BookingStatus.SETUP_IN_PROGRESS, "08:30", "09:30", 409),
        (BookingStatus.CONFIRMED, "10:00", "11:00", 201),  # back to back
        (BookingStatus.CONFIRMED, "08:00", "09:00", 201),  # back to back
        (BookingStatus.REJECTED, "09:00", "10:00", 201),
        (BookingStatus.CANCELLED, "09:00", "10:00", 201),
    ],
)
def test_clash_rules(
    client,
    frozen,
    room,
    booker,
    make_user,
    make_booking,
    auth_headers,
    status,
    start,
    end,
    expected,
):
    make_booking(room, make_user(roles=["STAFF"]), status=status)
    sessions = [one_session(DAY, start, end)]
    response = book(client, auth_headers(booker), room.id, sessions=sessions)
    assert response.status_code == expected


def test_over_capacity_and_holiday_warnings(
    client, frozen, room, booker, make_holiday, auth_headers
):
    make_holiday(DAY, name_en="Independence Day")
    response = book(client, auth_headers(booker), room.id, attendees=12)
    assert response.status_code == 201
    assert response.json()["warnings"] == [
        {"code": "PUBLIC_HOLIDAY", "date": DAY.isoformat(), "name": "Independence Day"},
        {"code": "OVER_CAPACITY", "seats": 10, "attendees": 12},
    ]


@pytest.mark.parametrize("title", ["ab", "  ab  ", "<b>Team</b>"])
def test_title_3_letters(client, frozen, room, booker, auth_headers, title):
    response = book(client, auth_headers(booker), room.id, meeting_title=title)
    assert error(response) == (422, "VALIDATION_ERROR")
    assert list(fields(response)) == ["meeting_title"]


def test_title_trimmed(client, frozen, room, booker, auth_headers):
    response = book(client, auth_headers(booker), room.id, meeting_title="  abc  ")
    assert response.status_code == 201
    assert response.json()["meeting_title"] == "abc"


def test_unknown_room(client, frozen, booker, auth_headers):
    response = book(client, auth_headers(booker), 999999)
    assert error(response) == (422, "VALIDATION_ERROR")
    assert fields(response) == {"room_id": "Room not found."}


def test_no_reviewer(client, frozen, make_pitika, make_bookable_room, booker, auth_headers):
    make_pitika(province="SIEM_REAP")
    room = make_bookable_room(province="PHNOM_PENH")
    assert error(book(client, auth_headers(booker), room.id)) == (409, "NO_REVIEWER")


def test_past_session(client, freeze_now, room, booker, auth_headers):
    freeze_now(datetime(2026, 11, 10, 9, 1))
    assert error(book(client, auth_headers(booker), room.id)) == (409, "TIME_PASSED")


def test_session_shapes_checked_first(client, frozen, booker, auth_headers):
    # Shapes are checked before the room is looked up.
    response = book(client, auth_headers(booker), 999999, sessions=[])
    assert error(response) == (422, "VALIDATION_ERROR")
    assert fields(response) == {"sessions": "Add 1 to 20 sessions."}


def test_unknown_field_refused(client, frozen, room, booker, auth_headers):
    response = book(client, auth_headers(booker), room.id, status="CONFIRMED")
    assert error(response) == (422, "VALIDATION_ERROR")
    assert fields(response) == {"status": "Unknown field."}


def test_same_person_two_rooms_same_time(
    client, frozen, room, booker, make_bookable_room, auth_headers
):
    other = make_bookable_room()
    assert book(client, auth_headers(booker), room.id).status_code == 201
    assert book(client, auth_headers(booker), other.id).status_code == 201


def test_create_reads_clashes_with_a_lock(client, frozen, room, booker, auth_headers, monkeypatch):
    """BR-SCH-08: after the room lock, the clash check must be a locking read, or it reads
    the transaction's old snapshot and two requests can book one slot. /check does not lock."""
    from app.services import booking_scheduling

    calls = []
    original = booking_scheduling.check_clashes

    def spy(*args, **kwargs):
        calls.append(kwargs.get("locking", False))
        return original(*args, **kwargs)

    monkeypatch.setattr(booking_scheduling, "check_clashes", spy)
    assert book(client, auth_headers(booker), room.id).status_code == 201
    check = {"room_id": room.id, "sessions": [one_session(NEXT_DAY)]}
    assert client.post(f"{URL}/check", json=check, headers=auth_headers(booker)).status_code == 200
    assert calls == [True, False]


def test_reference_code_taken_meanwhile_is_drawn_again(
    client, frozen, room, booker, make_user, make_booking, auth_headers, monkeypatch
):
    """The unique key is the last guard (spec 8.3): a code taken between the draw and the
    insert gets a new draw."""
    from app.services import booking_codes

    taken = make_booking(
        room,
        make_user(roles=["STAFF"]),
        status=BookingStatus.PENDING_PITIKA,
        sessions=((NEXT_DAY, time(9), time(10)),),
    ).reference_code
    draws = iter([taken, "NBC-26-11111"])
    monkeypatch.setattr(booking_codes, "new_reference_code", lambda *_args: next(draws))
    response = book(client, auth_headers(booker), room.id)
    assert response.status_code == 201
    assert response.json()["reference_code"] == "NBC-26-11111"


def test_sign_in_required(client, frozen, room):
    assert error(client.post(URL, json={})) == (401, "UNAUTHORIZED")
