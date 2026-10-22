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


class Location(IdMixin, ActiveMixin, TimestampMixin, Base):
    __tablename__ = "locations"
    __table_args__ = (UniqueConstraint("name_en"), MYSQL_TABLE)

    name_en: Mapped[str] = mapped_column(String(100))
    name_kh: Mapped[str] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(String(1000))
    address: Mapped[str | None] = mapped_column(String(200))
    province: Mapped[str] = mapped_column(String(30), index=True)
    map_query: Mapped[str | None] = mapped_column(String(500))


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


class Floor(IdMixin, SortOrderMixin, ActiveMixin, TimestampMixin, Base):
    __tablename__ = "floors"
    __table_args__ = (UniqueConstraint("building_id", "floor_label"), MYSQL_TABLE)

    building_id: Mapped[int] = mapped_column(
        UnsignedInt, ForeignKey("buildings.id", ondelete="RESTRICT", onupdate="RESTRICT")
    )
    floor_label: Mapped[str] = mapped_column(String(100))
