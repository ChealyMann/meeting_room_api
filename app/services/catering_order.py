"""The day's food list (spec 9.12, B-12)."""

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.constants.booking import BookingStatus
from app.constants.roles import RoleCode
from app.models import Booking, BookingSession, CateringOrder
from app.schemas.catering_order import CateringOrderItem
from app.security import CurrentUser
from app.services import booking_access
from app.services import booking_transitions as transitions
from app.services.booking_view import booking_load_options, room_ref


def list_food_orders(session: Session, current: CurrentUser, day: date) -> list[CateringOrderItem]:
    """Food orders of bookings in IT setup or confirmed whose first session is on `day`.
    A Pitika sees their province (none: nothing); Admin sees every province. Sorted by
    delivery time, then room name."""
    first_day = (
        select(func.min(BookingSession.date))
        .where(BookingSession.booking_id == Booking.id)
        .scalar_subquery()
    )
    query = (
        select(Booking)
        .join(CateringOrder, CateringOrder.booking_id == Booking.id)
        .where(
            Booking.status.in_([BookingStatus.SETUP_IN_PROGRESS, BookingStatus.CONFIRMED]),
            first_day == day,
        )
        .options(*booking_load_options())
    )
    if not current.has_role(RoleCode.ADMIN):
        province = booking_access.pitika_province(current)
        query = query.where(Booking.room_id.in_(booking_access.room_ids_in_province(province)))

    rows = []
    for booking in session.scalars(query):
        start = transitions.first_start(booking)
        order = booking.catering_order
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
        )
        rows.append(((start.time(), booking.room.name_en, booking.id), item))
    rows.sort(key=lambda row: row[0])
    return [item for _key, item in rows]
