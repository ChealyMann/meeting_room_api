"""POST /api/v1/auth/change-password (spec section 11, rules R16 and R18)."""

from typing import Annotated

import pytest
from fastapi import Depends

from app.security import CurrentUser, get_current_user, verify_password
from tests.factories import DEFAULT_PASSWORD

URL = "/api/v1/auth/change-password"
NEW = "MyNewPassword@123"


@pytest.fixture
def whoami(app):
    @app.get("/t/whoami")
    def route(current: Annotated[CurrentUser, Depends(get_current_user)]):
        return {"id": current.id}

    return "/t/whoami"


def change(client, headers, current=DEFAULT_PASSWORD, new=NEW):
    return client.post(
        URL, json={"current_password": current, "new_password": new}, headers=headers
    )


def _fields(response) -> dict:
    assert response.status_code == 422, response.text
    return response.json()["error"]["fields"]


# --- Success ---------------------------------------------------------------------------


def test_change_password(client, make_user, auth_headers, db_session):
    user = make_user()
    response = change(client, auth_headers(user))
    assert response.status_code == 200
    body = response.json()
    assert body["must_change_password"] is False
    assert body["token_type"] == "bearer"
    db_session.refresh(user)
    assert verify_password(user.password_hash, NEW)
    assert not verify_password(user.password_hash, DEFAULT_PASSWORD)


def test_first_sign_in_flow(client, make_user, auth_headers, whoami, db_session):
    """Story 1: a new user must change the temporary password, then can use the API."""
    user = make_user(must_change_password=True)
    headers = auth_headers(user)
    assert client.get(whoami, headers=headers).status_code == 403

    response = change(client, headers)
    assert response.status_code == 200
    assert response.json()["must_change_password"] is False
    db_session.refresh(user)
    assert user.must_change_password is False

    new_headers = {"Authorization": f"Bearer {response.json()['access_token']}"}
    assert client.get(whoami, headers=new_headers).status_code == 200


def test_old_tokens_stop_working(client, make_user, auth_headers, whoami):
    user = make_user()
    old = auth_headers(user)
    new_access = change(client, old).json()["access_token"]
    assert client.get(whoami, headers=old).status_code == 401
    assert client.get(whoami, headers={"Authorization": f"Bearer {new_access}"}).status_code == 200


def test_old_refresh_token_stops_working(client, make_user, auth_headers, settings):
    from app.security import create_refresh_token

    user = make_user()
    old_refresh = create_refresh_token(user, settings)
    change(client, auth_headers(user))
    response = client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert response.status_code == 401


def test_can_sign_in_with_the_new_password(client, make_user, auth_headers):
    user = make_user()
    change(client, auth_headers(user))
    login = client.post("/api/v1/auth/login", json={"email": user.email, "password": NEW})
    assert login.status_code == 200


def test_new_password_is_not_trimmed(client, make_user, auth_headers, db_session):
    user = make_user()
    change(client, auth_headers(user), new=" spaced password ")
    db_session.refresh(user)
    assert verify_password(user.password_hash, " spaced password ")
    assert not verify_password(user.password_hash, "spaced password")


# --- Refused ---------------------------------------------------------------------------


def test_wrong_current_password(client, make_user, auth_headers, db_session):
    user = make_user()
    old_hash = user.password_hash
    response = change(client, auth_headers(user), current="Not@MyPassword1")
    assert response.status_code == 400
    assert response.json()["error"] == {
        "code": "WRONG_PASSWORD",
        "message": "Current password is wrong.",
    }
    db_session.refresh(user)
    assert user.password_hash == old_hash


def test_new_password_same_as_current(client, make_user, auth_headers):
    user = make_user()
    response = change(client, auth_headers(user), new=DEFAULT_PASSWORD)
    assert _fields(response) == {"new_password": "Use a new password."}


@pytest.mark.parametrize("new", ["user.email@company.com", "USER.EMAIL@Company.com"])
def test_new_password_same_as_email(client, make_user, auth_headers, new):
    user = make_user(email="user.email@company.com")
    assert _fields(change(client, auth_headers(user), new=new)) == {
        "new_password": "Password cannot be your email."
    }


@pytest.mark.parametrize("new", ["x" * 7, "x" * 129])
def test_new_password_length(client, make_user, auth_headers, new):
    assert _fields(change(client, auth_headers(make_user()), new=new)) == {
        "new_password": "Password must be 8 to 128 characters."
    }


def test_missing_fields(client, make_user, auth_headers):
    response = client.post(URL, json={}, headers=auth_headers(make_user()))
    assert set(_fields(response)) == {"current_password", "new_password"}


def test_unknown_field(client, make_user, auth_headers):
    response = client.post(
        URL,
        json={"current_password": DEFAULT_PASSWORD, "new_password": NEW, "email": "x@y.com"},
        headers=auth_headers(make_user()),
    )
    assert _fields(response) == {"email": "Unknown field."}


def test_needs_a_token(client):
    response = client.post(URL, json={"current_password": "a" * 8, "new_password": NEW})
    assert response.status_code == 401


def test_inactive_user_cannot_change(client, make_user, auth_headers, db_session):
    user = make_user()
    headers = auth_headers(user)
    user.is_active = False
    db_session.flush()
    assert change(client, headers).status_code == 401
