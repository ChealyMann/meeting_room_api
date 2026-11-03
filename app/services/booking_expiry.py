"""The expiry job (spec 10.1): when a booking's first session starts, a waiting booking is
rejected (T15) and a booking still in IT setup is confirmed (T17, BR-IT-06).

Each booking is changed in its own transaction. A person may act on a booking while the
job runs; then the version guard fails (STALE_VERSION) and the job skips that booking.
"""

import logging
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.constants.booking import EXPIRY_REASON, PENDING, BookingStatus, RejectedBy
from app.errors import AppError, ErrorCode
from app.models import Booking
from app.services import booking_transitions as transitions
from app.services import clock
from app.services.booking_review import first_start_sql

logger = logging.getLogger(__name__)

WATCHED = PENDING | {BookingStatus.SETUP_IN_PROGRESS}


@dataclass
class ExpiryResult:
    rejected: list[int] = field(default_factory=list)
    confirmed: list[int] = field(default_factory=list)


def run_once(session: Session) -> ExpiryResult:
    """Reject or confirm every watched booking whose first session has started."""
    ids = list(
        session.scalars(
            select(Booking.id)
            .where(Booking.status.in_(WATCHED), first_start_sql() <= clock.now_local())
            .order_by(Booking.id)
        )
    )
    # End the read, so each booking below starts a fresh transaction (and a fresh snapshot).
    session.commit()

    result = ExpiryResult()
    for booking_id in ids:
        try:
            new_status = _expire(session, booking_id)
            session.commit()
        except Exception as exc:
            # One bad booking must not stop the others. STALE_VERSION: a person acted first.
            session.rollback()
            if not (isinstance(exc, AppError) and exc.code == ErrorCode.STALE_VERSION):
                logger.exception("Expiry job: booking %d failed. Skipped.", booking_id)
            continue
        if new_status == BookingStatus.REJECTED:
            result.rejected.append(booking_id)
        elif new_status == BookingStatus.CONFIRMED:
            result.confirmed.append(booking_id)

    logger.info(
        "Expiry job: rejected %d %s, confirmed %d %s",
        len(result.rejected),
        result.rejected,
        len(result.confirmed),
        result.confirmed,
    )
    return result


def _expire(session: Session, booking_id: int) -> BookingStatus | None:
    """Re-read the booking and move it. None when it changed since the ids were read."""
    booking = session.get(Booking, booking_id, populate_existing=True)
    if booking is None or booking.status not in WATCHED or not transitions.has_started(booking):
        return None
    if booking.status == BookingStatus.SETUP_IN_PROGRESS:
        transitions.make_confirmed(session, booking, booking.version)  # T17
    else:
        transitions.reject(  # T15
            session,
            booking,
            booking.version,
            by=RejectedBy.SYSTEM,
            actor_id=None,
            reason=EXPIRY_REASON,
            stage=None,
        )
    return booking.status
