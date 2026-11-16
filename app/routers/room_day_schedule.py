from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query

from app.routers.common import DbSession
from app.schemas.common import ItemList
from app.schemas.room_schedule import RoomDaySchedule
from app.security import AnyUser
from app.services import room_schedule as schedule_service
from app.services.listing import parse_ids

router = APIRouter(prefix="/room-schedule", tags=["Room"])


@router.get("", response_model=ItemList[RoomDaySchedule], summary="See every room's day")
def get_day_schedule(
    current: AnyUser,
    session: DbSession,
    day: Annotated[date | None, Query(alias="date", description="The day; default today")] = None,
    room_ids: Annotated[
        str | None, Query(description="Comma list, e.g. 3,5; default every active room")
    ] = None,
) -> ItemList[RoomDaySchedule]:
    """Every room's blocking sessions on one day, in one request, for the Staff room cards.
    A private booking you may not see shows as a masked item, as in a room's schedule."""
    rows = schedule_service.get_day_schedule(session, current, day, parse_ids(room_ids, "room_ids"))
    return ItemList[RoomDaySchedule](items=rows, total=len(rows))
