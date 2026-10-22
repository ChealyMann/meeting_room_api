"""Small references used inside other responses (spec section 10)."""

from app.constants.provinces import get_province
from app.schemas.common import ResponseModel


class ProvinceRef(ResponseModel):
    code: str
    name_en: str
    name_kh: str

    @classmethod
    def from_code(cls, code: str) -> "ProvinceRef":
        return cls.model_validate(get_province(code)._asdict())


class NamedRef(ResponseModel):
    id: int
    name_en: str
    name_kh: str


class BuildingRef(ResponseModel):
    id: int
    name_en: str
    name_kh: str
    short_name: str | None


class FloorRef(ResponseModel):
    id: int
    floor_label: str


class RoleRef(ResponseModel):
    code: str
    name_en: str
    name_kh: str
