"""Booking use cases (spec section 9): check, send, read, list mine.

The answers are built in `booking_view`."""

from datetime import datetime
from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import Settings
from app.constants.booking import (
    BookingRoute,
    BookingStatus,
    DisplayStatus,
    ITStatus,
    ReviewDecision,
    ReviewStage,
)
from app.errors import AppError, ErrorCode
from app.models import (
    Booking,
    BookingParticipant,
    BookingReview,
    BookingSession,
    CateringOrder,
    CateringPackage,
    ITService,
    ITTicket,
    Room,
    User,
)
from app.schemas.booking import BookingCheck, BookingCheckResult, BookingCreate, Problem
from app.security import CurrentUser
from app.services import booking_access, booking_codes
from app.services import booking_scheduling as scheduling
from app.services import booking_transitions as transitions
from app.services.booking_view import booking_load_options
from app.services.clock import now_local, now_utc
from app.services.listing import apply_search, paginate
from app.services.records import _duplicate_field

# Tries to save a new reference code when the unique key says it is taken (spec 8.3).
REFERENCE_TRIES = 3


def _invalid(field: str, message: str) -> AppError:
    return AppError(ErrorCode.VALIDATION_ERROR, 422, "Invalid request.", {field: message})


def _room_not_found() -> AppError:
    return _invalid("room_id", "Room not found.")


def _session_key(item):
    return (item.date, item.start_time)


# --- Check (spec 9.3) ------------------------------------------------------------------


def check_booking(
    session: Session, current: CurrentUser, body: BookingCheck, settings: Settings
) -> BookingCheckResult:
    """Spec 9.3: run the checks in order and report the first problem. Saves nothing.

    A rule error is returned as `problem`, not raised. `route`, `first_status` and `steps`
    stay empty until the room is found and can be booked.
    """
    result = BookingCheckResult(
        route=None, first_status=None, steps=None, problem=None, warnings=[]
    )
    sessions = body.sessions
    now = now_local()
    room = None
    try:
        scheduling.check_session_shapes(sessions, settings, now.date())
        room = session.get(Room, body.room_id)
        if room is None:
            raise _room_not_found()
        scheduling.check_room_bookable(room)
        route = scheduling.pick_route(room, current.id, body.has_catering, body.has_it)
        result.route = route
        result.first_status = scheduling.first_status(route)
        result.steps = scheduling.steps_for(route, body.has_it)
        scheduling.check_room_hours(sessions, room)
        scheduling.check_not_past(sessions, now)
        scheduling.check_reviewer(session, room, route)
        scheduling.check_clashes(session, current, room, sessions)
    except AppError as error:
        result.problem = Problem(
            code=error.code.value, message=error.message, fields=error.fields or {}
        )
    if room is not None:
        result.warnings = scheduling.warnings_for(session, room, sessions, None)
    return result


# --- Send (spec 9.4, T1, T2) -----------------------------------------------------------


def requester_info(user: User) -> dict[str, Any]:
    """BR-FRM-06 (spec 8.4): the booker's details, copied when the booking is sent."""
    division = user.division
    department = division.department if division else None
    office = department.location if department else None
    return {
        "name_en": user.name_en,
        "name_kh": user.name_kh,
        "staff_id": user.staff_id,
        "position": user.position.name_en,
        "division": division.name_en if division else None,
        "department": department.name_en if department else None,
        "office": office.name_en if office else None,
        "email": user.email,
        "phone": user.phone,
    }


def _participant_emails(
    current: CurrentUser, attendees: int, emails: list[str], settings: Settings
) -> list[str]:
    """BR-FRM-03, BR-FRM-05, B-23. Emails are lowercase already; repeats and the booker's
    own email are dropped."""
    if not 1 <= attendees <= settings.booking_max_attendees:
        raise _invalid("attendees", f"Must be 1 to {settings.booking_max_attendees}.")
    own = current.user.email.lower()
    kept = [email for email in dict.fromkeys(emails) if email != own]
    if len(kept) > settings.booking_max_participants:
        raise _invalid("participant_emails", f"At most {settings.booking_max_participants} emails.")
    if attendees < len(kept) + 1:
        raise _invalid("attendees", "Attendees must be at least the participants plus you.")
    return kept


def _catalog_copy(
    session: Session, model, ids: list[int], field: str, label: str, name: str
) -> list[dict[str, Any]]:
    """Each id must exist (422 "<label> not found.") and be active (409 "This <name> is
    inactive."). Repeats are dropped. Returns the `[{id, name}]` copy saved on the booking."""
    copies = []
    for record_id in dict.fromkeys(ids):
        record = session.get(model, record_id)
        if record is None:
            raise _invalid(field, f"{label} not found.")
        if not record.is_active:
            message = f"This {name} is inactive."
            raise AppError(ErrorCode.INACTIVE_REFERENCE, 409, message, {field: message})
        copies.append({"id": record.id, "name": record.name})
    return copies


def _new_booking(
    current: CurrentUser,
    room: Room,
    body: BookingCreate,
    route: BookingRoute,
    emails: list[str],
    packages: list[dict] | None,
    services: list[dict] | None,
    reference_code: str,
) -> Booking:
    """The booking and its child rows, not yet saved."""
    booking = Booking(
        reference_code=reference_code,
        requester_id=current.id,
        room_id=room.id,
        requester_info=requester_info(current.user),
        meeting_title=body.meeting_title,
        meeting_type=body.meeting_type,
        meeting_purpose=body.meeting_purpose,
        attendees=body.attendees,
        private_justification=body.private_justification,
        route=route,
        status=scheduling.first_status(route),
        version=1,
    )
    booking.sessions = [
        BookingSession(
            room_id=room.id,
            date=item.date,
            start_time=item.start_time,
            end_time=item.end_time,
            is_blocking=True,
        )
        for item in sorted(body.sessions, key=_session_key)
    ]
    booking.participants = [BookingParticipant(email=email) for email in emails]
    if packages is not None:
        booking.catering_order = CateringOrder(packages=packages, remarks=body.catering.remarks)
    if services is not None:
        booking.it_ticket = ITTicket(
            requested_items=services,
            special_requirements=body.it.special_requirements,
            status=ITStatus.RECEIVED,
        )
    if route == BookingRoute.R3:
        # T2: the owner books their own room; no review is needed.
        booking.reviews = [
            BookingReview(
                stage=ReviewStage.PITIKA,
                decision=ReviewDecision.NOT_REQUIRED,
                reviewer_id=None,
                reviewed_at=now_utc(),
            )
        ]
    return booking


def _insert_booking(session: Session, now: datetime, make) -> Booking:
    """Save `make(reference_code)`. When the unique key says the code was taken meanwhile,
    draw a new one; at most REFERENCE_TRIES tries."""
    attempt = 1
    while True:
        booking = make(booking_codes.new_reference_code(session, now))
        try:
            with session.begin_nested():
                session.add(booking)
                session.flush()
            return booking
        except IntegrityError as exc:
            if attempt >= REFERENCE_TRIES or _duplicate_field(exc) != "reference_code":
                raise
            attempt += 1


def create_booking(
    session: Session, current: CurrentUser, body: BookingCreate, settings: Settings
) -> tuple[Booking, list[dict]]:
    """Spec 9.4: checks in order, then lock the room, check clashes and save it all in one
    transaction. Returns the booking and its warnings."""
    now = now_local()
    scheduling.check_session_shapes(body.sessions, settings, now.date())
    emails = _participant_emails(current, body.attendees, body.participant_emails, settings)

    room = session.get(Room, body.room_id)
    if room is None:
        raise _room_not_found()
    scheduling.check_room_bookable(room)
    scheduling.check_room_hours(body.sessions, room)
    scheduling.check_not_past(body.sessions, now)

    route = scheduling.pick_route(room, current.id, body.catering is not None, body.it is not None)
    scheduling.check_reviewer(session, room, route)
    if route == BookingRoute.R2 and not body.private_justification:
        raise _invalid("private_justification", "Explain why you need this private room.")

    packages = services = None
    if body.catering is not None:
        packages = _catalog_copy(
            session,
            CateringPackage,
            body.catering.package_ids,
            "catering.package_ids",
            "Package",
            "package",
        )
    if body.it is not None:
        services = _catalog_copy(
            session, ITService, body.it.service_ids, "it.service_ids", "IT service", "IT service"
        )

    # BR-SCH-08: one booking at a time per room, so two requests cannot both pass the
    # clash check. The lock is held until the commit. The clash check is a locking read:
    # a plain SELECT would read this transaction's old snapshot (REPEATABLE READ) and miss
    # a booking the other request committed while we waited for the lock.
    session.execute(select(Room.id).where(Room.id == room.id).with_for_update())
    scheduling.check_clashes(session, current, room, body.sessions, locking=True)

    booking = _insert_booking(
        session,
        now,
        lambda code: _new_booking(current, room, body, route, emails, packages, services, code),
    )
    if route == BookingRoute.R3:
        transitions.add_door_pass(session, booking)
    session.commit()
    warnings = scheduling.warnings_for(session, room, body.sessions, body.attendees)
    return booking, warnings


# --- Read (spec 9.5, 9.6) --------------------------------------------------------------


def get_booking(session: Session, current: CurrentUser, booking_id: int) -> Booking:
    """404 when missing or not visible to this user (B-08)."""
    return booking_access.load_visible_booking(session, current, booking_id)


def _last_end_sql():
    """The local end of a booking's last session, as a correlated subquery."""
    return (
        select(func.max(func.timestamp(BookingSession.date, BookingSession.end_time)))
        .where(BookingSession.booking_id == Booking.id)
        .scalar_subquery()
    )


def filter_display_status(query: Select, status: str | None) -> Select:
    """`?status=` is a display status (B-10): CONFIRMED means not yet ended; COMPLETED
    means confirmed and ended. Empty means no filter; anything else is 422."""
    if status is None or not status.strip():
        return query
    try:
        wanted = DisplayStatus(status.strip())
    except ValueError:
        choices = ", ".join(DisplayStatus)
        raise _invalid("status", f"Must be one of {choices}.") from None
    if wanted == DisplayStatus.COMPLETED:
        return query.where(
            Booking.status == BookingStatus.CONFIRMED, _last_end_sql() <= now_local()
        )
    if wanted == DisplayStatus.CONFIRMED:
        return query.where(Booking.status == BookingStatus.CONFIRMED, _last_end_sql() > now_local())
    return query.where(Booking.status == wanted.value)


def list_my_bookings(
    session: Session,
    current: CurrentUser,
    page: int,
    size: int,
    status: str | None,
    q: str | None,
) -> dict:
    """The user's own bookings, newest first. `q` matches the title or reference code."""
    query = (
        select(Booking).where(Booking.requester_id == current.id).options(*booking_load_options())
    )
    query = filter_display_status(query, status)
    query = apply_search(query, q, [Booking.meeting_title, Booking.reference_code])
    query = query.order_by(Booking.created_at.desc(), Booking.id.desc())
    return paginate(session, query, page, size)
