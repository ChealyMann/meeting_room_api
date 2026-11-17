"""Pitika approve and reject bodies (spec 9.11), and the Pitika's decided list."""

from app.schemas.booking import BookingListItem, PersonRef
from app.schemas.common import (
    BookingText,
    OptionalBookingText,
    RequestModel,
    ResponseModel,
    UtcDateTime,
)


class DecidedBookingItem(BookingListItem):
    """A decided booking, with when, what was written, and who decided (a Pitika of the
    province, the room owner, or an Admin as a backup when `by_admin`)."""

    decided_at: UtcDateTime
    # The review's notes on an approval; the rejection's reason on a rejection.
    decision_note: str | None
    decided_by: PersonRef | None
    by_admin: bool


class ApproveBody(RequestModel):
    """`version` is the booking version the person saw (B-04). The notes go to the review and,
    when the booking has food, to the food order."""

    notes: OptionalBookingText(1000) = None
    version: int


class RejectBody(RequestModel):
    reason: BookingText(1000, min_length=5)
    version: int


class ReviewSummary(ResponseModel):
    """Bookings waiting for me now, and my decisions today (Phnom Penh day)."""

    waiting: int
    approved_today: int
    rejected_today: int


# The Pitika's name for it, kept for its router.
PitikaSummary = ReviewSummary
