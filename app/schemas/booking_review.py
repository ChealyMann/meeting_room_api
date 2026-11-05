"""Pitika approve and reject bodies (spec 9.11), and the Pitika's decided list."""

from app.schemas.booking import BookingListItem
from app.schemas.common import (
    BookingText,
    OptionalBookingText,
    RequestModel,
    ResponseModel,
    UtcDateTime,
)


class DecidedBookingItem(BookingListItem):
    """A booking this Pitika approved or rejected, with when and what they wrote."""

    decided_at: UtcDateTime
    # The review's notes on an approval; the rejection's reason on a rejection.
    decision_note: str | None


class ApproveBody(RequestModel):
    """`version` is the booking version the person saw (B-04). The notes go to the review and,
    when the booking has food, to the food order."""

    notes: OptionalBookingText(1000) = None
    version: int


class RejectBody(RequestModel):
    reason: BookingText(1000, min_length=5)
    version: int


class PitikaSummary(ResponseModel):
    """Bookings waiting in my province now, and my decisions today (Phnom Penh day)."""

    waiting: int
    approved_today: int
    rejected_today: int
