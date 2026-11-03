"""Pitika approve and reject bodies (spec 9.11)."""

from app.schemas.common import BookingText, OptionalBookingText, RequestModel


class ApproveBody(RequestModel):
    """`version` is the booking version the person saw (B-04). The notes go to the review and,
    when the booking has food, to the food order."""

    notes: OptionalBookingText(1000) = None
    version: int


class RejectBody(RequestModel):
    reason: BookingText(1000, min_length=5)
    version: int
