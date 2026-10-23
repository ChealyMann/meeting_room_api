"""Users: detail view and self-service profile. Admin account management: tasks 47-52."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.constants.roles import seed_order
from app.errors import AppError, ErrorCode
from app.models import Role, Room, User, user_roles
from app.schemas.refs import NamedRef, ProvinceRef, RoleRef
from app.schemas.user import UserDetail
from app.services.province import get_user_province


def load_roles(session: Session, user_id: int) -> list[Role]:
    """The user's roles in seed order."""
    roles = session.scalars(
        select(Role)
        .join(user_roles, user_roles.c.role_id == Role.id)
        .where(user_roles.c.user_id == user_id)
    ).all()
    return sorted(roles, key=lambda role: seed_order(role.code))


def owned_room_ids(session: Session, user_id: int) -> list[int]:
    return list(
        session.scalars(select(Room.id).where(Room.room_owner_id == user_id).order_by(Room.id))
    )


def build_user_detail(session: Session, user: User) -> UserDetail:
    division = user.division
    province = get_user_province(user)
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
        province=ProvinceRef.model_validate(province._asdict()) if province else None,
        roles=[RoleRef.model_validate(role) for role in load_roles(session, user.id)],
        owned_room_ids=owned_room_ids(session, user.id),
        is_active=user.is_active,
        must_change_password=user.must_change_password,
        last_login_at=user.last_login_at,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


def update_me(session: Session, user: User, changes: dict) -> UserDetail:
    """Apply a PATCH /me. `changes` holds only the fields sent (secondary email, phone,
    photo link, email notifications), already trimmed and checked by the schema."""
    secondary_email = changes.get("secondary_email")
    if secondary_email is not None and secondary_email == user.email:
        raise AppError(
            ErrorCode.VALIDATION_ERROR,
            422,
            "Invalid request.",
            {"secondary_email": "Second email must be different."},
        )
    for field, value in changes.items():
        setattr(user, field, value)
    session.commit()
    return build_user_detail(session, user)
