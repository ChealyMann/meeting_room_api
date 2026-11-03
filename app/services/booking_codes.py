"""Reference codes and door pass codes (spec 8.3, B-28)."""

import secrets
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.constants.booking import REFERENCE_PREFIX
from app.models import Booking, BookingDoorPass
from app.services import clock

MAX_TRIES = 20


def _five_digits() -> int:
    return secrets.randbelow(90000) + 10000


def _reference_taken(session: Session, code: str) -> bool:
    return session.scalar(select(Booking.id).where(Booking.reference_code == code)) is not None


def new_reference_code(session: Session, now_local: datetime) -> str:
    """`NBC-YY-NNNNN`: YY is the local year the booking is sent.
    The unique key is the last guard; the create retries on a duplicate-key error."""
    year = f"{now_local.year % 100:02d}"
    for _ in range(MAX_TRIES):
        code = f"{REFERENCE_PREFIX}{year}-{_five_digits()}"
        if not _reference_taken(session, code):
            return code
    raise RuntimeError("No free reference code after 20 tries.")


def _door_pass_taken(session: Session, code: str) -> bool:
    """A code is taken while a pass with it has not expired. Old passes may repeat a code."""
    return (
        session.scalar(
            select(BookingDoorPass.id).where(
                BookingDoorPass.passcode == code, BookingDoorPass.expires_at > clock.now_utc()
            )
        )
        is not None
    )


def new_door_pass_code(session: Session, reference_code: str) -> str:
    """`NBC-NNNNN` (BR-DP-01): not the booking's reference code, not used by an active pass."""
    for _ in range(MAX_TRIES):
        code = f"{REFERENCE_PREFIX}{_five_digits()}"
        if code != reference_code and not _door_pass_taken(session, code):
            return code
    raise RuntimeError("No free door pass code after 20 tries.")
