"""The request slip's signers, copied when a booking is confirmed (the snapshot rule).

The heads are those of the office and department the booker was in when they SENT the booking
(`requester_info`), not where they are now. A head that is not set gets no row; that box on the
slip stays empty. The booker may also be a head: then they sign that box too.
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


def record_signers(session: Session, booking: Booking) -> None:
    """One row per signer, in the same transaction as the confirm."""
    division, department = _office_and_department(session, booking)
    people: list[tuple[SignerRole, User | None]] = [
        (SignerRole.MAKER, booking.requester),
        (SignerRole.OFFICE_HEAD, division.head if division else None),
        (SignerRole.DEPARTMENT_HEAD, department.head if department else None),
        (SignerRole.DIRECTOR, get_slip_settings(session).director),
    ]
    for role, user in people:
        if user is None:
            continue
        session.add(
            BookingSigner(
                booking_id=booking.id,
                role=role,
                user_id=user.id,
                name_kh=user.name_kh,
                title=user.title,
                signature_path=user.user_signature,
                signed_at=booking.confirmed_at,
            )
        )
    session.flush()


def signature_in_use(session: Session, stored: str) -> bool:
    """A confirmed slip still prints this signature file: keep it."""
    return session.query(BookingSigner.id).filter_by(signature_path=stored).first() is not None
