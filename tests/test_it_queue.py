"""IT setup queue for the dashboard: states (missed on done), setup-day range, mine, the
summary and the IT staff list (spec docs/superpowers/specs/2026-11-05-owner-and-it-pages-design.md,
Part B)."""

from datetime import date, datetime, time, timedelta

import pytest
from sqlalchemy import event

from app.constants.booking import BookingStatus, ITStatus
from tests.booking_helpers import DAY, NOW

URL = "/api/v1/it/tickets"
SUMMARY = f"{URL}/summary"
STAFF = "/api/v1/it/staff"


@pytest.fixture
def lead(make_user):
    return make_user(roles=["IT_LEAD"])


@pytest.fixture
def staff(make_user):
    return make_user(roles=["IT_STAFF"], name_en="Sok Pisey")


@pytest.fixture
def setup(make_user, make_bookable_room, make_booking, db_session):
    """`build(state="RECEIVED", day=DAY, start=9, staff=(), ready_at=None, sessions=None,
    **options)`: a booking in IT setup whose ticket is in `state`; one session on `day` at
    `start`, or the given `sessions`."""

    def build(
        state=ITStatus.RECEIVED, day=DAY, start=9, staff=(), ready_at=None, sessions=None, **options
    ):
        options.setdefault("status", BookingStatus.SETUP_IN_PROGRESS)
        booking = make_booking(
            make_bookable_room(), make_user(roles=["STAFF"]), it=True, forwarded=True,
            sessions=sessions or ((day, time(start), time(start + 1)),), **options,
        )  # fmt: skip
        ticket = booking.it_ticket
        ticket.status = state
        ticket.staff.extend(staff)
        if state != ITStatus.RECEIVED:
            ticket.assigned_at = datetime(2026, 11, 8, 1, 0)
        ticket.ready_at = ready_at
        db_session.commit()
        return booking

    return build


def listed(client, headers, **params):
    response = client.get(URL, params=params, headers=headers)
    assert response.status_code == 200, response.json()
    return response.json()


def ids(data):
    return [item["booking"]["id"] for item in data["items"]]


# --- States ------------------------------------------------------------------------------


def test_states_split_the_tickets(client, frozen, lead, staff, setup, auth_headers):
    headers = auth_headers(lead)
    received = setup()
    assigned = setup(ITStatus.ASSIGNED, staff=[staff])
    done = setup(ITStatus.READY, staff=[staff], ready_at=datetime(2026, 11, 9, 0, 30),
                 status=BookingStatus.CONFIRMED)  # fmt: skip
    assert ids(listed(client, headers, state="to_assign")) == [received.id]
    assert ids(listed(client, headers, state="in_progress")) == [assigned.id]
    assert ids(listed(client, headers, state="done")) == [done.id]


def test_missed_moves_to_done(client, frozen, freeze_now, lead, staff, setup, auth_headers):
    headers = auth_headers(lead)
    today = NOW.date()
    late = setup(day=today, start=9)  # still SETUP_IN_PROGRESS: the expiry job has not run
    confirmed = setup(ITStatus.ASSIGNED, day=today, start=9, staff=[staff],
                      status=BookingStatus.CONFIRMED)  # fmt: skip
    future = setup(day=DAY)
    freeze_now(datetime(2026, 11, 9, 9, 15))

    assert ids(listed(client, headers, state="to_assign")) == [future.id]
    assert listed(client, headers, state="in_progress")["items"] == []
    done = listed(client, headers, state="done")
    assert set(ids(done)) == {late.id, confirmed.id}
    assert all(item["missed"] for item in done["items"])
    assert listed(client, headers, state="to_assign")["items"][0]["missed"] is False


def test_done_newest_first(client, frozen, freeze_now, lead, staff, setup, auth_headers):
    headers = auth_headers(lead)
    today = NOW.date()
    older = setup(ITStatus.READY, staff=[staff], ready_at=datetime(2026, 11, 9, 0, 0),
                  status=BookingStatus.CONFIRMED)  # fmt: skip
    newer = setup(ITStatus.READY, staff=[staff], ready_at=datetime(2026, 11, 9, 3, 0),
                  status=BookingStatus.CONFIRMED)  # fmt: skip
    missed = setup(day=today, start=8)  # started 08:00 local = 01:00 UTC
    freeze_now(datetime(2026, 11, 9, 12, 0))
    assert ids(listed(client, headers, state="done")) == [newer.id, missed.id, older.id]


def test_mine_only_my_tickets(client, frozen, make_user, staff, setup, auth_headers):
    both = make_user(roles=["IT_LEAD", "IT_STAFF"])
    mine = setup(ITStatus.ASSIGNED, staff=[both])
    other = setup(ITStatus.ASSIGNED, staff=[staff])
    headers = auth_headers(both)
    assert ids(listed(client, headers, state="in_progress", mine="true")) == [mine.id]
    assert set(ids(listed(client, headers, state="in_progress"))) == {mine.id, other.id}


def test_from_to_by_first_day(client, frozen, lead, setup, auth_headers):
    headers = auth_headers(lead)
    near = setup(day=DAY)
    far = setup(day=DAY + timedelta(days=3))
    assert ids(listed(client, headers, **{"from": str(DAY + timedelta(days=1))})) == [far.id]
    assert ids(listed(client, headers, to=str(DAY))) == [near.id]
    params = {"from": str(DAY), "to": str(DAY - timedelta(days=1))}
    response = client.get(URL, params=params, headers=headers)
    assert response.status_code == 422
    assert "to" in response.json()["error"]["fields"]


def test_bad_state_is_422(client, frozen, lead, auth_headers):
    response = client.get(URL, params={"state": "later"}, headers=auth_headers(lead))
    assert response.status_code == 422


def test_query_count_does_not_grow(
    client, frozen, conn, db_session, lead, staff, setup, auth_headers
):
    headers = auth_headers(lead)

    def add(n):
        for k in range(n):
            setup(ITStatus.READY, staff=[staff], ready_at=datetime(2026, 11, 9, 0, k),
                  status=BookingStatus.CONFIRMED)  # fmt: skip
        db_session.expire_all()

    def statements():
        seen = []

        def remember(*_args):
            seen.append(1)

        event.listen(conn, "before_cursor_execute", remember)
        try:
            data = listed(client, headers, state="done")
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


def test_summary_counts(client, frozen, freeze_now, lead, staff, setup, auth_headers):
    today = date(2026, 11, 9)
    setup(day=today, start=15)  # to assign, due today
    setup(day=DAY)  # to assign, tomorrow
    setup(day=today, start=8)  # missed by 09:00: not "to assign", still due today
    setup(ITStatus.ASSIGNED, day=DAY, staff=[staff])  # in progress
    setup(ITStatus.READY, day=today, start=16, staff=[staff], ready_at=datetime(2026, 11, 9, 1, 30),
          status=BookingStatus.CONFIRMED)  # fmt: skip
    setup(ITStatus.READY, day=DAY, staff=[staff], ready_at=datetime(2026, 11, 8, 3, 0),
          status=BookingStatus.CONFIRMED)  # fmt: skip
    freeze_now(datetime(2026, 11, 9, 9, 0))
    response = client.get(SUMMARY, headers=auth_headers(lead))
    assert response.json() == {
        "to_assign": 2,
        "in_progress": 1,
        "ready_today": 1,
        "due_today": 3,
        "due_today_ready": 1,
    }


def test_summary_and_staff_lead_only(client, frozen, staff, as_staff, auth_headers):
    for headers in (auth_headers(staff), as_staff):
        assert client.get(SUMMARY, headers=headers).status_code == 403
        assert client.get(STAFF, headers=headers).status_code == 403


def test_staff_list_active_it_staff_by_name(client, frozen, lead, make_user, auth_headers):
    make_user(roles=["IT_STAFF"], name_en="Vann Dara")
    make_user(roles=["IT_STAFF"], name_en="Chan Bopha")
    make_user(roles=["IT_STAFF"], name_en="Gone User", is_active=False)
    make_user(roles=["STAFF"], name_en="Not IT")
    data = client.get(STAFF, headers=auth_headers(lead)).json()
    assert [user["name_en"] for user in data["items"]] == ["Chan Bopha", "Vann Dara"]
    assert all(user["is_active"] for user in data["items"])


def test_staff_list_photo_and_setups_that_day(
    client, frozen, lead, staff, make_user, setup, db_session, auth_headers
):
    """The assign picker: each person's photo, and with `day` how many setups they already
    have that day (cancelled bookings and other days left out); null without `day`."""
    other = make_user(roles=["IT_STAFF"], name_en="Vann Dara")
    staff.user_avatar = "photo.jpg"
    db_session.commit()
    setup(ITStatus.ASSIGNED, staff=[staff])
    setup(ITStatus.READY, staff=[staff, other], start=13)
    setup(ITStatus.ASSIGNED, staff=[staff], day=DAY + timedelta(days=1))
    setup(ITStatus.ASSIGNED, staff=[other], status=BookingStatus.CANCELLED)
    headers = auth_headers(lead)

    data = client.get(STAFF, params={"day": str(DAY)}, headers=headers).json()
    rows = {user["name_en"]: user for user in data["items"]}
    assert rows["Sok Pisey"]["avatar_url"] == f"/api/v1/users/{staff.id}/avatar"
    assert rows["Vann Dara"]["avatar_url"] is None
    assert (rows["Sok Pisey"]["setups_that_day"], rows["Vann Dara"]["setups_that_day"]) == (2, 1)

    plain = client.get(STAFF, headers=headers).json()["items"]
    assert all(user["setups_that_day"] is None for user in plain)


def test_staff_list_busy_at_the_same_time(
    client, frozen, lead, staff, make_user, setup, auth_headers
):
    """With `ticket_id`: each person's other setups whose time (set-up to meeting start)
    overlaps this one, and the day's count for that ticket's day. Cancelled bookings, other
    times and the ticket itself are left out; unknown tickets are 404."""
    other = make_user(roles=["IT_STAFF"], name_en="Vann Dara")
    target = setup(staff=[staff])
    clash = setup(ITStatus.ASSIGNED, staff=[staff])
    setup(ITStatus.ASSIGNED, staff=[staff, other], start=10)
    setup(ITStatus.ASSIGNED, staff=[other], status=BookingStatus.CANCELLED)
    headers = auth_headers(lead)

    params = {"ticket_id": target.it_ticket.id}
    rows = {
        u["name_en"]: u for u in client.get(STAFF, params=params, headers=headers).json()["items"]
    }
    assert rows["Sok Pisey"]["busy"] == [
        {
            "ticket_id": clash.it_ticket.id,
            "room_name_en": clash.room.name_en,
            "date": str(DAY),
            "setup_time": "08:30",
            "meeting_start": "09:00",
        }
    ]
    assert rows["Vann Dara"]["busy"] == []
    assert (rows["Sok Pisey"]["setups_that_day"], rows["Vann Dara"]["setups_that_day"]) == (3, 1)

    plain = client.get(STAFF, headers=headers).json()["items"]
    assert all(user["busy"] is None for user in plain)
    missing = client.get(STAFF, params={"ticket_id": 999999}, headers=headers)
    assert missing.status_code == 404


# --- IT at every session (owner decision, 6 Nov 2026: like food; assign once, ready once) ----

THREE_DAYS = ((DAY, time(9), time(10)), (DAY + timedelta(days=1), time(14), time(15)),
              (DAY + timedelta(days=2), time(9), time(10)))  # fmt: skip


def test_item_lists_a_setup_for_every_session(client, frozen, lead, setup, auth_headers):
    setup(sessions=THREE_DAYS)
    item = listed(client, auth_headers(lead), state="to_assign")["items"][0]
    assert item["setups"] == [
        {"session_number": 1, "date": str(DAY), "setup_time": "08:30",
         "start_time": "09:00", "end_time": "10:00"},
        {"session_number": 2, "date": str(DAY + timedelta(days=1)), "setup_time": "13:30",
         "start_time": "14:00", "end_time": "15:00"},
        {"session_number": 3, "date": str(DAY + timedelta(days=2)), "setup_time": "08:30",
         "start_time": "09:00", "end_time": "10:00"},
    ]  # fmt: skip


def test_in_progress_keeps_a_ready_setup_while_sessions_remain(
    client, frozen, freeze_now, lead, staff, setup, auth_headers
):
    """Made ready once (the booking is confirmed), but staff still set up the later sessions:
    it stays In progress until its last session starts."""
    headers = auth_headers(lead)
    later = setup(ITStatus.READY, staff=[staff], ready_at=datetime(2026, 11, 9, 1, 0),
                  sessions=THREE_DAYS, status=BookingStatus.CONFIRMED)  # fmt: skip
    one_day = setup(ITStatus.READY, staff=[staff], ready_at=datetime(2026, 11, 9, 1, 0),
                    status=BookingStatus.CONFIRMED)  # fmt: skip
    assert ids(listed(client, headers, state="in_progress")) == [later.id]
    assert set(ids(listed(client, headers, state="done"))) == {later.id, one_day.id}

    freeze_now(datetime(2026, 11, 12, 9, 30))  # the last session has started
    assert ids(listed(client, headers, state="in_progress")) == []


def test_from_to_match_any_session_day(client, frozen, lead, setup, auth_headers):
    booking = setup(sessions=THREE_DAYS)
    on = {"from": str(DAY + timedelta(days=2)), "to": str(DAY + timedelta(days=2))}
    assert ids(listed(client, auth_headers(lead), **on)) == [booking.id]


def test_staff_busy_and_counts_see_every_session(client, frozen, lead, staff, setup, auth_headers):
    """Another booking's second session at the same time as this one's setup is a clash, and
    every session is counted on its own day."""
    target = setup(day=DAY + timedelta(days=1), start=14)
    other = setup(ITStatus.ASSIGNED, staff=[staff], sessions=THREE_DAYS)
    rows = client.get(STAFF, params={"ticket_id": target.it_ticket.id},
                      headers=auth_headers(lead)).json()["items"]  # fmt: skip
    me = next(u for u in rows if u["id"] == staff.id)
    assert me["busy"] == [
        {"ticket_id": other.it_ticket.id, "room_name_en": other.room.name_en,
         "date": str(DAY + timedelta(days=1)), "setup_time": "13:30", "meeting_start": "14:00"}
    ]  # fmt: skip
    assert me["setups_that_day"] == 1
