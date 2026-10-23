from typing import Annotated

from fastapi import APIRouter, Depends

from app.routers.common import DbSession, IdPath, IsActiveQuery, PageParams, SearchQuery
from app.schemas.common import Page
from app.schemas.equipment import EquipmentCreate, EquipmentOut, EquipmentUpdate
from app.security import AdminUser, AnyUser
from app.services import equipment as equipment_service

router = APIRouter(prefix="/equipment", tags=["Equipment"])


@router.get("", response_model=Page[EquipmentOut], summary="List equipment")
def list_equipment(
    current: AnyUser,
    session: DbSession,
    paging: Annotated[PageParams, Depends()],
    is_active: IsActiveQuery = None,
    search: SearchQuery = None,
) -> Page[EquipmentOut]:
    """Filter by status; search matches the name. Sorted by sort order, then name."""
    result = equipment_service.list_equipment(session, paging.page, paging.size, is_active, search)
    return Page[EquipmentOut].model_validate(result, from_attributes=True)


@router.get("/{equipment_id}", response_model=EquipmentOut, summary="See one item")
def get_equipment(equipment_id: IdPath, current: AnyUser, session: DbSession) -> EquipmentOut:
    return EquipmentOut.model_validate(equipment_service.get_equipment(session, equipment_id))


@router.post("", response_model=EquipmentOut, status_code=201, summary="Add an item")
def create_equipment(body: EquipmentCreate, current: AdminUser, session: DbSession) -> EquipmentOut:
    return EquipmentOut.model_validate(
        equipment_service.create_equipment(session, body.model_dump())
    )


@router.patch(
    "/{equipment_id}", response_model=EquipmentOut, summary="Change an item, or turn it off or on"
)
def update_equipment(
    equipment_id: IdPath, body: EquipmentUpdate, current: AdminUser, session: DbSession
) -> EquipmentOut:
    changes = body.model_dump(exclude_unset=True)
    return EquipmentOut.model_validate(
        equipment_service.update_equipment(session, equipment_id, changes)
    )
