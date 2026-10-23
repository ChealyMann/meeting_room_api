from app.schemas.common import (
    IntRange,
    LocalTime,
    OptionalRefId,
    OptionalText,
    RefId,
    RequestModel,
    ResponseModel,
    Text,
    UtcDateTime,
)
from app.schemas.equipment import EquipmentOut
from app.schemas.refs import BuildingRef, FloorRef, NamedRef, ProvinceRef
from app.schemas.room_photo import CoverPhoto, PhotoOut

Capacity = IntRange(1, 10000)
SizeSqm = IntRange(1, 100000)

# Fields a room owner may change on their own rooms (R8). Everything else is Admin only.
OWNER_FIELDS = frozenset(
    {
        "name_en",
        "name_kh",
        "short_desc",
        "description",
        "capacity",
        "size_sqm",
        "start_time",
        "end_time",
        "door_code",
        "category_id",
        "is_private",
    }
)


class RoomCreate(RequestModel):
    name_en: Text(100)  # unique per floor (R4)
    name_kh: Text(100)
    floor_id: RefId  # must exist and be active (R2)
    category_id: RefId  # must exist and be active (R2)
    capacity: Capacity
    size_sqm: SizeSqm | None = None
    start_time: LocalTime  # before end_time (R13)
    end_time: LocalTime
    short_desc: OptionalText(200) = None
    description: OptionalText(1000) = None
    door_code: OptionalText(50) = None  # write-only: never returned here
    room_owner_id: OptionalRefId = None  # null = no-owner room; else R7
    is_private: bool = False  # a label only; independent of the owner


class RoomUpdate(RequestModel):
    """PATCH: the fields of RoomCreate, all optional, plus is_active. A room owner may send
    only OWNER_FIELDS."""

    name_en: Text(100) = None
    name_kh: Text(100) = None
    floor_id: RefId = None
    category_id: RefId = None
    capacity: Capacity = None
    size_sqm: SizeSqm | None = None
    start_time: LocalTime = None
    end_time: LocalTime = None
    short_desc: OptionalText(200) = None
    description: OptionalText(1000) = None
    door_code: OptionalText(50) = None
    room_owner_id: OptionalRefId = None
    is_private: bool = None
    is_active: bool = None


class RoomListItem(ResponseModel):
    """Never contains the door code."""

    id: int
    name_en: str
    name_kh: str
    short_desc: str | None
    capacity: int
    size_sqm: int | None
    start_time: LocalTime
    end_time: LocalTime
    category: NamedRef
    floor: FloorRef
    building: BuildingRef
    location: NamedRef
    province: ProvinceRef
    owner: NamedRef | None
    cover_photo: CoverPhoto | None
    is_active: bool
    is_bookable: bool  # computed (R12), never stored
    is_private: bool  # a label only


class RoomDetail(RoomListItem):
    description: str | None
    photos: list[PhotoOut]
    equipment: list[EquipmentOut]
    created_at: UtcDateTime
    updated_at: UtcDateTime


class DoorCode(ResponseModel):
    room_id: int
    door_code: str | None
