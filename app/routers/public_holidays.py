from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.routers.common import DbSession, IdPath, PageParams
from app.schemas.common import Page
from app.schemas.public_holiday import PublicHolidayCreate, PublicHolidayOut, PublicHolidayUpdate
from app.security import AdminUser, AnyUser
from app.services import public_holiday as holiday_service

router = APIRouter(prefix="/public-holidays", tags=["Public holidays"])

YearQuery = Annotated[int | None, Query(ge=1900, le=2200)]


@router.get("", response_model=Page[PublicHolidayOut], summary="List public holidays")
def list_holidays(
    current: AnyUser,
    session: DbSession,
    paging: Annotated[PageParams, Depends()],
    year: YearQuery = None,
) -> Page[PublicHolidayOut]:
    """Sorted by date. `year` keeps one year only."""
    result = holiday_service.list_holidays(session, paging.page, paging.size, year)
    return Page[PublicHolidayOut].model_validate(result, from_attributes=True)


@router.post("", response_model=PublicHolidayOut, status_code=201, summary="Add a holiday")
def create_holiday(
    body: PublicHolidayCreate, current: AdminUser, session: DbSession
) -> PublicHolidayOut:
    return PublicHolidayOut.model_validate(
        holiday_service.create_holiday(session, body.model_dump())
    )


@router.patch("/{holiday_id}", response_model=PublicHolidayOut, summary="Change a holiday")
def update_holiday(
    holiday_id: IdPath, body: PublicHolidayUpdate, current: AdminUser, session: DbSession
) -> PublicHolidayOut:
    changes = body.model_dump(exclude_unset=True)
    return PublicHolidayOut.model_validate(
        holiday_service.update_holiday(session, holiday_id, changes)
    )


@router.delete("/{holiday_id}", status_code=204, summary="Delete a holiday")
def delete_holiday(holiday_id: IdPath, current: AdminUser, session: DbSession) -> None:
    holiday_service.delete_holiday(session, holiday_id)
