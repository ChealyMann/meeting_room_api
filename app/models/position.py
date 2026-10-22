from sqlalchemy import String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import (
    MYSQL_TABLE,
    ActiveMixin,
    Base,
    IdMixin,
    SortOrderMixin,
    TimestampMixin,
)


class Position(IdMixin, SortOrderMixin, ActiveMixin, TimestampMixin, Base):
    """A job position."""

    __tablename__ = "positions"
    __table_args__ = (UniqueConstraint("name_en"), MYSQL_TABLE)

    name_en: Mapped[str] = mapped_column(String(100))
    name_kh: Mapped[str] = mapped_column(String(100))
