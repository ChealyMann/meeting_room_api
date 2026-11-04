from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import MYSQL_TABLE, Base, IdMixin, TimestampMixin, UnsignedInt

if TYPE_CHECKING:
    from app.models.booking import Booking
    from app.models.user import User


class CateringOrder(IdMixin, TimestampMixin, Base):
    __tablename__ = "catering_orders"
    __table_args__ = (UniqueConstraint("booking_id"), MYSQL_TABLE)

    booking_id: Mapped[int] = mapped_column(
        UnsignedInt, ForeignKey("bookings.id", ondelete="RESTRICT", onupdate="RESTRICT")
    )
    packages: Mapped[list[dict[str, Any]]] = mapped_column(JSON)  # [{id, name}]
    remarks: Mapped[str | None] = mapped_column(String(1000))
    approver_notes: Mapped[str | None] = mapped_column(String(1000))
    decided_by: Mapped[int | None] = mapped_column(
        UnsignedInt, ForeignKey("users.id", ondelete="RESTRICT", onupdate="RESTRICT")
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime)

    booking: Mapped["Booking"] = relationship(back_populates="catering_order")
    decider: Mapped["User | None"] = relationship()
