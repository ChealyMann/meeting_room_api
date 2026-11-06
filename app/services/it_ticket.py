"""IT tickets (spec 9.14): the IT Lead's queue, assigning IT Staff (T10) and Ready (T11).

A ticket is visible once it was forwarded and its booking is not REJECTED or CANCELLED
(BR-IT-01). The IT Lead sees all; a user with only IT_STAFF sees the tickets they are
assigned to. The `version` in a request is the booking's (B-19).
"""

from datetime import date, datetime, time, timedelta

from sqlalchemy import Select, and_, func, literal_column, or_, select
from sqlalchemy.orm import Session, selectinload

from app.config import Settings
from app.constants.booking import (
    BookingStatus,
    ITStatus,
    ReviewDecision,
)
from app.constants.roles import RoleCode
from app.errors import AppError, ErrorCode
from app.models import Booking, ITTicket, Role, User, it_ticket_staff, user_roles
from app.schemas.it_ticket import ITBusy, ITStaffOut, ITStaffPick, ITTicketItem
from app.security import CurrentUser, load_role_codes
from app.services import booking_access, booking_view
from app.services import booking_transitions as transitions
from app.services.clock import local_to_utc, now_local, now_utc
from app.services.listing import apply_search, paginate
from app.services.records import not_found
from app.services.user_avatar import avatar_url

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


STATES = ("to_assign", "in_progress", "done")


def _missed_sql():
    """Not Ready and the meeting has started (spec Part B, "Missed setup"): the ticket can no
    longer change (T17 confirms the booking at the start)."""
    return and_(
        ITTicket.status != ITStatus.READY.value,
        transitions.first_start_sql() <= now_local(),
    )


def _in_state(query: Select, state: str) -> Select:
    """The dashboard tabs: to assign, in progress (both without missed ones), and done (Ready
    or missed)."""
    if state == "to_assign":
        return query.where(ITTicket.status == ITStatus.RECEIVED.value, ~_missed_sql())
    if state == "in_progress":
        return query.where(ITTicket.status == ITStatus.ASSIGNED.value, ~_missed_sql())
    return query.where(or_(ITTicket.status == ITStatus.READY.value, _missed_sql()))


def _mine(query: Select, current: CurrentUser) -> Select:
    assigned = select(it_ticket_staff.c.ticket_id).where(it_ticket_staff.c.user_id == current.id)
    return query.where(ITTicket.id.in_(assigned))


def list_tickets(
    session: Session,
    current: CurrentUser,
    page: int,
    size: int,
    status: str | None,
    q: str | None,
    state: str | None = None,
    mine: bool = False,
    date_from: date | None = None,
    date_to: date | None = None,
) -> dict:
    """Visible tickets, earliest first start first; `state="done"` newest first (made ready,
    or the meeting start of a missed one). `date_from` / `date_to`: the first session's day
    (the setup day). `mine`: only tickets assigned to me."""
    if date_from is not None and date_to is not None and date_to < date_from:
        raise _invalid("to", "Must be on or after from.")
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
    if state is not None:
        if state not in STATES:
            raise _invalid("state", f"Must be one of {', '.join(STATES)}.")
        query = _in_state(query, state)
    if mine:
        query = _mine(query, current)
    first_day = transitions.first_day_sql()
    if date_from is not None:
        query = query.where(first_day >= date_from)
    if date_to is not None:
        query = query.where(first_day <= date_to)
    query = apply_search(query, q, [Booking.meeting_title, Booking.reference_code])
    if state == "done":
        # Newest first: when it was made ready, or (missed) when the meeting started, both as
        # Phnom Penh time (ready_at is UTC).
        ready_local = func.timestampadd(literal_column("HOUR"), 7, ITTicket.ready_at)
        moment = func.coalesce(ready_local, transitions.first_start_sql())
        query = query.order_by(moment.desc(), ITTicket.id.desc())
    else:
        query = query.order_by(transitions.first_start_sql(), ITTicket.id)
    return paginate(session, query, page, size)


def ticket_summary(session: Session, current: CurrentUser) -> dict[str, int]:
    """The IT Lead's day: to assign and in progress now (missed left out), made ready today,
    and today's setups (first session today, Phnom Penh) with how many are ready."""
    base = select(func.count(ITTicket.id)).join(Booking, ITTicket.booking_id == Booking.id)
    base = _visible(base, current)

    def count(query) -> int:
        return session.scalar(query) or 0

    today = now_local().date()
    start = local_to_utc(datetime.combine(today, time()))
    first_day = transitions.first_day_sql()
    return {
        "to_assign": count(_in_state(base, "to_assign")),
        "in_progress": count(_in_state(base, "in_progress")),
        "ready_today": count(
            base.where(ITTicket.ready_at >= start, ITTicket.ready_at < start + timedelta(days=1))
        ),
        "due_today": count(base.where(first_day == today)),
        "due_today_ready": count(
            base.where(first_day == today, ITTicket.status == ITStatus.READY.value)
        ),
    }


def list_it_staff(session: Session) -> list[User]:
    """Active users with the IT_STAFF role, by English name (the assign picker)."""
    query = (
        select(User)
        .join(user_roles, user_roles.c.user_id == User.id)
        .join(Role, Role.id == user_roles.c.role_id)
        .where(User.is_active, Role.code == RoleCode.IT_STAFF.value)
        .order_by(User.name_en, User.id)
    )
    return list(session.scalars(query).unique())


def staff_out(user: User) -> ITStaffOut:
    return ITStaffOut(
        id=user.id,
        name_en=user.name_en,
        name_kh=user.name_kh,
        is_active=user.is_active,
        avatar_url=avatar_url(user),
    )


def _busy_at_the_same_time(
    session: Session, settings: Settings, target: ITTicket, user_ids: list[int]
) -> dict[int, list[ITBusy]]:
    """Per user: their other visible setups whose time (set-up to meeting start) overlaps the
    target's. Both last `it_setup_lead_minutes`, so they overlap when the meetings start less
    than that apart."""
    lead = timedelta(minutes=settings.it_setup_lead_minutes)
    start = transitions.first_start(target.booking)
    day = start.date()
    first_day = transitions.first_day_sql()
    query = (
        select(ITTicket)
        .join(Booking, ITTicket.booking_id == Booking.id)
        .where(
            ITTicket.id != target.id,
            ITTicket.forwarded_at.is_not(None),
            Booking.status.not_in(_HIDDEN),
            first_day.between(day - timedelta(days=1), day + timedelta(days=1)),
            ITTicket.id.in_(
                select(it_ticket_staff.c.ticket_id).where(it_ticket_staff.c.user_id.in_(user_ids))
            ),
        )
        .options(
            selectinload(ITTicket.staff),
            selectinload(ITTicket.booking).options(
                selectinload(Booking.sessions), selectinload(Booking.room)
            ),
        )
    )
    busy: dict[int, list[ITBusy]] = {}
    for ticket in session.scalars(query).unique():
        other = transitions.first_start(ticket.booking)
        if abs(other - start) >= lead:
            continue
        entry = ITBusy(
            ticket_id=ticket.id,
            room_name_en=ticket.booking.room.name_en,
            setup_time=(other - lead).time(),
            meeting_start=other.time(),
        )
        for user in ticket.staff:
            if user.id in user_ids:
                busy.setdefault(user.id, []).append(entry)
    for entries in busy.values():
        entries.sort(key=lambda e: (e.meeting_start, e.ticket_id))
    return busy


def staff_picks(
    session: Session,
    settings: Settings,
    current: CurrentUser,
    day: date | None,
    ticket_id: int | None = None,
) -> list[ITStaffPick]:
    """The assign picker: active IT Staff by name; with `day`, how many setups (visible
    tickets whose first session is that day) each one already has. With `ticket_id` (404 when
    hidden): that ticket's day, and each one's other setups at the same time."""
    users = list_it_staff(session)
    target = _load_visible(session, current, ticket_id) if ticket_id is not None else None
    if target is not None and day is None:
        day = transitions.first_start(target.booking).date()
    busy = (
        _busy_at_the_same_time(session, settings, target, [u.id for u in users])
        if target is not None and users
        else {}
    )
    counts: dict[int, int] = {}
    if day is not None and users:
        query = (
            select(it_ticket_staff.c.user_id, func.count(ITTicket.id))
            .join(ITTicket, ITTicket.id == it_ticket_staff.c.ticket_id)
            .join(Booking, ITTicket.booking_id == Booking.id)
            .where(
                ITTicket.forwarded_at.is_not(None),
                Booking.status.not_in(_HIDDEN),
                transitions.first_day_sql() == day,
                it_ticket_staff.c.user_id.in_([u.id for u in users]),
            )
            .group_by(it_ticket_staff.c.user_id)
        )
        counts = {user_id: n for user_id, n in session.execute(query)}
    return [
        ITStaffPick(
            **staff_out(user).model_dump(),
            setups_that_day=None if day is None else counts.get(user.id, 0),
            busy=None if target is None else busy.get(user.id, []),
        )
        for user in users
    ]


def build_ticket_items(tickets: list[ITTicket], settings: Settings) -> list[ITTicketItem]:
    """Answers for `tickets`. Their bookings, staff and reviews should be preloaded."""
    bookings = booking_view.build_booking_list_items([t.booking for t in tickets])
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
                staff=[staff_out(user) for user in ticket.staff],
                setup_date=setup.date(),
                setup_time=setup.time(),
                forwarded_at=ticket.forwarded_at,
                assigned_at=ticket.assigned_at,
                ready_at=ticket.ready_at,
                missed=ticket.status != ITStatus.READY and transitions.has_started(booking),
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


def _load_for_write(
    session: Session, current: CurrentUser, ticket_id: int
) -> tuple[ITTicket, Booking]:
    """The visible ticket (else 404) and its booking, read for a write (B-31)."""
    ticket = _load_visible(session, current, ticket_id)
    return ticket, booking_access.load_booking_for_write(session, ticket.booking_id)


def _check_open(booking: Booking, version: int) -> None:
    """Spec 8.5 steps 4 and 5: the booking's version, then it must be in IT setup."""
    transitions.check_version(booking, version)
    if booking.status != BookingStatus.SETUP_IN_PROGRESS:
        raise transitions.invalid_transition(booking)


def _is_active_it_staff(session: Session, user: User) -> bool:
    """Active and still holding the IT_STAFF role."""
    return user.is_active and RoleCode.IT_STAFF in load_role_codes(session, user.id)


def _active_it_staff(session: Session, user_ids: list[int]) -> list[User]:
    """Every id must be a user (422 `user_ids`) who is active with the IT_STAFF role (409)."""
    users = []
    for user_id in dict.fromkeys(user_ids):
        user = session.get(User, user_id)
        if user is None:
            raise _invalid("user_ids", "User not found.")
        users.append(user)
    for user in users:
        if not _is_active_it_staff(session, user):
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
    ticket, booking = _load_for_write(session, current, ticket_id)
    _check_open(booking, version)
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
    """T11 (BR-IT-03, B-22): needs at least one assigned user who is active and still holds
    IT_STAFF. Confirms the booking."""
    ticket, booking = _load_for_write(session, current, ticket_id)
    _check_open(booking, version)
    staff_ready = any(_is_active_it_staff(session, user) for user in ticket.staff)
    if ticket.status != ITStatus.ASSIGNED or not staff_ready:
        raise transitions.invalid_transition(booking, NO_ACTIVE_STAFF)

    ticket.status = ITStatus.READY.value
    ticket.ready_at = now_utc()
    transitions.make_confirmed(session, booking, version)
    session.commit()
    return ticket
