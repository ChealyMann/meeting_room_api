"""What bookings a room or place still has, for the guards on rooms, places and users
(spec section 12). Imports models, constants, errors and the clock only, so the room,
place and user services can use it without import cycles.
"""

from sqlalchemy import distinct, func, or_, select
from sqlalchemy.orm import Session

from app.constants.booking import BookingRoute, BookingStatus
from app.errors import AppError, ErrorCode
from app.models import Booking, BookingSession, Building, Floor, Room
from app.services import clock


def future_booking_count(session: Session, room_ids: list[int]) -> int:
    """Distinct bookings with a blocking session in these rooms that has not ended yet."""
    if not room_ids:
        return 0
    session_end = func.timestamp(BookingSession.date, BookingSession.end_time)
    return session.scalar(
        select(func.count(distinct(BookingSession.booking_id))).where(
            BookingSession.room_id.in_(room_ids),
            BookingSession.is_blocking.is_(True),
            session_end > clock.now_local(),
        )
    )


def check_no_future_bookings(session: Session, room_ids: list[int], place: str, field: str) -> None:
    """409 HAS_FUTURE_BOOKINGS when the rooms have future bookings. `place` is the word
    for what changes ("room", "floor", "building", "office"); `field` is `is_active` when it
    is turned off, else the field that moves it (B-21)."""
    count = future_booking_count(session, room_ids)
    if not count:
        return
    then = "Ask the bookers to cancel first." if field == "is_active" else "Move it after they end."
    message = f"This {place} has {count} future bookings. {then}"
    raise AppError(ErrorCode.HAS_FUTURE_BOOKINGS, 409, message, {field: message})


def pending_owner_count(session: Session, room_id: int) -> int:
    """Bookings waiting for the room owner, plus R2 bookings still waiting for Pitika
    (they reach the owner next, B-14)."""
    return session.scalar(
        select(func.count(Booking.id)).where(
            Booking.room_id == room_id,
            or_(
                Booking.status == BookingStatus.PENDING_OWNER,
                (Booking.status == BookingStatus.PENDING_PITIKA)
                & (Booking.route == BookingRoute.R2),
            ),
        )
    )


def private_room_ids_owned_by(session: Session, user_id: int) -> list[int]:
    return list(
        session.scalars(
            select(Room.id)
            .where(Room.room_owner_id == user_id, Room.is_private.is_(True))
            .order_by(Room.id)
        )
    )


def room_ids_in(
    session: Session,
    *,
    floor_id: int | None = None,
    building_id: int | None = None,
    location_id: int | None = None,
) -> list[int]:
    """Every room (active or not) in a floor, building or office."""
    query = select(Room.id).join(Floor, Floor.id == Room.floor_id)
    if floor_id is not None:
        query = query.where(Room.floor_id == floor_id)
    if building_id is not None:
        query = query.where(Floor.building_id == building_id)
    if location_id is not None:
        query = query.join(Building, Building.id == Floor.building_id).where(
            Building.location_id == location_id
        )
    return list(session.scalars(query.order_by(Room.id)))
