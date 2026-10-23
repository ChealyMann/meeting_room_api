from app.schemas.common import RequestModel, ResponseModel, SortOrder, Text, UtcDateTime


class CategoryCreate(RequestModel):
    name_en: Text(100)
    name_kh: Text(100)
    sort_order: SortOrder = 0


class CategoryUpdate(RequestModel):
    """PATCH: the fields of CategoryCreate, all optional, plus is_active."""

    name_en: Text(100) = None
    name_kh: Text(100) = None
    sort_order: SortOrder = None
    is_active: bool = None


class CategoryOut(ResponseModel):
    id: int
    name_en: str
    name_kh: str
    sort_order: int
    is_active: bool
    created_at: UtcDateTime
    updated_at: UtcDateTime
