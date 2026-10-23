from datetime import time
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, String, Time, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import MYSQL_TABLE, ActiveMixin, Base, IdMixin, TimestampMixin, UnsignedInt

if TYPE_CHECKING:
    from app.models.category import Category
    from app.models.floor import Floor
    from app.models.user import User


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
    # A label only, shown and filterable; it changes no access or booking rule.
    is_private: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("0"))

    floor: Mapped["Floor"] = relationship()
    category: Mapped["Category"] = relationship()
    owner: Mapped["User | None"] = relationship()
