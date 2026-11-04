from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response

from app.routers.common import (
    AppSettings,
    DbSession,
    IdPath,
    IdQuery,
    PageParams,
    ProvinceQuery,
    SearchQuery,
)
from app.schemas.booking import (
    BookingCheck,
    BookingCheckResult,
    BookingCreate,
    BookingDetail,
    BookingListItem,
    BookingSaved,
    BookingUpdate,
    CancelBody,
    DoorPassOut,
)
from app.schemas.common import Page
from app.security import AdminUser, AnyUser
from app.services import booking as booking_service
from app.services import booking_review, booking_view
from app.services.booking_ics import build_ics
from app.services.clock import now_utc

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
    detail = booking_view.build_booking_detail(session, booking, settings)
    return BookingSaved(**dict(detail), warnings=warnings)


@router.get("", response_model=Page[BookingListItem], summary="List all bookings (Admin)")
def list_all_bookings(
    current: AdminUser,
    session: DbSession,
    paging: Annotated[PageParams, Depends()],
    status: Annotated[
        str | None, Query(description="A display status, e.g. PENDING_PITIKA or COMPLETED")
    ] = None,
    province: ProvinceQuery = None,
    date_from: Annotated[
        date | None, Query(alias="from", description="Any session on or after this day")
    ] = None,
    date_to: Annotated[
        date | None, Query(alias="to", description="Any session on or before this day")
    ] = None,
    room_id: IdQuery = None,
    q: SearchQuery = None,
) -> Page[BookingListItem]:
    """B-32. Bookings in every province, earliest first start first. `q` matches the title,
    the reference code or the booker's name. Read only: the Admin cannot approve, reject,
    cancel or edit."""
    result = booking_review.list_admin_bookings(
        session, paging.page, paging.size, status, province, date_from, date_to, room_id, q
    )
    items = booking_view.build_booking_list_items(result["items"])
    return Page[BookingListItem](**{**result, "items": items})


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
    items = booking_view.build_booking_list_items(result["items"])
    return Page[BookingListItem](**{**result, "items": items})


@router.get("/{booking_id}", response_model=BookingDetail, summary="See one booking")
def get_booking(
    booking_id: IdPath, current: AnyUser, session: DbSession, settings: AppSettings
) -> BookingDetail:
    """For the booker, Admin, the room owner, a Pitika of the room's province and the IT
    users of a forwarded ticket. Anyone else gets 404."""
    booking = booking_service.get_booking(session, current, booking_id)
    return booking_view.build_booking_detail(session, booking, settings)


@router.get("/{booking_id}/door-pass", response_model=DoorPassOut, summary="See the door pass")
def get_door_pass(
    booking_id: IdPath, current: AnyUser, session: DbSession, response: Response
) -> DoorPassOut:
    """For the booker, Admin, the room owner and a Pitika of the room's province, once the
    booking is CONFIRMED. Before that: 404. IT users get 403. Never cached (no-store)."""
    door_pass = booking_service.get_door_pass(session, current, booking_id)
    response.headers["Cache-Control"] = "no-store"
    return DoorPassOut(
        passcode=door_pass.passcode,
        expires_at=door_pass.expires_at,
        expired=now_utc() >= door_pass.expires_at,
    )


@router.get(
    "/{booking_id}/ics",
    response_class=Response,
    responses={200: {"content": {"text/calendar": {}}}},
    summary="Download the calendar file",
)
def get_booking_ics(booking_id: IdPath, current: AnyUser, session: DbSession) -> Response:
    """A calendar file with one event per session. Same visibility as the booking. It never
    holds the door pass."""
    booking = booking_service.get_booking(session, current, booking_id)
    return Response(
        content=build_ics(booking),
        media_type="text/calendar; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{booking.reference_code}.ics"'},
    )


@router.patch("/{booking_id}", response_model=BookingSaved, summary="Edit a booking a little")
def update_booking(
    booking_id: IdPath,
    body: BookingUpdate,
    current: AnyUser,
    session: DbSession,
    settings: AppSettings,
) -> BookingSaved:
    """T13. Only the booker, and only before the first session starts. You can change the
    title, type, purpose, attendees, participant emails, the food remarks and the IT
    requirements. The room, dates, times and the choice of packages or services cannot change
    (422 FIELD_NOT_EDITABLE): cancel and book again. The status does not change. A body with
    only `version` changes nothing."""
    booking, warnings = booking_service.update_booking(session, current, booking_id, body, settings)
    detail = booking_view.build_booking_detail(session, booking, settings)
    return BookingSaved(**dict(detail), warnings=warnings)


@router.post("/{booking_id}/cancel", response_model=BookingDetail, summary="Cancel a booking")
def cancel_booking(
    booking_id: IdPath,
    body: CancelBody,
    current: AnyUser,
    session: DbSession,
    settings: AppSettings,
) -> BookingDetail:
    """T12. Only the booker, while the booking is not final and its last session has not
    ended. The reason is optional (5 to 500 characters). The room is free again."""
    booking = booking_service.cancel_booking(
        session, current, booking_id, body.reason, body.version
    )
    return booking_view.build_booking_detail(session, booking, settings)
