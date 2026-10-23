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

import re
from datetime import UTC, datetime, time
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


# A practical check, not full RFC 5322: one @, no spaces, a dot in the domain.
_EMAIL = re.compile(r"[^@\s]+@[^@\s.]+(\.[^@\s.]+)+")


def _check_email(value: str) -> str:
    if not _EMAIL.fullmatch(value):
        raise ValueError("Must be a valid email address.")
    return value.lower()


# Trimmed and saved lowercase, at most 254 characters.
Email = Annotated[
    Annotated[str, Field(min_length=1, max_length=254), AfterValidator(_check_email)],
    BeforeValidator(_strip),
]
OptionalEmail = Annotated[
    Annotated[str, Field(max_length=254), AfterValidator(_check_email)] | None,
    BeforeValidator(_strip_to_none),
]


def _check_link(value: str) -> str:
    # "//host" would be a link to another site, so a single leading slash only.
    if not value.startswith(("http://", "https://", "/")) or value.startswith("//"):
        raise ValueError("Must start with http://, https:// or /.")
    return value


def OptionalLink(max_length: int) -> Any:  # noqa: N802
    """Optional link such as a photo URL: http://, https:// or a path starting with /."""
    limited = Annotated[str, Field(max_length=max_length), AfterValidator(_check_link)]
    return Annotated[limited | None, BeforeValidator(_strip_to_none)]


def _check_province_code(value: str) -> str:
    from app.constants.provinces import PROVINCE_CODES

    if value not in PROVINCE_CODES:
        raise ValueError("Must be a province code from GET /provinces.")
    return value


# Rule R1: a code from the fixed list, e.g. "PHNOM_PENH".
ProvinceCode = Annotated[str, AfterValidator(_check_province_code)]


# A record linked by id in a request body: a positive whole number.
RefId = Annotated[int, Field(gt=0)]
# The same, where `null` is allowed (e.g. a user's division, a room's owner).
OptionalRefId = RefId | None

TITLES = ("Mr.", "Ms.", "Mrs.", "Dr.")


def _check_title(value: str) -> str:
    if value not in TITLES:
        raise ValueError("Must be one of Mr., Ms., Mrs., Dr.")
    return value


# A person's title, exactly one of TITLES; empty after trimming is saved as None.
OptionalTitle = Annotated[
    Annotated[str, AfterValidator(_check_title)] | None, BeforeValidator(_strip_to_none)
]


def IntRange(low: int, high: int) -> Any:  # noqa: N802 - used like a type: `capacity: IntRange(1, 10000)`
    """A whole number from `low` to `high`."""

    def check(value: int) -> int:
        if not low <= value <= high:
            raise ValueError(f"Must be {low} to {high}.")
        return value

    return Annotated[int, AfterValidator(check)]


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


_TIME = re.compile(r"(\d{1,2}):(\d{2})(?::(\d{2}))?")


def _parse_local_time(value: Any) -> Any:
    if value is None or isinstance(value, time):
        return value.replace(second=0, microsecond=0) if value else value
    match = _TIME.fullmatch(value.strip()) if isinstance(value, str) else None
    if match is None:
        raise ValueError("Must be a time as HH:MM.")
    hour, minute, second = int(match[1]), int(match[2]), int(match[3] or 0)
    if hour > 23 or minute > 59 or second > 59:
        raise ValueError("Must be a time as HH:MM.")
    return time(hour, minute)


# Room hours, Cambodia local time. Accepts "8:00", "08:00" or "08:00:30" (seconds are
# dropped); "24:00" is refused. Always returned as "HH:MM".
LocalTime = Annotated[
    time,
    BeforeValidator(_parse_local_time),
    PlainSerializer(lambda value: value.strftime("%H:%M"), return_type=str, when_used="json"),
]


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
