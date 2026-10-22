"""Sign-in logic (spec section 9). No FastAPI imports: the booking scope reuses these."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.errors import AppError, ErrorCode
from app.models import User, utcnow
from app.schemas.auth import Tokens
from app.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    needs_rehash,
    user_from_token,
    verify_password,
)
from app.services.login_rate_limit import LoginRateLimiter


def normalize_email(email: str) -> str:
    return email.strip().lower()


def issue_tokens(user: User, settings: Settings) -> Tokens:
    """A fresh access and refresh token for `user`."""
    return Tokens(
        access_token=create_access_token(user, settings),
        refresh_token=create_refresh_token(user, settings),
        expires_in=settings.access_token_minutes * 60,
        must_change_password=user.must_change_password,
    )


def login(
    session: Session,
    settings: Settings,
    limiter: LoginRateLimiter,
    email: str,
    password: str,
    client_ip: str,
) -> Tokens:
    """Check the email and password and return tokens.

    Wrong email, wrong password and inactive user all fail the same way (401), and an
    unknown email still runs a password check so the timing does not reveal it.
    """
    email = normalize_email(email)
    limit_key = (email, client_ip)
    retry_after = limiter.retry_after(limit_key)
    if retry_after is not None:
        raise AppError(
            ErrorCode.RATE_LIMITED,
            429,
            "Too many tries. Try again later.",
            headers={"Retry-After": str(retry_after)},
        )

    user = session.scalars(select(User).where(User.email == email)).one_or_none()
    password_ok = verify_password(user.password_hash if user else None, password)
    if user is None or not password_ok or not user.is_active:
        limiter.record_failure(limit_key)
        raise AppError(ErrorCode.INVALID_CREDENTIALS, 401, "Email or password is wrong.")

    limiter.reset(limit_key)
    if needs_rehash(user.password_hash):
        # Rare (after an Argon2 settings upgrade). The new hash changes the password
        # fingerprint, so the user's older tokens on other devices stop working.
        user.password_hash = hash_password(password)
    user.last_login_at = utcnow()
    session.commit()
    return issue_tokens(user, settings)


def refresh(session: Session, settings: Settings, refresh_token: str) -> Tokens:
    """New tokens for a valid refresh token (401 if expired, wrong type, user inactive or
    password changed). Tokens are stateless, so the old refresh token is not revoked."""
    user = user_from_token(session, refresh_token, "refresh", settings)
    return issue_tokens(user, settings)
