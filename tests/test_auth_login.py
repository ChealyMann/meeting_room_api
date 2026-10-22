"""POST /api/v1/auth/login (spec sections 9 and 11, edge cases in section 16)."""

from datetime import timedelta

import jwt
import pytest
from argon2 import PasswordHasher
from fastapi.testclient import TestClient

import app.services.auth as auth_service
from app.models import utcnow
from app.security import needs_rehash, password_fingerprint
from tests.factories import DEFAULT_PASSWORD

URL = "/api/v1/auth/login"
WRONG = {"error": {"code": "INVALID_CREDENTIALS", "message": "Email or password is wrong."}}


def login(client, email, password=DEFAULT_PASSWORD):
    return client.post(URL, json={"email": email, "password": password})


# --- Success ---------------------------------------------------------------------------


def test_login_returns_tokens(client, make_user, settings):
    user = make_user()
    response = login(client, user.email)
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {
        "access_token",
        "refresh_token",
        "token_type",
        "expires_in",
        "must_change_password",
    }
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 900
    assert body["must_change_password"] is False

    access = jwt.decode(body["access_token"], settings.jwt_secret, algorithms=["HS256"])
    refresh = jwt.decode(body["refresh_token"], settings.jwt_secret, algorithms=["HS256"])
    assert (access["sub"], access["type"]) == (str(user.id), "access")
    assert (refresh["sub"], refresh["type"]) == (str(user.id), "refresh")
    assert access["pwd"] == password_fingerprint(user.password_hash)


def test_access_token_works_on_the_api(client, make_user, app):
    from typing import Annotated

    from fastapi import Depends

    from app.security import CurrentUser, get_current_user

    @app.get("/t/whoami")
    def whoami(current: Annotated[CurrentUser, Depends(get_current_user)]):
        return {"id": current.id}

    user = make_user()
    token = login(client, user.email).json()["access_token"]
    response = client.get("/t/whoami", headers={"Authorization": f"Bearer {token}"})
    assert response.json() == {"id": user.id}


def test_email_is_trimmed_and_lowercased(client, make_user):
    make_user(email="sok.dara@company.com")
    assert login(client, "  Sok.Dara@Company.COM ").status_code == 200


def test_must_change_password_is_reported(client, make_user):
    user = make_user(must_change_password=True)
    response = login(client, user.email)
    assert response.status_code == 200
    assert response.json()["must_change_password"] is True


def test_last_login_at_is_set(client, make_user, db_session):
    user = make_user()
    assert user.last_login_at is None
    login(client, user.email)
    db_session.refresh(user)
    assert abs(user.last_login_at - utcnow()) < timedelta(seconds=5)


def test_outdated_hash_is_upgraded_on_login(client, make_user, db_session):
    weak = PasswordHasher(time_cost=1, memory_cost=8, parallelism=1)
    user = make_user(password_hash=weak.hash("Password@123"))
    response = login(client, user.email, "Password@123")
    assert response.status_code == 200
    db_session.refresh(user)
    assert not needs_rehash(user.password_hash)
    # The new tokens carry the new hash's fingerprint, so they keep working.
    access = jwt.decode(response.json()["access_token"], options={"verify_signature": False})
    assert access["pwd"] == password_fingerprint(user.password_hash)


def test_khmer_password(client, make_user):
    user = make_user(password="ពាក្យសម្ងាត់១២៣")
    assert login(client, user.email, "ពាក្យសម្ងាត់១២៣").status_code == 200


# --- Failure: always the same answer ---------------------------------------------------


def test_wrong_password(client, make_user):
    user = make_user()
    response = login(client, user.email, "Wrong@Password1")
    assert response.status_code == 401
    assert response.json() == WRONG


def test_unknown_email_gets_the_same_answer(client):
    response = login(client, "nobody@company.com")
    assert response.status_code == 401
    assert response.json() == WRONG


def test_unknown_email_still_checks_a_password(client, monkeypatch):
    """So the response time does not show which emails exist."""
    calls = []
    real = auth_service.verify_password

    def spy(password_hash, password):
        calls.append((password_hash, password))
        return real(password_hash, password)

    monkeypatch.setattr(auth_service, "verify_password", spy)
    login(client, "nobody@company.com", "Some@Password1")
    assert calls == [(None, "Some@Password1")]


def test_inactive_user_with_right_password(client, make_user):
    user = make_user(is_active=False)
    response = login(client, user.email)
    assert response.status_code == 401
    assert response.json() == WRONG


def test_password_spaces_are_kept(client, make_user):
    user = make_user(password=" abc12345")
    assert login(client, user.email, "abc12345").status_code == 401
    assert login(client, user.email, " abc12345").status_code == 200


def test_failed_login_does_not_set_last_login_at(client, make_user, db_session):
    user = make_user()
    login(client, user.email, "Wrong@Password1")
    db_session.refresh(user)
    assert user.last_login_at is None


# --- Body checks -----------------------------------------------------------------------


def test_missing_fields(client):
    response = client.post(URL, json={})
    assert response.status_code == 422
    assert set(response.json()["error"]["fields"]) == {"email", "password"}


def test_unknown_field(client):
    response = client.post(URL, json={"email": "a@b.com", "password": "x", "remember": True})
    assert response.json()["error"]["fields"] == {"remember": "Unknown field."}


def test_empty_password(client):
    response = client.post(URL, json={"email": "a@b.com", "password": ""})
    assert response.json()["error"]["fields"] == {"password": "This field is required."}


def test_needs_no_token(client, make_user):
    assert login(client, make_user().email).status_code == 200


# --- Rate limit ------------------------------------------------------------------------


def test_sixth_failed_login_is_rate_limited(client, make_user):
    user = make_user()
    for _ in range(5):
        assert login(client, user.email, "Wrong@Password1").status_code == 401
    response = login(client, user.email, "Wrong@Password1")
    assert response.status_code == 429
    assert response.json()["error"]["code"] == "RATE_LIMITED"
    assert 1 <= int(response.headers["retry-after"]) <= 15 * 60


def test_right_password_is_refused_while_blocked(client, make_user):
    user = make_user()
    for _ in range(5):
        login(client, user.email, "Wrong@Password1")
    assert login(client, user.email).status_code == 429


def test_rate_limit_ignores_email_case(client, make_user):
    make_user(email="sok.dara@company.com")
    for _ in range(5):
        login(client, "SOK.DARA@company.com", "Wrong@Password1")
    assert login(client, "sok.dara@company.com").status_code == 429


def test_rate_limit_counts_unknown_emails_too(client):
    for _ in range(5):
        login(client, "nobody@company.com", "Wrong@Password1")
    assert login(client, "nobody@company.com", "Wrong@Password1").status_code == 429


def test_rate_limit_is_per_email(client, make_user):
    first, second = make_user(), make_user()
    for _ in range(5):
        login(client, first.email, "Wrong@Password1")
    assert login(client, second.email).status_code == 200


def test_rate_limit_is_per_ip(app, client, make_user):
    user = make_user()
    for _ in range(5):
        login(client, user.email, "Wrong@Password1")
    with TestClient(app, client=("10.9.9.9", 50000)) as other_computer:
        assert login(other_computer, user.email).status_code == 200


def test_success_clears_earlier_failures(client, make_user):
    user = make_user()
    for _ in range(4):
        login(client, user.email, "Wrong@Password1")
    assert login(client, user.email).status_code == 200
    for _ in range(4):
        assert login(client, user.email, "Wrong@Password1").status_code == 401
    assert login(client, user.email).status_code == 200


@pytest.mark.parametrize("password", ["Wrong@Password1", DEFAULT_PASSWORD])
def test_inactive_user_counts_as_a_failure(client, make_user, password):
    user = make_user(is_active=False)
    for _ in range(5):
        login(client, user.email, password)
    assert login(client, user.email, password).status_code == 429
