"""Documents on a booking (spec: booking attachments, 16 Nov 2026).

Everyone who can see the booking can list and download them. Only the booker adds or removes
them, and only while the booking is still open (not confirmed, rejected or cancelled). Files
live in ATTACHMENT_DIR, which is never served publicly. Adding or removing a file does not
change the booking's version.
"""

import logging
import uuid
from pathlib import Path
from typing import BinaryIO

from sqlalchemy.orm import Session

from app.config import Settings
from app.constants.booking import ATTACHMENTS_OPEN, BookingStatus
from app.errors import AppError, ErrorCode
from app.models import Booking, BookingAttachment
from app.security import CurrentUser
from app.services import booking_access
from app.services.document_files import clean_file_name, detect_document
from app.services.images import read_upload, remove_files
from app.services.records import not_found

logger = logging.getLogger(__name__)


def _file(settings: Settings, stored: str) -> Path | None:
    """The file behind a stored path, or None if it points outside ATTACHMENT_DIR."""
    root = settings.attachment_dir.resolve()
    path = (root / stored).resolve()
    return path if path.is_relative_to(root) else None


def _check_can_change(current: CurrentUser, booking: Booking) -> None:
    if booking.requester_id != current.id:
        raise AppError(ErrorCode.FORBIDDEN, 403, "Only the booker can change the files.")
    if booking.status in ATTACHMENTS_OPEN:
        return
    if booking.status == BookingStatus.CONFIRMED:
        message = "Files are locked once the booking is confirmed."
    else:
        message = "Files are locked: this booking is closed."
    raise AppError(ErrorCode.INVALID_TRANSITION, 409, message)


def _read(file: BinaryIO, settings: Settings) -> bytes:
    """The upload's bytes: 413 when too big, 422 when empty."""
    try:
        return read_upload(file, settings.max_attachment_mb)
    except AppError as exc:
        if exc.code != ErrorCode.INVALID_IMAGE:
            raise
        raise AppError(ErrorCode.VALIDATION_ERROR, 422, "The file is empty.") from exc


def _row_of(booking: Booking, attachment_id: int) -> BookingAttachment:
    for row in booking.attachments:
        if row.id == attachment_id:
            return row
    raise not_found()


def list_attachments(
    session: Session, current: CurrentUser, booking_id: int
) -> list[BookingAttachment]:
    return list(booking_access.load_visible_booking(session, current, booking_id).attachments)


def add_attachment(
    session: Session,
    settings: Settings,
    current: CurrentUser,
    booking_id: int,
    file: BinaryIO,
    file_name: str,
) -> BookingAttachment:
    """Save a new document. The booking row is locked (FOR UPDATE) so a confirm at the same
    moment can't let a file in after it."""
    booking = booking_access.load_visible_booking(session, current, booking_id, for_write=True)
    _check_can_change(current, booking)
    if len(booking.attachments) >= settings.max_attachments_per_booking:
        limit = settings.max_attachments_per_booking
        raise AppError(ErrorCode.ATTACHMENT_LIMIT_REACHED, 409, f"Up to {limit} files.")
    data = _read(file, settings)
    found = detect_document(data, file_name)
    stored = f"bookings/{booking.id}/{uuid.uuid4()}.{found.extension}"
    path = settings.attachment_dir / stored
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    row = BookingAttachment(
        booking_id=booking.id,
        file_name=clean_file_name(file_name, found.extension),
        content_type=found.content_type,
        size_bytes=len(data),
        stored_path=stored,
        uploaded_by=current.id,
    )
    try:
        session.add(row)
        session.commit()
    except BaseException:
        remove_files([path])
        raise
    return row


def attachment_file(
    session: Session, settings: Settings, current: CurrentUser, booking_id: int, attachment_id: int
) -> tuple[BookingAttachment, Path]:
    """The row and the file to serve, or 404 (also when the file is gone)."""
    booking = booking_access.load_visible_booking(session, current, booking_id)
    row = _row_of(booking, attachment_id)
    path = _file(settings, row.stored_path)
    if path is None or not path.is_file():
        logger.warning("Attachment file missing for row %s: %s", row.id, row.stored_path)
        raise not_found()
    return row, path


def remove_attachment(
    session: Session, settings: Settings, current: CurrentUser, booking_id: int, attachment_id: int
) -> None:
    """Delete the row, then its file."""
    booking = booking_access.load_visible_booking(session, current, booking_id, for_write=True)
    row = _row_of(booking, attachment_id)
    _check_can_change(current, booking)
    path = _file(settings, row.stored_path)
    session.delete(row)
    session.commit()
    if path is not None:
        remove_files([path])
