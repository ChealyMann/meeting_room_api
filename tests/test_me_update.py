"""PATCH /api/v1/me (spec section 11, requirements AUTH-F07 and AUTH-V11 to V13)."""

from datetime import datetime

import pytest

URL = "/api/v1/me"
OLD = datetime(2026, 1, 1, 0, 0, 0)


def patch(client, headers, body):
    return client.patch(URL, json=body, headers=headers)


def _fields(response) -> dict:
    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    return response.json()["error"]["fields"]


@pytest.fixture
def user(make_user, db_session):
    user = make_user(
        email="sok.dara@company.com",
        secondary_email="dara.old@gmail.com",
        phone="011 111 111",
    )
    user.updated_at = OLD
    db_session.flush()
    return user


@pytest.fixture
def headers(user, auth_headers):
    return auth_headers(user)


# --- Success ---------------------------------------------------------------------------


def test_update_all_three_fields(client, headers, user, db_session):
    response = patch(
        client,
        headers,
        {
            "secondary_email": "  Dara.Personal@Gmail.com ",
            "phone": " 012 345 678 ",
            "email_notifications": False,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["secondary_email"] == "dara.personal@gmail.com"
    assert body["phone"] == "012 345 678"
    assert body["email_notifications"] is False
    assert body["updated_at"] != "2026-01-01T00:00:00Z"
    db_session.refresh(user)
    assert user.secondary_email == "dara.personal@gmail.com"


def test_returns_user_detail(client, headers, user):
    body = patch(client, headers, {"phone": "099"}).json()
    assert body["id"] == user.id
    assert {"roles", "province", "owned_room_ids", "position"} <= set(body)


def test_only_sent_fields_change(client, headers):
    body = patch(client, headers, {"phone": "099 999 999"}).json()
    assert body["phone"] == "099 999 999"
    assert body["secondary_email"] == "dara.old@gmail.com"
    assert body["email_notifications"] is True


def test_empty_body_changes_nothing(client, headers):
    response = patch(client, headers, {})
    assert response.status_code == 200
    assert response.json()["phone"] == "011 111 111"
    assert response.json()["updated_at"] == "2026-01-01T00:00:00Z"


def test_same_value_does_not_change_updated_at(client, headers):
    body = patch(client, headers, {"phone": "011 111 111", "email_notifications": True}).json()
    assert body["updated_at"] == "2026-01-01T00:00:00Z"


@pytest.mark.parametrize("field", ["secondary_email", "phone"])
def test_null_clears_optional_field(client, headers, field):
    assert patch(client, headers, {field: None}).json()[field] is None


@pytest.mark.parametrize("field", ["secondary_email", "phone"])
def test_only_spaces_clears_optional_field(client, headers, field):
    assert patch(client, headers, {field: "   "}).json()[field] is None


def test_photo_link_is_refused(client, headers):
    """The photo is uploaded with PUT /me/avatar (R20); a link is an unknown field."""
    assert _fields(patch(client, headers, {"avatar_url": "https://cdn.company.com/a.jpg"})) == {
        "avatar_url": "Unknown field."
    }


def test_phone_of_20_characters(client, headers):
    assert patch(client, headers, {"phone": "+855 12 345 678 9012"}).status_code == 200


# --- Refused ---------------------------------------------------------------------------


def test_email_notifications_cannot_be_null(client, headers):
    assert _fields(patch(client, headers, {"email_notifications": None})) == {
        "email_notifications": "This field is required."
    }


@pytest.mark.parametrize("value", ["sok.dara@company.com", " SOK.Dara@Company.COM "])
def test_second_email_must_differ_from_email(client, headers, value):
    assert _fields(patch(client, headers, {"secondary_email": value})) == {
        "secondary_email": "Second email must be different."
    }


@pytest.mark.parametrize("value", ["not-an-email", "a@b", "a b@c.com", "@company.com", "a@@b.com"])
def test_second_email_must_be_an_email(client, headers, value):
    assert _fields(patch(client, headers, {"secondary_email": value})) == {
        "secondary_email": "Must be a valid email address."
    }


def test_second_email_max_254(client, headers):
    value = "a" * 245 + "@gmail.com"  # 255 characters
    assert _fields(patch(client, headers, {"secondary_email": value})) == {
        "secondary_email": "Too long (max 254)."
    }


def test_phone_max_20(client, headers):
    assert _fields(patch(client, headers, {"phone": "1" * 21})) == {"phone": "Too long (max 20)."}


@pytest.mark.parametrize(
    "field",
    [
        "name_en",
        "name_kh",
        "email",
        "staff_id",
        "title",
        "division_id",
        "position_id",
        "roles",
        "role_codes",
        "is_active",
        "must_change_password",
        "password_hash",
        "id",
    ],
)
def test_other_fields_cannot_be_changed(client, headers, user, db_session, field):
    response = patch(client, headers, {field: "x", "phone": "099"})
    assert _fields(response) == {field: "Unknown field."}
    db_session.refresh(user)
    assert user.phone == "011 111 111"  # nothing saved


def test_not_allowed_while_password_change_required(client, make_user, auth_headers):
    user = make_user(must_change_password=True)
    response = patch(client, auth_headers(user), {"phone": "099"})
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "PASSWORD_CHANGE_REQUIRED"


def test_needs_a_token(client):
    assert client.patch(URL, json={"phone": "099"}).status_code == 401
