from urllib.parse import quote

from fastapi import APIRouter, UploadFile
from fastapi.responses import FileResponse

from app.routers.common import AppSettings, DbSession, IdPath
from app.schemas.booking_attachment import AttachmentOut, attachment_out
from app.schemas.common import ItemList
from app.security import AnyUser
from app.services import booking_attachment as attachment_service

router = APIRouter(prefix="/bookings/{booking_id}/attachments", tags=["Booking"])


@router.get("", response_model=ItemList[AttachmentOut], summary="List a booking's files")
def list_attachments(
    booking_id: IdPath, current: AnyUser, session: DbSession
) -> ItemList[AttachmentOut]:
    """For everyone who can see the booking (else 404), in the order they were added."""
    items = [
        attachment_out(row)
        for row in attachment_service.list_attachments(session, current, booking_id)
    ]
    return ItemList[AttachmentOut](items=items, total=len(items))


@router.post(
    "",
    response_model=AttachmentOut,
    status_code=201,
    summary="Add a file (PDF, Word or Excel)",
    responses={
        403: {"description": "FORBIDDEN: only the booker"},
        409: {"description": "ATTACHMENT_LIMIT_REACHED or INVALID_TRANSITION (locked)"},
        413: {"description": "FILE_TOO_LARGE"},
        415: {"description": "UNSUPPORTED_FILE_TYPE"},
        422: {"description": "VALIDATION_ERROR: empty file"},
    },
)
def add_attachment(
    booking_id: IdPath,
    file: UploadFile,
    current: AnyUser,
    session: DbSession,
    settings: AppSettings,
) -> AttachmentOut:
    """Only the booker, while the booking is not confirmed, rejected or cancelled. The type is
    checked from the content. The booking's version does not change."""
    row = attachment_service.add_attachment(
        session, settings, current, booking_id, file.file, file.filename or ""
    )
    return attachment_out(row)


@router.get(
    "/{attachment_id}",
    response_class=FileResponse,
    summary="Download a file",
)
def get_attachment(
    booking_id: IdPath,
    attachment_id: IdPath,
    current: AnyUser,
    session: DbSession,
    settings: AppSettings,
) -> FileResponse:
    """For everyone who can see the booking (else 404). Never cached."""
    row, path = attachment_service.attachment_file(
        session, settings, current, booking_id, attachment_id
    )
    extension = path.suffix.lstrip(".")
    return FileResponse(
        path,
        media_type=row.content_type,
        headers={
            "Content-Disposition": (
                f'attachment; filename="attachment-{row.id}.{extension}"; '
                f"filename*=UTF-8''{quote(row.file_name)}"
            ),
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "private, no-store",
        },
    )


@router.delete("/{attachment_id}", status_code=204, summary="Remove a file")
def remove_attachment(
    booking_id: IdPath,
    attachment_id: IdPath,
    current: AnyUser,
    session: DbSession,
    settings: AppSettings,
) -> None:
    """Only the booker, while the booking is not confirmed, rejected or cancelled."""
    attachment_service.remove_attachment(session, settings, current, booking_id, attachment_id)
