from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.routers.common import (
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
from app.security import AdminUser
from app.services import user as user_service

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
