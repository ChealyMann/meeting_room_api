"""Pitika decided list and today's summary
(spec docs/superpowers/specs/2026-11-05-pitika-decided-design.md). Since 17 Nov 2026 (owner, weak
spot 1 of "Working Together in the Same Role") they hold every Pitika-stage decision in the
province, each with who decided, not only my own."""

from datetime import datetime, time, timedelta

import pytest
from sqlalchemy import event

from app.constants.booking import BookingRoute, BookingStatus, ReviewDecision, ReviewStage
from app.models import BookingReview
from tests.booking_helpers import DAY, NOW

LIST = "/api/v1/pitika/bookings"
DECIDED = f"{LIST}/decided"


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
def pitika(make_pitika):
    return make_pitika(province="PHNOM_PENH")


@pytest.fixture
def pending(make_user, make_bookable_room, make_booking):
    """A booking waiting for Pitika in a Phnom Penh room; `build(room=None, **options)`."""

    def build(room=None, **options):
        options.setdefault("status", BookingStatus.PENDING_PITIKA)
        return make_booking(room or make_bookable_room(), make_user(roles=["STAFF"]), **options)

    return build


def decided(client, headers, decision="APPROVED", **params):
    response = client.get(DECIDED, params={"decision": decision, **params}, headers=headers)
    assert response.status_code == 200, response.json()
    return response.json()


def ids(data):
    return [item["id"] for item in data["items"]]


# --- List --------------------------------------------------------------------------------


def test_lists_my_approvals_newest_first(client, frozen, freeze_now, pitika, pending, auth_headers):
    headers = auth_headers(pitika)
    first, second = pending(), pending(sessions=((DAY, time(14), time(15)),))
    approve(client, headers, first, notes="Fine")
    freeze_now(NOW + timedelta(hours=1))
    approve(client, headers, second)

    data = decided(client, headers)
    assert ids(data) == [second.id, first.id]
    assert data["total"] == 2
    newest, oldest = data["items"]
    # NOW is 08:00 in Phnom Penh (UTC+7): one hour later is 02:00 UTC.
    assert newest["decided_at"] == "2026-11-09T02:00:00Z"
    assert (newest["decision_note"], oldest["decision_note"]) == (None, "Fine")
    me = {"id": pitika.id, "name_en": pitika.name_en}
    assert (newest["decided_by"], newest["by_admin"]) == (me, False)


def test_lists_my_rejections_with_reason(client, frozen, pitika, pending, auth_headers):
    headers = auth_headers(pitika)
    booking = pending()
    reject(client, headers, booking, reason="Room is not free.")

    data = decided(client, headers, "REJECTED")
    assert ids(data) == [booking.id]
    assert data["items"][0]["decision_note"] == "Room is not free."
    assert data["items"][0]["display_status"] == "REJECTED"
    assert decided(client, headers, "APPROVED")["items"] == []


def test_lists_other_pitikas_and_admin_backups_with_who_decided(
    client, frozen, db_session, pitika, pending, make_pitika, make_user, auth_headers
):
    other = make_pitika(province="PHNOM_PENH")
    by_other = pending()
    approve(client, auth_headers(other), by_other)
    # The Admin decided for Pitika as a backup (B-34): saved under the Admin's id.
    admin = make_user(roles=["ADMIN"])
    backup = pending(status=BookingStatus.CONFIRMED)
    db_session.add(
        BookingReview(
            booking_id=backup.id,
            stage=ReviewStage.PITIKA,
            decision=ReviewDecision.APPROVED,
            reviewer_id=admin.id,
            reviewed_at=datetime(2026, 11, 9, 0, 30),
            by_admin=True,
        )
    )
    db_session.commit()

    data = decided(client, auth_headers(pitika))
    assert ids(data) == [by_other.id, backup.id]
    who = [(item["decided_by"]["name_en"], item["by_admin"]) for item in data["items"]]
    assert who == [(other.name_en, False), (admin.name_en, True)]


def test_room_owner_decisions_are_not_pitika_decisions(
    client, frozen, db_session, pitika, pending, auth_headers
):
    booking = pending(status=BookingStatus.CONFIRMED)
    db_session.add(
        BookingReview(
            booking_id=booking.id,
            stage=ReviewStage.OWNER,
            decision=ReviewDecision.APPROVED,
            reviewer_id=pitika.id,
            reviewed_at=datetime(2026, 11, 9, 0, 30),
        )
    )
    db_session.commit()
    assert decided(client, auth_headers(pitika))["items"] == []


def test_approved_then_owner_rejected_stays_on_approved(
    client, frozen, pitika, pending, make_user, make_bookable_room, auth_headers
):
    owner = make_user(roles=["ROOM_OWNER"])
    booking = pending(make_bookable_room(private=True, owner=owner), route=BookingRoute.R2)
    after = approve(client, auth_headers(pitika), booking)
    assert after["status"] == "PENDING_OWNER"
    response = client.post(
        f"/api/v1/owner/bookings/{booking.id}/reject",
        json={"version": after["version"], "reason": "Room is not free."},
        headers=auth_headers(owner),
    )
    assert response.status_code == 200, response.json()

    headers = auth_headers(pitika)
    data = decided(client, headers, "APPROVED")
    assert ids(data) == [booking.id]
    assert data["items"][0]["display_status"] == "REJECTED"
    assert decided(client, headers, "REJECTED")["items"] == []


def test_only_current_province(
    client, frozen, db_session, pitika, pending, make_user, make_division, make_department,
    make_location, auth_headers,
):  # fmt: skip
    approve(client, auth_headers(pitika), pending())
    # The Pitika moves to an office in Siem Reap: Phnom Penh decisions are no longer listed.
    pitika.division = make_division(make_department(make_location(province="SIEM_REAP")))
    db_session.commit()
    assert decided(client, auth_headers(pitika))["total"] == 0

    nobody = make_user(roles=["PITIKA"])
    data = decided(client, auth_headers(nobody))
    assert (data["items"], data["total"]) == ([], 0)


def test_filters(
    client, frozen, pitika, pending, make_user, make_bookable_room, make_booking, auth_headers
):
    headers = auth_headers(pitika)
    room = make_bookable_room()
    asked = make_user(roles=["STAFF"], name_en="Sokha Chan")
    budget = make_booking(room, asked, status=BookingStatus.PENDING_PITIKA,
                          meeting_title="Budget review")  # fmt: skip
    later = pending(sessions=((DAY + timedelta(days=3), time(9), time(10)),))
    for booking in (budget, later):
        approve(client, headers, booking)

    def found(**params):
        return set(ids(decided(client, headers, **params)))

    assert found(q="budg") == {budget.id}
    assert found(q="sokha") == {budget.id}
    assert found(q=later.reference_code) == {later.id}
    assert found(room_id=room.id) == {budget.id}
    assert found(**{"from": str(DAY + timedelta(days=1))}) == {later.id}
    assert found(to=str(DAY)) == {budget.id}
    response = client.get(
        DECIDED,
        params={"decision": "APPROVED", "from": str(DAY), "to": str(DAY - timedelta(days=1))},
        headers=headers,
    )
    assert response.status_code == 422
    assert "to" in response.json()["error"]["fields"]


def test_decision_required_and_checked(client, frozen, pitika, auth_headers):
    headers = auth_headers(pitika)
    assert client.get(DECIDED, headers=headers).status_code == 422
    response = client.get(DECIDED, params={"decision": "NOT_REQUIRED"}, headers=headers)
    assert response.status_code == 422


def test_staff_and_admin_forbidden(client, frozen, as_staff, as_admin):
    for headers in (as_staff, as_admin):
        response = client.get(DECIDED, params={"decision": "APPROVED"}, headers=headers)
        assert response.status_code == 403


def test_query_count_does_not_grow(
    client, frozen, conn, db_session, pitika, make_user, make_bookable_room, make_booking,
    auth_headers,
):  # fmt: skip
    headers = auth_headers(pitika)
    booker = make_user(roles=["STAFF"])

    def add(n):
        for _ in range(n):
            booking = make_booking(
                make_bookable_room(),
                booker,
                status=BookingStatus.PENDING_PITIKA,
                catering=True,
                it=True,
            )
            approve(client, headers, booking, notes="Fine")
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

SUMMARY = f"{LIST}/summary"


def summary(client, headers):
    response = client.get(SUMMARY, headers=headers)
    assert response.status_code == 200, response.json()
    return response.json()


def test_summary_counts_today(
    client, frozen, freeze_now, pitika, pending, make_bookable_room, auth_headers
):
    headers = auth_headers(pitika)
    waiting = [pending() for _ in range(6)]
    pending(make_bookable_room(province="SIEM_REAP"))
    freeze_now(NOW - timedelta(days=1))
    approve(client, headers, waiting[0])
    freeze_now(NOW)
    approve(client, headers, waiting[1])
    approve(client, headers, waiting[2])
    reject(client, headers, waiting[3])
    assert summary(client, headers) == {"waiting": 2, "approved_today": 2, "rejected_today": 1}


def test_summary_day_is_phnom_penh(client, frozen, freeze_now, pitika, pending, auth_headers):
    headers = auth_headers(pitika)
    late, early = pending(), pending()
    freeze_now(datetime(2026, 11, 9, 23, 50))  # 16:50 UTC, still the 9th in Phnom Penh
    approve(client, headers, late)
    freeze_now(datetime(2026, 11, 10, 0, 30))  # 17:30 UTC on the 9th, but the 10th here
    assert summary(client, headers)["approved_today"] == 0
    approve(client, headers, early)
    assert summary(client, headers)["approved_today"] == 1


def test_summary_counts_the_whole_province(
    client, frozen, db_session, pitika, pending, make_pitika, make_user, auth_headers
):
    """Other Pitikas and Admin backups count too, like the decided lists."""
    approve(client, auth_headers(make_pitika(province="PHNOM_PENH")), pending())
    backup = pending(status=BookingStatus.CONFIRMED)
    db_session.add(
        BookingReview(
            booking_id=backup.id,
            stage=ReviewStage.PITIKA,
            decision=ReviewDecision.APPROVED,
            reviewer_id=make_user(roles=["ADMIN"]).id,
            reviewed_at=datetime(2026, 11, 9, 1, 0),
            by_admin=True,
        )
    )
    db_session.commit()
    assert summary(client, auth_headers(pitika)) == {
        "waiting": 0,
        "approved_today": 2,
        "rejected_today": 0,
    }


def test_summary_without_province_is_zero(client, frozen, make_user, pending, auth_headers):
    pending()
    nobody = make_user(roles=["PITIKA"])
    assert summary(client, auth_headers(nobody)) == {
        "waiting": 0,
        "approved_today": 0,
        "rejected_today": 0,
    }


def test_summary_forbidden_for_staff(client, frozen, as_staff):
    assert client.get(SUMMARY, headers=as_staff).status_code == 403
