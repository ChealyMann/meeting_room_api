import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "mysql+pymysql://app:app@localhost:3307/rooms_test?charset=utf8mb4",
)
TEST_JWT_SECRET = "test-secret-" + "x" * 52

# Set before any app module is imported, so module-level settings point at the test database.
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ.setdefault("JWT_SECRET", TEST_JWT_SECRET)


def alembic_config(url: str = TEST_DATABASE_URL) -> Config:
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "alembic"))
    config.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
    return config


@pytest.fixture(scope="session")
def migrated_engine():
    """The test database, freshly migrated to the latest schema once per test run."""
    from app.db import create_db_engine

    config = alembic_config()
    command.downgrade(config, "base")
    command.upgrade(config, "head")
    engine = create_db_engine(TEST_DATABASE_URL)
    yield engine
    engine.dispose()


@pytest.fixture
def conn(migrated_engine):
    """A connection whose changes are rolled back after the test."""
    with migrated_engine.connect() as connection:
        transaction = connection.begin()
        yield connection
        transaction.rollback()


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
