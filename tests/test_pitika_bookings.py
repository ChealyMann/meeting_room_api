"""Pitika review: spec 9.11, 8.5, B-08, B-20."""

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

LIST = "/api/v1/pitika/bookings"
NEXT_DAY = DAY + timedelta(days=1)


def approve(client, headers, booking, **values):
    body = {"version": booking.version, **values}
    return client.post(f"{LIST}/{booking.id}/approve", json=body, headers=headers)


def reject(client, headers, booking, **values):
    body = {"version": booking.version, "reason": "Room is not free.", **values}
    return client.post(f"{LIST}/{booking.id}/reject", json=body, headers=headers)


@pytest.fixture
def pitika(make_pitika):
    return make_pitika(province="PHNOM_PENH")


@pytest.fixture
def pending(make_user, make_bookable_room, make_booking):
    """A booking waiting for Pitika in a Phnom Penh room; `build(room=None, **options)`."""

    def build(room=None, **options):
        options.setdefault("status", BookingStatus.PENDING_PITIKA)
        return make_booking(room or make_bookable_room(), make_user(roles=["STAFF"]), **options)

    return build


# --- List --------------------------------------------------------------------------------


def test_list_only_own_province(client, frozen, pitika, pending, make_bookable_room, auth_headers):
    mine = pending()
    pending(make_bookable_room(province="SIEM_REAP"))
    data = client.get(LIST, headers=auth_headers(pitika)).json()
    assert [item["id"] for item in data["items"]] == [mine.id]
    assert data["total"] == 1


def test_list_without_province_is_empty(client, frozen, make_user, pending, auth_headers):
    pending()
    nobody = make_user(roles=["PITIKA"])
    data = client.get(LIST, headers=auth_headers(nobody)).json()
    assert (data["items"], data["total"]) == ([], 0)


def test_list_sorted_by_first_start(client, frozen, pitika, pending, auth_headers):
    late = pending(sessions=((NEXT_DAY, time(9), time(10)),))
    early = pending(sessions=((DAY, time(14), time(15)), (NEXT_DAY, time(8), time(9))))
    data = client.get(LIST, headers=auth_headers(pitika)).json()
    assert [item["id"] for item in data["items"]] == [early.id, late.id]


def test_list_from_to_match_any_session(client, frozen, pitika, pending, auth_headers):
    far_day = NEXT_DAY + timedelta(days=5)
    two_days = pending(sessions=((DAY, time(9), time(10)), (far_day, time(9), time(10))))
    only_day = pending(sessions=((DAY, time(11), time(12)),))
    headers = auth_headers(pitika)

    far = far_day.isoformat()
    data = client.get(LIST, params={"from": far, "to": far}, headers=headers).json()
    assert [item["id"] for item in data["items"]] == [two_days.id]

    data = client.get(LIST, params={"to": DAY.isoformat()}, headers=headers).json()
    assert {item["id"] for item in data["items"]} == {two_days.id, only_day.id}

    data = client.get(LIST, params={"from": NEXT_DAY.isoformat()}, headers=headers).json()
    assert [item["id"] for item in data["items"]] == [two_days.id]


def test_list_filters(client, frozen, pitika, pending, make_bookable_room, auth_headers):
    room = make_bookable_room()
    first = pending(room, meeting_title="Budget")
    second = pending(status=BookingStatus.CONFIRMED, sessions=((NEXT_DAY, time(9), time(10)),))
    headers = auth_headers(pitika)

    def ids(**params):
        data = client.get(LIST, params=params, headers=headers).json()
        return {item["id"] for item in data["items"]}

    assert ids(status="PENDING_PITIKA") == {first.id}
    assert ids(status="CONFIRMED") == {second.id}
    assert ids(room_id=room.id) == {first.id}
    assert ids(q="budg") == {first.id}
    assert ids(q=second.reference_code) == {second.id}
    assert client.get(LIST, params={"status": "NOPE"}, headers=headers).status_code == 422


def test_list_q_matches_requester_name(
    client, frozen, pitika, make_user, make_bookable_room, make_booking, auth_headers
):
    room = make_bookable_room()
    asked = make_user(roles=["STAFF"], name_en="Sokha Chan")
    wanted = make_booking(room, asked, status=BookingStatus.PENDING_PITIKA)
    make_booking(room, make_user(roles=["STAFF"]), status=BookingStatus.PENDING_PITIKA,
                 sessions=((DAY, time(12), time(13)),))  # fmt: skip
    data = client.get(LIST, params={"q": "sokha"}, headers=auth_headers(pitika)).json()
    assert [item["id"] for item in data["items"]] == [wanted.id]


def test_list_query_count_does_not_grow(
    client, frozen, conn, db_session, pitika, make_user, make_bookable_room, make_booking,
    auth_headers,
):  # fmt: skip
    from sqlalchemy import event

    headers = auth_headers(pitika)
    booker = make_user(roles=["STAFF"])

    def add(n):
        for _ in range(n):
            make_booking(make_bookable_room(), booker, status=BookingStatus.PENDING_PITIKA,
                         catering=True, it=True)  # fmt: skip
        db_session.expire_all()

    def statements():
        seen = []

        def remember(*_args):
            seen.append(1)

        event.listen(conn, "before_cursor_execute", remember)
        try:
            response = client.get(LIST, headers=headers)
        finally:
            event.remove(conn, "before_cursor_execute", remember)
        assert response.status_code == 200
        return len(seen), response.json()["total"]

    add(2)
    few = statements()
    add(4)
    many = statements()
    assert (few[1], many[1]) == (2, 6)
    assert many[0] == few[0]


# --- Approve -----------------------------------------------------------------------------


def test_t3_r2_goes_to_owner(client, frozen, pitika, pending, make_bookable_room, auth_headers):
    booking = pending(make_bookable_room(private=True), route=BookingRoute.R2)
    response = approve(client, auth_headers(pitika), booking, notes="  Fine  ")
    assert response.status_code == 200
    data = response.json()
    assert (data["status"], data["version"]) == ("PENDING_OWNER", 2)
    review = data["reviews"][-1]
    assert (review["stage"], review["decision"], review["notes"]) == ("PITIKA", "APPROVED", "Fine")
    assert review["reviewer"]["id"] == pitika.id
    assert data["rejection"] is None


def test_t4_it_forwarded(client, frozen, pitika, pending, auth_headers):
    booking = pending(it=True)
    response = approve(client, auth_headers(pitika), booking)
    assert response.status_code == 200
    data = response.json()
    assert (data["status"], data["version"]) == ("SETUP_IN_PROGRESS", 2)
    assert data["it"]["forwarded_at"] is not None
    assert data["reviews"][-1]["notes"] is None


def test_t5_confirmed_with_door_pass(client, frozen, pitika, pending, auth_headers):
    booking = pending()
    response = approve(client, auth_headers(pitika), booking)
    assert response.status_code == 200
    assert response.json()["status"] == "CONFIRMED"
    assert booking.door_pass is not None
    assert booking.door_pass.expires_at == datetime(2026, 11, 10, 3, 0)  # 10:00 local, UTC+7
    assert all(s.is_blocking for s in booking.sessions)


def test_food_approved_with_notes(client, frozen, pitika, pending, auth_headers):
    booking = pending(catering=True)
    response = approve(client, auth_headers(pitika), booking, notes="Coffee at 08:45")
    assert response.status_code == 200
    order = booking.catering_order
    assert order.decided_by == pitika.id
    assert order.decided_at is not None
    assert order.approver_notes == "Coffee at 08:45"
    catering = response.json()["catering"]
    assert catering["approver_notes"] == "Coffee at 08:45"
    assert catering["decided_by"]["id"] == pitika.id
    assert response.json()["reviews"][-1]["notes"] == "Coffee at 08:45"


def test_blank_notes_are_saved_as_none(client, frozen, pitika, pending, auth_headers):
    booking = pending(catering=True)
    approve(client, auth_headers(pitika), booking, notes="   ")
    assert booking.catering_order.approver_notes is None
    assert booking.catering_order.decided_by == pitika.id


def test_approve_after_start_time_passed(client, frozen, freeze_now, pitika, pending, auth_headers):
    booking = pending()
    freeze_now(datetime(2026, 11, 10, 9, 30))
    response = approve(client, auth_headers(pitika), booking)
    assert error(response) == (409, "TIME_PASSED")
    assert booking.status == BookingStatus.PENDING_PITIKA


def test_wrong_status_invalid_transition(client, frozen, pitika, pending, auth_headers):
    booking = pending(status=BookingStatus.PENDING_OWNER, route=BookingRoute.R2)
    response = approve(client, auth_headers(pitika), booking)
    assert error(response) == (409, "INVALID_TRANSITION")
    assert response.json()["error"]["message"] == "This booking is waiting for the room owner."


def test_stale_version(client, frozen, pitika, pending, auth_headers):
    booking = pending()
    response = approve(client, auth_headers(pitika), booking, version=0)
    assert error(response) == (409, "STALE_VERSION")
    assert booking.status == BookingStatus.PENDING_PITIKA


def test_version_is_checked_before_status(client, frozen, pitika, pending, auth_headers):
    booking = pending(status=BookingStatus.CONFIRMED)
    response = approve(client, auth_headers(pitika), booking, version=7)
    assert error(response) == (409, "STALE_VERSION")


def test_self_approval_allowed(
    client, frozen, pitika, make_bookable_room, make_booking, auth_headers
):
    booking = make_booking(make_bookable_room(), pitika, status=BookingStatus.PENDING_PITIKA)
    assert approve(client, auth_headers(pitika), booking).status_code == 200
    assert booking.status == BookingStatus.CONFIRMED


def test_other_province_404(client, frozen, pending, make_pitika, make_bookable_room, auth_headers):
    booking = pending(make_bookable_room(province="SIEM_REAP"))
    headers = auth_headers(make_pitika(province="PHNOM_PENH"))
    assert error(approve(client, headers, booking)) == (404, "NOT_FOUND")
    assert error(reject(client, headers, booking)) == (404, "NOT_FOUND")
    assert booking.status == BookingStatus.PENDING_PITIKA


def test_missing_and_no_province_404(client, frozen, pending, make_user, pitika, auth_headers):
    booking = pending()
    response = client.post(
        f"{LIST}/999999/approve", json={"version": 1}, headers=auth_headers(pitika)
    )
    assert error(response) == (404, "NOT_FOUND")
    nobody = auth_headers(make_user(roles=["PITIKA"]))
    assert error(approve(client, nobody, booking)) == (404, "NOT_FOUND")


def test_staff_and_admin_forbidden(client, frozen, pending, as_staff, as_admin):
    booking = pending()
    for headers in (as_staff, as_admin):
        assert error(client.get(LIST, headers=headers)) == (403, "FORBIDDEN")
        assert error(approve(client, headers, booking)) == (403, "FORBIDDEN")
        assert error(reject(client, headers, booking)) == (403, "FORBIDDEN")


def test_approve_body_rules(client, frozen, pitika, pending, auth_headers):
    booking = pending()
    headers = auth_headers(pitika)
    url = f"{LIST}/{booking.id}/approve"
    assert client.post(url, json={}, headers=headers).status_code == 422
    assert client.post(url, json={"version": 1, "x": 1}, headers=headers).status_code == 422
    long = {"version": 1, "notes": "a" * 1001}
    assert client.post(url, json=long, headers=headers).status_code == 422
    html = {"version": 1, "notes": "<b>x"}
    assert client.post(url, json=html, headers=headers).status_code == 422


# --- Reject ------------------------------------------------------------------------------


def test_t6_reject_needs_reason(client, frozen, pitika, pending, db_session, auth_headers):
    booking = pending(catering=True, it=True)
    headers = auth_headers(pitika)
    assert reject(client, headers, booking, reason="abc").status_code == 422
    assert reject(client, headers, booking, reason="x" * 1001).status_code == 422
    assert booking.status == BookingStatus.PENDING_PITIKA

    response = reject(client, headers, booking, reason="  Not available  ")
    assert response.status_code == 200
    data = response.json()
    assert (data["status"], data["version"]) == ("REJECTED", 2)
    assert (data["rejection"]["rejected_by"], data["rejection"]["reason"]) == (
        RejectedBy.PITIKA,
        "Not available",
    )
    assert data["rejection"]["actor"]["id"] == pitika.id
    review = data["reviews"][-1]
    assert (review["stage"], review["decision"]) == (ReviewStage.PITIKA, ReviewDecision.REJECTED)
    blocking = db_session.scalars(
        select(BookingSession.is_blocking).where(BookingSession.booking_id == booking.id)
    ).all()
    assert blocking and not any(blocking)
    assert booking.catering_order.decided_by is None


def test_reject_after_start_ok(client, frozen, freeze_now, pitika, pending, auth_headers):
    booking = pending()
    freeze_now(datetime(2026, 11, 10, 9, 30))
    assert reject(client, auth_headers(pitika), booking).status_code == 200
    assert booking.status == BookingStatus.REJECTED


def test_reject_wrong_status_and_stale(client, frozen, pitika, pending, auth_headers):
    headers = auth_headers(pitika)
    booking = pending(status=BookingStatus.CONFIRMED)
    assert error(reject(client, headers, booking)) == (409, "INVALID_TRANSITION")
    assert error(reject(client, headers, booking, version=0)) == (409, "STALE_VERSION")
