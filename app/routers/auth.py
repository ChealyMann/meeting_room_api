from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.config import Settings, get_app_settings
from app.db import get_db
from app.schemas.auth import LoginRequest, RefreshRequest, Tokens
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
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_app_settings)],
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
def refresh(
    body: RefreshRequest,
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> Tokens:
    return auth_service.refresh(session, settings, body.refresh_token)
