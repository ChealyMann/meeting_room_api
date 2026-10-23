from typing import Annotated

from fastapi import APIRouter, Depends

from app.routers.common import DbSession, IdPath, IdQuery, IsActiveQuery, PageParams, SearchQuery
from app.schemas.common import Page
from app.schemas.division import DivisionCreate, DivisionOut, DivisionUpdate
from app.security import AdminUser, AnyUser
from app.services import division as division_service

router = APIRouter(prefix="/divisions", tags=["Organisation"])


@router.get("", response_model=Page[DivisionOut], summary="List divisions")
def list_divisions(
    current: AnyUser,
    session: DbSession,
    paging: Annotated[PageParams, Depends()],
    department_id: IdQuery = None,
    is_active: IsActiveQuery = None,
    search: SearchQuery = None,
) -> Page[DivisionOut]:
    """Filter by department and status; search matches English name, Khmer name and
    short name. Sorted by sort order, then English name."""
    result = division_service.list_divisions(
        session, paging.page, paging.size, department_id, is_active, search
    )
    return Page[DivisionOut].model_validate(result, from_attributes=True)


@router.get("/{division_id}", response_model=DivisionOut, summary="See one division")
def get_division(division_id: IdPath, current: AnyUser, session: DbSession) -> DivisionOut:
    return DivisionOut.model_validate(division_service.get_division(session, division_id))


@router.post("", response_model=DivisionOut, status_code=201, summary="Create a division")
def create_division(body: DivisionCreate, current: AdminUser, session: DbSession) -> DivisionOut:
    return DivisionOut.model_validate(division_service.create_division(session, body.model_dump()))


@router.patch(
    "/{division_id}",
    response_model=DivisionOut,
    summary="Change a division, move it to another department, or turn it off or on",
)
def update_division(
    division_id: IdPath, body: DivisionUpdate, current: AdminUser, session: DbSession
) -> DivisionOut:
    changes = body.model_dump(exclude_unset=True)
    return DivisionOut.model_validate(
        division_service.update_division(session, division_id, changes)
    )
