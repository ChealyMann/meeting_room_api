"""Where a room or a user is (spec section 5). The booking scope reuses these.

Room: floor -> building -> location -> province.
User: division -> department -> location -> province; no division means no province.
"""

from app.constants.provinces import Province, get_province
from app.models import Room, User


def get_room_province(room: Room) -> Province | None:
    return get_province(room.floor.building.location.province)


def get_user_province(user: User) -> Province | None:
    if user.division is None:
        return None
    return get_province(user.division.department.location.province)
