"""The day's food list (spec 9.12). Food is served at every session (owner decision,
6 Nov 2026): one item per session on the day."""

from datetime import date
from typing import Any

from app.constants.booking import BookingStatus
from app.schemas.booking import BookingRoomRef
from app.schemas.common import LocalTime, ResponseModel


class CateringOrderItem(ResponseModel):
    booking_id: int
    reference_code: str
    booking_status: BookingStatus
    room: BookingRoomRef
    meeting_title: str
    delivery_date: date
    delivery_time: LocalTime
    servings: int
    packages: list[dict[str, Any]]
    remarks: str | None
    approver_notes: str | None
    session_number: int  # which session of the booking this delivery is for (1 = the first)
    session_count: int
