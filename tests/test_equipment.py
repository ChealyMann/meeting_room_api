"""Equipment: tasks 29-32, spec section 13, rule R4."""

import re
from datetime import datetime

import pytest

URL = "/api/v1/equipment"
EQUIPMENT_FIELDS = {"id", "name", "icon", "sort_order", "is_active", "created_at", "updated_at"}
NEW = {"name": "Projector", "icon": "projector", "sort_order": 2}
UTC_Z = re.compile(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ")


def _error(response) -> tuple[int, str]:
    return response.status_code, response.json()["error"]["code"]


def _fields(response) -> dict:
    return response.json()["error"]["fields"]


# --- Task 29: POST /equipment ----------------------------------------------------------


def test_create_equipment(client, as_admin):
    response = client.post(URL, json=NEW, headers=as_admin)
    assert response.status_code == 201
    body = response.json()
    assert set(body) == EQUIPMENT_FIELDS
    assert (body["name"], body["icon"], body["sort_order"], body["is_active"]) == (
        "Projector",
        "projector",
        2,
        True,
    )
    assert UTC_Z.fullmatch(body["created_at"]) and UTC_Z.fullmatch(body["updated_at"])


def test_create_defaults(client, as_admin):
    response = client.post(URL, json={"name": "Whiteboard"}, headers=as_admin)
    assert response.status_code == 201
    assert (response.json()["icon"], response.json()["sort_order"]) == (None, 0)


def test_create_trims_and_blank_icon_becomes_null(client, as_admin):
    response = client.post(URL, json={"name": "  Speaker ", "icon": "   "}, headers=as_admin)
    assert (response.json()["name"], response.json()["icon"]) == ("Speaker", None)


def test_create_icon_can_be_a_url(client, as_admin):
    icon = "https://cdn.example.com/icons/tv.svg"
    response = client.post(URL, json={"name": "TV", "icon": icon}, headers=as_admin)
    assert response.json()["icon"] == icon


@pytest.mark.parametrize(
    "name", ["Projector", "projector", "PROJECTOR", "Projéctor", " Projector "]
)
def test_create_duplicate_name(client, as_admin, name):
    client.post(URL, json=NEW, headers=as_admin)
    response = client.post(URL, json={**NEW, "name": name}, headers=as_admin)
    assert _error(response) == (409, "DUPLICATE")
    assert _fields(response) == {"name": "This name already exists."}


def test_duplicate_of_inactive_equipment(client, as_admin, make_equipment):
    make_equipment(name="Fax", is_active=False)
    assert _error(client.post(URL, json={"name": "fax"}, headers=as_admin)) == (409, "DUPLICATE")


@pytest.mark.parametrize(("field", "limit"), [("name", 200), ("icon", 1000)])
def test_create_text_limits(client, as_admin, field, limit):
    ok = client.post(
        URL, json={**NEW, "name": f"Item {field}", field: "ក" * limit}, headers=as_admin
    )
    assert ok.status_code == 201, ok.text
    too_long = client.post(
        URL, json={**NEW, "name": f"Long {field}", field: "x" * (limit + 1)}, headers=as_admin
    )
    assert _error(too_long) == (422, "VALIDATION_ERROR")
    assert _fields(too_long) == {field: f"Too long (max {limit})."}


@pytest.mark.parametrize("value", ["", "   "])
def test_create_blank_name(client, as_admin, value):
    assert _fields(client.post(URL, json={**NEW, "name": value}, headers=as_admin)) == {
        "name": "This field is required."
    }


@pytest.mark.parametrize(
    ("value", "message"), [(-1, "Must be 0 to 9999."), (10000, "Must be 0 to 9999.")]
)
def test_create_sort_order_out_of_range(client, as_admin, value, message):
    response = client.post(URL, json={**NEW, "sort_order": value}, headers=as_admin)
    assert _fields(response) == {"sort_order": message}


@pytest.mark.parametrize("value", ["abc", 1.5, None])
def test_create_sort_order_not_a_whole_number(client, as_admin, value):
    response = client.post(URL, json={**NEW, "sort_order": value}, headers=as_admin)
    assert set(_fields(response)) == {"sort_order"}


def test_create_missing_name(client, as_admin):
    response = client.post(URL, json={"icon": "x"}, headers=as_admin)
    assert _fields(response) == {"name": "This field is required."}


@pytest.mark.parametrize("field", ["id", "is_active", "created_at", "updated_at", "name_en"])
def test_create_refuses_unknown_and_server_fields(client, as_admin, field):
    response = client.post(URL, json={**NEW, field: True}, headers=as_admin)
    assert _fields(response) == {field: "Unknown field."}


def test_create_malformed_json(client, as_admin):
    response = client.post(
        URL, content=b"{", headers={**as_admin, "Content-Type": "application/json"}
    )
    assert _error(response) == (422, "VALIDATION_ERROR")


def test_create_needs_admin(client, as_staff):
    assert _error(client.post(URL, json=NEW, headers=as_staff)) == (403, "FORBIDDEN")


def test_create_needs_a_token(client):
    assert _error(client.post(URL, json=NEW)) == (401, "UNAUTHORIZED")


# --- Task 30: GET /equipment -----------------------------------------------------------


@pytest.fixture
def items(make_equipment):
    return {
        "projector": make_equipment(name="Projector", icon="projector", sort_order=2),
        "board": make_equipment(name="Whiteboard", sort_order=1),
        "screen": make_equipment(name="Screen", sort_order=1),
        "fax": make_equipment(name="Fax machine", sort_order=0, is_active=False),
        "percent": make_equipment(name="Mic 100% wireless", sort_order=3),
        "under": make_equipment(name="TV a_b", sort_order=3),
    }


def _names(response) -> list[str]:
    assert response.status_code == 200, response.text
    return [item["name"] for item in response.json()["items"]]


def _ours(names: list[str], items: dict) -> list[str]:
    mine = {item.name for item in items.values()}
    return [name for name in names if name in mine]


def test_list_shape(client, as_staff, items):
    body = client.get(URL, headers=as_staff).json()
    assert set(body) == {"items", "page", "size", "total"}
    assert (body["page"], body["size"]) == (1, 20)
    assert set(body["items"][0]) == EQUIPMENT_FIELDS


def test_list_order(client, as_staff, items):
    # sort_order, then name, then id
    assert _ours(_names(client.get(f"{URL}?size=100", headers=as_staff)), items) == [
        "Fax machine",
        "Screen",
        "Whiteboard",
        "Projector",
        "Mic 100% wireless",
        "TV a_b",
    ]


def test_list_filter_active(client, as_staff, items):
    active = _names(client.get(f"{URL}?is_active=true&size=100", headers=as_staff))
    inactive = _names(client.get(f"{URL}?is_active=false&size=100", headers=as_staff))
    assert "Fax machine" not in active and "Projector" in active
    assert "Fax machine" in inactive and "Projector" not in inactive


@pytest.mark.parametrize(
    ("term", "expected"),
    [
        ("board", ["Whiteboard"]),
        ("SCREEN", ["Screen"]),
        ("100%", ["Mic 100% wireless"]),
        ("a_b", ["TV a_b"]),
        ("  fax ", ["Fax machine"]),
        ("projectorx", []),
    ],
)
def test_list_search(client, as_staff, items, term, expected):
    response = client.get(URL, params={"search": term, "size": 100}, headers=as_staff)
    assert _ours(_names(response), items) == expected


def test_list_search_does_not_match_icon(client, as_staff, make_equipment):
    make_equipment(name="Beamer", icon="zzicon")
    assert _names(client.get(URL, params={"search": "zzicon"}, headers=as_staff)) == []


def test_list_blank_search_is_no_filter(client, as_staff, items):
    everything = client.get(URL, headers=as_staff).json()["total"]
    assert client.get(URL, params={"search": "  "}, headers=as_staff).json()["total"] == everything


def test_list_paging(client, as_staff, make_equipment):
    for n in range(3):
        make_equipment(name=f"Zz Paging {n}")
    body = client.get(
        URL, params={"search": "Zz Paging", "size": 2, "page": 2}, headers=as_staff
    ).json()
    assert (body["page"], body["size"], body["total"]) == (2, 2, 3)
    assert [item["name"] for item in body["items"]] == ["Zz Paging 2"]


def test_list_page_past_the_end(client, as_staff, items):
    body = client.get(URL, params={"search": "Screen", "page": 9}, headers=as_staff).json()
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


# --- Task 31: GET /equipment/{id} ------------------------------------------------------


def test_get_equipment(client, as_staff, items):
    item = items["projector"]
    response = client.get(f"{URL}/{item.id}", headers=as_staff)
    assert response.status_code == 200
    assert set(response.json()) == EQUIPMENT_FIELDS
    assert (response.json()["id"], response.json()["icon"]) == (item.id, "projector")


def test_get_inactive_equipment(client, as_staff, items):
    assert client.get(f"{URL}/{items['fax'].id}", headers=as_staff).json()["is_active"] is False


def test_get_unknown_equipment(client, as_staff):
    assert _error(client.get(f"{URL}/999999", headers=as_staff)) == (404, "NOT_FOUND")


@pytest.mark.parametrize("bad_id", ["abc", "0", "-1"])
def test_get_bad_id(client, as_staff, bad_id):
    assert _error(client.get(f"{URL}/{bad_id}", headers=as_staff)) == (422, "VALIDATION_ERROR")


def test_get_needs_a_token(client, items):
    assert _error(client.get(f"{URL}/{items['board'].id}")) == (401, "UNAUTHORIZED")


# --- Task 32: PATCH /equipment/{id} ----------------------------------------------------


@pytest.fixture
def item(make_equipment, db_session):
    item = make_equipment(name="Projector", icon="projector", sort_order=2)
    item.updated_at = datetime(2026, 1, 1)
    db_session.flush()
    return item


def patch(client, headers, item, body):
    return client.patch(f"{URL}/{item.id}", json=body, headers=headers)


def test_patch_changes_sent_fields(client, as_admin, item):
    response = patch(client, as_admin, item, {"name": "Laser projector", "sort_order": 4})
    assert response.status_code == 200
    body = response.json()
    assert set(body) == EQUIPMENT_FIELDS
    assert (body["name"], body["icon"], body["sort_order"]) == ("Laser projector", "projector", 4)
    assert body["updated_at"] != "2026-01-01T00:00:00Z"


def test_patch_empty_body(client, as_admin, item):
    response = patch(client, as_admin, item, {})
    assert response.status_code == 200
    assert response.json()["updated_at"] == "2026-01-01T00:00:00Z"


def test_patch_same_values(client, as_admin, item):
    body = {"name": "Projector", "icon": "projector", "sort_order": 2, "is_active": True}
    assert patch(client, as_admin, item, body).json()["updated_at"] == "2026-01-01T00:00:00Z"


@pytest.mark.parametrize("value", [None, "  "])
def test_patch_clears_icon(client, as_admin, item, value):
    assert patch(client, as_admin, item, {"icon": value}).json()["icon"] is None


def test_patch_own_name_in_another_case(client, as_admin, item):
    assert patch(client, as_admin, item, {"name": "PROJECTOR"}).json()["name"] == "PROJECTOR"


@pytest.mark.parametrize("field", ["name", "sort_order", "is_active"])
def test_patch_null_for_required(client, as_admin, item, field):
    assert _fields(patch(client, as_admin, item, {field: None})) == {
        field: "This field is required."
    }


@pytest.mark.parametrize(
    ("body", "field"),
    [
        ({"name": " "}, "name"),
        ({"name": "x" * 201}, "name"),
        ({"icon": "x" * 1001}, "icon"),
        ({"sort_order": 10000}, "sort_order"),
        ({"is_active": "maybe"}, "is_active"),
    ],
)
def test_patch_invalid_values(client, as_admin, item, body, field):
    response = patch(client, as_admin, item, body)
    assert _error(response) == (422, "VALIDATION_ERROR")
    assert set(_fields(response)) == {field}


def test_patch_duplicate_name(client, as_admin, item, make_equipment, db_session):
    make_equipment(name="Screen")
    db_session.commit()  # like data from earlier requests: the 409's rollback keeps it
    response = patch(client, as_admin, item, {"name": "screen", "sort_order": 9})
    assert _error(response) == (409, "DUPLICATE")
    assert _fields(response) == {"name": "This name already exists."}
    db_session.refresh(item)
    assert (item.name, item.sort_order) == ("Projector", 2)


def test_deactivate_and_reactivate(client, as_admin, item):
    assert patch(client, as_admin, item, {"is_active": False}).json()["is_active"] is False
    assert patch(client, as_admin, item, {"is_active": True}).json()["is_active"] is True


def test_deactivate_keeps_it_on_rooms(client, as_admin, item, make_room, db_session):
    from sqlalchemy import select

    from app.models import room_equipment

    room = make_room()
    db_session.execute(room_equipment.insert().values(room_id=room.id, equipment_id=item.id))
    assert patch(client, as_admin, item, {"is_active": False}).status_code == 200
    kept = db_session.scalars(
        select(room_equipment.c.equipment_id).where(room_equipment.c.room_id == room.id)
    ).all()
    assert kept == [item.id]


def test_patch_unknown_equipment(client, as_admin):
    response = client.patch(f"{URL}/999999", json={"name": "x"}, headers=as_admin)
    assert _error(response) == (404, "NOT_FOUND")


@pytest.mark.parametrize("bad_id", ["abc", "0", "-1"])
def test_patch_bad_id(client, as_admin, bad_id):
    assert _error(client.patch(f"{URL}/{bad_id}", json={}, headers=as_admin)) == (
        422,
        "VALIDATION_ERROR",
    )


@pytest.mark.parametrize("field", ["id", "created_at", "updated_at"])
def test_patch_server_fields(client, as_admin, item, field):
    assert _fields(patch(client, as_admin, item, {field: 5})) == {field: "Unknown field."}


def test_patch_needs_admin(client, as_staff, item):
    assert _error(patch(client, as_staff, item, {"name": "x"})) == (403, "FORBIDDEN")


def test_patch_needs_a_token(client, item):
    assert _error(client.patch(f"{URL}/{item.id}", json={})) == (401, "UNAUTHORIZED")


@pytest.mark.parametrize("method", ["DELETE", "PUT"])
def test_method_not_allowed(client, as_admin, item, method):
    response = client.request(method, f"{URL}/{item.id}", headers=as_admin)
    assert _error(response) == (405, "METHOD_NOT_ALLOWED")
