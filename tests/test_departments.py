"""Departments: tasks 37-40, spec section 14, rules R2, R3, R4."""

import re
from datetime import datetime

import pytest

from app.services.province import get_user_province

URL = "/api/v1/departments"
DEPARTMENT_FIELDS = {
    "id",
    "location_id",
    "name_en",
    "name_kh",
    "sort_order",
    "is_active",
    "created_at",
    "updated_at",
}
UTC_Z = re.compile(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ")


def _error(response) -> tuple[int, str]:
    return response.status_code, response.json()["error"]["code"]


def _fields(response) -> dict:
    return response.json()["error"]["fields"]


@pytest.fixture
def office(make_location):
    return make_location(name_en="Head Office", province="PHNOM_PENH")


def new(office, **overrides) -> dict:
    return {
        "location_id": office.id,
        "name_en": "Operations",
        "name_kh": "ប្រតិបត្តិការ",
        "sort_order": 1,
        **overrides,
    }


# --- Task 37: POST /departments --------------------------------------------------------


def test_create_department(client, as_admin, office):
    response = client.post(URL, json=new(office), headers=as_admin)
    assert response.status_code == 201
    body = response.json()
    assert set(body) == DEPARTMENT_FIELDS
    assert (body["location_id"], body["name_en"], body["name_kh"], body["sort_order"]) == (
        office.id,
        "Operations",
        "ប្រតិបត្តិការ",
        1,
    )
    assert body["is_active"] is True
    assert UTC_Z.fullmatch(body["created_at"]) and UTC_Z.fullmatch(body["updated_at"])


def test_create_default_sort_order(client, as_admin, office):
    body = {"location_id": office.id, "name_en": "Finance", "name_kh": "ហិរញ្ញវត្ថុ"}
    assert client.post(URL, json=body, headers=as_admin).json()["sort_order"] == 0


def test_create_trims_names(client, as_admin, office):
    body = new(office, name_en="  Finance ", name_kh=" ហិរញ្ញវត្ថុ ")
    response = client.post(URL, json=body, headers=as_admin).json()
    assert (response["name_en"], response["name_kh"]) == ("Finance", "ហិរញ្ញវត្ថុ")


def test_create_under_unknown_location(client, as_admin, office):
    response = client.post(URL, json=new(office, location_id=999_999), headers=as_admin)
    assert _error(response) == (422, "VALIDATION_ERROR")
    assert _fields(response) == {"location_id": "Office not found."}


def test_create_under_inactive_location(client, as_admin, make_location):
    response = client.post(URL, json=new(make_location(is_active=False)), headers=as_admin)
    assert _error(response) == (409, "INACTIVE_REFERENCE")
    assert _fields(response) == {"location_id": "This office is inactive."}


@pytest.mark.parametrize("value", [0, -1, "abc", None, 1.5])
def test_create_bad_location_id(client, as_admin, office, value):
    response = client.post(URL, json=new(office, location_id=value), headers=as_admin)
    assert _error(response) == (422, "VALIDATION_ERROR")
    assert set(_fields(response)) == {"location_id"}


@pytest.mark.parametrize("name", ["Operations", "operations", "OPERATIONS", "Operatións"])
def test_duplicate_name_in_same_location(client, as_admin, office, name):
    client.post(URL, json=new(office), headers=as_admin)
    response = client.post(URL, json=new(office, name_en=name), headers=as_admin)
    assert _error(response) == (409, "DUPLICATE")
    assert _fields(response) == {"name_en": "This name already exists."}


def test_same_name_in_another_location_is_allowed(client, as_admin, office, make_location):
    client.post(URL, json=new(office), headers=as_admin)
    assert client.post(URL, json=new(make_location()), headers=as_admin).status_code == 201


@pytest.mark.parametrize("field", ["name_en", "name_kh"])
def test_create_name_limits(client, as_admin, office, field):
    ok = client.post(URL, json={**new(office), field: "ក" * 100}, headers=as_admin)
    assert ok.status_code == 201, ok.text
    too_long = client.post(URL, json=new(office, **{field: "x" * 101}), headers=as_admin)
    assert _fields(too_long) == {field: "Too long (max 100)."}


@pytest.mark.parametrize("field", ["name_en", "name_kh"])
def test_create_blank_name(client, as_admin, office, field):
    response = client.post(URL, json=new(office, **{field: "  "}), headers=as_admin)
    assert _fields(response) == {field: "This field is required."}


@pytest.mark.parametrize("value", [-1, 10000, "abc"])
def test_create_bad_sort_order(client, as_admin, office, value):
    response = client.post(URL, json=new(office, sort_order=value), headers=as_admin)
    assert set(_fields(response)) == {"sort_order"}


def test_create_missing_required_fields(client, as_admin):
    assert set(_fields(client.post(URL, json={}, headers=as_admin))) == {
        "location_id",
        "name_en",
        "name_kh",
    }


@pytest.mark.parametrize("field", ["id", "is_active", "created_at", "updated_at", "short_name"])
def test_create_refuses_unknown_and_server_fields(client, as_admin, office, field):
    response = client.post(URL, json=new(office, **{field: True}), headers=as_admin)
    assert _fields(response) == {field: "Unknown field."}


def test_create_needs_admin(client, as_staff, office):
    assert _error(client.post(URL, json=new(office), headers=as_staff)) == (403, "FORBIDDEN")


def test_create_needs_a_token(client, office):
    assert _error(client.post(URL, json=new(office))) == (401, "UNAUTHORIZED")


# --- Task 38: GET /departments ---------------------------------------------------------


@pytest.fixture
def departments(office, make_location, make_department):
    elsewhere = make_location(name_en="Branch", province="KAMPOT")
    return {
        "ops": make_department(location=office, name_en="Operations", sort_order=1),
        "fin": make_department(location=office, name_en="Finance", name_kh="ហិរញ្ញវត្ថុ", sort_order=1),
        "hr": make_department(location=office, name_en="Human resources", sort_order=2),
        "old": make_department(location=office, name_en="Archive", is_active=False),
        "branch_ops": make_department(location=elsewhere, name_en="Operations", sort_order=1),
        "percent": make_department(location=elsewhere, name_en="Sales 100%", sort_order=3),
        "under": make_department(location=elsewhere, name_en="Sales a_b", sort_order=3),
    }


def _names(response) -> list[str]:
    assert response.status_code == 200, response.text
    return [item["name_en"] for item in response.json()["items"]]


def test_list_shape(client, as_staff, departments):
    body = client.get(URL, headers=as_staff).json()
    assert set(body) == {"items", "page", "size", "total"}
    assert set(body["items"][0]) == DEPARTMENT_FIELDS


def test_list_by_location_in_order(client, as_staff, office, departments):
    # sort_order, then English name, then id
    assert _names(client.get(f"{URL}?location_id={office.id}", headers=as_staff)) == [
        "Archive",
        "Finance",
        "Operations",
        "Human resources",
    ]


def test_list_filter_active(client, as_staff, office, departments):
    query = f"{URL}?location_id={office.id}&is_active=false"
    assert _names(client.get(query, headers=as_staff)) == ["Archive"]
    query = f"{URL}?location_id={office.id}&is_active=true"
    assert "Archive" not in _names(client.get(query, headers=as_staff))


@pytest.mark.parametrize(
    ("term", "expected"),
    [
        ("operations", ["Operations", "Operations"]),
        ("ហិរញ្ញ", ["Finance"]),
        ("100%", ["Sales 100%"]),
        ("a_b", ["Sales a_b"]),
        ("  archive ", ["Archive"]),
    ],
)
def test_list_search(client, as_staff, departments, term, expected):
    response = client.get(URL, params={"search": term, "size": 100}, headers=as_staff)
    mine = {department.name_en for department in departments.values()}
    assert [name for name in _names(response) if name in mine] == expected


def test_list_search_inside_location(client, as_staff, office, departments):
    params = {"search": "operations", "location_id": office.id}
    response = client.get(URL, params=params, headers=as_staff)
    assert [item["id"] for item in response.json()["items"]] == [departments["ops"].id]


def test_list_blank_search_is_no_filter(client, as_staff, office, departments):
    params = {"search": "   ", "location_id": office.id}
    assert client.get(URL, params=params, headers=as_staff).json()["total"] == 4


def test_list_unknown_location_is_empty(client, as_staff, departments):
    body = client.get(f"{URL}?location_id=999999", headers=as_staff).json()
    assert (body["items"], body["total"]) == ([], 0)


def test_list_paging(client, as_staff, office, departments):
    query = f"{URL}?location_id={office.id}&size=3&page=2"
    body = client.get(query, headers=as_staff).json()
    assert (body["page"], body["size"], body["total"]) == (2, 3, 4)
    assert [item["name_en"] for item in body["items"]] == ["Human resources"]


def test_list_page_past_the_end(client, as_staff, office, departments):
    body = client.get(f"{URL}?location_id={office.id}&page=9", headers=as_staff).json()
    assert body["items"] == [] and body["total"] == 4


@pytest.mark.parametrize(
    ("query", "field"),
    [
        ("location_id=abc", "location_id"),
        ("location_id=0", "location_id"),
        ("size=101", "size"),
        ("page=0", "page"),
        ("is_active=x", "is_active"),
    ],
)
def test_list_bad_query(client, as_staff, query, field):
    response = client.get(f"{URL}?{query}", headers=as_staff)
    assert _error(response) == (422, "VALIDATION_ERROR")
    assert set(_fields(response)) == {field}


def test_list_needs_a_token(client):
    assert _error(client.get(URL)) == (401, "UNAUTHORIZED")


# --- Task 39: GET /departments/{id} ----------------------------------------------------


def test_get_department(client, as_staff, departments, office):
    department = departments["fin"]
    response = client.get(f"{URL}/{department.id}", headers=as_staff)
    assert response.status_code == 200
    body = response.json()
    assert set(body) == DEPARTMENT_FIELDS
    assert (body["id"], body["location_id"], body["name_kh"]) == (
        department.id,
        office.id,
        "ហិរញ្ញវត្ថុ",
    )


def test_get_inactive_department(client, as_staff, departments):
    response = client.get(f"{URL}/{departments['old'].id}", headers=as_staff)
    assert response.json()["is_active"] is False


def test_get_unknown_department(client, as_staff):
    assert _error(client.get(f"{URL}/999999", headers=as_staff)) == (404, "NOT_FOUND")


@pytest.mark.parametrize("bad_id", ["abc", "0", "-1"])
def test_get_bad_id(client, as_staff, bad_id):
    assert _error(client.get(f"{URL}/{bad_id}", headers=as_staff)) == (422, "VALIDATION_ERROR")


def test_get_needs_a_token(client, departments):
    assert _error(client.get(f"{URL}/{departments['ops'].id}")) == (401, "UNAUTHORIZED")


# --- Task 40: PATCH /departments/{id} --------------------------------------------------


@pytest.fixture
def department(office, make_department, db_session):
    department = make_department(
        location=office, name_en="Operations", name_kh="ប្រតិបត្តិការ", sort_order=1
    )
    department.updated_at = datetime(2026, 1, 1)
    db_session.flush()
    return department


def patch(client, headers, department, body):
    return client.patch(f"{URL}/{department.id}", json=body, headers=headers)


def test_patch_changes_sent_fields(client, as_admin, department, office):
    body = patch(client, as_admin, department, {"name_en": "Ops", "sort_order": 4}).json()
    assert set(body) == DEPARTMENT_FIELDS
    assert (body["name_en"], body["name_kh"], body["sort_order"], body["location_id"]) == (
        "Ops",
        "ប្រតិបត្តិការ",
        4,
        office.id,
    )
    assert body["updated_at"] != "2026-01-01T00:00:00Z"


def test_patch_empty_body(client, as_admin, department):
    response = patch(client, as_admin, department, {})
    assert response.status_code == 200
    assert response.json()["updated_at"] == "2026-01-01T00:00:00Z"


def test_patch_same_values(client, as_admin, department, office):
    body = {"location_id": office.id, "name_en": "Operations", "sort_order": 1}
    assert patch(client, as_admin, department, body).json()["updated_at"] == "2026-01-01T00:00:00Z"


@pytest.mark.parametrize("field", ["location_id", "name_en", "name_kh", "sort_order", "is_active"])
def test_patch_null_for_required(client, as_admin, department, field):
    assert _fields(patch(client, as_admin, department, {field: None})) == {
        field: "This field is required."
    }


@pytest.mark.parametrize(
    ("body", "field"),
    [
        ({"name_en": " "}, "name_en"),
        ({"name_kh": "x" * 101}, "name_kh"),
        ({"sort_order": 10000}, "sort_order"),
        ({"location_id": 0}, "location_id"),
        ({"is_active": "x"}, "is_active"),
    ],
)
def test_patch_invalid_values(client, as_admin, department, body, field):
    assert set(_fields(patch(client, as_admin, department, body))) == {field}


def test_patch_duplicate_name(client, as_admin, department, office, make_department, db_session):
    make_department(location=office, name_en="Finance")
    db_session.commit()  # like data from earlier requests: the 409's rollback keeps it
    response = patch(client, as_admin, department, {"name_en": "FINANCE"})
    assert _error(response) == (409, "DUPLICATE")
    assert _fields(response) == {"name_en": "This name already exists."}
    db_session.refresh(department)
    assert department.name_en == "Operations"


def test_move_into_location_with_same_name(
    client, as_admin, department, make_location, make_department
):
    target = make_location()
    make_department(location=target, name_en="Operations")
    response = patch(client, as_admin, department, {"location_id": target.id})
    assert _error(response) == (409, "DUPLICATE")


def test_move_changes_province_of_users(
    client, as_admin, department, make_location, make_division, make_user, db_session
):
    user = make_user(division=make_division(department=department))
    assert get_user_province(user).code == "PHNOM_PENH"
    target = make_location(province="SIEM_REAP")
    response = patch(client, as_admin, department, {"location_id": target.id})
    assert response.json()["location_id"] == target.id
    db_session.expire_all()
    assert get_user_province(user).code == "SIEM_REAP"


def test_move_to_unknown_location(client, as_admin, department):
    response = patch(client, as_admin, department, {"location_id": 999_999})
    assert _error(response) == (422, "VALIDATION_ERROR")
    assert _fields(response) == {"location_id": "Office not found."}


def test_move_to_inactive_location(client, as_admin, department, make_location):
    response = patch(
        client, as_admin, department, {"location_id": make_location(is_active=False).id}
    )
    assert _error(response) == (409, "INACTIVE_REFERENCE")
    assert _fields(response) == {"location_id": "This office is inactive."}


def test_deactivate_and_reactivate(client, as_admin, department):
    assert patch(client, as_admin, department, {"is_active": False}).json()["is_active"] is False
    assert patch(client, as_admin, department, {"is_active": True}).json()["is_active"] is True


def test_deactivate_keeps_divisions_active(client, as_admin, department, make_division, db_session):
    division = make_division(department=department)
    assert patch(client, as_admin, department, {"is_active": False}).status_code == 200
    db_session.refresh(division)
    assert division.is_active is True


def test_reactivate_under_inactive_location(client, as_admin, department, office, db_session):
    department.is_active = False
    office.is_active = False
    db_session.flush()
    response = patch(client, as_admin, department, {"is_active": True})
    assert _error(response) == (409, "INACTIVE_REFERENCE")
    assert _fields(response) == {"is_active": "The office is inactive."}


def test_reactivate_while_moving_to_active_location(
    client, as_admin, department, office, make_location, db_session
):
    department.is_active = False
    office.is_active = False
    db_session.flush()
    target = make_location()
    body = patch(client, as_admin, department, {"is_active": True, "location_id": target.id}).json()
    assert (body["is_active"], body["location_id"]) == (True, target.id)


def test_edit_under_inactive_location_without_moving(
    client, as_admin, department, office, db_session
):
    # R2 only checks a reference that changes.
    office.is_active = False
    db_session.flush()
    body = {"name_en": "Renamed", "location_id": office.id}
    assert patch(client, as_admin, department, body).status_code == 200


def test_deactivate_under_inactive_location(client, as_admin, department, office, db_session):
    office.is_active = False
    db_session.flush()
    assert patch(client, as_admin, department, {"is_active": False}).status_code == 200


def test_patch_unknown_department(client, as_admin):
    response = client.patch(f"{URL}/999999", json={"name_en": "x"}, headers=as_admin)
    assert _error(response) == (404, "NOT_FOUND")


@pytest.mark.parametrize("bad_id", ["abc", "0", "-1"])
def test_patch_bad_id(client, as_admin, bad_id):
    assert client.patch(f"{URL}/{bad_id}", json={}, headers=as_admin).status_code == 422


@pytest.mark.parametrize("field", ["id", "created_at", "updated_at"])
def test_patch_server_fields(client, as_admin, department, field):
    assert _fields(patch(client, as_admin, department, {field: 5})) == {field: "Unknown field."}


def test_patch_needs_admin(client, as_staff, department):
    assert _error(patch(client, as_staff, department, {"name_en": "x"})) == (403, "FORBIDDEN")


def test_patch_needs_a_token(client, department):
    assert _error(client.patch(f"{URL}/{department.id}", json={})) == (401, "UNAUTHORIZED")


@pytest.mark.parametrize("method", ["DELETE", "PUT"])
def test_method_not_allowed(client, as_admin, department, method):
    response = client.request(method, f"{URL}/{department.id}", headers=as_admin)
    assert _error(response) == (405, "METHOD_NOT_ALLOWED")
