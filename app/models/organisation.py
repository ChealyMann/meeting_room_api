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


class Department(IdMixin, SortOrderMixin, ActiveMixin, TimestampMixin, Base):
    __tablename__ = "departments"
    __table_args__ = (UniqueConstraint("location_id", "name_en"), MYSQL_TABLE)

    location_id: Mapped[int] = mapped_column(
        UnsignedInt, ForeignKey("locations.id", ondelete="RESTRICT", onupdate="RESTRICT")
    )
    name_en: Mapped[str] = mapped_column(String(100))
    name_kh: Mapped[str] = mapped_column(String(100))


class Division(IdMixin, SortOrderMixin, ActiveMixin, TimestampMixin, Base):
    __tablename__ = "divisions"
    __table_args__ = (UniqueConstraint("department_id", "name_en"), MYSQL_TABLE)

    department_id: Mapped[int] = mapped_column(
        UnsignedInt, ForeignKey("departments.id", ondelete="RESTRICT", onupdate="RESTRICT")
    )
    name_en: Mapped[str] = mapped_column(String(100))
    name_kh: Mapped[str] = mapped_column(String(100))
    short_name: Mapped[str | None] = mapped_column(String(20))


class Position(IdMixin, SortOrderMixin, ActiveMixin, TimestampMixin, Base):
    __tablename__ = "positions"
    __table_args__ = (UniqueConstraint("name_en"), MYSQL_TABLE)

    name_en: Mapped[str] = mapped_column(String(100))
    name_kh: Mapped[str] = mapped_column(String(100))
