from typing import Annotated

from fastapi import APIRouter, Depends

from app.routers.common import DbSession, IdPath, IdQuery, IsActiveQuery, PageParams, SearchQuery
from app.schemas.common import Page
from app.schemas.department import DepartmentCreate, DepartmentOut, DepartmentUpdate
from app.security import AdminUser, AnyUser
from app.services import department as department_service

router = APIRouter(prefix="/departments", tags=["Organisation"])


@router.get("", response_model=Page[DepartmentOut], summary="List departments")
def list_departments(
    current: AnyUser,
    session: DbSession,
    paging: Annotated[PageParams, Depends()],
    location_id: IdQuery = None,
    is_active: IsActiveQuery = None,
    search: SearchQuery = None,
) -> Page[DepartmentOut]:
    """Filter by office and status; search matches English and Khmer name.
    Sorted by sort order, then English name."""
    result = department_service.list_departments(
        session, paging.page, paging.size, location_id, is_active, search
    )
    return Page[DepartmentOut].model_validate(result, from_attributes=True)


@router.get("/{department_id}", response_model=DepartmentOut, summary="See one department")
def get_department(department_id: IdPath, current: AnyUser, session: DbSession) -> DepartmentOut:
    return DepartmentOut.model_validate(department_service.get_department(session, department_id))


@router.post("", response_model=DepartmentOut, status_code=201, summary="Create a department")
def create_department(
    body: DepartmentCreate, current: AdminUser, session: DbSession
) -> DepartmentOut:
    department = department_service.create_department(session, body.model_dump())
    return DepartmentOut.model_validate(department)


@router.patch(
    "/{department_id}",
    response_model=DepartmentOut,
    summary="Change a department, move it to another office, or turn it off or on",
)
def update_department(
    department_id: IdPath, body: DepartmentUpdate, current: AdminUser, session: DbSession
) -> DepartmentOut:
    changes = body.model_dump(exclude_unset=True)
    department = department_service.update_department(session, department_id, changes)
    return DepartmentOut.model_validate(department)
