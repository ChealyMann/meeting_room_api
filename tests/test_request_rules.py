"""Shared request and response rules of spec section 4, checked through real HTTP calls."""

from datetime import UTC, datetime, timedelta, timezone
from typing import Annotated

import pytest
from fastapi import Depends

from app.routers.common import IdPath, PageParams
from app.schemas.common import (
    ItemList,
    OptionalText,
    Page,
    Password,
    RequestModel,
    ResponseModel,
    SortOrder,
    Text,
    UtcDateTime,
)


class ThingCreate(RequestModel):
    name_en: Text(100)
    name_kh: Text(100)
    address: OptionalText(200) = None
    sort_order: SortOrder = 0
    password: Password | None = None


class ThingUpdate(RequestModel):
    """PATCH: every field optional to send, but `null` is refused for required ones."""

    name_en: Text(100) = None
    address: OptionalText(200) = None
    sort_order: SortOrder = None


class ThingOut(ResponseModel):
    id: int
    name_en: str
    created_at: UtcDateTime


@pytest.fixture
def routes(app):
    @app.post("/t/things")
    def create(body: ThingCreate):
        return body.model_dump()

    @app.patch("/t/things")
    def update(body: ThingUpdate):
        return body.model_dump(exclude_unset=True)

    @app.get("/t/things/{thing_id}")
    def get_one(thing_id: IdPath):
        return {"id": thing_id}

    @app.get("/t/things")
    def get_list(paging: Annotated[PageParams, Depends()]):
        return {"page": paging.page, "size": paging.size}

    return app


def _fields(response) -> dict:
    assert response.status_code == 422, response.text
    body = response.json()["error"]
    assert body["code"] == "VALIDATION_ERROR"
    return body["fields"]


VALID = {"name_en": "Head Office", "name_kh": "ការិយាល័យ"}


# --- Strings ---------------------------------------------------------------------------


def test_strings_are_trimmed(routes, client):
    response = client.post("/t/things", json={"name_en": "  Head Office ", "name_kh": " ក "})
    assert response.json()["name_en"] == "Head Office"
    assert response.json()["name_kh"] == "ក"


def test_required_string_of_only_spaces(routes, client):
    response = client.post("/t/things", json={**VALID, "name_en": "   "})
    assert _fields(response) == {"name_en": "This field is required."}


def test_missing_required_string(routes, client):
    assert _fields(client.post("/t/things", json={"name_kh": "ក"})) == {
        "name_en": "This field is required."
    }


def test_optional_string_of_only_spaces_becomes_null(routes, client):
    response = client.post("/t/things", json={**VALID, "address": "   "})
    assert response.json()["address"] is None


def test_khmer_text_of_100_characters_is_accepted(routes, client):
    response = client.post("/t/things", json={**VALID, "name_kh": "ក" * 100})
    assert response.status_code == 200


def test_text_of_101_characters_is_refused(routes, client):
    response = client.post("/t/things", json={**VALID, "name_en": "x" * 101})
    assert _fields(response) == {"name_en": "Too long (max 100)."}


def test_optional_text_limit(routes, client):
    response = client.post("/t/things", json={**VALID, "address": "x" * 201})
    assert _fields(response) == {"address": "Too long (max 200)."}


def test_length_counts_after_trimming(routes, client):
    response = client.post("/t/things", json={**VALID, "name_en": " " + "x" * 100 + " "})
    assert response.status_code == 200


def test_string_field_refuses_other_types(routes, client):
    assert "name_en" in _fields(client.post("/t/things", json={**VALID, "name_en": 5}))


# --- Passwords -------------------------------------------------------------------------


def test_password_is_not_trimmed(routes, client):
    response = client.post("/t/things", json={**VALID, "password": " abc12345 "})
    assert response.json()["password"] == " abc12345 "


@pytest.mark.parametrize("password", ["x" * 7, "x" * 129])
def test_password_length(routes, client, password):
    response = client.post("/t/things", json={**VALID, "password": password})
    assert _fields(response) == {"password": "Password must be 8 to 128 characters."}


@pytest.mark.parametrize("password", ["x" * 8, "x" * 128, "ពាក្យសម្ងាត់១២"])
def test_password_length_bounds_accepted(routes, client, password):
    assert client.post("/t/things", json={**VALID, "password": password}).status_code == 200


# --- Sort order ------------------------------------------------------------------------


@pytest.mark.parametrize("value", [-1, 10000])
def test_sort_order_range(routes, client, value):
    response = client.post("/t/things", json={**VALID, "sort_order": value})
    assert _fields(response) == {"sort_order": "Must be 0 to 9999."}


@pytest.mark.parametrize("value", [0, 9999])
def test_sort_order_bounds_accepted(routes, client, value):
    assert client.post("/t/things", json={**VALID, "sort_order": value}).status_code == 200


def test_sort_order_must_be_whole_number(routes, client):
    assert "sort_order" in _fields(client.post("/t/things", json={**VALID, "sort_order": 1.5}))


# --- Unknown and server-set fields -----------------------------------------------------


def test_unknown_field(routes, client):
    response = client.post("/t/things", json={**VALID, "name": "x"})
    assert _fields(response) == {"name": "Unknown field."}


@pytest.mark.parametrize(
    "field",
    ["id", "created_at", "updated_at", "last_login_at", "password_hash", "must_change_password"],
)
def test_server_set_fields_are_refused(routes, client, field):
    response = client.post("/t/things", json={**VALID, field: "x"})
    assert _fields(response) == {field: "Unknown field."}


# --- PATCH -----------------------------------------------------------------------------


def test_patch_returns_only_sent_fields(routes, client):
    assert client.patch("/t/things", json={"address": "Road 1"}).json() == {"address": "Road 1"}


def test_patch_empty_body(routes, client):
    assert client.patch("/t/things", json={}).json() == {}


def test_patch_null_clears_optional_field(routes, client):
    assert client.patch("/t/things", json={"address": None}).json() == {"address": None}


@pytest.mark.parametrize("field", ["name_en", "sort_order"])
def test_patch_null_for_required_field(routes, client, field):
    assert _fields(client.patch("/t/things", json={field: None})) == {
        field: "This field is required."
    }


# --- Path ids and paging ---------------------------------------------------------------


@pytest.mark.parametrize("thing_id", ["abc", "-1", "0", "1.5"])
def test_bad_path_id(routes, client, thing_id):
    assert list(_fields(client.get(f"/t/things/{thing_id}"))) == ["thing_id"]


def test_good_path_id(routes, client):
    assert client.get("/t/things/12").json() == {"id": 12}


def test_paging_defaults(routes, client):
    assert client.get("/t/things").json() == {"page": 1, "size": 20}


def test_paging_values(routes, client):
    assert client.get("/t/things?page=3&size=100").json() == {"page": 3, "size": 100}


@pytest.mark.parametrize("query", ["size=0", "size=101", "page=0", "page=x"])
def test_paging_out_of_range(routes, client, query):
    assert list(_fields(client.get(f"/t/things?{query}"))) == [query.split("=")[0]]


# --- Responses -------------------------------------------------------------------------


def test_datetimes_are_utc_with_z():
    thing = ThingOut(id=1, name_en="x", created_at=datetime(2026, 10, 21, 2, 15, 0))
    assert thing.model_dump(mode="json")["created_at"] == "2026-10-21T02:15:00Z"


def test_aware_datetimes_are_converted_to_utc():
    cambodia = timezone(timedelta(hours=7))
    thing = ThingOut(id=1, name_en="x", created_at=datetime(2026, 10, 21, 9, 15, tzinfo=cambodia))
    assert thing.model_dump(mode="json")["created_at"] == "2026-10-21T02:15:00Z"
    utc = ThingOut(id=1, name_en="x", created_at=datetime(2026, 10, 21, 2, 15, tzinfo=UTC))
    assert utc.model_dump(mode="json")["created_at"] == "2026-10-21T02:15:00Z"


def test_response_model_reads_orm_objects(make_location):
    location = make_location(name_en="Head Office")
    assert ThingOut.model_validate(location).name_en == "Head Office"


def test_page_shape():
    page = Page[ThingOut](
        items=[ThingOut(id=1, name_en="x", created_at=datetime(2026, 1, 1))],
        page=1,
        size=20,
        total=57,
    )
    assert page.model_dump(mode="json") == {
        "items": [{"id": 1, "name_en": "x", "created_at": "2026-01-01T00:00:00Z"}],
        "page": 1,
        "size": 20,
        "total": 57,
    }


def test_item_list_shape():
    assert ItemList[int](items=[1, 2], total=2).model_dump() == {"items": [1, 2], "total": 2}
