from typing import Annotated

from fastapi import APIRouter, Depends

from app.routers.common import (
    DbSession,
    IdPath,
    IsActiveQuery,
    PageParams,
    ProvinceQuery,
    SearchQuery,
)
from app.schemas.common import Page
from app.schemas.location import LocationCreate, LocationOut, LocationUpdate
from app.security import AdminUser, AnyUser
from app.services import location as location_service

router = APIRouter(prefix="/locations", tags=["Location"])


def _page(result: dict) -> Page[LocationOut]:
    items = [LocationOut.from_model(location) for location in result["items"]]
    return Page[LocationOut](**{**result, "items": items})


@router.get("", response_model=Page[LocationOut], summary="List offices")
def list_locations(
    current: AnyUser,
    session: DbSession,
    paging: Annotated[PageParams, Depends()],
    province: ProvinceQuery = None,
    is_active: IsActiveQuery = None,
    search: SearchQuery = None,
) -> Page[LocationOut]:
    """Filter by province code and status; search matches English name, Khmer name and
    address. Sorted by English name."""
    result = location_service.list_locations(
        session, paging.page, paging.size, province, is_active, search
    )
    return _page(result)


@router.get("/{location_id}", response_model=LocationOut, summary="See one office")
def get_location(location_id: IdPath, current: AnyUser, session: DbSession) -> LocationOut:
    return LocationOut.from_model(location_service.get_location(session, location_id))


@router.post("", response_model=LocationOut, status_code=201, summary="Create an office")
def create_location(body: LocationCreate, current: AdminUser, session: DbSession) -> LocationOut:
    location = location_service.create_location(session, body.model_dump())
    return LocationOut.from_model(location)


@router.patch(
    "/{location_id}",
    response_model=LocationOut,
    summary="Change an office, or turn it off or on",
)
def update_location(
    location_id: IdPath, body: LocationUpdate, current: AdminUser, session: DbSession
) -> LocationOut:
    changes = body.model_dump(exclude_unset=True)
    return LocationOut.from_model(location_service.update_location(session, location_id, changes))
