"""POST /api/v1/auth/refresh (spec sections 9 and 11, edge cases in section 16)."""

from datetime import UTC, datetime, timedelta
from typing import Annotated

import jwt
import pytest
from fastapi import Depends

from app.security import (
    CurrentUser,
    create_access_token,
    create_refresh_token,
    get_current_user,
    hash_password,
)

URL = "/api/v1/auth/refresh"
UNAUTHORIZED = (401, "UNAUTHORIZED")


def refresh(client, token):
    return client.post(URL, json={"refresh_token": token})


def _error(response) -> tuple[int, str]:
    return response.status_code, response.json()["error"]["code"]


def _claims(token: str, settings) -> dict:
    return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])


# --- Success ---------------------------------------------------------------------------


def test_refresh_returns_new_tokens(client, make_user, settings):
    user = make_user()
    old = create_refresh_token(user, settings)
    response = refresh(client, old)
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 900
    assert body["must_change_password"] is False

    access = _claims(body["access_token"], settings)
    new_refresh = _claims(body["refresh_token"], settings)
    assert (access["sub"], access["type"]) == (str(user.id), "access")
    assert (new_refresh["sub"], new_refresh["type"]) == (str(user.id), "refresh")
    assert new_refresh["jti"] != _claims(old, settings)["jti"]


def test_new_access_token_works(app, client, make_user, settings):
    @app.get("/t/whoami")
    def whoami(current: Annotated[CurrentUser, Depends(get_current_user)]):
        return {"id": current.id}

    user = make_user()
    access = refresh(client, create_refresh_token(user, settings)).json()["access_token"]
    response = client.get("/t/whoami", headers={"Authorization": f"Bearer {access}"})
    assert response.json() == {"id": user.id}


def test_new_refresh_token_can_refresh_again(client, make_user, settings):
    user = make_user()
    second = refresh(client, create_refresh_token(user, settings)).json()["refresh_token"]
    assert refresh(client, second).status_code == 200


def test_tokens_from_login_can_be_refreshed(client, make_user):
    user = make_user()
    login = client.post(
        "/api/v1/auth/login", json={"email": user.email, "password": "Password@123"}
    )
    assert refresh(client, login.json()["refresh_token"]).status_code == 200


def test_reports_must_change_password(client, make_user, settings):
    user = make_user(must_change_password=True)
    response = refresh(client, create_refresh_token(user, settings))
    assert response.status_code == 200
    assert response.json()["must_change_password"] is True


def test_old_refresh_token_still_works_until_it_expires(client, make_user, settings):
    """Tokens are stateless (spec section 9): refreshing does not revoke the old one."""
    user = make_user()
    old = create_refresh_token(user, settings)
    refresh(client, old)
    assert refresh(client, old).status_code == 200


def test_needs_no_authorization_header(client, make_user, settings):
    token = create_refresh_token(make_user(), settings)
    assert client.post(URL, json={"refresh_token": token}, headers={}).status_code == 200


# --- Refused ---------------------------------------------------------------------------


def test_access_token_is_refused(client, make_user, settings):
    assert _error(refresh(client, create_access_token(make_user(), settings))) == UNAUTHORIZED


def test_expired_refresh_token(client, make_user, settings):
    claims = _claims(create_refresh_token(make_user(), settings), settings)
    past = datetime.now(UTC) - timedelta(days=8)
    expired = jwt.encode(
        {**claims, "iat": past, "exp": past + timedelta(days=7)}, settings.jwt_secret
    )
    assert _error(refresh(client, expired)) == UNAUTHORIZED


def test_wrongly_signed_refresh_token(client, make_user, settings):
    claims = _claims(create_refresh_token(make_user(), settings), settings)
    forged = jwt.encode(claims, "someone-elses-secret-" + "z" * 40)
    assert _error(refresh(client, forged)) == UNAUTHORIZED


@pytest.mark.parametrize("token", ["not-a-token", "a.b.c"])
def test_malformed_refresh_token(client, token):
    assert _error(refresh(client, token)) == UNAUTHORIZED


def test_user_deactivated(client, make_user, settings, db_session):
    user = make_user()
    token = create_refresh_token(user, settings)
    user.is_active = False
    db_session.flush()
    assert _error(refresh(client, token)) == UNAUTHORIZED


def test_user_no_longer_exists(client, make_user, settings, db_session):
    user = make_user()
    token = create_refresh_token(user, settings)
    user.id = 999_999
    db_session.flush()
    assert _error(refresh(client, token)) == UNAUTHORIZED


def test_password_changed_since_token_issued(client, make_user, settings, db_session):
    user = make_user()
    token = create_refresh_token(user, settings)
    user.password_hash = hash_password("NewPassword@456")
    db_session.flush()
    assert _error(refresh(client, token)) == UNAUTHORIZED


# --- Body checks -----------------------------------------------------------------------


def test_missing_refresh_token(client):
    response = client.post(URL, json={})
    assert response.status_code == 422
    assert response.json()["error"]["fields"] == {"refresh_token": "This field is required."}


def test_empty_refresh_token(client):
    response = refresh(client, "")
    assert response.json()["error"]["fields"] == {"refresh_token": "This field is required."}


def test_unknown_field(client):
    response = client.post(URL, json={"refresh_token": "x", "access_token": "y"})
    assert response.json()["error"]["fields"] == {"access_token": "Unknown field."}
