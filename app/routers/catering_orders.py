from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query

from app.routers.common import DbSession
from app.schemas.catering_order import CateringOrderItem
from app.schemas.common import ItemList
from app.security import PitikaOrAdminUser
from app.services import catering_order as catering_service
from app.services.clock import now_local

router = APIRouter(prefix="/pitika/catering", tags=["Pitika"])


@router.get("", response_model=ItemList[CateringOrderItem], summary="See the day's food list")
def list_food_orders(
    current: PitikaOrAdminUser,
    session: DbSession,
    day: Annotated[date | None, Query(alias="date", description="Default today")] = None,
) -> ItemList[CateringOrderItem]:
    """Food for bookings in IT setup or confirmed whose first session is on that day, by
    delivery time and room name. A Pitika sees their province; Admin sees every province.
    Servings are the current attendees."""
    items = catering_service.list_food_orders(session, current, day or now_local().date())
    return ItemList[CateringOrderItem](items=items, total=len(items))
