"""Public holidays (spec 9.15). One row per date."""

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import PublicHoliday
from app.services.listing import paginate
from app.services.records import apply_changes, get_or_404, save


def list_holidays(session: Session, page: int, size: int, year: int | None = None) -> dict:
    query = select(PublicHoliday)
    if year is not None:
        query = query.where(
            PublicHoliday.holiday_date.between(date(year, 1, 1), date(year, 12, 31))
        )
    query = query.order_by(PublicHoliday.holiday_date)
    return paginate(session, query, page, size)


def create_holiday(session: Session, data: dict) -> PublicHoliday:
    holiday = PublicHoliday(**data)
    session.add(holiday)
    save(session)
    return holiday


def update_holiday(session: Session, holiday_id: int, changes: dict) -> PublicHoliday:
    holiday = get_or_404(session, PublicHoliday, holiday_id)
    apply_changes(holiday, changes)
    save(session)
    return holiday


def delete_holiday(session: Session, holiday_id: int) -> None:
    session.delete(get_or_404(session, PublicHoliday, holiday_id))
    save(session)
