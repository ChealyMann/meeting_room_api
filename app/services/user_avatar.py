"""User profile photos (avatars). Rule R20.

An upload (JPEG, PNG or WebP, same limits as room photos) becomes a clean JPEG: upright,
transparent parts white, cropped to a square from the centre, at most 512 x 512 px, with no
metadata (GPS included). Files live in AVATAR_DIR, which is never served publicly; GET
/users/{id}/avatar serves them to signed-in users. `users.user_avatar` holds the file's path
inside that folder.
"""

import io
import logging
import uuid
from pathlib import Path
from typing import BinaryIO

from PIL import Image, ImageOps
from sqlalchemy.orm import Session

from app.config import Settings
from app.models import User
from app.services.images import open_image, read_upload, remove_files
from app.services.records import not_found

logger = logging.getLogger(__name__)

SIDE = 512
JPEG_QUALITY = 85


def make_avatar_jpeg(data: bytes) -> bytes:
    """The cleaned photo as JPEG bytes: a centred square, never enlarged."""
    image = ImageOps.exif_transpose(open_image(data)).convert("RGBA")
    flat = Image.new("RGB", image.size, "white")  # see-through parts become white
    flat.paste(image, mask=image.getchannel("A"))
    side = min(SIDE, *flat.size)
    square = ImageOps.fit(flat, (side, side), method=Image.Resampling.LANCZOS)
    buffer = io.BytesIO()
    square.save(buffer, format="JPEG", quality=JPEG_QUALITY)  # a fresh image: no metadata
    return buffer.getvalue()


def avatar_url(user: User) -> str | None:
    return f"/api/v1/users/{user.id}/avatar" if user.user_avatar else None


def _file(settings: Settings, stored: str) -> Path | None:
    """The file behind a stored path, or None if it points outside AVATAR_DIR."""
    root = settings.avatar_dir.resolve()
    path = (root / stored).resolve()
    return path if path.is_relative_to(root) else None


def _save_path(session: Session, user: User, stored: str | None) -> None:
    user.user_avatar = stored
    session.commit()


def set_avatar(session: Session, settings: Settings, user: User, file: BinaryIO) -> User:
    """Save a new photo, then delete the one it replaces."""
    jpeg = make_avatar_jpeg(read_upload(file, settings.max_upload_mb))
    stored = f"users/{user.id}/{uuid.uuid4()}.jpg"
    path = settings.avatar_dir / stored
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(jpeg)
    old = user.user_avatar
    try:
        _save_path(session, user, stored)
    except BaseException:
        remove_files([path])
        raise
    if old and (old_path := _file(settings, old)):
        remove_files([old_path])
    return user


def remove_avatar(session: Session, settings: Settings, user: User) -> None:
    """Clear the photo and delete its file. Nothing to do if there is none."""
    old = user.user_avatar
    if not old:
        return
    _save_path(session, user, None)
    if old_path := _file(settings, old):
        remove_files([old_path])


def avatar_file(settings: Settings, user: User) -> Path:
    """The JPEG to serve, or 404 if the user has none (or its file is gone)."""
    if not user.user_avatar:
        raise not_found()
    path = _file(settings, user.user_avatar)
    if path is None or not path.is_file():
        logger.warning("Avatar file missing for user %s: %s", user.id, user.user_avatar)
        raise not_found()
    return path
