"""Who can see a booking, its door pass and its title (spec 8.1)."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.constants.booking import MASKED_TITLE, BookingRoute
from app.constants.roles import RoleCode
from app.models import Booking, Building, Floor, Location, Room, it_ticket_staff
from app.security import CurrentUser
from app.services.province import get_room_province, get_user_province
from app.services.records import not_found


def room_province(room: Room) -> str:
    return get_room_province(room).code


def pitika_province(current: CurrentUser) -> str | None:
    """The province of the user's office, or None when they have no division."""
    province = get_user_province(current.user)
    return province.code if province else None


def room_ids_in_province(code: str | None):
    """A subquery of the ids of the rooms in a province (room, floor, building, location).
    A None code matches no room."""
    return (
        select(Room.id)
        .join(Floor, Room.floor_id == Floor.id)
        .join(Building, Floor.building_id == Building.id)
        .join(Location, Building.location_id == Location.id)
        .where(Location.province == code)
    )


def _is_pitika_of(current: CurrentUser, booking: Booking) -> bool:
    if not current.has_role(RoleCode.PITIKA):
        return False
    province = pitika_province(current)
    return province is not None and province == room_province(booking.room)


def _is_assigned_it_staff(session: Session, current: CurrentUser, booking: Booking) -> bool:
    ticket = booking.it_ticket
    if ticket is None or not current.has_role(RoleCode.IT_STAFF):
        return False
    assigned = select(it_ticket_staff.c.user_id).where(
        it_ticket_staff.c.ticket_id == ticket.id, it_ticket_staff.c.user_id == current.id
    )
    return session.scalar(assigned) is not None


def can_view(session: Session, current: CurrentUser, booking: Booking) -> bool:
    """Booker, Admin, the room owner, a Pitika of the room's province, the IT Lead once the
    booking is forwarded, or an IT Staff user assigned to the ticket."""
    if booking.requester_id == current.id or current.has_role(RoleCode.ADMIN):
        return True
    if booking.room.room_owner_id == current.id or _is_pitika_of(current, booking):
        return True
    ticket = booking.it_ticket
    if current.has_role(RoleCode.IT_LEAD) and ticket is not None and ticket.forwarded_at:
        return True
    return _is_assigned_it_staff(session, current, booking)


def is_door_pass_viewer(current: CurrentUser, booking: Booking) -> bool:
    """The role part of who sees the door pass. The endpoint also checks the booking is
    CONFIRMED. IT roles never see it."""
    return (
        booking.requester_id == current.id
        or current.has_role(RoleCode.ADMIN)
        or booking.room.room_owner_id == current.id
        or _is_pitika_of(current, booking)
    )


def load_booking_for_write(session: Session, booking_id: int) -> Booking:
    """B-31: the booking row read FOR UPDATE, with fresh values (404 when missing).

    Every write that checks the version loads the booking this way, so a second request
    at the same version waits here until the first commits, then sees the new version
    and stops with STALE_VERSION before it writes any child row."""
    booking = session.get(Booking, booking_id, with_for_update=True, populate_existing=True)
    if booking is None:
        raise not_found()
    return booking


def load_visible_booking(
    session: Session, current: CurrentUser, booking_id: int, *, for_write: bool = False
) -> Booking:
    """404 when the booking does not exist or the user may not see it (the same answer).
    `for_write=True` reads it with `load_booking_for_write`."""
    if for_write:
        booking = load_booking_for_write(session, booking_id)
    else:
        booking = session.get(Booking, booking_id)
    if booking is None or not can_view(session, current, booking):
        raise not_found()
    return booking


def is_private_booking(booking: Booking) -> bool:
    """B-30: the room is private now, or the booking was made while it was private (any
    route but R1). A room that turns shared does not show its old private bookings."""
    return booking.room.is_private or booking.route != BookingRoute.R1


def is_masked(session: Session, current: CurrentUser, booking: Booking) -> bool:
    """BR-PRV-01, BR-PRV-02: a private booking is masked for those who cannot view it."""
    return is_private_booking(booking) and not can_view(session, current, booking)


def visible_title(session: Session, current: CurrentUser, booking: Booking) -> str:
    """The real title, or MASKED_TITLE when the booking is masked for this user."""
    return MASKED_TITLE if is_masked(session, current, booking) else booking.meeting_title
