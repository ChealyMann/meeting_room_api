"""The booking rules that need no write: shapes, room, route, clashes, warnings (spec 8.2).

A "session" here is anything with `date`, `start_time` and `end_time` (the request body or a
stored `BookingSession`). Times are Phnom Penh local time. Session numbers in messages and
field names are 0-based, like pydantic's (B-16).
"""

from collections.abc import Sequence
from datetime import date, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import Settings
from app.constants.booking import BookingRoute, BookingStatus, BookingStep
from app.constants.roles import RoleCode
from app.errors import AppError, ErrorCode
from app.models import (
    Booking,
    BookingSession,
    Department,
    Division,
    Location,
    PublicHoliday,
    Role,
    Room,
    User,
    user_roles,
)
from app.security import CurrentUser
from app.services import booking_access
from app.services.clock import session_end, session_start
from app.services.room import is_bookable


def _invalid(fields: dict[str, str]) -> AppError:
    return AppError(ErrorCode.VALIDATION_ERROR, 422, "Invalid request.", fields)


def _hhmm(value) -> str:
    return value.strftime("%H:%M")


# --- Pure checks -----------------------------------------------------------------------


def check_session_shapes(sessions: Sequence, settings: Settings, today: date) -> None:
    """422 for the first problem found, in the order of spec 8.2."""
    if not 1 <= len(sessions) <= settings.booking_max_sessions:
        raise _invalid({"sessions": f"Add 1 to {settings.booking_max_sessions} sessions."})
    for i, item in enumerate(sessions):
        if item.end_time <= item.start_time:
            raise _invalid({f"sessions.{i}.end_time": "End must be after start."})
    for i, item in enumerate(sessions):
        if (session_end(item) - session_start(item)).total_seconds() < (
            settings.booking_min_minutes * 60
        ):
            message = f"A session is at least {settings.booking_min_minutes} minutes."
            raise _invalid({f"sessions.{i}.end_time": message})
    for i, item in enumerate(sessions):
        if (item.date - today).days > settings.booking_max_days_ahead:
            message = f"You can book at most {settings.booking_max_days_ahead} days ahead."
            raise _invalid({f"sessions.{i}.date": message})
    _check_no_overlap(sessions)


def _check_no_overlap(sessions: Sequence) -> None:
    """BR-SCH-06. Sorted a copy by (date, start); the error names the later session's own index."""
    order = sorted(range(len(sessions)), key=lambda i: (sessions[i].date, sessions[i].start_time))
    for position, j in enumerate(order):
        later = sessions[j]
        for i in order[:position]:
            earlier = sessions[i]
            if (
                earlier.date == later.date
                and earlier.start_time < later.end_time
                and earlier.end_time > later.start_time
            ):
                message = f"This session overlaps session {i + 1}."
                raise _invalid({f"sessions.{j}.start_time": message})


def check_room_bookable(room: Room) -> None:
    if not is_bookable(room):
        message = "This room cannot be booked right now."
        raise AppError(ErrorCode.ROOM_NOT_BOOKABLE, 409, message)
    if room.is_private and room.room_owner_id is None:
        message = "This private room has no owner yet."
        raise AppError(ErrorCode.ROOM_NOT_BOOKABLE, 409, message)


def check_room_hours(sessions: Sequence, room: Room) -> None:
    message = f"This room is open from {_hhmm(room.start_time)} to {_hhmm(room.end_time)}."
    for i, item in enumerate(sessions):
        if item.start_time < room.start_time:
            field = f"sessions.{i}.start_time"
        elif item.end_time > room.end_time:
            field = f"sessions.{i}.end_time"
        else:
            continue
        raise AppError(ErrorCode.OUTSIDE_ROOM_HOURS, 422, message, {field: message})


def check_not_past(sessions: Sequence, now_local: datetime) -> None:
    """BR-SCH-03: a start equal to now is allowed."""
    for i, item in enumerate(sessions):
        if session_start(item) < now_local:
            message = f"This session starts at {_hhmm(item.start_time)}, which has passed."
            raise AppError(
                ErrorCode.TIME_PASSED, 409, message, {f"sessions.{i}.start_time": message}
            )


def pick_route(room: Room, booker_id: int, has_catering: bool, has_it: bool) -> BookingRoute:
    if not room.is_private:
        return BookingRoute.R1
    if room.room_owner_id != booker_id:
        return BookingRoute.R2
    if has_catering or has_it:
        return BookingRoute.R4
    return BookingRoute.R3


def first_status(route: BookingRoute) -> BookingStatus:
    """R3 has no reviewer, so it is confirmed at once."""
    if route == BookingRoute.R3:
        return BookingStatus.CONFIRMED
    return BookingStatus.PENDING_PITIKA


def steps_for(route: BookingRoute, has_it: bool) -> list[BookingStep]:
    steps = {
        BookingRoute.R1: [BookingStep.PITIKA],
        BookingRoute.R2: [BookingStep.PITIKA, BookingStep.OWNER],
        BookingRoute.R3: [],
        BookingRoute.R4: [BookingStep.PITIKA],
    }[route]
    steps = list(steps)
    if has_it and route != BookingRoute.R3:
        steps.append(BookingStep.IT_SETUP)
    steps.append(BookingStep.CONFIRMED)
    return steps


# --- Checks that read the database -----------------------------------------------------


def active_pitika_count(session: Session, province: str) -> int:
    """Active users with role PITIKA whose division -> department -> office is in `province`."""
    query = (
        select(func.count(func.distinct(User.id)))
        .join(user_roles, user_roles.c.user_id == User.id)
        .join(Role, Role.id == user_roles.c.role_id)
        .join(Division, Division.id == User.division_id)
        .join(Department, Department.id == Division.department_id)
        .join(Location, Location.id == Department.location_id)
        .where(
            User.is_active.is_(True), Role.code == RoleCode.PITIKA, Location.province == province
        )
    )
    return session.scalar(query)


def check_reviewer(session: Session, room: Room, route: BookingRoute) -> None:
    """BR-SCH-13: every route but R3 needs a Pitika in the room's province."""
    if route == BookingRoute.R3:
        return
    if active_pitika_count(session, booking_access.room_province(room)) == 0:
        raise AppError(ErrorCode.NO_REVIEWER, 409, "No reviewer for this office yet.")


def check_clashes(
    session: Session,
    current: CurrentUser,
    room: Room,
    sessions: Sequence,
    exclude_booking_id: int | None = None,
) -> None:
    """BR-SCH-04, 05, BR-PRV-02: the first session that meets a blocking one is refused.
    Back-to-back sessions are fine."""
    for i, item in enumerate(sessions):
        query = (
            select(BookingSession)
            .where(
                BookingSession.room_id == room.id,
                BookingSession.date == item.date,
                BookingSession.is_blocking.is_(True),
                BookingSession.start_time < item.end_time,
                BookingSession.end_time > item.start_time,
            )
            .order_by(BookingSession.start_time, BookingSession.id)
            .limit(1)
        )
        if exclude_booking_id is not None:
            query = query.where(BookingSession.booking_id != exclude_booking_id)
        other = session.scalar(query)
        if other is None:
            continue
        title = booking_access.visible_title(
            session, current, session.get(Booking, other.booking_id)
        )
        message = (
            f"This room is already booked from {_hhmm(other.start_time)} "
            f"to {_hhmm(other.end_time)} for {title}."
        )
        raise AppError(ErrorCode.SCHEDULE_CONFLICT, 409, message, {f"sessions.{i}": message})


def warnings_for(
    session: Session, room: Room, sessions: Sequence, attendees: int | None
) -> list[dict]:
    """Things to tell the booker that do not stop the booking."""
    warnings: list[dict] = []
    days = sorted({item.date for item in sessions})
    holidays = session.scalars(
        select(PublicHoliday)
        .where(PublicHoliday.holiday_date.in_(days))
        .order_by(PublicHoliday.holiday_date)
    )
    for holiday in holidays:
        warnings.append(
            {
                "code": "PUBLIC_HOLIDAY",
                "date": holiday.holiday_date.isoformat(),
                "name": holiday.name_en or holiday.name_km,
            }
        )
    if attendees is not None and attendees > room.capacity:
        warnings.append({"code": "OVER_CAPACITY", "seats": room.capacity, "attendees": attendees})
    return warnings
