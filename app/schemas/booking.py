"""Booking request and response shapes (spec section 9).

Local values (session dates and times) go out as `date` + `time` pairs; stored UTC
datetimes go out with a `Z` (B-17).
"""

from datetime import date
from typing import Any

from pydantic import Field

from app.constants.booking import (
    BookingRoute,
    BookingStatus,
    BookingStep,
    DisplayStatus,
    ITStatus,
    MeetingType,
    RejectedBy,
    ReviewDecision,
    ReviewStage,
)
from app.schemas.common import (
    BookingText,
    Email,
    LocalTime,
    OptionalBookingText,
    RefId,
    RequestModel,
    ResponseModel,
    UtcDateTime,
)
from app.schemas.refs import NamedRef, ProvinceRef

# --- Requests --------------------------------------------------------------------------


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


class CateringIn(RequestModel):
    package_ids: list[RefId] = Field(min_length=1)
    remarks: OptionalBookingText(1000) = None


class ITIn(RequestModel):
    service_ids: list[RefId] = Field(min_length=1)
    special_requirements: OptionalBookingText(1000) = None


class BookingCreate(RequestModel):
    """The body of POST /bookings. The server picks the route; limits that are settings
    (attendees, emails, sessions) are checked by the service."""

    room_id: RefId
    sessions: list[SessionIn]
    meeting_title: BookingText(200, min_length=3)
    meeting_type: MeetingType
    meeting_purpose: OptionalBookingText(1000) = None
    attendees: int
    participant_emails: list[Email] = Field(default_factory=list)
    private_justification: OptionalBookingText(1000) = None
    catering: CateringIn | None = None
    it: ITIn | None = None


# --- Check answer ----------------------------------------------------------------------


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


# --- Booking answers -------------------------------------------------------------------


class SessionOut(ResponseModel):
    id: int
    date: date
    start_time: LocalTime
    end_time: LocalTime


class LocalMoment(ResponseModel):
    """A local date and time, e.g. the end of the last session."""

    date: date
    time: LocalTime


class BookingRoomRef(ResponseModel):
    id: int
    name_en: str
    name_kh: str
    is_private: bool
    location: NamedRef
    province: ProvinceRef


class PersonRef(ResponseModel):
    """A user who acted on the booking: a reviewer, the food approver."""

    id: int
    name_en: str


class CateringOut(ResponseModel):
    packages: list[dict[str, Any]]
    remarks: str | None
    servings: int
    delivery_date: date
    delivery_time: LocalTime
    approver_notes: str | None
    decided_by: PersonRef | None
    decided_at: UtcDateTime | None


class ITOut(ResponseModel):
    ticket_id: int
    items: list[dict[str, Any]]
    special_requirements: str | None
    status: ITStatus
    technician_notes: str | None
    staff: list[NamedRef]
    setup_date: date
    setup_time: LocalTime
    forwarded_at: UtcDateTime | None
    assigned_at: UtcDateTime | None
    ready_at: UtcDateTime | None


class ReviewOut(ResponseModel):
    stage: ReviewStage
    decision: ReviewDecision
    reviewer: PersonRef | None
    notes: str | None
    reviewed_at: UtcDateTime


class RejectionOut(ResponseModel):
    rejected_by: RejectedBy
    actor: PersonRef | None
    reason: str
    decided_at: UtcDateTime


class BookingListItem(ResponseModel):
    id: int
    reference_code: str
    room: BookingRoomRef
    meeting_title: str
    meeting_type: MeetingType
    route: BookingRoute
    status: BookingStatus
    display_status: DisplayStatus  # CONFIRMED and ended -> COMPLETED (B-10)
    requester: NamedRef
    first_session: SessionOut
    session_count: int
    attendees: int
    has_catering: bool
    has_it: bool
    created_at: UtcDateTime
    version: int


class BookingDetail(BookingListItem):
    requester_info: dict[str, Any]  # copied when sent (BR-FRM-06)
    meeting_purpose: str | None
    private_justification: str | None
    participant_emails: list[str]
    sessions: list[SessionOut]
    last_end: LocalMoment
    catering: CateringOut | None
    it: ITOut | None
    reviews: list[ReviewOut]
    rejection: RejectionOut | None
    cancelled_at: UtcDateTime | None
    cancel_reason: str | None
    updated_at: UtcDateTime


class BookingSaved(BookingDetail):
    """The answer of create and edit: the booking plus things to tell the booker."""

    warnings: list[dict]
