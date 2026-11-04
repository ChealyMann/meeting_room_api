from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from app.constants.booking import RejectedBy
from app.models.base import MYSQL_TABLE, Base, IdMixin, UnsignedInt, enum_check


class BookingRejection(IdMixin, Base):
    __tablename__ = "booking_rejections"
    __table_args__ = (
        UniqueConstraint("booking_id"),
        enum_check("rejected_by", RejectedBy),
        MYSQL_TABLE,
    )

    booking_id: Mapped[int] = mapped_column(
        UnsignedInt, ForeignKey("bookings.id", ondelete="RESTRICT", onupdate="RESTRICT")
    )
    rejected_by: Mapped[str] = mapped_column(String(10))
    # Null when the system rejected the booking (expiry).
    actor_user_id: Mapped[int | None] = mapped_column(
        UnsignedInt, ForeignKey("users.id", ondelete="RESTRICT", onupdate="RESTRICT")
    )
    reason: Mapped[str] = mapped_column(String(1000))
    # The Admin rejected as a backup for `rejected_by`'s stage (B-34); actor_user_id is the Admin.
    by_admin: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("0"))
    decided_at: Mapped[datetime] = mapped_column(DateTime)
