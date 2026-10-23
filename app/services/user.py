"""Users: detail view, self-service profile and Admin account management (tasks 47-52).

Rules: R2 (position and division), R5 (unique email and staff ID, second email differs),
R6 (some roles need a division), R9 (losing ROOM_OWNER or being turned off clears the
user's rooms), R10 (always one active Admin), R11 (an Admin cannot demote or turn off
themselves), R18 (new passwords).
"""

from sqlalchemy import delete, insert, select
from sqlalchemy.orm import Session

from app.constants.roles import RoleCode, seed_order
from app.errors import AppError, ErrorCode
from app.models import Department, Division, Location, Position, Role, Room, User, user_roles
from app.schemas.refs import NamedRef, ProvinceRef, RoleRef
from app.schemas.user import UserDetail, UserListItem
from app.security import hash_password
from app.services.listing import apply_active_filter, apply_default_order, apply_search, paginate
from app.services.passwords import check_new_password
from app.services.province import check_province_code, get_user_province
from app.services.records import apply_changes, get_or_404, get_reference, save

POSITION = "Job position"
DIVISION = "Division"
ROLES_NEEDING_DIVISION = {RoleCode.PITIKA, RoleCode.IT_LEAD, RoleCode.IT_STAFF}


def _invalid(field: str, message: str) -> AppError:
    return AppError(ErrorCode.VALIDATION_ERROR, 422, "Invalid request.", {field: message})


def _conflict(code: ErrorCode, field: str, message: str) -> AppError:
    return AppError(code, 409, message, {field: message})


# --- Reading ---------------------------------------------------------------------------


def load_roles(session: Session, user_id: int) -> list[Role]:
    """The user's roles in seed order."""
    roles = session.scalars(
        select(Role)
        .join(user_roles, user_roles.c.role_id == Role.id)
        .where(user_roles.c.user_id == user_id)
    ).all()
    return sorted(roles, key=lambda role: seed_order(role.code))


def role_codes_by_user(session: Session, user_ids: list[int]) -> dict[int, list[str]]:
    """Role codes of several users at once, each list in seed order."""
    rows = session.execute(
        select(user_roles.c.user_id, Role.code)
        .join(Role, Role.id == user_roles.c.role_id)
        .where(user_roles.c.user_id.in_(user_ids))
    ).all()
    codes: dict[int, list[str]] = {user_id: [] for user_id in user_ids}
    for user_id, code in rows:
        codes[user_id].append(code)
    return {user_id: sorted(found, key=seed_order) for user_id, found in codes.items()}


def owned_room_ids(session: Session, user_id: int) -> list[int]:
    return list(
        session.scalars(select(Room.id).where(Room.room_owner_id == user_id).order_by(Room.id))
    )


def _province_ref(user: User) -> ProvinceRef | None:
    province = get_user_province(user)
    return ProvinceRef.model_validate(province._asdict()) if province else None


def build_user_detail(session: Session, user: User) -> UserDetail:
    division = user.division
    return UserDetail(
        id=user.id,
        staff_id=user.staff_id,
        title=user.title,
        name_en=user.name_en,
        name_kh=user.name_kh,
        email=user.email,
        secondary_email=user.secondary_email,
        phone=user.phone,
        avatar_url=user.avatar_url,
        email_notifications=user.email_notifications,
        division=NamedRef.model_validate(division) if division else None,
        department=NamedRef.model_validate(division.department) if division else None,
        position=NamedRef.model_validate(user.position),
        province=_province_ref(user),
        roles=[RoleRef.model_validate(role) for role in load_roles(session, user.id)],
        owned_room_ids=owned_room_ids(session, user.id),
        is_active=user.is_active,
        must_change_password=user.must_change_password,
        last_login_at=user.last_login_at,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


def build_user_list_item(user: User, role_codes: list[str]) -> UserListItem:
    return UserListItem(
        id=user.id,
        staff_id=user.staff_id,
        title=user.title,
        name_en=user.name_en,
        name_kh=user.name_kh,
        email=user.email,
        division=NamedRef.model_validate(user.division) if user.division else None,
        position=NamedRef.model_validate(user.position),
        province=_province_ref(user),
        role_codes=role_codes,
        is_active=user.is_active,
        last_login_at=user.last_login_at,
    )


def list_users(
    session: Session,
    page: int,
    size: int,
    division_id: int | None = None,
    department_id: int | None = None,
    position_id: int | None = None,
    role: str | None = None,
    province: str | None = None,
    is_active: bool | None = None,
    search: str | None = None,
) -> dict:
    """Paged users sorted by English name. A user without a division has no province, so
    they never match a `province` filter."""
    check_province_code(province)
    if role is not None and role not in RoleCode.__members__:
        raise _invalid("role", "Unknown role.")

    query = select(User)
    if division_id is not None:
        query = query.where(User.division_id == division_id)
    if department_id is not None or province is not None:
        query = query.join(Division, Division.id == User.division_id)
        if department_id is not None:
            query = query.where(Division.department_id == department_id)
        if province is not None:
            query = (
                query.join(Department, Department.id == Division.department_id)
                .join(Location, Location.id == Department.location_id)
                .where(Location.province == province)
            )
    if position_id is not None:
        query = query.where(User.position_id == position_id)
    if role is not None:
        with_role = (
            select(user_roles.c.user_id)
            .join(Role, Role.id == user_roles.c.role_id)
            .where(Role.code == role)
        )
        query = query.where(User.id.in_(with_role))
    query = apply_active_filter(query, User, is_active)
    query = apply_search(query, search, [User.name_en, User.name_kh, User.staff_id, User.email])
    return paginate(session, apply_default_order(query, User), page, size)


def get_user(session: Session, user_id: int) -> User:
    return get_or_404(session, User, user_id)


# --- Shared rule checks ----------------------------------------------------------------


def _check_secondary_email(email: str, secondary_email: str | None, field: str) -> None:
    """R5: the second email must differ from the main one (both are stored lowercase)."""
    if secondary_email is not None and secondary_email == email:
        raise _invalid(field, "Second email must be different.")


def _check_not_last_admin(session: Session, user_id: int, field: str) -> None:
    """R10. Locks the active Admins' rows, so two Admins demoting each other at the same
    moment cannot both succeed."""
    admin_ids = session.scalars(
        select(User.id)
        .join(user_roles, user_roles.c.user_id == User.id)
        .join(Role, Role.id == user_roles.c.role_id)
        .where(Role.code == RoleCode.ADMIN, User.is_active.is_(True))
        .with_for_update()
    ).all()
    if not any(admin_id != user_id for admin_id in admin_ids):
        raise _conflict(ErrorCode.LAST_ADMIN, field, "You cannot remove the last Admin.")


def _clear_owned_rooms(session: Session, user_id: int) -> list[int]:
    """R9: every room the user owns becomes a no-owner room. Returns their ids."""
    rooms = session.scalars(
        select(Room).where(Room.room_owner_id == user_id).order_by(Room.id)
    ).all()
    for room in rooms:
        room.owner = None
    return [room.id for room in rooms]


def _self_action(field: str) -> AppError:
    return _conflict(ErrorCode.SELF_ACTION_NOT_ALLOWED, field, "You cannot do this to yourself.")


def _division_required(field: str) -> AppError:
    return _conflict(ErrorCode.DIVISION_REQUIRED, field, "This role needs a division.")


# --- Changing --------------------------------------------------------------------------


def create_user(session: Session, data: dict) -> User:
    """POST /users: no roles, and the user must change the temporary password."""
    password = data.pop("temporary_password")
    check_new_password(password, data["email"], "temporary_password")
    _check_secondary_email(data["email"], data["secondary_email"], "secondary_email")
    position = get_reference(session, Position, data["position_id"], "position_id", POSITION)
    division = None
    if data["division_id"] is not None:
        division = get_reference(session, Division, data["division_id"], "division_id", DIVISION)

    user = User(**data, password_hash=hash_password(password), must_change_password=True)
    user.position, user.division = position, division
    session.add(user)
    save(session)
    return user


def update_user(
    session: Session, user_id: int, changes: dict, actor_id: int
) -> tuple[User, list[int]]:
    """PATCH /users/{id}. Returns the user and the rooms cleared by R9."""
    user = get_or_404(session, User, user_id)

    email = changes.get("email", user.email)
    secondary_email = changes.get("secondary_email", user.secondary_email)
    field = "secondary_email" if "secondary_email" in changes else "email"
    _check_secondary_email(email, secondary_email, field)

    position = user.position
    if "position_id" in changes and changes["position_id"] != user.position_id:
        position = get_reference(session, Position, changes["position_id"], "position_id", POSITION)
    division = user.division
    if "division_id" in changes and changes["division_id"] != user.division_id:
        if changes["division_id"] is None:
            codes = {role.code for role in load_roles(session, user.id)}
            if codes & ROLES_NEEDING_DIVISION:
                raise _division_required("division_id")
            division = None
        else:
            division = get_reference(
                session, Division, changes["division_id"], "division_id", DIVISION
            )

    turning_off = changes.get("is_active") is False and user.is_active
    if turning_off:
        if user.id == actor_id:
            raise _self_action("is_active")  # R11, checked before R10
        if any(role.code == RoleCode.ADMIN for role in load_roles(session, user.id)):
            _check_not_last_admin(session, user.id, "is_active")

    apply_changes(user, changes)
    user.position, user.division = position, division
    rooms_unassigned = _clear_owned_rooms(session, user.id) if turning_off else []
    save(session)
    return user, rooms_unassigned


def set_user_roles(
    session: Session, user_id: int, role_codes: list[str], actor_id: int
) -> tuple[User, list[int]]:
    """PUT /users/{id}/roles: replace every role in one transaction. Returns the user and
    the rooms cleared by R9."""
    user = get_or_404(session, User, user_id)
    new_codes = sorted(set(role_codes), key=seed_order)
    old_codes = {role.code for role in load_roles(session, user.id)}

    losing_admin = RoleCode.ADMIN in old_codes and RoleCode.ADMIN not in new_codes
    if losing_admin and user.id == actor_id:
        raise _self_action("role_codes")  # R11, checked before R10
    if losing_admin and user.is_active:
        _check_not_last_admin(session, user.id, "role_codes")
    if ROLES_NEEDING_DIVISION.intersection(new_codes) and user.division_id is None:
        raise _division_required("role_codes")

    role_ids = dict(
        session.execute(select(Role.code, Role.id).where(Role.code.in_(new_codes))).all()
    )
    if len(role_ids) != len(new_codes):  # the roles table is missing a seeded role
        raise _invalid("role_codes", "Unknown role.")

    losing_owner = RoleCode.ROOM_OWNER in old_codes and RoleCode.ROOM_OWNER not in new_codes
    rooms_unassigned = _clear_owned_rooms(session, user.id) if losing_owner else []
    session.execute(delete(user_roles).where(user_roles.c.user_id == user.id))
    if new_codes:
        session.execute(
            insert(user_roles), [{"user_id": user.id, "role_id": role_ids[c]} for c in new_codes]
        )
    save(session)
    return user, rooms_unassigned


def reset_password(session: Session, user_id: int, password: str) -> None:
    """POST /users/{id}/reset-password. The new hash changes the password fingerprint, so
    every token the user holds stops working. Works on inactive users too."""
    user = get_or_404(session, User, user_id)
    check_new_password(password, user.email, "temporary_password")
    user.password_hash = hash_password(password)
    user.must_change_password = True
    session.commit()


def update_me(session: Session, user: User, changes: dict) -> UserDetail:
    """Apply a PATCH /me. `changes` holds only the fields sent (secondary email, phone,
    photo link, email notifications), already trimmed and checked by the schema."""
    secondary_email = changes.get("secondary_email")
    if secondary_email is not None and secondary_email == user.email:
        raise _invalid("secondary_email", "Second email must be different.")
    for field, value in changes.items():
        setattr(user, field, value)
    session.commit()
    return build_user_detail(session, user)
