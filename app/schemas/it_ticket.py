"""IT ticket request and response shapes (spec 9.14)."""

from datetime import date
from typing import Any

from pydantic import Field

from app.constants.booking import ITStatus
from app.schemas.booking import BookingListItem
from app.schemas.common import (
    LocalTime,
    OptionalBookingText,
    RefId,
    RequestModel,
    ResponseModel,
    UtcDateTime,
)


class AssignStaffBody(RequestModel):
    """`version` is the booking's version (B-19). The staff list replaces the old one."""

    user_ids: list[RefId] = Field(min_length=1)
    technician_notes: OptionalBookingText(1000) = None
    version: int


class ReadyBody(RequestModel):
    """`version` is the booking's version (B-19)."""

    version: int


class ITStaffOut(ResponseModel):
    """An assigned user. `is_active` is false when the user was turned off later (B-22)."""

    id: int
    name_en: str
    name_kh: str
    is_active: bool
    avatar_url: str | None  # GET /users/{id}/avatar, or null when there is no photo


class ITBusy(ResponseModel):
    """Another setup of the same person whose time (set-up to meeting start) overlaps."""

    ticket_id: int
    room_name_en: str
    setup_time: LocalTime
    meeting_start: LocalTime


class ITStaffPick(ITStaffOut):
    """A row of the assign picker. `setups_that_day`: the setups they already have on the
    asked day (null when no day was asked). `busy`: their other setups at the same time as the
    asked ticket (null when no ticket was asked)."""

    setups_that_day: int | None
    busy: list[ITBusy] | None


class ITTicketItem(ResponseModel):
    id: int
    status: ITStatus
    items: list[dict[str, Any]]
    special_requirements: str | None
    technician_notes: str | None
    staff: list[ITStaffOut]
    setup_date: date
    setup_time: LocalTime
    forwarded_at: UtcDateTime | None
    assigned_at: UtcDateTime | None
    ready_at: UtcDateTime | None
    # Not Ready and the meeting started: it can no longer change (shown on Ready as missed).
    missed: bool
    review_notes: list[str]
    booking: BookingListItem


class ITSummary(ResponseModel):
    """The IT Lead's day (Phnom Penh): to assign and in progress now (missed left out), made
    ready today, today's setups and how many of them are ready."""

    to_assign: int
    in_progress: int
    ready_today: int
    due_today: int
    due_today_ready: int
