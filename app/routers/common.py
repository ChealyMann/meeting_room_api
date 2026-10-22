"""Shared path and query parameters for routers (spec section 4)."""

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Path, Query
from sqlalchemy.orm import Session

from app.config import Settings, get_app_settings
from app.db import get_db

DbSession = Annotated[Session, Depends(get_db)]
AppSettings = Annotated[Settings, Depends(get_app_settings)]

# Path ids are positive integers: `abc`, `0` or `-1` return 422.
IdPath = Annotated[int, Path(gt=0)]


@dataclass
class PageParams:
    """`page` (default 1, at least 1) and `size` (default 20, 1 to 100).

    Usage: `paging: Annotated[PageParams, Depends()]`.
    """

    page: Annotated[int, Query(ge=1)] = 1
    size: Annotated[int, Query(ge=1, le=100)] = 20


# `?is_active=true|false`; without it, lists return active and inactive records.
IsActiveQuery = Annotated[bool | None, Query()]

# `?search=...`; trimmed, empty means no filter.
SearchQuery = Annotated[str | None, Query()]
