from fastapi import APIRouter

from app.routers.common import DbSession
from app.schemas.slip_settings import SlipSettingsOut, SlipSettingsUpdate
from app.security import AdminUser
from app.services import slip_settings as slip_settings_service

router = APIRouter(prefix="/slip-settings", tags=["Request slip"])


@router.get("", response_model=SlipSettingsOut, summary="See the request slip settings")
def get_slip_settings(current: AdminUser, session: DbSession) -> SlipSettingsOut:
    return SlipSettingsOut.model_validate(slip_settings_service.get_slip_settings(session))


@router.put("", response_model=SlipSettingsOut, summary="Change the request slip settings")
def update_slip_settings(
    body: SlipSettingsUpdate, current: AdminUser, session: DbSession
) -> SlipSettingsOut:
    row = slip_settings_service.update_slip_settings(session, body.model_dump())
    return SlipSettingsOut.model_validate(row)
