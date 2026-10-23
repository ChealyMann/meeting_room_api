from app.schemas.common import RequestModel, ResponseModel, SortOrder, Text, UtcDateTime


class PositionCreate(RequestModel):
    name_en: Text(100)
    name_kh: Text(100)
    sort_order: SortOrder = 0


class PositionUpdate(RequestModel):
    """PATCH: the fields of PositionCreate, all optional, plus is_active."""

    name_en: Text(100) = None
    name_kh: Text(100) = None
    sort_order: SortOrder = None
    is_active: bool = None


class PositionOut(ResponseModel):
    id: int
    name_en: str
    name_kh: str
    sort_order: int
    is_active: bool
    created_at: UtcDateTime
    updated_at: UtcDateTime
