"""Room photos. Rule R14: at most `MAX_PHOTOS_PER_ROOM` per room; JPEG, PNG or WebP by
content; at most `MAX_UPLOAD_MB` and 40 million pixels (checks in app/services/images.py).

Every upload is re-encoded: turned upright from its EXIF data, stripped of all metadata
(GPS included), flattened onto white, and saved as a JPEG plus a thumbnail under a random
name. The client's file name and Content-Type are never trusted.
"""

import io
import uuid
from pathlib import Path
from typing import BinaryIO

from PIL import Image, ImageOps
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import Settings
from app.errors import AppError, ErrorCode
from app.models import Room, RoomPhoto
from app.security import CurrentUser
from app.services.images import open_image, read_upload, remove_files
from app.services.records import get_or_404, not_found, save
from app.services.room import check_can_manage, room_photos

MAIN_SIDE = 2560
THUMB_SIDE = 400
JPEG_QUALITY = 85


# --- Image processing ------------------------------------------------------------------


def _flatten(image: Image.Image) -> Image.Image:
    """Upright, RGB, transparent areas white, and no metadata at all."""
    image = ImageOps.exif_transpose(image)
    has_alpha = image.mode in ("RGBA", "LA", "PA") or (
        image.mode == "P" and "transparency" in image.info
    )
    if has_alpha:
        rgba = image.convert("RGBA")
        flat = Image.new("RGB", rgba.size, "white")
        flat.paste(rgba, mask=rgba.getchannel("A"))
    else:
        flat = image.convert("RGB")
    flat.info = {}  # drop EXIF, ICC profile and every other chunk
    return flat


def _jpeg(image: Image.Image, longest_side: int) -> bytes:
    copy = image.copy()
    copy.thumbnail((longest_side, longest_side))  # shrinks only, keeps the aspect ratio
    buffer = io.BytesIO()
    copy.save(buffer, format="JPEG", quality=JPEG_QUALITY)
    return buffer.getvalue()


def process_image(data: bytes) -> tuple[bytes, bytes]:
    """The main JPEG (longest side 2560) and the thumbnail JPEG (longest side 400)."""
    image = _flatten(open_image(data))
    return _jpeg(image, MAIN_SIDE), _jpeg(image, THUMB_SIDE)


# --- Files -----------------------------------------------------------------------------


def _file_path(upload_dir: Path, url: str) -> Path | None:
    """The file behind a photo URL, or None if the URL points outside the upload folder."""
    root = upload_dir.resolve()
    path = (root / url.removeprefix("/uploads/")).resolve()
    return path if path.is_relative_to(root) else None


# --- Endpoints -------------------------------------------------------------------------


def list_photos(session: Session, room_id: int) -> list[RoomPhoto]:
    get_or_404(session, Room, room_id)
    return room_photos(session, room_id)


def _insert_photo(session: Session, room_id: int, url: str, thumbnail_url: str) -> RoomPhoto:
    highest = session.scalar(
        select(func.max(RoomPhoto.sort_order)).where(RoomPhoto.room_id == room_id)
    )
    photo = RoomPhoto(
        room_id=room_id, url=url, thumbnail_url=thumbnail_url, sort_order=(highest or 0) + 1
    )
    session.add(photo)
    save(session)
    return photo


def add_photo(
    session: Session, settings: Settings, room_id: int, current: CurrentUser, file: BinaryIO
) -> RoomPhoto:
    """POST /rooms/{id}/photos, in the order of spec section 13."""
    # Lock the room so two uploads at once cannot both pass the photo limit.
    room = session.scalars(select(Room).where(Room.id == room_id).with_for_update()).first()
    if room is None:
        raise not_found()
    check_can_manage(current, room)
    count = session.scalar(select(func.count()).where(RoomPhoto.room_id == room.id))
    if count >= settings.max_photos_per_room:
        raise AppError(
            ErrorCode.PHOTO_LIMIT_REACHED,
            409,
            f"This room has {settings.max_photos_per_room} photos already.",
        )

    main, thumbnail = process_image(read_upload(file, settings.max_upload_mb))

    folder = settings.upload_dir / "rooms" / str(room.id)
    folder.mkdir(parents=True, exist_ok=True)
    name = uuid.uuid4()
    main_path, thumb_path = folder / f"{name}.jpg", folder / f"{name}_thumb.jpg"
    main_path.write_bytes(main)
    thumb_path.write_bytes(thumbnail)
    base = f"/uploads/rooms/{room.id}/{name}"
    try:
        return _insert_photo(session, room.id, f"{base}.jpg", f"{base}_thumb.jpg")
    except BaseException:
        remove_files([main_path, thumb_path])
        raise


def reorder_photos(
    session: Session, room_id: int, photo_ids: list[int], current: CurrentUser
) -> list[RoomPhoto]:
    """Every photo of the room exactly once, in the new order: sort_order 1, 2, 3..."""
    room = get_or_404(session, Room, room_id)
    check_can_manage(current, room)
    photos = {photo.id: photo for photo in room_photos(session, room.id)}
    if sorted(photo_ids) != sorted(photos):
        raise AppError(
            ErrorCode.VALIDATION_ERROR,
            422,
            "Invalid request.",
            {"photo_ids": "The list of photos is not complete."},
        )
    for position, photo_id in enumerate(photo_ids, start=1):
        photos[photo_id].sort_order = position
    save(session)
    return room_photos(session, room.id)


def delete_photo(
    session: Session, settings: Settings, room_id: int, photo_id: int, current: CurrentUser
) -> None:
    """Delete the row, then both files. Other photos keep their sort_order."""
    room = get_or_404(session, Room, room_id)
    check_can_manage(current, room)
    photo = session.get(RoomPhoto, photo_id)
    if photo is None or photo.room_id != room.id:
        raise not_found()
    urls = (photo.url, photo.thumbnail_url)
    session.delete(photo)
    session.commit()
    paths = [path for url in urls if (path := _file_path(settings.upload_dir, url))]
    remove_files(paths)
