from app.schemas.common import (
    OptionalText,
    RequestModel,
    ResponseModel,
    SortOrder,
    Text,
    UtcDateTime,
)


class EquipmentCreate(RequestModel):
    name: Text(200)  # one language, not bilingual
    icon: OptionalText(1000) = None  # icon name or URL chosen by the client app
    sort_order: SortOrder = 0


class EquipmentUpdate(RequestModel):
    """PATCH: the fields of EquipmentCreate, all optional, plus is_active."""

    name: Text(200) = None
    icon: OptionalText(1000) = None
    sort_order: SortOrder = None
    is_active: bool = None


class EquipmentOut(ResponseModel):
    id: int
    name: str
    icon: str | None
    sort_order: int
    is_active: bool
    created_at: UtcDateTime
    updated_at: UtcDateTime
