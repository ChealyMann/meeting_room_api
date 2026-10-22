from sqlalchemy import ForeignKey, Index, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import MYSQL_TABLE, Base, IdMixin, TimestampMixin, UnsignedInt


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
