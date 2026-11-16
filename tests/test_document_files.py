"""Booking attachments: a document is judged by its content (spec: booking attachments)."""

import io
import zipfile

import pytest

from app.errors import AppError
from app.services.document_files import clean_file_name, detect_document

PDF = b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n1 0 obj\n"
OLE2 = bytes.fromhex("D0CF11E0A1B11AE1") + b"\x00" * 64


def zipped(*names: str) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name in names:
            archive.writestr(name, "<x/>")
    return buffer.getvalue()


DOCX = zipped("[Content_Types].xml", "word/document.xml")
XLSX = zipped("[Content_Types].xml", "xl/workbook.xml")


def refused(data: bytes, name: str) -> AppError:
    with pytest.raises(AppError) as caught:
        detect_document(data, name)
    assert caught.value.status == 415
    assert caught.value.code == "UNSUPPORTED_FILE_TYPE"
    assert caught.value.message == "Only PDF, Word or Excel files."
    return caught.value


@pytest.mark.parametrize(
    ("data", "name", "extension", "content_type"),
    [
        (PDF, "a.pdf", "pdf", "application/pdf"),
        (OLE2, "a.doc", "doc", "application/msword"),
        (OLE2, "a.xls", "xls", "application/vnd.ms-excel"),
        (
            DOCX,
            "a.docx",
            "docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ),
        (
            XLSX,
            "a.xlsx",
            "xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ),
    ],
)
def test_accepts_each_type(data, name, extension, content_type):
    found = detect_document(data, name)
    assert found.extension == extension
    assert found.content_type == content_type


def test_extension_case_does_not_matter():
    assert detect_document(PDF, "Agenda.PDF").extension == "pdf"


def test_refuses_a_name_that_does_not_match():
    refused(PDF, "x.docx")
    refused(DOCX, "x.xlsx")


def test_refuses_a_plain_zip_named_docx():
    refused(zipped("a.txt"), "x.docx")


def test_refuses_a_png_named_pdf():
    refused(b"\x89PNG\r\n\x1a\n" + b"\x00" * 32, "a.pdf")


def test_refuses_an_exe():
    refused(b"MZ\x90\x00" + b"\x00" * 32, "x.exe")


def test_refuses_a_name_with_no_extension():
    refused(PDF, "agenda")


def test_refuses_broken_zip():
    refused(b"PK\x03\x04garbage", "x.xlsx")


def test_clean_file_name():
    assert clean_file_name("C:\\fake\\path\\Plan.pdf", "pdf") == "Plan.pdf"
    assert clean_file_name("../../a\x00b.pdf", "pdf") == "ab.pdf"
    assert clean_file_name("   ", "pdf") == "file.pdf"
    assert clean_file_name("កម្មវិធី.pdf", "pdf") == "កម្មវិធី.pdf"
    long = clean_file_name("x" * 300 + ".docx", "docx")
    assert len(long) == 255
    assert long.endswith(".docx")
