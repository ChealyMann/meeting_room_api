def test_health_is_public_and_ok(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_creates_upload_dir_on_start(settings):
    from app.main import create_app

    assert not settings.upload_dir.exists()
    create_app(settings)
    assert settings.upload_dir.is_dir()


def test_serves_uploaded_files_without_token(client, settings):
    (settings.upload_dir / "rooms").mkdir()
    (settings.upload_dir / "rooms" / "a.jpg").write_bytes(b"jpeg-bytes")
    response = client.get("/uploads/rooms/a.jpg")
    assert response.status_code == 200
    assert response.content == b"jpeg-bytes"


def test_upload_dir_has_no_directory_listing(client, settings):
    (settings.upload_dir / "rooms").mkdir()
    response = client.get("/uploads/rooms/")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


def test_cors_allows_configured_origin(client):
    response = client.get("/api/v1/health", headers={"Origin": "https://rooms.company.com"})
    assert response.headers["access-control-allow-origin"] == "https://rooms.company.com"


def test_cors_refuses_other_origin(client):
    response = client.get("/api/v1/health", headers={"Origin": "https://evil.example"})
    assert "access-control-allow-origin" not in response.headers


def test_openapi_docs_are_served(client):
    assert client.get("/docs").status_code == 200
    assert "/api/v1/health" in client.get("/openapi.json").json()["paths"]
