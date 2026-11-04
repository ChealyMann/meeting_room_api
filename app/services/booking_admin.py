"""The Admin's booking actions (B-33, B-34, B-35; decisions D-32 to D-40): cancel any open
booking, and approve or reject as a backup reviewer. Every write goes through the same version
check and row lock as the booker's, Pitika's and owner's (spec 8.5, B-31)."""

from sqlalchemy.orm import Session

from app.constants.booking import FINAL, BookingStatus, RejectedBy, ReviewStage
from app.errors import AppError, ErrorCode
from app.models import Booking
from app.security import CurrentUser
from app.services import booking_access, booking_review
from app.services import booking_transitions as transitions
from app.services.booking import ENDED_MESSAGE
from app.services.booking_scheduling import active_pitika_count

COVERED_MESSAGE = "This office has an active Pitika. Ask them to decide."
ADMIN_REJECT_REASON = "Rejected by the Admin."


def _stage(session: Session, booking: Booking) -> ReviewStage | None:
    """The review step the Admin may decide now: Pitika's only when the room's province has no
    active Pitika (D-33), the owner's always (D-34), none in IT setup (D-40) or later."""
    if booking.status == BookingStatus.PENDING_PITIKA:
        province = booking_access.room_province(booking.room)
        return ReviewStage.PITIKA if active_pitika_count(session, province) == 0 else None
    if booking.status == BookingStatus.PENDING_OWNER:
        return ReviewStage.OWNER
    return None


def allowed_actions(session: Session, booking: Booking) -> dict:
    """What the dashboard may offer the Admin for this booking now."""
    stage = _stage(session, booking)
    return {
        "cancel": booking.status not in FINAL and not transitions.has_ended(booking),
        "approve": stage is not None and not transitions.has_started(booking),
        "reject": stage is not None,
        "stage": stage,
    }


def get_actions(session: Session, booking_id: int) -> dict:
    return allowed_actions(session, booking_access.load_booking_for_write(session, booking_id))


def admin_cancel(
    session: Session, current: CurrentUser, booking_id: int, reason: str | None, version: int
) -> Booking:
    """B-33: any booking that is not final and has not ended; the same effects as a booker's
    cancel (D-38), with the Admin recorded as `cancelled_by` (D-36)."""
    booking = booking_access.load_booking_for_write(session, booking_id)
    transitions.check_version(booking, version)
    if booking.status in FINAL:
        raise transitions.invalid_transition(booking)
    if transitions.has_ended(booking):
        raise transitions.invalid_transition(booking, ENDED_MESSAGE)
    transitions.cancel(session, booking, version, reason, current.id)
    session.commit()
    return booking


def _load_for_review(
    session: Session, booking_id: int, version: int
) -> tuple[Booking, ReviewStage]:
    """Spec 8.5 order for approve and reject: the stage rule (403, D-33), the version, then
    the status (only the two waiting statuses, D-40)."""
    booking = booking_access.load_booking_for_write(session, booking_id)
    if booking.status == BookingStatus.PENDING_PITIKA and _stage(session, booking) is None:
        raise AppError(ErrorCode.FORBIDDEN, 403, COVERED_MESSAGE)
    transitions.check_version(booking, version)
    stage = _stage(session, booking)
    if stage is None:
        raise transitions.invalid_transition(booking)
    return booking, stage


def admin_approve(
    session: Session, current: CurrentUser, booking_id: int, notes: str | None, version: int
) -> Booking:
    """B-34: approve for Pitika or the owner, not after the first session started (D-37)."""
    booking, stage = _load_for_review(session, booking_id, version)
    if transitions.has_started(booking):
        raise AppError(ErrorCode.TIME_PASSED, 409, booking_review.STARTED_MESSAGE)
    if stage == ReviewStage.PITIKA:
        booking_review.approve_pitika_stage(
            session, booking, version, current, notes, by_admin=True
        )
    else:
        booking_review.approve_owner_stage(session, booking, version, current, notes, by_admin=True)
    session.commit()
    return booking


def admin_reject(
    session: Session, current: CurrentUser, booking_id: int, reason: str | None, version: int
) -> Booking:
    """B-34: reject for Pitika or the owner while the booking waits; the reason is optional
    (D-35) and the column is not, so none saves ADMIN_REJECT_REASON."""
    booking, stage = _load_for_review(session, booking_id, version)
    by = RejectedBy.PITIKA if stage == ReviewStage.PITIKA else RejectedBy.OWNER
    transitions.reject(
        session,
        booking,
        version,
        by,
        current.id,
        reason or ADMIN_REJECT_REASON,
        stage,
        by_admin=True,
    )
    session.commit()
    return booking
