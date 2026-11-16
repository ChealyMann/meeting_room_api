"""booking_attachments: the table, its settings (spec: booking attachments, 16 Nov 2026)."""

from pathlib import Path

from app.config import Settings
from app.constants.booking import BookingStatus


def test_settings_defaults():
    settings = Settings(_env_file=None, database_url="x", jwt_secret="a" * 32)
    assert settings.attachment_dir == Path("./attachments")
    assert settings.max_attachment_mb == 10
    assert settings.max_attachments_per_booking == 3


def test_attachment_rows_belong_to_a_booking_in_order(
    make_bookable_room, make_user, make_booking, db_session
):
    from app.models import BookingAttachment

    booker = make_user(roles=["STAFF"])
    booking = make_booking(make_bookable_room(), booker, status=BookingStatus.PENDING_PITIKA)
    for name in ("a.pdf", "b.docx"):
        db_session.add(
            BookingAttachment(
                booking_id=booking.id,
                file_name=name,
                content_type="application/pdf",
                size_bytes=10,
                stored_path=f"bookings/{booking.id}/{name}",
                uploaded_by=booker.id,
            )
        )
    db_session.flush()
    db_session.refresh(booking)
    assert [a.file_name for a in booking.attachments] == ["a.pdf", "b.docx"]
