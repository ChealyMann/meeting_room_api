from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.routers.common import AppSettings, DbSession, IdPath, PageParams, SearchQuery
from app.schemas.booking import (
    BookingCheck,
    BookingCheckResult,
    BookingCreate,
    BookingDetail,
    BookingListItem,
    BookingSaved,
)
from app.schemas.common import Page
from app.security import AnyUser
from app.services import booking as booking_service

router = APIRouter(prefix="/bookings", tags=["Booking"])


@router.post("/check", response_model=BookingCheckResult, summary="Check a booking before sending")
def check_booking(
    body: BookingCheck, current: AnyUser, session: DbSession, settings: AppSettings
) -> BookingCheckResult:
    """Gives the route, the steps and the first problem. A rule problem is part of the
    answer (status 200), not an error. Saves nothing."""
    return booking_service.check_booking(session, current, body, settings)


@router.post("", response_model=BookingSaved, status_code=201, summary="Send a booking")
def create_booking(
    body: BookingCreate, current: AnyUser, session: DbSession, settings: AppSettings
) -> BookingSaved:
    """T1, T2. The server picks the route. A booking of your own private room with no food
    and no IT (R3) is confirmed at once, with a door pass; every other booking waits for
    Pitika. Warnings (public holiday, more attendees than seats) do not stop it."""
    booking, warnings = booking_service.create_booking(session, current, body, settings)
    detail = booking_service.build_booking_detail(session, booking, settings)
    return BookingSaved(**dict(detail), warnings=warnings)


@router.get("/mine", response_model=Page[BookingListItem], summary="List my bookings")
def list_my_bookings(
    current: AnyUser,
    session: DbSession,
    paging: Annotated[PageParams, Depends()],
    status: Annotated[
        str | None, Query(description="A display status, e.g. CONFIRMED or COMPLETED")
    ] = None,
    q: SearchQuery = None,
) -> Page[BookingListItem]:
    """Newest first. `q` matches the title or the reference code. CONFIRMED means confirmed
    and not yet ended; COMPLETED means confirmed and ended."""
    result = booking_service.list_my_bookings(session, current, paging.page, paging.size, status, q)
    items = booking_service.build_booking_list_items(session, result["items"])
    return Page[BookingListItem](**{**result, "items": items})


@router.get("/{booking_id}", response_model=BookingDetail, summary="See one booking")
def get_booking(
    booking_id: IdPath, current: AnyUser, session: DbSession, settings: AppSettings
) -> BookingDetail:
    """For the booker, Admin, the room owner, a Pitika of the room's province and the IT
    users of a forwarded ticket. Anyone else gets 404."""
    booking = booking_service.get_booking(session, current, booking_id)
    return booking_service.build_booking_detail(session, booking, settings)
