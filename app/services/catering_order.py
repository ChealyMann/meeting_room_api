"""The day's food list (spec 9.12, B-12). Food is served at every session of a booking
(owner decision, 6 Nov 2026), so a booking with sessions on several days is on each day's list,
once per session that day."""

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.constants.booking import BookingStatus
from app.constants.roles import RoleCode
from app.models import Booking, BookingSession, CateringOrder
from app.schemas.catering_order import CateringOrderItem
from app.security import CurrentUser
from app.services import booking_access, clock
from app.services.booking_view import booking_load_options, room_ref


def list_food_orders(session: Session, current: CurrentUser, day: date) -> list[CateringOrderItem]:
    """One delivery per session on `day` of bookings with food in IT setup or confirmed, at
    that session's start. A Pitika sees their province (none: nothing); Admin sees every
    province. Sorted by delivery time, then room name."""
    on_day = select(BookingSession.booking_id).where(BookingSession.date == day)
    query = (
        select(Booking)
        .join(CateringOrder, CateringOrder.booking_id == Booking.id)
        .where(
            Booking.status.in_([BookingStatus.SETUP_IN_PROGRESS, BookingStatus.CONFIRMED]),
            Booking.id.in_(on_day),
        )
        .options(*booking_load_options())
    )
    if not current.has_role(RoleCode.ADMIN):
        province = booking_access.pitika_province(current)
        query = query.where(Booking.room_id.in_(booking_access.room_ids_in_province(province)))

    rows = []
    for booking in session.scalars(query):
        order = booking.catering_order
        sessions = sorted(booking.sessions, key=lambda s: (s.date, s.start_time))
        for number, booked in enumerate(sessions, start=1):
            if booked.date != day:
                continue
            start = clock.session_start(booked)
            item = CateringOrderItem(
                booking_id=booking.id,
                reference_code=booking.reference_code,
                booking_status=booking.status,
                room=room_ref(booking.room),
                meeting_title=booking.meeting_title,
                delivery_date=start.date(),
                delivery_time=start.time(),
                servings=booking.attendees,  # B-25: always the current attendees
                packages=order.packages,
                remarks=order.remarks,
                approver_notes=order.approver_notes,
                session_number=number,
                session_count=len(sessions),
            )
            rows.append(((start.time(), booking.room.name_en, booking.id, number), item))
    rows.sort(key=lambda row: row[0])
    return [item for _key, item in rows]
