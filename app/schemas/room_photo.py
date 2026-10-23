from app.schemas.common import RefId, RequestModel, ResponseModel, UtcDateTime


class PhotoOrderRequest(RequestModel):
    """PUT /rooms/{id}/photos/order: every photo of the room, each once, in the new order."""

    photo_ids: list[RefId]


class PhotoOut(ResponseModel):
    id: int
    room_id: int
    url: str
    thumbnail_url: str
    sort_order: int
    created_at: UtcDateTime
    updated_at: UtcDateTime


class CoverPhoto(ResponseModel):
    """The photo with the lowest sort_order."""

    url: str
    thumbnail_url: str
