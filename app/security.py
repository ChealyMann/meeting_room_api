"""Password hashing, JWT tokens, the current-user dependency and role checks.

Spec sections 5 and 9.
"""

import hashlib
import hmac
import re
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from typing import Annotated, Literal

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings, get_app_settings
from app.constants.roles import RoleCode
from app.db import get_db
from app.errors import AppError, ErrorCode
from app.models import Role, User, user_roles

# --- Passwords -------------------------------------------------------------------------

# Argon2id with the library defaults. Not bcrypt: it silently cuts passwords at 72 bytes.
_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    """Hash a password exactly as typed. Passwords are never trimmed."""
    return _hasher.hash(password)


@lru_cache(maxsize=1)
def _dummy_hash() -> str:
    return _hasher.hash("dummy-password-used-only-for-timing")


def verify_password(password_hash: str | None, password: str) -> bool:
    """True if `password` matches. With no hash (unknown email), still does the slow work
    so the response time does not reveal which emails exist, then returns False."""
    try:
        if password_hash is None:
            _hasher.verify(_dummy_hash(), password)
            return False
        return _hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


def needs_rehash(password_hash: str) -> bool:
    """True when the hash was made with older Argon2 settings; rehash it on a good login."""
    return _hasher.check_needs_rehash(password_hash)


def password_fingerprint(password_hash: str) -> str:
    """Put in every token as `pwd`, so a password change or reset logs out every device."""
    return hashlib.sha256(password_hash.encode()).hexdigest()[:16]


# --- Tokens ----------------------------------------------------------------------------

ALGORITHM = "HS256"
TokenType = Literal["access", "refresh"]
_REQUIRED_CLAIMS = ["sub", "type", "iat", "exp", "jti", "pwd"]
_USER_ID = re.compile(r"[1-9][0-9]*")


def _create_token(
    user: User, token_type: TokenType, lifetime: timedelta, settings: Settings
) -> str:
    now = datetime.now(UTC).replace(microsecond=0)
    claims = {
        "sub": str(user.id),
        "type": token_type,
        "iat": now,
        "exp": now + lifetime,
        "jti": str(uuid.uuid4()),
        "pwd": password_fingerprint(user.password_hash),
    }
    return jwt.encode(claims, settings.jwt_secret, algorithm=ALGORITHM)


def create_access_token(user: User, settings: Settings) -> str:
    return _create_token(user, "access", timedelta(minutes=settings.access_token_minutes), settings)


def create_refresh_token(user: User, settings: Settings) -> str:
    return _create_token(user, "refresh", timedelta(days=settings.refresh_token_days), settings)


def _unauthorized() -> AppError:
    return AppError(
        ErrorCode.UNAUTHORIZED, 401, "Please sign in again.", headers={"WWW-Authenticate": "Bearer"}
    )


def decode_token(token: str, expected_type: TokenType, settings: Settings) -> dict:
    """The token's claims, or 401 UNAUTHORIZED if it is invalid, expired or the wrong type."""
    try:
        claims = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[ALGORITHM],
            options={"require": _REQUIRED_CLAIMS},
        )
    except jwt.PyJWTError:
        raise _unauthorized() from None
    if claims["type"] != expected_type or not _USER_ID.fullmatch(str(claims["sub"])):
        raise _unauthorized()
    return claims


def user_from_token(
    session: Session, token: str, token_type: TokenType, settings: Settings
) -> User:
    """Checks 1-3 of spec section 5 for any token: valid and of `token_type`, the user
    exists and is active, and the password has not changed since the token was issued.
    Anything else is 401 UNAUTHORIZED."""
    claims = decode_token(token, token_type, settings)
    user = session.get(User, int(claims["sub"]))
    if user is None or not user.is_active:
        raise _unauthorized()
    if not hmac.compare_digest(claims["pwd"], password_fingerprint(user.password_hash)):
        raise _unauthorized()
    return user


# --- Current user ----------------------------------------------------------------------

_ROLE_ORDER = {code.value: index for index, code in enumerate(RoleCode)}


@dataclass(frozen=True)
class CurrentUser:
    """The signed-in user and their role codes, read from the database on this request."""

    user: User
    role_codes: tuple[str, ...]

    @property
    def id(self) -> int:
        return self.user.id

    def has_role(self, *codes: str) -> bool:
        return any(code in self.role_codes for code in codes)


def load_role_codes(session: Session, user_id: int) -> tuple[str, ...]:
    """The user's role codes in seed order: ADMIN, ROOM_OWNER, STAFF, PITIKA, IT_LEAD, IT_STAFF."""
    codes = session.scalars(
        select(Role.code)
        .join(user_roles, user_roles.c.role_id == Role.id)
        .where(user_roles.c.user_id == user_id)
    )
    return tuple(sorted(codes, key=lambda code: _ROLE_ORDER.get(code, len(_ROLE_ORDER))))


_bearer = HTTPBearer(auto_error=False, description="The access token from POST /auth/login.")


def get_current_user_allow_password_change(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> CurrentUser:
    """Checks 1-3 of spec section 5. Only for the endpoints a user may call while they must
    change their password: POST /auth/change-password, POST /auth/logout and GET /me."""
    if credentials is None:
        raise _unauthorized()
    user = user_from_token(session, credentials.credentials, "access", settings)
    return CurrentUser(user=user, role_codes=load_role_codes(session, user.id))


def get_current_user(
    current: Annotated[CurrentUser, Depends(get_current_user_allow_password_change)],
) -> CurrentUser:
    """Checks 1-4 of spec section 5: any active, signed-in user (access label "Any")."""
    if current.user.must_change_password:
        raise AppError(
            ErrorCode.PASSWORD_CHANGE_REQUIRED, 403, "Please change your password first."
        )
    return current


def require_roles(*codes: str):
    """Check 5 of spec section 5: a dependency that lets through users with any of `codes`.

    Usage: `current: CurrentUser = Depends(require_roles("ADMIN"))`.
    """
    unknown = [code for code in codes if code not in _ROLE_ORDER]
    if not codes or unknown:
        raise ValueError(f"Unknown role codes: {unknown or 'none given'}")

    def dependency(current: Annotated[CurrentUser, Depends(get_current_user)]) -> CurrentUser:
        if not current.has_role(*codes):
            raise AppError(ErrorCode.FORBIDDEN, 403, "You are not allowed.")
        return current

    return dependency


# Short names for route parameters, e.g. `def list_rooms(current: AnyUser): ...`
AnyUser = Annotated[CurrentUser, Depends(get_current_user)]
PasswordChangeAllowedUser = Annotated[CurrentUser, Depends(get_current_user_allow_password_change)]
AdminUser = Annotated[CurrentUser, Depends(require_roles(RoleCode.ADMIN))]
