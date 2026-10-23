from typing import Annotated

from fastapi import APIRouter, Depends

from app.routers.common import DbSession, IdPath, IsActiveQuery, PageParams, SearchQuery
from app.schemas.common import Page
from app.schemas.position import PositionCreate, PositionOut, PositionUpdate
from app.security import AdminUser, AnyUser
from app.services import position as position_service

router = APIRouter(prefix="/positions", tags=["Organisation"])


@router.get("", response_model=Page[PositionOut], summary="List job positions")
def list_positions(
    current: AnyUser,
    session: DbSession,
    paging: Annotated[PageParams, Depends()],
    is_active: IsActiveQuery = None,
    search: SearchQuery = None,
) -> Page[PositionOut]:
    """Filter by status; search matches English and Khmer name.
    Sorted by sort order, then English name."""
    result = position_service.list_positions(session, paging.page, paging.size, is_active, search)
    return Page[PositionOut].model_validate(result, from_attributes=True)


@router.get("/{position_id}", response_model=PositionOut, summary="See one job position")
def get_position(position_id: IdPath, current: AnyUser, session: DbSession) -> PositionOut:
    return PositionOut.model_validate(position_service.get_position(session, position_id))


@router.post("", response_model=PositionOut, status_code=201, summary="Create a job position")
def create_position(body: PositionCreate, current: AdminUser, session: DbSession) -> PositionOut:
    return PositionOut.model_validate(position_service.create_position(session, body.model_dump()))


@router.patch(
    "/{position_id}",
    response_model=PositionOut,
    summary="Change a job position, or turn it off or on",
)
def update_position(
    position_id: IdPath, body: PositionUpdate, current: AdminUser, session: DbSession
) -> PositionOut:
    changes = body.model_dump(exclude_unset=True)
    return PositionOut.model_validate(
        position_service.update_position(session, position_id, changes)
    )
