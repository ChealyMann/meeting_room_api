"""Where a room or a user is (spec section 5). The booking scope reuses these.

Room: floor -> building -> location -> province.
User: division -> department -> location -> province; no division means no province.
"""

from app.constants.provinces import PROVINCE_CODES, Province, get_province
from app.errors import AppError, ErrorCode
from app.models import Room, User


def check_province_code(code: str | None, field: str = "province") -> None:
    """Rule R1 for query filters: a province code from the fixed list (422 otherwise)."""
    if code is not None and code not in PROVINCE_CODES:
        raise AppError(
            ErrorCode.VALIDATION_ERROR,
            422,
            "Invalid request.",
            {field: "Must be a province code from GET /provinces."},
        )


def get_room_province(room: Room) -> Province | None:
    return get_province(room.floor.building.location.province)


def get_user_province(user: User) -> Province | None:
    if user.division is None:
        return None
    return get_province(user.division.department.location.province)
