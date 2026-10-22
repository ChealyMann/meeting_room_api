"""List helpers shared by every list endpoint (spec section 4). No FastAPI imports here."""

import re
from typing import Any

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session

from app.errors import AppError, ErrorCode

_LIKE_ESCAPE = "\\"
_ID = re.compile(r"[1-9][0-9]*")


def paginate(session: Session, query: Select, page: int, size: int) -> dict[str, Any]:
    """Run `query` for one page. A page past the end has no items but the real total."""
    total = session.scalar(select(func.count()).select_from(query.order_by(None).subquery()))
    items = session.scalars(query.limit(size).offset((page - 1) * size)).all()
    return {"items": items, "page": page, "size": size, "total": total}


def apply_search(query: Select, term: str | None, columns: list) -> Select:
    """Keep rows where any of `columns` contains `term`. `%`, `_` and `\\` match literally.

    The term is trimmed; an empty term means no filter. Matching follows the column
    collation, so it ignores case and accents.
    """
    term = (term or "").strip()
    if not term:
        return query
    escaped = term.replace(_LIKE_ESCAPE, _LIKE_ESCAPE * 2).replace("%", "\\%").replace("_", "\\_")
    pattern = f"%{escaped}%"
    return query.where(or_(*(column.like(pattern, escape=_LIKE_ESCAPE) for column in columns)))


def apply_active_filter(query: Select, model, is_active: bool | None) -> Select:
    """`is_active=true|false` filters by status; `None` returns both."""
    if is_active is None:
        return query
    return query.where(model.is_active.is_(is_active))


def apply_default_order(query: Select, model) -> Select:
    """`sort_order`, then the name, then `id` (all ascending). Tables without `sort_order`
    skip that step. Equipment and floors have a single-language `name` / `floor_label`."""
    order = []
    if hasattr(model, "sort_order"):
        order.append(model.sort_order)
    for name in ("name_en", "name", "floor_label"):
        if hasattr(model, name):
            order.append(getattr(model, name))
            break
    order.append(model.id)
    return query.order_by(*order)


def parse_ids(raw: str | None, field: str) -> list[int] | None:
    """Parse a comma list of ids such as `equipment_ids=1,4,7`. Empty means no filter (None).

    Duplicates are dropped, order kept. Anything that is not a positive id returns 422.
    """
    if raw is None or not raw.strip():
        return None
    parts = [part.strip() for part in raw.split(",")]
    if not all(_ID.fullmatch(part) for part in parts):
        raise AppError(
            ErrorCode.VALIDATION_ERROR,
            422,
            "Invalid request.",
            {field: "Must be a comma-separated list of ids, e.g. 1,4,7."},
        )
    return list(dict.fromkeys(int(part) for part in parts))
