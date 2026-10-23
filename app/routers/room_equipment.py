from fastapi import APIRouter

from app.routers.common import DbSession, IdPath
from app.schemas.common import ItemList
from app.schemas.equipment import EquipmentOut
from app.schemas.room_equipment import RoomEquipmentRequest
from app.security import AdminOrOwnerUser, AnyUser
from app.services import room_equipment as room_equipment_service

router = APIRouter(prefix="/rooms/{room_id}/equipment", tags=["Room"])


def _equipment_list(items) -> ItemList[EquipmentOut]:
    out = [EquipmentOut.model_validate(item) for item in items]
    return ItemList[EquipmentOut](items=out, total=len(out))


@router.get("", response_model=ItemList[EquipmentOut], summary="List a room's equipment")
def list_room_equipment(
    room_id: IdPath, current: AnyUser, session: DbSession
) -> ItemList[EquipmentOut]:
    return _equipment_list(room_equipment_service.list_room_equipment(session, room_id))


@router.put("", response_model=ItemList[EquipmentOut], summary="Replace a room's equipment")
def set_room_equipment(
    room_id: IdPath, body: RoomEquipmentRequest, current: AdminOrOwnerUser, session: DbSession
) -> ItemList[EquipmentOut]:
    """Sends the whole set: repeats are saved once, `[]` removes everything."""
    items = room_equipment_service.set_room_equipment(session, room_id, body.equipment_ids, current)
    return _equipment_list(items)
