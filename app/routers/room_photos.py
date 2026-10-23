from fastapi import APIRouter, UploadFile

from app.routers.common import AppSettings, DbSession, IdPath
from app.schemas.common import ItemList
from app.schemas.room_photo import PhotoOrderRequest, PhotoOut
from app.security import AdminOrOwnerUser, AnyUser
from app.services import room_photo as photo_service

router = APIRouter(prefix="/rooms/{room_id}/photos", tags=["Room"])


def _photo_list(photos) -> ItemList[PhotoOut]:
    items = [PhotoOut.model_validate(photo) for photo in photos]
    return ItemList[PhotoOut](items=items, total=len(items))


@router.get("", response_model=ItemList[PhotoOut], summary="List a room's photos")
def list_photos(room_id: IdPath, current: AnyUser, session: DbSession) -> ItemList[PhotoOut]:
    """In display order; the first one is the cover photo."""
    return _photo_list(photo_service.list_photos(session, room_id))


@router.post(
    "",
    response_model=PhotoOut,
    status_code=201,
    summary="Upload a photo (JPEG, PNG or WebP)",
    responses={
        409: {"description": "PHOTO_LIMIT_REACHED"},
        413: {"description": "FILE_TOO_LARGE"},
        415: {"description": "UNSUPPORTED_FILE_TYPE"},
        422: {"description": "INVALID_IMAGE or VALIDATION_ERROR"},
    },
)
def upload_photo(
    room_id: IdPath,
    file: UploadFile,
    current: AdminOrOwnerUser,
    session: DbSession,
    settings: AppSettings,
) -> PhotoOut:
    """Saved as a JPEG with a thumbnail, upright and without any metadata."""
    photo = photo_service.add_photo(session, settings, room_id, current, file.file)
    return PhotoOut.model_validate(photo)


@router.put("/order", response_model=ItemList[PhotoOut], summary="Change the order of photos")
def reorder_photos(
    room_id: IdPath, body: PhotoOrderRequest, current: AdminOrOwnerUser, session: DbSession
) -> ItemList[PhotoOut]:
    """List every photo of the room once, in the new order."""
    return _photo_list(photo_service.reorder_photos(session, room_id, body.photo_ids, current))


@router.delete("/{photo_id}", status_code=204, summary="Delete a photo")
def delete_photo(
    room_id: IdPath,
    photo_id: IdPath,
    current: AdminOrOwnerUser,
    session: DbSession,
    settings: AppSettings,
) -> None:
    photo_service.delete_photo(session, settings, room_id, photo_id, current)
