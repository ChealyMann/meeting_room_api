"""Pitika review of bookings (spec 9.11): list, approve (T3, T4, T5) and reject (T6)."""

from datetime import date

from sqlalchemy import exists, func, select
from sqlalchemy.orm import Session

from app.constants.booking import (
    BookingRoute,
    BookingStatus,
    RejectedBy,
    ReviewDecision,
    ReviewStage,
)
from app.errors import AppError, ErrorCode
from app.models import Booking, BookingReview, BookingSession, User
from app.security import CurrentUser
from app.services import booking_access
from app.services import booking_transitions as transitions
from app.services.booking import filter_display_status
from app.services.booking_view import booking_load_options
from app.services.clock import now_utc
from app.services.listing import apply_search, paginate
from app.services.records import not_found

STARTED_MESSAGE = "The meeting has started. It cannot be approved."


def _first_start_sql():
    """The local start of a booking's first session, as a correlated subquery."""
    return (
        select(func.min(func.timestamp(BookingSession.date, BookingSession.start_time)))
        .where(BookingSession.booking_id == Booking.id)
        .scalar_subquery()
    )


def list_pitika_bookings(
    session: Session,
    current: CurrentUser,
    page: int,
    size: int,
    status: str | None,
    date_from: date | None,
    date_to: date | None,
    room_id: int | None,
    q: str | None,
) -> dict:
    """Bookings of rooms in the Pitika's province, earliest first start first. No province
    means an empty list. `date_from` / `date_to` keep bookings with any session in the range."""
    province = booking_access.pitika_province(current)
    query = (
        select(Booking)
        .join(User, Booking.requester_id == User.id)
        .where(Booking.room_id.in_(booking_access.room_ids_in_province(province)))
        .options(*booking_load_options())
    )
    query = filter_display_status(query, status)
    if room_id is not None:
        query = query.where(Booking.room_id == room_id)
    if date_from is not None or date_to is not None:
        in_range = select(BookingSession.id).where(BookingSession.booking_id == Booking.id)
        if date_from is not None:
            in_range = in_range.where(BookingSession.date >= date_from)
        if date_to is not None:
            in_range = in_range.where(BookingSession.date <= date_to)
        query = query.where(exists(in_range))
    query = apply_search(
        query, q, [Booking.meeting_title, Booking.reference_code, User.name_en, User.name_kh]
    )
    query = query.order_by(_first_start_sql(), Booking.id)
    return paginate(session, query, page, size)


def _load_in_province(session: Session, current: CurrentUser, booking_id: int) -> Booking:
    """404 when the booking is missing or its room is outside the Pitika's province (B-08)."""
    booking = session.get(Booking, booking_id)
    province = booking_access.pitika_province(current)
    if (
        booking is None
        or province is None
        or booking_access.room_province(booking.room) != province
    ):
        raise not_found()
    return booking


def _check_pending(booking: Booking, version: int) -> None:
    """Spec 8.5 steps 4 and 5: the version, then the status."""
    transitions.check_version(booking, version)
    if booking.status != BookingStatus.PENDING_PITIKA:
        raise transitions.invalid_transition(booking)


def pitika_approve(
    session: Session, current: CurrentUser, booking_id: int, notes: str | None, version: int
) -> Booking:
    """T3 (R2: on to the owner), T4 (IT setup) or T5 (confirmed). BR-APR-03: not after the
    first session started."""
    booking = _load_in_province(session, current, booking_id)
    _check_pending(booking, version)
    if transitions.has_started(booking):
        raise AppError(ErrorCode.TIME_PASSED, 409, STARTED_MESSAGE)

    if booking.route == BookingRoute.R2:
        transitions.advance(session, booking, version, status=BookingStatus.PENDING_OWNER)
    else:
        transitions.after_last_review(session, booking, version)

    now = now_utc()
    booking.reviews.append(
        BookingReview(
            stage=ReviewStage.PITIKA,
            decision=ReviewDecision.APPROVED,
            reviewer_id=current.id,
            notes=notes,
            reviewed_at=now,
        )
    )
    order = booking.catering_order
    if order is not None:
        order.decided_by = current.id
        order.decided_at = now
        order.approver_notes = notes
    session.commit()
    return booking


def pitika_reject(
    session: Session, current: CurrentUser, booking_id: int, reason: str, version: int
) -> Booking:
    """T6. Allowed at any time while the booking waits for Pitika."""
    booking = _load_in_province(session, current, booking_id)
    _check_pending(booking, version)
    transitions.reject(
        session, booking, version, RejectedBy.PITIKA, current.id, reason, ReviewStage.PITIKA
    )
    session.commit()
    return booking
