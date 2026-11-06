"""IT tickets: spec 9.14, 8.5, B-19, B-22, BR-IT-01..06, BR-APR-07."""

from datetime import time

import pytest
from sqlalchemy import event

from app.constants.booking import BookingStatus, ITStatus, ReviewDecision, ReviewStage
from app.models import BookingReview
from tests.booking_helpers import DAY, error, fields

URL = "/api/v1/it/tickets"


@pytest.fixture
def lead(make_user):
    return make_user(roles=["IT_LEAD"])


@pytest.fixture
def staff(make_user):
    return make_user(roles=["IT_STAFF"])


@pytest.fixture
def setup(make_user, make_bookable_room, make_booking):
    """A booking in IT setup; `build(**options)` returns it. Its ticket is `booking.it_ticket`."""

    def build(**options):
        options.setdefault("status", BookingStatus.SETUP_IN_PROGRESS)
        options.setdefault("forwarded", True)
        return make_booking(make_bookable_room(), make_user(roles=["STAFF"]), it=True, **options)

    return build


def assign(client, headers, booking, user_ids, **values):
    body = {"user_ids": user_ids, "version": booking.version, **values}
    return client.put(f"{URL}/{booking.it_ticket.id}/staff", json=body, headers=headers)


def ready(client, headers, booking, **values):
    body = {"version": booking.version, **values}
    return client.post(f"{URL}/{booking.it_ticket.id}/ready", json=body, headers=headers)


def ids(response):
    return [item["booking"]["id"] for item in response.json()["items"]]


# --- List --------------------------------------------------------------------------------


def test_not_listed_before_forward(client, frozen, lead, staff, setup, auth_headers):
    waiting = setup(status=BookingStatus.PENDING_PITIKA, forwarded=False)
    sent = setup()
    headers = auth_headers(lead)
    assert ids(client.get(URL, headers=headers)) == [sent.id]
    assert error(assign(client, headers, waiting, [staff.id])) == (404, "NOT_FOUND")
    assert error(ready(client, headers, waiting)) == (404, "NOT_FOUND")


def test_lead_sees_all_staff_sees_assigned(
    client, frozen, lead, staff, make_user, setup, auth_headers
):
    other = make_user(roles=["IT_STAFF"])
    mine = setup(assigned_staff=(staff,))
    theirs = setup(assigned_staff=(other,))
    unassigned = setup()
    seen = ids(client.get(URL, headers=auth_headers(lead)))
    assert sorted(seen) == sorted([mine.id, theirs.id, unassigned.id])
    assert ids(client.get(URL, headers=auth_headers(staff))) == [mine.id]
    both = make_user(roles=["IT_LEAD", "IT_STAFF"])
    assert len(ids(client.get(URL, headers=auth_headers(both)))) == 3


def test_other_roles_cannot_list(client, frozen, make_user, auth_headers):
    response = client.get(URL, headers=auth_headers(make_user(roles=["STAFF"])))
    assert error(response) == (403, "FORBIDDEN")


def test_hidden_after_cancel_and_reject(client, frozen, lead, setup, auth_headers):
    cancelled = setup(status=BookingStatus.CANCELLED)
    rejected = setup(status=BookingStatus.REJECTED)
    live = setup()
    confirmed = setup(status=BookingStatus.CONFIRMED)
    headers = auth_headers(lead)
    assert sorted(ids(client.get(URL, headers=headers))) == sorted([live.id, confirmed.id])
    for hidden in (cancelled, rejected):
        assert error(ready(client, headers, hidden)) == (404, "NOT_FOUND")


def test_staff_gets_404_on_unassigned_ticket(frozen, db_session, staff, setup):
    """The routes are for the IT Lead; the service still hides tickets from other people."""
    from app.errors import AppError
    from app.services import it_ticket
    from tests.booking_helpers import current_for

    booking = setup()
    with pytest.raises(AppError) as caught:
        it_ticket.mark_ready(
            db_session, current_for(db_session, staff), booking.it_ticket.id, booking.version
        )
    assert caught.value.status == 404


def test_list_filters_and_order(client, frozen, lead, staff, setup, auth_headers):
    late = setup(sessions=((DAY, time(14), time(15)),), meeting_title="Late class")
    early = setup(
        sessions=((DAY, time(9), time(10)),), meeting_title="Early class", assigned_staff=(staff,)
    )
    headers = auth_headers(lead)
    assert ids(client.get(URL, headers=headers)) == [early.id, late.id]
    assert ids(client.get(URL, params={"status": "ASSIGNED"}, headers=headers)) == [early.id]
    assert ids(client.get(URL, params={"q": "late"}, headers=headers)) == [late.id]
    assert ids(client.get(URL, params={"q": late.reference_code}, headers=headers)) == [late.id]
    bad = client.get(URL, params={"status": "NOPE"}, headers=headers)
    assert error(bad) == (422, "VALIDATION_ERROR")
    assert "status" in fields(bad)


def test_item_shape(client, frozen, lead, staff, setup, auth_headers):
    booking = setup(assigned_staff=(staff,))
    item = client.get(URL, headers=auth_headers(lead)).json()["items"][0]
    assert set(item) == {
        "id", "status", "items", "special_requirements", "technician_notes", "staff",
        "setup_date", "setup_time", "forwarded_at", "assigned_at", "ready_at", "missed",
        "review_notes", "booking",
    }  # fmt: skip
    assert item["id"] == booking.it_ticket.id
    assert item["booking"]["id"] == booking.id
    assert item["staff"] == [
        {
            "id": staff.id,
            "name_en": staff.name_en,
            "name_kh": staff.name_kh,
            "is_active": True,
            "avatar_url": None,
        }
    ]


def test_setup_time_30_min_before(client, frozen, lead, setup, auth_headers):
    setup(sessions=((DAY, time(9), time(10)),))
    item = client.get(URL, headers=auth_headers(lead)).json()["items"][0]
    assert (item["setup_date"], item["setup_time"]) == (DAY.isoformat(), "08:30")


def test_review_notes_shown(client, frozen, lead, setup, db_session, make_user, auth_headers):
    booking = setup()
    pitika = make_user(roles=["PITIKA"])
    for stage, decision, notes in (
        (ReviewStage.PITIKA, ReviewDecision.APPROVED, "Bring a spare cable."),
        (ReviewStage.OWNER, ReviewDecision.APPROVED, None),
        (ReviewStage.OWNER, ReviewDecision.NOT_REQUIRED, "ignored"),
    ):
        db_session.add(
            BookingReview(
                booking_id=booking.id, stage=stage, decision=decision, reviewer_id=pitika.id,
                notes=notes, reviewed_at=booking.created_at,
            )
        )  # fmt: skip
    db_session.flush()
    db_session.expire_all()
    item = client.get(URL, headers=auth_headers(lead)).json()["items"][0]
    assert item["review_notes"] == ["Bring a spare cable."]


def test_list_query_count_does_not_grow(
    client, frozen, conn, db_session, lead, staff, setup, auth_headers
):
    headers = auth_headers(lead)

    def add(n):
        for _ in range(n):
            setup(assigned_staff=(staff,))
        db_session.expire_all()

    def statements():
        seen = []

        def remember(*_args):
            seen.append(1)

        event.listen(conn, "before_cursor_execute", remember)
        try:
            response = client.get(URL, headers=headers)
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
    assert few[0] <= 15


# --- Assign (T10) ------------------------------------------------------------------------


def test_t10_assign(client, frozen, lead, staff, setup, auth_headers, db_session):
    booking = setup()
    response = assign(
        client, auth_headers(lead), booking, [staff.id], technician_notes="Laptop and HDMI."
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ASSIGNED"
    assert data["assigned_at"] is not None
    assert data["technician_notes"] == "Laptop and HDMI."
    assert [user["id"] for user in data["staff"]] == [staff.id]
    assert data["booking"]["version"] == 2
    db_session.expire_all()
    assert booking.version == 2
    assert booking.status == BookingStatus.SETUP_IN_PROGRESS


def test_assign_stale_version(client, frozen, lead, staff, setup, auth_headers):
    booking = setup()
    response = assign(client, auth_headers(lead), booking, [staff.id], version=booking.version + 5)
    assert error(response) == (409, "STALE_VERSION")


def test_assign_needs_active_it_staff(client, frozen, lead, staff, make_user, setup, auth_headers):
    booking = setup()
    headers = auth_headers(lead)
    only_staff = make_user(roles=["STAFF"])
    response = assign(client, headers, booking, [staff.id, only_staff.id])
    assert error(response) == (409, "INACTIVE_REFERENCE")
    assert fields(response)["user_ids"] == "This user is not active IT Staff."

    off = make_user(roles=["IT_STAFF"], is_active=False)
    assert error(assign(client, headers, booking, [off.id])) == (409, "INACTIVE_REFERENCE")

    response = assign(client, headers, booking, [staff.id, 999999])
    assert error(response) == (422, "VALIDATION_ERROR")
    assert "user_ids" in fields(response)
    assert error(assign(client, headers, booking, [])) == (422, "VALIDATION_ERROR")


def test_assign_technician_notes_refuse_html(client, frozen, lead, staff, setup, auth_headers):
    booking = setup()
    response = assign(
        client, auth_headers(lead), booking, [staff.id], technician_notes="<b>Bring cables</b>"
    )
    assert error(response) == (422, "VALIDATION_ERROR")
    assert "technician_notes" in fields(response)


def test_assign_wrong_state(client, frozen, lead, staff, setup, auth_headers):
    confirmed = setup(status=BookingStatus.CONFIRMED)
    assert error(assign(client, auth_headers(lead), confirmed, [staff.id])) == (
        409,
        "INVALID_TRANSITION",
    )


def test_reassign_replaces(client, frozen, lead, staff, make_user, setup, auth_headers):
    other = make_user(roles=["IT_STAFF"])
    booking = setup(assigned_staff=(staff,))
    response = assign(client, auth_headers(lead), booking, [other.id])
    assert response.status_code == 200
    assert [user["id"] for user in response.json()["staff"]] == [other.id]
    assert ids(client.get(URL, headers=auth_headers(staff))) == []
    assert ids(client.get(URL, headers=auth_headers(other))) == [booking.id]


# --- Ready (T11) -------------------------------------------------------------------------


def test_t11_ready_confirms(client, frozen, lead, staff, setup, auth_headers, db_session):
    booking = setup(assigned_staff=(staff,))
    response = ready(client, auth_headers(lead), booking)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "READY"
    assert data["ready_at"] is not None
    assert data["booking"]["status"] == "CONFIRMED"
    db_session.expire_all()
    assert booking.status == BookingStatus.CONFIRMED
    assert booking.door_pass is not None
    assert booking.it_ticket.status == ITStatus.READY
    assert booking.version == 2


def test_ready_before_assign(client, frozen, lead, setup, auth_headers):
    booking = setup()
    assert error(ready(client, auth_headers(lead), booking)) == (409, "INVALID_TRANSITION")


def test_ready_with_only_inactive_staff(client, frozen, lead, make_user, setup, auth_headers):
    off = make_user(roles=["IT_STAFF"], is_active=False)
    booking = setup(assigned_staff=(off,))
    response = ready(client, auth_headers(lead), booking)
    assert error(response) == (409, "INVALID_TRANSITION")
    assert response.json()["error"]["message"] == "Assign active IT Staff first."


def test_ready_with_one_inactive_one_active(
    client, frozen, lead, staff, make_user, setup, auth_headers
):
    off = make_user(roles=["IT_STAFF"], is_active=False)
    booking = setup(assigned_staff=(off, staff))
    assert ready(client, auth_headers(lead), booking).status_code == 200


def test_ready_when_the_staff_lost_the_it_staff_role(
    client, frozen, lead, make_user, setup, auth_headers
):
    """An active user who still holds IT_STAFF is needed: the role counts, not only is_active."""
    former = make_user(roles=["STAFF"])  # was IT Staff when assigned, lost the role since
    booking = setup(assigned_staff=(former,))
    response = ready(client, auth_headers(lead), booking)
    assert error(response) == (409, "INVALID_TRANSITION")
    assert response.json()["error"]["message"] == "Assign active IT Staff first."


def test_ready_stale_and_wrong_status(client, frozen, lead, staff, setup, auth_headers):
    headers = auth_headers(lead)
    booking = setup(assigned_staff=(staff,))
    assert error(ready(client, headers, booking, version=9)) == (409, "STALE_VERSION")
    done = setup(status=BookingStatus.CONFIRMED, assigned_staff=(staff,))
    assert error(ready(client, headers, done)) == (409, "INVALID_TRANSITION")


def test_staff_item_shows_inactive(client, frozen, lead, make_user, setup, auth_headers):
    off = make_user(roles=["IT_STAFF"], is_active=False)
    setup(assigned_staff=(off,))
    item = client.get(URL, headers=auth_headers(lead)).json()["items"][0]
    assert item["staff"][0]["is_active"] is False


def test_it_staff_cannot_change(client, frozen, staff, setup, auth_headers):
    booking = setup(assigned_staff=(staff,))
    headers = auth_headers(staff)
    assert error(assign(client, headers, booking, [staff.id])) == (403, "FORBIDDEN")
    assert error(ready(client, headers, booking)) == (403, "FORBIDDEN")
