"""PATCH /bookings/{id}: spec 9.7 (T13), B-15, B-24, B-25."""

from datetime import datetime, time

import pytest
from sqlalchemy import select

from app.constants.booking import BookingStatus
from app.models import BookingParticipant
from tests.booking_helpers import DAY, URL, book, error, fields

CONFIRMED = BookingStatus.CONFIRMED


@pytest.fixture
def booker(make_user):
    return make_user(roles=["STAFF"])


@pytest.fixture
def room(make_bookable_room):
    return make_bookable_room()


@pytest.fixture
def booking(make_booking, room, booker):
    return make_booking(room, booker, status=CONFIRMED)


def patch(client, headers, booking, **values):
    body = {"version": booking.version, **values}
    return client.patch(f"{URL}/{booking.id}", json=body, headers=headers)


def test_small_edit_keeps_status(client, frozen, booking, booker, auth_headers):
    response = patch(
        client,
        auth_headers(booker),
        booking,
        meeting_title="New title",
        meeting_type="EXTERNAL",
        meeting_purpose="A new purpose",
        attendees=8,
    )
    assert response.status_code == 200
    data = response.json()
    assert (data["status"], data["version"]) == ("CONFIRMED", 2)
    assert (data["meeting_title"], data["meeting_type"]) == ("New title", "EXTERNAL")
    assert (data["meeting_purpose"], data["attendees"]) == ("A new purpose", 8)
    assert data["warnings"] == []


def test_purpose_can_be_cleared(client, frozen, make_booking, room, booker, auth_headers):
    booking = make_booking(room, booker, status=CONFIRMED, meeting_purpose="Old")
    response = patch(client, auth_headers(booker), booking, meeting_purpose=None)
    assert response.status_code == 200
    assert response.json()["meeting_purpose"] is None


def test_over_capacity_warning(client, frozen, booking, room, booker, auth_headers):
    response = patch(client, auth_headers(booker), booking, attendees=room.capacity + 1)
    assert response.status_code == 200
    assert response.json()["warnings"] == [
        {"code": "OVER_CAPACITY", "seats": room.capacity, "attendees": room.capacity + 1}
    ]


@pytest.mark.parametrize(
    "extra",
    [
        {"room_id": 2},
        {"room_id": None},
        {"sessions": []},
        {"private_justification": "x"},
        {"catering": {"package_ids": [1]}},
        {"it": {"service_ids": [1]}},
        {"catering": None},
        {"it": None},
    ],
)
def test_refused_fields(client, frozen, make_booking, room, booker, auth_headers, extra):
    booking = make_booking(room, booker, status=CONFIRMED, catering=True, it=True)
    response = patch(client, auth_headers(booker), booking, **extra)
    assert error(response) == (422, "FIELD_NOT_EDITABLE")
    assert response.json()["error"]["message"] == (
        "To change the room, date or time, cancel and book again."
    )


def test_refused_field_comes_before_stale_version(client, frozen, booking, booker, auth_headers):
    response = client.patch(
        f"{URL}/{booking.id}",
        json={"version": 99, "room_id": 2},
        headers=auth_headers(booker),
    )
    assert error(response) == (422, "FIELD_NOT_EDITABLE")


def test_catering_on_booking_without_food(client, frozen, booking, booker, auth_headers):
    response = patch(client, auth_headers(booker), booking, catering={"remarks": "More tea"})
    assert error(response) == (422, "FIELD_NOT_EDITABLE")


def test_it_on_booking_without_ticket(client, frozen, booking, booker, auth_headers):
    response = patch(client, auth_headers(booker), booking, it={"special_requirements": "Mics"})
    assert error(response) == (422, "FIELD_NOT_EDITABLE")


def test_catering_remarks_and_it_requirements(
    client, frozen, make_booking, room, booker, auth_headers
):
    booking = make_booking(room, booker, status=CONFIRMED, catering=True, it=True)
    response = patch(
        client,
        auth_headers(booker),
        booking,
        attendees=7,
        catering={"remarks": "No pork"},
        it={"special_requirements": "Two microphones"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["catering"]["remarks"] == "No pork"
    assert data["catering"]["servings"] == 7  # B-25
    assert data["it"]["special_requirements"] == "Two microphones"
    assert data["version"] == 2


def test_only_booker_edits(client, frozen, booking, make_user, auth_headers):
    admin = make_user(roles=["ADMIN"])
    response = patch(client, auth_headers(admin), booking, meeting_title="Hacked")
    assert error(response) == (403, "FORBIDDEN")


def test_stranger_gets_404(client, frozen, booking, make_user, auth_headers):
    other = make_user(roles=["STAFF"])
    response = patch(client, auth_headers(other), booking, meeting_title="Hacked")
    assert response.status_code == 404


def test_stale_version(client, frozen, booking, booker, auth_headers):
    response = client.patch(
        f"{URL}/{booking.id}",
        json={"version": booking.version + 1, "meeting_title": "Title"},
        headers=auth_headers(booker),
    )
    assert error(response) == (409, "STALE_VERSION")


def test_edit_after_start(client, freeze_now, booking, booker, auth_headers):
    freeze_now(datetime.combine(DAY, time(9, 0)))
    response = patch(client, auth_headers(booker), booking, meeting_title="Late")
    assert error(response) == (409, "TIME_PASSED")
    assert response.json()["error"]["message"] == "The meeting has started. It cannot be changed."


@pytest.mark.parametrize("status", [BookingStatus.CANCELLED, BookingStatus.REJECTED])
def test_edit_final(client, frozen, make_booking, room, booker, auth_headers, status):
    booking = make_booking(room, booker, status=status)
    response = patch(client, auth_headers(booker), booking, meeting_title="Again")
    assert error(response) == (409, "INVALID_TRANSITION")


def test_edit_completed(client, freeze_now, booking, booker, auth_headers):
    freeze_now(datetime.combine(DAY, time(11, 0)))
    response = patch(client, auth_headers(booker), booking, meeting_title="Again")
    assert error(response) == (409, "INVALID_TRANSITION")


def test_only_version_changes_nothing(client, frozen, booking, booker, auth_headers):
    response = patch(client, auth_headers(booker), booking)
    assert response.status_code == 200
    data = response.json()
    assert data["version"] == 1
    assert data["meeting_title"] == booking.meeting_title


def test_empty_nested_body_changes_nothing(
    client, frozen, make_booking, room, booker, auth_headers
):
    booking = make_booking(room, booker, status=CONFIRMED, catering=True)
    response = patch(client, auth_headers(booker), booking, catering={})
    assert response.status_code == 200
    assert response.json()["version"] == 1


def test_only_version_still_checks_version(client, frozen, booking, booker, auth_headers):
    headers = auth_headers(booker)
    response = client.patch(f"{URL}/{booking.id}", json={"version": 5}, headers=headers)
    assert error(response) == (409, "STALE_VERSION")


def test_attendees_rechecked(client, frozen, make_pitika, room, booker, auth_headers):
    make_pitika()
    headers = auth_headers(booker)
    created = book(
        client, headers, room.id, attendees=3, participant_emails=["a@company.com"]
    ).json()
    response = client.patch(
        f"{URL}/{created['id']}", json={"version": 1, "attendees": 1}, headers=headers
    )
    assert error(response) == (422, "VALIDATION_ERROR")
    assert "attendees" in fields(response)


def test_attendees_limits(client, frozen, booking, booker, auth_headers, settings):
    headers = auth_headers(booker)
    too_many = patch(client, headers, booking, attendees=settings.booking_max_attendees + 1)
    assert error(too_many) == (422, "VALIDATION_ERROR")
    assert "attendees" in fields(too_many)
    zero = patch(client, headers, booking, attendees=0)
    assert error(zero) == (422, "VALIDATION_ERROR")


def test_new_emails_checked_against_old_attendees(
    client, frozen, make_booking, room, booker, auth_headers
):
    booking = make_booking(room, booker, status=CONFIRMED, attendees=2)
    emails = ["a@company.com", "b@company.com"]
    response = patch(client, auth_headers(booker), booking, participant_emails=emails)
    assert error(response) == (422, "VALIDATION_ERROR")
    assert "attendees" in fields(response)


def test_too_many_emails(client, frozen, booking, booker, auth_headers, settings):
    emails = [f"p{i}@company.com" for i in range(settings.booking_max_participants + 1)]
    response = patch(
        client,
        auth_headers(booker),
        booking,
        attendees=settings.booking_max_attendees,
        participant_emails=emails,
    )
    assert error(response) == (422, "VALIDATION_ERROR")
    assert "participant_emails" in fields(response)


def test_participants_replaced(client, frozen, db_session, make_pitika, room, booker, auth_headers):
    make_pitika()
    headers = auth_headers(booker)
    created = book(
        client, headers, room.id, participant_emails=["a@company.com", "b@company.com"]
    ).json()
    assert sorted(created["participant_emails"]) == ["a@company.com", "b@company.com"]
    response = client.patch(
        f"{URL}/{created['id']}",
        json={
            "version": 1,
            "participant_emails": ["b@company.com", "c@company.com", "c@company.com", booker.email],
        },
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert sorted(data["participant_emails"]) == ["b@company.com", "c@company.com"]
    assert data["version"] == 2
    saved = db_session.scalars(
        select(BookingParticipant.email).where(BookingParticipant.booking_id == created["id"])
    )
    assert set(saved) == {"b@company.com", "c@company.com"}


def test_participants_cleared_by_empty_list(
    client, frozen, make_pitika, room, booker, auth_headers
):
    make_pitika()
    headers = auth_headers(booker)
    created = book(client, headers, room.id, participant_emails=["a@company.com"]).json()
    response = client.patch(
        f"{URL}/{created['id']}",
        json={"version": 1, "participant_emails": []},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["participant_emails"] == []


def test_html_refused(client, frozen, booking, booker, auth_headers):
    response = patch(client, auth_headers(booker), booking, meeting_title="<b>Hi there</b>")
    assert error(response) == (422, "VALIDATION_ERROR")


def test_null_title_refused(client, frozen, booking, booker, auth_headers):
    response = patch(client, auth_headers(booker), booking, meeting_title=None)
    assert error(response) == (422, "VALIDATION_ERROR")
