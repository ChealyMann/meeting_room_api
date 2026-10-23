from app.schemas.common import RequestModel, ResponseModel, Text


class RoleUpdate(RequestModel):
    """PATCH: display names only. `code` and `is_active` never change (R17), so sending
    them is refused like any unknown field."""

    name_en: Text(100) = None
    name_kh: Text(100) = None


class RoleOut(ResponseModel):
    id: int
    code: str
    name_en: str
    name_kh: str
    is_active: bool
