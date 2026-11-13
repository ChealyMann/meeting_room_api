from app.schemas.common import (
    OptionalRefId,
    OptionalText,
    RefId,
    RequestModel,
    ResponseModel,
    SortOrder,
    Text,
    UtcDateTime,
)
from app.schemas.refs import NamedRef


class DivisionCreate(RequestModel):
    department_id: RefId  # must exist and be active (R2)
    name_en: Text(100)
    name_kh: Text(100)
    short_name: OptionalText(20) = None
    sort_order: SortOrder = 0
    head_user_id: OptionalRefId = None  # who signs the request slip box


class DivisionUpdate(RequestModel):
    """PATCH: the fields of DivisionCreate, all optional, plus is_active."""

    department_id: RefId = None
    name_en: Text(100) = None
    name_kh: Text(100) = None
    short_name: OptionalText(20) = None
    sort_order: SortOrder = None
    head_user_id: OptionalRefId = None
    is_active: bool = None


class DivisionOut(ResponseModel):
    id: int
    department_id: int
    name_en: str
    name_kh: str
    short_name: str | None
    sort_order: int
    is_active: bool
    head: NamedRef | None
    created_at: UtcDateTime
    updated_at: UtcDateTime
