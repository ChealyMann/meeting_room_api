"""Categories (room types): tasks 25-28, spec section 12, rules R2 (for rooms), R4."""

import re
from datetime import datetime

import pytest

URL = "/api/v1/categories"
CATEGORY_FIELDS = {
    "id",
    "name_en",
    "name_kh",
    "sort_order",
    "is_active",
    "created_at",
    "updated_at",
}
NEW = {"name_en": "Training room", "name_kh": "បន្ទប់បណ្ដុះបណ្ដាល", "sort_order": 2}
UTC_Z = re.compile(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ")


def _error(response) -> tuple[int, str]:
    return response.status_code, response.json()["error"]["code"]


def _fields(response) -> dict:
    return response.json()["error"]["fields"]


# --- Task 25: POST /categories ---------------------------------------------------------


def test_create_category(client, as_admin):
    response = client.post(URL, json=NEW, headers=as_admin)
    assert response.status_code == 201
    body = response.json()
    assert set(body) == CATEGORY_FIELDS
    assert (body["name_en"], body["name_kh"], body["sort_order"]) == (
        "Training room",
        "បន្ទប់បណ្ដុះបណ្ដាល",
        2,
    )
    assert body["is_active"] is True
    assert isinstance(body["id"], int)
    assert UTC_Z.fullmatch(body["created_at"]) and UTC_Z.fullmatch(body["updated_at"])


def test_create_default_sort_order(client, as_admin):
    body = {"name_en": "Meeting room", "name_kh": "បន្ទប់ប្រជុំ"}
    response = client.post(URL, json=body, headers=as_admin)
    assert response.status_code == 201
    assert response.json()["sort_order"] == 0


def test_create_trims_names(client, as_admin):
    body = {**NEW, "name_en": "  Board room ", "name_kh": " បន្ទប់ "}
    response = client.post(URL, json=body, headers=as_admin)
    assert (response.json()["name_en"], response.json()["name_kh"]) == ("Board room", "បន្ទប់")


@pytest.mark.parametrize(
    "name", ["Training room", "training room", "TRAINING ROOM", "Tráining room", " Training room "]
)
def test_create_duplicate_name(client, as_admin, name):
    client.post(URL, json=NEW, headers=as_admin)
    response = client.post(URL, json={**NEW, "name_en": name}, headers=as_admin)
    assert _error(response) == (409, "DUPLICATE")
    assert _fields(response) == {"name_en": "This name already exists."}


def test_duplicate_of_inactive_category(client, as_admin, make_category):
    make_category(name_en="Old room", is_active=False)
    response = client.post(URL, json={**NEW, "name_en": "Old room"}, headers=as_admin)
    assert _error(response) == (409, "DUPLICATE")


def test_same_khmer_name_is_allowed(client, as_admin):
    client.post(URL, json=NEW, headers=as_admin)
    response = client.post(URL, json={**NEW, "name_en": "Other room"}, headers=as_admin)
    assert response.status_code == 201


@pytest.mark.parametrize("field", ["name_en", "name_kh"])
def test_create_name_limits(client, as_admin, field):
    # Khmer text of exactly 100 characters is accepted: limits count characters, not bytes.
    ok = client.post(
        URL, json={**NEW, "name_en": f"Room {field}", field: "ក" * 100}, headers=as_admin
    )
    assert ok.status_code == 201, ok.text
    too_long = client.post(
        URL, json={**NEW, "name_en": f"Long {field}", field: "x" * 101}, headers=as_admin
    )
    assert _error(too_long) == (422, "VALIDATION_ERROR")
    assert _fields(too_long) == {field: "Too long (max 100)."}


@pytest.mark.parametrize("field", ["name_en", "name_kh"])
@pytest.mark.parametrize("value", ["", "   "])
def test_create_blank_name(client, as_admin, field, value):
    response = client.post(URL, json={**NEW, field: value}, headers=as_admin)
    assert _fields(response) == {field: "This field is required."}


@pytest.mark.parametrize("field", ["name_en", "name_kh"])
def test_create_name_must_be_text(client, as_admin, field):
    response = client.post(URL, json={**NEW, field: 123}, headers=as_admin)
    assert set(_fields(response)) == {field}


@pytest.mark.parametrize("value", [0, 9999])
def test_create_sort_order_bounds(client, as_admin, value):
    response = client.post(URL, json={**NEW, "sort_order": value}, headers=as_admin)
    assert response.status_code == 201
    assert response.json()["sort_order"] == value


@pytest.mark.parametrize("value", [-1, 10000])
def test_create_sort_order_out_of_range(client, as_admin, value):
    response = client.post(URL, json={**NEW, "sort_order": value}, headers=as_admin)
    assert _fields(response) == {"sort_order": "Must be 0 to 9999."}


@pytest.mark.parametrize("value", ["abc", 1.5, None])
def test_create_sort_order_not_a_whole_number(client, as_admin, value):
    response = client.post(URL, json={**NEW, "sort_order": value}, headers=as_admin)
    assert _error(response) == (422, "VALIDATION_ERROR")
    assert set(_fields(response)) == {"sort_order"}


def test_create_missing_required_fields(client, as_admin):
    response = client.post(URL, json={}, headers=as_admin)
    assert _fields(response) == {
        "name_en": "This field is required.",
        "name_kh": "This field is required.",
    }


@pytest.mark.parametrize("field", ["id", "is_active", "created_at", "updated_at", "name"])
def test_create_refuses_unknown_and_server_fields(client, as_admin, field):
    response = client.post(URL, json={**NEW, field: True}, headers=as_admin)
    assert _fields(response) == {field: "Unknown field."}


def test_create_malformed_json(client, as_admin):
    response = client.post(
        URL, content=b'{"name_en": ', headers={**as_admin, "Content-Type": "application/json"}
    )
    assert _error(response) == (422, "VALIDATION_ERROR")


def test_create_needs_admin(client, as_staff):
    assert _error(client.post(URL, json=NEW, headers=as_staff)) == (403, "FORBIDDEN")


def test_create_needs_a_token(client):
    assert _error(client.post(URL, json=NEW)) == (401, "UNAUTHORIZED")


def test_create_blocked_until_password_changed(client, make_user, auth_headers):
    admin = make_user(roles=["ADMIN"], must_change_password=True)
    response = client.post(URL, json=NEW, headers=auth_headers(admin))
    assert _error(response) == (403, "PASSWORD_CHANGE_REQUIRED")


# --- Task 26: GET /categories ----------------------------------------------------------


@pytest.fixture
def categories(make_category):
    return {
        "meeting": make_category(name_en="Meeting room", name_kh="បន្ទប់ប្រជុំ", sort_order=1),
        "training": make_category(name_en="Training room", name_kh="បន្ទប់បណ្ដុះបណ្ដាល", sort_order=2),
        "board": make_category(name_en="Board room", name_kh="បន្ទប់ក្រុមប្រឹក្សា", sort_order=1),
        "old": make_category(name_en="Old hall", name_kh="សាលចាស់", sort_order=0, is_active=False),
        "percent": make_category(name_en="Room 50% off", name_kh="បន្ទប់ ៥០"),
        "under": make_category(name_en="Room a_b", name_kh="បន្ទប់ ab"),
    }


def _names(response) -> list[str]:
    assert response.status_code == 200, response.text
    return [item["name_en"] for item in response.json()["items"]]


def _ours(names: list[str], categories: dict) -> list[str]:
    """Only the fixture's categories, in the order returned."""
    mine = {category.name_en for category in categories.values()}
    return [name for name in names if name in mine]


def test_list_shape(client, as_staff, categories):
    body = client.get(URL, headers=as_staff).json()
    assert set(body) == {"items", "page", "size", "total"}
    assert (body["page"], body["size"]) == (1, 20)
    assert body["total"] >= len(categories)
    assert set(body["items"][0]) == CATEGORY_FIELDS


def test_list_order(client, as_staff, categories):
    # sort_order, then English name, then id
    names = _names(client.get(f"{URL}?size=100", headers=as_staff))
    assert _ours(names, categories) == [
        "Old hall",
        "Room 50% off",
        "Room a_b",
        "Board room",
        "Meeting room",
        "Training room",
    ]


def test_list_includes_inactive_by_default(client, as_staff, categories):
    assert "Old hall" in _names(client.get(f"{URL}?size=100", headers=as_staff))


def test_list_filter_active(client, as_staff, categories):
    active = _names(client.get(f"{URL}?is_active=true&size=100", headers=as_staff))
    inactive = _names(client.get(f"{URL}?is_active=false&size=100", headers=as_staff))
    assert "Old hall" not in active and "Meeting room" in active
    assert "Old hall" in inactive and "Meeting room" not in inactive


@pytest.mark.parametrize(
    ("term", "expected"),
    [
        ("room", ["Room 50% off", "Room a_b", "Board room", "Meeting room", "Training room"]),
        ("MEETING", ["Meeting room"]),
        ("បណ្ដុះ", ["Training room"]),
        ("50%", ["Room 50% off"]),
        ("a_b", ["Room a_b"]),
        ("  hall  ", ["Old hall"]),
        ("nothing like this", []),
    ],
)
def test_list_search(client, as_staff, categories, term, expected):
    response = client.get(URL, params={"search": term, "size": 100}, headers=as_staff)
    assert _ours(_names(response), categories) == expected


def test_list_blank_search_is_no_filter(client, as_staff, categories):
    everything = client.get(URL, params={"size": 100}, headers=as_staff).json()["total"]
    blank = client.get(URL, params={"search": "   ", "size": 100}, headers=as_staff)
    assert blank.json()["total"] == everything


def test_list_search_with_status(client, as_staff, categories):
    response = client.get(URL, params={"search": "room", "is_active": "false"}, headers=as_staff)
    assert _ours(_names(response), categories) == []


def test_list_paging(client, as_staff, make_category):
    for n in range(3):
        make_category(name_en=f"Zz Paging {n}")
    params = {"search": "Zz Paging", "size": 2, "page": 2}
    body = client.get(URL, params=params, headers=as_staff).json()
    assert (body["page"], body["size"], body["total"]) == (2, 2, 3)
    assert [item["name_en"] for item in body["items"]] == ["Zz Paging 2"]


def test_list_page_past_the_end(client, as_staff, categories):
    body = client.get(URL, params={"search": "Meeting", "page": 5}, headers=as_staff).json()
    assert body["items"] == [] and body["total"] == 1


@pytest.mark.parametrize(
    ("query", "field"),
    [
        ("size=0", "size"),
        ("size=101", "size"),
        ("page=0", "page"),
        ("page=abc", "page"),
        ("is_active=maybe", "is_active"),
    ],
)
def test_list_bad_query(client, as_staff, query, field):
    response = client.get(f"{URL}?{query}", headers=as_staff)
    assert _error(response) == (422, "VALIDATION_ERROR")
    assert set(_fields(response)) == {field}


def test_list_needs_a_token(client):
    assert _error(client.get(URL)) == (401, "UNAUTHORIZED")


def test_list_for_user_with_no_roles(client, make_user, auth_headers, categories):
    response = client.get(URL, headers=auth_headers(make_user(roles=[])))
    assert response.status_code == 200


# --- Task 27: GET /categories/{id} -----------------------------------------------------


def test_get_category(client, as_staff, categories):
    category = categories["training"]
    response = client.get(f"{URL}/{category.id}", headers=as_staff)
    assert response.status_code == 200
    body = response.json()
    assert set(body) == CATEGORY_FIELDS
    assert (body["id"], body["name_en"], body["sort_order"]) == (category.id, "Training room", 2)


def test_get_inactive_category(client, as_staff, categories):
    response = client.get(f"{URL}/{categories['old'].id}", headers=as_staff)
    assert response.json()["is_active"] is False


def test_get_unknown_category(client, as_staff):
    assert _error(client.get(f"{URL}/999999", headers=as_staff)) == (404, "NOT_FOUND")


@pytest.mark.parametrize("bad_id", ["abc", "0", "-1", "1.5"])
def test_get_bad_id(client, as_staff, bad_id):
    assert _error(client.get(f"{URL}/{bad_id}", headers=as_staff)) == (422, "VALIDATION_ERROR")


def test_get_needs_a_token(client, categories):
    assert _error(client.get(f"{URL}/{categories['meeting'].id}")) == (401, "UNAUTHORIZED")


# --- Task 28: PATCH /categories/{id} ---------------------------------------------------


@pytest.fixture
def category(make_category, db_session):
    category = make_category(name_en="Meeting room", name_kh="បន្ទប់ប្រជុំ", sort_order=1)
    category.updated_at = datetime(2026, 1, 1)
    db_session.flush()
    return category


def patch(client, headers, category, body):
    return client.patch(f"{URL}/{category.id}", json=body, headers=headers)


def test_patch_changes_sent_fields(client, as_admin, category):
    response = patch(client, as_admin, category, {"name_en": "Big meeting room", "sort_order": 5})
    assert response.status_code == 200
    body = response.json()
    assert set(body) == CATEGORY_FIELDS
    assert (body["name_en"], body["sort_order"]) == ("Big meeting room", 5)
    assert body["name_kh"] == "បន្ទប់ប្រជុំ"
    assert body["updated_at"] != "2026-01-01T00:00:00Z"


def test_patch_khmer_name(client, as_admin, category):
    body = patch(client, as_admin, category, {"name_kh": "  បន្ទប់ធំ "}).json()
    assert body["name_kh"] == "បន្ទប់ធំ"


def test_patch_empty_body(client, as_admin, category):
    response = patch(client, as_admin, category, {})
    assert response.status_code == 200
    assert response.json()["updated_at"] == "2026-01-01T00:00:00Z"


def test_patch_same_values(client, as_admin, category):
    body = {"name_en": "Meeting room", "name_kh": "បន្ទប់ប្រជុំ", "sort_order": 1, "is_active": True}
    response = patch(client, as_admin, category, body)
    assert response.status_code == 200
    assert response.json()["updated_at"] == "2026-01-01T00:00:00Z"


def test_patch_own_name_in_another_case(client, as_admin, category):
    # The unique key ignores case, but a record never clashes with itself.
    response = patch(client, as_admin, category, {"name_en": "MEETING ROOM"})
    assert response.status_code == 200
    assert response.json()["name_en"] == "MEETING ROOM"


@pytest.mark.parametrize("field", ["name_en", "name_kh", "sort_order", "is_active"])
def test_patch_null_for_required(client, as_admin, category, field):
    assert _fields(patch(client, as_admin, category, {field: None})) == {
        field: "This field is required."
    }


@pytest.mark.parametrize(
    ("body", "field"),
    [
        ({"name_en": "   "}, "name_en"),
        ({"name_kh": "x" * 101}, "name_kh"),
        ({"sort_order": 10000}, "sort_order"),
        ({"sort_order": -1}, "sort_order"),
        ({"is_active": "maybe"}, "is_active"),
    ],
)
def test_patch_invalid_values(client, as_admin, category, body, field):
    response = patch(client, as_admin, category, body)
    assert _error(response) == (422, "VALIDATION_ERROR")
    assert set(_fields(response)) == {field}


def test_patch_invalid_changes_nothing(client, as_admin, category, db_session):
    patch(client, as_admin, category, {"name_kh": "New", "sort_order": 10000})
    db_session.refresh(category)
    assert (category.name_kh, category.sort_order) == ("បន្ទប់ប្រជុំ", 1)


def test_patch_duplicate_name(client, as_admin, category, make_category, db_session):
    make_category(name_en="Training room")
    # Like data from earlier requests: the 409's rollback must not undo it.
    db_session.commit()
    response = patch(client, as_admin, category, {"name_en": "training ROOM", "sort_order": 7})
    assert _error(response) == (409, "DUPLICATE")
    assert _fields(response) == {"name_en": "This name already exists."}
    db_session.refresh(category)
    assert (category.name_en, category.sort_order) == ("Meeting room", 1)


def test_deactivate_and_reactivate(client, as_admin, category):
    off = patch(client, as_admin, category, {"is_active": False})
    assert off.json()["is_active"] is False
    assert off.json()["updated_at"] != "2026-01-01T00:00:00Z"
    assert patch(client, as_admin, category, {"is_active": True}).json()["is_active"] is True


def test_deactivate_category_used_by_rooms(client, as_admin, category, make_room, db_session):
    # Allowed; rooms keep the category and stay active (R2 only blocks new links).
    room = make_room(category=category)
    assert patch(client, as_admin, category, {"is_active": False}).status_code == 200
    db_session.refresh(room)
    assert (room.category_id, room.is_active) == (category.id, True)


def test_edit_inactive_category(client, as_admin, make_category):
    inactive = make_category(name_en="Old hall", is_active=False)
    body = patch(client, as_admin, inactive, {"name_en": "Older hall"}).json()
    assert (body["name_en"], body["is_active"]) == ("Older hall", False)


def test_patch_unknown_category(client, as_admin):
    response = client.patch(f"{URL}/999999", json={"name_en": "x"}, headers=as_admin)
    assert _error(response) == (404, "NOT_FOUND")


@pytest.mark.parametrize("bad_id", ["abc", "0", "-1"])
def test_patch_bad_id(client, as_admin, bad_id):
    response = client.patch(f"{URL}/{bad_id}", json={}, headers=as_admin)
    assert _error(response) == (422, "VALIDATION_ERROR")


@pytest.mark.parametrize("field", ["id", "created_at", "updated_at", "name"])
def test_patch_unknown_and_server_fields(client, as_admin, category, field):
    assert _fields(patch(client, as_admin, category, {field: 5})) == {field: "Unknown field."}


def test_patch_needs_admin(client, as_staff, category, db_session):
    assert _error(patch(client, as_staff, category, {"name_en": "x"})) == (403, "FORBIDDEN")
    db_session.refresh(category)
    assert category.name_en == "Meeting room"


def test_patch_needs_a_token(client, category):
    response = client.patch(f"{URL}/{category.id}", json={"name_en": "x"})
    assert _error(response) == (401, "UNAUTHORIZED")


@pytest.mark.parametrize("method", ["delete", "put"])
def test_method_not_allowed(client, as_admin, category, method):
    response = client.request(method.upper(), f"{URL}/{category.id}", headers=as_admin)
    assert _error(response) == (405, "METHOD_NOT_ALLOWED")
