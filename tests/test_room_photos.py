"""Room photos: tasks 58-61, spec section 13, rule R14."""

import io
import logging
from pathlib import Path

import pytest
from PIL import Image

from app.models import RoomPhoto

URL = "/api/v1/rooms"
PHOTO_FIELDS = {"id", "room_id", "url", "thumbnail_url", "sort_order", "created_at", "updated_at"}


def _error(response) -> tuple[int, str]:
    return response.status_code, response.json()["error"]["code"]


def _fields(response) -> dict:
    return response.json()["error"]["fields"]


def image_bytes(fmt="JPEG", size=(800, 600), mode="RGB", color=(200, 30, 30), **save) -> bytes:
    buffer = io.BytesIO()
    Image.new(mode, size, color).save(buffer, format=fmt, **save)
    return buffer.getvalue()


@pytest.fixture
def upload_dir(settings) -> Path:
    return settings.upload_dir


@pytest.fixture
def owner(make_user):
    return make_user(roles=["ROOM_OWNER"])


@pytest.fixture
def as_owner(owner, auth_headers):
    return auth_headers(owner)


@pytest.fixture
def room(make_room, owner):
    return make_room(owner=owner)


def upload(client, headers, room, data=None, name="photo.jpg", content_type="image/jpeg"):
    data = image_bytes() if data is None else data
    return client.post(
        f"{URL}/{room.id}/photos", files={"file": (name, data, content_type)}, headers=headers
    )


def files_on_disk(upload_dir: Path) -> list[Path]:
    return sorted(path for path in upload_dir.rglob("*") if path.is_file())


def disk_path(upload_dir: Path, url: str) -> Path:
    return upload_dir / url.removeprefix("/uploads/")


def add_photos(db_session, room, count: int) -> list[RoomPhoto]:
    photos = [
        RoomPhoto(
            room_id=room.id,
            url=f"/uploads/x/{n}.jpg",
            thumbnail_url=f"/uploads/x/{n}_t.jpg",
            sort_order=n,
        )
        for n in range(1, count + 1)
    ]
    db_session.add_all(photos)
    db_session.flush()
    return photos


# --- Task 58: POST /rooms/{id}/photos --------------------------------------------------


def test_upload_photo(client, as_admin, room, upload_dir):
    response = upload(client, as_admin, room)
    assert response.status_code == 201, response.text
    body = response.json()
    assert set(body) == PHOTO_FIELDS
    assert (body["room_id"], body["sort_order"]) == (room.id, 1)
    assert body["url"].startswith(f"/uploads/rooms/{room.id}/") and body["url"].endswith(".jpg")
    assert body["thumbnail_url"] == body["url"].removesuffix(".jpg") + "_thumb.jpg"
    main = disk_path(upload_dir, body["url"])
    thumb = disk_path(upload_dir, body["thumbnail_url"])
    with Image.open(main) as image:
        assert (image.format, image.size) == ("JPEG", (800, 600))
    with Image.open(thumb) as image:
        assert (image.format, image.size) == ("JPEG", (400, 300))


def test_files_are_served(client, as_admin, room):
    url = upload(client, as_admin, room).json()["url"]
    response = client.get(url)
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpeg"


def test_sort_order_increases(client, as_admin, room, db_session):
    add_photos(db_session, room, 3)
    assert upload(client, as_admin, room).json()["sort_order"] == 4


def test_large_image_is_resized(client, as_admin, room, upload_dir):
    body = upload(client, as_admin, room, image_bytes(size=(3000, 1500))).json()
    with Image.open(disk_path(upload_dir, body["url"])) as image:
        assert image.size == (2560, 1280)
    with Image.open(disk_path(upload_dir, body["thumbnail_url"])) as image:
        assert image.size == (400, 200)


def test_small_image_is_not_enlarged(client, as_admin, room, upload_dir):
    body = upload(client, as_admin, room, image_bytes(size=(120, 80))).json()
    with Image.open(disk_path(upload_dir, body["thumbnail_url"])) as image:
        assert image.size == (120, 80)


@pytest.mark.parametrize("fmt", ["PNG", "WEBP"])
def test_png_and_webp_saved_as_jpeg(client, as_admin, room, upload_dir, fmt):
    response = upload(
        client, as_admin, room, image_bytes(fmt), name="x.bin", content_type="text/plain"
    )
    assert response.status_code == 201, response.text
    with Image.open(disk_path(upload_dir, response.json()["url"])) as image:
        assert image.format == "JPEG"


def test_transparent_png_gets_white_background(client, as_admin, room, upload_dir):
    data = image_bytes("PNG", mode="RGBA", color=(0, 0, 0, 0))
    body = upload(client, as_admin, room, data, name="t.png", content_type="image/png").json()
    with Image.open(disk_path(upload_dir, body["url"])) as image:
        assert all(channel > 245 for channel in image.convert("RGB").getpixel((10, 10)))


def test_exif_rotation_applied_and_metadata_removed(client, as_admin, room, upload_dir):
    exif = Image.Exif()
    exif[0x0112] = 6  # Orientation: rotate 90 degrees clockwise to display
    exif[0x8825] = {1: "N", 2: (11.0, 33.0, 0.0)}  # GPS info
    data = image_bytes(size=(800, 400), exif=exif.tobytes())
    body = upload(client, as_admin, room, data).json()
    with Image.open(disk_path(upload_dir, body["url"])) as image:
        assert image.size == (400, 800)  # upright
        assert dict(image.getexif()) == {}
        assert "exif" not in image.info


def test_animated_image_keeps_first_frame(client, as_admin, room, upload_dir):
    frames = [Image.new("RGB", (100, 100), color) for color in ((255, 0, 0), (0, 0, 255))]
    buffer = io.BytesIO()
    frames[0].save(buffer, format="WEBP", save_all=True, append_images=frames[1:], lossless=True)
    body = upload(client, as_admin, room, buffer.getvalue()).json()
    with Image.open(disk_path(upload_dir, body["url"])) as image:
        red, _, blue = image.getpixel((50, 50))
        assert red > 200 and blue < 50


def test_file_name_is_ignored(client, as_admin, room, upload_dir):
    body = upload(client, as_admin, room, name="../../etc/passwd.jpg").json()
    assert "passwd" not in body["url"]
    assert all(
        path.is_relative_to(upload_dir / "rooms" / str(room.id))
        for path in files_on_disk(upload_dir)
    )


def test_21st_photo(client, as_admin, room, db_session, upload_dir):
    add_photos(db_session, room, 20)
    response = upload(client, as_admin, room)
    assert _error(response) == (409, "PHOTO_LIMIT_REACHED")
    assert files_on_disk(upload_dir) == []


def test_file_too_large(client, as_admin, room, upload_dir):
    data = b"\xff\xd8\xff" + b"0" * (6 * 1024 * 1024)
    response = upload(client, as_admin, room, data)
    assert _error(response) == (413, "FILE_TOO_LARGE")
    assert files_on_disk(upload_dir) == []


def test_file_of_exactly_the_limit_is_read(client, as_admin, room):
    # 5 MB of junk is not too large, just not an image.
    response = upload(client, as_admin, room, b"0" * (5 * 1024 * 1024))
    assert _error(response) == (422, "INVALID_IMAGE")


@pytest.mark.parametrize(
    "data",
    [
        b"",
        b"hello, this is a text file",
        image_bytes()[:200],  # broken JPEG
    ],
    ids=["empty", "text", "truncated"],
)
def test_invalid_image(client, as_admin, room, upload_dir, data):
    response = upload(client, as_admin, room, data)
    assert _error(response) == (422, "INVALID_IMAGE")
    assert files_on_disk(upload_dir) == []


@pytest.mark.parametrize("fmt", ["GIF", "BMP", "TIFF"])
def test_unsupported_type(client, as_admin, room, fmt):
    response = upload(client, as_admin, room, image_bytes(fmt), name="photo.jpg")
    assert _error(response) == (415, "UNSUPPORTED_FILE_TYPE")


def test_too_many_pixels(client, as_admin, room):
    data = image_bytes("PNG", size=(10000, 10000), mode="1", color=1)
    assert len(data) < 5 * 1024 * 1024
    assert _error(upload(client, as_admin, room, data)) == (422, "INVALID_IMAGE")


def test_just_over_the_pixel_limit(client, as_admin, room):
    data = image_bytes("PNG", size=(8000, 5001), mode="1", color=1)
    assert _error(upload(client, as_admin, room, data)) == (422, "INVALID_IMAGE")


def test_database_failure_removes_files(client, as_admin, room, upload_dir, monkeypatch):
    from app.services import room_photo as photo_service

    def fail(*args, **kwargs):
        raise RuntimeError("database down")

    monkeypatch.setattr(photo_service, "_insert_photo", fail)
    response = upload(client, as_admin, room)
    assert _error(response) == (500, "INTERNAL_ERROR")
    assert files_on_disk(upload_dir) == []


@pytest.mark.parametrize(
    "kwargs",
    [{"files": {"photo": ("a.jpg", b"x", "image/jpeg")}}, {"json": {"file": "x"}}, {}],
    ids=["wrong-field", "json", "nothing"],
)
def test_upload_without_file(client, as_admin, room, kwargs):
    response = client.post(f"{URL}/{room.id}/photos", headers=as_admin, **kwargs)
    assert _error(response) == (422, "VALIDATION_ERROR")
    assert set(_fields(response)) == {"file"}


def test_owner_uploads_to_own_room(client, as_owner, room):
    assert upload(client, as_owner, room).status_code == 201


def test_owner_cannot_upload_to_others_room(client, as_owner, make_room, upload_dir):
    assert _error(upload(client, as_owner, make_room())) == (403, "FORBIDDEN")
    assert files_on_disk(upload_dir) == []


def test_staff_cannot_upload(client, as_staff, room):
    assert _error(upload(client, as_staff, room)) == (403, "FORBIDDEN")


def test_upload_unknown_room(client, as_admin):
    from types import SimpleNamespace

    assert _error(upload(client, as_admin, SimpleNamespace(id=999_999))) == (404, "NOT_FOUND")


def test_upload_needs_a_token(client, room):
    response = client.post(f"{URL}/{room.id}/photos", files={"file": ("a.jpg", image_bytes())})
    assert _error(response) == (401, "UNAUTHORIZED")


# --- Task 59: GET /rooms/{id}/photos ---------------------------------------------------


def test_list_photos(client, as_staff, room, db_session):
    photos = add_photos(db_session, room, 3)
    photos[0].sort_order = 9
    db_session.flush()
    response = client.get(f"{URL}/{room.id}/photos", headers=as_staff)
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"items", "total"}
    assert body["total"] == 3
    assert [item["id"] for item in body["items"]] == [photos[1].id, photos[2].id, photos[0].id]
    assert set(body["items"][0]) == PHOTO_FIELDS


def test_list_no_photos(client, as_staff, room):
    assert client.get(f"{URL}/{room.id}/photos", headers=as_staff).json() == {
        "items": [],
        "total": 0,
    }


def test_list_photos_unknown_room(client, as_staff):
    assert _error(client.get(f"{URL}/999999/photos", headers=as_staff)) == (404, "NOT_FOUND")


def test_list_photos_needs_a_token(client, room):
    assert _error(client.get(f"{URL}/{room.id}/photos")) == (401, "UNAUTHORIZED")


# --- Task 60: PUT /rooms/{id}/photos/order ---------------------------------------------


def reorder(client, headers, room, ids):
    return client.put(f"{URL}/{room.id}/photos/order", json={"photo_ids": ids}, headers=headers)


def test_reorder(client, as_admin, room, db_session):
    a, b, c = add_photos(db_session, room, 3)
    response = reorder(client, as_admin, room, [c.id, a.id, b.id])
    assert response.status_code == 200
    items = response.json()["items"]
    assert [(item["id"], item["sort_order"]) for item in items] == [(c.id, 1), (a.id, 2), (b.id, 3)]
    assert response.json()["total"] == 3


def test_owner_reorders_own_room(client, as_owner, room, db_session):
    a, b = add_photos(db_session, room, 2)
    assert reorder(client, as_owner, room, [b.id, a.id]).status_code == 200


def test_reorder_empty_room(client, as_admin, room):
    assert reorder(client, as_admin, room, []).json() == {"items": [], "total": 0}


@pytest.mark.parametrize("case", ["missing", "extra", "duplicate", "other_room", "empty"])
def test_reorder_incomplete_list(client, as_admin, room, make_room, db_session, case):
    a, b = add_photos(db_session, room, 2)
    (other,) = add_photos(db_session, make_room(), 1)
    ids = {
        "missing": [a.id],
        "extra": [a.id, b.id, 999_999],
        "duplicate": [a.id, b.id, b.id],
        "other_room": [a.id, b.id, other.id],
        "empty": [],
    }[case]
    response = reorder(client, as_admin, room, ids)
    assert _error(response) == (422, "VALIDATION_ERROR")
    assert _fields(response) == {"photo_ids": "The list of photos is not complete."}
    db_session.refresh(a)
    assert a.sort_order == 1


@pytest.mark.parametrize("body", [{}, {"photo_ids": None}, {"photo_ids": ["a"]}, {"ids": []}])
def test_reorder_bad_body(client, as_admin, room, body):
    response = client.put(f"{URL}/{room.id}/photos/order", json=body, headers=as_admin)
    assert _error(response) == (422, "VALIDATION_ERROR")


def test_reorder_access(client, as_staff, as_owner, make_room, room):
    assert _error(reorder(client, as_staff, room, [])) == (403, "FORBIDDEN")
    assert _error(reorder(client, as_owner, make_room(), [])) == (403, "FORBIDDEN")


def test_reorder_unknown_room(client, as_admin):
    response = client.put(f"{URL}/999999/photos/order", json={"photo_ids": []}, headers=as_admin)
    assert _error(response) == (404, "NOT_FOUND")


def test_reorder_needs_a_token(client, room):
    response = client.put(f"{URL}/{room.id}/photos/order", json={"photo_ids": []})
    assert _error(response) == (401, "UNAUTHORIZED")


# --- Task 61: DELETE /rooms/{id}/photos/{photo_id} -------------------------------------


def test_delete_photo(client, as_admin, room, upload_dir, db_session):
    first = upload(client, as_admin, room).json()
    second = upload(client, as_admin, room).json()
    third = upload(client, as_admin, room).json()
    response = client.delete(f"{URL}/{room.id}/photos/{second['id']}", headers=as_admin)
    assert response.status_code == 204
    assert response.content == b""
    assert db_session.get(RoomPhoto, second["id"]) is None
    assert not disk_path(upload_dir, second["url"]).exists()
    assert not disk_path(upload_dir, second["thumbnail_url"]).exists()
    left = client.get(f"{URL}/{room.id}/photos", headers=as_admin).json()["items"]
    # Others keep their sort_order; gaps are fine.
    assert [(item["id"], item["sort_order"]) for item in left] == [
        (first["id"], 1),
        (third["id"], 3),
    ]


def test_owner_deletes_from_own_room(client, as_owner, room):
    photo = upload(client, as_owner, room).json()
    assert (
        client.delete(f"{URL}/{room.id}/photos/{photo['id']}", headers=as_owner).status_code == 204
    )


def test_delete_through_another_rooms_path(client, as_admin, room, make_room):
    photo = upload(client, as_admin, room).json()
    other = make_room()
    response = client.delete(f"{URL}/{other.id}/photos/{photo['id']}", headers=as_admin)
    assert _error(response) == (404, "NOT_FOUND")


def test_delete_unknown_photo(client, as_admin, room):
    assert _error(client.delete(f"{URL}/{room.id}/photos/999999", headers=as_admin)) == (
        404,
        "NOT_FOUND",
    )


def test_delete_photo_of_unknown_room(client, as_admin):
    assert _error(client.delete(f"{URL}/999999/photos/1", headers=as_admin)) == (404, "NOT_FOUND")


def test_delete_when_file_already_gone(client, as_admin, room, upload_dir, caplog):
    photo = upload(client, as_admin, room).json()
    disk_path(upload_dir, photo["url"]).unlink()
    with caplog.at_level(logging.WARNING):
        response = client.delete(f"{URL}/{room.id}/photos/{photo['id']}", headers=as_admin)
    assert response.status_code == 204
    assert any(record.levelno == logging.WARNING for record in caplog.records)
    assert not disk_path(upload_dir, photo["thumbnail_url"]).exists()


def test_delete_access(client, as_admin, as_staff, as_owner, room, make_room):
    photo = upload(client, as_admin, room).json()
    path = f"{URL}/{room.id}/photos/{photo['id']}"
    assert _error(client.delete(path, headers=as_staff)) == (403, "FORBIDDEN")
    other = make_room()
    other_photo = upload(client, as_admin, other).json()
    other_path = f"{URL}/{other.id}/photos/{other_photo['id']}"
    assert _error(client.delete(other_path, headers=as_owner)) == (403, "FORBIDDEN")
    assert _error(client.delete(path)) == (401, "UNAUTHORIZED")


@pytest.mark.parametrize("bad", ["abc", "0"])
def test_delete_bad_photo_id(client, as_admin, room, bad):
    response = client.delete(f"{URL}/{room.id}/photos/{bad}", headers=as_admin)
    assert _error(response) == (422, "VALIDATION_ERROR")
