"""Every status change of a booking goes through here (spec 8.5). Nothing else writes
`bookings.status`.

`advance` is the version guard: a conditional UPDATE that only hits the row when its
version is still the one the person saw (B-04). The times (first start, last end) are
local Phnom Penh times; "now" comes from `clock`.
"""

from datetime import datetime, timedelta

from sqlalchemy import Select, func, select, update
from sqlalchemy.orm import Session

from app.constants.booking import (
    BookingStatus,
    DisplayStatus,
    RejectedBy,
    ReviewDecision,
    ReviewStage,
)
from app.errors import AppError, ErrorCode
from app.models import (
    Booking,
    BookingDoorPass,
    BookingRejection,
    BookingReview,
    BookingSession,
)
from app.services import booking_codes, clock

STALE_MESSAGE = "This booking changed. Reload it."

# INVALID_TRANSITION messages, by what the reader sees (spec 8.5 step 5).
_STATUS_MESSAGES = {
    DisplayStatus.PENDING_PITIKA: "This booking is waiting for Pitika.",
    DisplayStatus.PENDING_OWNER: "This booking is waiting for the room owner.",
    DisplayStatus.SETUP_IN_PROGRESS: "This booking is in IT setup.",
    DisplayStatus.CONFIRMED: "This booking is already confirmed.",
    DisplayStatus.REJECTED: "This booking was rejected.",
    DisplayStatus.CANCELLED: "This booking was cancelled.",
    DisplayStatus.COMPLETED: "This booking is completed.",
}


# --- Times -----------------------------------------------------------------------------
# Each Python helper has its SQL twin (a correlated subquery on `Booking.id`) for queries.


def first_start(booking: Booking) -> datetime:
    """Local start of the earliest session."""
    return min(clock.session_start(s) for s in booking.sessions)


def first_start_sql():
    """`first_start` in SQL: the local start of a booking's first session."""
    return (
        select(func.min(func.timestamp(BookingSession.date, BookingSession.start_time)))
        .where(BookingSession.booking_id == Booking.id)
        .scalar_subquery()
    )


def first_day_sql():
    """The date of a booking's first session (the day of `first_start`), in SQL."""
    return (
        select(func.min(BookingSession.date))
        .where(BookingSession.booking_id == Booking.id)
        .scalar_subquery()
    )


def last_end(booking: Booking) -> datetime:
    """Local end of the latest session."""
    return max(clock.session_end(s) for s in booking.sessions)


def last_end_sql():
    """`last_end` in SQL: the local end of a booking's last session."""
    return (
        select(func.max(func.timestamp(BookingSession.date, BookingSession.end_time)))
        .where(BookingSession.booking_id == Booking.id)
        .scalar_subquery()
    )


def has_started(booking: Booking) -> bool:
    return clock.now_local() >= first_start(booking)


def has_ended(booking: Booking) -> bool:
    return clock.now_local() >= last_end(booking)


def display_status(booking: Booking) -> DisplayStatus:
    """B-10: a confirmed booking whose last session has ended shows as COMPLETED."""
    if booking.status == BookingStatus.CONFIRMED and has_ended(booking):
        return DisplayStatus.COMPLETED
    return DisplayStatus(booking.status)


def filter_display_status(query: Select, status: str | None) -> Select:
    """`display_status` in SQL, for `?status=` (B-10): CONFIRMED means not yet ended;
    COMPLETED means confirmed and ended. Empty means no filter; anything else is 422."""
    if status is None or not status.strip():
        return query
    try:
        wanted = DisplayStatus(status.strip())
    except ValueError:
        message = f"Must be one of {', '.join(DisplayStatus)}."
        raise AppError(
            ErrorCode.VALIDATION_ERROR, 422, "Invalid request.", {"status": message}
        ) from None
    confirmed = Booking.status == BookingStatus.CONFIRMED
    if wanted == DisplayStatus.COMPLETED:
        return query.where(confirmed, last_end_sql() <= clock.now_local())
    if wanted == DisplayStatus.CONFIRMED:
        return query.where(confirmed, last_end_sql() > clock.now_local())
    return query.where(Booking.status == wanted.value)


def setup_start(booking: Booking, lead_minutes: int) -> datetime:
    """BR-IT-05: IT setup is planned `lead_minutes` before the first session."""
    return first_start(booking) - timedelta(minutes=lead_minutes)


# --- Guards ----------------------------------------------------------------------------


def _stale() -> AppError:
    return AppError(ErrorCode.STALE_VERSION, 409, STALE_MESSAGE)


def check_version(booking: Booking, version: int) -> None:
    """The version the person saw must still be current (409 STALE_VERSION)."""
    if booking.version != version:
        raise _stale()


def invalid_transition(booking: Booking, message: str | None = None) -> AppError:
    """409 INVALID_TRANSITION. The default message names the booking's display status."""
    return AppError(
        ErrorCode.INVALID_TRANSITION, 409, message or _STATUS_MESSAGES[display_status(booking)]
    )


# --- Writes ----------------------------------------------------------------------------


def advance(session: Session, booking: Booking, version: int, **values) -> None:
    """Write `values` and raise the version by 1, only if the row is still at `version`.

    `UPDATE bookings SET <values>, version = version + 1, updated_at = :now
    WHERE id = :id AND version = :version`. No row hit -> 409 STALE_VERSION.
    With no `values` it only raises the version (an edit of other fields or child rows).
    """
    # Send pending ORM changes first (autoflush is off): `refresh` below would drop them.
    session.flush()
    statement = (
        update(Booking)
        .where(Booking.id == booking.id, Booking.version == version)
        .values(**values, version=Booking.version + 1, updated_at=clock.now_utc())
        .execution_options(synchronize_session=False)
    )
    if session.execute(statement).rowcount == 0:
        raise _stale()
    session.refresh(booking)


def stop_blocking(session: Session, booking: Booking) -> None:
    """The booking's sessions no longer hold the room (B-11). The rows stay."""
    session.execute(
        update(BookingSession)
        .where(BookingSession.booking_id == booking.id)
        .values(is_blocking=False)
    )


def cancel(session: Session, booking: Booking, version: int, reason: str | None) -> None:
    """T12 and B-27: CANCELLED with the time and the reason; the sessions stop blocking."""
    advance(
        session,
        booking,
        version,
        status=BookingStatus.CANCELLED,
        cancelled_at=clock.now_utc(),
        cancel_reason=reason,
    )
    stop_blocking(session, booking)


def add_door_pass(session: Session, booking: Booking) -> None:
    """The door pass of a confirmed booking; it expires at the last session's end (UTC)."""
    booking.door_pass = BookingDoorPass(
        passcode=booking_codes.new_door_pass_code(session, booking.reference_code),
        expires_at=clock.local_to_utc(last_end(booking)),
    )
    session.flush()


def reject(
    session: Session,
    booking: Booking,
    version: int,
    by: RejectedBy,
    actor_id: int | None,
    reason: str,
    stage: ReviewStage | None,
) -> None:
    """T6, T9, T15. `stage` adds a REJECTED review row (none for the system)."""
    advance(session, booking, version, status=BookingStatus.REJECTED)
    stop_blocking(session, booking)
    now = clock.now_utc()
    booking.rejection = BookingRejection(
        rejected_by=by, actor_user_id=actor_id, reason=reason, decided_at=now
    )
    if stage is not None:
        booking.reviews.append(
            BookingReview(
                stage=stage,
                decision=ReviewDecision.REJECTED,
                reviewer_id=actor_id,
                notes=reason,
                reviewed_at=now,
            )
        )
    session.flush()


def make_confirmed(session: Session, booking: Booking, version: int) -> None:
    """T5, T8, T11, T17: confirmed, with a door pass."""
    advance(session, booking, version, status=BookingStatus.CONFIRMED)
    add_door_pass(session, booking)


def forward_it(session: Session, booking: Booking, version: int) -> None:
    """T4, T7: the IT ticket goes to the IT Lead."""
    advance(session, booking, version, status=BookingStatus.SETUP_IN_PROGRESS)
    booking.it_ticket.forwarded_at = clock.now_utc()
    session.flush()


def after_last_review(session: Session, booking: Booking, version: int) -> None:
    """The last reviewer approved: IT setup when there is an IT ticket, else confirmed."""
    if booking.it_ticket is not None:
        forward_it(session, booking, version)
    else:
        make_confirmed(session, booking, version)
