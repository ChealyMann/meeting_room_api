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
    review_notes: list[str]
    booking: BookingListItem
