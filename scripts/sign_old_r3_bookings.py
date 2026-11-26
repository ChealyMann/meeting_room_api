"""Sign the request slip of R3 bookings confirmed before 26 Nov 2026. An R3 booking (an owner's
own room, no food or IT) is confirmed when it is sent, but until then it kept no confirm time and
no slip signers, so its slip's opinion boxes stayed empty. This gives each one its send time as
the confirm time and copies the signers set now. Safe to run again: it only touches confirmed R3
bookings with no confirm time.

Usage (from the project folder):  python -m scripts.sign_old_r3_bookings
"""

import sys

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.constants.booking import BookingRoute, BookingStatus
from app.db import SessionLocal
from app.models import Booking
from app.services import booking_signers


def sign_all(session: Session) -> list[int]:
    """Sets the confirm time (= when sent) and the signers; returns the bookings' ids."""
    bookings = session.scalars(
        select(Booking)
        .where(
            Booking.route == BookingRoute.R3,
            Booking.status == BookingStatus.CONFIRMED,
            Booking.confirmed_at.is_(None),
        )
        .order_by(Booking.id)
    ).all()
    for booking in bookings:
        booking.confirmed_at = booking.created_at
        booking_signers.record_signers(session, booking)
    session.commit()
    return [booking.id for booking in bookings]


def main() -> int:
    with SessionLocal() as session:
        ids = sign_all(session)
    print(f"Signed: {len(ids)} {ids}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
