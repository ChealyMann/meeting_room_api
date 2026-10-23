"""Divisions: tasks 41-44, spec section 14, rules R2, R3, R4."""

import re
from datetime import datetime

import pytest

URL = "/api/v1/divisions"
DIVISION_FIELDS = {
    "id",
    "department_id",
    "name_en",
    "name_kh",
    "short_name",
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
def department(make_department):
    return make_department(name_en="Operations")


def new(department, **overrides) -> dict:
    return {
        "department_id": department.id,
        "name_en": "IT Division",
        "name_kh": "ផ្នែកព័ត៌មានវិទ្យា",
        "short_name": "IT",
        "sort_order": 1,
        **overrides,
    }


# --- Task 41: POST /divisions ----------------------------------------------------------


def test_create_division(client, as_admin, department):
    response = client.post(URL, json=new(department), headers=as_admin)
    assert response.status_code == 201
    body = response.json()
    assert set(body) == DIVISION_FIELDS
    assert (body["department_id"], body["name_en"], body["name_kh"]) == (
        department.id,
        "IT Division",
        "ផ្នែកព័ត៌មានវិទ្យា",
    )
    assert (body["short_name"], body["sort_order"], body["is_active"]) == ("IT", 1, True)
    assert UTC_Z.fullmatch(body["created_at"]) and UTC_Z.fullmatch(body["updated_at"])


def test_create_defaults(client, as_admin, department):
    body = {"department_id": department.id, "name_en": "Audit", "name_kh": "សវនកម្ម"}
    response = client.post(URL, json=body, headers=as_admin).json()
    assert (response["short_name"], response["sort_order"]) == (None, 0)


def test_create_trims_and_blank_short_name_becomes_null(client, as_admin, department):
    body = new(department, name_en="  Audit ", short_name="   ")
    response = client.post(URL, json=body, headers=as_admin).json()
    assert (response["name_en"], response["short_name"]) == ("Audit", None)


def test_create_under_unknown_department(client, as_admin, department):
    response = client.post(URL, json=new(department, department_id=999_999), headers=as_admin)
    assert _error(response) == (422, "VALIDATION_ERROR")
    assert _fields(response) == {"department_id": "Department not found."}


def test_create_under_inactive_department(client, as_admin, make_department):
    department = make_department(is_active=False)
    response = client.post(URL, json=new(department), headers=as_admin)
    assert _error(response) == (409, "INACTIVE_REFERENCE")
    assert _fields(response) == {"department_id": "This department is inactive."}


def test_create_under_department_of_inactive_location(
    client, as_admin, make_location, make_department
):
    # Only the direct parent is checked (R2).
    department = make_department(location=make_location(is_active=False))
    assert client.post(URL, json=new(department), headers=as_admin).status_code == 201


@pytest.mark.parametrize("value", [0, -1, "abc", None])
def test_create_bad_department_id(client, as_admin, department, value):
    response = client.post(URL, json=new(department, department_id=value), headers=as_admin)
    assert set(_fields(response)) == {"department_id"}


@pytest.mark.parametrize("name", ["IT Division", "it division", "IT DIVISIÓN"])
def test_duplicate_name_in_same_department(client, as_admin, department, name):
    client.post(URL, json=new(department), headers=as_admin)
    response = client.post(URL, json=new(department, name_en=name), headers=as_admin)
    assert _error(response) == (409, "DUPLICATE")
    assert _fields(response) == {"name_en": "This name already exists."}


def test_same_name_in_another_department_is_allowed(client, as_admin, department, make_department):
    client.post(URL, json=new(department), headers=as_admin)
    assert client.post(URL, json=new(make_department()), headers=as_admin).status_code == 201


def test_same_short_name_is_allowed(client, as_admin, department):
    client.post(URL, json=new(department), headers=as_admin)
    response = client.post(URL, json=new(department, name_en="IT Support"), headers=as_admin)
    assert response.status_code == 201


@pytest.mark.parametrize(
    ("field", "limit"), [("name_en", 100), ("name_kh", 100), ("short_name", 20)]
)
def test_create_text_limits(client, as_admin, department, field, limit):
    ok = client.post(URL, json={**new(department), field: "ក" * limit}, headers=as_admin)
    assert ok.status_code == 201, ok.text
    too_long = client.post(
        URL, json={**new(department), field: "x" * (limit + 1)}, headers=as_admin
    )
    assert _fields(too_long) == {field: f"Too long (max {limit})."}


@pytest.mark.parametrize("field", ["name_en", "name_kh"])
def test_create_blank_name(client, as_admin, department, field):
    response = client.post(URL, json=new(department, **{field: ""}), headers=as_admin)
    assert _fields(response) == {field: "This field is required."}


@pytest.mark.parametrize("value", [-1, 10000, "abc"])
def test_create_bad_sort_order(client, as_admin, department, value):
    response = client.post(URL, json=new(department, sort_order=value), headers=as_admin)
    assert set(_fields(response)) == {"sort_order"}


def test_create_missing_required_fields(client, as_admin):
    assert set(_fields(client.post(URL, json={}, headers=as_admin))) == {
        "department_id",
        "name_en",
        "name_kh",
    }


@pytest.mark.parametrize("field", ["id", "is_active", "created_at", "updated_at", "location_id"])
def test_create_refuses_unknown_and_server_fields(client, as_admin, department, field):
    response = client.post(URL, json=new(department, **{field: 1}), headers=as_admin)
    assert _fields(response) == {field: "Unknown field."}


def test_create_needs_admin(client, as_staff, department):
    assert _error(client.post(URL, json=new(department), headers=as_staff)) == (403, "FORBIDDEN")


def test_create_needs_a_token(client, department):
    assert _error(client.post(URL, json=new(department))) == (401, "UNAUTHORIZED")


# --- Task 42: GET /divisions -----------------------------------------------------------


@pytest.fixture
def divisions(department, make_department, make_division):
    other = make_department(name_en="Finance")
    return {
        "it": make_division(
            department=department, name_en="IT Division", short_name="IT", sort_order=1
        ),
        "audit": make_division(department=department, name_en="Audit", sort_order=1),
        "hr": make_division(
            department=department, name_en="HR", name_kh="ធនធានមនុស្ស", short_name="PPL", sort_order=2
        ),
        "old": make_division(department=department, name_en="Typing pool", is_active=False),
        "other_it": make_division(department=other, name_en="IT Division", short_name="IT"),
        "percent": make_division(department=other, name_en="Sales 100%", sort_order=3),
        "under": make_division(department=other, name_en="Sales a_b", sort_order=3),
    }


def _names(response) -> list[str]:
    assert response.status_code == 200, response.text
    return [item["name_en"] for item in response.json()["items"]]


def test_list_shape(client, as_staff, divisions):
    body = client.get(URL, headers=as_staff).json()
    assert set(body) == {"items", "page", "size", "total"}
    assert set(body["items"][0]) == DIVISION_FIELDS


def test_list_by_department_in_order(client, as_staff, department, divisions):
    assert _names(client.get(f"{URL}?department_id={department.id}", headers=as_staff)) == [
        "Typing pool",
        "Audit",
        "IT Division",
        "HR",
    ]


def test_list_filter_active(client, as_staff, department, divisions):
    query = f"{URL}?department_id={department.id}&is_active=false"
    assert _names(client.get(query, headers=as_staff)) == ["Typing pool"]


@pytest.mark.parametrize(
    ("term", "expected"),
    [
        ("it division", ["IT Division", "IT Division"]),
        ("ppl", ["HR"]),
        ("ធនធាន", ["HR"]),
        ("100%", ["Sales 100%"]),
        ("a_b", ["Sales a_b"]),
        ("  audit  ", ["Audit"]),
    ],
)
def test_list_search(client, as_staff, divisions, term, expected):
    response = client.get(URL, params={"search": term, "size": 100}, headers=as_staff)
    mine = {division.name_en for division in divisions.values()}
    assert [name for name in _names(response) if name in mine] == expected


def test_list_search_inside_department(client, as_staff, department, divisions):
    params = {"search": "IT Div", "department_id": department.id}
    ids = [item["id"] for item in client.get(URL, params=params, headers=as_staff).json()["items"]]
    assert ids == [divisions["it"].id]


def test_list_blank_search_is_no_filter(client, as_staff, department, divisions):
    params = {"search": " ", "department_id": department.id}
    assert client.get(URL, params=params, headers=as_staff).json()["total"] == 4


def test_list_paging(client, as_staff, department, divisions):
    body = client.get(
        URL, params={"department_id": department.id, "size": 3, "page": 2}, headers=as_staff
    ).json()
    assert (body["page"], body["size"], body["total"]) == (2, 3, 4)
    assert [item["name_en"] for item in body["items"]] == ["HR"]


def test_list_page_past_the_end(client, as_staff, department, divisions):
    body = client.get(f"{URL}?department_id={department.id}&page=4", headers=as_staff).json()
    assert body["items"] == [] and body["total"] == 4


@pytest.mark.parametrize(
    ("query", "field"),
    [
        ("department_id=abc", "department_id"),
        ("department_id=-2", "department_id"),
        ("size=0", "size"),
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


# --- Task 43: GET /divisions/{id} ------------------------------------------------------


def test_get_division(client, as_staff, divisions, department):
    division = divisions["hr"]
    response = client.get(f"{URL}/{division.id}", headers=as_staff)
    assert response.status_code == 200
    body = response.json()
    assert set(body) == DIVISION_FIELDS
    assert (body["id"], body["department_id"], body["short_name"]) == (
        division.id,
        department.id,
        "PPL",
    )


def test_get_inactive_division(client, as_staff, divisions):
    assert client.get(f"{URL}/{divisions['old'].id}", headers=as_staff).json()["is_active"] is False


def test_get_unknown_division(client, as_staff):
    assert _error(client.get(f"{URL}/999999", headers=as_staff)) == (404, "NOT_FOUND")


@pytest.mark.parametrize("bad_id", ["abc", "0", "-1"])
def test_get_bad_id(client, as_staff, bad_id):
    assert _error(client.get(f"{URL}/{bad_id}", headers=as_staff)) == (422, "VALIDATION_ERROR")


def test_get_needs_a_token(client, divisions):
    assert _error(client.get(f"{URL}/{divisions['it'].id}")) == (401, "UNAUTHORIZED")


# --- Task 44: PATCH /divisions/{id} ----------------------------------------------------


@pytest.fixture
def division(department, make_division, db_session):
    division = make_division(
        department=department,
        name_en="IT Division",
        name_kh="ផ្នែក IT",
        short_name="IT",
        sort_order=1,
    )
    division.updated_at = datetime(2026, 1, 1)
    db_session.flush()
    return division


def patch(client, headers, division, body):
    return client.patch(f"{URL}/{division.id}", json=body, headers=headers)


def test_patch_changes_sent_fields(client, as_admin, division, department):
    body = patch(
        client, as_admin, division, {"name_en": "ICT Division", "short_name": "ICT"}
    ).json()
    assert set(body) == DIVISION_FIELDS
    assert (body["name_en"], body["short_name"], body["name_kh"], body["department_id"]) == (
        "ICT Division",
        "ICT",
        "ផ្នែក IT",
        department.id,
    )
    assert body["updated_at"] != "2026-01-01T00:00:00Z"


def test_patch_empty_body(client, as_admin, division):
    response = patch(client, as_admin, division, {})
    assert response.status_code == 200
    assert response.json()["updated_at"] == "2026-01-01T00:00:00Z"


def test_patch_same_values(client, as_admin, division, department):
    body = {"department_id": department.id, "short_name": "IT", "sort_order": 1}
    assert patch(client, as_admin, division, body).json()["updated_at"] == "2026-01-01T00:00:00Z"


@pytest.mark.parametrize("value", [None, "   "])
def test_patch_clears_short_name(client, as_admin, division, value):
    assert patch(client, as_admin, division, {"short_name": value}).json()["short_name"] is None


@pytest.mark.parametrize(
    "field", ["department_id", "name_en", "name_kh", "sort_order", "is_active"]
)
def test_patch_null_for_required(client, as_admin, division, field):
    assert _fields(patch(client, as_admin, division, {field: None})) == {
        field: "This field is required."
    }


@pytest.mark.parametrize(
    ("body", "field"),
    [
        ({"name_en": " "}, "name_en"),
        ({"short_name": "x" * 21}, "short_name"),
        ({"sort_order": 10000}, "sort_order"),
        ({"department_id": "abc"}, "department_id"),
    ],
)
def test_patch_invalid_values(client, as_admin, division, body, field):
    assert set(_fields(patch(client, as_admin, division, body))) == {field}


def test_patch_duplicate_name(client, as_admin, division, department, make_division, db_session):
    make_division(department=department, name_en="Audit")
    db_session.commit()  # like data from earlier requests: the 409's rollback keeps it
    response = patch(client, as_admin, division, {"name_en": "audit"})
    assert _error(response) == (409, "DUPLICATE")
    assert _fields(response) == {"name_en": "This name already exists."}
    db_session.refresh(division)
    assert division.name_en == "IT Division"


def test_move_to_another_department(client, as_admin, division, make_department):
    target = make_department()
    assert (
        patch(client, as_admin, division, {"department_id": target.id}).json()["department_id"]
        == target.id
    )


def test_move_into_department_with_same_name(
    client, as_admin, division, make_department, make_division
):
    target = make_department()
    make_division(department=target, name_en="IT Division")
    response = patch(client, as_admin, division, {"department_id": target.id})
    assert _error(response) == (409, "DUPLICATE")


def test_move_to_unknown_department(client, as_admin, division):
    response = patch(client, as_admin, division, {"department_id": 999_999})
    assert _fields(response) == {"department_id": "Department not found."}


def test_move_to_inactive_department(client, as_admin, division, make_department):
    target = make_department(is_active=False)
    response = patch(client, as_admin, division, {"department_id": target.id})
    assert _error(response) == (409, "INACTIVE_REFERENCE")
    assert _fields(response) == {"department_id": "This department is inactive."}


def test_deactivate_and_reactivate(client, as_admin, division):
    assert patch(client, as_admin, division, {"is_active": False}).json()["is_active"] is False
    assert patch(client, as_admin, division, {"is_active": True}).json()["is_active"] is True


def test_deactivate_division_with_users(client, as_admin, division, make_user, db_session):
    # Allowed; users keep it.
    user = make_user(division=division)
    assert patch(client, as_admin, division, {"is_active": False}).status_code == 200
    db_session.refresh(user)
    assert (user.division_id, user.is_active) == (division.id, True)


def test_reactivate_under_inactive_department(client, as_admin, division, department, db_session):
    division.is_active = False
    department.is_active = False
    db_session.flush()
    response = patch(client, as_admin, division, {"is_active": True})
    assert _error(response) == (409, "INACTIVE_REFERENCE")
    assert _fields(response) == {"is_active": "The department is inactive."}


def test_reactivate_while_moving_to_active_department(
    client, as_admin, division, department, make_department, db_session
):
    division.is_active = False
    department.is_active = False
    db_session.flush()
    target = make_department()
    body = patch(client, as_admin, division, {"is_active": True, "department_id": target.id}).json()
    assert (body["is_active"], body["department_id"]) == (True, target.id)


def test_edit_under_inactive_department_without_moving(
    client, as_admin, division, department, db_session
):
    department.is_active = False
    db_session.flush()
    body = {"name_en": "Renamed", "department_id": department.id}
    assert patch(client, as_admin, division, body).status_code == 200


def test_patch_unknown_division(client, as_admin):
    response = client.patch(f"{URL}/999999", json={"name_en": "x"}, headers=as_admin)
    assert _error(response) == (404, "NOT_FOUND")


@pytest.mark.parametrize("bad_id", ["abc", "0", "-1"])
def test_patch_bad_id(client, as_admin, bad_id):
    assert client.patch(f"{URL}/{bad_id}", json={}, headers=as_admin).status_code == 422


@pytest.mark.parametrize("field", ["id", "created_at", "updated_at"])
def test_patch_server_fields(client, as_admin, division, field):
    assert _fields(patch(client, as_admin, division, {field: 5})) == {field: "Unknown field."}


def test_patch_needs_admin(client, as_staff, division):
    assert _error(patch(client, as_staff, division, {"name_en": "x"})) == (403, "FORBIDDEN")


def test_patch_needs_a_token(client, division):
    assert _error(client.patch(f"{URL}/{division.id}", json={})) == (401, "UNAUTHORIZED")


@pytest.mark.parametrize("method", ["DELETE", "PUT"])
def test_method_not_allowed(client, as_admin, division, method):
    response = client.request(method, f"{URL}/{division.id}", headers=as_admin)
    assert _error(response) == (405, "METHOD_NOT_ALLOWED")
