"""Small references used inside other responses (spec section 10)."""

from app.schemas.common import ResponseModel


class ProvinceRef(ResponseModel):
    code: str
    name_en: str
    name_kh: str


class NamedRef(ResponseModel):
    id: int
    name_en: str
    name_kh: str


class RoleRef(ResponseModel):
    code: str
    name_en: str
    name_kh: str
