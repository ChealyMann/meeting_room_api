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


class Equipment(IdMixin, SortOrderMixin, ActiveMixin, TimestampMixin, Base):
    __tablename__ = "equipment"
    __table_args__ = (UniqueConstraint("name"), MYSQL_TABLE)

    name: Mapped[str] = mapped_column(String(200))  # one language, not bilingual
    icon: Mapped[str | None] = mapped_column(String(1000))
