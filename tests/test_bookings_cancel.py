"""POST /bookings/{id}/cancel: spec 9.8 (T12), B-11."""

from datetime import date, datetime, time

import pytest
from sqlalchemy import select

from app.constants.booking import BookingStatus
from app.models import BookingSession
from tests.booking_helpers import DAY, URL, book, error

SECOND_DAY = date(2026, 11, 12)
TWO_DAYS = ((DAY, time(9), time(10)), (SECOND_DAY, time(9), time(10)))


@pytest.fixture
def booker(make_user):
    return make_user(roles=["STAFF"])


@pytest.fixture
def room(make_bookable_room):
    return make_bookable_room()


def cancel(client, headers, booking, **values):
    body = {"version": booking.version, **values}
    return client.post(f"{URL}/{booking.id}/cancel", json=body, headers=headers)


def blocking_flags(db_session, booking_id) -> list[bool]:
    rows = db_session.scalars(
        select(BookingSession.is_blocking).where(BookingSession.booking_id == booking_id)
    )
    return list(rows)


def test_cancel_pending(client, frozen, db_session, make_booking, room, booker, auth_headers):
    booking = make_booking(room, booker, status=BookingStatus.PENDING_PITIKA)
    response = cancel(client, auth_headers(booker), booking, reason="Plans changed")
    assert response.status_code == 200
    data = response.json()
    assert (data["status"], data["display_status"], data["version"]) == (
        "CANCELLED",
        "CANCELLED",
        2,
    )
    assert data["cancel_reason"] == "Plans changed"
    assert data["cancelled_at"].endswith("Z")
    assert len(data["sessions"]) == 1
    assert blocking_flags(db_session, booking.id) == [False]


def test_cancel_without_reason(client, frozen, make_booking, room, booker, auth_headers):
    booking = make_booking(room, booker, status=BookingStatus.CONFIRMED)
    response = cancel(client, auth_headers(booker), booking)
    assert response.status_code == 200
    assert response.json()["cancel_reason"] is None


def test_cancel_keeps_food_and_it(client, frozen, make_booking, room, booker, auth_headers):
    booking = make_booking(
        room, booker, status=BookingStatus.SETUP_IN_PROGRESS, catering=True, it=True
    )
    response = cancel(client, auth_headers(booker), booking)
    assert response.status_code == 200
    data = response.json()
    assert data["catering"] is not None
    assert data["it"] is not None


def test_cancel_confirmed_mid_series(
    client, freeze_now, db_session, make_booking, room, booker, auth_headers
):
    booking = make_booking(room, booker, status=BookingStatus.CONFIRMED, sessions=TWO_DAYS)
    freeze_now(datetime.combine(DAY, time(12, 0)))  # after the first session ended
    response = cancel(client, auth_headers(booker), booking)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "CANCELLED"
    assert len(data["sessions"]) == 2
    assert blocking_flags(db_session, booking.id) == [False, False]


def test_cancel_after_last_end(client, freeze_now, make_booking, room, booker, auth_headers):
    booking = make_booking(room, booker, status=BookingStatus.CONFIRMED)
    freeze_now(datetime.combine(DAY, time(10, 0)))
    response = cancel(client, auth_headers(booker), booking)
    assert error(response) == (409, "INVALID_TRANSITION")
    assert response.json()["error"]["message"] == "This booking has ended."


@pytest.mark.parametrize("status", [BookingStatus.CANCELLED, BookingStatus.REJECTED])
def test_cancel_final(client, frozen, make_booking, room, booker, auth_headers, status):
    booking = make_booking(room, booker, status=status)
    response = cancel(client, auth_headers(booker), booking)
    assert error(response) == (409, "INVALID_TRANSITION")


def test_cancel_twice(client, frozen, make_booking, room, booker, auth_headers):
    booking = make_booking(room, booker, status=BookingStatus.CONFIRMED)
    headers = auth_headers(booker)
    assert cancel(client, headers, booking).status_code == 200
    again = client.post(f"{URL}/{booking.id}/cancel", json={"version": 2}, headers=headers)
    assert error(again) == (409, "INVALID_TRANSITION")
    assert again.json()["error"]["message"] == "This booking was cancelled."


def test_stale_version(client, frozen, make_booking, room, booker, auth_headers):
    booking = make_booking(room, booker, status=BookingStatus.CONFIRMED)
    response = client.post(
        f"{URL}/{booking.id}/cancel", json={"version": 7}, headers=auth_headers(booker)
    )
    assert error(response) == (409, "STALE_VERSION")


def test_others_cannot_cancel(
    client, frozen, make_booking, make_user, make_pitika, make_bookable_room, booker, auth_headers
):
    pitika = make_pitika()
    owner = make_user(roles=["ROOM_OWNER"])
    private = make_bookable_room(private=True, owner=owner)
    booking = make_booking(private, booker, status=BookingStatus.PENDING_OWNER)
    admin = make_user(roles=["ADMIN"])
    for user in (pitika, owner, admin):
        response = cancel(client, auth_headers(user), booking)
        assert error(response) == (403, "FORBIDDEN")
        message = response.json()["error"]["message"]
        assert message == "Only the booker can cancel. Reject it instead."


def test_stranger_gets_404(client, frozen, make_booking, make_user, room, booker, auth_headers):
    booking = make_booking(room, booker, status=BookingStatus.CONFIRMED)
    other = make_user(roles=["STAFF"])
    assert cancel(client, auth_headers(other), booking).status_code == 404


@pytest.mark.parametrize("reason", ["abc", "    ab  ", "<b>Plans</b>", "x" * 501])
def test_bad_reason(client, frozen, make_booking, room, booker, auth_headers, reason):
    booking = make_booking(room, booker, status=BookingStatus.CONFIRMED)
    response = cancel(client, auth_headers(booker), booking, reason=reason)
    assert error(response) == (422, "VALIDATION_ERROR")


def test_cancel_reason_rules(client, frozen, make_booking, room, booker, auth_headers):
    booking = make_booking(room, booker, status=BookingStatus.CONFIRMED)
    response = cancel(client, auth_headers(booker), booking, reason=None)
    assert response.status_code == 200
    assert response.json()["cancel_reason"] is None


def test_cancelled_time_free_again(client, frozen, make_pitika, room, booker, auth_headers):
    make_pitika()
    headers = auth_headers(booker)
    first = book(client, headers, room.id).json()
    assert book(client, headers, room.id).status_code == 409
    response = client.post(
        f"{URL}/{first['id']}/cancel", json={"version": first["version"]}, headers=headers
    )
    assert response.status_code == 200
    assert book(client, headers, room.id).status_code == 201
