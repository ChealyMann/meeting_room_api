"""Locations (offices): tasks 13-16, spec section 12, rules R1, R3, R4."""

import re
from datetime import datetime

import pytest

URL = "/api/v1/locations"
LOCATION_FIELDS = {
    "id",
    "name_en",
    "name_kh",
    "description",
    "address",
    "province",
    "map_query",
    "is_active",
    "created_at",
    "updated_at",
}
NEW = {
    "name_en": "Siem Reap Branch",
    "name_kh": "សាខាសៀមរាប",
    "description": "Branch office near the city center",
    "address": "Sivatha Blvd, Siem Reap",
    "province": "SIEM_REAP",
    "map_query": "13.3633,103.8564",
}
UTC_Z = re.compile(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ")


def _error(response) -> tuple[int, str]:
    return response.status_code, response.json()["error"]["code"]


def _fields(response) -> dict:
    return response.json()["error"]["fields"]


# --- Task 13: POST /locations ----------------------------------------------------------


def test_create_location(client, as_admin):
    response = client.post(URL, json=NEW, headers=as_admin)
    assert response.status_code == 201
    body = response.json()
    assert set(body) == LOCATION_FIELDS
    assert body["name_en"] == "Siem Reap Branch"
    assert body["name_kh"] == "សាខាសៀមរាប"
    assert body["province"] == {"code": "SIEM_REAP", "name_en": "Siem Reap", "name_kh": "សៀមរាប"}
    assert body["map_query"] == "13.3633,103.8564"
    assert body["is_active"] is True
    assert UTC_Z.fullmatch(body["created_at"]) and UTC_Z.fullmatch(body["updated_at"])


def test_create_with_only_required_fields(client, as_admin):
    body = {"name_en": "Kandal Office", "name_kh": "ការិយាល័យកណ្ដាល", "province": "KANDAL"}
    response = client.post(URL, json=body, headers=as_admin)
    assert response.status_code == 201
    assert (response.json()["description"], response.json()["address"]) == (None, None)


def test_create_trims_text_and_blanks_become_null(client, as_admin):
    body = {**NEW, "name_en": "  Trimmed Office ", "address": "   "}
    response = client.post(URL, json=body, headers=as_admin)
    assert response.json()["name_en"] == "Trimmed Office"
    assert response.json()["address"] is None


@pytest.mark.parametrize(
    "name", ["Siem Reap Branch", "siem reap branch", "SIEM REAP BRANCH", "Siém Reap Branch"]
)
def test_create_duplicate_name(client, as_admin, name):
    client.post(URL, json=NEW, headers=as_admin)
    response = client.post(URL, json={**NEW, "name_en": name}, headers=as_admin)
    assert _error(response) == (409, "DUPLICATE")
    assert _fields(response) == {"name_en": "This name already exists."}


def test_same_khmer_name_is_allowed(client, as_admin):
    client.post(URL, json=NEW, headers=as_admin)
    response = client.post(URL, json={**NEW, "name_en": "Other Branch"}, headers=as_admin)
    assert response.status_code == 201


@pytest.mark.parametrize("province", ["MARS", "siem_reap", "", "Siem Reap"])
def test_create_with_unknown_province(client, as_admin, province):
    response = client.post(URL, json={**NEW, "province": province}, headers=as_admin)
    assert _error(response) == (422, "VALIDATION_ERROR")
    assert set(_fields(response)) == {"province"}


def test_unknown_province_message(client, as_admin):
    response = client.post(URL, json={**NEW, "province": "MARS"}, headers=as_admin)
    assert _fields(response) == {"province": "Must be a province code from GET /provinces."}


@pytest.mark.parametrize(
    ("field", "limit"),
    [
        ("name_en", 100),
        ("name_kh", 100),
        ("description", 1000),
        ("address", 200),
        ("map_query", 500),
    ],
)
def test_create_text_limits(client, as_admin, field, limit):
    ok = client.post(
        URL, json={**NEW, "name_en": f"Office {field}", field: "ក" * limit}, headers=as_admin
    )
    assert ok.status_code == 201, ok.text
    too_long = client.post(
        URL, json={**NEW, "name_en": f"Long {field}", field: "x" * (limit + 1)}, headers=as_admin
    )
    assert _fields(too_long) == {field: f"Too long (max {limit})."}


def test_create_missing_required_fields(client, as_admin):
    response = client.post(URL, json={}, headers=as_admin)
    assert set(_fields(response)) == {"name_en", "name_kh", "province"}


@pytest.mark.parametrize("field", ["id", "is_active", "created_at", "name"])
def test_create_refuses_unknown_and_server_fields(client, as_admin, field):
    response = client.post(URL, json={**NEW, field: True}, headers=as_admin)
    assert _fields(response) == {field: "Unknown field."}


def test_create_needs_admin(client, as_staff):
    assert _error(client.post(URL, json=NEW, headers=as_staff)) == (403, "FORBIDDEN")


def test_create_needs_a_token(client):
    assert client.post(URL, json=NEW).status_code == 401


# --- Task 14: GET /locations -----------------------------------------------------------


@pytest.fixture
def offices(make_location):
    return {
        "pp": make_location(
            name_en="Head Office",
            name_kh="ការិយាល័យកណ្ដាល",
            province="PHNOM_PENH",
            address="No. 12, Street 214",
        ),
        "sr": make_location(
            name_en="Siem Reap Branch",
            name_kh="សាខាសៀមរាប",
            province="SIEM_REAP",
            address="Sivatha Blvd",
        ),
        "bb": make_location(
            name_en="Battambang Branch",
            name_kh="សាខាបាត់ដំបង",
            province="BATTAMBANG",
            is_active=False,
        ),
    }


def _names(response) -> list[str]:
    assert response.status_code == 200, response.text
    return [item["name_en"] for item in response.json()["items"]]


def test_list_locations(client, as_staff, offices):
    response = client.get(URL, headers=as_staff)
    body = response.json()
    assert set(body) == {"items", "page", "size", "total"}
    assert (body["page"], body["size"]) == (1, 20)
    assert body["total"] >= 3
    assert set(body["items"][0]) == LOCATION_FIELDS


def test_list_sorted_by_name(client, as_staff, offices):
    names = _names(client.get(f"{URL}?size=100", headers=as_staff))
    assert names == sorted(names, key=str.lower)


def test_list_includes_inactive_by_default(client, as_staff, offices):
    assert "Battambang Branch" in _names(client.get(f"{URL}?size=100", headers=as_staff))


def test_list_filter_active(client, as_staff, offices):
    active = _names(client.get(f"{URL}?is_active=true&size=100", headers=as_staff))
    inactive = _names(client.get(f"{URL}?is_active=false&size=100", headers=as_staff))
    assert "Battambang Branch" not in active and "Head Office" in active
    assert "Battambang Branch" in inactive and "Head Office" not in inactive


def test_list_filter_province(client, as_staff, offices):
    assert _names(client.get(f"{URL}?province=SIEM_REAP", headers=as_staff)) == ["Siem Reap Branch"]


def test_list_unknown_province(client, as_staff):
    response = client.get(f"{URL}?province=MARS", headers=as_staff)
    assert _error(response) == (422, "VALIDATION_ERROR")
    assert set(_fields(response)) == {"province"}


@pytest.mark.parametrize(
    ("term", "expected"),
    [
        ("branch", ["Battambang Branch", "Siem Reap Branch"]),
        ("សៀមរាប", ["Siem Reap Branch"]),
        ("street 214", ["Head Office"]),
    ],
)
def test_list_search_name_and_address(client, as_staff, offices, term, expected):
    names = _names(client.get(URL, params={"search": term, "size": 100}, headers=as_staff))
    assert [n for n in names if n in {o.name_en for o in offices.values()}] == expected


def test_list_paging(client, as_staff, offices, make_location):
    for n in range(3):
        make_location(name_en=f"Zz Paging {n}", province="KEP")
    body = client.get(f"{URL}?province=KEP&size=2&page=2", headers=as_staff).json()
    assert (body["page"], body["size"], body["total"]) == (2, 2, 3)
    assert [item["name_en"] for item in body["items"]] == ["Zz Paging 2"]


def test_list_page_past_the_end(client, as_staff, offices):
    body = client.get(f"{URL}?province=SIEM_REAP&page=5", headers=as_staff).json()
    assert body["items"] == [] and body["total"] == 1


def test_list_needs_a_token(client):
    assert client.get(URL).status_code == 401


# --- Task 15: GET /locations/{id} ------------------------------------------------------


def test_get_location(client, as_staff, offices):
    office = offices["sr"]
    response = client.get(f"{URL}/{office.id}", headers=as_staff)
    assert response.status_code == 200
    assert response.json()["id"] == office.id
    assert response.json()["province"]["code"] == "SIEM_REAP"


def test_get_inactive_location(client, as_staff, offices):
    response = client.get(f"{URL}/{offices['bb'].id}", headers=as_staff)
    assert response.json()["is_active"] is False


def test_get_unknown_location(client, as_staff):
    assert _error(client.get(f"{URL}/999999", headers=as_staff)) == (404, "NOT_FOUND")


@pytest.mark.parametrize("bad_id", ["abc", "0", "-1"])
def test_get_bad_id(client, as_staff, bad_id):
    assert client.get(f"{URL}/{bad_id}", headers=as_staff).status_code == 422


def test_get_needs_a_token(client, offices):
    assert client.get(f"{URL}/{offices['pp'].id}").status_code == 401


# --- Task 16: PATCH /locations/{id} ----------------------------------------------------


@pytest.fixture
def office(make_location, db_session):
    office = make_location(
        name_en="Head Office", name_kh="ការិយាល័យកណ្ដាល", province="PHNOM_PENH", address="Old"
    )
    office.updated_at = datetime(2026, 1, 1)
    db_session.flush()
    return office


def patch(client, headers, office, body):
    return client.patch(f"{URL}/{office.id}", json=body, headers=headers)


def test_patch_changes_sent_fields(client, as_admin, office):
    response = patch(client, as_admin, office, {"address": "New address", "province": "KANDAL"})
    assert response.status_code == 200
    body = response.json()
    assert body["address"] == "New address"
    assert body["province"]["code"] == "KANDAL"
    assert body["name_en"] == "Head Office"
    assert body["updated_at"] != "2026-01-01T00:00:00Z"


def test_patch_empty_body(client, as_admin, office):
    response = patch(client, as_admin, office, {})
    assert response.status_code == 200
    assert response.json()["updated_at"] == "2026-01-01T00:00:00Z"


def test_patch_same_values(client, as_admin, office):
    response = patch(client, as_admin, office, {"name_en": "Head Office", "address": "Old"})
    assert response.json()["updated_at"] == "2026-01-01T00:00:00Z"


def test_patch_null_clears_optional(client, as_admin, office):
    assert patch(client, as_admin, office, {"address": None}).json()["address"] is None


@pytest.mark.parametrize("field", ["name_en", "name_kh", "province", "is_active"])
def test_patch_null_for_required(client, as_admin, office, field):
    assert _fields(patch(client, as_admin, office, {field: None})) == {
        field: "This field is required."
    }


def test_patch_duplicate_name(client, as_admin, office, make_location):
    make_location(name_en="Branch Two")
    response = patch(client, as_admin, office, {"name_en": "branch two"})
    assert _error(response) == (409, "DUPLICATE")


def test_patch_unknown_province(client, as_admin, office):
    assert set(_fields(patch(client, as_admin, office, {"province": "MARS"}))) == {"province"}


def test_deactivate_and_reactivate(client, as_admin, office):
    assert patch(client, as_admin, office, {"is_active": False}).json()["is_active"] is False
    assert patch(client, as_admin, office, {"is_active": True}).json()["is_active"] is True


def test_deactivate_keeps_buildings_active(client, as_admin, office, make_building, db_session):
    building = make_building(location=office)
    assert patch(client, as_admin, office, {"is_active": False}).json()["is_active"] is False
    db_session.refresh(building)
    assert building.is_active is True


def test_patch_unknown_location(client, as_admin):
    assert _error(client.patch(f"{URL}/999999", json={}, headers=as_admin)) == (404, "NOT_FOUND")


def test_patch_needs_admin(client, as_staff, office):
    assert _error(patch(client, as_staff, office, {"address": "x"})) == (403, "FORBIDDEN")


def test_patch_unknown_field(client, as_admin, office):
    assert _fields(patch(client, as_admin, office, {"id": 5})) == {"id": "Unknown field."}


def test_no_delete(client, as_admin, office):
    assert _error(client.delete(f"{URL}/{office.id}", headers=as_admin)) == (
        405,
        "METHOD_NOT_ALLOWED",
    )
