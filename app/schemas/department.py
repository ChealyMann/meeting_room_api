from app.schemas.common import (
    OptionalRefId,
    RefId,
    RequestModel,
    ResponseModel,
    SortOrder,
    Text,
    UtcDateTime,
)
from app.schemas.refs import NamedRef


class DepartmentCreate(RequestModel):
    location_id: RefId  # must exist and be active (R2)
    name_en: Text(100)
    name_kh: Text(100)
    sort_order: SortOrder = 0
    head_user_id: OptionalRefId = None  # who signs the request slip box


class DepartmentUpdate(RequestModel):
    """PATCH: the fields of DepartmentCreate, all optional, plus is_active.
    Changing location_id changes the province of every user in its divisions."""

    location_id: RefId = None
    name_en: Text(100) = None
    name_kh: Text(100) = None
    sort_order: SortOrder = None
    head_user_id: OptionalRefId = None
    is_active: bool = None


class DepartmentOut(ResponseModel):
    id: int
    location_id: int
    name_en: str
    name_kh: str
    sort_order: int
    is_active: bool
    head: NamedRef | None
    created_at: UtcDateTime
    updated_at: UtcDateTime
