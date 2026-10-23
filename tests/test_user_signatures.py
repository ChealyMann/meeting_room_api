"""User signatures (tasks 67-69): an image per user for booking approval forms, rule R19."""

import io
import logging
from pathlib import Path

import pytest
from PIL import Image, ImageDraw, ImageFilter

URL = "/api/v1/users"
ME = "/api/v1/me/signature"


def _error(response) -> tuple[int, str]:
    return response.status_code, response.json()["error"]["code"]


def signature_bytes(
    fmt="JPEG", size=(1200, 800), ink=(20, 30, 90), background="white", mode="RGB", **save
) -> bytes:
    """A signature-like drawing: dark strokes in the middle of plain paper."""
    image = Image.new(mode, size, background)
    draw = ImageDraw.Draw(image)
    width, height = size
    draw.line([(width * 0.3, height * 0.55), (width * 0.5, height * 0.4)], fill=ink, width=8)
    draw.line([(width * 0.5, height * 0.4), (width * 0.7, height * 0.6)], fill=ink, width=8)
    buffer = io.BytesIO()
    image.save(buffer, format=fmt, **save)
    return buffer.getvalue()


def put(client, url, headers, data=None, name="signature.jpg"):
    data = signature_bytes() if data is None else data
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
    response = client.get(f"{URL}/{user.id}/signature", headers=headers)
    assert response.status_code == 200, response.text
    return Image.open(io.BytesIO(response.content))


# --- Task 67: PUT /me/signature, DELETE /me/signature ---------------------------------


def test_upload_own_signature(client, user, user_headers):
    response = put(client, ME, user_headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["id"] == user.id
    assert body["signature_url"] == f"/api/v1/users/{user.id}/signature"
    assert "user_signature" not in response.text


def test_signature_shows_in_profile(client, user, user_headers):
    assert client.get("/api/v1/me", headers=user_headers).json()["signature_url"] is None
    put(client, ME, user_headers)
    me = client.get("/api/v1/me", headers=user_headers).json()
    assert me["signature_url"] == f"/api/v1/users/{user.id}/signature"


def test_paper_becomes_transparent_and_ink_stays(client, user, user_headers):
    put(client, ME, user_headers)
    image = stored_image(client, user, user_headers)
    assert (image.format, image.mode) == ("PNG", "RGBA")
    width, height = image.size
    alphas = [image.getpixel((x, y))[3] for x in range(width) for y in range(height)]
    assert min(alphas) == 0  # paper removed
    assert max(alphas) == 255  # ink kept
    dark = [image.getpixel((x, y)) for x in range(width) for y in range(height)]
    assert any(pixel[3] == 255 and sum(pixel[:3]) < 300 for pixel in dark)


def phone_photo_bytes() -> bytes:
    """Like a real phone photo: off-white, slightly grey paper with a shadow, blue ink."""
    page = Image.new("RGB", (1600, 1000), (236, 233, 226))
    shade = Image.new("L", page.size, 0)
    ImageDraw.Draw(shade).rectangle([0, 0, 500, 1000], fill=40)
    page.paste((205, 202, 195), mask=shade.filter(ImageFilter.GaussianBlur(120)))
    draw = ImageDraw.Draw(page)
    strokes = [(520, 560), (600, 420), (660, 600), (720, 430), (800, 590), (880, 470), (960, 560)]
    draw.line(strokes + [(1080, 500)], fill=(25, 40, 120), width=9)
    draw.line([(560, 640), (1100, 610)], fill=(25, 40, 120), width=6)
    buffer = io.BytesIO()
    page.save(buffer, format="JPEG", quality=88)
    return buffer.getvalue()


def test_grey_paper_and_shadow_are_removed(client, user, user_headers):
    # The ink spans 584 x 226 px; the shadow and grey paper must not count as ink.
    put(client, ME, user_headers, phone_photo_bytes())
    image = stored_image(client, user, user_headers)
    width, height = image.size
    assert 570 <= width <= 600 and 210 <= height <= 240  # cropped tight around the strokes
    alpha = image.getchannel("A").histogram()
    haze = sum(alpha[1:128])  # see-through grey left from the paper
    assert haze < 0.05 * width * height
    assert alpha[255] > 0  # the ink itself stays fully opaque


@pytest.mark.parametrize(
    "ink", [(25, 40, 120), (200, 20, 20), (60, 60, 60)], ids=["blue", "red", "grey"]
)
def test_ink_becomes_black(client, user, user_headers, ink):
    put(client, ME, user_headers, signature_bytes(ink=ink))
    image = stored_image(client, user, user_headers)
    visible = {pixel[:3] for pixel in image.get_flattened_data() if pixel[3] > 0}
    assert visible == {(0, 0, 0)}  # black ink, only its opacity varies at the edges


def test_cropped_to_the_ink(client, user, user_headers):
    # The strokes cover about 40% x 20% of a 1200 x 800 page.
    put(client, ME, user_headers)
    width, height = stored_image(client, user, user_headers).size
    assert width < 600 and height < 300
    assert width > height


def test_large_signature_is_scaled_down(client, user, user_headers):
    put(client, ME, user_headers, signature_bytes(size=(6000, 4000)))
    width, height = stored_image(client, user, user_headers).size
    assert width <= 600 and height <= 300


def test_transparent_png_stays_transparent(client, user, user_headers):
    data = signature_bytes("PNG", mode="RGBA", background=(0, 0, 0, 0), ink=(0, 0, 0, 255))
    assert put(client, ME, user_headers, data, name="sig.png").status_code == 200
    image = stored_image(client, user, user_headers)
    assert image.getpixel((0, 0))[3] == 0


def test_exif_rotation_applied_and_metadata_removed(client, user, user_headers):
    exif = Image.Exif()
    exif[0x0112] = 6  # display rotated 90 degrees clockwise
    exif[0x8825] = {1: "N", 2: (11.0, 33.0, 0.0)}  # GPS
    put(client, ME, user_headers, signature_bytes(exif=exif.tobytes()))
    image = stored_image(client, user, user_headers)
    width, height = image.size
    assert height > width  # the wide signature now stands upright
    assert dict(image.getexif()) == {}
    assert not {"exif", "icc_profile"} & set(image.info)


def test_blank_page_is_refused(client, user, user_headers):
    blank = io.BytesIO()
    Image.new("RGB", (800, 400), "white").save(blank, format="PNG")
    response = put(client, ME, user_headers, blank.getvalue(), name="blank.png")
    assert _error(response) == (422, "INVALID_IMAGE")
    assert response.json()["error"]["message"] == "No signature found in the image."


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        (b"", (422, "INVALID_IMAGE")),
        (b"this is not an image", (422, "INVALID_IMAGE")),
        (signature_bytes("GIF"), (415, "UNSUPPORTED_FILE_TYPE")),
        (signature_bytes("BMP"), (415, "UNSUPPORTED_FILE_TYPE")),
        (b"\xff\xd8\xff" + b"0" * (6 * 1024 * 1024), (413, "FILE_TOO_LARGE")),
    ],
    ids=["empty", "text", "gif", "bmp", "too-large"],
)
def test_bad_files_are_refused(client, user, user_headers, settings, data, expected):
    assert _error(put(client, ME, user_headers, data)) == expected
    assert files_in(settings.signature_dir) == []


def test_upload_without_file(client, user_headers):
    response = client.put(ME, headers=user_headers)
    assert _error(response) == (422, "VALIDATION_ERROR")
    assert set(response.json()["error"]["fields"]) == {"file"}


def test_replacing_removes_the_old_file(client, user, user_headers, settings):
    put(client, ME, user_headers)
    first = files_in(settings.signature_dir)
    put(client, ME, user_headers, signature_bytes(ink=(200, 0, 0)))
    second = files_in(settings.signature_dir)
    assert len(first) == len(second) == 1
    assert first != second


def test_stored_privately(client, user, user_headers, settings):
    put(client, ME, user_headers)
    (path,) = files_in(settings.signature_dir)
    assert path.suffix == ".png"
    assert not path.resolve().is_relative_to(settings.upload_dir.resolve())
    assert files_in(settings.upload_dir) == []


def test_database_failure_keeps_the_old_signature(
    client, user, user_headers, settings, monkeypatch
):
    from app.services import user_signature as signature_service

    put(client, ME, user_headers)
    old = files_in(settings.signature_dir)

    def fail(*args, **kwargs):
        raise RuntimeError("database down")

    monkeypatch.setattr(signature_service, "_save_path", fail)
    response = put(client, ME, user_headers, signature_bytes(ink=(200, 0, 0)))
    assert _error(response) == (500, "INTERNAL_ERROR")
    assert files_in(settings.signature_dir) == old


def test_remove_own_signature(client, user, user_headers, settings):
    put(client, ME, user_headers)
    response = client.delete(ME, headers=user_headers)
    assert response.status_code == 204
    assert files_in(settings.signature_dir) == []
    assert client.get("/api/v1/me", headers=user_headers).json()["signature_url"] is None
    assert _error(client.get(f"{URL}/{user.id}/signature", headers=user_headers)) == (
        404,
        "NOT_FOUND",
    )


def test_remove_when_there_is_none(client, user_headers):
    assert client.delete(ME, headers=user_headers).status_code == 204


def test_own_signature_needs_a_token(client):
    assert _error(put(client, ME, {})) == (401, "UNAUTHORIZED")
    assert _error(client.delete(ME)) == (401, "UNAUTHORIZED")


def test_blocked_until_password_changed(client, make_user, auth_headers):
    headers = auth_headers(make_user(must_change_password=True))
    assert _error(put(client, ME, headers)) == (403, "PASSWORD_CHANGE_REQUIRED")


# --- Task 68: PUT /users/{id}/signature, DELETE /users/{id}/signature -----------------


def test_admin_sets_a_users_signature(client, as_admin, user):
    response = put(client, f"{URL}/{user.id}/signature", as_admin)
    assert response.status_code == 200, response.text
    assert response.json()["id"] == user.id
    assert response.json()["signature_url"] == f"/api/v1/users/{user.id}/signature"


def test_admin_removes_a_users_signature(client, as_admin, user, user_headers, settings):
    put(client, ME, user_headers)
    assert client.delete(f"{URL}/{user.id}/signature", headers=as_admin).status_code == 204
    assert files_in(settings.signature_dir) == []


def test_only_admin_sets_others(client, user, make_user, auth_headers):
    other = auth_headers(make_user(roles=["STAFF"]))
    assert _error(put(client, f"{URL}/{user.id}/signature", other)) == (403, "FORBIDDEN")
    response = client.delete(f"{URL}/{user.id}/signature", headers=other)
    assert _error(response) == (403, "FORBIDDEN")


def test_admin_unknown_user(client, as_admin):
    assert _error(put(client, f"{URL}/999999/signature", as_admin)) == (404, "NOT_FOUND")
    response = client.delete(f"{URL}/999999/signature", headers=as_admin)
    assert _error(response) == (404, "NOT_FOUND")


@pytest.mark.parametrize("bad_id", ["abc", "0", "-1"])
def test_bad_user_id(client, as_admin, bad_id):
    assert _error(put(client, f"{URL}/{bad_id}/signature", as_admin)) == (422, "VALIDATION_ERROR")


# --- Task 69: GET /users/{id}/signature -----------------------------------------------


def test_anyone_signed_in_can_see_it(client, user, user_headers, make_user, auth_headers):
    put(client, ME, user_headers)
    other = auth_headers(make_user(roles=[]))
    response = client.get(f"{URL}/{user.id}/signature", headers=other)
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert "private" in response.headers["cache-control"]


def test_inactive_users_signature_still_shows(client, user, user_headers, as_admin, db_session):
    put(client, ME, user_headers)
    user.is_active = False
    db_session.flush()
    assert client.get(f"{URL}/{user.id}/signature", headers=as_admin).status_code == 200


def test_signature_needs_a_token(client, user, user_headers):
    put(client, ME, user_headers)
    assert _error(client.get(f"{URL}/{user.id}/signature")) == (401, "UNAUTHORIZED")


def test_no_signature(client, user, as_admin):
    assert _error(client.get(f"{URL}/{user.id}/signature", headers=as_admin)) == (
        404,
        "NOT_FOUND",
    )


def test_unknown_user(client, as_admin):
    assert _error(client.get(f"{URL}/999999/signature", headers=as_admin)) == (404, "NOT_FOUND")


def test_file_missing_on_disk(client, user, user_headers, as_admin, settings, caplog):
    put(client, ME, user_headers)
    for path in files_in(settings.signature_dir):
        path.unlink()
    with caplog.at_level(logging.WARNING):
        response = client.get(f"{URL}/{user.id}/signature", headers=as_admin)
    assert _error(response) == (404, "NOT_FOUND")
    assert any(record.levelno == logging.WARNING for record in caplog.records)


def test_not_served_from_public_uploads(client, user, user_headers, settings):
    put(client, ME, user_headers)
    (path,) = files_in(settings.signature_dir)
    relative = path.relative_to(settings.signature_dir).as_posix()
    assert client.get(f"/uploads/{relative}").status_code == 404
