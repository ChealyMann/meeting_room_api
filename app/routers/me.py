from fastapi import APIRouter, UploadFile

from app.routers.common import AppSettings, DbSession
from app.schemas.user import MeUpdate, UserDetail
from app.security import AnyUser, PasswordChangeAllowedUser
from app.services import user as user_service
from app.services import user_signature as signature_service

router = APIRouter(prefix="/me", tags=["Auth"])

_IMAGE_ERRORS = {
    413: {"description": "FILE_TOO_LARGE"},
    415: {"description": "UNSUPPORTED_FILE_TYPE"},
    422: {"description": "INVALID_IMAGE or VALIDATION_ERROR"},
}


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


@router.put(
    "/signature",
    response_model=UserDetail,
    summary="Upload my signature (JPEG, PNG or WebP)",
    responses=_IMAGE_ERRORS,
)
def set_my_signature(
    file: UploadFile, current: AnyUser, session: DbSession, settings: AppSettings
) -> UserDetail:
    """Saved as a transparent PNG cropped to the ink; replaces any earlier signature."""
    user = signature_service.set_signature(session, settings, current.user, file.file)
    return user_service.build_user_detail(session, user)


@router.delete("/signature", status_code=204, summary="Remove my signature")
def remove_my_signature(current: AnyUser, session: DbSession, settings: AppSettings) -> None:
    signature_service.remove_signature(session, settings, current.user)
