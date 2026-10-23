from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.routers.common import (
    DbSession,
    IdPath,
    IdQuery,
    IsActiveQuery,
    PageParams,
    ProvinceQuery,
    SearchQuery,
)
from app.schemas.common import Page
from app.schemas.room import DoorCode, RoomCreate, RoomDetail, RoomListItem, RoomUpdate
from app.security import AdminOrOwnerUser, AdminUser, AnyUser
from app.services import room as room_service

router = APIRouter(prefix="/rooms", tags=["Room"])


@router.get("", response_model=Page[RoomListItem], summary="List rooms")
def list_rooms(
    current: AnyUser,
    session: DbSession,
    paging: Annotated[PageParams, Depends()],
    province: ProvinceQuery = None,
    location_id: IdQuery = None,
    building_id: IdQuery = None,
    floor_id: IdQuery = None,
    category_id: IdQuery = None,
    min_capacity: Annotated[int | None, Query(ge=1)] = None,
    equipment_ids: Annotated[
        str | None, Query(description="Comma list, e.g. 1,4: rooms having every one")
    ] = None,
    owner_id: IdQuery = None,
    has_owner: Annotated[bool | None, Query()] = None,
    is_active: IsActiveQuery = None,
    is_bookable: Annotated[bool | None, Query()] = None,
    search: SearchQuery = None,
) -> Page[RoomListItem]:
    """All filters combine with AND. Search matches English name, Khmer name and short
    description. Sorted by English name."""
    result = room_service.list_rooms(
        session,
        paging.page,
        paging.size,
        province,
        location_id,
        building_id,
        floor_id,
        category_id,
        min_capacity,
        equipment_ids,
        owner_id,
        has_owner,
        is_active,
        is_bookable,
        search,
    )
    items = room_service.build_room_list_items(session, result["items"])
    return Page[RoomListItem](**{**result, "items": items})


@router.get(
    "/{room_id}",
    response_model=RoomDetail,
    summary="See one room, with its photos and equipment",
)
def get_room(room_id: IdPath, current: AnyUser, session: DbSession) -> RoomDetail:
    return room_service.build_room_detail(session, room_service.get_room(session, room_id))


@router.post("", response_model=RoomDetail, status_code=201, summary="Create a room")
def create_room(body: RoomCreate, current: AdminUser, session: DbSession) -> RoomDetail:
    room = room_service.create_room(session, body.model_dump())
    return room_service.build_room_detail(session, room)


@router.patch(
    "/{room_id}",
    response_model=RoomDetail,
    summary="Change a room (a room owner: only some fields of their own rooms)",
)
def update_room(
    room_id: IdPath, body: RoomUpdate, current: AdminOrOwnerUser, session: DbSession
) -> RoomDetail:
    changes = body.model_dump(exclude_unset=True)
    room = room_service.update_room(session, room_id, changes, current)
    return room_service.build_room_detail(session, room)


@router.get(
    "/{room_id}/door-code",
    response_model=DoorCode,
    summary="See a room's door code (Admin, or the room's owner)",
)
def get_door_code(room_id: IdPath, current: AdminOrOwnerUser, session: DbSession) -> DoorCode:
    room = room_service.get_door_code(session, room_id, current)
    return DoorCode(room_id=room.id, door_code=room.door_code)
