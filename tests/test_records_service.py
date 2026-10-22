"""Shared create/update rules in app/services/records.py (R2, R3, R4)."""

import pytest
from sqlalchemy.exc import IntegrityError

from app.errors import AppError
from app.models import Building, Location, User
from app.services.records import (
    check_parent_active,
    get_or_404,
    get_reference,
    save,
)


def _raises(fn) -> AppError:
    with pytest.raises(AppError) as exc_info:
        fn()
    return exc_info.value


def test_get_or_404(db_session, make_location):
    location = make_location()
    assert get_or_404(db_session, Location, location.id) is location
    error = _raises(lambda: get_or_404(db_session, Location, 999_999))
    assert (error.status, error.code, error.message) == (404, "NOT_FOUND", "Not found.")


def test_reference_must_exist(db_session):
    error = _raises(lambda: get_reference(db_session, Location, 999_999, "location_id", "Office"))
    assert (error.status, error.code) == (422, "VALIDATION_ERROR")
    assert error.fields == {"location_id": "Office not found."}


def test_reference_must_be_active(db_session, make_location):
    location = make_location(is_active=False)
    error = _raises(
        lambda: get_reference(db_session, Location, location.id, "location_id", "Office")
    )
    assert (error.status, error.code) == (409, "INACTIVE_REFERENCE")
    assert error.fields == {"location_id": "This office is inactive."}


def test_active_reference_is_returned(db_session, make_location):
    location = make_location()
    assert get_reference(db_session, Location, location.id, "location_id", "Office") is location


def test_parent_must_be_active_to_reactivate(make_location):
    check_parent_active(make_location(), "Office")
    error = _raises(lambda: check_parent_active(make_location(is_active=False), "Office"))
    assert (error.status, error.code) == (409, "INACTIVE_REFERENCE")
    assert error.fields == {"is_active": "The office is inactive."}


def test_save_turns_duplicate_name_into_409(db_session, make_location):
    make_location(name_en="Head Office")
    db_session.add(Location(name_en="head office", name_kh="ក", province="KANDAL"))
    error = _raises(lambda: save(db_session))
    assert (error.status, error.code) == (409, "DUPLICATE")
    assert error.fields == {"name_en": "This name already exists."}


def test_save_reports_the_last_column_of_a_scoped_key(db_session, make_building):
    building = make_building(name_en="Building A")
    db_session.add(Building(location_id=building.location_id, name_en="BUILDING A", name_kh="ក"))
    assert _raises(lambda: save(db_session)).fields == {"name_en": "This name already exists."}


@pytest.mark.parametrize(
    ("field", "message"),
    [("email", "This email already exists."), ("staff_id", "This staff ID already exists.")],
)
def test_save_has_field_specific_messages(db_session, make_user, field, message):
    existing = make_user()
    values = {
        "staff_id": "NEW-1",
        "name_en": "x",
        "name_kh": "x",
        "email": "new@company.com",
        "password_hash": "x",
        "position_id": existing.position_id,
        field: getattr(existing, field).upper(),
    }
    db_session.add(User(**values))
    assert _raises(lambda: save(db_session)).fields == {field: message}


def test_save_lets_other_integrity_errors_through(db_session):
    db_session.add(Building(location_id=999_999, name_en="x", name_kh="x"))
    with pytest.raises(IntegrityError):
        save(db_session)


def test_save_commits(db_session):
    location = Location(name_en="Saved Office", name_kh="ក", province="KANDAL")
    db_session.add(location)
    save(db_session)
    assert location.id is not None
