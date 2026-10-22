from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import (
    MYSQL_TABLE,
    ActiveMixin,
    Base,
    IdMixin,
    SortOrderMixin,
    TimestampMixin,
    UnsignedInt,
)


class Division(IdMixin, SortOrderMixin, ActiveMixin, TimestampMixin, Base):
    """A team inside a department."""

    __tablename__ = "divisions"
    __table_args__ = (UniqueConstraint("department_id", "name_en"), MYSQL_TABLE)

    department_id: Mapped[int] = mapped_column(
        UnsignedInt, ForeignKey("departments.id", ondelete="RESTRICT", onupdate="RESTRICT")
    )
    name_en: Mapped[str] = mapped_column(String(100))
    name_kh: Mapped[str] = mapped_column(String(100))
    short_name: Mapped[str | None] = mapped_column(String(20))
