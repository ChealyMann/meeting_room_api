from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, CheckConstraint, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.constants.booking import BookingRoute, BookingStatus, MeetingType
from app.models.base import MYSQL_TABLE, Base, IdMixin, TimestampMixin, UnsignedInt, enum_check

if TYPE_CHECKING:
    from app.models.booking_door_pass import BookingDoorPass
    from app.models.booking_participant import BookingParticipant
    from app.models.booking_rejection import BookingRejection
    from app.models.booking_review import BookingReview
    from app.models.booking_session import BookingSession
    from app.models.catering_order import CateringOrder
    from app.models.it_ticket import ITTicket
    from app.models.room import Room
    from app.models.user import User


class Booking(IdMixin, TimestampMixin, Base):
    __tablename__ = "bookings"
    __table_args__ = (
        UniqueConstraint("reference_code"),
        enum_check("meeting_type", MeetingType),
        enum_check("route", BookingRoute),
        enum_check("status", BookingStatus),
        CheckConstraint("attendees >= 1", name="attendees_min"),
        MYSQL_TABLE,
    )

    reference_code: Mapped[str] = mapped_column(String(20))  # NBC-YY-NNNNN (B-28)
    requester_id: Mapped[int] = mapped_column(
        UnsignedInt, ForeignKey("users.id", ondelete="RESTRICT", onupdate="RESTRICT"), index=True
    )
    room_id: Mapped[int] = mapped_column(
        UnsignedInt, ForeignKey("rooms.id", ondelete="RESTRICT", onupdate="RESTRICT"), index=True
    )
    # The form's "about the requester" block, copied at booking time (BR-FRM-06).
    requester_info: Mapped[dict[str, Any]] = mapped_column(JSON)
    meeting_title: Mapped[str] = mapped_column(String(200))
    meeting_type: Mapped[str] = mapped_column(String(30))
    meeting_purpose: Mapped[str | None] = mapped_column(String(1000))
    attendees: Mapped[int] = mapped_column(UnsignedInt)
    private_justification: Mapped[str | None] = mapped_column(String(1000))
    route: Mapped[str] = mapped_column(String(2))
    status: Mapped[str] = mapped_column(String(20), index=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime)
    cancel_reason: Mapped[str | None] = mapped_column(String(500))
    version: Mapped[int] = mapped_column(UnsignedInt, default=1)  # optimistic lock (B-04)

    room: Mapped["Room"] = relationship()
    requester: Mapped["User"] = relationship()
    sessions: Mapped[list["BookingSession"]] = relationship(
        order_by="(BookingSession.date, BookingSession.start_time)"
    )
    participants: Mapped[list["BookingParticipant"]] = relationship()
    catering_order: Mapped["CateringOrder | None"] = relationship(
        back_populates="booking", uselist=False
    )
    it_ticket: Mapped["ITTicket | None"] = relationship(back_populates="booking", uselist=False)
    reviews: Mapped[list["BookingReview"]] = relationship(order_by="BookingReview.id")
    rejection: Mapped["BookingRejection | None"] = relationship(uselist=False)
    door_pass: Mapped["BookingDoorPass | None"] = relationship(uselist=False)
