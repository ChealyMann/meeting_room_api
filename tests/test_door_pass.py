"""GET /bookings/{id}/door-pass: spec 9.9, BR-DP-03, B-08."""

from datetime import datetime, time

import pytest

from app.constants.booking import BookingStatus
from tests.booking_helpers import DAY, URL, error


@pytest.fixture
def confirmed(make_user, make_bookable_room, make_booking):
    """A CONFIRMED booking (DAY 09:00-10:00 local) in a private room, with its people."""
    owner = make_user(roles=["ROOM_OWNER"])
    room = make_bookable_room(private=True, owner=owner)
    booker = make_user(roles=["STAFF"])
    booking = make_booking(room, booker, status=BookingStatus.CONFIRMED)
    return booking, booker, owner


def test_no_door_pass_before_confirm(
    client, frozen, make_user, make_bookable_room, make_booking, auth_headers
):
    booker = make_user(roles=["STAFF"])
    booking = make_booking(
        make_bookable_room(), booker, status=BookingStatus.PENDING_PITIKA, it=True
    )
    response = client.get(f"{URL}/{booking.id}/door-pass", headers=auth_headers(booker))
    assert error(response) == (404, "NOT_FOUND")
    assert response.json()["error"]["message"] == "No door pass yet."


@pytest.mark.parametrize("viewer", ["booker", "owner", "pitika", "admin"])
def test_door_pass_viewers(client, frozen, confirmed, make_user, make_pitika, auth_headers, viewer):
    booking, booker, owner = confirmed
    users = {
        "booker": lambda: booker,
        "owner": lambda: owner,
        "pitika": lambda: make_pitika(province="PHNOM_PENH"),
        "admin": lambda: make_user(roles=["ADMIN"]),
    }
    response = client.get(f"{URL}/{booking.id}/door-pass", headers=auth_headers(users[viewer]()))
    assert response.status_code == 200
    data = response.json()
    assert set(data) == {"passcode", "expires_at", "expired"}
    assert data["passcode"] == booking.door_pass.passcode
    assert data["expired"] is False


def test_door_pass_it_lead_403(
    client, frozen, make_user, make_bookable_room, make_booking, auth_headers
):
    booker = make_user(roles=["STAFF"])
    booking = make_booking(
        make_bookable_room(), booker, status=BookingStatus.CONFIRMED, it=True, forwarded=True
    )
    lead = make_user(roles=["IT_LEAD"])
    response = client.get(f"{URL}/{booking.id}/door-pass", headers=auth_headers(lead))
    assert error(response) == (403, "FORBIDDEN")


def test_door_pass_404_for_others(client, frozen, confirmed, make_user, make_pitika, auth_headers):
    booking, _booker, _owner = confirmed
    for other in (make_user(roles=["STAFF"]), make_pitika(province="SIEM_REAP")):
        response = client.get(f"{URL}/{booking.id}/door-pass", headers=auth_headers(other))
        assert error(response) == (404, "NOT_FOUND")


def test_door_pass_missing_404(client, frozen, as_admin):
    assert error(client.get(f"{URL}/999999/door-pass", headers=as_admin)) == (404, "NOT_FOUND")


def test_expired_flag(client, freeze_now, frozen, confirmed, auth_headers):
    booking, booker, _owner = confirmed
    headers = auth_headers(booker)
    url = f"{URL}/{booking.id}/door-pass"
    freeze_now(datetime(2026, 11, 10, 9, 59, 59))  # one second before the last end
    assert client.get(url, headers=headers).json()["expired"] is False
    freeze_now(datetime(2026, 11, 10, 10, 0))  # the last end
    assert client.get(url, headers=headers).json()["expired"] is True


def test_expires_at_is_last_end_utc(
    client, frozen, make_user, make_bookable_room, make_booking, auth_headers
):
    booker = make_user(roles=["STAFF"])
    booking = make_booking(
        make_bookable_room(),
        booker,
        status=BookingStatus.CONFIRMED,
        sessions=((DAY, time(8), time(9)), (DAY, time(9, 30), time(10))),
    )
    data = client.get(f"{URL}/{booking.id}/door-pass", headers=auth_headers(booker)).json()
    assert data["expires_at"] == "2026-11-10T03:00:00Z"
