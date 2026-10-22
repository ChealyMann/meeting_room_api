import pytest
from pydantic import BaseModel, ConfigDict

from app.errors import AppError, ErrorCode


class Item(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name_en: str
    tags: list[int] = []


@pytest.fixture
def routes(app):
    @app.get("/t/app-error")
    def app_error():
        raise AppError(
            ErrorCode.DUPLICATE, 409, "This name already exists.", {"name_en": "Already used."}
        )

    @app.get("/t/app-error-no-fields")
    def app_error_no_fields():
        raise AppError(ErrorCode.FORBIDDEN, 403, "You are not allowed.")

    @app.post("/t/items")
    def create_item(item: Item):
        return item

    @app.get("/t/query")
    def query(size: int):
        return {"size": size}

    @app.get("/t/boom")
    def boom():
        raise RuntimeError("SELECT password_hash FROM users")

    @app.get("/t/items/{item_id}")
    def get_item(item_id: int):
        return {"id": item_id}

    return app


def test_app_error_uses_common_shape(routes, client):
    response = client.get("/t/app-error")
    assert response.status_code == 409
    assert response.json() == {
        "error": {
            "code": "DUPLICATE",
            "message": "This name already exists.",
            "fields": {"name_en": "Already used."},
        }
    }


def test_fields_left_out_when_not_field_level(routes, client):
    response = client.get("/t/app-error-no-fields")
    assert response.status_code == 403
    assert response.json() == {"error": {"code": "FORBIDDEN", "message": "You are not allowed."}}


def test_missing_required_field(routes, client):
    response = client.post("/t/items", json={})
    assert response.status_code == 422
    body = response.json()["error"]
    assert body["code"] == "VALIDATION_ERROR"
    assert body["message"] == "Invalid request."
    assert body["fields"] == {"name_en": "This field is required."}


def test_unknown_field_is_named(routes, client):
    response = client.post("/t/items", json={"name_en": "x", "name": "x"})
    assert response.status_code == 422
    assert response.json()["error"]["fields"] == {"name": "Unknown field."}


def test_nested_field_path_uses_dots(routes, client):
    response = client.post("/t/items", json={"name_en": "x", "tags": [1, "a"]})
    assert response.status_code == 422
    assert list(response.json()["error"]["fields"]) == ["tags.1"]


def test_malformed_json(routes, client):
    response = client.post(
        "/t/items", content=b"{not json", headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 422
    body = response.json()["error"]
    assert body["code"] == "VALIDATION_ERROR"
    assert "body" in body["fields"]


def test_invalid_query_value(routes, client):
    response = client.get("/t/query", params={"size": "abc"})
    assert response.status_code == 422
    assert list(response.json()["error"]["fields"]) == ["size"]


def test_non_integer_path_id(routes, client):
    response = client.get("/t/items/abc")
    assert response.status_code == 422
    assert list(response.json()["error"]["fields"]) == ["item_id"]


def test_unknown_route_is_not_found(client):
    response = client.get("/api/v1/no-such-thing")
    assert response.status_code == 404
    assert response.json() == {"error": {"code": "NOT_FOUND", "message": "Not found."}}


def test_method_not_allowed(client):
    response = client.delete("/api/v1/health")
    assert response.status_code == 405
    assert response.json()["error"]["code"] == "METHOD_NOT_ALLOWED"
    assert "GET" in response.headers["allow"]


def test_unexpected_error_hides_details(routes, client):
    response = client.get("/t/boom")
    assert response.status_code == 500
    assert response.json() == {
        "error": {"code": "INTERNAL_ERROR", "message": "Something went wrong."}
    }
    assert "password_hash" not in response.text
    assert "Traceback" not in response.text


def test_error_codes_are_the_complete_spec_list():
    assert {code.value for code in ErrorCode} == {
        "WRONG_PASSWORD",
        "UNAUTHORIZED",
        "INVALID_CREDENTIALS",
        "PASSWORD_CHANGE_REQUIRED",
        "FORBIDDEN",
        "NOT_FOUND",
        "METHOD_NOT_ALLOWED",
        "DUPLICATE",
        "INACTIVE_REFERENCE",
        "DIVISION_REQUIRED",
        "OWNER_INVALID",
        "LAST_ADMIN",
        "SELF_ACTION_NOT_ALLOWED",
        "PHOTO_LIMIT_REACHED",
        "FILE_TOO_LARGE",
        "UNSUPPORTED_FILE_TYPE",
        "VALIDATION_ERROR",
        "INVALID_IMAGE",
        "RATE_LIMITED",
        "INTERNAL_ERROR",
    }
