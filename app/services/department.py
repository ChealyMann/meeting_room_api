"""Departments. Rules R2 (active office), R3 (no reactivation under an inactive office), R4."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Department, Location
from app.services.listing import apply_active_filter, apply_default_order, apply_search, paginate
from app.services.records import (
    apply_changes,
    check_parent_active,
    get_or_404,
    get_reference,
    save,
)

OFFICE = "Office"


def list_departments(
    session: Session,
    page: int,
    size: int,
    location_id: int | None = None,
    is_active: bool | None = None,
    search: str | None = None,
) -> dict:
    query = select(Department)
    if location_id is not None:
        query = query.where(Department.location_id == location_id)
    query = apply_active_filter(query, Department, is_active)
    query = apply_search(query, search, [Department.name_en, Department.name_kh])
    return paginate(session, apply_default_order(query, Department), page, size)


def get_department(session: Session, department_id: int) -> Department:
    return get_or_404(session, Department, department_id)


def create_department(session: Session, data: dict) -> Department:
    location = get_reference(session, Location, data["location_id"], "location_id", OFFICE)
    department = Department(**data)
    department.location = location
    session.add(department)
    save(session)
    return department


def update_department(session: Session, department_id: int, changes: dict) -> Department:
    """Changing location_id moves the department; the province of every user in its
    divisions follows (computed from the chain, nothing else is stored)."""
    department = get_or_404(session, Department, department_id)
    location = department.location
    if "location_id" in changes and changes["location_id"] != department.location_id:
        location = get_reference(session, Location, changes["location_id"], "location_id", OFFICE)
    if changes.get("is_active") is True and not department.is_active:
        check_parent_active(location, OFFICE)
    apply_changes(department, changes)
    department.location = location
    save(session)
    return department
