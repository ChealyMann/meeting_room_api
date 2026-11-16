"""Booking attachments: which documents are allowed (spec: booking attachments, 16 Nov 2026).

PDF, Word and Excel only, decided by the file's content and its name together: the name's
extension says what it claims to be, the first bytes must agree. A .docx or .xlsx is a zip; only
its list of names is read, nothing is extracted.
"""

import io
import unicodedata
import zipfile
from dataclasses import dataclass

from app.errors import AppError, ErrorCode

PDF_MAGIC = b"%PDF-"
OLE2_MAGIC = bytes.fromhex("D0CF11E0A1B11AE1")  # Word 97-2003 and Excel 97-2003
MAX_NAME = 255


@dataclass(frozen=True)
class DocumentType:
    extension: str
    content_type: str


TYPES = {
    "pdf": DocumentType("pdf", "application/pdf"),
    "doc": DocumentType("doc", "application/msword"),
    "xls": DocumentType("xls", "application/vnd.ms-excel"),
    "docx": DocumentType(
        "docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ),
    "xlsx": DocumentType(
        "xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    ),
}
# The part a real Word or Excel zip always holds.
ZIP_PART = {"docx": "word/document.xml", "xlsx": "xl/workbook.xml"}


def unsupported() -> AppError:
    return AppError(ErrorCode.UNSUPPORTED_FILE_TYPE, 415, "Only PDF, Word or Excel files.")


def _base_name(file_name: str) -> str:
    return file_name.replace("\\", "/").rsplit("/", 1)[-1]


def _extension(file_name: str) -> str:
    base = _base_name(file_name)
    return base.rsplit(".", 1)[1].lower() if "." in base else ""


def _zip_holds(data: bytes, part: str) -> bool:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            return part in archive.namelist()
    except (zipfile.BadZipFile, ValueError, OSError):
        return False


def detect_document(data: bytes, file_name: str) -> DocumentType:
    """The document's type, or 415 UNSUPPORTED_FILE_TYPE."""
    extension = _extension(file_name)
    if extension == "pdf":
        ok = data.startswith(PDF_MAGIC)
    elif extension in ("doc", "xls"):
        ok = data.startswith(OLE2_MAGIC)
    elif extension in ZIP_PART:
        ok = _zip_holds(data, ZIP_PART[extension])
    else:
        ok = False
    if not ok:
        raise unsupported()
    return TYPES[extension]


def clean_file_name(file_name: str, extension: str) -> str:
    """The name to keep and show: no folders, no control characters, at most 255 characters,
    and `file.<extension>` when nothing is left."""
    name = _base_name(file_name)
    name = "".join(ch for ch in name if not unicodedata.category(ch).startswith("C")).strip()
    if not name:
        return f"file.{extension}"
    if len(name) > MAX_NAME:
        stem = name.rsplit(".", 1)[0] if "." in name else name
        name = f"{stem[: MAX_NAME - len(extension) - 1]}.{extension}"
    return name
