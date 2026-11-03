from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.routers.common import AppSettings, DbSession, IdPath, IdQuery, PageParams, SearchQuery
from app.schemas.booking import BookingDetail, BookingListItem
from app.schemas.booking_review import ApproveBody, RejectBody
from app.schemas.common import Page
from app.security import RoomOwnerUser
from app.services import booking_review, booking_view

router = APIRouter(prefix="/owner/bookings", tags=["Room owner"])


@router.get("", response_model=Page[BookingListItem], summary="List bookings in my private rooms")
def list_owner_bookings(
    current: RoomOwnerUser,
    session: DbSession,
    paging: Annotated[PageParams, Depends()],
    status: Annotated[str | None, Query(description="A display status, e.g. PENDING_OWNER")] = None,
    room_id: IdQuery = None,
    q: SearchQuery = None,
) -> Page[BookingListItem]:
    """Bookings in the private rooms you own now, earliest first start first. When a room
    gets a new owner, its bookings move to the new owner's list. `q` matches the title, the
    reference code or the requester's name."""
    result = booking_review.list_owner_bookings(
        session, current, paging.page, paging.size, status, room_id, q
    )
    items = booking_view.build_booking_list_items(session, result["items"])
    return Page[BookingListItem](**{**result, "items": items})


@router.post("/{booking_id}/approve", response_model=BookingDetail, summary="Approve a booking")
def approve_booking(
    booking_id: IdPath,
    body: ApproveBody,
    current: RoomOwnerUser,
    session: DbSession,
    settings: AppSettings,
) -> BookingDetail:
    """T7, T8. The booking must wait for the room owner (409 INVALID_TRANSITION otherwise)
    and its first session must not have started (409 TIME_PASSED). A booking with IT goes to
    IT setup; any other is confirmed with a door pass."""
    booking = booking_review.owner_approve(session, current, booking_id, body.notes, body.version)
    return booking_view.build_booking_detail(session, booking, settings)


@router.post("/{booking_id}/reject", response_model=BookingDetail, summary="Reject a booking")
def reject_booking(
    booking_id: IdPath,
    body: RejectBody,
    current: RoomOwnerUser,
    session: DbSession,
    settings: AppSettings,
) -> BookingDetail:
    """T9. The reason (5 to 1000 characters) is shown to the booker. Allowed even after the
    meeting started."""
    booking = booking_review.owner_reject(session, current, booking_id, body.reason, body.version)
    return booking_view.build_booking_detail(session, booking, settings)
