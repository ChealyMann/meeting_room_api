from sqlalchemy import String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import MYSQL_TABLE, ActiveMixin, Base, IdMixin, TimestampMixin


class Role(IdMixin, ActiveMixin, TimestampMixin, Base):
    """The six fixed roles. Code checks `code`, never the display name."""

    __tablename__ = "roles"
    __table_args__ = (UniqueConstraint("code"), MYSQL_TABLE)

    code: Mapped[str] = mapped_column(String(50))
    name_en: Mapped[str] = mapped_column(String(100))
    name_kh: Mapped[str] = mapped_column(String(100))
