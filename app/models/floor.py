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


class Floor(IdMixin, SortOrderMixin, ActiveMixin, TimestampMixin, Base):
    __tablename__ = "floors"
    __table_args__ = (UniqueConstraint("building_id", "floor_label"), MYSQL_TABLE)

    building_id: Mapped[int] = mapped_column(
        UnsignedInt, ForeignKey("buildings.id", ondelete="RESTRICT", onupdate="RESTRICT")
    )
    floor_label: Mapped[str] = mapped_column(String(100))  # one language, not bilingual
