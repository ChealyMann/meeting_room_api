import pytest
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from app.db import create_db_engine, get_db
from tests.conftest import TEST_DATABASE_URL


@pytest.fixture(scope="module")
def engine():
    engine = create_db_engine(TEST_DATABASE_URL)
    try:
        with engine.connect():
            pass
    except OperationalError as exc:
        pytest.fail(
            f"MySQL test database is not reachable ({exc.orig}). "
            "Start it with `docker compose up -d`."
        )
    yield engine
    engine.dispose()


def test_every_connection_uses_utc(engine):
    with engine.connect() as conn:
        assert conn.execute(text("SELECT @@session.time_zone")).scalar() == "+00:00"


def test_connection_uses_utf8mb4(engine):
    with engine.connect() as conn:
        assert conn.execute(text("SELECT @@character_set_client")).scalar() == "utf8mb4"


def test_round_trips_khmer_text(engine):
    with engine.connect() as conn:
        assert conn.execute(text("SELECT :v"), {"v": "ភ្នំពេញ"}).scalar() == "ភ្នំពេញ"


def test_get_db_yields_working_session_and_closes_it():
    generator = get_db()
    session = next(generator)
    assert session.execute(text("SELECT 1")).scalar() == 1
    generator.close()
    assert not session.in_transaction()
