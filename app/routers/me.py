from fastapi import APIRouter

from app.routers.common import DbSession
from app.schemas.user import MeUpdate, UserDetail
from app.security import AnyUser, PasswordChangeAllowedUser
from app.services import user as user_service

router = APIRouter(prefix="/me", tags=["Auth"])


@router.get(
    "",
    response_model=UserDetail,
    summary="See my profile (allowed while a password change is required)",
)
def get_me(current: PasswordChangeAllowedUser, session: DbSession) -> UserDetail:
    return user_service.build_user_detail(session, current.user)


@router.patch(
    "",
    response_model=UserDetail,
    summary="Change my second email, phone, photo link or email notifications",
)
def update_me(body: MeUpdate, current: AnyUser, session: DbSession) -> UserDetail:
    changes = body.model_dump(exclude_unset=True)
    return user_service.update_me(session, current.user, changes)
