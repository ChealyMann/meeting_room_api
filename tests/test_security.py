import hashlib
import uuid
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import jwt
import pytest
from argon2 import PasswordHasher

from app.errors import AppError
from app.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    needs_rehash,
    password_fingerprint,
    verify_password,
)

# Tokens only read `id` and `password_hash`, so a plain object stands in for a user here.
USER = SimpleNamespace(id=15, password_hash=PasswordHasher().hash("Password@123"))


# --- Passwords -------------------------------------------------------------------------


def test_hash_password_uses_argon2id():
    hashed = hash_password("MyPassword@123")
    assert hashed.startswith("$argon2id$")
    assert "MyPassword@123" not in hashed
    assert verify_password(hashed, "MyPassword@123")


def test_same_password_hashes_differently_each_time():
    assert hash_password("MyPassword@123") != hash_password("MyPassword@123")


def test_password_is_not_trimmed():
    hashed = hash_password(" abc12345")
    assert verify_password(hashed, " abc12345")
    assert not verify_password(hashed, "abc12345")


def test_hashes_khmer_password():
    hashed = hash_password("ពាក្យសម្ងាត់១២៣")
    assert verify_password(hashed, "ពាក្យសម្ងាត់១២៣")


def test_long_password_is_not_cut_at_72_bytes():
    hashed = hash_password("a" * 100)
    assert not verify_password(hashed, "a" * 72)


def test_verify_wrong_password():
    assert not verify_password(hash_password("right-password"), "wrong-password")


def test_verify_without_hash_is_false():
    # Login uses this for unknown emails: it still does the slow work, then fails.
    assert verify_password(None, "anything") is False


def test_verify_against_garbage_hash_is_false():
    assert verify_password("not-a-hash", "anything") is False


def test_needs_rehash():
    assert not needs_rehash(hash_password("Password@123"))
    weak = PasswordHasher(time_cost=1, memory_cost=8, parallelism=1).hash("Password@123")
    assert needs_rehash(weak)


def test_password_fingerprint_is_first_16_hex_of_sha256():
    fingerprint = password_fingerprint("$argon2id$abc")
    assert fingerprint == hashlib.sha256(b"$argon2id$abc").hexdigest()[:16]
    assert password_fingerprint("$argon2id$other") != fingerprint


# --- Tokens ----------------------------------------------------------------------------


def _claims(token: str, settings) -> dict:
    return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])


def test_access_token_claims(settings):
    token = create_access_token(USER, settings)
    assert jwt.get_unverified_header(token)["alg"] == "HS256"
    claims = _claims(token, settings)
    assert claims["sub"] == "15"
    assert claims["type"] == "access"
    assert claims["exp"] - claims["iat"] == 15 * 60
    assert uuid.UUID(claims["jti"])
    assert claims["pwd"] == password_fingerprint(USER.password_hash)
    assert "roles" not in claims


def test_refresh_token_claims(settings):
    claims = _claims(create_refresh_token(USER, settings), settings)
    assert claims["type"] == "refresh"
    assert claims["exp"] - claims["iat"] == 7 * 24 * 3600


def test_token_lifetimes_come_from_settings(settings):
    settings.access_token_minutes = 30
    settings.refresh_token_days = 1
    assert (
        _claims(create_access_token(USER, settings), settings)["exp"]
        - _claims(create_access_token(USER, settings), settings)["iat"]
        == 30 * 60
    )
    refresh = _claims(create_refresh_token(USER, settings), settings)
    assert refresh["exp"] - refresh["iat"] == 24 * 3600


def test_every_token_has_its_own_jti(settings):
    first = _claims(create_access_token(USER, settings), settings)["jti"]
    second = _claims(create_access_token(USER, settings), settings)["jti"]
    assert first != second


def test_decode_valid_tokens(settings):
    assert decode_token(create_access_token(USER, settings), "access", settings)["sub"] == "15"
    assert decode_token(create_refresh_token(USER, settings), "refresh", settings)["sub"] == "15"


def _unauthorized(token: str, token_type: str, settings) -> None:
    with pytest.raises(AppError) as exc_info:
        decode_token(token, token_type, settings)
    assert exc_info.value.code == "UNAUTHORIZED"
    assert exc_info.value.status == 401


def test_refresh_token_is_not_an_access_token(settings):
    _unauthorized(create_refresh_token(USER, settings), "access", settings)


def test_access_token_is_not_a_refresh_token(settings):
    _unauthorized(create_access_token(USER, settings), "refresh", settings)


def _signed(settings, secret=None, algorithm="HS256", **overrides) -> str:
    now = datetime.now(UTC)
    claims = {
        "sub": "15",
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=15),
        "jti": str(uuid.uuid4()),
        "pwd": password_fingerprint(USER.password_hash),
        **overrides,
    }
    claims = {k: v for k, v in claims.items() if v is not None}
    key = None if algorithm == "none" else secret or settings.jwt_secret
    return jwt.encode(claims, key, algorithm=algorithm)


def test_expired_token(settings):
    past = datetime.now(UTC) - timedelta(minutes=20)
    _unauthorized(_signed(settings, iat=past, exp=past + timedelta(minutes=15)), "access", settings)


def test_wrongly_signed_token(settings):
    _unauthorized(_signed(settings, secret="another-secret-" + "y" * 40), "access", settings)


def test_malformed_token(settings):
    _unauthorized("not.a.token", "access", settings)
    _unauthorized("", "access", settings)


def test_unsigned_token_is_refused(settings):
    _unauthorized(_signed(settings, algorithm="none"), "access", settings)


def test_other_algorithm_is_refused(settings):
    _unauthorized(_signed(settings, algorithm="HS512"), "access", settings)


@pytest.mark.parametrize("claim", ["sub", "type", "iat", "exp", "jti", "pwd"])
def test_token_missing_a_claim(settings, claim):
    _unauthorized(_signed(settings, **{claim: None}), "access", settings)


@pytest.mark.parametrize("sub", ["abc", "0", "-1", "1.5"])
def test_token_with_bad_user_id(settings, sub):
    _unauthorized(_signed(settings, sub=sub), "access", settings)
