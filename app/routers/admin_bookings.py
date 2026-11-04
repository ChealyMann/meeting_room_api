from fastapi import APIRouter

from app.routers.common import AppSettings, DbSession, IdPath
from app.schemas.booking import BookingDetail, CancelBody
from app.schemas.booking_admin import AdminActionsOut, AdminRejectBody
from app.schemas.booking_review import ApproveBody
from app.security import AdminUser
from app.services import booking_admin, booking_view

router = APIRouter(prefix="/admin/bookings", tags=["Admin bookings"])


@router.get(
    "/{booking_id}/actions", response_model=AdminActionsOut, summary="What the Admin may do"
)
def get_actions(booking_id: IdPath, current: AdminUser, session: DbSession) -> AdminActionsOut:
    """Cancel while the booking is open; approve or reject as a backup reviewer: for Pitika only
    when the province has no active Pitika, for the room owner always (B-33, B-34)."""
    return AdminActionsOut(**booking_admin.get_actions(session, booking_id))


@router.post(
    "/{booking_id}/cancel", response_model=BookingDetail, summary="Cancel a booking (Admin)"
)
def cancel_booking(
    booking_id: IdPath,
    body: CancelBody,
    current: AdminUser,
    session: DbSession,
    settings: AppSettings,
) -> BookingDetail:
    """B-33. Any booking that is not final and has not ended; the reason is optional."""
    booking = booking_admin.admin_cancel(session, current, booking_id, body.reason, body.version)
    return booking_view.build_booking_detail(session, booking, settings)


@router.post(
    "/{booking_id}/approve", response_model=BookingDetail, summary="Approve as backup (Admin)"
)
def approve_booking(
    booking_id: IdPath,
    body: ApproveBody,
    current: AdminUser,
    session: DbSession,
    settings: AppSettings,
) -> BookingDetail:
    """B-34. 403 when the province has an active Pitika; 409 TIME_PASSED after the first
    session started; 409 INVALID_TRANSITION unless the booking waits for Pitika or the owner."""
    booking = booking_admin.admin_approve(session, current, booking_id, body.notes, body.version)
    return booking_view.build_booking_detail(session, booking, settings)


@router.post(
    "/{booking_id}/reject", response_model=BookingDetail, summary="Reject as backup (Admin)"
)
def reject_booking(
    booking_id: IdPath,
    body: AdminRejectBody,
    current: AdminUser,
    session: DbSession,
    settings: AppSettings,
) -> BookingDetail:
    """B-34. Allowed while the booking waits for Pitika (no active Pitika) or the owner; the
    reason is optional ("Rejected by the Admin." when none)."""
    booking = booking_admin.admin_reject(session, current, booking_id, body.reason, body.version)
    return booking_view.build_booking_detail(session, booking, settings)
