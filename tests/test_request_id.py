import logging
import uuid

from app.errors import AppError


def test_generates_request_id_when_missing(client):
    response = client.get("/api/v1/health")
    assert uuid.UUID(response.headers["x-request-id"])


def test_reuses_request_id_from_request(client):
    response = client.get("/api/v1/health", headers={"X-Request-ID": "abc-123"})
    assert response.headers["x-request-id"] == "abc-123"


def test_replaces_unsafe_request_id(client):
    response = client.get("/api/v1/health", headers={"X-Request-ID": "bad id\twith spaces"})
    assert uuid.UUID(response.headers["x-request-id"])


def test_request_id_on_error_responses(app, client):
    @app.get("/boom-app-error")
    def boom():
        raise AppError("NOT_FOUND", 404, "Not found.")

    assert "x-request-id" in client.get("/boom-app-error").headers
    assert "x-request-id" in client.get("/no-such-route").headers


def test_request_id_on_unexpected_error(app, client):
    @app.get("/boom")
    def boom():
        raise RuntimeError("secret detail")

    response = client.get("/boom", headers={"X-Request-ID": "req-500"})
    assert response.status_code == 500
    assert response.headers["x-request-id"] == "req-500"


def test_unexpected_error_is_logged_with_request_id(app, client, caplog):
    @app.get("/boom")
    def boom():
        raise RuntimeError("secret detail")

    with caplog.at_level(logging.ERROR):
        client.get("/boom", headers={"X-Request-ID": "req-log"})
    records = [r for r in caplog.records if r.levelno >= logging.ERROR]
    assert records
    assert records[0].request_id == "req-log"
