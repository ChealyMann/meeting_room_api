"""Food list: spec 9.12, B-12, B-25. Food is served at every session of a booking (owner
decision, 6 Nov 2026): each session on the day is a delivery."""

from datetime import time, timedelta

import pytest

from app.constants.booking import BookingStatus
from tests.booking_helpers import DAY, error

URL = "/api/v1/pitika/catering"
NEXT_DAY = DAY + timedelta(days=1)


@pytest.fixture
def pitika(make_pitika):
    return make_pitika(province="PHNOM_PENH")


@pytest.fixture
def order(make_user, make_bookable_room, make_booking):
    """A booking with food in a Phnom Penh room; `build(room=None, **options)`."""

    def build(room=None, **options):
        options.setdefault("status", BookingStatus.CONFIRMED)
        options.setdefault("catering", True)
        return make_booking(room or make_bookable_room(), make_user(roles=["STAFF"]), **options)

    return build


def ids(client, headers, **params):
    response = client.get(URL, params=params, headers=headers)
    assert response.status_code == 200
    return [item["booking_id"] for item in response.json()["items"]]


def test_food_list_day_and_status(client, frozen, pitika, order, auth_headers):
    headers = auth_headers(pitika)
    confirmed = order()
    setup = order(status=BookingStatus.SETUP_IN_PROGRESS, it=True, forwarded=True,
                  sessions=((DAY, time(8), time(9)),))  # fmt: skip
    order(status=BookingStatus.PENDING_PITIKA)
    order(status=BookingStatus.PENDING_OWNER)
    order(status=BookingStatus.REJECTED)
    order(status=BookingStatus.CANCELLED)
    order(catering=False)
    order(sessions=((NEXT_DAY, time(9), time(10)),))
    first_on_day = order(sessions=((DAY, time(13), time(14)), (NEXT_DAY, time(9), time(10))))
    # A later session on the day counts too: food comes at every session.
    later_on_day = order(
        sessions=((NEXT_DAY - timedelta(days=2), time(9), time(10)), (DAY, time(15), time(16)))
    )
    order(sessions=((NEXT_DAY, time(9), time(10)), (DAY + timedelta(days=2), time(9), time(10))))

    assert ids(client, headers, date=DAY.isoformat()) == [
        setup.id, confirmed.id, first_on_day.id, later_on_day.id
    ]  # fmt: skip
    assert ids(client, headers, date=(DAY + timedelta(days=9)).isoformat()) == []


def test_food_list_default_date_is_today(client, freeze_now, pitika, order, auth_headers):
    from datetime import datetime

    freeze_now(datetime(2026, 11, 10, 7, 0))
    today = order()
    order(sessions=((NEXT_DAY, time(9), time(10)),))
    assert ids(client, auth_headers(pitika)) == [today.id]


def test_food_list_sorted_by_time_then_room(
    client, frozen, pitika, order, make_bookable_room, auth_headers
):
    zebra = make_bookable_room(name_en="Zebra room")
    alpha = make_bookable_room(name_en="Alpha room")
    late = order(sessions=((DAY, time(14), time(15)),))
    in_zebra = order(zebra, sessions=((DAY, time(9), time(10)),))
    in_alpha = order(alpha, sessions=((DAY, time(9), time(10)),))
    assert ids(client, auth_headers(pitika), date=DAY.isoformat()) == [
        in_alpha.id,
        in_zebra.id,
        late.id,
    ]


def test_food_list_item_shape(client, frozen, pitika, order, make_user, auth_headers):
    approver = make_user(roles=["PITIKA"])
    booking = order(meeting_title="Board", food_approved_by=approver, attendees=12)
    booking.catering_order.packages = [{"id": 1, "name": "Lunch box"}]
    booking.catering_order.remarks = "No pork"
    booking.catering_order.approver_notes = "Serve at 11:45"
    item = client.get(URL, params={"date": DAY.isoformat()}, headers=auth_headers(pitika)).json()
    assert item["total"] == 1
    item = item["items"][0]
    assert set(item) == {
        "booking_id", "reference_code", "booking_status", "room", "meeting_title",
        "delivery_date", "delivery_time", "servings", "packages", "remarks", "approver_notes",
        "session_number", "session_count",
    }  # fmt: skip
    assert item["booking_id"] == booking.id
    assert item["reference_code"] == booking.reference_code
    assert item["booking_status"] == "CONFIRMED"
    assert item["room"]["id"] == booking.room_id
    assert item["room"]["province"]["code"] == "PHNOM_PENH"
    assert (item["meeting_title"], item["servings"]) == ("Board", 12)
    assert (item["delivery_date"], item["delivery_time"]) == (DAY.isoformat(), "09:00")
    assert item["packages"] == [{"id": 1, "name": "Lunch box"}]
    assert (item["remarks"], item["approver_notes"]) == ("No pork", "Serve at 11:45")
    assert (item["session_number"], item["session_count"]) == (1, 1)


def test_food_at_every_session(client, frozen, pitika, order, auth_headers):
    """A 3-day training: one delivery on each day at that session's start, saying which
    session it is; two sessions on one day are two deliveries."""
    headers = auth_headers(pitika)
    third = DAY + timedelta(days=2)
    booking = order(sessions=(
        (DAY, time(8), time(10)), (NEXT_DAY, time(13), time(15)),
        (third, time(8), time(10)), (third, time(14), time(16)),
    ))  # fmt: skip

    def deliveries(day):
        data = client.get(URL, params={"date": day.isoformat()}, headers=headers).json()
        keys = ("booking_id", "delivery_date", "delivery_time", "session_number", "session_count")
        return [tuple(i[k] for k in keys) for i in data["items"]]

    assert deliveries(DAY) == [(booking.id, DAY.isoformat(), "08:00", 1, 4)]
    assert deliveries(NEXT_DAY) == [(booking.id, NEXT_DAY.isoformat(), "13:00", 2, 4)]
    assert deliveries(third) == [
        (booking.id, third.isoformat(), "08:00", 3, 4),
        (booking.id, third.isoformat(), "14:00", 4, 4),
    ]


def test_food_list_private_title_not_masked(
    client, frozen, pitika, order, make_bookable_room, auth_headers
):
    booking = order(make_bookable_room(private=True), meeting_title="Secret plan")
    data = client.get(URL, params={"date": DAY.isoformat()}, headers=auth_headers(pitika)).json()
    assert data["items"][0]["booking_id"] == booking.id
    assert data["items"][0]["meeting_title"] == "Secret plan"


def test_food_list_servings_follow_attendees(
    client, frozen, db_session, pitika, order, auth_headers
):
    booking = order(attendees=5)
    headers = auth_headers(pitika)
    first = client.get(URL, params={"date": DAY.isoformat()}, headers=headers).json()
    assert first["items"][0]["servings"] == 5
    booking.attendees = 9
    db_session.flush()
    second = client.get(URL, params={"date": DAY.isoformat()}, headers=headers).json()
    assert second["items"][0]["servings"] == 9


def test_pitika_sees_only_own_province(
    client, frozen, pitika, order, make_bookable_room, auth_headers
):
    mine = order()
    order(make_bookable_room(province="SIEM_REAP"))
    assert ids(client, auth_headers(pitika), date=DAY.isoformat()) == [mine.id]


def test_pitika_without_province_sees_nothing(client, frozen, make_user, order, auth_headers):
    order()
    nobody = auth_headers(make_user(roles=["PITIKA"]))
    assert ids(client, nobody, date=DAY.isoformat()) == []


def test_admin_sees_all_provinces(client, frozen, order, make_bookable_room, as_admin):
    here = order()
    there = order(make_bookable_room(province="SIEM_REAP"))
    assert set(ids(client, as_admin, date=DAY.isoformat())) == {here.id, there.id}


def test_staff_forbidden_and_bad_date(client, frozen, as_staff, pitika, auth_headers):
    assert error(client.get(URL, headers=as_staff)) == (403, "FORBIDDEN")
    response = client.get(URL, params={"date": "nope"}, headers=auth_headers(pitika))
    assert response.status_code == 422
