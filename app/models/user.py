from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import MYSQL_TABLE, ActiveMixin, Base, IdMixin, TimestampMixin, UnsignedInt

if TYPE_CHECKING:
    from app.models.division import Division
    from app.models.position import Position


class User(IdMixin, ActiveMixin, TimestampMixin, Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("staff_id"), UniqueConstraint("email"), MYSQL_TABLE)

    staff_id: Mapped[str] = mapped_column(String(20))
    name_kh: Mapped[str] = mapped_column(String(100))
    name_en: Mapped[str] = mapped_column(String(100))
    title: Mapped[str | None] = mapped_column(String(20))
    # Required for PITIKA, IT_LEAD and IT_STAFF (rule R6); gives the user's province.
    division_id: Mapped[int | None] = mapped_column(
        UnsignedInt,
        ForeignKey("divisions.id", ondelete="RESTRICT", onupdate="RESTRICT"),
        index=True,
    )
    position_id: Mapped[int] = mapped_column(
        UnsignedInt,
        ForeignKey("positions.id", ondelete="RESTRICT", onupdate="RESTRICT"),
        index=True,
    )
    email: Mapped[str] = mapped_column(String(254))  # stored lowercase
    secondary_email: Mapped[str | None] = mapped_column(String(254))
    phone: Mapped[str | None] = mapped_column(String(20))
    avatar_url: Mapped[str | None] = mapped_column(String(3000))
    # Signature PNG for booking approval forms: its path inside SIGNATURE_DIR. Never returned.
    user_signature: Mapped[str | None] = mapped_column(String(3000))
    email_notifications: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=text("1")
    )
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime)
    password_hash: Mapped[str] = mapped_column(String(255))  # Argon2id; never returned
    must_change_password: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=text("1")
    )

    division: Mapped["Division | None"] = relationship()
    position: Mapped["Position"] = relationship()
