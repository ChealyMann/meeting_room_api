"""Admin list of all bookings: spec B-32."""

from datetime import date, time, timedelta

import pytest

from app.constants.booking import BookingStatus
from tests.booking_helpers import DAY

LIST = "/api/v1/bookings"
NEXT_DAY = DAY + timedelta(days=1)
PAST_DAY = date(2026, 11, 6)  # before NOW (Monday Nov 9)


@pytest.fixture
def admin(make_user):
    return make_user(roles=["ADMIN"])


@pytest.fixture
def booking(make_user, make_bookable_room, make_booking):
    """A booking waiting for Pitika; `build(room=None, **options)`."""

    def build(room=None, **options):
        options.setdefault("status", BookingStatus.PENDING_PITIKA)
        return make_booking(room or make_bookable_room(), make_user(roles=["STAFF"]), **options)

    return build


def ids(client, headers, **params):
    response = client.get(LIST, params=params, headers=headers)
    assert response.status_code == 200, response.text
    return [item["id"] for item in response.json()["items"]]


def test_admin_sees_every_province(
    client, frozen, admin, booking, make_bookable_room, auth_headers
):
    here = booking()
    there = booking(make_bookable_room(province="SIEM_REAP"))
    data = client.get(LIST, headers=auth_headers(admin)).json()
    assert {item["id"] for item in data["items"]} == {here.id, there.id}
    assert data["total"] == 2


def test_province_filter(client, frozen, admin, booking, make_bookable_room, auth_headers):
    booking()
    there = booking(make_bookable_room(province="SIEM_REAP"))
    assert ids(client, auth_headers(admin), province="SIEM_REAP") == [there.id]


def test_status_filter_uses_display_status(client, frozen, admin, booking, auth_headers):
    ended = booking(status=BookingStatus.CONFIRMED, sessions=((PAST_DAY, time(9), time(10)),))
    coming = booking(status=BookingStatus.CONFIRMED)
    headers = auth_headers(admin)
    assert ids(client, headers, status="COMPLETED") == [ended.id]
    assert ids(client, headers, status="CONFIRMED") == [coming.id]


def test_bad_status_422(client, frozen, admin, auth_headers):
    response = client.get(LIST, params={"status": "NOPE"}, headers=auth_headers(admin))
    assert response.status_code == 422
    assert "status" in response.json()["error"]["fields"]


def test_from_to_match_any_session(client, frozen, admin, booking, auth_headers):
    far_day = NEXT_DAY + timedelta(days=5)
    two_days = booking(sessions=((DAY, time(9), time(10)), (far_day, time(9), time(10))))
    only_day = booking(sessions=((DAY, time(11), time(12)),))
    headers = auth_headers(admin)

    far = far_day.isoformat()
    assert ids(client, headers, **{"from": far, "to": far}) == [two_days.id]
    assert set(ids(client, headers, to=DAY.isoformat())) == {two_days.id, only_day.id}
    assert ids(client, headers, **{"from": NEXT_DAY.isoformat()}) == [two_days.id]


def test_from_after_to_422(client, frozen, admin, auth_headers):
    params = {"from": NEXT_DAY.isoformat(), "to": DAY.isoformat()}
    response = client.get(LIST, params=params, headers=auth_headers(admin))
    assert response.status_code == 422
    assert response.json()["error"]["fields"] == {"to": "Must be on or after from."}


def test_room_and_q(
    client, frozen, admin, booking, make_user, make_bookable_room, make_booking, auth_headers
):
    room = make_bookable_room()
    first = booking(room, meeting_title="Budget")
    second = booking(sessions=((NEXT_DAY, time(9), time(10)),))
    named = make_booking(make_bookable_room(), make_user(roles=["STAFF"], name_en="Sokha Chan"),
                         status=BookingStatus.PENDING_PITIKA)  # fmt: skip
    headers = auth_headers(admin)
    assert ids(client, headers, room_id=room.id) == [first.id]
    assert ids(client, headers, q="budg") == [first.id]
    assert ids(client, headers, q=second.reference_code) == [second.id]
    assert ids(client, headers, q="sokha") == [named.id]


def test_sorted_by_first_start(client, frozen, admin, booking, auth_headers):
    late = booking(sessions=((NEXT_DAY, time(9), time(10)),))
    early = booking(sessions=((DAY, time(14), time(15)), (NEXT_DAY, time(8), time(9))))
    assert ids(client, auth_headers(admin)) == [early.id, late.id]


@pytest.mark.parametrize("role", ["STAFF", "PITIKA", "ROOM_OWNER", "IT_LEAD"])
def test_not_admin_403(client, frozen, make_user, auth_headers, role):
    response = client.get(LIST, headers=auth_headers(make_user(roles=[role])))
    assert response.status_code == 403


def test_query_count_does_not_grow(
    client, frozen, conn, db_session, admin, make_user, make_bookable_room, make_booking,
    auth_headers,
):  # fmt: skip
    from sqlalchemy import event

    headers = auth_headers(admin)
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
