from app.models import Floor
from app.schemas.common import RefId, RequestModel, ResponseModel, SortOrder, Text, UtcDateTime
from app.schemas.refs import BuildingRef, NamedRef, ProvinceRef


class FloorCreate(RequestModel):
    building_id: RefId  # must exist and be active (R2)
    floor_label: Text(100)  # e.g. "3rd floor"; one language only
    sort_order: SortOrder = 0


class FloorUpdate(RequestModel):
    """PATCH: the fields of FloorCreate, all optional, plus is_active."""

    building_id: RefId = None
    floor_label: Text(100) = None
    sort_order: SortOrder = None
    is_active: bool = None


class FloorOut(ResponseModel):
    id: int
    building_id: int
    floor_label: str
    sort_order: int
    is_active: bool
    created_at: UtcDateTime
    updated_at: UtcDateTime


class FloorDetail(FloorOut):
    building: BuildingRef
    location: NamedRef
    province: ProvinceRef

    @classmethod
    def from_model(cls, floor: Floor) -> "FloorDetail":
        location = floor.building.location
        return cls(
            **FloorOut.model_validate(floor).model_dump(),
            building=BuildingRef.model_validate(floor.building),
            location=NamedRef.model_validate(location),
            province=ProvinceRef.from_code(location.province),
        )
