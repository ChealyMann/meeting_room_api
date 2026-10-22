from typing import Annotated

from fastapi import APIRouter, Depends

from app.routers.common import DbSession, IdPath, IdQuery, IsActiveQuery, PageParams, SearchQuery
from app.schemas.common import Page
from app.schemas.floor import FloorCreate, FloorDetail, FloorOut, FloorUpdate
from app.security import AdminUser, AnyUser
from app.services import floor as floor_service

router = APIRouter(prefix="/floors", tags=["Location"])


@router.get("", response_model=Page[FloorOut], summary="List floors")
def list_floors(
    current: AnyUser,
    session: DbSession,
    paging: Annotated[PageParams, Depends()],
    building_id: IdQuery = None,
    location_id: IdQuery = None,
    is_active: IsActiveQuery = None,
    search: SearchQuery = None,
) -> Page[FloorOut]:
    """Filter by building, office and status; search matches the floor label.
    Sorted by sort order, then label."""
    result = floor_service.list_floors(
        session, paging.page, paging.size, building_id, location_id, is_active, search
    )
    return Page[FloorOut].model_validate(result, from_attributes=True)


@router.get(
    "/{floor_id}",
    response_model=FloorDetail,
    summary="See one floor, with its building, office and province",
)
def get_floor(floor_id: IdPath, current: AnyUser, session: DbSession) -> FloorDetail:
    return FloorDetail.from_model(floor_service.get_floor(session, floor_id))


@router.post("", response_model=FloorDetail, status_code=201, summary="Create a floor")
def create_floor(body: FloorCreate, current: AdminUser, session: DbSession) -> FloorDetail:
    return FloorDetail.from_model(floor_service.create_floor(session, body.model_dump()))


@router.patch(
    "/{floor_id}",
    response_model=FloorDetail,
    summary="Change a floor, or turn it off or on",
)
def update_floor(
    floor_id: IdPath, body: FloorUpdate, current: AdminUser, session: DbSession
) -> FloorDetail:
    changes = body.model_dump(exclude_unset=True)
    return FloorDetail.from_model(floor_service.update_floor(session, floor_id, changes))
