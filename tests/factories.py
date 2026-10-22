"""Test data in one line each. Every value can be overridden by keyword."""

from itertools import count

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.constants.roles import RoleCode
from app.models import Position, Role, User, user_roles
from app.security import hash_password

DEFAULT_PASSWORD = "Password@123"

_sequence = count(1)
# Hashing is slow on purpose; hash the default password once per test run.
_default_hash: str | None = None


def _next() -> int:
    return next(_sequence)


def _password_hash(password: str) -> str:
    global _default_hash
    if password != DEFAULT_PASSWORD:
        return hash_password(password)
    if _default_hash is None:
        _default_hash = hash_password(DEFAULT_PASSWORD)
    return _default_hash


def ensure_roles(session: Session) -> dict[str, int]:
    """The six roles, created if missing. Returns code -> id."""
    existing = dict(session.execute(select(Role.code, Role.id)).all())
    for code in RoleCode:
        if code not in existing:
            role = Role(code=code, name_en=code.title(), name_kh=code.title())
            session.add(role)
            session.flush()
            existing[code] = role.id
    return existing


def make_position(session: Session, **fields) -> Position:
    n = _next()
    position = Position(**{"name_en": f"Position {n}", "name_kh": f"មុខតំណែង {n}", **fields})
    session.add(position)
    session.flush()
    return position


def make_user(session: Session, roles=(), password: str = DEFAULT_PASSWORD, **fields) -> User:
    n = _next()
    if "position_id" not in fields:
        fields["position_id"] = make_position(session).id
    values = {
        "staff_id": f"EMP-{n:05d}",
        "name_en": f"User {n}",
        "name_kh": f"អ្នកប្រើ {n}",
        "email": f"user{n}@company.com",
        "password_hash": _password_hash(password),
        "must_change_password": False,
        **fields,
    }
    user = User(**values)
    session.add(user)
    session.flush()
    set_roles(session, user, roles)
    return user


def set_roles(session: Session, user: User, roles) -> None:
    """Replace the user's roles with `roles` (role codes)."""
    role_ids = ensure_roles(session)
    session.execute(user_roles.delete().where(user_roles.c.user_id == user.id))
    for code in dict.fromkeys(roles):
        session.execute(user_roles.insert().values(user_id=user.id, role_id=role_ids[code]))
    session.flush()
