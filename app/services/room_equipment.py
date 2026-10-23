"""A room's equipment. Rule R15: repeats are saved once; every id must exist; an id the
room does not already have must be active (inactive items the room has may stay)."""

from sqlalchemy import delete, insert, select
from sqlalchemy.orm import Session

from app.errors import AppError, ErrorCode
from app.models import Equipment, Room, room_equipment
from app.security import CurrentUser
from app.services.records import get_or_404
from app.services.room import check_can_manage, room_equipment_items


def _id_list(ids: list[int]) -> str:
    return ", ".join(str(item_id) for item_id in ids)


def list_room_equipment(session: Session, room_id: int) -> list[Equipment]:
    get_or_404(session, Room, room_id)
    return room_equipment_items(session, room_id)


def set_room_equipment(
    session: Session, room_id: int, equipment_ids: list[int], current: CurrentUser
) -> list[Equipment]:
    """Replace the room's whole set in one transaction."""
    room = get_or_404(session, Room, room_id)
    check_can_manage(current, room)
    wanted = list(dict.fromkeys(equipment_ids))
    found = {
        item.id: item for item in session.scalars(select(Equipment).where(Equipment.id.in_(wanted)))
    }

    missing = sorted(set(wanted) - set(found))
    if missing:
        raise AppError(
            ErrorCode.VALIDATION_ERROR,
            422,
            "Invalid request.",
            {"equipment_ids": f"Equipment not found: {_id_list(missing)}."},
        )
    current_ids = set(
        session.scalars(
            select(room_equipment.c.equipment_id).where(room_equipment.c.room_id == room.id)
        )
    )
    inactive = sorted(i for i in wanted if i not in current_ids and not found[i].is_active)
    if inactive:
        message = f"This equipment is inactive: {_id_list(inactive)}."
        raise AppError(ErrorCode.INACTIVE_REFERENCE, 409, message, {"equipment_ids": message})

    session.execute(delete(room_equipment).where(room_equipment.c.room_id == room.id))
    if wanted:
        session.execute(
            insert(room_equipment), [{"room_id": room.id, "equipment_id": i} for i in wanted]
        )
    session.commit()
    return room_equipment_items(session, room.id)
