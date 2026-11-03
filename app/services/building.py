"""Buildings. Rules R2 (active office), R3 (no reactivation under an inactive office), R4.
Not turned off or moved while a room inside has future bookings (spec section 12, B-21)."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Building, Location
from app.services.listing import apply_active_filter, apply_default_order, apply_search, paginate
from app.services.records import (
    apply_changes,
    check_parent_active,
    get_or_404,
    get_reference,
    save,
)
from app.services.room_bookings import check_no_future_bookings, room_ids_in

OFFICE = "Office"


def list_buildings(
    session: Session,
    page: int,
    size: int,
    location_id: int | None = None,
    is_active: bool | None = None,
    search: str | None = None,
) -> dict:
    query = select(Building)
    if location_id is not None:
        query = query.where(Building.location_id == location_id)
    query = apply_active_filter(query, Building, is_active)
    query = apply_search(query, search, [Building.name_en, Building.name_kh, Building.short_name])
    return paginate(session, apply_default_order(query, Building), page, size)


def get_building(session: Session, building_id: int) -> Building:
    return get_or_404(session, Building, building_id)


def create_building(session: Session, data: dict) -> Building:
    location = get_reference(session, Location, data["location_id"], "location_id", OFFICE)
    building = Building(**data)
    building.location = location
    session.add(building)
    save(session)
    return building


def update_building(session: Session, building_id: int, changes: dict) -> Building:
    """Changing location_id moves the building; its floors and rooms move with it."""
    building = get_or_404(session, Building, building_id)
    location = building.location
    moving = "location_id" in changes and changes["location_id"] != building.location_id
    if moving:
        location = get_reference(session, Location, changes["location_id"], "location_id", OFFICE)
    if changes.get("is_active") is True and not building.is_active:
        check_parent_active(location, OFFICE)
    turning_off = changes.get("is_active") is False and building.is_active
    if turning_off or moving:
        room_ids = room_ids_in(session, building_id=building.id)
        if turning_off:
            check_no_future_bookings(session, room_ids, "building", "is_active")
        if moving:
            check_no_future_bookings(session, room_ids, "building", "location_id")
    apply_changes(building, changes)
    building.location = location
    save(session)
    return building
