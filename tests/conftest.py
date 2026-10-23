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


@pytest.fixture(scope="session", autouse=True)
def fast_password_hashing():
    """Argon2 is slow on purpose. Tests use cheap (still Argon2id) settings so the suite
    stays fast; the app itself always uses the library defaults."""
    from argon2 import PasswordHasher

    import app.security as security

    original = security._hasher
    security._hasher = PasswordHasher(time_cost=1, memory_cost=1024, parallelism=1)
    security._dummy_hash.cache_clear()
    yield
    security._hasher = original
    security._dummy_hash.cache_clear()


def alembic_config(url: str = TEST_DATABASE_URL) -> Config:
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "alembic"))
    config.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
    return config


@pytest.fixture(scope="session")
def migrated_engine():
    """The test database, migrated to the latest schema once per test run.

    Every test's changes are rolled back, so the tables stay empty between runs and only
    new migrations need applying. (test_migrations.py tests the full down and up.)
    """
    from app.db import create_db_engine

    command.upgrade(alembic_config(), "head")
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
def db_session(conn):
    """An ORM session inside the test's transaction. `commit()` only releases a savepoint."""
    from sqlalchemy.orm import Session

    with Session(bind=conn, join_transaction_mode="create_savepoint") as session:
        yield session


def _factory_fixture(name: str):
    """A fixture that returns `tests.factories.<name>` bound to the test's session."""

    @pytest.fixture(name=name)
    def fixture(db_session):
        from tests import factories

        factory = getattr(factories, name)
        return lambda *args, **kwargs: factory(db_session, *args, **kwargs)

    fixture.__doc__ = f"`{name}(...)` from tests/factories.py, saved in the test's session."
    return fixture


# make_user(roles=["ADMIN"]), make_room(), make_location(province="SIEM_REAP"), ...
make_location = _factory_fixture("make_location")
make_building = _factory_fixture("make_building")
make_floor = _factory_fixture("make_floor")
make_category = _factory_fixture("make_category")
make_room = _factory_fixture("make_room")
make_equipment = _factory_fixture("make_equipment")
make_department = _factory_fixture("make_department")
make_division = _factory_fixture("make_division")
make_position = _factory_fixture("make_position")
make_user = _factory_fixture("make_user")


@pytest.fixture
def auth_headers(settings):
    """`auth_headers(user)` -> an Authorization header with a fresh access token."""
    from app.security import create_access_token

    return lambda user: {"Authorization": f"Bearer {create_access_token(user, settings)}"}


@pytest.fixture
def as_admin(make_user, auth_headers):
    """Headers of a fresh, active Admin."""
    return auth_headers(make_user(roles=["ADMIN"]))


@pytest.fixture
def as_staff(make_user, auth_headers):
    """Headers of a fresh, active Staff user (reads only)."""
    return auth_headers(make_user(roles=["STAFF"]))


@pytest.fixture
def settings(tmp_path):
    from app.config import Settings

    return Settings(
        _env_file=None,
        database_url=TEST_DATABASE_URL,
        jwt_secret=TEST_JWT_SECRET,
        upload_dir=tmp_path / "uploads",
        signature_dir=tmp_path / "signatures",
        cors_origins="https://rooms.company.com",
    )


@pytest.fixture
def app(settings):
    from app.main import create_app

    return create_app(settings)


@pytest.fixture
def client(app, db_session):
    """Calls the API with requests that share the test's session, so data is rolled back."""
    from app.db import get_db

    app.dependency_overrides[get_db] = lambda: db_session
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client
    app.dependency_overrides.clear()
