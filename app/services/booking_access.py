"""Who can see a booking, its door pass and its title (spec 8.1)."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.constants.booking import MASKED_TITLE
from app.constants.roles import RoleCode
from app.models import Booking, Room, it_ticket_staff
from app.security import CurrentUser
from app.services.province import get_room_province, get_user_province
from app.services.records import not_found


def room_province(room: Room) -> str:
    return get_room_province(room).code


def pitika_province(current: CurrentUser) -> str | None:
    """The province of the user's office, or None when they have no division."""
    province = get_user_province(current.user)
    return province.code if province else None


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


def load_visible_booking(session: Session, current: CurrentUser, booking_id: int) -> Booking:
    """404 when the booking does not exist or the user may not see it (the same answer)."""
    booking = session.get(Booking, booking_id)
    if booking is None or not can_view(session, current, booking):
        raise not_found()
    return booking


def visible_title(session: Session, current: CurrentUser, booking: Booking) -> str:
    """BR-PRV-01, BR-PRV-02: a private room's title is hidden from those who cannot view it."""
    if booking.room.is_private and not can_view(session, current, booking):
        return MASKED_TITLE
    return booking.meeting_title
