"""Locations (offices). Rules R1, R3 (none: a location has no parent), R4."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Location
from app.services.listing import apply_active_filter, apply_default_order, apply_search, paginate
from app.services.province import check_province_code
from app.services.records import apply_changes, get_or_404, save


def list_locations(
    session: Session,
    page: int,
    size: int,
    province: str | None = None,
    is_active: bool | None = None,
    search: str | None = None,
) -> dict:
    check_province_code(province)
    query = select(Location)
    if province is not None:
        query = query.where(Location.province == province)
    query = apply_active_filter(query, Location, is_active)
    query = apply_search(query, search, [Location.name_en, Location.name_kh, Location.address])
    return paginate(session, apply_default_order(query, Location), page, size)


def get_location(session: Session, location_id: int) -> Location:
    return get_or_404(session, Location, location_id)


def create_location(session: Session, data: dict) -> Location:
    location = Location(**data)
    session.add(location)
    save(session)
    return location


def update_location(session: Session, location_id: int, changes: dict) -> Location:
    """Turning a location off does not change its buildings, but every room inside
    becomes unbookable (R12, computed from the chain)."""
    location = get_or_404(session, Location, location_id)
    apply_changes(location, changes)
    save(session)
    return location
