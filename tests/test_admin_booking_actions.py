"""Admin booking actions: spec B-33, B-34, B-35 (decisions D-32 to D-40)."""

from datetime import date, time

import pytest
from sqlalchemy import select

from app.constants.booking import BookingStatus
from app.models import BookingSession
from tests.booking_helpers import DAY, error

BASE = "/api/v1/admin/bookings"
PAST_DAY = date(2026, 11, 6)  # before NOW (Monday Nov 9, 08:00)
NOW_DAY = date(2026, 11, 9)


@pytest.fixture
def admin(make_user):
    return make_user(roles=["ADMIN"])


@pytest.fixture
def booking(make_user, make_bookable_room, make_booking):
    """`build(status, room=None, **options)`: a booking by a staff member, in a Siem Reap room
    (no Pitika there unless a test adds one)."""

    def build(status, room=None, **options):
        room = room or make_bookable_room(province="SIEM_REAP")
        return make_booking(room, make_user(roles=["STAFF"]), status=status, **options)

    return build


def post(client, headers, b, action, **body):
    return client.post(
        f"{BASE}/{b.id}/{action}", json={"version": b.version, **body}, headers=headers
    )


def blocking(db_session, booking_id):
    rows = select(BookingSession.is_blocking).where(BookingSession.booking_id == booking_id)
    return db_session.scalars(rows).all()


# --- Cancel (D-32, D-35, D-37, D-38) -----------------------------------------------------


@pytest.mark.parametrize(
    "status",
    [
        BookingStatus.PENDING_PITIKA,
        BookingStatus.PENDING_OWNER,
        BookingStatus.SETUP_IN_PROGRESS,
        BookingStatus.CONFIRMED,
    ],
)
def test_cancel_any_open_booking(client, frozen, admin, booking, db_session, auth_headers, status):
    b = booking(status, catering=True, it=True)
    response = post(client, auth_headers(admin), b, "cancel", reason="The room is closed.")
    assert response.status_code == 200, response.text
    data = response.json()
    assert (data["status"], data["cancel_reason"]) == ("CANCELLED", "The room is closed.")
    assert data["cancelled_by"]["id"] == admin.id
    assert data["catering"] is not None and data["it"] is not None
    assert blocking(db_session, b.id) == [False]


def test_cancel_without_reason(client, frozen, admin, booking, auth_headers):
    b = booking(BookingStatus.CONFIRMED)
    data = post(client, auth_headers(admin), b, "cancel").json()
    assert (data["status"], data["cancel_reason"]) == ("CANCELLED", None)


def test_cancel_reason_html_refused(client, frozen, admin, booking, auth_headers):
    b = booking(BookingStatus.CONFIRMED)
    response = post(client, auth_headers(admin), b, "cancel", reason="<b>closed</b>")
    assert response.status_code == 422
    assert "reason" in response.json()["error"]["fields"]


def test_cancel_after_end_refused(client, frozen, admin, booking, auth_headers):
    b = booking(BookingStatus.CONFIRMED, sessions=((PAST_DAY, time(9), time(10)),))
    response = post(client, auth_headers(admin), b, "cancel")
    assert error(response) == (409, "INVALID_TRANSITION")
    assert response.json()["error"]["message"] == "This booking has ended."


def test_cancel_final_refused(client, frozen, admin, booking, auth_headers):
    b = booking(BookingStatus.REJECTED)
    assert error(post(client, auth_headers(admin), b, "cancel")) == (409, "INVALID_TRANSITION")


def test_admin_cancels_own_booking(
    client, frozen, admin, make_bookable_room, make_booking, auth_headers
):
    b = make_booking(make_bookable_room(), admin, status=BookingStatus.CONFIRMED)
    data = post(client, auth_headers(admin), b, "cancel").json()
    assert data["cancelled_by"]["id"] == admin.id


def test_stale_version_before_status(client, frozen, admin, booking, auth_headers):
    b = booking(BookingStatus.REJECTED)
    response = client.post(
        f"{BASE}/{b.id}/cancel", json={"version": b.version + 5}, headers=auth_headers(admin)
    )
    assert error(response) == (409, "STALE_VERSION")


# --- Approve and reject for Pitika (D-33) ------------------------------------------------


def test_approve_for_pitika_confirms_r1(client, frozen, admin, booking, auth_headers):
    b = booking(BookingStatus.PENDING_PITIKA, catering=True)
    data = post(client, auth_headers(admin), b, "approve", notes="Fine").json()
    assert data["status"] == "CONFIRMED"
    review = data["reviews"][-1]
    assert (review["stage"], review["decision"], review["by_admin"]) == ("PITIKA", "APPROVED", True)
    assert review["reviewer"]["id"] == admin.id
    assert data["catering"]["decided_by"]["id"] == admin.id


def test_approve_for_pitika_r2_goes_to_owner(
    client, frozen, admin, booking, make_bookable_room, auth_headers
):
    room = make_bookable_room(province="SIEM_REAP", private=True)
    b = booking(BookingStatus.PENDING_PITIKA, room)
    assert post(client, auth_headers(admin), b, "approve").json()["status"] == "PENDING_OWNER"


def test_approve_for_pitika_with_it_goes_to_setup(client, frozen, admin, booking, auth_headers):
    b = booking(BookingStatus.PENDING_PITIKA, it=True)
    assert post(client, auth_headers(admin), b, "approve").json()["status"] == "SETUP_IN_PROGRESS"


def test_active_pitika_blocks_the_admin(client, frozen, admin, booking, make_pitika, auth_headers):
    make_pitika(province="SIEM_REAP")
    b = booking(BookingStatus.PENDING_PITIKA)
    for action in ("approve", "reject"):
        response = post(client, auth_headers(admin), b, action)
        assert error(response) == (403, "FORBIDDEN")
        assert response.json()["error"]["message"] == (
            "This office has an active Pitika. Ask them to decide."
        )


def test_approve_after_start_refused(client, frozen, admin, booking, auth_headers):
    b = booking(BookingStatus.PENDING_PITIKA, sessions=((NOW_DAY, time(7), time(9)),))
    assert error(post(client, auth_headers(admin), b, "approve")) == (409, "TIME_PASSED")


def test_reject_for_pitika_without_reason(client, frozen, admin, booking, auth_headers):
    b = booking(BookingStatus.PENDING_PITIKA)
    data = post(client, auth_headers(admin), b, "reject").json()
    assert data["status"] == "REJECTED"
    rejection = data["rejection"]
    assert (rejection["rejected_by"], rejection["by_admin"]) == ("PITIKA", True)
    assert rejection["reason"] == "Rejected by the Admin."
    assert rejection["actor"]["id"] == admin.id


# --- Approve and reject for the room owner (D-34) ----------------------------------------


@pytest.fixture
def owner_waiting(booking, make_bookable_room):
    def build(**options):
        room = make_bookable_room(province="PHNOM_PENH", private=True)
        return booking(BookingStatus.PENDING_OWNER, room, **options)

    return build


def test_approve_for_owner(client, frozen, admin, owner_waiting, make_pitika, auth_headers):
    make_pitika(province="PHNOM_PENH")  # an active Pitika does not matter at the owner stage
    data = post(client, auth_headers(admin), owner_waiting(), "approve").json()
    assert data["status"] == "CONFIRMED"
    review = data["reviews"][-1]
    assert (review["stage"], review["by_admin"], review["reviewer"]["id"]) == (
        "OWNER",
        True,
        admin.id,
    )


def test_reject_for_owner(client, frozen, admin, owner_waiting, auth_headers):
    data = post(
        client, auth_headers(admin), owner_waiting(), "reject", reason="Closed that day."
    ).json()
    rejection = data["rejection"]
    assert (data["status"], rejection["rejected_by"], rejection["by_admin"]) == (
        "REJECTED",
        "OWNER",
        True,
    )
    assert rejection["reason"] == "Closed that day."


# --- No Admin IT steps (D-40) ------------------------------------------------------------


def test_setup_cannot_be_approved_or_rejected(client, frozen, admin, booking, auth_headers):
    b = booking(BookingStatus.SETUP_IN_PROGRESS, it=True, forwarded=True)
    for action in ("approve", "reject"):
        assert error(post(client, auth_headers(admin), b, action)) == (409, "INVALID_TRANSITION")


# --- Allowed actions ---------------------------------------------------------------------


def actions(client, headers, b):
    response = client.get(f"{BASE}/{b.id}/actions", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def test_actions_for_each_case(
    client, frozen, admin, booking, owner_waiting, make_pitika, make_bookable_room, auth_headers
):
    h = auth_headers(admin)
    assert actions(client, h, booking(BookingStatus.PENDING_PITIKA)) == {
        "cancel": True, "approve": True, "reject": True, "stage": "PITIKA",
    }  # fmt: skip
    assert actions(client, h, owner_waiting()) == {
        "cancel": True, "approve": True, "reject": True, "stage": "OWNER",
    }  # fmt: skip
    assert actions(client, h, booking(BookingStatus.SETUP_IN_PROGRESS, it=True)) == {
        "cancel": True, "approve": False, "reject": False, "stage": None,
    }  # fmt: skip
    assert actions(client, h, booking(BookingStatus.CANCELLED)) == {
        "cancel": False, "approve": False, "reject": False, "stage": None,
    }  # fmt: skip
    ended = booking(BookingStatus.CONFIRMED, sessions=((PAST_DAY, time(9), time(10)),))
    assert actions(client, h, ended)["cancel"] is False
    started = booking(BookingStatus.PENDING_PITIKA, sessions=((NOW_DAY, time(7), time(9)),))
    assert actions(client, h, started) == {
        "cancel": True, "approve": False, "reject": True, "stage": "PITIKA",
    }  # fmt: skip
    make_pitika(province="PHNOM_PENH")
    covered = booking(BookingStatus.PENDING_PITIKA, make_bookable_room(province="PHNOM_PENH"))
    assert actions(client, h, covered) == {
        "cancel": True, "approve": False, "reject": False, "stage": None,
    }  # fmt: skip


# --- Access ------------------------------------------------------------------------------


@pytest.mark.parametrize("role", ["STAFF", "PITIKA"])
def test_not_admin_403(client, frozen, booking, make_user, auth_headers, role):
    b = booking(BookingStatus.PENDING_PITIKA)
    h = auth_headers(make_user(roles=[role]))
    assert client.get(f"{BASE}/{b.id}/actions", headers=h).status_code == 403
    for action in ("cancel", "approve", "reject"):
        assert post(client, h, b, action).status_code == 403


def test_missing_booking_404(client, frozen, admin, auth_headers):
    h = auth_headers(admin)
    assert client.get(f"{BASE}/999999/actions", headers=h).status_code == 404
    response = client.post(f"{BASE}/999999/cancel", json={"version": 1}, headers=h)
    assert response.status_code == 404


def test_day_is_tomorrow():
    assert DAY == date(2026, 11, 10)
