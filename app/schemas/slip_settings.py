from app.schemas.common import OptionalRefId, RequestModel, ResponseModel, Text, UtcDateTime
from app.schemas.refs import NamedRef


class SlipSettingsUpdate(RequestModel):
    """PUT /slip-settings: both fields, every time."""

    director_user_id: OptionalRefId  # null: nobody signs the director's box
    address_kh: Text(500)


class SlipSettingsOut(ResponseModel):
    director: NamedRef | None
    address_kh: str
    updated_at: UtcDateTime
