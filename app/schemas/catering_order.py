"""The day's food list (spec 9.12)."""

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
