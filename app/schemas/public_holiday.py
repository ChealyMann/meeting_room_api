from datetime import date

from app.schemas.common import (
    BookingText,
    OptionalBookingText,
    RequestModel,
    ResponseModel,
    UtcDateTime,
)


class PublicHolidayCreate(RequestModel):
    holiday_date: date
    name_km: BookingText(255)
    name_en: OptionalBookingText(255) = None
    remarks: OptionalBookingText(1000) = None


class PublicHolidayUpdate(RequestModel):
    """PATCH: the fields of PublicHolidayCreate, all optional."""

    holiday_date: date = None
    name_km: BookingText(255) = None
    name_en: OptionalBookingText(255) = None
    remarks: OptionalBookingText(1000) = None


class PublicHolidayOut(ResponseModel):
    id: int
    holiday_date: date
    name_km: str
    name_en: str | None
    remarks: str | None
    created_at: UtcDateTime
    updated_at: UtcDateTime
