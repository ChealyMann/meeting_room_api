from app.schemas.common import ResponseModel, UtcDateTime
from app.schemas.refs import NamedRef, ProvinceRef, RoleRef


class UserDetail(ResponseModel):
    """One user with everything about them. Never contains the password hash."""

    id: int
    staff_id: str
    title: str | None
    name_en: str
    name_kh: str
    email: str
    secondary_email: str | None
    phone: str | None
    avatar_url: str | None
    email_notifications: bool
    division: NamedRef | None
    department: NamedRef | None
    position: NamedRef
    province: ProvinceRef | None
    roles: list[RoleRef]  # seed order: ADMIN, ROOM_OWNER, STAFF, PITIKA, IT_LEAD, IT_STAFF
    owned_room_ids: list[int]
    is_active: bool
    must_change_password: bool
    last_login_at: UtcDateTime | None
    created_at: UtcDateTime
    updated_at: UtcDateTime
