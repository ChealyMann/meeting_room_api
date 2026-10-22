"""Building blocks every request and response model uses (spec section 4).

Request models
    Subclass `RequestModel`. Unknown fields are refused, so server-set fields
    (`id`, `created_at`, `password_hash`, ...) are refused too.
    - `Text(100)`: required text, trimmed, 1 to 100 characters.
    - `OptionalText(200)`: trimmed; empty after trimming is saved as `None`.
    - `Password`: 8 to 128 characters, never trimmed.
    - `SortOrder`: whole number 0 to 9999.

PATCH models
    Declare required fields as `name_en: Text(100) = None`. A field left out keeps its
    default and is not "set"; sending `null` fails validation ("This field is required.").
    Read the changes with `body.model_dump(exclude_unset=True)`.

Response models
    Subclass `ResponseModel` (reads ORM objects). Use `UtcDateTime` for datetimes so they
    are returned as `2026-10-21T02:15:00Z`. Lists use `Page[Item]` or `ItemList[Item]`.
"""

from datetime import UTC, datetime
from typing import Annotated, Any

from pydantic import AfterValidator, BaseModel, BeforeValidator, ConfigDict, Field, PlainSerializer


class RequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ResponseModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


def _strip(value: Any) -> Any:
    return value.strip() if isinstance(value, str) else value


def _strip_to_none(value: Any) -> Any:
    if isinstance(value, str):
        return value.strip() or None
    return value


def Text(max_length: int) -> Any:  # noqa: N802 - used like a type: `name_en: Text(100)`
    """Required text: trimmed, then 1 to `max_length` characters (not bytes)."""
    # The limits sit on the inner `str`, so they apply after trimming and to text only.
    limited = Annotated[str, Field(min_length=1, max_length=max_length)]
    return Annotated[limited, BeforeValidator(_strip)]


def OptionalText(max_length: int) -> Any:  # noqa: N802
    """Optional text: trimmed; empty becomes None; at most `max_length` characters."""
    limited = Annotated[str, Field(max_length=max_length)]
    return Annotated[limited | None, BeforeValidator(_strip_to_none)]


def _check_password_length(value: str) -> str:
    if not 8 <= len(value) <= 128:
        raise ValueError("Password must be 8 to 128 characters.")
    return value


# Rule R18 (length part). Never trimmed: " abc12345" and "abc12345" are different passwords.
Password = Annotated[str, AfterValidator(_check_password_length)]


def _check_sort_order(value: int) -> int:
    if not 0 <= value <= 9999:
        raise ValueError("Must be 0 to 9999.")
    return value


SortOrder = Annotated[int, AfterValidator(_check_sort_order)]


def _format_utc(value: datetime) -> str:
    if value.tzinfo is not None:
        value = value.astimezone(UTC).replace(tzinfo=None)
    return value.strftime("%Y-%m-%dT%H:%M:%SZ")


# Stored as naive UTC; always returned in ISO 8601 with a Z.
UtcDateTime = Annotated[datetime, PlainSerializer(_format_utc, return_type=str)]


class Page[T](BaseModel):
    """A paged list: `{"items": [...], "page": 1, "size": 20, "total": 57}`."""

    items: list[T]
    page: int
    size: int
    total: int


class ItemList[T](BaseModel):
    """A small fixed list that is not paged: `{"items": [...], "total": 6}`."""

    items: list[T]
    total: int
