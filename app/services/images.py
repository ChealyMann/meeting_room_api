"""Uploaded images: the checks every upload shares (rules R14 and R19).

At most `MAX_UPLOAD_MB`; JPEG, PNG or WebP decided by the file's content, never its name
or Content-Type; at most 40 million pixels. Animated images keep only the first frame.
"""

import io
import logging
import warnings
from pathlib import Path
from typing import BinaryIO

from PIL import Image, UnidentifiedImageError

from app.errors import AppError, ErrorCode

logger = logging.getLogger(__name__)

MAX_PIXELS = 40_000_000
Image.MAX_IMAGE_PIXELS = MAX_PIXELS
ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}


def invalid_image(message: str = "Not a real image.") -> AppError:
    return AppError(ErrorCode.INVALID_IMAGE, 422, message)


def read_upload(file: BinaryIO, max_upload_mb: int) -> bytes:
    """Read at most `max_upload_mb` (+1 byte to notice more): 413 if bigger, 422 if empty."""
    limit = max_upload_mb * 1024 * 1024
    data = file.read(limit + 1)
    if len(data) > limit:
        raise AppError(ErrorCode.FILE_TOO_LARGE, 413, f"File too big (max {max_upload_mb} MB).")
    if not data:
        raise invalid_image()
    return data


def open_image(data: bytes) -> Image.Image:
    """Decode the first frame, or raise 422 INVALID_IMAGE / 415 UNSUPPORTED_FILE_TYPE."""
    try:
        with warnings.catch_warnings():
            # Over MAX_PIXELS Pillow only warns (it raises at twice that); refuse both.
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            image = Image.open(io.BytesIO(data))
            if image.format not in ALLOWED_FORMATS:
                raise AppError(ErrorCode.UNSUPPORTED_FILE_TYPE, 415, "Wrong file type.")
            if image.width * image.height > MAX_PIXELS:
                raise invalid_image()
            image.seek(0)  # animated images keep only the first frame
            image.load()
    except AppError:
        raise
    except (
        UnidentifiedImageError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
        OSError,
        SyntaxError,
        ValueError,
        EOFError,
    ):
        raise invalid_image() from None
    return image


def remove_files(paths: list[Path]) -> None:
    """Delete files; one already gone is logged as a warning, not an error."""
    for path in paths:
        try:
            path.unlink()
        except FileNotFoundError:
            logger.warning("Image file already missing: %s", path)
