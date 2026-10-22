"""Floors: tasks 21-24, spec section 12, rules R2, R3, R4."""

from datetime import datetime

import pytest

URL = "/api/v1/floors"
FLOOR_FIELDS = {
    "id",
    "building_id",
    "floor_label",
    "sort_order",
    "is_active",
    "created_at",
    "updated_at",
}
DETAIL_FIELDS = FLOOR_FIELDS | {"building", "location", "province"}


def _error(response) -> tuple[int, str]:
    return response.status_code, response.json()["error"]["code"]


def _fields(response) -> dict:
    return response.json()["error"]["fields"]


@pytest.fixture
def office(make_location):
    return make_location(name_en="Head Office", name_kh="ការិយាល័យកណ្ដាល", province="KANDAL")


@pytest.fixture
def building(office, make_building):
    return make_building(location=office, name_en="Building A", name_kh="អគារ A", short_name="A")


def new(building, **overrides) -> dict:
    return {"building_id": building.id, "floor_label": "3rd floor", "sort_order": 3, **overrides}


# --- Task 21: POST /floors -------------------------------------------------------------


def test_create_floor(client, as_admin, building, office):
    response = client.post(URL, json=new(building), headers=as_admin)
    assert response.status_code == 201
    body = response.json()
    assert set(body) == DETAIL_FIELDS
    assert (body["building_id"], body["floor_label"], body["sort_order"]) == (
        building.id,
        "3rd floor",
        3,
    )
    assert body["building"] == {
        "id": building.id,
        "name_en": "Building A",
        "name_kh": "អគារ A",
        "short_name": "A",
    }
    assert body["location"] == {
        "id": office.id,
        "name_en": "Head Office",
        "name_kh": "ការិយាល័យកណ្ដាល",
    }
    assert body["province"] == {"code": "KANDAL", "name_en": "Kandal", "name_kh": "កណ្ដាល"}


def test_create_default_sort_order(client, as_admin, building):
    response = client.post(
        URL, json={"building_id": building.id, "floor_label": "Ground floor"}, headers=as_admin
    )
    assert response.json()["sort_order"] == 0


def test_create_in_unknown_building(client, as_admin, building):
    response = client.post(URL, json=new(building, building_id=999_999), headers=as_admin)
    assert _error(response) == (422, "VALIDATION_ERROR")
    assert _fields(response) == {"building_id": "Building not found."}


def test_create_in_inactive_building(client, as_admin, make_building):
    response = client.post(URL, json=new(make_building(is_active=False)), headers=as_admin)
    assert _error(response) == (409, "INACTIVE_REFERENCE")
    assert _fields(response) == {"building_id": "This building is inactive."}


@pytest.mark.parametrize("label", ["3rd floor", "3RD FLOOR", " 3rd floor "])
def test_duplicate_label_in_same_building(client, as_admin, building, label):
    client.post(URL, json=new(building), headers=as_admin)
    response = client.post(URL, json=new(building, floor_label=label), headers=as_admin)
    assert _error(response) == (409, "DUPLICATE")
    assert _fields(response) == {"floor_label": "This floor already exists."}


def test_same_label_in_another_building_is_allowed(client, as_admin, building, make_building):
    client.post(URL, json=new(building), headers=as_admin)
    assert client.post(URL, json=new(make_building()), headers=as_admin).status_code == 201


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("floor_label", "x" * 101, "Too long (max 100)."),
        ("floor_label", "   ", "This field is required."),
        ("sort_order", 10000, "Must be 0 to 9999."),
    ],
)
def test_create_field_limits(client, as_admin, building, field, value, message):
    assert _fields(client.post(URL, json=new(building, **{field: value}), headers=as_admin)) == {
        field: message
    }


def test_create_missing_fields(client, as_admin):
    assert set(_fields(client.post(URL, json={}, headers=as_admin))) == {
        "building_id",
        "floor_label",
    }


def test_create_needs_admin(client, as_staff, building):
    assert _error(client.post(URL, json=new(building), headers=as_staff)) == (403, "FORBIDDEN")


def test_create_needs_a_token(client, building):
    assert client.post(URL, json=new(building)).status_code == 401


# --- Task 22: GET /floors --------------------------------------------------------------


@pytest.fixture
def floors(building, office, make_building, make_floor):
    second = make_building(location=office, name_en="Building B")
    elsewhere = make_building()
    return {
        "ground": make_floor(building=building, floor_label="Ground floor", sort_order=0),
        "first": make_floor(building=building, floor_label="1st floor", sort_order=1),
        "roof": make_floor(building=building, floor_label="Roof", sort_order=1, is_active=False),
        "b1": make_floor(building=second, floor_label="B 1st floor", sort_order=1),
        "far": make_floor(building=elsewhere, floor_label="Far floor"),
    }


def _labels(response) -> list[str]:
    assert response.status_code == 200, response.text
    return [item["floor_label"] for item in response.json()["items"]]


def test_list_shape(client, as_staff, floors):
    body = client.get(URL, headers=as_staff).json()
    assert set(body) == {"items", "page", "size", "total"}
    assert set(body["items"][0]) == FLOOR_FIELDS


def test_list_by_building_in_order(client, as_staff, building, floors):
    # sort_order, then label
    assert _labels(client.get(f"{URL}?building_id={building.id}", headers=as_staff)) == [
        "Ground floor",
        "1st floor",
        "Roof",
    ]


def test_list_by_location(client, as_staff, office, floors):
    labels = _labels(client.get(f"{URL}?location_id={office.id}", headers=as_staff))
    assert sorted(labels) == sorted(["Ground floor", "1st floor", "Roof", "B 1st floor"])


def test_list_filter_active(client, as_staff, building, floors):
    assert _labels(
        client.get(f"{URL}?building_id={building.id}&is_active=false", headers=as_staff)
    ) == ["Roof"]


def test_list_search_label(client, as_staff, office, floors):
    response = client.get(URL, params={"location_id": office.id, "search": "1st"}, headers=as_staff)
    assert sorted(_labels(response)) == ["1st floor", "B 1st floor"]


@pytest.mark.parametrize("query", ["building_id=0", "location_id=abc"])
def test_list_bad_filters(client, as_staff, query):
    assert client.get(f"{URL}?{query}", headers=as_staff).status_code == 422


def test_list_needs_a_token(client):
    assert client.get(URL).status_code == 401


# --- Task 23: GET /floors/{id} ---------------------------------------------------------


def test_get_floor_detail(client, as_staff, floors, building, office):
    body = client.get(f"{URL}/{floors['first'].id}", headers=as_staff).json()
    assert set(body) == DETAIL_FIELDS
    assert (body["building"]["id"], body["location"]["id"], body["province"]["code"]) == (
        building.id,
        office.id,
        "KANDAL",
    )


def test_get_unknown_floor(client, as_staff):
    assert _error(client.get(f"{URL}/999999", headers=as_staff)) == (404, "NOT_FOUND")


def test_get_needs_a_token(client, floors):
    assert client.get(f"{URL}/{floors['first'].id}").status_code == 401


# --- Task 24: PATCH /floors/{id} -------------------------------------------------------


@pytest.fixture
def floor(building, make_floor, db_session):
    floor = make_floor(building=building, floor_label="2nd floor", sort_order=2)
    floor.updated_at = datetime(2026, 1, 1)
    db_session.flush()
    return floor


def patch(client, headers, floor, body):
    return client.patch(f"{URL}/{floor.id}", json=body, headers=headers)


def test_patch_fields(client, as_admin, floor):
    body = patch(client, as_admin, floor, {"floor_label": "Second floor", "sort_order": 5}).json()
    assert (body["floor_label"], body["sort_order"]) == ("Second floor", 5)
    assert set(body) == DETAIL_FIELDS


def test_patch_empty_body_keeps_updated_at(client, as_admin, floor):
    assert patch(client, as_admin, floor, {}).json()["updated_at"] == "2026-01-01T00:00:00Z"


def test_patch_duplicate_label(client, as_admin, floor, building, make_floor):
    make_floor(building=building, floor_label="3rd floor")
    assert _error(patch(client, as_admin, floor, {"floor_label": "3rd Floor"})) == (
        409,
        "DUPLICATE",
    )


def test_move_to_another_building(client, as_admin, floor, make_building, make_location):
    target = make_building(location=make_location(province="TAKEO"))
    body = patch(client, as_admin, floor, {"building_id": target.id}).json()
    assert body["building"]["id"] == target.id
    assert body["province"]["code"] == "TAKEO"


def test_move_to_inactive_building(client, as_admin, floor, make_building):
    response = patch(client, as_admin, floor, {"building_id": make_building(is_active=False).id})
    assert _error(response) == (409, "INACTIVE_REFERENCE")


def test_deactivate_and_reactivate(client, as_admin, floor):
    assert patch(client, as_admin, floor, {"is_active": False}).json()["is_active"] is False
    assert patch(client, as_admin, floor, {"is_active": True}).json()["is_active"] is True


def test_reactivate_under_inactive_building(client, as_admin, floor, building, db_session):
    floor.is_active = False
    building.is_active = False
    db_session.flush()
    response = patch(client, as_admin, floor, {"is_active": True})
    assert _error(response) == (409, "INACTIVE_REFERENCE")
    assert _fields(response) == {"is_active": "The building is inactive."}


def test_edit_under_inactive_building_without_moving(client, as_admin, floor, building, db_session):
    building.is_active = False
    db_session.flush()
    assert patch(client, as_admin, floor, {"floor_label": "Renamed"}).status_code == 200


def test_deactivate_keeps_rooms_active(client, as_admin, floor, make_room, db_session):
    room = make_room(floor=floor)
    assert patch(client, as_admin, floor, {"is_active": False}).status_code == 200
    db_session.refresh(room)
    assert room.is_active is True


@pytest.mark.parametrize("field", ["building_id", "floor_label", "sort_order", "is_active"])
def test_patch_null_for_required(client, as_admin, floor, field):
    assert _fields(patch(client, as_admin, floor, {field: None})) == {
        field: "This field is required."
    }


def test_patch_unknown_floor(client, as_admin):
    assert _error(client.patch(f"{URL}/999999", json={}, headers=as_admin)) == (404, "NOT_FOUND")


def test_patch_needs_admin(client, as_staff, floor):
    assert _error(patch(client, as_staff, floor, {"floor_label": "x"})) == (403, "FORBIDDEN")


def test_no_delete(client, as_admin, floor):
    assert client.delete(f"{URL}/{floor.id}", headers=as_admin).status_code == 405
