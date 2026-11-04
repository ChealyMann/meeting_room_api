from sqlalchemy import Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import MYSQL_TABLE, ActiveMixin, Base, IdMixin, SortOrderMixin, TimestampMixin


class ITService(IdMixin, ActiveMixin, SortOrderMixin, TimestampMixin, Base):
    """An IT service a booker can ask for. The Admin manages the list."""

    __tablename__ = "it_services"
    __table_args__ = (UniqueConstraint("name"), MYSQL_TABLE)

    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(String(1000))
    version: Mapped[int] = mapped_column(Integer, default=1)  # optimistic lock
