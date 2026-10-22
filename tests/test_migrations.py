from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, inspect
from sqlalchemy.pool import NullPool

from app.models import Base
from tests.conftest import TEST_DATABASE_URL, alembic_config

ALL_TABLES = {
    "locations",
    "buildings",
    "floors",
    "categories",
    "rooms",
    "room_photos",
    "equipment",
    "room_equipment",
    "departments",
    "divisions",
    "positions",
    "users",
    "roles",
    "user_roles",
}


def _tables(engine) -> set[str]:
    return set(inspect(engine).get_table_names()) - {"alembic_version"}


def test_models_define_the_14_spec_tables():
    assert set(Base.metadata.tables) == ALL_TABLES


def test_upgrade_then_downgrade_on_empty_database():
    config = alembic_config()
    engine = create_engine(TEST_DATABASE_URL, poolclass=NullPool)
    try:
        command.downgrade(config, "base")
        assert _tables(engine) == set()

        command.upgrade(config, "head")
        assert _tables(engine) == ALL_TABLES

        command.downgrade(config, "base")
        assert _tables(engine) == set()
    finally:
        # Leave the test database at the latest schema for the other tests.
        command.upgrade(config, "head")
        engine.dispose()


def test_migrations_match_the_models(migrated_engine):
    with migrated_engine.connect() as connection:
        context = MigrationContext.configure(connection, opts={"compare_type": True})
        assert compare_metadata(context, Base.metadata) == []
