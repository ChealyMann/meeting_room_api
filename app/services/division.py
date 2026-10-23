"""Divisions. Rules R2 (active department), R3 (no reactivation under an inactive
department), R4."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Department, Division
from app.services.listing import apply_active_filter, apply_default_order, apply_search, paginate
from app.services.records import (
    apply_changes,
    check_parent_active,
    get_or_404,
    get_reference,
    save,
)

DEPARTMENT = "Department"


def list_divisions(
    session: Session,
    page: int,
    size: int,
    department_id: int | None = None,
    is_active: bool | None = None,
    search: str | None = None,
) -> dict:
    query = select(Division)
    if department_id is not None:
        query = query.where(Division.department_id == department_id)
    query = apply_active_filter(query, Division, is_active)
    query = apply_search(query, search, [Division.name_en, Division.name_kh, Division.short_name])
    return paginate(session, apply_default_order(query, Division), page, size)


def get_division(session: Session, division_id: int) -> Division:
    return get_or_404(session, Division, division_id)


def create_division(session: Session, data: dict) -> Division:
    department = get_reference(
        session, Department, data["department_id"], "department_id", DEPARTMENT
    )
    division = Division(**data)
    division.department = department
    session.add(division)
    save(session)
    return division


def update_division(session: Session, division_id: int, changes: dict) -> Division:
    """Turning a division off leaves its users in it; new users cannot join it (R2)."""
    division = get_or_404(session, Division, division_id)
    department = division.department
    if "department_id" in changes and changes["department_id"] != division.department_id:
        department = get_reference(
            session, Department, changes["department_id"], "department_id", DEPARTMENT
        )
    if changes.get("is_active") is True and not division.is_active:
        check_parent_active(department, DEPARTMENT)
    apply_changes(division, changes)
    division.department = department
    save(session)
    return division
