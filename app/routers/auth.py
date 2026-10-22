from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.routers.common import AppSettings, DbSession
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    Tokens,
)
from app.security import PasswordChangeAllowedUser
from app.services import auth as auth_service
from app.services.login_rate_limit import LoginRateLimiter

router = APIRouter(prefix="/auth", tags=["auth"])


def get_login_limiter(request: Request) -> LoginRateLimiter:
    return request.app.state.login_limiter


@router.post(
    "/login",
    response_model=Tokens,
    summary="Sign in with email and password",
    responses={401: {"description": "INVALID_CREDENTIALS"}, 429: {"description": "RATE_LIMITED"}},
)
def login(
    body: LoginRequest,
    request: Request,
    session: DbSession,
    settings: AppSettings,
    limiter: Annotated[LoginRateLimiter, Depends(get_login_limiter)],
) -> Tokens:
    client_ip = request.client.host if request.client else "unknown"
    return auth_service.login(session, settings, limiter, body.email, body.password, client_ip)


@router.post(
    "/refresh",
    response_model=Tokens,
    summary="Get new tokens with a refresh token",
    responses={401: {"description": "UNAUTHORIZED"}},
)
def refresh(body: RefreshRequest, session: DbSession, settings: AppSettings) -> Tokens:
    return auth_service.refresh(session, settings, body.refresh_token)


@router.post(
    "/logout",
    status_code=204,
    summary="Sign out (the client deletes its tokens)",
)
def logout(current: PasswordChangeAllowedUser, body: LogoutRequest | None = None) -> None:
    """Tokens are stateless, so nothing is revoked on the server: a token stays valid until
    it expires, the password changes, or the user is deactivated (spec section 9)."""
    return None


@router.post(
    "/change-password",
    response_model=Tokens,
    summary="Change my password (allowed while a password change is required)",
    responses={400: {"description": "WRONG_PASSWORD"}},
)
def change_password(
    body: ChangePasswordRequest,
    current: PasswordChangeAllowedUser,
    session: DbSession,
    settings: AppSettings,
) -> Tokens:
    return auth_service.change_password(
        session, settings, current.user, body.current_password, body.new_password
    )
