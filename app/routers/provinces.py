from fastapi import APIRouter

from app.constants.provinces import PROVINCES
from app.schemas.common import ItemList
from app.schemas.refs import ProvinceRef
from app.security import AnyUser

router = APIRouter(prefix="/provinces", tags=["Location"])


@router.get(
    "",
    response_model=ItemList[ProvinceRef],
    summary="List the 25 provinces (fixed list, not paged)",
)
def list_provinces(current: AnyUser) -> ItemList[ProvinceRef]:
    items = [ProvinceRef.model_validate(province._asdict()) for province in PROVINCES]
    return ItemList[ProvinceRef](items=items, total=len(items))
