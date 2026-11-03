"""Review of bookings by Pitika (spec 9.11: T3, T4, T5, T6) and by the room owner
(spec 9.13: T7, T8, T9): list, approve and reject."""

from datetime import date

from sqlalchemy import exists, select
from sqlalchemy.orm import Session

from app.constants.booking import (
    BookingRoute,
    BookingStatus,
    RejectedBy,
    ReviewDecision,
    ReviewStage,
)
from app.errors import AppError, ErrorCode
from app.models import Booking, BookingReview, BookingSession, Room, User
from app.security import CurrentUser
from app.services import booking_access
from app.services import booking_transitions as transitions
from app.services.booking_view import booking_load_options
from app.services.clock import now_utc
from app.services.listing import apply_search, paginate
from app.services.records import not_found

STARTED_MESSAGE = "The meeting has started. It cannot be approved."


def _list_in_rooms(
    session: Session,
    room_ids,
    page: int,
    size: int,
    status: str | None,
    date_from: date | None,
    date_to: date | None,
    room_id: int | None,
    q: str | None,
) -> dict:
    """Bookings of the rooms in the `room_ids` subquery, earliest first start first.
    `date_from` / `date_to` keep bookings with any session in the range."""
    query = (
        select(Booking)
        .join(User, Booking.requester_id == User.id)
        .where(Booking.room_id.in_(room_ids))
        .options(*booking_load_options())
    )
    query = transitions.filter_display_status(query, status)
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
    query = query.order_by(transitions.first_start_sql(), Booking.id)
    return paginate(session, query, page, size)


def _check_waiting(booking: Booking, version: int, status: BookingStatus) -> None:
    """Spec 8.5 steps 4 and 5: the version, then the status."""
    transitions.check_version(booking, version)
    if booking.status != status:
        raise transitions.invalid_transition(booking)


def _check_not_started(booking: Booking) -> None:
    """BR-APR-03, B-09: nobody approves after the first session started."""
    if transitions.has_started(booking):
        raise AppError(ErrorCode.TIME_PASSED, 409, STARTED_MESSAGE)


def _add_review(
    booking: Booking, stage: ReviewStage, current: CurrentUser, notes: str | None, now
) -> None:
    booking.reviews.append(
        BookingReview(
            stage=stage,
            decision=ReviewDecision.APPROVED,
            reviewer_id=current.id,
            notes=notes,
            reviewed_at=now,
        )
    )


# --- Pitika ----------------------------------------------------------------------------


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
    """Bookings of rooms in the Pitika's province. No province means an empty list."""
    province = booking_access.pitika_province(current)
    rooms = booking_access.room_ids_in_province(province)
    return _list_in_rooms(session, rooms, page, size, status, date_from, date_to, room_id, q)


def _load_in_province(session: Session, current: CurrentUser, booking_id: int) -> Booking:
    """404 when the booking is missing or its room is outside the Pitika's province (B-08).
    The booking is read for a write (B-31)."""
    booking = booking_access.load_booking_for_write(session, booking_id)
    province = booking_access.pitika_province(current)
    if province is None or booking_access.room_province(booking.room) != province:
        raise not_found()
    return booking


def pitika_approve(
    session: Session, current: CurrentUser, booking_id: int, notes: str | None, version: int
) -> Booking:
    """T3 (R2: on to the owner), T4 (IT setup) or T5 (confirmed). BR-APR-03: not after the
    first session started."""
    booking = _load_in_province(session, current, booking_id)
    _check_waiting(booking, version, BookingStatus.PENDING_PITIKA)
    _check_not_started(booking)

    if booking.route == BookingRoute.R2:
        transitions.advance(session, booking, version, status=BookingStatus.PENDING_OWNER)
    else:
        transitions.after_last_review(session, booking, version)

    now = now_utc()
    _add_review(booking, ReviewStage.PITIKA, current, notes, now)
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
    _check_waiting(booking, version, BookingStatus.PENDING_PITIKA)
    transitions.reject(
        session, booking, version, RejectedBy.PITIKA, current.id, reason, ReviewStage.PITIKA
    )
    session.commit()
    return booking


# --- Room owner ------------------------------------------------------------------------


def list_owner_bookings(
    session: Session,
    current: CurrentUser,
    page: int,
    size: int,
    status: str | None,
    room_id: int | None,
    q: str | None,
) -> dict:
    """Bookings of the private rooms the user owns now (BR-OWN-05: the queue follows the room)."""
    rooms = select(Room.id).where(Room.is_private, Room.room_owner_id == current.id)
    return _list_in_rooms(session, rooms, page, size, status, None, None, room_id, q)


def _load_owned(session: Session, current: CurrentUser, booking_id: int) -> Booking:
    """404 when the booking is missing or not in a private room the user owns now (B-08).
    The booking is read for a write (B-31)."""
    booking = booking_access.load_booking_for_write(session, booking_id)
    if not (booking.room.is_private and booking.room.room_owner_id == current.id):
        raise not_found()
    return booking


def owner_approve(
    session: Session, current: CurrentUser, booking_id: int, notes: str | None, version: int
) -> Booking:
    """T7 (IT setup) or T8 (confirmed). B-09: not after the first session started."""
    booking = _load_owned(session, current, booking_id)
    _check_waiting(booking, version, BookingStatus.PENDING_OWNER)
    _check_not_started(booking)
    transitions.after_last_review(session, booking, version)
    _add_review(booking, ReviewStage.OWNER, current, notes, now_utc())
    session.commit()
    return booking


def owner_reject(
    session: Session, current: CurrentUser, booking_id: int, reason: str, version: int
) -> Booking:
    """T9. Allowed at any time while the booking waits for the room owner."""
    booking = _load_owned(session, current, booking_id)
    _check_waiting(booking, version, BookingStatus.PENDING_OWNER)
    transitions.reject(
        session, booking, version, RejectedBy.OWNER, current.id, reason, ReviewStage.OWNER
    )
    session.commit()
    return booking
