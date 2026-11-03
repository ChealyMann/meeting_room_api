"""Booking use cases (spec section 9)."""

from sqlalchemy.orm import Session

from app.config import Settings
from app.errors import AppError, ErrorCode
from app.models import Room
from app.schemas.booking import BookingCheck, BookingCheckResult, Problem
from app.security import CurrentUser
from app.services import booking_scheduling as scheduling
from app.services.clock import now_local


def check_booking(
    session: Session, current: CurrentUser, body: BookingCheck, settings: Settings
) -> BookingCheckResult:
    """Spec 9.3: run the checks in order and report the first problem. Saves nothing.

    A rule error is returned as `problem`, not raised. `route`, `first_status` and `steps`
    stay empty until the room is found and can be booked.
    """
    result = BookingCheckResult(
        route=None, first_status=None, steps=None, problem=None, warnings=[]
    )
    sessions = body.sessions
    now = now_local()
    room = None
    try:
        scheduling.check_session_shapes(sessions, settings, now.date())
        room = session.get(Room, body.room_id)
        if room is None:
            message = "Invalid request."
            raise AppError(ErrorCode.VALIDATION_ERROR, 422, message, {"room_id": "Room not found."})
        scheduling.check_room_bookable(room)
        route = scheduling.pick_route(room, current.id, body.has_catering, body.has_it)
        result.route = route
        result.first_status = scheduling.first_status(route)
        result.steps = scheduling.steps_for(route, body.has_it)
        scheduling.check_room_hours(sessions, room)
        scheduling.check_not_past(sessions, now)
        scheduling.check_reviewer(session, room, route)
        scheduling.check_clashes(session, current, room, sessions)
    except AppError as error:
        result.problem = Problem(
            code=error.code.value, message=error.message, fields=error.fields or {}
        )
    if room is not None:
        result.warnings = scheduling.warnings_for(session, room, sessions, None)
    return result
