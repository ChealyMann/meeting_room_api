from fastapi import APIRouter

from app.routers.common import DbSession, IdPath
from app.schemas.common import ItemList
from app.schemas.role import RoleOut, RoleUpdate
from app.security import AdminUser
from app.services import role as role_service

router = APIRouter(prefix="/roles", tags=["User & roles"])


@router.get("", response_model=ItemList[RoleOut], summary="List the 6 roles")
def list_roles(current: AdminUser, session: DbSession) -> ItemList[RoleOut]:
    """Not paged. In seed order: Admin, Room owner, Staff, Pitika, IT Lead, IT Staff."""
    roles = [RoleOut.model_validate(role) for role in role_service.list_roles(session)]
    return ItemList[RoleOut](items=roles, total=len(roles))


@router.patch("/{role_id}", response_model=RoleOut, summary="Rename a role")
def update_role(
    role_id: IdPath, body: RoleUpdate, current: AdminUser, session: DbSession
) -> RoleOut:
    """Only `name_en` and `name_kh` can change; `code` and `is_active` never do."""
    changes = body.model_dump(exclude_unset=True)
    return RoleOut.model_validate(role_service.update_role(session, role_id, changes))
