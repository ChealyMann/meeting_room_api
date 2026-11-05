from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query

from app.constants.booking import ReviewDecision
from app.routers.common import AppSettings, DbSession, IdPath, IdQuery, PageParams, SearchQuery
from app.schemas.booking import BookingDetail, BookingListItem
from app.schemas.booking_review import ApproveBody, DecidedBookingItem, PitikaSummary, RejectBody
from app.schemas.common import Page
from app.security import PitikaUser
from app.services import booking_review, booking_view

router = APIRouter(prefix="/pitika/bookings", tags=["Pitika"])


@router.get("", response_model=Page[BookingListItem], summary="List bookings in my province")
def list_pitika_bookings(
    current: PitikaUser,
    session: DbSession,
    paging: Annotated[PageParams, Depends()],
    status: Annotated[
        str | None, Query(description="A display status, e.g. PENDING_PITIKA")
    ] = None,
    date_from: Annotated[
        date | None, Query(alias="from", description="Any session on or after this day")
    ] = None,
    date_to: Annotated[
        date | None, Query(alias="to", description="Any session on or before this day")
    ] = None,
    room_id: IdQuery = None,
    q: SearchQuery = None,
) -> Page[BookingListItem]:
    """Bookings of rooms in the province of your office, earliest first start first. `q`
    matches the title, the reference code or the requester's name. With no province you
    get an empty list."""
    result = booking_review.list_pitika_bookings(
        session, current, paging.page, paging.size, status, date_from, date_to, room_id, q
    )
    items = booking_view.build_booking_list_items(result["items"])
    return Page[BookingListItem](**{**result, "items": items})


@router.get("/decided", response_model=Page[DecidedBookingItem], summary="List bookings I decided")
def list_decided_bookings(
    current: PitikaUser,
    session: DbSession,
    paging: Annotated[PageParams, Depends()],
    decision: Annotated[Literal["APPROVED", "REJECTED"], Query(description="APPROVED or REJECTED")],
    date_from: Annotated[
        date | None, Query(alias="from", description="Any session on or after this day")
    ] = None,
    date_to: Annotated[
        date | None, Query(alias="to", description="Any session on or before this day")
    ] = None,
    room_id: IdQuery = None,
    q: SearchQuery = None,
) -> Page[DecidedBookingItem]:
    """Bookings you approved or rejected (`decision`), newest decision first, in rooms of
    your current province. Each has `decided_at` and `decision_note` (your notes on an
    approval, your reason on a rejection). Decisions the Admin made as a backup are not
    listed. `q` matches the title, the reference code or the requester's name."""
    result = booking_review.list_pitika_decided(
        session,
        current,
        paging.page,
        paging.size,
        ReviewDecision(decision),
        date_from,
        date_to,
        room_id,
        q,
    )
    items = booking_view.build_decided_items(result["items"], current.id)
    return Page[DecidedBookingItem](**{**result, "items": items})


@router.get("/summary", response_model=PitikaSummary, summary="See my day in numbers")
def pitika_summary(current: PitikaUser, session: DbSession) -> PitikaSummary:
    """`waiting`: bookings in your province waiting for Pitika now. `approved_today` and
    `rejected_today`: your own decisions today (Phnom Penh day; Admin backups not counted).
    With no province, all are 0."""
    return PitikaSummary(**booking_review.pitika_summary(session, current))


@router.post("/{booking_id}/approve", response_model=BookingDetail, summary="Approve a booking")
def approve_booking(
    booking_id: IdPath,
    body: ApproveBody,
    current: PitikaUser,
    session: DbSession,
    settings: AppSettings,
) -> BookingDetail:
    """T3, T4, T5. The booking must wait for Pitika (409 INVALID_TRANSITION otherwise) and
    its first session must not have started (409 TIME_PASSED). The notes go to the review and
    to the food order. A private-room booking goes on to the room owner; one with IT goes to
    IT setup; any other is confirmed with a door pass."""
    booking = booking_review.pitika_approve(session, current, booking_id, body.notes, body.version)
    return booking_view.build_booking_detail(session, booking, settings)


@router.post("/{booking_id}/reject", response_model=BookingDetail, summary="Reject a booking")
def reject_booking(
    booking_id: IdPath,
    body: RejectBody,
    current: PitikaUser,
    session: DbSession,
    settings: AppSettings,
) -> BookingDetail:
    """T6. The reason (5 to 1000 characters) is shown to the booker. Allowed even after the
    meeting started."""
    booking = booking_review.pitika_reject(session, current, booking_id, body.reason, body.version)
    return booking_view.build_booking_detail(session, booking, settings)
