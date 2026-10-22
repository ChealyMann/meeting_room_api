from app.models import Building
from app.schemas.common import (
    OptionalText,
    RefId,
    RequestModel,
    ResponseModel,
    SortOrder,
    Text,
    UtcDateTime,
)
from app.schemas.refs import NamedRef, ProvinceRef


class BuildingCreate(RequestModel):
    location_id: RefId  # must exist and be active (R2)
    name_en: Text(100)
    name_kh: Text(100)
    short_name: OptionalText(20) = None
    sort_order: SortOrder = 0


class BuildingUpdate(RequestModel):
    """PATCH: the fields of BuildingCreate, all optional, plus is_active.
    Changing location_id moves the building with its floors and rooms."""

    location_id: RefId = None
    name_en: Text(100) = None
    name_kh: Text(100) = None
    short_name: OptionalText(20) = None
    sort_order: SortOrder = None
    is_active: bool = None


class BuildingOut(ResponseModel):
    id: int
    location_id: int
    name_en: str
    name_kh: str
    short_name: str | None
    sort_order: int
    is_active: bool
    created_at: UtcDateTime
    updated_at: UtcDateTime


class BuildingDetail(BuildingOut):
    location: NamedRef
    province: ProvinceRef

    @classmethod
    def from_model(cls, building: Building) -> "BuildingDetail":
        return cls(
            **BuildingOut.model_validate(building).model_dump(),
            location=NamedRef.model_validate(building.location),
            province=ProvinceRef.from_code(building.location.province),
        )
