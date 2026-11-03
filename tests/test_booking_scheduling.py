"""Scheduling rules (spec 8.2): shapes, room, route, clashes, warnings, steps."""

from datetime import date, datetime, time, timedelta
from types import SimpleNamespace

import pytest

from app.constants.booking import BookingRoute, BookingStatus, BookingStep
from app.errors import AppError, ErrorCode
from app.services import booking_scheduling as scheduling
from tests.booking_helpers import DAY, NOW, current_for

TODAY = date(2026, 11, 9)


def s(day, start, end):
    return SimpleNamespace(date=day, start_time=start, end_time=end)


def one(start=time(9), end=time(10), day=DAY):
    return [s(day, start, end)]


def refused(call, *args, **kwargs):
    """The AppError raised by `call(...)`."""
    with pytest.raises(AppError) as caught:
        call(*args, **kwargs)
    return caught.value


# --- Shapes ----------------------------------------------------------------------------


def test_valid_shape_passes(settings):
    scheduling.check_session_shapes(one(), settings, TODAY)


def test_no_sessions(settings):
    error = refused(scheduling.check_session_shapes, [], settings, TODAY)
    assert (error.status, error.code) == (422, ErrorCode.VALIDATION_ERROR)
    assert error.fields == {"sessions": "Add 1 to 20 sessions."}


def test_21_sessions(settings):
    sessions = [s(DAY + timedelta(days=i), time(9), time(10)) for i in range(21)]
    error = refused(scheduling.check_session_shapes, sessions, settings, TODAY)
    assert error.fields == {"sessions": "Add 1 to 20 sessions."}


def test_20_sessions_ok(settings):
    sessions = [s(DAY + timedelta(days=i), time(9), time(10)) for i in range(20)]
    scheduling.check_session_shapes(sessions, settings, TODAY)


def test_end_before_start(settings):
    error = refused(scheduling.check_session_shapes, one(time(10), time(9)), settings, TODAY)
    assert error.fields == {"sessions.0.end_time": "End must be after start."}


def test_end_equal_start(settings):
    error = refused(scheduling.check_session_shapes, one(time(9), time(9)), settings, TODAY)
    assert error.fields == {"sessions.0.end_time": "End must be after start."}


def test_14_minutes_refused_15_ok(settings):
    error = refused(scheduling.check_session_shapes, one(time(9), time(9, 14)), settings, TODAY)
    assert error.fields == {"sessions.0.end_time": "A session is at least 15 minutes."}
    scheduling.check_session_shapes(one(time(9), time(9, 15)), settings, TODAY)


def test_91_days_ahead_refused_90_ok(settings):
    scheduling.check_session_shapes(one(day=TODAY + timedelta(days=90)), settings, TODAY)
    error = refused(
        scheduling.check_session_shapes, one(day=TODAY + timedelta(days=91)), settings, TODAY
    )
    assert error.fields == {"sessions.0.date": "You can book at most 90 days ahead."}


def test_shape_errors_use_the_index_of_the_bad_session(settings):
    sessions = [s(DAY, time(9), time(10)), s(DAY, time(11), time(10))]
    error = refused(scheduling.check_session_shapes, sessions, settings, TODAY)
    assert list(error.fields) == ["sessions.1.end_time"]


def test_overlap_inside_booking(settings):
    # Given order: B (9:30-10:30) first, A (9:00-10:00) second. The later one is B, index 0.
    sessions = [s(DAY, time(9, 30), time(10, 30)), s(DAY, time(9), time(10))]
    error = refused(scheduling.check_session_shapes, sessions, settings, TODAY)
    assert error.fields == {"sessions.0.start_time": "This session overlaps session 2."}


def test_overlap_does_not_change_the_given_order(settings):
    sessions = [s(DAY, time(9, 30), time(10, 30)), s(DAY, time(9), time(10))]
    before = list(sessions)
    refused(scheduling.check_session_shapes, sessions, settings, TODAY)
    assert sessions == before


def test_back_to_back_inside_booking_ok(settings):
    sessions = [s(DAY, time(9), time(10)), s(DAY, time(10), time(11))]
    scheduling.check_session_shapes(sessions, settings, TODAY)


def test_same_hours_on_different_days_ok(settings):
    sessions = [s(DAY, time(9), time(10)), s(DAY + timedelta(days=1), time(9), time(10))]
    scheduling.check_session_shapes(sessions, settings, TODAY)


# --- Room ------------------------------------------------------------------------------


def test_room_hours_boundaries_ok(make_bookable_room):
    room = make_bookable_room()
    scheduling.check_room_hours(one(time(8), time(9)), room)
    scheduling.check_room_hours(one(time(17), time(18)), room)


def test_outside_hours(make_bookable_room):
    error = refused(scheduling.check_room_hours, one(time(7, 45), time(9)), make_bookable_room())
    assert (error.status, error.code) == (422, ErrorCode.OUTSIDE_ROOM_HOURS)
    assert error.message == "This room is open from 08:00 to 18:00."
    assert list(error.fields) == ["sessions.0.start_time"]


def test_ending_after_closing(make_bookable_room):
    error = refused(scheduling.check_room_hours, one(time(17), time(18, 15)), make_bookable_room())
    assert list(error.fields) == ["sessions.0.end_time"]


def test_bookable_room_passes(make_bookable_room):
    scheduling.check_room_bookable(make_bookable_room())


def test_inactive_floor_not_bookable(make_bookable_room):
    room = make_bookable_room()
    room.floor.is_active = False
    error = refused(scheduling.check_room_bookable, room)
    assert (error.status, error.code) == (409, ErrorCode.ROOM_NOT_BOOKABLE)
    assert error.message == "This room cannot be booked right now."


def test_private_room_without_owner(make_bookable_room):
    room = make_bookable_room(private=True)
    room.owner = None
    room.room_owner_id = None
    error = refused(scheduling.check_room_bookable, room)
    assert (error.status, error.code) == (409, ErrorCode.ROOM_NOT_BOOKABLE)
    assert error.message == "This private room has no owner yet."


def test_private_room_with_owner_is_bookable(make_bookable_room):
    scheduling.check_room_bookable(make_bookable_room(private=True))


# --- Past ------------------------------------------------------------------------------


def test_past_uses_local_date():
    now = datetime(2026, 11, 10, 6, 30)
    scheduling.check_not_past(one(time(7), time(8), day=date(2026, 11, 10)), now)
    error = refused(scheduling.check_not_past, one(time(9), time(10), day=date(2026, 11, 9)), now)
    assert (error.status, error.code) == (409, ErrorCode.TIME_PASSED)
    assert error.message == "This session starts at 09:00, which has passed."
    assert list(error.fields) == ["sessions.0.start_time"]


def test_start_equal_now_ok():
    scheduling.check_not_past(one(time(8), time(9), day=NOW.date()), NOW)


def test_past_names_the_first_bad_session():
    sessions = [s(DAY, time(9), time(10)), s(date(2026, 11, 9), time(7), time(7, 30))]
    error = refused(scheduling.check_not_past, sessions, NOW)
    assert list(error.fields) == ["sessions.1.start_time"]


# --- Route -----------------------------------------------------------------------------


@pytest.mark.parametrize(
    "private,own,food,it,route",
    [
        (False, False, False, False, "R1"),
        (False, True, True, True, "R1"),
        (True, False, False, False, "R2"),
        (True, True, False, False, "R3"),
        (True, True, True, False, "R4"),
        (True, True, False, True, "R4"),
    ],
)
def test_pick_route(make_bookable_room, make_user, private, own, food, it, route):
    owner = make_user(roles=["ROOM_OWNER"])
    room = make_bookable_room(private=private, owner=owner if private else None)
    booker_id = owner.id if own else make_user().id
    assert scheduling.pick_route(room, booker_id, food, it) == BookingRoute(route)


def test_first_status():
    assert scheduling.first_status(BookingRoute.R1) == BookingStatus.PENDING_PITIKA
    assert scheduling.first_status(BookingRoute.R2) == BookingStatus.PENDING_PITIKA
    assert scheduling.first_status(BookingRoute.R4) == BookingStatus.PENDING_PITIKA
    assert scheduling.first_status(BookingRoute.R3) == BookingStatus.CONFIRMED


def test_steps():
    pitika, owner = BookingStep.PITIKA, BookingStep.OWNER
    it_setup, confirmed = BookingStep.IT_SETUP, BookingStep.CONFIRMED
    assert scheduling.steps_for(BookingRoute.R1, False) == [pitika, confirmed]
    assert scheduling.steps_for(BookingRoute.R1, True) == [pitika, it_setup, confirmed]
    assert scheduling.steps_for(BookingRoute.R2, False) == [pitika, owner, confirmed]
    assert scheduling.steps_for(BookingRoute.R2, True) == [pitika, owner, it_setup, confirmed]
    assert scheduling.steps_for(BookingRoute.R3, False) == [confirmed]
    assert scheduling.steps_for(BookingRoute.R3, True) == [confirmed]
    assert scheduling.steps_for(BookingRoute.R4, True) == [pitika, it_setup, confirmed]
    assert scheduling.steps_for(BookingRoute.R4, False) == [pitika, confirmed]


# --- Reviewer --------------------------------------------------------------------------


def test_no_reviewer(make_bookable_room, db_session):
    room = make_bookable_room(province="SIEM_REAP")
    error = refused(scheduling.check_reviewer, db_session, room, BookingRoute.R1)
    assert (error.status, error.code) == (409, ErrorCode.NO_REVIEWER)
    assert error.message == "No reviewer for this office yet."


def test_reviewer_in_the_province_passes(make_bookable_room, make_pitika, db_session):
    make_pitika(province="SIEM_REAP")
    room = make_bookable_room(province="SIEM_REAP")
    for route in (BookingRoute.R1, BookingRoute.R2, BookingRoute.R4):
        scheduling.check_reviewer(db_session, room, route)


def test_pitika_of_another_province_does_not_count(make_bookable_room, make_pitika, db_session):
    make_pitika(province="PHNOM_PENH")
    room = make_bookable_room(province="SIEM_REAP")
    assert scheduling.active_pitika_count(db_session, "SIEM_REAP") == 0
    assert refused(scheduling.check_reviewer, db_session, room, BookingRoute.R2).status == 409


def test_inactive_pitika_does_not_count(make_bookable_room, make_pitika, db_session):
    make_pitika(province="SIEM_REAP", is_active=False)
    room = make_bookable_room(province="SIEM_REAP")
    assert scheduling.active_pitika_count(db_session, "SIEM_REAP") == 0
    assert refused(scheduling.check_reviewer, db_session, room, BookingRoute.R1).status == 409


def test_active_pitika_count(make_pitika, db_session):
    make_pitika(province="KAMPOT")
    make_pitika(province="KAMPOT")
    make_pitika(province="KAMPOT", is_active=False)
    assert scheduling.active_pitika_count(db_session, "KAMPOT") == 2


def test_r3_needs_no_pitika(make_bookable_room, db_session):
    room = make_bookable_room(province="SIEM_REAP", private=True)
    scheduling.check_reviewer(db_session, room, BookingRoute.R3)


# --- Clashes ---------------------------------------------------------------------------


@pytest.fixture
def clash_setup(make_bookable_room, make_user, make_booking):
    """A shared room with a PENDING booking on DAY 09:00-10:00."""
    room = make_bookable_room()
    booking = make_booking(room, make_user(), status=BookingStatus.PENDING_PITIKA)
    return SimpleNamespace(room=room, booking=booking)


def test_clash_overlap(clash_setup, make_user, db_session):
    current = current_for(db_session, make_user())
    error = refused(
        scheduling.check_clashes,
        db_session,
        current,
        clash_setup.room,
        one(time(9, 30), time(10, 30)),
    )
    assert (error.status, error.code) == (409, ErrorCode.SCHEDULE_CONFLICT)
    assert list(error.fields) == ["sessions.0"]
    assert error.message == (
        f"This room is already booked from 09:00 to 10:00 for {clash_setup.booking.meeting_title}."
    )


def test_clash_reports_the_index_of_the_clashing_session(clash_setup, make_user, db_session):
    current = current_for(db_session, make_user())
    sessions = [s(DAY, time(13), time(14)), s(DAY, time(9), time(9, 30))]
    error = refused(scheduling.check_clashes, db_session, current, clash_setup.room, sessions)
    assert list(error.fields) == ["sessions.1"]


def test_back_to_back_ok(clash_setup, make_user, db_session):
    current = current_for(db_session, make_user())
    scheduling.check_clashes(db_session, current, clash_setup.room, one(time(10), time(11)))
    scheduling.check_clashes(db_session, current, clash_setup.room, one(time(8), time(9)))


def test_other_room_or_day_does_not_clash(clash_setup, make_bookable_room, make_user, db_session):
    current = current_for(db_session, make_user())
    scheduling.check_clashes(db_session, current, make_bookable_room(), one())
    scheduling.check_clashes(db_session, current, clash_setup.room, one(day=DAY + timedelta(1)))


@pytest.mark.parametrize("status", [BookingStatus.REJECTED, BookingStatus.CANCELLED])
def test_rejected_and_cancelled_do_not_block(
    status, make_bookable_room, make_user, make_booking, db_session
):
    room = make_bookable_room()
    make_booking(room, make_user(), status=status)
    scheduling.check_clashes(db_session, current_for(db_session, make_user()), room, one())


@pytest.mark.parametrize(
    "status",
    [
        BookingStatus.PENDING_PITIKA,
        BookingStatus.PENDING_OWNER,
        BookingStatus.SETUP_IN_PROGRESS,
        BookingStatus.CONFIRMED,
    ],
)
def test_pending_and_confirmed_block(
    status, make_bookable_room, make_user, make_booking, db_session
):
    room = make_bookable_room()
    make_booking(room, make_user(), status=status)
    error = refused(
        scheduling.check_clashes, db_session, current_for(db_session, make_user()), room, one()
    )
    assert error.code == ErrorCode.SCHEDULE_CONFLICT


def test_exclude_booking_id(clash_setup, make_user, db_session):
    current = current_for(db_session, make_user())
    scheduling.check_clashes(
        db_session, current, clash_setup.room, one(), exclude_booking_id=clash_setup.booking.id
    )


def test_clash_message_masked_for_others(make_bookable_room, make_user, make_booking, db_session):
    owner = make_user(roles=["ROOM_OWNER"])
    room = make_bookable_room(private=True, owner=owner)
    make_booking(room, owner, status=BookingStatus.CONFIRMED, meeting_title="Secret plan")
    current = current_for(db_session, make_user(roles=["STAFF"]))
    error = refused(scheduling.check_clashes, db_session, current, room, one())
    assert error.message == (
        "This room is already booked from 09:00 to 10:00 for Reserved (Private Session)."
    )


def test_clash_message_shows_title_to_owner(
    make_bookable_room, make_user, make_booking, db_session
):
    owner = make_user(roles=["ROOM_OWNER"])
    room = make_bookable_room(private=True, owner=owner)
    make_booking(room, owner, status=BookingStatus.CONFIRMED, meeting_title="Secret plan")
    error = refused(
        scheduling.check_clashes, db_session, current_for(db_session, owner), room, one()
    )
    assert error.message.endswith("for Secret plan.")


# --- Warnings --------------------------------------------------------------------------


def test_holiday_warning_once_per_date(make_bookable_room, make_holiday, db_session):
    make_holiday(DAY, name_km="ថ្ងៃឈប់", name_en="Day Off")
    sessions = [s(DAY, time(9), time(10)), s(DAY, time(11), time(12))]
    warnings = scheduling.warnings_for(db_session, make_bookable_room(), sessions, 5)
    assert warnings == [{"code": "PUBLIC_HOLIDAY", "date": "2026-11-10", "name": "Day Off"}]


def test_holiday_name_falls_back_to_khmer(make_bookable_room, make_holiday, db_session):
    make_holiday(DAY, name_km="ថ្ងៃឈប់", name_en=None)
    warnings = scheduling.warnings_for(db_session, make_bookable_room(), one(), 5)
    assert warnings[0]["name"] == "ថ្ងៃឈប់"


def test_no_warning_on_a_normal_day(make_bookable_room, db_session):
    assert scheduling.warnings_for(db_session, make_bookable_room(), one(), 5) == []


def test_over_capacity_warning(make_bookable_room, db_session):
    warnings = scheduling.warnings_for(db_session, make_bookable_room(), one(), 12)
    assert warnings == [{"code": "OVER_CAPACITY", "seats": 10, "attendees": 12}]


def test_exact_capacity_and_unknown_attendees_give_no_warning(make_bookable_room, db_session):
    room = make_bookable_room()
    assert scheduling.warnings_for(db_session, room, one(), 10) == []
    assert scheduling.warnings_for(db_session, room, one(), None) == []
