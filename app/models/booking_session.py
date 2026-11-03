from datetime import date, time

from sqlalchemy import Boolean, CheckConstraint, Date, ForeignKey, Index, Time, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import MYSQL_TABLE, Base, IdMixin, UnsignedInt


class BookingSession(IdMixin, Base):
    """One day and time span of a booking. Date and times are local Phnom Penh (B-01)."""

    __tablename__ = "booking_sessions"
    __table_args__ = (
        CheckConstraint("start_time < end_time", name="time_order"),
        Index(None, "room_id", "date", "is_blocking"),
        MYSQL_TABLE,
    )

    booking_id: Mapped[int] = mapped_column(
        UnsignedInt,
        ForeignKey("bookings.id", ondelete="RESTRICT", onupdate="RESTRICT"),
        index=True,
    )
    # A copy of bookings.room_id, so the clash check can use one index (B-05).
    room_id: Mapped[int] = mapped_column(
        UnsignedInt, ForeignKey("rooms.id", ondelete="RESTRICT", onupdate="RESTRICT")
    )
    date: Mapped[date] = mapped_column(Date)
    start_time: Mapped[time] = mapped_column(Time)
    end_time: Mapped[time] = mapped_column(Time)
    # False once the booking is rejected or cancelled (B-11).
    is_blocking: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("1"))
