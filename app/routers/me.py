from fastapi import APIRouter

from app.routers.common import DbSession
from app.schemas.user import UserDetail
from app.security import PasswordChangeAllowedUser
from app.services.user import build_user_detail

router = APIRouter(prefix="/me", tags=["me"])


@router.get(
    "",
    response_model=UserDetail,
    summary="See my profile (allowed while a password change is required)",
)
def get_me(current: PasswordChangeAllowedUser, session: DbSession) -> UserDetail:
    return build_user_detail(session, current.user)
