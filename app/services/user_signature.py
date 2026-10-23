"""User signatures for booking approval forms. Rule R19.

An upload (JPEG, PNG or WebP, same limits as room photos) becomes a clean PNG: upright,
black ink on transparent paper, cropped to the ink, at most 600 x 300 px, with no metadata. Files
live in SIGNATURE_DIR, which is never served publicly; GET /users/{id}/signature serves
them to signed-in users. `users.user_signature` holds the file's path inside that folder.
"""

import io
import logging
import uuid
from pathlib import Path
from typing import BinaryIO

from PIL import Image, ImageChops, ImageFilter, ImageOps
from sqlalchemy.orm import Session

from app.config import Settings
from app.models import User
from app.services.images import invalid_image, open_image, read_upload, remove_files
from app.services.records import not_found

logger = logging.getLogger(__name__)

MAX_SIZE = (600, 300)
# Ink is judged against the paper around it, so grey paper and shadows in phone photos
# disappear too. A pixel darker than its paper by INK_FULL or more (0-255 scale) stays
# fully opaque; by INK_MIN or less it becomes transparent; in between it fades, so stroke
# edges stay smooth.
INK_MIN = 25
INK_FULL = 80
# The paper estimate is made on a copy this big (long side), where a window of
# PAPER_WINDOW pixels is wider than a pen stroke, so the strokes drop out of it.
PAPER_SCALE = 256
PAPER_WINDOW = 9
# Faint pixels (alpha below this) do not count when cropping to the ink.
CROP_ALPHA = 64


def _ink_alpha(darkness: int) -> int:
    if darkness >= INK_FULL:
        return 255
    if darkness <= INK_MIN:
        return 0
    return round((darkness - INK_MIN) * 255 / (INK_FULL - INK_MIN))


def _paper_lightness(lightness: Image.Image) -> Image.Image:
    """How light the paper is around each pixel: the lightest nearby spot, smoothed."""
    width, height = lightness.size
    factor = PAPER_SCALE / max(width, height)
    small = lightness.resize((max(1, round(width * factor)), max(1, round(height * factor))))
    paper = small.filter(ImageFilter.MaxFilter(PAPER_WINDOW)).filter(ImageFilter.GaussianBlur(4))
    return paper.resize(lightness.size, Image.Resampling.BILINEAR)


def make_signature_png(data: bytes) -> bytes:
    """The cleaned signature as PNG bytes, or 422 INVALID_IMAGE if there is no ink."""
    image = ImageOps.exif_transpose(open_image(data)).convert("RGBA")
    flat = Image.new("RGB", image.size, "white")  # see-through parts count as white paper
    flat.paste(image, mask=image.getchannel("A"))
    lightness = flat.convert("L")
    darkness = ImageChops.subtract(_paper_lightness(lightness), lightness)
    alpha = ImageChops.multiply(image.getchannel("A"), darkness.point(_ink_alpha))
    image = Image.new("RGB", image.size, "black")  # any pen colour becomes black ink
    image.putalpha(alpha)
    box = alpha.point(lambda value: 255 if value >= CROP_ALPHA else 0).getbbox()
    if box is None:
        raise invalid_image("No signature found in the image.")
    signature = image.crop(box)
    signature.thumbnail(MAX_SIZE)  # shrinks only, keeps the aspect ratio
    clean = Image.new("RGBA", signature.size)  # a fresh image carries no metadata
    clean.paste(signature)
    buffer = io.BytesIO()
    clean.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()


def signature_url(user: User) -> str | None:
    return f"/api/v1/users/{user.id}/signature" if user.user_signature else None


def _file(settings: Settings, stored: str) -> Path | None:
    """The file behind a stored path, or None if it points outside SIGNATURE_DIR."""
    root = settings.signature_dir.resolve()
    path = (root / stored).resolve()
    return path if path.is_relative_to(root) else None


def _save_path(session: Session, user: User, stored: str | None) -> None:
    user.user_signature = stored
    session.commit()


def set_signature(session: Session, settings: Settings, user: User, file: BinaryIO) -> User:
    """Save a new signature, then delete the one it replaces."""
    png = make_signature_png(read_upload(file, settings.max_upload_mb))
    stored = f"users/{user.id}/{uuid.uuid4()}.png"
    path = settings.signature_dir / stored
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(png)
    old = user.user_signature
    try:
        _save_path(session, user, stored)
    except BaseException:
        remove_files([path])
        raise
    if old and (old_path := _file(settings, old)):
        remove_files([old_path])
    return user


def remove_signature(session: Session, settings: Settings, user: User) -> None:
    """Clear the signature and delete its file. Nothing to do if there is none."""
    old = user.user_signature
    if not old:
        return
    _save_path(session, user, None)
    if old_path := _file(settings, old):
        remove_files([old_path])


def signature_file(settings: Settings, user: User) -> Path:
    """The PNG to serve, or 404 if the user has none (or its file is gone)."""
    if not user.user_signature:
        raise not_found()
    path = _file(settings, user.user_signature)
    if path is None or not path.is_file():
        logger.warning("Signature file missing for user %s: %s", user.id, user.user_signature)
        raise not_found()
    return path
