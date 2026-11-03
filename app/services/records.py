"""Rules every create and update shares (spec sections 4 and 15). No FastAPI imports.

- `get_or_404`: the record in the path, or 404 NOT_FOUND.
- `get_reference` (R2): a record linked by id must exist (else 422 on that field) and be
  active (else 409 INACTIVE_REFERENCE).
- `check_parent_active` (R3): a record cannot be turned on again under an inactive parent.
- `check_and_bump_version`: the version a person saw must still be current (STALE_VERSION).
- `save` (R4): flush and commit; a unique-key clash becomes 409 DUPLICATE on its field.
  The database's unique keys (case- and accent-insensitive) are the single source of
  truth, which also covers two requests racing to create the same name.
"""

import re

from sqlalchemy import UniqueConstraint
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.errors import AppError, ErrorCode
from app.models import Base

_ER_DUP_ENTRY = 1062
_DUPLICATE_KEY = re.compile(r"for key '(?:[^'.]+\.)?([^']+)'")

# Field-specific messages; anything else gets "This name already exists."
_DUPLICATE_MESSAGES = {
    "floor_label": "This floor already exists.",
    "email": "This email already exists.",
    "staff_id": "This staff ID already exists.",
    "holiday_date": "This date already has a holiday.",
}


def _unique_key_fields() -> dict[str, str]:
    """Unique key name -> the field to report (its last column, e.g. `name_en`)."""
    fields = {}
    for table in Base.metadata.tables.values():
        for constraint in table.constraints:
            if isinstance(constraint, UniqueConstraint) and constraint.name:
                fields[constraint.name] = list(constraint.columns)[-1].name
    return fields


_UNIQUE_KEY_FIELDS = _unique_key_fields()


def not_found() -> AppError:
    return AppError(ErrorCode.NOT_FOUND, 404, "Not found.")


def get_or_404(session: Session, model, record_id: int, *, lock: bool = False):
    """`lock=True` reads the row with FOR UPDATE and fresh values, so a second request
    for the same row waits until the first one commits."""
    if lock:
        record = session.get(model, record_id, with_for_update=True, populate_existing=True)
    else:
        record = session.get(model, record_id)
    if record is None:
        raise not_found()
    return record


def get_reference(session: Session, model, record_id: int, field: str, label: str):
    """R2. `label` names the record for people, e.g. "Office" or "Building"."""
    record = session.get(model, record_id)
    if record is None:
        raise AppError(
            ErrorCode.VALIDATION_ERROR, 422, "Invalid request.", {field: f"{label} not found."}
        )
    if not record.is_active:
        message = f"This {label.lower()} is inactive."
        raise AppError(ErrorCode.INACTIVE_REFERENCE, 409, message, {field: message})
    return record


def check_parent_active(parent, label: str) -> None:
    """R3: call when `is_active` goes from false to true."""
    if not parent.is_active:
        message = f"The {label.lower()} is inactive."
        raise AppError(ErrorCode.INACTIVE_REFERENCE, 409, message, {"is_active": message})


def check_and_bump_version(
    record, version: int, message: str = "This item changed. Reload it."
) -> None:
    """Optimistic lock: `version` is what the person saw. Load the record with
    `get_or_404(..., lock=True)` first, so the check and the bump are one step."""
    if record.version != version:
        raise AppError(ErrorCode.STALE_VERSION, 409, message)
    record.version += 1


def apply_changes(record, changes: dict) -> None:
    for field, value in changes.items():
        setattr(record, field, value)


def save(session: Session) -> None:
    """Flush and commit. A unique-key clash becomes 409 DUPLICATE on the clashing field."""
    try:
        session.flush()
    except IntegrityError as exc:
        session.rollback()
        field = _duplicate_field(exc)
        if field is None:
            raise
        message = _DUPLICATE_MESSAGES.get(field, "This name already exists.")
        raise AppError(ErrorCode.DUPLICATE, 409, message, {field: message}) from None
    session.commit()


def _duplicate_field(exc: IntegrityError) -> str | None:
    args = getattr(exc.orig, "args", ())
    if len(args) < 2 or args[0] != _ER_DUP_ENTRY:
        return None
    match = _DUPLICATE_KEY.search(str(args[1]))
    return _UNIQUE_KEY_FIELDS.get(match.group(1)) if match else None
