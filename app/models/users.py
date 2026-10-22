from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Table, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import MYSQL_TABLE, ActiveMixin, Base, IdMixin, TimestampMixin, UnsignedInt


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
    email_notifications: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=text("1")
    )
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime)
    password_hash: Mapped[str] = mapped_column(String(255))  # Argon2id; never returned
    must_change_password: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=text("1")
    )


class Role(IdMixin, ActiveMixin, TimestampMixin, Base):
    """The six fixed roles. Code checks `code`, never the display name."""

    __tablename__ = "roles"
    __table_args__ = (UniqueConstraint("code"), MYSQL_TABLE)

    code: Mapped[str] = mapped_column(String(50))
    name_en: Mapped[str] = mapped_column(String(100))
    name_kh: Mapped[str] = mapped_column(String(100))


user_roles = Table(
    "user_roles",
    Base.metadata,
    Column(
        "user_id",
        UnsignedInt,
        ForeignKey("users.id", ondelete="RESTRICT", onupdate="RESTRICT"),
        primary_key=True,
    ),
    Column(
        "role_id",
        UnsignedInt,
        ForeignKey("roles.id", ondelete="RESTRICT", onupdate="RESTRICT"),
        primary_key=True,
        index=True,
    ),
    **MYSQL_TABLE,
)
