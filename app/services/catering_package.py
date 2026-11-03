"""Catering packages (spec 9.15, B-13). Admin edits; everyone else sees active ones only."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.constants.roles import RoleCode
from app.models import CateringPackage
from app.security import CurrentUser
from app.services.listing import apply_active_filter, apply_default_order, apply_search, paginate
from app.services.records import apply_changes, check_and_bump_version, get_or_404, save


def list_catering_packages(
    session: Session,
    current: CurrentUser,
    page: int,
    size: int,
    is_active: bool | None = None,
    search: str | None = None,
) -> dict:
    if not current.has_role(RoleCode.ADMIN):
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
    package = get_or_404(session, CateringPackage, package_id, lock=True)
    check_and_bump_version(package, changes["version"])
    apply_changes(package, {k: v for k, v in changes.items() if k != "version"})
    save(session)
    return package
