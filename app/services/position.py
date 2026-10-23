"""Positions (job titles). Rule R4; a position has no parent, so no R2 or R3 here."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Position
from app.services.listing import apply_active_filter, apply_default_order, apply_search, paginate
from app.services.records import apply_changes, get_or_404, save


def list_positions(
    session: Session,
    page: int,
    size: int,
    is_active: bool | None = None,
    search: str | None = None,
) -> dict:
    query = apply_active_filter(select(Position), Position, is_active)
    query = apply_search(query, search, [Position.name_en, Position.name_kh])
    return paginate(session, apply_default_order(query, Position), page, size)


def get_position(session: Session, position_id: int) -> Position:
    return get_or_404(session, Position, position_id)


def create_position(session: Session, data: dict) -> Position:
    position = Position(**data)
    session.add(position)
    save(session)
    return position


def update_position(session: Session, position_id: int, changes: dict) -> Position:
    """Turning a position off leaves its users as they are; new users cannot get it (R2,
    checked by the users service)."""
    position = get_or_404(session, Position, position_id)
    apply_changes(position, changes)
    save(session)
    return position
