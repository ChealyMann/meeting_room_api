from fastapi import APIRouter

from app.routers.common import DbSession
from app.schemas.common import ItemList
from app.schemas.it_ticket import ITStaffOut
from app.security import ITLeadUser
from app.services import it_ticket

router = APIRouter(prefix="/it/staff", tags=["IT"])


@router.get("", response_model=ItemList[ITStaffOut], summary="List IT Staff")
def list_it_staff(current: ITLeadUser, session: DbSession) -> ItemList[ITStaffOut]:
    """IT Lead only: active users with the IT Staff role, by name, to assign to a setup."""
    users = it_ticket.list_it_staff(session)
    return ItemList[ITStaffOut](
        items=[ITStaffOut.model_validate(u) for u in users], total=len(users)
    )
