from sqlalchemy import String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import MYSQL_TABLE, ActiveMixin, Base, IdMixin, TimestampMixin


class Location(IdMixin, ActiveMixin, TimestampMixin, Base):
    __tablename__ = "locations"
    __table_args__ = (UniqueConstraint("name_en"), MYSQL_TABLE)

    name_en: Mapped[str] = mapped_column(String(100))
    name_kh: Mapped[str] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(String(1000))
    address: Mapped[str | None] = mapped_column(String(200))
    province: Mapped[str] = mapped_column(String(30), index=True)
    map_query: Mapped[str | None] = mapped_column(String(500))
