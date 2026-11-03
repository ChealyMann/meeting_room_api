from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import MYSQL_TABLE, Base, IdMixin, UnsignedInt


class BookingParticipant(IdMixin, Base):
    __tablename__ = "booking_participants"
    __table_args__ = (UniqueConstraint("booking_id", "email"), MYSQL_TABLE)

    booking_id: Mapped[int] = mapped_column(
        UnsignedInt, ForeignKey("bookings.id", ondelete="RESTRICT", onupdate="RESTRICT")
    )
    email: Mapped[str] = mapped_column(String(254))
