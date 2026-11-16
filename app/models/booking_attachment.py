from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import MYSQL_TABLE, Base, IdMixin, TimestampMixin, UnsignedInt


class BookingAttachment(IdMixin, TimestampMixin, Base):
    """A document the booker added to a booking (PDF, Word or Excel). The file lives in
    ATTACHMENT_DIR, which is never served publicly. Rows are really deleted, like room photos."""

    __tablename__ = "booking_attachments"
    __table_args__ = (MYSQL_TABLE,)

    booking_id: Mapped[int] = mapped_column(
        UnsignedInt, ForeignKey("bookings.id", ondelete="RESTRICT", onupdate="RESTRICT"), index=True
    )
    file_name: Mapped[str] = mapped_column(String(255))  # as uploaded, cleaned
    content_type: Mapped[str] = mapped_column(String(100))  # from the detected type
    size_bytes: Mapped[int] = mapped_column(UnsignedInt)
    stored_path: Mapped[str] = mapped_column(String(500))  # inside ATTACHMENT_DIR
    uploaded_by: Mapped[int] = mapped_column(
        UnsignedInt, ForeignKey("users.id", ondelete="RESTRICT", onupdate="RESTRICT"), index=True
    )
