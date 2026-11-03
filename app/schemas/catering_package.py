from app.schemas.common import (
    BookingText,
    OptionalBookingText,
    RefId,
    RequestModel,
    ResponseModel,
    SortOrder,
    UtcDateTime,
)


class CateringPackageCreate(RequestModel):
    name: BookingText(200, min_length=2)
    description: OptionalBookingText(1000) = None
    sort_order: SortOrder = 0
    is_active: bool = True


class CateringPackageUpdate(RequestModel):
    """PATCH: the fields of CateringPackageCreate, all optional, plus the required `version`."""

    version: RefId
    name: BookingText(200, min_length=2) = None
    description: OptionalBookingText(1000) = None
    sort_order: SortOrder = None
    is_active: bool = None


class CateringPackageOut(ResponseModel):
    id: int
    name: str
    description: str | None
    sort_order: int
    is_active: bool
    version: int
    created_at: UtcDateTime
    updated_at: UtcDateTime
