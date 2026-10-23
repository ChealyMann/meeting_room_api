"""Positions (job titles): tasks 33-36, spec section 14, rule R4 (R2 is for users)."""

import re
from datetime import datetime

import pytest

URL = "/api/v1/positions"
POSITION_FIELDS = {
    "id",
    "name_en",
    "name_kh",
    "sort_order",
    "is_active",
    "created_at",
    "updated_at",
}
NEW = {"name_en": "Manager", "name_kh": "ប្រធាន", "sort_order": 1}
UTC_Z = re.compile(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ")


def _error(response) -> tuple[int, str]:
    return response.status_code, response.json()["error"]["code"]


def _fields(response) -> dict:
    return response.json()["error"]["fields"]


# --- Task 33: POST /positions ----------------------------------------------------------


def test_create_position(client, as_admin):
    response = client.post(URL, json=NEW, headers=as_admin)
    assert response.status_code == 201
    body = response.json()
    assert set(body) == POSITION_FIELDS
    assert (body["name_en"], body["name_kh"], body["sort_order"], body["is_active"]) == (
        "Manager",
        "ប្រធាន",
        1,
        True,
    )
    assert UTC_Z.fullmatch(body["created_at"]) and UTC_Z.fullmatch(body["updated_at"])


def test_create_default_sort_order(client, as_admin):
    response = client.post(URL, json={"name_en": "Clerk", "name_kh": "ស្មៀន"}, headers=as_admin)
    assert response.status_code == 201
    assert response.json()["sort_order"] == 0


def test_create_trims_names(client, as_admin):
    response = client.post(
        URL, json={**NEW, "name_en": " Officer  ", "name_kh": " មន្ត្រី "}, headers=as_admin
    )
    assert (response.json()["name_en"], response.json()["name_kh"]) == ("Officer", "មន្ត្រី")


@pytest.mark.parametrize("name", ["Manager", "manager", "MANAGER", "Mánager"])
def test_create_duplicate_name(client, as_admin, name):
    client.post(URL, json=NEW, headers=as_admin)
    response = client.post(URL, json={**NEW, "name_en": name}, headers=as_admin)
    assert _error(response) == (409, "DUPLICATE")
    assert _fields(response) == {"name_en": "This name already exists."}


def test_same_khmer_name_is_allowed(client, as_admin):
    client.post(URL, json=NEW, headers=as_admin)
    response = client.post(URL, json={**NEW, "name_en": "Head"}, headers=as_admin)
    assert response.status_code == 201


@pytest.mark.parametrize("field", ["name_en", "name_kh"])
def test_create_name_limits(client, as_admin, field):
    ok = client.post(URL, json={**NEW, "name_en": f"P {field}", field: "ក" * 100}, headers=as_admin)
    assert ok.status_code == 201, ok.text
    too_long = client.post(
        URL, json={**NEW, "name_en": f"Long {field}", field: "x" * 101}, headers=as_admin
    )
    assert _fields(too_long) == {field: "Too long (max 100)."}


@pytest.mark.parametrize("field", ["name_en", "name_kh"])
def test_create_blank_name(client, as_admin, field):
    response = client.post(URL, json={**NEW, field: "   "}, headers=as_admin)
    assert _fields(response) == {field: "This field is required."}


@pytest.mark.parametrize("value", [-1, 10000, "abc", None])
def test_create_bad_sort_order(client, as_admin, value):
    response = client.post(URL, json={**NEW, "sort_order": value}, headers=as_admin)
    assert _error(response) == (422, "VALIDATION_ERROR")
    assert set(_fields(response)) == {"sort_order"}


def test_create_missing_required_fields(client, as_admin):
    assert set(_fields(client.post(URL, json={}, headers=as_admin))) == {"name_en", "name_kh"}


@pytest.mark.parametrize("field", ["id", "is_active", "created_at", "updated_at", "name"])
def test_create_refuses_unknown_and_server_fields(client, as_admin, field):
    response = client.post(URL, json={**NEW, field: True}, headers=as_admin)
    assert _fields(response) == {field: "Unknown field."}


def test_create_needs_admin(client, as_staff):
    assert _error(client.post(URL, json=NEW, headers=as_staff)) == (403, "FORBIDDEN")


def test_create_needs_a_token(client):
    assert _error(client.post(URL, json=NEW)) == (401, "UNAUTHORIZED")


# --- Task 34: GET /positions -----------------------------------------------------------


@pytest.fixture
def positions(make_position):
    return {
        "manager": make_position(name_en="Manager", name_kh="ប្រធាន", sort_order=1),
        "deputy": make_position(name_en="Deputy manager", name_kh="អនុប្រធាន", sort_order=2),
        "clerk": make_position(name_en="Clerk", name_kh="ស្មៀន", sort_order=1),
        "old": make_position(name_en="Typist", name_kh="អ្នកវាយអក្សរ", is_active=False),
        "percent": make_position(name_en="Staff 50%", name_kh="បុគ្គលិក", sort_order=5),
        "under": make_position(name_en="Staff a_b", name_kh="បុគ្គលិក ab", sort_order=5),
    }


def _names(response) -> list[str]:
    assert response.status_code == 200, response.text
    return [item["name_en"] for item in response.json()["items"]]


def _ours(names: list[str], positions: dict) -> list[str]:
    mine = {position.name_en for position in positions.values()}
    return [name for name in names if name in mine]


def test_list_shape(client, as_staff, positions):
    body = client.get(URL, headers=as_staff).json()
    assert set(body) == {"items", "page", "size", "total"}
    assert set(body["items"][0]) == POSITION_FIELDS


def test_list_order(client, as_staff, positions):
    assert _ours(_names(client.get(f"{URL}?size=100", headers=as_staff)), positions) == [
        "Typist",
        "Clerk",
        "Manager",
        "Deputy manager",
        "Staff 50%",
        "Staff a_b",
    ]


def test_list_filter_active(client, as_staff, positions):
    active = _names(client.get(f"{URL}?is_active=true&size=100", headers=as_staff))
    inactive = _names(client.get(f"{URL}?is_active=false&size=100", headers=as_staff))
    assert "Typist" not in active and "Manager" in active
    assert "Typist" in inactive and "Manager" not in inactive


@pytest.mark.parametrize(
    ("term", "expected"),
    [
        ("manager", ["Manager", "Deputy manager"]),
        ("អនុ", ["Deputy manager"]),
        ("50%", ["Staff 50%"]),
        ("a_b", ["Staff a_b"]),
        (" typist ", ["Typist"]),
    ],
)
def test_list_search(client, as_staff, positions, term, expected):
    response = client.get(URL, params={"search": term, "size": 100}, headers=as_staff)
    assert _ours(_names(response), positions) == expected


def test_list_blank_search_is_no_filter(client, as_staff, positions):
    everything = client.get(URL, headers=as_staff).json()["total"]
    assert client.get(URL, params={"search": "  "}, headers=as_staff).json()["total"] == everything


def test_list_paging(client, as_staff, make_position):
    for n in range(3):
        make_position(name_en=f"Zz Paging {n}")
    body = client.get(
        URL, params={"search": "Zz Paging", "size": 2, "page": 2}, headers=as_staff
    ).json()
    assert (body["page"], body["size"], body["total"]) == (2, 2, 3)
    assert [item["name_en"] for item in body["items"]] == ["Zz Paging 2"]


def test_list_page_past_the_end(client, as_staff, positions):
    body = client.get(URL, params={"search": "Clerk", "page": 3}, headers=as_staff).json()
    assert body["items"] == [] and body["total"] == 1


@pytest.mark.parametrize(
    ("query", "field"),
    [("size=0", "size"), ("size=101", "size"), ("page=0", "page"), ("is_active=x", "is_active")],
)
def test_list_bad_query(client, as_staff, query, field):
    response = client.get(f"{URL}?{query}", headers=as_staff)
    assert _error(response) == (422, "VALIDATION_ERROR")
    assert set(_fields(response)) == {field}


def test_list_needs_a_token(client):
    assert _error(client.get(URL)) == (401, "UNAUTHORIZED")


# --- Task 35: GET /positions/{id} ------------------------------------------------------


def test_get_position(client, as_staff, positions):
    position = positions["deputy"]
    response = client.get(f"{URL}/{position.id}", headers=as_staff)
    assert response.status_code == 200
    assert set(response.json()) == POSITION_FIELDS
    assert (response.json()["id"], response.json()["name_kh"]) == (position.id, "អនុប្រធាន")


def test_get_inactive_position(client, as_staff, positions):
    assert client.get(f"{URL}/{positions['old'].id}", headers=as_staff).json()["is_active"] is False


def test_get_unknown_position(client, as_staff):
    assert _error(client.get(f"{URL}/999999", headers=as_staff)) == (404, "NOT_FOUND")


@pytest.mark.parametrize("bad_id", ["abc", "0", "-1"])
def test_get_bad_id(client, as_staff, bad_id):
    assert _error(client.get(f"{URL}/{bad_id}", headers=as_staff)) == (422, "VALIDATION_ERROR")


def test_get_needs_a_token(client, positions):
    assert _error(client.get(f"{URL}/{positions['clerk'].id}")) == (401, "UNAUTHORIZED")


# --- Task 36: PATCH /positions/{id} ----------------------------------------------------


@pytest.fixture
def position(make_position, db_session):
    position = make_position(name_en="Manager", name_kh="ប្រធាន", sort_order=1)
    position.updated_at = datetime(2026, 1, 1)
    db_session.flush()
    return position


def patch(client, headers, position, body):
    return client.patch(f"{URL}/{position.id}", json=body, headers=headers)


def test_patch_changes_sent_fields(client, as_admin, position):
    body = patch(client, as_admin, position, {"name_en": "Senior manager", "sort_order": 3}).json()
    assert set(body) == POSITION_FIELDS
    assert (body["name_en"], body["name_kh"], body["sort_order"]) == ("Senior manager", "ប្រធាន", 3)
    assert body["updated_at"] != "2026-01-01T00:00:00Z"


def test_patch_empty_body(client, as_admin, position):
    response = patch(client, as_admin, position, {})
    assert response.status_code == 200
    assert response.json()["updated_at"] == "2026-01-01T00:00:00Z"


def test_patch_same_values(client, as_admin, position):
    body = {"name_en": "Manager", "name_kh": "ប្រធាន", "sort_order": 1}
    assert patch(client, as_admin, position, body).json()["updated_at"] == "2026-01-01T00:00:00Z"


def test_patch_own_name_in_another_case(client, as_admin, position):
    assert patch(client, as_admin, position, {"name_en": "MANAGER"}).status_code == 200


@pytest.mark.parametrize("field", ["name_en", "name_kh", "sort_order", "is_active"])
def test_patch_null_for_required(client, as_admin, position, field):
    assert _fields(patch(client, as_admin, position, {field: None})) == {
        field: "This field is required."
    }


@pytest.mark.parametrize(
    ("body", "field"),
    [
        ({"name_en": ""}, "name_en"),
        ({"name_kh": "x" * 101}, "name_kh"),
        ({"sort_order": -1}, "sort_order"),
        ({"is_active": "x"}, "is_active"),
    ],
)
def test_patch_invalid_values(client, as_admin, position, body, field):
    assert set(_fields(patch(client, as_admin, position, body))) == {field}


def test_patch_duplicate_name(client, as_admin, position, make_position, db_session):
    make_position(name_en="Clerk")
    db_session.commit()  # like data from earlier requests: the 409's rollback keeps it
    response = patch(client, as_admin, position, {"name_en": "CLERK"})
    assert _error(response) == (409, "DUPLICATE")
    assert _fields(response) == {"name_en": "This name already exists."}
    db_session.refresh(position)
    assert position.name_en == "Manager"


def test_deactivate_and_reactivate(client, as_admin, position):
    assert patch(client, as_admin, position, {"is_active": False}).json()["is_active"] is False
    assert patch(client, as_admin, position, {"is_active": True}).json()["is_active"] is True


def test_deactivate_position_with_users(client, as_admin, position, make_user, db_session):
    user = make_user(position=position)
    assert patch(client, as_admin, position, {"is_active": False}).status_code == 200
    db_session.refresh(user)
    assert (user.position_id, user.is_active) == (position.id, True)


def test_patch_unknown_position(client, as_admin):
    response = client.patch(f"{URL}/999999", json={"name_en": "x"}, headers=as_admin)
    assert _error(response) == (404, "NOT_FOUND")


@pytest.mark.parametrize("bad_id", ["abc", "0", "-1"])
def test_patch_bad_id(client, as_admin, bad_id):
    assert client.patch(f"{URL}/{bad_id}", json={}, headers=as_admin).status_code == 422


@pytest.mark.parametrize("field", ["id", "created_at", "updated_at"])
def test_patch_server_fields(client, as_admin, position, field):
    assert _fields(patch(client, as_admin, position, {field: 5})) == {field: "Unknown field."}


def test_patch_needs_admin(client, as_staff, position):
    assert _error(patch(client, as_staff, position, {"name_en": "x"})) == (403, "FORBIDDEN")


def test_patch_needs_a_token(client, position):
    assert _error(client.patch(f"{URL}/{position.id}", json={})) == (401, "UNAUTHORIZED")


@pytest.mark.parametrize("method", ["DELETE", "PUT"])
def test_method_not_allowed(client, as_admin, position, method):
    response = client.request(method, f"{URL}/{position.id}", headers=as_admin)
    assert _error(response) == (405, "METHOD_NOT_ALLOWED")
