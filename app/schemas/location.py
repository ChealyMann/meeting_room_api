from app.models import Location
from app.schemas.common import (
    OptionalText,
    ProvinceCode,
    RequestModel,
    ResponseModel,
    Text,
    UtcDateTime,
)
from app.schemas.refs import ProvinceRef


class LocationCreate(RequestModel):
    name_en: Text(100)
    name_kh: Text(100)
    province: ProvinceCode
    description: OptionalText(1000) = None
    address: OptionalText(200) = None
    map_query: OptionalText(500) = None  # free text for a map search, e.g. coordinates


class LocationUpdate(RequestModel):
    """PATCH: the fields of LocationCreate, all optional, plus is_active."""

    name_en: Text(100) = None
    name_kh: Text(100) = None
    province: ProvinceCode = None
    description: OptionalText(1000) = None
    address: OptionalText(200) = None
    map_query: OptionalText(500) = None
    is_active: bool = None


class LocationOut(ResponseModel):
    id: int
    name_en: str
    name_kh: str
    description: str | None
    address: str | None
    province: ProvinceRef
    map_query: str | None
    is_active: bool
    created_at: UtcDateTime
    updated_at: UtcDateTime

    @classmethod
    def from_model(cls, location: Location) -> "LocationOut":
        return cls(
            id=location.id,
            name_en=location.name_en,
            name_kh=location.name_kh,
            description=location.description,
            address=location.address,
            province=ProvinceRef.from_code(location.province),
            map_query=location.map_query,
            is_active=location.is_active,
            created_at=location.created_at,
            updated_at=location.updated_at,
        )
