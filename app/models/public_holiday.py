from datetime import date

from sqlalchemy import Date, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import MYSQL_TABLE, Base, IdMixin, TimestampMixin


class PublicHoliday(IdMixin, TimestampMixin, Base):
    __tablename__ = "public_holidays"
    __table_args__ = (UniqueConstraint("holiday_date"), MYSQL_TABLE)

    holiday_date: Mapped[date] = mapped_column(Date)
    name_km: Mapped[str] = mapped_column(String(255))
    name_en: Mapped[str | None] = mapped_column(String(255))
    remarks: Mapped[str | None] = mapped_column(String(1000))
