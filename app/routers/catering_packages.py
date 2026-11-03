from typing import Annotated

from fastapi import APIRouter, Depends

from app.routers.common import DbSession, IdPath, IsActiveQuery, PageParams, SearchQuery
from app.schemas.catering_package import (
    CateringPackageCreate,
    CateringPackageOut,
    CateringPackageUpdate,
)
from app.schemas.common import Page
from app.security import AdminUser, AnyUser
from app.services import catering_package as package_service

router = APIRouter(prefix="/catering-packages", tags=["Catering packages"])


@router.get("", response_model=Page[CateringPackageOut], summary="List catering packages")
def list_catering_packages(
    current: AnyUser,
    session: DbSession,
    paging: Annotated[PageParams, Depends()],
    is_active: IsActiveQuery = None,
    search: SearchQuery = None,
) -> Page[CateringPackageOut]:
    """Admin can filter by status; everyone else sees active packages only."""
    result = package_service.list_catering_packages(
        session, current, paging.page, paging.size, is_active, search
    )
    return Page[CateringPackageOut].model_validate(result, from_attributes=True)


@router.post("", response_model=CateringPackageOut, status_code=201, summary="Add a package")
def create_catering_package(
    body: CateringPackageCreate, current: AdminUser, session: DbSession
) -> CateringPackageOut:
    return CateringPackageOut.model_validate(
        package_service.create_catering_package(session, body.model_dump())
    )


@router.patch(
    "/{package_id}",
    response_model=CateringPackageOut,
    summary="Change a package, or turn it off or on",
)
def update_catering_package(
    package_id: IdPath, body: CateringPackageUpdate, current: AdminUser, session: DbSession
) -> CateringPackageOut:
    """Send the `version` you read. If someone saved first, this returns 409 STALE_VERSION."""
    changes = body.model_dump(exclude_unset=True)
    return CateringPackageOut.model_validate(
        package_service.update_catering_package(session, package_id, changes)
    )
