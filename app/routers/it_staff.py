from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query

from app.routers.common import AppSettings, DbSession
from app.schemas.common import ItemList
from app.schemas.it_ticket import ITStaffPick
from app.security import ITLeadUser
from app.services import it_ticket

router = APIRouter(prefix="/it/staff", tags=["IT"])


@router.get("", response_model=ItemList[ITStaffPick], summary="List IT Staff")
def list_it_staff(
    current: ITLeadUser,
    session: DbSession,
    settings: AppSettings,
    day: Annotated[date | None, Query(description="Count each person's setups on this day")] = None,
    ticket_id: Annotated[
        int | None, Query(description="The setup being assigned: its day and time clashes")
    ] = None,
) -> ItemList[ITStaffPick]:
    """IT Lead only: active users with the IT Staff role, by name, to assign to a setup. With
    `day`, `setups_that_day` counts the setups each one already has that day. With `ticket_id`,
    the day is that setup's, and `busy` lists each one's other setups at the same time (a
    warning only: they can still be assigned)."""
    picks = it_ticket.staff_picks(session, settings, current, day, ticket_id)
    return ItemList[ITStaffPick](items=picks, total=len(picks))
