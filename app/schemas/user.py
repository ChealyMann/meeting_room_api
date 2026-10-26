from typing import Annotated

from pydantic import AfterValidator

from app.constants.roles import RoleCode
from app.schemas.common import (
    Email,
    OptionalEmail,
    OptionalRefId,
    OptionalText,
    OptionalTitle,
    Password,
    RefId,
    RequestModel,
    ResponseModel,
    Text,
    UtcDateTime,
)
from app.schemas.refs import NamedRef, ProvinceRef, RoleRef


class UserCreate(RequestModel):
    """POST /users. The new user has no roles and must change the password at first sign-in."""

    staff_id: Text(20)
    title: OptionalTitle = None
    name_en: Text(100)
    name_kh: Text(100)
    email: Email
    secondary_email: OptionalEmail = None
    phone: OptionalText(20) = None
    division_id: OptionalRefId = None  # must exist and be active (R2)
    position_id: RefId  # must exist and be active (R2)
    email_notifications: bool = True
    temporary_password: Password  # R18; never trimmed


class UserUpdate(RequestModel):
    """PATCH /users/{id}: the fields of UserCreate except the password, plus is_active."""

    staff_id: Text(20) = None
    title: OptionalTitle = None
    name_en: Text(100) = None
    name_kh: Text(100) = None
    email: Email = None
    secondary_email: OptionalEmail = None
    phone: OptionalText(20) = None
    division_id: OptionalRefId = None
    position_id: RefId = None
    email_notifications: bool = None
    is_active: bool = None


class ResetPasswordRequest(RequestModel):
    temporary_password: Password  # R18; never trimmed


def _check_role_codes(codes: list[str]) -> list[str]:
    if any(code not in RoleCode.__members__ for code in codes):
        raise ValueError("Unknown role.")
    return codes


class SetRolesRequest(RequestModel):
    """PUT /users/{id}/roles: replaces every role. Repeats are saved once; [] removes all."""

    role_codes: Annotated[list[str], AfterValidator(_check_role_codes)]


class UserListItem(ResponseModel):
    id: int
    staff_id: str
    title: str | None
    name_en: str
    name_kh: str
    email: str
    division: NamedRef | None
    position: NamedRef
    province: ProvinceRef | None
    role_codes: list[str]  # seed order
    is_active: bool
    last_login_at: UtcDateTime | None


class MeUpdate(RequestModel):
    """PATCH /me: only these three fields. The photo is uploaded with PUT /me/avatar;
    name, email and roles are changed by the Admin."""

    secondary_email: OptionalEmail = None
    phone: OptionalText(20) = None
    email_notifications: bool = None  # `null` is refused


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
    avatar_url: str | None  # GET /users/{id}/avatar, or null when there is no photo
    signature_url: str | None  # GET /users/{id}/signature, or null when there is none
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


class UserChanged(UserDetail):
    """PATCH /users/{id} and PUT /users/{id}/roles: the user, plus the rooms whose owner
    was cleared by this change (R9). Empty when nothing was cleared."""

    rooms_unassigned: list[int]
