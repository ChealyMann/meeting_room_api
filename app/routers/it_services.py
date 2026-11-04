from typing import Annotated

from fastapi import APIRouter, Depends

from app.routers.common import DbSession, IdPath, IsActiveQuery, PageParams, SearchQuery
from app.schemas.common import Page
from app.schemas.it_service import ITServiceCreate, ITServiceOut, ITServiceUpdate
from app.security import AdminUser, AnyUser
from app.services import it_service as it_service_service

router = APIRouter(prefix="/it-services", tags=["IT services"])


@router.get("", response_model=Page[ITServiceOut], summary="List IT services")
def list_it_services(
    current: AnyUser,
    session: DbSession,
    paging: Annotated[PageParams, Depends()],
    is_active: IsActiveQuery = None,
    search: SearchQuery = None,
) -> Page[ITServiceOut]:
    """Admin can filter by status; everyone else sees active services only."""
    result = it_service_service.list_it_services(
        session, current, paging.page, paging.size, is_active, search
    )
    return Page[ITServiceOut].model_validate(result, from_attributes=True)


@router.post("", response_model=ITServiceOut, status_code=201, summary="Add an IT service")
def create_it_service(
    body: ITServiceCreate, current: AdminUser, session: DbSession
) -> ITServiceOut:
    return ITServiceOut.model_validate(
        it_service_service.create_it_service(session, body.model_dump())
    )


@router.patch(
    "/{service_id}",
    response_model=ITServiceOut,
    summary="Change an IT service, or turn it off or on",
)
def update_it_service(
    service_id: IdPath, body: ITServiceUpdate, current: AdminUser, session: DbSession
) -> ITServiceOut:
    """Send the `version` you read. If someone saved first, this returns 409 STALE_VERSION."""
    changes = body.model_dump(exclude_unset=True)
    return ITServiceOut.model_validate(
        it_service_service.update_it_service(session, service_id, changes)
    )
