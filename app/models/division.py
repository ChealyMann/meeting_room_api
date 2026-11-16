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
    from app.models.department import Department
    from app.models.user import User


class Division(IdMixin, SortOrderMixin, ActiveMixin, TimestampMixin, Base):
    """A team inside a department."""

    __tablename__ = "divisions"
    __table_args__ = (UniqueConstraint("department_id", "name_en"), MYSQL_TABLE)

    department_id: Mapped[int] = mapped_column(
        UnsignedInt, ForeignKey("departments.id", ondelete="RESTRICT", onupdate="RESTRICT")
    )
    name_en: Mapped[str] = mapped_column(String(100))
    name_kh: Mapped[str] = mapped_column(String(100))
    short_name: Mapped[str | None] = mapped_column(String(20))
    head_user_id: Mapped[int | None] = mapped_column(
        UnsignedInt,
        # use_alter: users → divisions → departments → users is a circle; this link is added last.
        ForeignKey("users.id", ondelete="RESTRICT", onupdate="RESTRICT", use_alter=True),
        index=True,
    )  # signs this office's opinion box on the request slip

    department: Mapped["Department"] = relationship()
    head: Mapped["User | None"] = relationship(foreign_keys=[head_user_id])
