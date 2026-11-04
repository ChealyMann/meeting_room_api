"""GET /bookings/{id}/ics: spec 9.10, B-18."""

from datetime import time

import pytest

from app.constants.booking import BookingStatus
from tests.booking_helpers import DAY, URL, error


def get_ics(client, booking, headers):
    response = client.get(f"{URL}/{booking.id}/ics", headers=headers)
    assert response.status_code == 200
    return response


def unfolded(text: str) -> list[str]:
    """The content lines of an ics text, with folded lines joined."""
    lines: list[str] = []
    for line in text.split("\r\n"):
        if line.startswith(" ") and lines:
            lines[-1] += line[1:]
        else:
            lines.append(line)
    return lines


def test_ics_one_event_per_session(
    client, frozen, make_user, make_bookable_room, make_booking, auth_headers
):
    booker = make_user(roles=["STAFF"])
    room = make_bookable_room()
    booking = make_booking(
        room,
        booker,
        status=BookingStatus.CONFIRMED,
        sessions=((DAY, time(9), time(10)), (DAY, time(14), time(15, 30))),
    )
    response = get_ics(client, booking, auth_headers(booker))
    assert response.headers["content-type"] == "text/calendar; charset=utf-8"
    assert response.headers["content-disposition"] == (
        f'attachment; filename="{booking.reference_code}.ics"'
    )
    text = response.text
    assert text.count("BEGIN:VEVENT") == 2
    assert text.startswith("BEGIN:VCALENDAR\r\nVERSION:2.0\r\n")
    assert text.endswith("END:VCALENDAR\r\n")
    assert "PRODID:-//NBC//Room Booking//EN" in text
    assert "METHOD:PUBLISH" in text
    assert "DTSTART:20261110T020000Z" in text
    assert "DTEND:20261110T030000Z" in text
    assert "DTSTART:20261110T070000Z" in text
    assert "DTEND:20261110T083000Z" in text
    assert "DTSTAMP:20261109T010000Z" in text  # NOW is 08:00 local
    lines = unfolded(text)
    ids = sorted(s.id for s in booking.sessions)
    for session_id in ids:
        assert f"UID:booking-{booking.id}-session-{session_id}@nbc-room-booking" in lines
    assert f"SUMMARY:{booking.meeting_title}" in lines
    assert f"DESCRIPTION:Reference {booking.reference_code}" in lines
    assert "STATUS:CONFIRMED" in lines
    building = room.floor.building
    place = f"LOCATION:{room.name_en}\\, {building.name_en}\\, {building.location.name_en}"
    assert place in lines


def test_ics_has_no_door_pass(
    client, frozen, make_user, make_bookable_room, make_booking, auth_headers
):
    booker = make_user(roles=["STAFF"])
    booking = make_booking(make_bookable_room(), booker, status=BookingStatus.CONFIRMED)
    text = get_ics(client, booking, auth_headers(booker)).text
    assert booking.door_pass.passcode not in text


def test_ics_escapes_and_folds(
    client, frozen, make_user, make_bookable_room, make_booking, auth_headers
):
    booker = make_user(roles=["STAFF"])
    booking = make_booking(
        make_bookable_room(),
        booker,
        status=BookingStatus.CONFIRMED,
        meeting_title="a, b; c \\ d",
    )
    text = get_ics(client, booking, auth_headers(booker)).text
    assert "SUMMARY:a\\, b\\; c \\\\ d\r\n" in text

    long_title = "ការប្រជុំ" * 15 + " , long title"  # Khmer: 3 bytes per character
    booking = make_booking(
        make_bookable_room(), booker, status=BookingStatus.CONFIRMED, meeting_title=long_title
    )
    text = get_ics(client, booking, auth_headers(booker)).text
    raw_lines = text.encode("utf-8").split(b"\r\n")
    assert max(len(line) for line in raw_lines) <= 75
    for line in raw_lines:
        line.decode("utf-8")  # no multi-byte character is cut
    assert any(line.startswith(b" ") for line in raw_lines)
    assert f"SUMMARY:{long_title.replace(',', chr(92) + ',')}" in unfolded(text)
    assert text.count("\r\n") == text.count("\n")  # every line ends with CRLF


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (BookingStatus.PENDING_PITIKA, "TENTATIVE"),
        (BookingStatus.PENDING_OWNER, "TENTATIVE"),
        (BookingStatus.SETUP_IN_PROGRESS, "TENTATIVE"),
        (BookingStatus.CONFIRMED, "CONFIRMED"),
        (BookingStatus.REJECTED, "CANCELLED"),
        (BookingStatus.CANCELLED, "CANCELLED"),
    ],
)
def test_ics_status(
    client, frozen, make_user, make_bookable_room, make_booking, auth_headers, status, expected
):
    booker = make_user(roles=["STAFF"])
    booking = make_booking(make_bookable_room(), booker, status=status)
    text = get_ics(client, booking, auth_headers(booker)).text
    assert f"STATUS:{expected}\r\n" in text


def test_ics_visible_to_it_lead(
    client, frozen, make_user, make_bookable_room, make_booking, auth_headers
):
    booker = make_user(roles=["STAFF"])
    booking = make_booking(
        make_bookable_room(), booker, status=BookingStatus.CONFIRMED, it=True, forwarded=True
    )
    lead = make_user(roles=["IT_LEAD"])
    text = get_ics(client, booking, auth_headers(lead)).text
    assert booking.door_pass.passcode not in text


def test_ics_404_for_others(
    client, frozen, make_user, make_pitika, make_bookable_room, make_booking, auth_headers
):
    booking = make_booking(
        make_bookable_room(), make_user(roles=["STAFF"]), status=BookingStatus.CONFIRMED
    )
    for other in (make_user(roles=["STAFF"]), make_pitika(province="SIEM_REAP")):
        response = client.get(f"{URL}/{booking.id}/ics", headers=auth_headers(other))
        assert error(response) == (404, "NOT_FOUND")
    assert error(client.get(f"{URL}/999999/ics", headers=auth_headers(other))) == (
        404,
        "NOT_FOUND",
    )
