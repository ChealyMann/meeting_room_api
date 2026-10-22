from datetime import time

from sqlalchemy import (
    CheckConstraint,
    Column,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
    Time,
    UniqueConstraint,
    text,
)
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


class Category(IdMixin, SortOrderMixin, ActiveMixin, TimestampMixin, Base):
    __tablename__ = "categories"
    __table_args__ = (UniqueConstraint("name_en"), MYSQL_TABLE)

    name_en: Mapped[str] = mapped_column(String(100))
    name_kh: Mapped[str] = mapped_column(String(100))


class Room(IdMixin, ActiveMixin, TimestampMixin, Base):
    __tablename__ = "rooms"
    __table_args__ = (
        UniqueConstraint("floor_id", "name_en"),
        CheckConstraint("capacity >= 1", name="capacity_min"),
        CheckConstraint("start_time < end_time", name="hours_order"),
        MYSQL_TABLE,
    )

    name_kh: Mapped[str] = mapped_column(String(100))
    name_en: Mapped[str] = mapped_column(String(100))
    door_code: Mapped[str | None] = mapped_column(String(50))  # secret, never in normal responses
    short_desc: Mapped[str | None] = mapped_column(String(200))
    floor_id: Mapped[int] = mapped_column(
        UnsignedInt, ForeignKey("floors.id", ondelete="RESTRICT", onupdate="RESTRICT")
    )
    category_id: Mapped[int] = mapped_column(
        UnsignedInt,
        ForeignKey("categories.id", ondelete="RESTRICT", onupdate="RESTRICT"),
        index=True,
    )
    # Null means a no-owner room.
    room_owner_id: Mapped[int | None] = mapped_column(
        UnsignedInt, ForeignKey("users.id", ondelete="RESTRICT", onupdate="RESTRICT"), index=True
    )
    capacity: Mapped[int] = mapped_column(UnsignedInt)
    size_sqm: Mapped[int | None] = mapped_column(UnsignedInt)
    description: Mapped[str | None] = mapped_column(String(1000))
    # Cambodia local time (UTC+7), the same every day.
    start_time: Mapped[time] = mapped_column(Time)
    end_time: Mapped[time] = mapped_column(Time)


class RoomPhoto(IdMixin, TimestampMixin, Base):
    """Photos are the only rows that are really deleted, so there is no is_active."""

    __tablename__ = "room_photos"
    __table_args__ = (Index(None, "room_id", "sort_order"), MYSQL_TABLE)

    room_id: Mapped[int] = mapped_column(
        UnsignedInt, ForeignKey("rooms.id", ondelete="RESTRICT", onupdate="RESTRICT")
    )
    url: Mapped[str] = mapped_column(String(3000))
    thumbnail_url: Mapped[str] = mapped_column(String(3000))
    sort_order: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"))


class Equipment(IdMixin, SortOrderMixin, ActiveMixin, TimestampMixin, Base):
    __tablename__ = "equipment"
    __table_args__ = (UniqueConstraint("name"), MYSQL_TABLE)

    name: Mapped[str] = mapped_column(String(200))
    icon: Mapped[str | None] = mapped_column(String(1000))


room_equipment = Table(
    "room_equipment",
    Base.metadata,
    Column(
        "room_id",
        UnsignedInt,
        ForeignKey("rooms.id", ondelete="RESTRICT", onupdate="RESTRICT"),
        primary_key=True,
    ),
    Column(
        "equipment_id",
        UnsignedInt,
        ForeignKey("equipment.id", ondelete="RESTRICT", onupdate="RESTRICT"),
        primary_key=True,
        index=True,
    ),
    **MYSQL_TABLE,
)
