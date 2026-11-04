"""Every route from send to CONFIRMED through the HTTP API (spec 4, 5, 12.1).

R1 shared room; R2 someone else's private room; R3 the owner's own private room with no
extras; R4 the owner's own private room with food and/or IT. With IT, the booking goes
through IT setup (T4/T7, T10, T11) before it is confirmed.
"""

import re

import pytest

from tests.booking_helpers import URL, book, error

PITIKA_URL = "/api/v1/pitika/bookings"
OWNER_URL = "/api/v1/owner/bookings"
IT_URL = "/api/v1/it/tickets"


def _ok(response) -> dict:
    assert response.status_code in (200, 201), response.text
    return response.json()


def _approve(client, url, headers, data) -> dict:
    body = {"notes": "Looks fine.", "version": data["version"]}
    return _ok(client.post(f"{url}/{data['id']}/approve", json=body, headers=headers))


def _it_setup(client, headers, booking_id, staff_id) -> dict:
    """The IT Lead finds the ticket, assigns staff (T10) and presses Ready (T11).
    Returns the booking as the ready answer shows it."""
    tickets = _ok(client.get(IT_URL, headers=headers))["items"]
    [ticket] = [item for item in tickets if item["booking"]["id"] == booking_id]
    assert (ticket["status"], ticket["booking"]["status"]) == ("RECEIVED", "SETUP_IN_PROGRESS")

    body = {"user_ids": [staff_id], "version": ticket["booking"]["version"]}
    ticket = _ok(client.put(f"{IT_URL}/{ticket['id']}/staff", json=body, headers=headers))
    assert (ticket["status"], ticket["booking"]["status"]) == ("ASSIGNED", "SETUP_IN_PROGRESS")

    body = {"version": ticket["booking"]["version"]}
    ticket = _ok(client.post(f"{IT_URL}/{ticket['id']}/ready", json=body, headers=headers))
    assert ticket["status"] == "READY"
    return ticket["booking"]


@pytest.mark.parametrize(
    ("route", "it"),
    [
        ("R1", False),
        ("R1", True),
        ("R2", False),
        ("R2", True),
        ("R3", False),
        ("R4", False),
        ("R4", True),
    ],
)
def test_route_to_confirmed(
    client,
    frozen,
    route,
    it,
    make_user,
    make_pitika,
    make_bookable_room,
    make_catering_package,
    make_it_service,
    auth_headers,
):
    pitika = make_pitika()
    owner = make_user(roles=["ROOM_OWNER"])
    lead = make_user(roles=["IT_LEAD"])
    staff = make_user(roles=["IT_STAFF"])
    room = make_bookable_room(private=route != "R1", owner=owner if route != "R1" else None)
    booker = owner if route in ("R3", "R4") else make_user(roles=["STAFF"])

    extras = {}
    if route != "R3":
        extras["catering"] = {"package_ids": [make_catering_package().id]}
    if it:
        extras["it"] = {"service_ids": [make_it_service().id]}
    if route == "R2":
        extras["private_justification"] = "Board meeting needs privacy."

    data = _ok(book(client, auth_headers(booker), room.id, **extras))
    assert data["route"] == route
    seen = [data["status"]]

    if route != "R3":
        data = _approve(client, PITIKA_URL, auth_headers(pitika), data)
        seen.append(data["status"])
        assert data["catering"]["decided_by"]["id"] == pitika.id
    if route == "R2":
        data = _approve(client, OWNER_URL, auth_headers(owner), data)
        seen.append(data["status"])
    if it:
        data = _it_setup(client, auth_headers(lead), data["id"], staff.id)
        seen.append(data["status"])

    expected = {
        "R1": ["PENDING_PITIKA"],
        "R2": ["PENDING_PITIKA", "PENDING_OWNER"],
        "R3": [],
        "R4": ["PENDING_PITIKA"],
    }[route]
    expected += ["SETUP_IN_PROGRESS"] if it else []
    assert seen == [*expected, "CONFIRMED"]

    headers = auth_headers(booker)
    final = _ok(client.get(f"{URL}/{data['id']}", headers=headers))
    assert (final["status"], final["display_status"]) == ("CONFIRMED", "CONFIRMED")
    door_pass = _ok(client.get(f"{URL}/{data['id']}/door-pass", headers=headers))
    assert re.fullmatch(r"NBC-\d{5}", door_pass["passcode"])
    assert door_pass["expired"] is False


def test_move_not_in_table(
    client, frozen, make_user, make_pitika, make_bookable_room, auth_headers
):
    """Approving a booking that is already CONFIRMED is not a move in the table."""
    pitika = make_pitika()
    room = make_bookable_room()
    data = _ok(book(client, auth_headers(make_user(roles=["STAFF"])), room.id))
    data = _approve(client, PITIKA_URL, auth_headers(pitika), data)
    assert data["status"] == "CONFIRMED"

    body = {"notes": None, "version": data["version"]}
    response = client.post(
        f"{PITIKA_URL}/{data['id']}/approve", json=body, headers=auth_headers(pitika)
    )
    assert error(response) == (409, "INVALID_TRANSITION")
