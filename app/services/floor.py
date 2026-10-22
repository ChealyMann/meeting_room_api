"""Floors. Rules R2 (active building), R3 (no reactivation under an inactive building), R4."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Building, Floor
from app.services.listing import apply_active_filter, apply_default_order, apply_search, paginate
from app.services.records import (
    apply_changes,
    check_parent_active,
    get_or_404,
    get_reference,
    save,
)

BUILDING = "Building"


def list_floors(
    session: Session,
    page: int,
    size: int,
    building_id: int | None = None,
    location_id: int | None = None,
    is_active: bool | None = None,
    search: str | None = None,
) -> dict:
    query = select(Floor)
    if building_id is not None:
        query = query.where(Floor.building_id == building_id)
    if location_id is not None:
        query = query.join(Building, Building.id == Floor.building_id).where(
            Building.location_id == location_id
        )
    query = apply_active_filter(query, Floor, is_active)
    query = apply_search(query, search, [Floor.floor_label])
    return paginate(session, apply_default_order(query, Floor), page, size)


def get_floor(session: Session, floor_id: int) -> Floor:
    return get_or_404(session, Floor, floor_id)


def create_floor(session: Session, data: dict) -> Floor:
    building = get_reference(session, Building, data["building_id"], "building_id", BUILDING)
    floor = Floor(**data)
    floor.building = building
    session.add(floor)
    save(session)
    return floor


def update_floor(session: Session, floor_id: int, changes: dict) -> Floor:
    floor = get_or_404(session, Floor, floor_id)
    building = floor.building
    if "building_id" in changes and changes["building_id"] != floor.building_id:
        building = get_reference(session, Building, changes["building_id"], "building_id", BUILDING)
    if changes.get("is_active") is True and not floor.is_active:
        check_parent_active(building, BUILDING)
    apply_changes(floor, changes)
    floor.building = building
    save(session)
    return floor
