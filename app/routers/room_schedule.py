from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query

from app.routers.common import AppSettings, DbSession, IdPath
from app.schemas.common import ItemList
from app.schemas.room_schedule import ScheduleItem
from app.security import AnyUser
from app.services import room_schedule as schedule_service

router = APIRouter(prefix="/rooms/{room_id}/schedule", tags=["Room"])


@router.get("", response_model=ItemList[ScheduleItem], summary="See a room's schedule")
def get_schedule(
    room_id: IdPath,
    current: AnyUser,
    session: DbSession,
    settings: AppSettings,
    date_from: Annotated[
        date | None, Query(alias="from", description="First day; default today")
    ] = None,
    date_to: Annotated[
        date | None, Query(alias="to", description="Last day; default 6 days after from")
    ] = None,
) -> ItemList[ScheduleItem]:
    """Every session that blocks the room, by date and start time, both days included
    (at most 31 days). A private room's booking you may not see shows as a masked item."""
    items = schedule_service.get_schedule(session, current, room_id, date_from, date_to, settings)
    return ItemList[ScheduleItem](items=items, total=len(items))
