"""Buildings: tasks 17-20, spec section 12, rules R2, R3, R4."""

from datetime import datetime

import pytest

from app.services.province import get_room_province

URL = "/api/v1/buildings"
BUILDING_FIELDS = {
    "id",
    "location_id",
    "name_en",
    "name_kh",
    "short_name",
    "sort_order",
    "is_active",
    "created_at",
    "updated_at",
}
DETAIL_FIELDS = BUILDING_FIELDS | {"location", "province"}


def _error(response) -> tuple[int, str]:
    return response.status_code, response.json()["error"]["code"]


def _fields(response) -> dict:
    return response.json()["error"]["fields"]


@pytest.fixture
def office(make_location):
    return make_location(name_en="Head Office", name_kh="ការិយាល័យកណ្ដាល", province="SIEM_REAP")


def new(office, **overrides) -> dict:
    return {
        "location_id": office.id,
        "name_en": "Building C",
        "name_kh": "អគារ C",
        "short_name": "C",
        "sort_order": 3,
        **overrides,
    }


# --- Task 17: POST /buildings ----------------------------------------------------------


def test_create_building(client, as_admin, office):
    response = client.post(URL, json=new(office), headers=as_admin)
    assert response.status_code == 201
    body = response.json()
    assert set(body) == DETAIL_FIELDS
    assert (body["location_id"], body["name_en"], body["short_name"], body["sort_order"]) == (
        office.id,
        "Building C",
        "C",
        3,
    )
    assert body["location"] == {
        "id": office.id,
        "name_en": "Head Office",
        "name_kh": "ការិយាល័យកណ្ដាល",
    }
    assert body["province"] == {"code": "SIEM_REAP", "name_en": "Siem Reap", "name_kh": "សៀមរាប"}
    assert body["is_active"] is True


def test_create_defaults(client, as_admin, office):
    body = {"location_id": office.id, "name_en": "Building D", "name_kh": "អគារ D"}
    response = client.post(URL, json=body, headers=as_admin).json()
    assert (response["short_name"], response["sort_order"]) == (None, 0)


def test_create_under_unknown_location(client, as_admin, office):
    response = client.post(URL, json=new(office, location_id=999_999), headers=as_admin)
    assert _error(response) == (422, "VALIDATION_ERROR")
    assert _fields(response) == {"location_id": "Office not found."}


def test_create_under_inactive_location(client, as_admin, make_location):
    office = make_location(is_active=False)
    response = client.post(URL, json=new(office), headers=as_admin)
    assert _error(response) == (409, "INACTIVE_REFERENCE")
    assert _fields(response) == {"location_id": "This office is inactive."}


@pytest.mark.parametrize("name", ["Building C", "building c"])
def test_duplicate_name_in_same_location(client, as_admin, office, name):
    client.post(URL, json=new(office), headers=as_admin)
    response = client.post(URL, json=new(office, name_en=name), headers=as_admin)
    assert _error(response) == (409, "DUPLICATE")
    assert _fields(response) == {"name_en": "This name already exists."}


def test_same_name_in_another_location_is_allowed(client, as_admin, office, make_location):
    client.post(URL, json=new(office), headers=as_admin)
    response = client.post(URL, json=new(make_location()), headers=as_admin)
    assert response.status_code == 201


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("short_name", "x" * 21, "Too long (max 20)."),
        ("name_en", "x" * 101, "Too long (max 100)."),
        ("sort_order", 10000, "Must be 0 to 9999."),
        ("sort_order", -1, "Must be 0 to 9999."),
    ],
)
def test_create_field_limits(client, as_admin, office, field, value, message):
    response = client.post(URL, json=new(office, **{field: value}), headers=as_admin)
    assert _fields(response) == {field: message}


@pytest.mark.parametrize("location_id", [0, -1, "abc"])
def test_create_bad_location_id(client, as_admin, office, location_id):
    response = client.post(URL, json=new(office, location_id=location_id), headers=as_admin)
    assert set(_fields(response)) == {"location_id"}


def test_create_missing_fields(client, as_admin):
    assert set(_fields(client.post(URL, json={}, headers=as_admin))) == {
        "location_id",
        "name_en",
        "name_kh",
    }


def test_create_needs_admin(client, as_staff, office):
    assert _error(client.post(URL, json=new(office), headers=as_staff)) == (403, "FORBIDDEN")


def test_create_needs_a_token(client, office):
    assert client.post(URL, json=new(office)).status_code == 401


# --- Task 18: GET /buildings -----------------------------------------------------------


@pytest.fixture
def buildings(office, make_location, make_building):
    other = make_location()
    return {
        "a": make_building(
            location=office, name_en="Alpha", name_kh="អាល់ហ្វា", short_name="AL", sort_order=2
        ),
        "b": make_building(
            location=office, name_en="Bravo", name_kh="ប្រាវ៉ូ", short_name="BR", sort_order=1
        ),
        "c": make_building(
            location=office, name_en="Charlie", name_kh="ឆាលី", sort_order=1, is_active=False
        ),
        "other": make_building(location=other, name_en="Elsewhere", name_kh="ផ្សេង"),
    }


def _names(response) -> list[str]:
    assert response.status_code == 200, response.text
    return [item["name_en"] for item in response.json()["items"]]


def test_list_shape(client, as_staff, buildings):
    body = client.get(URL, headers=as_staff).json()
    assert set(body) == {"items", "page", "size", "total"}
    assert set(body["items"][0]) == BUILDING_FIELDS


def test_list_filter_location_and_sort_order(client, as_staff, office, buildings):
    # sort_order, then English name
    assert _names(client.get(f"{URL}?location_id={office.id}", headers=as_staff)) == [
        "Bravo",
        "Charlie",
        "Alpha",
    ]


def test_list_filter_active(client, as_staff, office, buildings):
    url = f"{URL}?location_id={office.id}"
    assert _names(client.get(f"{url}&is_active=true", headers=as_staff)) == ["Bravo", "Alpha"]
    assert _names(client.get(f"{url}&is_active=false", headers=as_staff)) == ["Charlie"]


@pytest.mark.parametrize(
    ("term", "expected"), [("al", ["Alpha"]), ("BR", ["Bravo"]), ("ឆាលី", ["Charlie"])]
)
def test_list_search(client, as_staff, office, buildings, term, expected):
    response = client.get(URL, params={"location_id": office.id, "search": term}, headers=as_staff)
    assert _names(response) == expected


def test_list_unknown_location_is_empty(client, as_staff, buildings):
    body = client.get(f"{URL}?location_id=999999", headers=as_staff).json()
    assert (body["items"], body["total"]) == ([], 0)


@pytest.mark.parametrize("value", ["0", "abc"])
def test_list_bad_location_id(client, as_staff, value):
    assert client.get(f"{URL}?location_id={value}", headers=as_staff).status_code == 422


def test_list_needs_a_token(client):
    assert client.get(URL).status_code == 401


# --- Task 19: GET /buildings/{id} ------------------------------------------------------


def test_get_building_detail(client, as_staff, office, buildings):
    response = client.get(f"{URL}/{buildings['a'].id}", headers=as_staff)
    assert response.status_code == 200
    body = response.json()
    assert set(body) == DETAIL_FIELDS
    assert body["location"]["id"] == office.id
    assert body["province"]["code"] == "SIEM_REAP"


def test_get_unknown_building(client, as_staff):
    assert _error(client.get(f"{URL}/999999", headers=as_staff)) == (404, "NOT_FOUND")


def test_get_needs_a_token(client, buildings):
    assert client.get(f"{URL}/{buildings['a'].id}").status_code == 401


# --- Task 20: PATCH /buildings/{id} ----------------------------------------------------


@pytest.fixture
def building(office, make_building, db_session):
    building = make_building(location=office, name_en="Building A", name_kh="អគារ A")
    building.updated_at = datetime(2026, 1, 1)
    db_session.flush()
    return building


def patch(client, headers, building, body):
    return client.patch(f"{URL}/{building.id}", json=body, headers=headers)


def test_patch_fields(client, as_admin, building):
    response = patch(
        client, as_admin, building, {"name_en": "Building A2", "short_name": "A2", "sort_order": 9}
    )
    assert response.status_code == 200
    body = response.json()
    assert (body["name_en"], body["short_name"], body["sort_order"]) == ("Building A2", "A2", 9)
    assert set(body) == DETAIL_FIELDS


def test_patch_empty_body_keeps_updated_at(client, as_admin, building):
    assert patch(client, as_admin, building, {}).json()["updated_at"] == "2026-01-01T00:00:00Z"


def test_move_to_another_location(
    client, as_admin, building, make_location, make_floor, make_room, db_session
):
    room = make_room(floor=make_floor(building=building))
    target = make_location(province="KAMPOT")
    response = patch(client, as_admin, building, {"location_id": target.id})
    assert response.status_code == 200
    assert response.json()["location"]["id"] == target.id
    assert response.json()["province"]["code"] == "KAMPOT"
    db_session.expire_all()
    assert get_room_province(room).code == "KAMPOT"  # floors and rooms move with it


def test_move_to_inactive_location(client, as_admin, building, make_location):
    response = patch(client, as_admin, building, {"location_id": make_location(is_active=False).id})
    assert _error(response) == (409, "INACTIVE_REFERENCE")


def test_move_to_unknown_location(client, as_admin, building):
    response = patch(client, as_admin, building, {"location_id": 999_999})
    assert _error(response) == (422, "VALIDATION_ERROR")
    assert _fields(response) == {"location_id": "Office not found."}


def test_move_into_a_name_clash(client, as_admin, building, make_location, make_building):
    target = make_location()
    make_building(location=target, name_en="building a")
    assert _error(patch(client, as_admin, building, {"location_id": target.id})) == (
        409,
        "DUPLICATE",
    )


def test_rename_to_existing_name(client, as_admin, building, office, make_building):
    make_building(location=office, name_en="Building B")
    assert _error(patch(client, as_admin, building, {"name_en": "BUILDING B"})) == (
        409,
        "DUPLICATE",
    )


def test_edit_under_inactive_location_without_moving(
    client, as_admin, building, office, db_session
):
    office.is_active = False
    db_session.flush()
    response = patch(client, as_admin, building, {"name_en": "Renamed", "location_id": office.id})
    assert response.status_code == 200  # R2 only checks references that change


def test_deactivate_and_reactivate(client, as_admin, building):
    assert patch(client, as_admin, building, {"is_active": False}).json()["is_active"] is False
    assert patch(client, as_admin, building, {"is_active": True}).json()["is_active"] is True


def test_reactivate_under_inactive_location(client, as_admin, building, office, db_session):
    building.is_active = False
    office.is_active = False
    db_session.flush()
    response = patch(client, as_admin, building, {"is_active": True})
    assert _error(response) == (409, "INACTIVE_REFERENCE")
    assert _fields(response) == {"is_active": "The office is inactive."}


def test_reactivate_while_moving_to_active_location(
    client, as_admin, building, office, make_location, db_session
):
    building.is_active = False
    office.is_active = False
    db_session.flush()
    response = patch(
        client, as_admin, building, {"is_active": True, "location_id": make_location().id}
    )
    assert response.status_code == 200


def test_keep_active_under_inactive_location(client, as_admin, building, office, db_session):
    office.is_active = False
    db_session.flush()
    assert patch(client, as_admin, building, {"is_active": True}).status_code == 200  # no change


def test_deactivate_keeps_floors_active(client, as_admin, building, make_floor, db_session):
    floor = make_floor(building=building)
    assert patch(client, as_admin, building, {"is_active": False}).status_code == 200
    db_session.refresh(floor)
    assert floor.is_active is True


@pytest.mark.parametrize("field", ["location_id", "name_en", "name_kh", "sort_order", "is_active"])
def test_patch_null_for_required(client, as_admin, building, field):
    assert _fields(patch(client, as_admin, building, {field: None})) == {
        field: "This field is required."
    }


def test_patch_null_clears_short_name(client, as_admin, building):
    assert patch(client, as_admin, building, {"short_name": None}).json()["short_name"] is None


def test_patch_unknown_building(client, as_admin):
    assert _error(client.patch(f"{URL}/999999", json={}, headers=as_admin)) == (404, "NOT_FOUND")


def test_patch_needs_admin(client, as_staff, building):
    assert _error(patch(client, as_staff, building, {"name_en": "x"})) == (403, "FORBIDDEN")


def test_no_delete(client, as_admin, building):
    assert client.delete(f"{URL}/{building.id}", headers=as_admin).status_code == 405
