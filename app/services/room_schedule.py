"""A room's blocking sessions for a date range (spec 9.2)."""

from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.config import Settings
from app.errors import AppError, ErrorCode
from app.models import Booking, BookingSession, Room
from app.schemas.room_schedule import ScheduleItem
from app.security import CurrentUser
from app.services import booking_access
from app.services.clock import now_local
from app.services.records import get_or_404

DEFAULT_DAYS = 7


def _invalid_to(message: str) -> AppError:
    return AppError(ErrorCode.VALIDATION_ERROR, 422, "Invalid request.", {"to": message})


def _range(date_from: date | None, date_to: date | None, settings: Settings) -> tuple[date, date]:
    """`from` defaults to today and `to` to 6 days later; both days count."""
    first = date_from or now_local().date()
    last = date_to or first + timedelta(days=DEFAULT_DAYS - 1)
    if last < first:
        raise _invalid_to("Must not be before from.")
    if (last - first).days + 1 > settings.schedule_max_days:
        raise _invalid_to(f"At most {settings.schedule_max_days} days.")
    return first, last


def _item(session: Session, current: CurrentUser, row: BookingSession, booking: Booking):
    masked = booking.room.is_private and not booking_access.can_view(session, current, booking)
    return ScheduleItem(
        date=row.date,
        start_time=row.start_time,
        end_time=row.end_time,
        booking_id=None if masked else booking.id,
        reference_code=None if masked else booking.reference_code,
        title=booking_access.visible_title(session, current, booking),
        requester_name=None if masked else booking.requester_info.get("name_en"),
        status=booking.status,
        is_masked=masked,
    )


def get_schedule(
    session: Session,
    current: CurrentUser,
    room_id: int,
    date_from: date | None,
    date_to: date | None,
    settings: Settings,
) -> list[ScheduleItem]:
    get_or_404(session, Room, room_id)
    first, last = _range(date_from, date_to, settings)
    rows = session.execute(
        select(BookingSession, Booking)
        .join(Booking, Booking.id == BookingSession.booking_id)
        .where(
            BookingSession.room_id == room_id,
            BookingSession.is_blocking.is_(True),
            BookingSession.date >= first,
            BookingSession.date <= last,
        )
        .options(selectinload(Booking.it_ticket))
        .order_by(
            BookingSession.date,
            BookingSession.start_time,
            BookingSession.end_time,
            BookingSession.id,
        )
    ).all()
    return [_item(session, current, row, booking) for row, booking in rows]
