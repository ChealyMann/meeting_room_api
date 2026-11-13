from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import MYSQL_TABLE, Base, IdMixin, UnsignedInt


class BookingSigner(IdMixin, Base):
    """A copy, taken when the booking is confirmed, of one person on its request slip: the booker
    or the head who signs an opinion box. Name, title and signature file as they were then, so an
    old slip never changes (the signature file is kept while a slip uses it)."""

    __tablename__ = "booking_signers"
    __table_args__ = (UniqueConstraint("booking_id", "role"), MYSQL_TABLE)

    booking_id: Mapped[int] = mapped_column(
        UnsignedInt, ForeignKey("bookings.id", ondelete="RESTRICT", onupdate="RESTRICT")
    )
    role: Mapped[str] = mapped_column(String(20))  # SignerRole
    user_id: Mapped[int | None] = mapped_column(
        UnsignedInt, ForeignKey("users.id", ondelete="RESTRICT", onupdate="RESTRICT"), index=True
    )
    name_kh: Mapped[str] = mapped_column(String(100))
    title: Mapped[str | None] = mapped_column(String(20))
    signature_path: Mapped[str | None] = mapped_column(String(3000))  # inside SIGNATURE_DIR
    signed_at: Mapped[datetime] = mapped_column(DateTime)  # UTC: the confirm time
