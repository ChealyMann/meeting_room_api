"""Room owner "Decided by me": the decided list and today's summary
(spec docs/superpowers/specs/2026-11-05-owner-and-it-pages-design.md, Part A)."""

from datetime import datetime, time, timedelta

import pytest
from sqlalchemy import event

from app.constants.booking import BookingRoute, BookingStatus, ReviewDecision, ReviewStage
from app.models import BookingReview
from tests.booking_helpers import DAY, NOW

LIST = "/api/v1/owner/bookings"
DECIDED = f"{LIST}/decided"
SUMMARY = f"{LIST}/summary"
ZERO = {"waiting": 0, "approved_today": 0, "rejected_today": 0}


def approve(client, headers, booking, **values):
    body = {"version": booking.version, **values}
    response = client.post(f"{LIST}/{booking.id}/approve", json=body, headers=headers)
    assert response.status_code == 200, response.json()
    return response.json()


def reject(client, headers, booking, reason="Room is not free."):
    body = {"version": booking.version, "reason": reason}
    response = client.post(f"{LIST}/{booking.id}/reject", json=body, headers=headers)
    assert response.status_code == 200, response.json()
    return response.json()


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


def decided(client, headers, decision="APPROVED", **params):
    response = client.get(DECIDED, params={"decision": decision, **params}, headers=headers)
    assert response.status_code == 200, response.json()
    return response.json()


def summary(client, headers):
    response = client.get(SUMMARY, headers=headers)
    assert response.status_code == 200, response.json()
    return response.json()


def ids(data):
    return [item["id"] for item in data["items"]]


def backup_review(db_session, booking, reviewer, stage=ReviewStage.OWNER):
    db_session.add(
        BookingReview(
            booking_id=booking.id,
            stage=stage,
            decision=ReviewDecision.APPROVED,
            reviewer_id=reviewer.id,
            reviewed_at=datetime(2026, 11, 9, 1, 0),
            by_admin=True,
        )
    )
    db_session.commit()


# --- List --------------------------------------------------------------------------------


def test_lists_my_owner_approvals_newest_first(
    client, frozen, freeze_now, owner, waiting, auth_headers
):
    headers = auth_headers(owner)
    first, second = waiting(), waiting(sessions=((DAY, time(14), time(15)),))
    approve(client, headers, first, notes="Ok")
    freeze_now(NOW + timedelta(hours=1))
    approve(client, headers, second)

    data = decided(client, headers)
    assert ids(data) == [second.id, first.id]
    assert data["items"][0]["decided_at"] == "2026-11-09T02:00:00Z"
    assert [item["decision_note"] for item in data["items"]] == [None, "Ok"]


def test_lists_my_owner_rejections_with_reason(client, frozen, owner, waiting, auth_headers):
    headers = auth_headers(owner)
    booking = waiting()
    reject(client, headers, booking, reason="Room is not free.")

    data = decided(client, headers, "REJECTED")
    assert ids(data) == [booking.id]
    assert data["items"][0]["decision_note"] == "Room is not free."
    assert decided(client, headers)["items"] == []


def test_pitika_review_not_in_owner_list(
    client, frozen, make_user, make_division, make_department, make_location,
    make_bookable_room, make_booking, auth_headers,
):  # fmt: skip
    office = make_division(make_department(make_location(province="PHNOM_PENH")))
    both = make_user(roles=["PITIKA", "ROOM_OWNER"], division=office)
    room = make_bookable_room(private=True, owner=both)
    booking = make_booking(room, make_user(roles=["STAFF"]), status=BookingStatus.PENDING_PITIKA,
                           route=BookingRoute.R2)  # fmt: skip
    response = client.post(
        f"/api/v1/pitika/bookings/{booking.id}/approve",
        json={"version": booking.version},
        headers=auth_headers(both),
    )
    assert response.status_code == 200, response.json()
    assert decided(client, auth_headers(both))["items"] == []
    assert summary(client, auth_headers(both))["waiting"] == 1


def test_new_owner_takes_the_queue(
    client, frozen, db_session, owner, waiting, make_user, make_bookable_room, auth_headers
):
    room = make_bookable_room(private=True, owner=owner)
    done, other = waiting(room), waiting(room, sessions=((DAY, time(14), time(15)),))
    approve(client, auth_headers(owner), done)
    new_owner = make_user(roles=["ROOM_OWNER"])
    room.room_owner_id = new_owner.id
    db_session.commit()

    assert decided(client, auth_headers(owner))["total"] == 0
    assert summary(client, auth_headers(owner)) == ZERO
    assert summary(client, auth_headers(new_owner))["waiting"] == 1
    assert other.id not in ids(decided(client, auth_headers(new_owner)))


def test_admin_backup_not_listed_or_counted(
    client, frozen, db_session, owner, waiting, auth_headers
):
    backup_review(db_session, waiting(status=BookingStatus.CONFIRMED), owner)
    headers = auth_headers(owner)
    assert decided(client, headers)["items"] == []
    assert summary(client, headers) == ZERO


def test_filters(client, frozen, owner, waiting, make_user, make_bookable_room, make_booking,
                 auth_headers):  # fmt: skip
    headers = auth_headers(owner)
    room = make_bookable_room(private=True, owner=owner)
    asked = make_user(roles=["STAFF"], name_en="Sokha Chan")
    budget = make_booking(room, asked, status=BookingStatus.PENDING_OWNER, route=BookingRoute.R2,
                          meeting_title="Budget review")  # fmt: skip
    later = waiting(sessions=((DAY + timedelta(days=3), time(9), time(10)),))
    for booking in (budget, later):
        approve(client, headers, booking)

    def found(**params):
        return set(ids(decided(client, headers, **params)))

    assert found(q="budg") == {budget.id}
    assert found(q="sokha") == {budget.id}
    assert found(room_id=room.id) == {budget.id}
    assert found(**{"from": str(DAY + timedelta(days=1))}) == {later.id}
    assert found(to=str(DAY)) == {budget.id}
    params = {"decision": "APPROVED", "from": str(DAY), "to": str(DAY - timedelta(days=1))}
    response = client.get(DECIDED, params=params, headers=headers)
    assert response.status_code == 422
    assert "to" in response.json()["error"]["fields"]


def test_decision_required_and_checked(client, frozen, owner, auth_headers):
    headers = auth_headers(owner)
    assert client.get(DECIDED, headers=headers).status_code == 422
    assert (
        client.get(DECIDED, params={"decision": "NOT_REQUIRED"}, headers=headers).status_code == 422
    )


def test_forbidden_for_staff_and_pitika(client, frozen, as_staff, make_pitika, auth_headers):
    pitika = auth_headers(make_pitika(province="PHNOM_PENH"))
    for headers in (as_staff, pitika):
        assert (
            client.get(DECIDED, params={"decision": "APPROVED"}, headers=headers).status_code == 403
        )
        assert client.get(SUMMARY, headers=headers).status_code == 403


def test_query_count_does_not_grow(client, frozen, conn, db_session, owner, waiting, auth_headers):
    headers = auth_headers(owner)

    def add(n):
        for _ in range(n):
            approve(client, headers, waiting(catering=True, it=True), notes="Ok")
        db_session.expire_all()

    def statements():
        seen = []

        def remember(*_args):
            seen.append(1)

        event.listen(conn, "before_cursor_execute", remember)
        try:
            data = decided(client, headers)
        finally:
            event.remove(conn, "before_cursor_execute", remember)
        return len(seen), data["total"]

    add(1)
    few = statements()
    add(4)
    many = statements()
    assert (few[1], many[1]) == (1, 5)
    assert many[0] == few[0]


# --- Summary -----------------------------------------------------------------------------


def test_summary_counts_today(client, frozen, freeze_now, owner, waiting, auth_headers):
    headers = auth_headers(owner)
    queue = [waiting(sessions=((DAY, time(8 + k), time(9 + k)),)) for k in range(6)]
    freeze_now(NOW - timedelta(days=1))
    approve(client, headers, queue[0])
    freeze_now(NOW)
    approve(client, headers, queue[1])
    approve(client, headers, queue[2])
    reject(client, headers, queue[3])
    assert summary(client, headers) == {"waiting": 2, "approved_today": 2, "rejected_today": 1}


def test_summary_day_is_phnom_penh(client, frozen, freeze_now, owner, waiting, auth_headers):
    headers = auth_headers(owner)
    late, early = waiting(), waiting(sessions=((DAY, time(14), time(15)),))
    freeze_now(datetime(2026, 11, 9, 23, 50))
    approve(client, headers, late)
    freeze_now(datetime(2026, 11, 10, 0, 30))
    assert summary(client, headers)["approved_today"] == 0
    approve(client, headers, early)
    assert summary(client, headers)["approved_today"] == 1
