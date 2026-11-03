from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import MYSQL_TABLE, Base, IdMixin, UnsignedInt


class BookingDoorPass(IdMixin, Base):
    __tablename__ = "booking_door_passes"
    __table_args__ = (UniqueConstraint("booking_id"), MYSQL_TABLE)

    booking_id: Mapped[int] = mapped_column(
        UnsignedInt, ForeignKey("bookings.id", ondelete="RESTRICT", onupdate="RESTRICT")
    )
    # NBC- and 5 digits. Not unique: old passes may repeat.
    passcode: Mapped[str] = mapped_column(String(10), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime)  # UTC of the last session's end
