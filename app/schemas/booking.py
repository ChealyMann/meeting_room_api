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


class CateringUpdate(RequestModel):
    """Food: only the remarks can change. `package_ids` is declared so the service can
    refuse it with FIELD_NOT_EDITABLE (B-15)."""

    remarks: OptionalBookingText(1000) = None
    package_ids: Any = None


class ITUpdate(RequestModel):
    """IT: only the special requirements can change. `service_ids` is declared to be refused."""

    special_requirements: OptionalBookingText(1000) = None
    service_ids: Any = None


class BookingUpdate(RequestModel):
    """The body of PATCH /bookings/{id} (T13): small edits only. A field left out keeps its
    value; read what was sent with `model_fields_set`. `room_id`, `sessions` and
    `private_justification` are declared so the service can refuse them (BR-EDT-03)."""

    version: int
    meeting_title: BookingText(200, min_length=3) = None
    meeting_type: MeetingType = None
    meeting_purpose: OptionalBookingText(1000) = None
    attendees: int = None
    participant_emails: list[Email] = None
    # `| None` so an explicit null reaches the service and is refused as FIELD_NOT_EDITABLE.
    catering: CateringUpdate | None = None
    it: ITUpdate | None = None
    room_id: Any = None
    sessions: Any = None
    private_justification: Any = None


class CancelBody(RequestModel):
    reason: OptionalBookingText(500, min_length=5) = None
    version: int


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
    by_admin: bool  # the Admin decided as a backup for this stage (B-34)


class RejectionOut(ResponseModel):
    rejected_by: RejectedBy
    actor: PersonRef | None
    reason: str
    decided_at: UtcDateTime
    by_admin: bool


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
    cancelled_by: PersonRef | None  # null: the system cancelled it (B-27)
    updated_at: UtcDateTime


class DoorPassOut(ResponseModel):
    passcode: str
    expires_at: UtcDateTime
    expired: bool  # now is at or after expires_at (BR-DP-03)


class BookingSaved(BookingDetail):
    """The answer of create and edit: the booking plus things to tell the booker."""

    warnings: list[dict]
