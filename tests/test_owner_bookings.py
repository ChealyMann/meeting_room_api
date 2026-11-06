"""Room owner review: spec 9.13, 8.5, B-08, B-09, BR-OWN-05."""

from datetime import datetime, time, timedelta

import pytest
from sqlalchemy import select

from app.constants.booking import (
    BookingRoute,
    BookingStatus,
    RejectedBy,
    ReviewDecision,
    ReviewStage,
)
from app.models import BookingSession
from tests.booking_helpers import DAY, error

LIST = "/api/v1/owner/bookings"
NEXT_DAY = DAY + timedelta(days=1)


def approve(client, headers, booking, **values):
    body = {"version": booking.version, **values}
    return client.post(f"{LIST}/{booking.id}/approve", json=body, headers=headers)


def reject(client, headers, booking, **values):
    body = {"version": booking.version, "reason": "Room is not free.", **values}
    return client.post(f"{LIST}/{booking.id}/reject", json=body, headers=headers)


@pytest.fixture
def owner(make_user):
    return make_user(roles=["ROOM_OWNER"])


@pytest.fixture
def waiting(make_user, make_bookable_room, make_booking, owner):
    """A booking waiting for `owner` in their private room; `build(room=None, **options)`."""

    def build(room=None, **options):
        options.setdefault("status", BookingStatus.PENDING_OWNER)
        options.setdefault("route", BookingRoute.R2)
        room = room or make_bookable_room(private=True, owner=owner)
        return make_booking(room, make_user(roles=["STAFF"]), **options)

    return build


# --- List --------------------------------------------------------------------------------


def test_list_only_own_private_rooms(
    client, frozen, owner, waiting, make_bookable_room, make_user, auth_headers
):
    mine = waiting()
    waiting(make_bookable_room(private=True))  # another owner's room
    waiting(make_bookable_room(owner=owner), status=BookingStatus.CONFIRMED)  # not private
    data = client.get(LIST, headers=auth_headers(owner)).json()
    assert [item["id"] for item in data["items"]] == [mine.id]
    assert data["total"] == 1


def test_list_sorted_by_first_start(client, frozen, owner, waiting, auth_headers):
    late = waiting(sessions=((NEXT_DAY, time(9), time(10)),))
    early = waiting(sessions=((DAY, time(14), time(15)), (NEXT_DAY, time(8), time(9))))
    data = client.get(LIST, headers=auth_headers(owner)).json()
    assert [item["id"] for item in data["items"]] == [early.id, late.id]


def test_list_filters(client, frozen, owner, waiting, make_bookable_room, auth_headers):
    room = make_bookable_room(private=True, owner=owner)
    first = waiting(room, meeting_title="Budget")
    second = waiting(status=BookingStatus.CONFIRMED, sessions=((NEXT_DAY, time(9), time(10)),))
    headers = auth_headers(owner)

    def ids(**params):
        data = client.get(LIST, params=params, headers=headers).json()
        return {item["id"] for item in data["items"]}

    assert ids(status="PENDING_OWNER") == {first.id}
    assert ids(status="CONFIRMED") == {second.id}
    assert ids(room_id=room.id) == {first.id}
    assert ids(q="budg") == {first.id}
    assert ids(q=second.reference_code) == {second.id}
    assert client.get(LIST, params={"status": "NOPE"}, headers=headers).status_code == 422


def test_list_other_roles_forbidden(client, frozen, as_staff, as_admin, make_pitika, auth_headers):
    for headers in (as_staff, as_admin, auth_headers(make_pitika())):
        assert error(client.get(LIST, headers=headers)) == (403, "FORBIDDEN")


# --- Approve -----------------------------------------------------------------------------


def test_t7_it_forwarded(client, frozen, owner, waiting, auth_headers):
    booking = waiting(it=True)
    response = approve(client, auth_headers(owner), booking, notes="  Ok  ")
    assert response.status_code == 200
    data = response.json()
    assert (data["status"], data["version"]) == ("SETUP_IN_PROGRESS", 2)
    assert data["it"]["forwarded_at"] is not None
    review = data["reviews"][-1]
    assert (review["stage"], review["decision"], review["notes"]) == ("OWNER", "APPROVED", "Ok")
    assert review["reviewer"]["id"] == owner.id


def test_t8_confirmed(client, frozen, owner, waiting, auth_headers):
    booking = waiting()
    response = approve(client, auth_headers(owner), booking)
    assert response.status_code == 200
    assert response.json()["status"] == "CONFIRMED"
    assert booking.door_pass is not None
    assert booking.door_pass.expires_at == datetime(2026, 11, 10, 3, 0)  # 10:00 local, UTC+7
    assert all(s.is_blocking for s in booking.sessions)
    assert booking.reviews[-1].stage == ReviewStage.OWNER


def test_approve_after_start_time_passed(client, frozen, freeze_now, owner, waiting, auth_headers):
    booking = waiting()
    freeze_now(datetime(2026, 11, 10, 9, 30))
    response = approve(client, auth_headers(owner), booking)
    assert error(response) == (409, "TIME_PASSED")
    assert response.json()["error"]["message"] == "The meeting has started. It cannot be approved."
    assert booking.status == BookingStatus.PENDING_OWNER


def test_pending_pitika_invalid_transition(client, frozen, owner, waiting, auth_headers):
    booking = waiting(status=BookingStatus.PENDING_PITIKA)
    headers = auth_headers(owner)
    response = approve(client, headers, booking)
    assert error(response) == (409, "INVALID_TRANSITION")
    assert response.json()["error"]["message"] == "This booking is waiting for Pitika."
    assert error(reject(client, headers, booking)) == (409, "INVALID_TRANSITION")
    assert booking.status == BookingStatus.PENDING_PITIKA


def test_stale_version_checked_before_status(client, frozen, owner, waiting, auth_headers):
    headers = auth_headers(owner)
    assert error(approve(client, headers, waiting(), version=0)) == (409, "STALE_VERSION")
    confirmed = waiting(status=BookingStatus.CONFIRMED)
    assert error(approve(client, headers, confirmed, version=7)) == (409, "STALE_VERSION")
    assert error(approve(client, headers, confirmed)) == (409, "INVALID_TRANSITION")


def test_other_owner_404(client, frozen, waiting, make_user, make_bookable_room, auth_headers):
    booking = waiting()
    stranger = auth_headers(make_user(roles=["ROOM_OWNER"]))
    assert error(approve(client, stranger, booking)) == (404, "NOT_FOUND")
    assert error(reject(client, stranger, booking)) == (404, "NOT_FOUND")
    assert booking.status == BookingStatus.PENDING_OWNER


def test_missing_and_non_private_room_404(
    client, frozen, owner, waiting, make_bookable_room, auth_headers
):
    headers = auth_headers(owner)
    response = client.post(f"{LIST}/999999/approve", json={"version": 1}, headers=headers)
    assert error(response) == (404, "NOT_FOUND")
    public = waiting(make_bookable_room(owner=owner))
    assert error(approve(client, headers, public)) == (404, "NOT_FOUND")


def test_other_roles_forbidden(
    client, frozen, waiting, as_staff, as_admin, make_pitika, auth_headers
):
    booking = waiting()
    for headers in (as_staff, as_admin, auth_headers(make_pitika())):
        assert error(approve(client, headers, booking)) == (403, "FORBIDDEN")
        assert error(reject(client, headers, booking)) == (403, "FORBIDDEN")


def test_approve_body_rules(client, frozen, owner, waiting, auth_headers):
    booking = waiting()
    headers = auth_headers(owner)
    url = f"{LIST}/{booking.id}/approve"
    assert client.post(url, json={}, headers=headers).status_code == 422
    assert client.post(url, json={"version": 1, "x": 1}, headers=headers).status_code == 422
    assert (
        client.post(url, json={"version": 1, "notes": "a" * 1001}, headers=headers).status_code
        == 422
    )


def test_queue_follows_new_owner(client, frozen, owner, waiting, make_user, as_admin, auth_headers):
    booking = waiting()
    newcomer = make_user(roles=["ROOM_OWNER"])
    response = client.patch(
        f"/api/v1/rooms/{booking.room_id}", json={"room_owner_id": newcomer.id}, headers=as_admin
    )
    assert response.status_code == 200

    old, new = auth_headers(owner), auth_headers(newcomer)
    assert client.get(LIST, headers=old).json()["items"] == []
    assert error(approve(client, old, booking)) == (404, "NOT_FOUND")

    data = client.get(LIST, headers=new).json()
    assert [item["id"] for item in data["items"]] == [booking.id]
    response = approve(client, new, booking)
    assert response.status_code == 200
    assert response.json()["reviews"][-1]["reviewer"]["id"] == newcomer.id


# --- Reject ------------------------------------------------------------------------------


def test_t9_reject(client, frozen, owner, waiting, db_session, auth_headers):
    booking = waiting(catering=True, it=True)
    headers = auth_headers(owner)
    assert reject(client, headers, booking, reason="abc").status_code == 422
    assert booking.status == BookingStatus.PENDING_OWNER

    response = reject(client, headers, booking, reason="  Not available  ")
    assert response.status_code == 200
    data = response.json()
    assert (data["status"], data["version"]) == ("REJECTED", 2)
    assert (data["rejection"]["rejected_by"], data["rejection"]["reason"]) == (
        RejectedBy.OWNER,
        "Not available",
    )
    assert data["rejection"]["actor"]["id"] == owner.id
    review = data["reviews"][-1]
    assert (review["stage"], review["decision"]) == (ReviewStage.OWNER, ReviewDecision.REJECTED)
    blocking = db_session.scalars(
        select(BookingSession.is_blocking).where(BookingSession.booking_id == booking.id)
    ).all()
    assert blocking and not any(blocking)


def test_reject_after_start_ok(client, frozen, freeze_now, owner, waiting, auth_headers):
    booking = waiting()
    freeze_now(datetime(2026, 11, 10, 9, 30))
    assert reject(client, auth_headers(owner), booking).status_code == 200
    assert booking.status == BookingStatus.REJECTED


def test_reject_stale(client, frozen, owner, waiting, auth_headers):
    booking = waiting()
    assert error(reject(client, auth_headers(owner), booking, version=0)) == (409, "STALE_VERSION")


def test_list_from_to_match_any_session(client, frozen, owner, waiting, auth_headers):
    far_day = NEXT_DAY + timedelta(days=5)
    two_days = waiting(sessions=((DAY, time(9), time(10)), (far_day, time(9), time(10))))
    only_day = waiting(sessions=((DAY, time(11), time(12)),))
    headers = auth_headers(owner)

    far = far_day.isoformat()
    data = client.get(LIST, params={"from": far, "to": far}, headers=headers).json()
    assert [item["id"] for item in data["items"]] == [two_days.id]

    data = client.get(LIST, params={"to": DAY.isoformat()}, headers=headers).json()
    assert {item["id"] for item in data["items"]} == {two_days.id, only_day.id}

    params = {"from": DAY.isoformat(), "to": (DAY - timedelta(days=1)).isoformat()}
    assert error(client.get(LIST, params=params, headers=headers))[0] == 422
