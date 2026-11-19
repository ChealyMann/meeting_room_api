"""Confirm every booking still in IT setup (spec 2026-11-19-it-setup-addon): since 19 Nov 2026 IT
help is an add-on and the last approval confirms the booking. Bookings sent to IT before that
change get their door pass now; their IT tickets stay as they are. Safe to run again: it only
touches bookings in SETUP_IN_PROGRESS.

Usage (from the project folder):  python -m scripts.confirm_it_setup_bookings
"""

import sys

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.constants.booking import BookingStatus
from app.db import SessionLocal
from app.models import Booking
from app.services import booking_transitions as transitions


def confirm_all(session: Session) -> list[int]:
    """Confirms them (door pass, confirm time, the slip's signers) and returns their ids."""
    bookings = session.scalars(
        select(Booking)
        .where(Booking.status == BookingStatus.SETUP_IN_PROGRESS)
        .order_by(Booking.id)
    ).all()
    for booking in bookings:
        transitions.make_confirmed(session, booking, booking.version)
    session.commit()
    return [booking.id for booking in bookings]


def main() -> int:
    with SessionLocal() as session:
        ids = confirm_all(session)
    print(f"Confirmed: {len(ids)} {ids}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
