"""Rooms. Rules R2 (active floor and room type), R3 (no reactivation on an inactive
floor), R4, R7 (valid owner), R8 (owners edit only their rooms and some fields), R12
(bookable), R13 (opening hours)."""

from datetime import time

from sqlalchemy import and_, func, not_, select
from sqlalchemy.orm import Session

from app.constants.roles import RoleCode
from app.errors import AppError, ErrorCode
from app.models import (
    Building,
    Category,
    Equipment,
    Floor,
    Location,
    Room,
    RoomPhoto,
    User,
    room_equipment,
)
from app.schemas.equipment import EquipmentOut
from app.schemas.refs import BuildingRef, FloorRef, NamedRef, ProvinceRef
from app.schemas.room import OWNER_FIELDS, RoomDetail, RoomListItem
from app.schemas.room_photo import CoverPhoto, PhotoOut
from app.security import CurrentUser, load_role_codes
from app.services.listing import (
    apply_active_filter,
    apply_default_order,
    apply_search,
    paginate,
    parse_ids,
)
from app.services.province import check_province_code
from app.services.records import (
    apply_changes,
    check_parent_active,
    get_or_404,
    get_reference,
    save,
)

FLOOR = "Floor"
ROOM_TYPE = "Room type"

# R12: the room, its floor, its building and its office are all active.
_BOOKABLE = and_(
    Room.is_active.is_(True),
    Floor.is_active.is_(True),
    Building.is_active.is_(True),
    Location.is_active.is_(True),
)


def _forbidden(message: str = "You are not allowed.") -> AppError:
    return AppError(ErrorCode.FORBIDDEN, 403, message)


def check_can_manage(current: CurrentUser, room: Room) -> None:
    """R8: the Admin manages every room; a room owner only the rooms they own."""
    if current.has_role(RoleCode.ADMIN):
        return
    if not (current.has_role(RoleCode.ROOM_OWNER) and room.room_owner_id == current.id):
        raise _forbidden()


def is_bookable(room: Room) -> bool:
    building = room.floor.building
    return all(
        (room.is_active, room.floor.is_active, building.is_active, building.location.is_active)
    )


# --- Responses -------------------------------------------------------------------------


def _cover_photos(session: Session, room_ids: list[int]) -> dict[int, RoomPhoto]:
    """The photo with the lowest sort_order (then id) of each room."""
    covers: dict[int, RoomPhoto] = {}
    photos = session.scalars(
        select(RoomPhoto)
        .where(RoomPhoto.room_id.in_(room_ids))
        .order_by(RoomPhoto.room_id, RoomPhoto.sort_order, RoomPhoto.id)
    )
    for photo in photos:
        covers.setdefault(photo.room_id, photo)
    return covers


def _list_item_fields(room: Room, cover: RoomPhoto | None) -> dict:
    building = room.floor.building
    location = building.location
    return {
        "id": room.id,
        "name_en": room.name_en,
        "name_kh": room.name_kh,
        "short_desc": room.short_desc,
        "capacity": room.capacity,
        "size_sqm": room.size_sqm,
        "start_time": room.start_time,
        "end_time": room.end_time,
        "category": NamedRef.model_validate(room.category),
        "floor": FloorRef.model_validate(room.floor),
        "building": BuildingRef.model_validate(building),
        "location": NamedRef.model_validate(location),
        "province": ProvinceRef.from_code(location.province),
        "owner": NamedRef.model_validate(room.owner) if room.owner else None,
        "cover_photo": CoverPhoto.model_validate(cover) if cover else None,
        "is_active": room.is_active,
        "is_bookable": is_bookable(room),
        "is_private": room.is_private,
    }


def build_room_list_items(session: Session, rooms: list[Room]) -> list[RoomListItem]:
    covers = _cover_photos(session, [room.id for room in rooms])
    return [RoomListItem(**_list_item_fields(room, covers.get(room.id))) for room in rooms]


def room_photos(session: Session, room_id: int) -> list[RoomPhoto]:
    return list(
        session.scalars(
            select(RoomPhoto)
            .where(RoomPhoto.room_id == room_id)
            .order_by(RoomPhoto.sort_order, RoomPhoto.id)
        )
    )


def room_equipment_items(session: Session, room_id: int) -> list[Equipment]:
    query = (
        select(Equipment)
        .join(room_equipment, room_equipment.c.equipment_id == Equipment.id)
        .where(room_equipment.c.room_id == room_id)
    )
    return list(session.scalars(apply_default_order(query, Equipment)))


def build_room_detail(session: Session, room: Room) -> RoomDetail:
    photos = room_photos(session, room.id)
    return RoomDetail(
        **_list_item_fields(room, photos[0] if photos else None),
        description=room.description,
        photos=[PhotoOut.model_validate(photo) for photo in photos],
        equipment=[
            EquipmentOut.model_validate(item) for item in room_equipment_items(session, room.id)
        ],
        created_at=room.created_at,
        updated_at=room.updated_at,
    )


# --- Reading ---------------------------------------------------------------------------


def list_rooms(
    session: Session,
    page: int,
    size: int,
    province: str | None = None,
    location_id: int | None = None,
    building_id: int | None = None,
    floor_id: int | None = None,
    category_id: int | None = None,
    min_capacity: int | None = None,
    equipment_ids: str | None = None,
    owner_id: int | None = None,
    has_owner: bool | None = None,
    is_active: bool | None = None,
    bookable: bool | None = None,
    search: str | None = None,
    is_private: bool | None = None,
) -> dict:
    """Paged rooms sorted by English name. All filters combine with AND."""
    check_province_code(province)
    wanted_equipment = parse_ids(equipment_ids, "equipment_ids")

    query = (
        select(Room)
        .join(Floor, Floor.id == Room.floor_id)
        .join(Building, Building.id == Floor.building_id)
        .join(Location, Location.id == Building.location_id)
    )
    exact = (
        (Location.province, province),
        (Location.id, location_id),
        (Building.id, building_id),
        (Room.floor_id, floor_id),
        (Room.category_id, category_id),
        (Room.room_owner_id, owner_id),
    )
    for column, value in exact:
        if value is not None:
            query = query.where(column == value)
    if min_capacity is not None:
        query = query.where(Room.capacity >= min_capacity)
    if wanted_equipment:
        # Rooms having every one of the ids.
        having_all = (
            select(room_equipment.c.room_id)
            .where(room_equipment.c.equipment_id.in_(wanted_equipment))
            .group_by(room_equipment.c.room_id)
            .having(func.count() == len(wanted_equipment))
        )
        query = query.where(Room.id.in_(having_all))
    if has_owner is not None:
        owned = Room.room_owner_id.is_not(None)
        query = query.where(owned if has_owner else not_(owned))
    query = apply_active_filter(query, Room, is_active)
    if is_private is not None:
        query = query.where(Room.is_private.is_(is_private))
    if bookable is not None:
        query = query.where(_BOOKABLE if bookable else not_(_BOOKABLE))
    query = apply_search(query, search, [Room.name_en, Room.name_kh, Room.short_desc])
    return paginate(session, apply_default_order(query, Room), page, size)


def get_room(session: Session, room_id: int) -> Room:
    return get_or_404(session, Room, room_id)


def get_door_code(session: Session, room_id: int, current: CurrentUser) -> Room:
    room = get_or_404(session, Room, room_id)
    check_can_manage(current, room)
    return room


# --- Changing --------------------------------------------------------------------------


def _check_hours(start_time: time, end_time: time) -> None:
    """R13: opening time strictly before closing time; rooms do not stay open past midnight."""
    if start_time >= end_time:
        message = "Opening time must be before closing time."
        raise AppError(ErrorCode.VALIDATION_ERROR, 422, "Invalid request.", {"end_time": message})


def _get_owner(session: Session, user_id: int) -> User:
    """R7: an existing user (else 422) who is active and has ROOM_OWNER (else 409)."""
    user = session.get(User, user_id)
    if user is None:
        raise AppError(
            ErrorCode.VALIDATION_ERROR,
            422,
            "Invalid request.",
            {"room_owner_id": "User not found."},
        )
    if not user.is_active or RoleCode.ROOM_OWNER not in load_role_codes(session, user.id):
        message = "This user cannot own rooms."
        raise AppError(ErrorCode.OWNER_INVALID, 409, message, {"room_owner_id": message})
    return user


def create_room(session: Session, data: dict) -> Room:
    _check_hours(data["start_time"], data["end_time"])
    floor = get_reference(session, Floor, data["floor_id"], "floor_id", FLOOR)
    category = get_reference(session, Category, data["category_id"], "category_id", ROOM_TYPE)
    owner = _get_owner(session, data["room_owner_id"]) if data["room_owner_id"] else None

    room = Room(**data)
    room.floor, room.category, room.owner = floor, category, owner
    session.add(room)
    save(session)
    return room


def update_room(session: Session, room_id: int, changes: dict, current: CurrentUser) -> Room:
    """PATCH /rooms/{id}. A room owner may change only OWNER_FIELDS of their own rooms (R8);
    anything else is refused before any change."""
    room = get_or_404(session, Room, room_id)
    check_can_manage(current, room)
    if not current.has_role(RoleCode.ADMIN) and set(changes) - OWNER_FIELDS:
        raise _forbidden("Only the Admin can change the floor, owner or status of a room.")

    if "start_time" in changes or "end_time" in changes:
        _check_hours(
            changes.get("start_time", room.start_time), changes.get("end_time", room.end_time)
        )
    floor = room.floor
    if "floor_id" in changes and changes["floor_id"] != room.floor_id:
        floor = get_reference(session, Floor, changes["floor_id"], "floor_id", FLOOR)
    category = room.category
    if "category_id" in changes and changes["category_id"] != room.category_id:
        category = get_reference(
            session, Category, changes["category_id"], "category_id", ROOM_TYPE
        )
    owner = room.owner
    if "room_owner_id" in changes and changes["room_owner_id"] != room.room_owner_id:
        owner_id = changes["room_owner_id"]
        owner = _get_owner(session, owner_id) if owner_id is not None else None
    if changes.get("is_active") is True and not room.is_active:
        check_parent_active(floor, FLOOR)

    apply_changes(room, changes)
    room.floor, room.category, room.owner = floor, category, owner
    save(session)
    return room
