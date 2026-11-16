from app.models import BookingAttachment
from app.schemas.common import ResponseModel, UtcDateTime


class AttachmentOut(ResponseModel):
    """A document on a booking. `url` downloads it (signed in, and able to see the booking)."""

    id: int
    file_name: str
    content_type: str
    size_bytes: int
    created_at: UtcDateTime
    url: str


def attachment_out(row: BookingAttachment) -> AttachmentOut:
    return AttachmentOut(
        id=row.id,
        file_name=row.file_name,
        content_type=row.content_type,
        size_bytes=row.size_bytes,
        created_at=row.created_at,
        url=f"/api/v1/bookings/{row.booking_id}/attachments/{row.id}",
    )
