"""Equipment. Rule R4; R15 (which equipment a room may have) lives with room equipment."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Equipment
from app.services.listing import apply_active_filter, apply_default_order, apply_search, paginate
from app.services.records import apply_changes, get_or_404, save


def list_equipment(
    session: Session,
    page: int,
    size: int,
    is_active: bool | None = None,
    search: str | None = None,
) -> dict:
    query = apply_active_filter(select(Equipment), Equipment, is_active)
    query = apply_search(query, search, [Equipment.name])
    return paginate(session, apply_default_order(query, Equipment), page, size)


def get_equipment(session: Session, equipment_id: int) -> Equipment:
    return get_or_404(session, Equipment, equipment_id)


def create_equipment(session: Session, data: dict) -> Equipment:
    equipment = Equipment(**data)
    session.add(equipment)
    save(session)
    return equipment


def update_equipment(session: Session, equipment_id: int, changes: dict) -> Equipment:
    """Turning equipment off keeps it on rooms that already have it; it cannot be
    added to a room again (R15)."""
    equipment = get_or_404(session, Equipment, equipment_id)
    apply_changes(equipment, changes)
    save(session)
    return equipment
