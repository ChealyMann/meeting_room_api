from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.constants.booking import ITStatus
from app.models.base import MYSQL_TABLE, Base, IdMixin, TimestampMixin, UnsignedInt, enum_check
from app.models.it_ticket_staff import it_ticket_staff

if TYPE_CHECKING:
    from app.models.booking import Booking
    from app.models.user import User


class ITTicket(IdMixin, TimestampMixin, Base):
    __tablename__ = "it_tickets"
    __table_args__ = (UniqueConstraint("booking_id"), enum_check("status", ITStatus), MYSQL_TABLE)

    booking_id: Mapped[int] = mapped_column(
        UnsignedInt, ForeignKey("bookings.id", ondelete="RESTRICT", onupdate="RESTRICT")
    )
    requested_items: Mapped[list[dict[str, Any]]] = mapped_column(JSON)  # [{id, name}]
    special_requirements: Mapped[str | None] = mapped_column(String(1000))
    status: Mapped[str] = mapped_column(String(10), default=ITStatus.RECEIVED.value)
    technician_notes: Mapped[str | None] = mapped_column(String(1000))
    forwarded_at: Mapped[datetime | None] = mapped_column(DateTime)
    assigned_at: Mapped[datetime | None] = mapped_column(DateTime)
    ready_at: Mapped[datetime | None] = mapped_column(DateTime)

    booking: Mapped["Booking"] = relationship(back_populates="it_ticket")
    staff: Mapped[list["User"]] = relationship(secondary=it_ticket_staff, order_by="User.name_en")
