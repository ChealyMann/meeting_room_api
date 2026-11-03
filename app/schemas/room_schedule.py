from datetime import date

from app.schemas.common import LocalTime, ResponseModel


class ScheduleItem(ResponseModel):
    """One blocking session of a room. A private booking the viewer may not see is masked:
    no booking id, reference code or requester, and a fixed title."""

    date: date
    start_time: LocalTime
    end_time: LocalTime
    booking_id: int | None
    reference_code: str | None
    title: str
    requester_name: str | None
    status: str
    is_masked: bool
