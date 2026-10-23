from app.schemas.common import RefId, RequestModel


class RoomEquipmentRequest(RequestModel):
    """PUT /rooms/{id}/equipment: the room's whole set. Repeats are saved once (R15)."""

    equipment_ids: list[RefId]
