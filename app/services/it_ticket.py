"""IT tickets (spec 9.14): the IT Lead's queue, assigning IT Staff (T10) and Ready (T11).

A ticket is visible once it was forwarded and its booking is not REJECTED or CANCELLED
(BR-IT-01). The IT Lead sees all; a user with only IT_STAFF sees the tickets they are
assigned to. The `version` in a request is the booking's (B-19).
"""

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.config import Settings
from app.constants.booking import (
    BookingStatus,
    ITStatus,
    ReviewDecision,
)
from app.constants.roles import RoleCode
from app.errors import AppError, ErrorCode
from app.models import Booking, ITTicket, User, it_ticket_staff
from app.schemas.it_ticket import ITStaffOut, ITTicketItem
from app.security import CurrentUser, load_role_codes
from app.services import booking_transitions as transitions
from app.services import booking_view
from app.services.booking_review import first_start_sql
from app.services.clock import now_utc
from app.services.listing import apply_search, paginate
from app.services.records import not_found

NOT_ACTIVE_STAFF = "This user is not active IT Staff."
NO_ACTIVE_STAFF = "Assign active IT Staff first."
_HIDDEN = (BookingStatus.REJECTED.value, BookingStatus.CANCELLED.value)


def _invalid(field: str, message: str) -> AppError:
    return AppError(ErrorCode.VALIDATION_ERROR, 422, "Invalid request.", {field: message})


def _visible(query, current: CurrentUser):
    """Keep the tickets `current` may see. The query must join `Booking`."""
    query = query.where(ITTicket.forwarded_at.is_not(None), Booking.status.not_in(_HIDDEN))
    if not current.has_role(RoleCode.IT_LEAD):
        assigned = select(it_ticket_staff.c.ticket_id).where(
            it_ticket_staff.c.user_id == current.id
        )
        query = query.where(ITTicket.id.in_(assigned))
    return query


def _load_visible(session: Session, current: CurrentUser, ticket_id: int) -> ITTicket:
    """404 when the ticket is missing, not forwarded yet, hidden, or not the user's."""
    query = select(ITTicket).join(Booking, ITTicket.booking_id == Booking.id)
    ticket = session.scalars(_visible(query, current).where(ITTicket.id == ticket_id)).first()
    if ticket is None:
        raise not_found()
    return ticket


# --- Read ------------------------------------------------------------------------------


def list_tickets(
    session: Session, current: CurrentUser, page: int, size: int, status: str | None, q: str | None
) -> dict:
    """Visible tickets, earliest first start first."""
    query = (
        select(ITTicket)
        .join(Booking, ITTicket.booking_id == Booking.id)
        .join(User, Booking.requester_id == User.id)
        .options(
            selectinload(ITTicket.staff),
            selectinload(ITTicket.booking).options(
                *booking_view.booking_load_options(), selectinload(Booking.reviews)
            ),
        )
    )
    query = _visible(query, current)
    status = (status or "").strip()
    if status:
        try:
            query = query.where(ITTicket.status == ITStatus(status).value)
        except ValueError:
            choices = ", ".join(ITStatus)
            raise _invalid("status", f"Must be one of {choices}.") from None
    query = apply_search(query, q, [Booking.meeting_title, Booking.reference_code])
    query = query.order_by(first_start_sql(), ITTicket.id)
    return paginate(session, query, page, size)


def build_ticket_items(
    session: Session, tickets: list[ITTicket], settings: Settings
) -> list[ITTicketItem]:
    """Answers for `tickets`. Their bookings, staff and reviews should be preloaded."""
    bookings = booking_view.build_booking_list_items(session, [t.booking for t in tickets])
    items = []
    for ticket, booking_item in zip(tickets, bookings, strict=True):
        booking = ticket.booking
        setup = transitions.setup_start(booking, settings.it_setup_lead_minutes)
        items.append(
            ITTicketItem(
                id=ticket.id,
                status=ticket.status,
                items=ticket.requested_items,
                special_requirements=ticket.special_requirements,
                technician_notes=ticket.technician_notes,
                staff=[ITStaffOut.model_validate(user) for user in ticket.staff],
                setup_date=setup.date(),
                setup_time=setup.time(),
                forwarded_at=ticket.forwarded_at,
                assigned_at=ticket.assigned_at,
                ready_at=ticket.ready_at,
                review_notes=[
                    review.notes
                    for review in booking.reviews
                    if review.decision == ReviewDecision.APPROVED and review.notes
                ],
                booking=booking_item,
            )
        )
    return items


# --- T10: assign -----------------------------------------------------------------------


def _check_open(ticket: ITTicket, version: int) -> Booking:
    """Spec 8.5 steps 4 and 5: the booking's version, then it must be in IT setup."""
    booking = ticket.booking
    transitions.check_version(booking, version)
    if booking.status != BookingStatus.SETUP_IN_PROGRESS:
        raise transitions.invalid_transition(booking)
    return booking


def _active_it_staff(session: Session, user_ids: list[int]) -> list[User]:
    """Every id must be a user (422 `user_ids`) who is active with the IT_STAFF role (409)."""
    users = []
    for user_id in dict.fromkeys(user_ids):
        user = session.get(User, user_id)
        if user is None:
            raise _invalid("user_ids", "User not found.")
        users.append(user)
    for user in users:
        if not user.is_active or RoleCode.IT_STAFF not in load_role_codes(session, user.id):
            raise AppError(
                ErrorCode.INACTIVE_REFERENCE, 409, NOT_ACTIVE_STAFF, {"user_ids": NOT_ACTIVE_STAFF}
            )
    return users


def assign_staff(
    session: Session,
    current: CurrentUser,
    ticket_id: int,
    user_ids: list[int],
    technician_notes: str | None,
    version: int,
) -> ITTicket:
    """T10 (BR-IT-02). The new list replaces the old one; the booking version goes up by 1."""
    ticket = _load_visible(session, current, ticket_id)
    booking = _check_open(ticket, version)
    if ticket.status == ITStatus.READY:
        raise transitions.invalid_transition(booking)
    users = _active_it_staff(session, user_ids)

    ticket.staff = sorted(users, key=lambda user: user.name_en)
    ticket.status = ITStatus.ASSIGNED.value
    ticket.assigned_at = now_utc()
    ticket.technician_notes = technician_notes
    transitions.advance(session, booking, version)
    session.commit()
    return ticket


# --- T11: ready ------------------------------------------------------------------------


def mark_ready(session: Session, current: CurrentUser, ticket_id: int, version: int) -> ITTicket:
    """T11 (BR-IT-03, B-22): needs at least one active assigned IT Staff. Confirms the booking."""
    ticket = _load_visible(session, current, ticket_id)
    booking = _check_open(ticket, version)
    if ticket.status != ITStatus.ASSIGNED or not any(user.is_active for user in ticket.staff):
        raise transitions.invalid_transition(booking, NO_ACTIVE_STAFF)

    ticket.status = ITStatus.READY.value
    ticket.ready_at = now_utc()
    transitions.make_confirmed(session, booking, version)
    session.commit()
    return ticket
