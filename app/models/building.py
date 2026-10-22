from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import (
    MYSQL_TABLE,
    ActiveMixin,
    Base,
    IdMixin,
    SortOrderMixin,
    TimestampMixin,
    UnsignedInt,
)

if TYPE_CHECKING:
    from app.models.location import Location


class Building(IdMixin, SortOrderMixin, ActiveMixin, TimestampMixin, Base):
    __tablename__ = "buildings"
    # The unique key leads with location_id, so it also serves as that column's index.
    __table_args__ = (UniqueConstraint("location_id", "name_en"), MYSQL_TABLE)

    location_id: Mapped[int] = mapped_column(
        UnsignedInt, ForeignKey("locations.id", ondelete="RESTRICT", onupdate="RESTRICT")
    )
    name_en: Mapped[str] = mapped_column(String(100))
    name_kh: Mapped[str] = mapped_column(String(100))
    short_name: Mapped[str | None] = mapped_column(String(20))

    location: Mapped["Location"] = relationship()
