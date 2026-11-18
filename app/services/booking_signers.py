"""The request slip's signers, copied when a booking is confirmed (the snapshot rule).

The heads are those of the office and department the booker was in when they SENT the booking
(`requester_info`), not where they are now. A head that is not set gets no row; that box is
filled later by whoever is set then (`late_signers`, owner, 18 Nov 2026). The booker may also be
a head: then they sign that box too.
"""

from sqlalchemy.orm import Session

from app.constants.booking import SignerRole
from app.models import Booking, BookingSigner, Department, Division, User
from app.services.slip_settings import get_slip_settings


def _office_and_department(
    session: Session, booking: Booking
) -> tuple[Division | None, Department | None]:
    info = booking.requester_info or {}
    if "division_id" in info:
        division = session.get(Division, info["division_id"]) if info["division_id"] else None
        department = (
            session.get(Department, info["department_id"]) if info["department_id"] else None
        )
        return division, department
    # Sent before the slip existed: the booker's office now is the best we know.
    division = booking.requester.division
    return division, division.department if division else None


def _people(session: Session, booking: Booking) -> list[tuple[SignerRole, User | None]]:
    """Who signs each box now: the booker, the heads of the office and department it was sent
    from, and the Director of Cabinet. None where nobody is set."""
    division, department = _office_and_department(session, booking)
    return [
        (SignerRole.MAKER, booking.requester),
        (SignerRole.OFFICE_HEAD, division.head if division else None),
        (SignerRole.DEPARTMENT_HEAD, department.head if department else None),
        (SignerRole.DIRECTOR, get_slip_settings(session).director),
    ]


def _row(booking: Booking, role: SignerRole, user: User, signature: str | None) -> BookingSigner:
    return BookingSigner(
        booking_id=booking.id,
        role=role,
        user_id=user.id,
        name_kh=user.name_kh,
        title=user.title,
        signature_path=signature,
        signed_at=booking.confirmed_at,
    )


def record_signers(session: Session, booking: Booking) -> None:
    """One row per signer, in the same transaction as the confirm."""
    for role, user in _people(session, booking):
        if user is not None:
            session.add(_row(booking, role, user, user.user_signature))
    session.flush()


def late_signers(
    session: Session, booking: Booking, kept: set[str]
) -> dict[SignerRole, BookingSigner]:
    """Fill empty boxes (owner, 18 Nov 2026): for a confirmed booking, each box with no kept
    copy (nobody was set when it was confirmed) gets the person set now. The rows are NOT saved:
    the slip reads them, so a head set later still changes a box that was empty, never a kept
    one. Their signature is read from the profile (no copy), and the date stays the confirm day."""
    if booking.confirmed_at is None:
        return {}
    return {
        role: _row(booking, role, user, None)
        for role, user in _people(session, booking)
        if user is not None and role not in kept
    }


def signature_in_use(session: Session, stored: str) -> bool:
    """A confirmed slip still prints this signature file: keep it."""
    return session.query(BookingSigner.id).filter_by(signature_path=stored).first() is not None
