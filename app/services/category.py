"""Categories (room types). Rule R4; a category has no parent, so no R2 or R3 here."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Category
from app.services.listing import apply_active_filter, apply_default_order, apply_search, paginate
from app.services.records import apply_changes, get_or_404, save


def list_categories(
    session: Session,
    page: int,
    size: int,
    is_active: bool | None = None,
    search: str | None = None,
) -> dict:
    query = apply_active_filter(select(Category), Category, is_active)
    query = apply_search(query, search, [Category.name_en, Category.name_kh])
    return paginate(session, apply_default_order(query, Category), page, size)


def get_category(session: Session, category_id: int) -> Category:
    return get_or_404(session, Category, category_id)


def create_category(session: Session, data: dict) -> Category:
    category = Category(**data)
    session.add(category)
    save(session)
    return category


def update_category(session: Session, category_id: int, changes: dict) -> Category:
    """Turning a category off leaves its rooms as they are; new or moved rooms cannot
    use it (R2, checked by the rooms service)."""
    category = get_or_404(session, Category, category_id)
    apply_changes(category, changes)
    save(session)
    return category
