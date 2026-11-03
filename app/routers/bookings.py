from fastapi import APIRouter

from app.routers.common import AppSettings, DbSession
from app.schemas.booking import BookingCheck, BookingCheckResult
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
