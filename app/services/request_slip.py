"""Download a booking's request slip (ប័ណ្ណស្នើ): who may, when, and the file's name."""

import re
from urllib.parse import quote

from sqlalchemy.orm import Session

from app.config import Settings
from app.constants.booking import BookingStatus
from app.errors import AppError, ErrorCode
from app.models import Booking
from app.security import CurrentUser
from app.services import booking_access
from app.services.request_slip_data import build_slip_data
from app.services.request_slip_docx import render_slip_docx

DOCX_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
# Characters a file name cannot hold (Windows) or a header line must not.
_UNSAFE = re.compile(r'[\\/:*?"<>|\r\n]+')


def content_disposition(booking: Booking) -> str:
    """An ASCII name for old clients and the Khmer name (room and first day) for the rest."""
    first = min(session.date for session in booking.sessions)
    room = _UNSAFE.sub("-", booking.room.name_kh)
    khmer = f"ប័ណ្ណស្នើបន្ទប់ប្រជុំ_{room}_{first:%d_%m_%Y}.docx"
    return (
        f'attachment; filename="request-slip-{booking.reference_code}.docx"; '
        f"filename*=UTF-8''{quote(khmer)}"
    )


def get_request_slip(
    session: Session, settings: Settings, current: CurrentUser, booking_id: int
) -> tuple[Booking, bytes]:
    """Not visible 404; visible but not the booker, Admin or Pitika of the province 403; not
    CONFIRMED (a COMPLETED booking is still CONFIRMED) 404."""
    booking = booking_access.load_visible_booking(session, current, booking_id)
    if not booking_access.is_slip_viewer(current, booking):
        raise AppError(ErrorCode.FORBIDDEN, 403, "You are not allowed.")
    if booking.status != BookingStatus.CONFIRMED:
        raise AppError(ErrorCode.NOT_FOUND, 404, "This booking is not confirmed yet.")
    return booking, render_slip_docx(build_slip_data(session, settings, booking))
