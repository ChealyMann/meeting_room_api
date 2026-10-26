from typing import Annotated

from fastapi import APIRouter, Depends, Query, UploadFile
from fastapi.responses import FileResponse

from app.routers.common import (
    AppSettings,
    DbSession,
    IdPath,
    IdQuery,
    IsActiveQuery,
    PageParams,
    ProvinceQuery,
    SearchQuery,
)
from app.schemas.common import Page
from app.schemas.user import (
    ResetPasswordRequest,
    SetRolesRequest,
    UserChanged,
    UserCreate,
    UserDetail,
    UserListItem,
    UserUpdate,
)
from app.security import AdminUser, AnyUser
from app.services import user as user_service
from app.services import user_avatar as avatar_service
from app.services import user_signature as signature_service

router = APIRouter(prefix="/users", tags=["User & roles"])


def _changed(session, user, rooms_unassigned: list[int]) -> UserChanged:
    detail = user_service.build_user_detail(session, user)
    return UserChanged(**detail.model_dump(), rooms_unassigned=rooms_unassigned)


@router.get("", response_model=Page[UserListItem], summary="List users")
def list_users(
    current: AdminUser,
    session: DbSession,
    paging: Annotated[PageParams, Depends()],
    division_id: IdQuery = None,
    department_id: IdQuery = None,
    position_id: IdQuery = None,
    role: Annotated[str | None, Query(description="A role code, e.g. PITIKA")] = None,
    province: ProvinceQuery = None,
    is_active: IsActiveQuery = None,
    search: SearchQuery = None,
) -> Page[UserListItem]:
    """Search matches English name, Khmer name, staff ID and email. Sorted by English name."""
    result = user_service.list_users(
        session,
        paging.page,
        paging.size,
        division_id,
        department_id,
        position_id,
        role,
        province,
        is_active,
        search,
    )
    users = result["items"]
    codes = user_service.role_codes_by_user(session, [user.id for user in users])
    items = [user_service.build_user_list_item(user, codes[user.id]) for user in users]
    return Page[UserListItem](**{**result, "items": items})


@router.get("/{user_id}", response_model=UserDetail, summary="See one user")
def get_user(user_id: IdPath, current: AdminUser, session: DbSession) -> UserDetail:
    return user_service.build_user_detail(session, user_service.get_user(session, user_id))


@router.post(
    "",
    response_model=UserDetail,
    status_code=201,
    summary="Create a user (no roles; must change the temporary password)",
)
def create_user(body: UserCreate, current: AdminUser, session: DbSession) -> UserDetail:
    user = user_service.create_user(session, body.model_dump())
    return user_service.build_user_detail(session, user)


@router.patch(
    "/{user_id}",
    response_model=UserChanged,
    summary="Change a user, or turn them off or on",
)
def update_user(
    user_id: IdPath, body: UserUpdate, current: AdminUser, session: DbSession
) -> UserChanged:
    """Turning a user off clears the rooms they own; `rooms_unassigned` lists them."""
    changes = body.model_dump(exclude_unset=True)
    user, rooms_unassigned = user_service.update_user(session, user_id, changes, current.id)
    return _changed(session, user, rooms_unassigned)


@router.post(
    "/{user_id}/reset-password",
    status_code=204,
    summary="Set a temporary password (signs the user out everywhere)",
)
def reset_password(
    user_id: IdPath, body: ResetPasswordRequest, current: AdminUser, session: DbSession
) -> None:
    user_service.reset_password(session, user_id, body.temporary_password)


@router.put("/{user_id}/roles", response_model=UserChanged, summary="Replace a user's roles")
def set_roles(
    user_id: IdPath, body: SetRolesRequest, current: AdminUser, session: DbSession
) -> UserChanged:
    """Removing Room owner clears the rooms the user owns; `rooms_unassigned` lists them."""
    user, rooms_unassigned = user_service.set_user_roles(
        session, user_id, body.role_codes, current.id
    )
    return _changed(session, user, rooms_unassigned)


@router.get(
    "/{user_id}/signature",
    response_class=FileResponse,
    summary="See a user's signature (PNG)",
    responses={200: {"content": {"image/png": {}}}, 404: {"description": "NOT_FOUND"}},
)
def get_signature(
    user_id: IdPath, current: AnyUser, session: DbSession, settings: AppSettings
) -> FileResponse:
    """Any signed-in user, for booking approval forms. 404 when the user has none."""
    user = user_service.get_user(session, user_id)
    path = signature_service.signature_file(settings, user)
    return FileResponse(
        path, media_type="image/png", headers={"Cache-Control": "private, no-cache"}
    )


@router.put(
    "/{user_id}/signature",
    response_model=UserDetail,
    summary="Upload a user's signature (JPEG, PNG or WebP)",
    responses={
        413: {"description": "FILE_TOO_LARGE"},
        415: {"description": "UNSUPPORTED_FILE_TYPE"},
        422: {"description": "INVALID_IMAGE or VALIDATION_ERROR"},
    },
)
def set_signature(
    user_id: IdPath,
    file: UploadFile,
    current: AdminUser,
    session: DbSession,
    settings: AppSettings,
) -> UserDetail:
    """Saved as a transparent PNG cropped to the ink; replaces any earlier signature."""
    user = user_service.get_user(session, user_id)
    signature_service.set_signature(session, settings, user, file.file)
    return user_service.build_user_detail(session, user)


@router.delete("/{user_id}/signature", status_code=204, summary="Remove a user's signature")
def remove_signature(
    user_id: IdPath, current: AdminUser, session: DbSession, settings: AppSettings
) -> None:
    user = user_service.get_user(session, user_id)
    signature_service.remove_signature(session, settings, user)


@router.get(
    "/{user_id}/avatar",
    response_class=FileResponse,
    summary="See a user's photo (JPEG)",
    responses={200: {"content": {"image/jpeg": {}}}, 404: {"description": "NOT_FOUND"}},
)
def get_avatar(
    user_id: IdPath, current: AnyUser, session: DbSession, settings: AppSettings
) -> FileResponse:
    """Any signed-in user. 404 when the user has no photo."""
    user = user_service.get_user(session, user_id)
    path = avatar_service.avatar_file(settings, user)
    return FileResponse(
        path, media_type="image/jpeg", headers={"Cache-Control": "private, no-cache"}
    )


@router.put(
    "/{user_id}/avatar",
    response_model=UserDetail,
    summary="Upload a user's photo (JPEG, PNG or WebP)",
    responses={
        413: {"description": "FILE_TOO_LARGE"},
        415: {"description": "UNSUPPORTED_FILE_TYPE"},
        422: {"description": "INVALID_IMAGE or VALIDATION_ERROR"},
    },
)
def set_avatar(
    user_id: IdPath,
    file: UploadFile,
    current: AdminUser,
    session: DbSession,
    settings: AppSettings,
) -> UserDetail:
    """Saved as a square JPEG (at most 512 x 512); replaces any earlier photo."""
    user = user_service.get_user(session, user_id)
    avatar_service.set_avatar(session, settings, user, file.file)
    return user_service.build_user_detail(session, user)


@router.delete("/{user_id}/avatar", status_code=204, summary="Remove a user's photo")
def remove_avatar(
    user_id: IdPath, current: AdminUser, session: DbSession, settings: AppSettings
) -> None:
    user = user_service.get_user(session, user_id)
    avatar_service.remove_avatar(session, settings, user)
