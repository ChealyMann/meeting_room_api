"""Booking request and response shapes (spec section 9)."""

from datetime import date

from pydantic import Field

from app.constants.booking import BookingRoute, BookingStatus, BookingStep
from app.schemas.common import LocalTime, RefId, RequestModel, ResponseModel


class SessionIn(RequestModel):
    """One meeting session, Phnom Penh local time."""

    date: date
    start_time: LocalTime
    end_time: LocalTime


class BookingCheck(RequestModel):
    room_id: RefId
    sessions: list[SessionIn]
    has_catering: bool = False
    has_it: bool = False


class Problem(ResponseModel):
    code: str
    message: str
    fields: dict[str, str] = Field(default_factory=dict)


class BookingCheckResult(ResponseModel):
    route: BookingRoute | None
    first_status: BookingStatus | None
    steps: list[BookingStep] | None
    problem: Problem | None
    warnings: list[dict]
