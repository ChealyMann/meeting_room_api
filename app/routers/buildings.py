from typing import Annotated

from fastapi import APIRouter, Depends

from app.routers.common import DbSession, IdPath, IdQuery, IsActiveQuery, PageParams, SearchQuery
from app.schemas.building import BuildingCreate, BuildingDetail, BuildingOut, BuildingUpdate
from app.schemas.common import Page
from app.security import AdminUser, AnyUser
from app.services import building as building_service

router = APIRouter(prefix="/buildings", tags=["Location"])


@router.get("", response_model=Page[BuildingOut], summary="List buildings")
def list_buildings(
    current: AnyUser,
    session: DbSession,
    paging: Annotated[PageParams, Depends()],
    location_id: IdQuery = None,
    is_active: IsActiveQuery = None,
    search: SearchQuery = None,
) -> Page[BuildingOut]:
    """Filter by office and status; search matches English name, Khmer name and short name.
    Sorted by sort order, then English name."""
    result = building_service.list_buildings(
        session, paging.page, paging.size, location_id, is_active, search
    )
    return Page[BuildingOut].model_validate(result, from_attributes=True)


@router.get(
    "/{building_id}",
    response_model=BuildingDetail,
    summary="See one building, with its office and province",
)
def get_building(building_id: IdPath, current: AnyUser, session: DbSession) -> BuildingDetail:
    return BuildingDetail.from_model(building_service.get_building(session, building_id))


@router.post("", response_model=BuildingDetail, status_code=201, summary="Create a building")
def create_building(body: BuildingCreate, current: AdminUser, session: DbSession) -> BuildingDetail:
    return BuildingDetail.from_model(building_service.create_building(session, body.model_dump()))


@router.patch(
    "/{building_id}",
    response_model=BuildingDetail,
    summary="Change a building, move it to another office, or turn it off or on",
)
def update_building(
    building_id: IdPath, body: BuildingUpdate, current: AdminUser, session: DbSession
) -> BuildingDetail:
    changes = body.model_dump(exclude_unset=True)
    building = building_service.update_building(session, building_id, changes)
    return BuildingDetail.from_model(building)
