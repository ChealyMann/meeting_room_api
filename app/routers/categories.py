from typing import Annotated

from fastapi import APIRouter, Depends

from app.routers.common import DbSession, IdPath, IsActiveQuery, PageParams, SearchQuery
from app.schemas.category import CategoryCreate, CategoryOut, CategoryUpdate
from app.schemas.common import Page
from app.security import AdminUser, AnyUser
from app.services import category as category_service

router = APIRouter(prefix="/categories", tags=["Room"])


@router.get("", response_model=Page[CategoryOut], summary="List room types")
def list_categories(
    current: AnyUser,
    session: DbSession,
    paging: Annotated[PageParams, Depends()],
    is_active: IsActiveQuery = None,
    search: SearchQuery = None,
) -> Page[CategoryOut]:
    """Filter by status; search matches English and Khmer name.
    Sorted by sort order, then English name."""
    result = category_service.list_categories(session, paging.page, paging.size, is_active, search)
    return Page[CategoryOut].model_validate(result, from_attributes=True)


@router.get("/{category_id}", response_model=CategoryOut, summary="See one room type")
def get_category(category_id: IdPath, current: AnyUser, session: DbSession) -> CategoryOut:
    return CategoryOut.model_validate(category_service.get_category(session, category_id))


@router.post("", response_model=CategoryOut, status_code=201, summary="Create a room type")
def create_category(body: CategoryCreate, current: AdminUser, session: DbSession) -> CategoryOut:
    category = category_service.create_category(session, body.model_dump())
    return CategoryOut.model_validate(category)


@router.patch(
    "/{category_id}",
    response_model=CategoryOut,
    summary="Change a room type, or turn it off or on",
)
def update_category(
    category_id: IdPath, body: CategoryUpdate, current: AdminUser, session: DbSession
) -> CategoryOut:
    changes = body.model_dump(exclude_unset=True)
    return CategoryOut.model_validate(
        category_service.update_category(session, category_id, changes)
    )
