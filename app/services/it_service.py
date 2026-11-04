"""IT services (spec 9.15, B-13). Admin edits; everyone else sees active ones only."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.constants.roles import RoleCode
from app.models import ITService
from app.security import CurrentUser
from app.services.listing import apply_active_filter, apply_default_order, apply_search, paginate
from app.services.records import apply_changes, check_and_bump_version, get_or_404, save


def list_it_services(
    session: Session,
    current: CurrentUser,
    page: int,
    size: int,
    is_active: bool | None = None,
    search: str | None = None,
) -> dict:
    if not current.has_role(RoleCode.ADMIN):
        is_active = True
    query = apply_active_filter(select(ITService), ITService, is_active)
    query = apply_search(query, search, [ITService.name])
    return paginate(session, apply_default_order(query, ITService), page, size)


def create_it_service(session: Session, data: dict) -> ITService:
    service = ITService(**data)
    session.add(service)
    save(session)
    return service


def update_it_service(session: Session, service_id: int, changes: dict) -> ITService:
    """`changes` holds the `version` the person saw; an old one means someone else saved first."""
    service = get_or_404(session, ITService, service_id, lock=True)
    check_and_bump_version(service, changes["version"])
    apply_changes(service, {k: v for k, v in changes.items() if k != "version"})
    save(session)
    return service
