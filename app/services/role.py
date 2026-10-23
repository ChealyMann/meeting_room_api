"""Roles. Rule R17: only the six seeded roles; their code and status never change."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.constants.roles import seed_order
from app.models import Role
from app.services.records import apply_changes, get_or_404, save


def list_roles(session: Session) -> list[Role]:
    """Every role in seed order: ADMIN, ROOM_OWNER, STAFF, PITIKA, IT_LEAD, IT_STAFF."""
    return sorted(session.scalars(select(Role)).all(), key=lambda role: seed_order(role.code))


def update_role(session: Session, role_id: int, changes: dict) -> Role:
    """`changes` holds only `name_en` and `name_kh`; the request model refuses the rest."""
    role = get_or_404(session, Role, role_id)
    apply_changes(role, changes)
    save(session)
    return role
