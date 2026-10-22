import os

import pytest
from fastapi.testclient import TestClient

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "mysql+pymysql://app:app@localhost:3307/rooms_test?charset=utf8mb4",
)
TEST_JWT_SECRET = "test-secret-" + "x" * 52

# Set before any app module is imported, so module-level settings point at the test database.
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ.setdefault("JWT_SECRET", TEST_JWT_SECRET)


@pytest.fixture
def settings(tmp_path):
    from app.config import Settings

    return Settings(
        _env_file=None,
        database_url=TEST_DATABASE_URL,
        jwt_secret=TEST_JWT_SECRET,
        upload_dir=tmp_path / "uploads",
        cors_origins="https://rooms.company.com",
    )


@pytest.fixture
def app(settings):
    from app.main import create_app

    return create_app(settings)


@pytest.fixture
def client(app):
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client
