"""User photos (avatars): an uploaded image per user, seen only by signed-in users, rule R20."""

import io
import logging
from pathlib import Path

import pytest
from PIL import Image

URL = "/api/v1/users"
ME = "/api/v1/me/avatar"


def _error(response) -> tuple[int, str]:
    return response.status_code, response.json()["error"]["code"]


def photo_bytes(fmt="JPEG", size=(1200, 800), colour=(40, 120, 200), mode="RGB", **save) -> bytes:
    """A photo-like image: a coloured block with a red mark in the centre."""
    image = Image.new(mode, size, colour)
    width, height = size
    image.paste(
        (220, 20, 20) if mode == "RGB" else (220, 20, 20, 255),
        (
            width // 2 - 20,
            height // 2 - 20,
            width // 2 + 20,
            height // 2 + 20,
        ),
    )
    buffer = io.BytesIO()
    image.save(buffer, format=fmt, **save)
    return buffer.getvalue()


def put(client, url, headers, data=None, name="photo.jpg"):
    data = photo_bytes() if data is None else data
    return client.put(url, files={"file": (name, data, "image/jpeg")}, headers=headers)


def files_in(folder: Path) -> list[Path]:
    return sorted(path for path in folder.rglob("*") if path.is_file()) if folder.exists() else []


@pytest.fixture
def user(make_user):
    return make_user(roles=["STAFF"])


@pytest.fixture
def user_headers(user, auth_headers):
    return auth_headers(user)


def stored_image(client, user, headers) -> Image.Image:
    response = client.get(f"{URL}/{user.id}/avatar", headers=headers)
    assert response.status_code == 200, response.text
    return Image.open(io.BytesIO(response.content))


# --- PUT /me/avatar, DELETE /me/avatar --------------------------------------------------


def test_upload_own_photo(client, user, user_headers):
    response = put(client, ME, user_headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["id"] == user.id
    assert body["avatar_url"] == f"/api/v1/users/{user.id}/avatar"
    assert "user_avatar" not in response.text


def test_photo_shows_in_profile_and_list(client, user, user_headers, as_admin):
    assert client.get("/api/v1/me", headers=user_headers).json()["avatar_url"] is None
    put(client, ME, user_headers)
    me = client.get("/api/v1/me", headers=user_headers).json()
    assert me["avatar_url"] == f"/api/v1/users/{user.id}/avatar"
    detail = client.get(f"{URL}/{user.id}", headers=as_admin).json()
    assert detail["avatar_url"] == f"/api/v1/users/{user.id}/avatar"


def test_cropped_to_a_square_from_the_centre(client, user, user_headers):
    put(client, ME, user_headers)
    image = stored_image(client, user, user_headers)
    assert (image.format, image.mode) == ("JPEG", "RGB")
    assert image.size == (512, 512)
    red, green, blue = image.getpixel((256, 256))
    assert red > 180 and green < 80 and blue < 80  # the centre mark is still in the middle


def test_small_photo_is_not_enlarged(client, user, user_headers):
    put(client, ME, user_headers, photo_bytes(size=(300, 200)))
    assert stored_image(client, user, user_headers).size == (200, 200)


def test_transparent_png_gets_white_background(client, user, user_headers):
    data = photo_bytes("PNG", mode="RGBA", colour=(0, 0, 0, 0))
    assert put(client, ME, user_headers, data, name="photo.png").status_code == 200
    assert stored_image(client, user, user_headers).getpixel((5, 5)) == (255, 255, 255)


def test_webp_is_accepted(client, user, user_headers):
    assert put(client, ME, user_headers, photo_bytes("WEBP"), name="p.webp").status_code == 200


def test_exif_rotation_applied_and_metadata_removed(client, user, user_headers):
    exif = Image.Exif()
    exif[0x0112] = 6  # display rotated 90 degrees clockwise
    exif[0x8825] = {1: "N", 2: (11.0, 33.0, 0.0)}  # GPS
    put(client, ME, user_headers, photo_bytes(size=(1200, 400), exif=exif.tobytes()))
    image = stored_image(client, user, user_headers)
    assert image.size == (400, 400)  # cropped from the upright 400 x 1200 image
    assert dict(image.getexif()) == {}
    assert not {"exif", "icc_profile"} & set(image.info)


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        (b"", (422, "INVALID_IMAGE")),
        (b"this is not an image", (422, "INVALID_IMAGE")),
        (photo_bytes("GIF"), (415, "UNSUPPORTED_FILE_TYPE")),
        (photo_bytes("BMP"), (415, "UNSUPPORTED_FILE_TYPE")),
        (b"\xff\xd8\xff" + b"0" * (6 * 1024 * 1024), (413, "FILE_TOO_LARGE")),
    ],
    ids=["empty", "text", "gif", "bmp", "too-large"],
)
def test_bad_files_are_refused(client, user, user_headers, settings, data, expected):
    assert _error(put(client, ME, user_headers, data)) == expected
    assert files_in(settings.avatar_dir) == []


def test_upload_without_file(client, user_headers):
    response = client.put(ME, headers=user_headers)
    assert _error(response) == (422, "VALIDATION_ERROR")
    assert set(response.json()["error"]["fields"]) == {"file"}


def test_replacing_removes_the_old_file(client, user, user_headers, settings):
    put(client, ME, user_headers)
    first = files_in(settings.avatar_dir)
    put(client, ME, user_headers, photo_bytes(colour=(10, 200, 10)))
    second = files_in(settings.avatar_dir)
    assert len(first) == len(second) == 1
    assert first != second


def test_stored_privately(client, user, user_headers, settings):
    put(client, ME, user_headers)
    (path,) = files_in(settings.avatar_dir)
    assert path.suffix == ".jpg"
    assert not path.resolve().is_relative_to(settings.upload_dir.resolve())
    assert files_in(settings.upload_dir) == []


def test_database_failure_keeps_the_old_photo(client, user, user_headers, settings, monkeypatch):
    from app.services import user_avatar as avatar_service

    put(client, ME, user_headers)
    old = files_in(settings.avatar_dir)

    def fail(*args, **kwargs):
        raise RuntimeError("database down")

    monkeypatch.setattr(avatar_service, "_save_path", fail)
    response = put(client, ME, user_headers, photo_bytes(colour=(10, 200, 10)))
    assert _error(response) == (500, "INTERNAL_ERROR")
    assert files_in(settings.avatar_dir) == old


def test_remove_own_photo(client, user, user_headers, settings):
    put(client, ME, user_headers)
    response = client.delete(ME, headers=user_headers)
    assert response.status_code == 204
    assert files_in(settings.avatar_dir) == []
    assert client.get("/api/v1/me", headers=user_headers).json()["avatar_url"] is None
    assert _error(client.get(f"{URL}/{user.id}/avatar", headers=user_headers)) == (
        404,
        "NOT_FOUND",
    )


def test_remove_when_there_is_none(client, user_headers):
    assert client.delete(ME, headers=user_headers).status_code == 204


def test_own_photo_needs_a_token(client):
    assert _error(put(client, ME, {})) == (401, "UNAUTHORIZED")
    assert _error(client.delete(ME)) == (401, "UNAUTHORIZED")


def test_blocked_until_password_changed(client, make_user, auth_headers):
    headers = auth_headers(make_user(roles=["STAFF"], must_change_password=True))
    assert _error(put(client, ME, headers)) == (403, "PASSWORD_CHANGE_REQUIRED")
    assert _error(client.delete(ME, headers=headers)) == (403, "PASSWORD_CHANGE_REQUIRED")


def test_photo_link_is_no_longer_accepted(client, user_headers):
    response = client.patch(
        "/api/v1/me", json={"avatar_url": "https://cdn.company.com/a.jpg"}, headers=user_headers
    )
    assert _error(response) == (422, "VALIDATION_ERROR")
    assert response.json()["error"]["fields"] == {"avatar_url": "Unknown field."}


# --- PUT /users/{id}/avatar, DELETE /users/{id}/avatar (Admin) ---------------------------


def test_admin_sets_a_users_photo(client, as_admin, user):
    response = put(client, f"{URL}/{user.id}/avatar", as_admin)
    assert response.status_code == 200, response.text
    assert response.json()["avatar_url"] == f"/api/v1/users/{user.id}/avatar"


def test_admin_removes_a_users_photo(client, as_admin, user, user_headers, settings):
    put(client, ME, user_headers)
    assert client.delete(f"{URL}/{user.id}/avatar", headers=as_admin).status_code == 204
    assert files_in(settings.avatar_dir) == []


def test_only_admin_sets_others(client, user, make_user, auth_headers):
    other = auth_headers(make_user(roles=["STAFF"]))
    assert _error(put(client, f"{URL}/{user.id}/avatar", other)) == (403, "FORBIDDEN")
    assert _error(client.delete(f"{URL}/{user.id}/avatar", headers=other)) == (403, "FORBIDDEN")


def test_admin_unknown_user(client, as_admin):
    assert _error(put(client, f"{URL}/999999/avatar", as_admin)) == (404, "NOT_FOUND")
    assert _error(client.delete(f"{URL}/999999/avatar", headers=as_admin)) == (404, "NOT_FOUND")


def test_admin_cannot_send_a_photo_link(client, as_admin, user):
    response = client.patch(
        f"{URL}/{user.id}", json={"avatar_url": "https://cdn.company.com/a.jpg"}, headers=as_admin
    )
    assert _error(response) == (422, "VALIDATION_ERROR")
    assert response.json()["error"]["fields"] == {"avatar_url": "Unknown field."}


# --- GET /users/{id}/avatar --------------------------------------------------------------


def test_anyone_signed_in_can_see_it(client, user, user_headers, make_user, auth_headers):
    put(client, ME, user_headers)
    other = auth_headers(make_user(roles=[]))
    response = client.get(f"{URL}/{user.id}/avatar", headers=other)
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpeg"
    assert "private" in response.headers["cache-control"]


def test_photo_needs_a_token(client, user, user_headers):
    put(client, ME, user_headers)
    assert _error(client.get(f"{URL}/{user.id}/avatar")) == (401, "UNAUTHORIZED")


def test_no_photo(client, user, as_admin):
    assert _error(client.get(f"{URL}/{user.id}/avatar", headers=as_admin)) == (404, "NOT_FOUND")


def test_unknown_user(client, as_admin):
    assert _error(client.get(f"{URL}/999999/avatar", headers=as_admin)) == (404, "NOT_FOUND")


def test_file_missing_on_disk(client, user, user_headers, as_admin, settings, caplog):
    put(client, ME, user_headers)
    for path in files_in(settings.avatar_dir):
        path.unlink()
    with caplog.at_level(logging.WARNING):
        response = client.get(f"{URL}/{user.id}/avatar", headers=as_admin)
    assert _error(response) == (404, "NOT_FOUND")
    assert any(record.levelno == logging.WARNING for record in caplog.records)


def test_not_served_from_public_uploads(client, user, user_headers, settings):
    put(client, ME, user_headers)
    (path,) = files_in(settings.avatar_dir)
    relative = path.relative_to(settings.avatar_dir).as_posix()
    assert client.get(f"/uploads/{relative}").status_code == 404
