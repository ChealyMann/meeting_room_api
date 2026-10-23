"""Roles: tasks 45-46, spec section 14, rule R17."""

from datetime import datetime

import pytest
from sqlalchemy import select

from app.constants.roles import RoleCode
from app.models import Role

URL = "/api/v1/roles"
ROLE_FIELDS = {"id", "code", "name_en", "name_kh", "is_active"}


def _error(response) -> tuple[int, str]:
    return response.status_code, response.json()["error"]["code"]


def _fields(response) -> dict:
    return response.json()["error"]["fields"]


@pytest.fixture
def roles(db_session) -> dict[str, Role]:
    """The six roles, inserted in reverse so the list order cannot come from the ids."""
    for code in reversed(RoleCode):
        db_session.add(Role(code=code, name_en=code.title(), name_kh=f"{code} kh"))
    db_session.flush()
    return {role.code: role for role in db_session.scalars(select(Role))}


@pytest.fixture
def admin_headers(roles, make_user, auth_headers):
    return auth_headers(make_user(roles=["ADMIN"]))


# --- Task 45: GET /roles ---------------------------------------------------------------


def test_list_roles(client, admin_headers, roles):
    response = client.get(URL, headers=admin_headers)
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"items", "total"}
    assert body["total"] == 6
    assert set(body["items"][0]) == ROLE_FIELDS
    admin = body["items"][0]
    assert admin == {
        "id": roles["ADMIN"].id,
        "code": "ADMIN",
        "name_en": "Admin",
        "name_kh": "ADMIN kh",
        "is_active": True,
    }


def test_list_in_seed_order(client, admin_headers, roles):
    codes = [item["code"] for item in client.get(URL, headers=admin_headers).json()["items"]]
    assert codes == ["ADMIN", "ROOM_OWNER", "STAFF", "PITIKA", "IT_LEAD", "IT_STAFF"]


def test_list_is_not_paged(client, admin_headers, roles):
    body = client.get(f"{URL}?page=2&size=1&is_active=false", headers=admin_headers).json()
    assert (len(body["items"]), body["total"]) == (6, 6)


@pytest.mark.parametrize("role", ["STAFF", "ROOM_OWNER", "PITIKA", "IT_LEAD", "IT_STAFF"])
def test_list_needs_admin(client, roles, make_user, auth_headers, role):
    headers = auth_headers(make_user(roles=[role]))
    assert _error(client.get(URL, headers=headers)) == (403, "FORBIDDEN")


def test_list_user_with_no_roles(client, roles, make_user, auth_headers):
    headers = auth_headers(make_user(roles=[]))
    assert _error(client.get(URL, headers=headers)) == (403, "FORBIDDEN")


def test_list_needs_a_token(client):
    assert _error(client.get(URL)) == (401, "UNAUTHORIZED")


def test_list_blocked_until_password_changed(client, roles, make_user, auth_headers):
    headers = auth_headers(make_user(roles=["ADMIN"], must_change_password=True))
    assert _error(client.get(URL, headers=headers)) == (403, "PASSWORD_CHANGE_REQUIRED")


def test_no_create(client, admin_headers):
    body = {"code": "MANAGER", "name_en": "Manager", "name_kh": "Manager"}
    assert _error(client.post(URL, json=body, headers=admin_headers)) == (
        405,
        "METHOD_NOT_ALLOWED",
    )


# --- Task 46: PATCH /roles/{id} --------------------------------------------------------


@pytest.fixture
def staff_role(roles, db_session) -> Role:
    role = roles["STAFF"]
    role.updated_at = datetime(2026, 1, 1)
    db_session.flush()
    return role


def patch(client, headers, role, body):
    return client.patch(f"{URL}/{role.id}", json=body, headers=headers)


def test_patch_names(client, admin_headers, staff_role, db_session):
    response = patch(
        client, admin_headers, staff_role, {"name_en": " Employee ", "name_kh": "បុគ្គលិក"}
    )
    assert response.status_code == 200
    assert response.json() == {
        "id": staff_role.id,
        "code": "STAFF",
        "name_en": "Employee",
        "name_kh": "បុគ្គលិក",
        "is_active": True,
    }
    db_session.refresh(staff_role)
    assert staff_role.updated_at != datetime(2026, 1, 1)


def test_patch_one_name(client, admin_headers, staff_role):
    body = patch(client, admin_headers, staff_role, {"name_kh": "បុគ្គលិក"}).json()
    assert (body["name_en"], body["name_kh"]) == ("Staff", "បុគ្គលិក")


def test_patch_empty_body(client, admin_headers, staff_role, db_session):
    response = patch(client, admin_headers, staff_role, {})
    assert response.status_code == 200
    assert response.json()["name_en"] == "Staff"
    db_session.refresh(staff_role)
    assert staff_role.updated_at == datetime(2026, 1, 1)


def test_patch_same_values(client, admin_headers, staff_role, db_session):
    patch(client, admin_headers, staff_role, {"name_en": "Staff"})
    db_session.refresh(staff_role)
    assert staff_role.updated_at == datetime(2026, 1, 1)


def test_two_roles_may_share_a_name(client, admin_headers, roles):
    response = patch(client, admin_headers, roles["IT_LEAD"], {"name_en": "Staff"})
    assert response.status_code == 200


@pytest.mark.parametrize(
    ("body", "field"),
    [
        ({"code": "MANAGER"}, "code"),
        ({"code": "STAFF"}, "code"),
        ({"is_active": False}, "is_active"),
        ({"id": 9}, "id"),
        ({"created_at": "2026-01-01T00:00:00Z"}, "created_at"),
    ],
)
def test_patch_refuses_code_status_and_server_fields(
    client, admin_headers, staff_role, db_session, body, field
):
    response = patch(client, admin_headers, staff_role, {**body, "name_en": "Changed"})
    assert _error(response) == (422, "VALIDATION_ERROR")
    assert _fields(response) == {field: "Unknown field."}
    db_session.refresh(staff_role)
    assert (staff_role.code, staff_role.name_en, staff_role.is_active) == ("STAFF", "Staff", True)


@pytest.mark.parametrize("field", ["name_en", "name_kh"])
@pytest.mark.parametrize(
    ("value", "message"),
    [
        (None, "This field is required."),
        ("  ", "This field is required."),
        ("x" * 101, "Too long (max 100)."),
    ],
)
def test_patch_invalid_names(client, admin_headers, staff_role, field, value, message):
    assert _fields(patch(client, admin_headers, staff_role, {field: value})) == {field: message}


def test_patch_khmer_name_of_100_characters(client, admin_headers, staff_role):
    response = patch(client, admin_headers, staff_role, {"name_kh": "ក" * 100})
    assert response.status_code == 200


def test_renamed_role_still_grants_access(client, admin_headers, roles):
    # Code checks the role code, never the display name.
    patch(client, admin_headers, roles["ADMIN"], {"name_en": "Superuser"})
    assert client.get(URL, headers=admin_headers).status_code == 200


def test_patch_unknown_role(client, admin_headers):
    response = client.patch(f"{URL}/999999", json={"name_en": "x"}, headers=admin_headers)
    assert _error(response) == (404, "NOT_FOUND")


@pytest.mark.parametrize("bad_id", ["abc", "0", "-1"])
def test_patch_bad_id(client, admin_headers, bad_id):
    response = client.patch(f"{URL}/{bad_id}", json={}, headers=admin_headers)
    assert _error(response) == (422, "VALIDATION_ERROR")


def test_patch_needs_admin(client, staff_role, make_user, auth_headers):
    headers = auth_headers(make_user(roles=["STAFF"]))
    assert _error(patch(client, headers, staff_role, {"name_en": "x"})) == (403, "FORBIDDEN")


def test_patch_needs_a_token(client, staff_role):
    response = client.patch(f"{URL}/{staff_role.id}", json={"name_en": "x"})
    assert _error(response) == (401, "UNAUTHORIZED")


@pytest.mark.parametrize("method", ["DELETE", "PUT", "GET"])
def test_method_not_allowed(client, admin_headers, staff_role, method):
    response = client.request(method, f"{URL}/{staff_role.id}", headers=admin_headers)
    assert _error(response) == (405, "METHOD_NOT_ALLOWED")
