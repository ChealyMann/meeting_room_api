"""/bookings/{id}/attachments: documents on a booking (spec: booking attachments, 16 Nov 2026)."""

import io
import zipfile
from types import SimpleNamespace

import pytest

from app.constants.booking import BookingStatus
from tests.booking_helpers import URL, error

PDF = b"%PDF-1.7\n1 0 obj\n"


def docx() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("word/document.xml", "<x/>")
    return buffer.getvalue()


@pytest.fixture
def world(make_bookable_room, make_user, make_pitika, make_booking, auth_headers, db_session):
    """`world(status)`: a private room in Phnom Penh with a booking that has a forwarded IT
    ticket and an assigned IT Staff, plus every kind of user around it."""

    def build(status=BookingStatus.PENDING_PITIKA):
        owner = make_user(roles=["ROOM_OWNER"])
        room = make_bookable_room(private=True, owner=owner)
        booker = make_user(roles=["STAFF"])
        helper = make_user(roles=["IT_STAFF"])
        booking = make_booking(
            room, booker, status=status, it=True, forwarded=True, assigned_staff=[helper]
        )
        people = dict(
            booker=booker,
            owner=owner,
            helper=helper,
            admin=make_user(roles=["ADMIN"]),
            pitika=make_pitika(province="PHNOM_PENH"),
            lead=make_user(roles=["IT_LEAD"]),
            stranger=make_user(roles=["STAFF"]),
            far_pitika=make_pitika(province="SIEM_REAP"),
            other_helper=make_user(roles=["IT_STAFF"]),
        )
        headers = {name: auth_headers(user) for name, user in people.items()}
        return SimpleNamespace(
            booking=booking, headers=headers, url=f"{URL}/{booking.id}/attachments"
        )

    return build


def upload(client, w, name="a.pdf", data=PDF, who="booker"):
    return client.post(
        w.url,
        files={"file": (name, data, "application/octet-stream")},
        headers=w.headers[who],
    )


def test_booker_uploads_and_lists(client, world):
    w = world()
    response = upload(client, w)
    assert response.status_code == 201
    body = response.json()
    assert body["file_name"] == "a.pdf"
    assert body["content_type"] == "application/pdf"
    assert body["size_bytes"] == len(PDF)
    assert body["url"] == f"{w.url}/{body['id']}"
    listed = client.get(w.url, headers=w.headers["booker"]).json()
    assert listed["total"] == 1
    assert listed["items"][0]["id"] == body["id"]


def test_file_is_private(client, world, settings):
    w = world()
    upload(client, w)
    saved = [p for p in settings.attachment_dir.rglob("*") if p.is_file()]
    assert len(saved) == 1
    assert saved[0].read_bytes() == PDF
    assert not settings.upload_dir.exists() or not any(settings.upload_dir.rglob("*.pdf"))


@pytest.mark.parametrize("who", ["booker", "admin", "owner", "pitika", "lead", "helper"])
def test_every_viewer_can_list_and_download(client, world, who):
    w = world()
    file_id = upload(client, w).json()["id"]
    assert client.get(w.url, headers=w.headers[who]).json()["total"] == 1
    response = client.get(f"{w.url}/{file_id}", headers=w.headers[who])
    assert response.status_code == 200
    assert response.content == PDF


@pytest.mark.parametrize("who", ["stranger", "far_pitika", "other_helper"])
def test_non_viewer_gets_404(client, world, who):
    w = world()
    file_id = upload(client, w).json()["id"]
    headers = w.headers[who]
    assert error(client.get(w.url, headers=headers)) == (404, "NOT_FOUND")
    assert error(client.get(f"{w.url}/{file_id}", headers=headers)) == (404, "NOT_FOUND")
    assert error(upload(client, w, who=who)) == (404, "NOT_FOUND")
    assert error(client.delete(f"{w.url}/{file_id}", headers=headers)) == (404, "NOT_FOUND")


@pytest.mark.parametrize("who", ["admin", "owner", "pitika"])
def test_viewer_who_is_not_the_booker_cannot_change(client, world, who):
    w = world()
    file_id = upload(client, w).json()["id"]
    assert error(upload(client, w, who=who)) == (403, "FORBIDDEN")
    response = client.delete(f"{w.url}/{file_id}", headers=w.headers[who])
    assert error(response) == (403, "FORBIDDEN")


def test_locked_after_confirm(client, world, db_session):
    w = world()
    file_id = upload(client, w).json()["id"]
    w.booking.status = BookingStatus.CONFIRMED
    db_session.flush()
    response = upload(client, w)
    assert error(response) == (409, "INVALID_TRANSITION")
    assert response.json()["error"]["message"] == "Files are locked once the booking is confirmed."
    deleted = client.delete(f"{w.url}/{file_id}", headers=w.headers["booker"])
    assert error(deleted) == (409, "INVALID_TRANSITION")
    assert client.get(f"{w.url}/{file_id}", headers=w.headers["booker"]).status_code == 200


@pytest.mark.parametrize("status", [BookingStatus.REJECTED, BookingStatus.CANCELLED])
def test_locked_when_closed(client, world, status):
    w = world(status)
    response = upload(client, w)
    assert error(response) == (409, "INVALID_TRANSITION")
    assert response.json()["error"]["message"] == "Files are locked: this booking is closed."


@pytest.mark.parametrize("status", [BookingStatus.PENDING_OWNER, BookingStatus.SETUP_IN_PROGRESS])
def test_open_while_waiting(client, world, status):
    assert upload(client, world(status)).status_code == 201


def test_fourth_file_refused(client, world):
    w = world()
    for name in ("a.pdf", "b.pdf", "c.docx"):
        data = docx() if name.endswith("docx") else PDF
        assert upload(client, w, name=name, data=data).status_code == 201
    response = upload(client, w, name="d.pdf")
    assert error(response) == (409, "ATTACHMENT_LIMIT_REACHED")
    assert response.json()["error"]["message"] == "Up to 3 files."


def test_too_big(client, world, settings):
    settings.max_attachment_mb = 1
    w = world()
    response = upload(client, w, data=PDF + b"0" * (1024 * 1024))
    assert error(response) == (413, "FILE_TOO_LARGE")
    assert response.json()["error"]["message"] == "File too big (max 1 MB)."


def test_wrong_type(client, world):
    response = upload(client, world(), data=b"\x89PNG\r\n\x1a\n" + b"\x00" * 16)
    assert error(response) == (415, "UNSUPPORTED_FILE_TYPE")
    assert response.json()["error"]["message"] == "Only PDF, Word or Excel files."


def test_empty_file(client, world):
    response = upload(client, world(), data=b"")
    assert error(response) == (422, "VALIDATION_ERROR")
    assert response.json()["error"]["message"] == "The file is empty."


def test_khmer_name_download(client, world):
    w = world()
    body = upload(client, w, name="កម្មវិធី.pdf").json()
    assert body["file_name"] == "កម្មវិធី.pdf"
    response = client.get(f"{w.url}/{body['id']}", headers=w.headers["booker"])
    disposition = response.headers["content-disposition"]
    assert disposition.startswith(f'attachment; filename="attachment-{body["id"]}.pdf"')
    assert "filename*=UTF-8''%E1%9E%80" in disposition
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["cache-control"] == "private, no-store"


def test_missing_file_is_404(client, world, settings):
    w = world()
    file_id = upload(client, w).json()["id"]
    for path in settings.attachment_dir.rglob("*.pdf"):
        path.unlink()
    response = client.get(f"{w.url}/{file_id}", headers=w.headers["booker"])
    assert error(response) == (404, "NOT_FOUND")


def test_attachment_of_another_booking_is_404(client, world):
    first, second = world(), world()
    other_id = upload(client, second).json()["id"]
    response = client.get(f"{first.url}/{other_id}", headers=first.headers["admin"])
    assert error(response) == (404, "NOT_FOUND")


def test_delete_removes_row_and_file(client, world, settings):
    w = world()
    file_id = upload(client, w).json()["id"]
    response = client.delete(f"{w.url}/{file_id}", headers=w.headers["booker"])
    assert response.status_code == 204
    assert client.get(w.url, headers=w.headers["booker"]).json()["total"] == 0
    assert not any(settings.attachment_dir.rglob("*.pdf"))


def test_version_unchanged(client, world, db_session):
    w = world()
    before = w.booking.version
    file_id = upload(client, w).json()["id"]
    client.delete(f"{w.url}/{file_id}", headers=w.headers["booker"])
    db_session.refresh(w.booking)
    assert w.booking.version == before


def test_detail_carries_files(client, world, db_session):
    w = world()
    upload(client, w)
    detail = client.get(f"{URL}/{w.booking.id}", headers=w.headers["booker"]).json()
    assert [a["file_name"] for a in detail["attachments"]] == ["a.pdf"]
    assert detail["attachments_open"] is True
    w.booking.status = BookingStatus.CONFIRMED
    db_session.flush()
    detail = client.get(f"{URL}/{w.booking.id}", headers=w.headers["booker"]).json()
    assert detail["attachments_open"] is False
    assert len(detail["attachments"]) == 1
