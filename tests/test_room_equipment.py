"""Room equipment: tasks 62-63, spec section 13, rule R15."""

import pytest
from sqlalchemy import insert, select

from app.models import room_equipment

URL = "/api/v1/rooms"
EQUIPMENT_FIELDS = {"id", "name", "icon", "sort_order", "is_active", "created_at", "updated_at"}


def _error(response) -> tuple[int, str]:
    return response.status_code, response.json()["error"]["code"]


def _fields(response) -> dict:
    return response.json()["error"]["fields"]


@pytest.fixture
def owner(make_user):
    return make_user(roles=["ROOM_OWNER"])


@pytest.fixture
def as_owner(owner, auth_headers):
    return auth_headers(owner)


@pytest.fixture
def room(make_room, owner):
    return make_room(owner=owner)


@pytest.fixture
def items(make_equipment):
    return {
        "projector": make_equipment(name="Projector", sort_order=2),
        "board": make_equipment(name="Whiteboard", sort_order=1),
        "screen": make_equipment(name="Screen", sort_order=1),
        "fax": make_equipment(name="Fax", is_active=False),
    }


def give(db_session, room, *equipment) -> None:
    for item in equipment:
        db_session.execute(insert(room_equipment).values(room_id=room.id, equipment_id=item.id))


def stored(db_session, room) -> list[int]:
    query = select(room_equipment.c.equipment_id).where(room_equipment.c.room_id == room.id)
    return sorted(db_session.scalars(query))


def put(client, headers, room, ids):
    return client.put(f"{URL}/{room.id}/equipment", json={"equipment_ids": ids}, headers=headers)


# --- Task 62: PUT /rooms/{id}/equipment ------------------------------------------------


def test_set_equipment(client, as_admin, room, items, db_session):
    ids = [items["projector"].id, items["board"].id, items["screen"].id]
    response = put(client, as_admin, room, ids)
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"items", "total"}
    assert body["total"] == 3
    assert set(body["items"][0]) == EQUIPMENT_FIELDS
    # sort_order, then name
    assert [item["name"] for item in body["items"]] == ["Screen", "Whiteboard", "Projector"]
    assert stored(db_session, room) == sorted(ids)


def test_set_replaces_whole_set(client, as_admin, room, items, db_session):
    give(db_session, room, items["projector"], items["board"])
    body = put(client, as_admin, room, [items["screen"].id]).json()
    assert [item["name"] for item in body["items"]] == ["Screen"]
    assert stored(db_session, room) == [items["screen"].id]


def test_duplicates_saved_once(client, as_admin, room, items, db_session):
    one, four = items["projector"].id, items["board"].id
    body = put(client, as_admin, room, [one, one, four]).json()
    assert body["total"] == 2
    assert stored(db_session, room) == sorted([one, four])


def test_empty_list_removes_all(client, as_admin, room, items, db_session):
    give(db_session, room, items["projector"])
    assert put(client, as_admin, room, []).json() == {"items": [], "total": 0}
    assert stored(db_session, room) == []


def test_unknown_ids(client, as_admin, room, items, db_session):
    give(db_session, room, items["projector"])
    response = put(client, as_admin, room, [items["board"].id, 999_999, 999_998, 999_999])
    assert _error(response) == (422, "VALIDATION_ERROR")
    assert _fields(response) == {"equipment_ids": "Equipment not found: 999998, 999999."}
    assert stored(db_session, room) == [items["projector"].id]


def test_add_inactive_equipment(client, as_admin, room, items, db_session):
    response = put(client, as_admin, room, [items["board"].id, items["fax"].id])
    assert _error(response) == (409, "INACTIVE_REFERENCE")
    assert _fields(response) == {"equipment_ids": f"This equipment is inactive: {items['fax'].id}."}
    assert stored(db_session, room) == []


def test_keep_inactive_equipment_the_room_has(client, as_admin, room, items, db_session):
    give(db_session, room, items["fax"])
    body = put(client, as_admin, room, [items["fax"].id, items["board"].id]).json()
    assert sorted(item["name"] for item in body["items"]) == ["Fax", "Whiteboard"]
    assert {item["name"]: item["is_active"] for item in body["items"]}["Fax"] is False


def test_other_rooms_unchanged(client, as_admin, room, items, make_room, db_session):
    other = make_room()
    give(db_session, other, items["projector"])
    put(client, as_admin, room, [items["board"].id])
    assert stored(db_session, other) == [items["projector"].id]


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"equipment_ids": None},
        {"equipment_ids": "1,2"},
        {"equipment_ids": ["a"]},
        {"equipment_ids": [0]},
        {"equipment_ids": [-1]},
        {"equipment_ids": [], "extra": 1},
    ],
)
def test_bad_body(client, as_admin, room, body):
    response = client.put(f"{URL}/{room.id}/equipment", json=body, headers=as_admin)
    assert _error(response) == (422, "VALIDATION_ERROR")


def test_owner_sets_own_room(client, as_owner, room, items):
    assert put(client, as_owner, room, [items["board"].id]).status_code == 200


def test_owner_cannot_set_others_room(client, as_owner, make_room, items):
    assert _error(put(client, as_owner, make_room(), [items["board"].id])) == (403, "FORBIDDEN")


def test_staff_cannot_set(client, as_staff, room):
    assert _error(put(client, as_staff, room, [])) == (403, "FORBIDDEN")


def test_set_unknown_room(client, as_admin):
    response = client.put(f"{URL}/999999/equipment", json={"equipment_ids": []}, headers=as_admin)
    assert _error(response) == (404, "NOT_FOUND")


def test_set_needs_a_token(client, room):
    response = client.put(f"{URL}/{room.id}/equipment", json={"equipment_ids": []})
    assert _error(response) == (401, "UNAUTHORIZED")


# --- Task 63: GET /rooms/{id}/equipment ------------------------------------------------


def test_list_equipment(client, as_staff, room, items, db_session):
    give(db_session, room, items["projector"], items["fax"], items["screen"])
    response = client.get(f"{URL}/{room.id}/equipment", headers=as_staff)
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 3
    assert [item["name"] for item in body["items"]] == ["Fax", "Screen", "Projector"]


def test_list_no_equipment(client, as_staff, room):
    response = client.get(f"{URL}/{room.id}/equipment", headers=as_staff)
    assert response.json() == {"items": [], "total": 0}


def test_list_unknown_room(client, as_staff):
    assert _error(client.get(f"{URL}/999999/equipment", headers=as_staff)) == (404, "NOT_FOUND")


def test_list_needs_a_token(client, room):
    assert _error(client.get(f"{URL}/{room.id}/equipment")) == (401, "UNAUTHORIZED")


def test_no_delete(client, as_admin, room):
    response = client.delete(f"{URL}/{room.id}/equipment", headers=as_admin)
    assert _error(response) == (405, "METHOD_NOT_ALLOWED")
