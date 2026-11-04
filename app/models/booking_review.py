from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.constants.booking import ReviewDecision, ReviewStage
from app.models.base import MYSQL_TABLE, Base, IdMixin, UnsignedInt, enum_check


class BookingReview(IdMixin, Base):
    """One review step of a booking: approved, rejected or not required."""

    __tablename__ = "booking_reviews"
    __table_args__ = (
        enum_check("stage", ReviewStage),
        enum_check("decision", ReviewDecision),
        MYSQL_TABLE,
    )

    booking_id: Mapped[int] = mapped_column(
        UnsignedInt,
        ForeignKey("bookings.id", ondelete="RESTRICT", onupdate="RESTRICT"),
        index=True,
    )
    stage: Mapped[str] = mapped_column(String(10))
    decision: Mapped[str] = mapped_column(String(15))
    # Null when the decision is NOT_REQUIRED.
    reviewer_id: Mapped[int | None] = mapped_column(
        UnsignedInt, ForeignKey("users.id", ondelete="RESTRICT", onupdate="RESTRICT")
    )
    notes: Mapped[str | None] = mapped_column(String(1000))
    reviewed_at: Mapped[datetime] = mapped_column(DateTime)
