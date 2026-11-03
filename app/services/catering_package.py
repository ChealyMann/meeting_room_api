"""Catering packages (spec 9.15, B-13). Admin edits; everyone else sees active ones only."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.errors import AppError, ErrorCode
from app.models import CateringPackage
from app.security import CurrentUser
from app.services.listing import apply_active_filter, apply_default_order, apply_search, paginate
from app.services.records import apply_changes, get_or_404, save


def list_catering_packages(
    session: Session,
    current: CurrentUser,
    page: int,
    size: int,
    is_active: bool | None = None,
    search: str | None = None,
) -> dict:
    if not current.has_role("ADMIN"):
        is_active = True
    query = apply_active_filter(select(CateringPackage), CateringPackage, is_active)
    query = apply_search(query, search, [CateringPackage.name])
    return paginate(session, apply_default_order(query, CateringPackage), page, size)


def create_catering_package(session: Session, data: dict) -> CateringPackage:
    package = CateringPackage(**data)
    session.add(package)
    save(session)
    return package


def update_catering_package(session: Session, package_id: int, changes: dict) -> CateringPackage:
    """`changes` holds the `version` the person saw; an old one means someone else saved first."""
    package = get_or_404(session, CateringPackage, package_id)
    if package.version != changes.pop("version"):
        raise AppError(ErrorCode.STALE_VERSION, 409, "This item changed. Reload it.")
    apply_changes(package, changes)
    package.version += 1
    save(session)
    return package
