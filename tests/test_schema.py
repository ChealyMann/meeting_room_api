"""The database schema matches spec sections 6 and 7."""

from datetime import UTC, datetime, time

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.models import Base, Location, utcnow

ER_DUP_ENTRY = 1062
ER_DATA_TOO_LONG = 1406
ER_ROW_IS_REFERENCED_2 = 1451
ER_NO_REFERENCED_ROW_2 = 1452
ER_CHECK_CONSTRAINT_VIOLATED = 3819

COMMON = {
    "id": ("int unsigned", False),
    "is_active": ("tinyint(1)", False),
    "created_at": ("datetime", False),
    "updated_at": ("datetime", False),
}
SORT_ORDER = {"sort_order": ("int", False)}
NAMES = {"name_en": ("varchar(100)", False), "name_kh": ("varchar(100)", False)}

# table -> column -> (MySQL column type, nullable)
EXPECTED_COLUMNS = {
    "locations": {
        **COMMON,
        **NAMES,
        "description": ("varchar(1000)", True),
        "address": ("varchar(200)", True),
        "province": ("varchar(30)", False),
        "map_query": ("varchar(500)", True),
    },
    "buildings": {
        **COMMON,
        **SORT_ORDER,
        **NAMES,
        "location_id": ("int unsigned", False),
        "short_name": ("varchar(20)", True),
    },
    "floors": {
        **COMMON,
        **SORT_ORDER,
        "building_id": ("int unsigned", False),
        "floor_label": ("varchar(100)", False),
    },
    "categories": {**COMMON, **SORT_ORDER, **NAMES},
    "rooms": {
        **COMMON,
        **NAMES,
        "door_code": ("varchar(50)", True),
        "short_desc": ("varchar(200)", True),
        "floor_id": ("int unsigned", False),
        "category_id": ("int unsigned", False),
        "room_owner_id": ("int unsigned", True),
        "capacity": ("int unsigned", False),
        "size_sqm": ("int unsigned", True),
        "description": ("varchar(1000)", True),
        "start_time": ("time", False),
        "end_time": ("time", False),
        "is_private": ("tinyint(1)", False),
    },
    "room_photos": {
        "id": ("int unsigned", False),
        "room_id": ("int unsigned", False),
        "url": ("varchar(3000)", False),
        "thumbnail_url": ("varchar(3000)", False),
        "sort_order": ("int", False),
        "created_at": ("datetime", False),
        "updated_at": ("datetime", False),
    },
    "equipment": {
        **COMMON,
        **SORT_ORDER,
        "name": ("varchar(200)", False),
        "icon": ("varchar(1000)", True),
    },
    "room_equipment": {
        "room_id": ("int unsigned", False),
        "equipment_id": ("int unsigned", False),
    },
    "departments": {**COMMON, **SORT_ORDER, **NAMES, "location_id": ("int unsigned", False)},
    "divisions": {
        **COMMON,
        **SORT_ORDER,
        **NAMES,
        "department_id": ("int unsigned", False),
        "short_name": ("varchar(20)", True),
    },
    "positions": {**COMMON, **SORT_ORDER, **NAMES},
    "users": {
        **COMMON,
        **NAMES,
        "staff_id": ("varchar(20)", False),
        "title": ("varchar(20)", True),
        "division_id": ("int unsigned", True),
        "position_id": ("int unsigned", False),
        "email": ("varchar(254)", False),
        "secondary_email": ("varchar(254)", True),
        "phone": ("varchar(20)", True),
        "avatar_url": ("varchar(3000)", True),
        "user_signature": ("varchar(3000)", True),
        "email_notifications": ("tinyint(1)", False),
        "last_login_at": ("datetime", True),
        "password_hash": ("varchar(255)", False),
        "must_change_password": ("tinyint(1)", False),
    },
    "roles": {**COMMON, **NAMES, "code": ("varchar(50)", False)},
    "user_roles": {"user_id": ("int unsigned", False), "role_id": ("int unsigned", False)},
}

EXPECTED_UNIQUE_KEYS = {
    ("locations", ("name_en",)),
    ("buildings", ("location_id", "name_en")),
    ("floors", ("building_id", "floor_label")),
    ("categories", ("name_en",)),
    ("rooms", ("floor_id", "name_en")),
    ("equipment", ("name",)),
    ("departments", ("location_id", "name_en")),
    ("divisions", ("department_id", "name_en")),
    ("positions", ("name_en",)),
    ("users", ("staff_id",)),
    ("users", ("email",)),
    ("roles", ("code",)),
}

EXPECTED_PRIMARY_KEYS = {
    **{table: ("id",) for table in EXPECTED_COLUMNS if "id" in EXPECTED_COLUMNS[table]},
    "room_equipment": ("room_id", "equipment_id"),
    "user_roles": ("user_id", "role_id"),
}

# (table, column, referenced table)
EXPECTED_FOREIGN_KEYS = {
    ("buildings", "location_id", "locations"),
    ("floors", "building_id", "buildings"),
    ("rooms", "floor_id", "floors"),
    ("rooms", "category_id", "categories"),
    ("rooms", "room_owner_id", "users"),
    ("room_photos", "room_id", "rooms"),
    ("room_equipment", "room_id", "rooms"),
    ("room_equipment", "equipment_id", "equipment"),
    ("departments", "location_id", "locations"),
    ("divisions", "department_id", "departments"),
    ("users", "division_id", "divisions"),
    ("users", "position_id", "positions"),
    ("user_roles", "user_id", "users"),
    ("user_roles", "role_id", "roles"),
}

# Columns the spec marks "Indexed": each must lead some index.
EXPECTED_INDEXED = {
    ("locations", "province"),
    ("buildings", "location_id"),
    ("floors", "building_id"),
    ("rooms", "floor_id"),
    ("rooms", "category_id"),
    ("rooms", "room_owner_id"),
    ("room_photos", "room_id"),
    ("room_equipment", "equipment_id"),
    ("departments", "location_id"),
    ("divisions", "department_id"),
    ("users", "division_id"),
    ("users", "position_id"),
    ("user_roles", "role_id"),
}


def _rows(conn, sql: str, **params):
    return conn.execute(text(sql), params).all()


def _indexes(conn) -> dict[tuple[str, str], tuple[bool, tuple[str, ...]]]:
    """(table, index name) -> (unique, columns in order)."""
    rows = _rows(
        conn,
        "SELECT TABLE_NAME, INDEX_NAME, NON_UNIQUE, COLUMN_NAME FROM information_schema.STATISTICS "
        "WHERE TABLE_SCHEMA = DATABASE() ORDER BY TABLE_NAME, INDEX_NAME, SEQ_IN_INDEX",
    )
    indexes: dict = {}
    for table, name, non_unique, column in rows:
        unique, columns = indexes.get((table, name), (not non_unique, ()))
        indexes[(table, name)] = (unique, (*columns, column))
    return indexes


def _error_code(exc_info) -> int:
    return exc_info.value.orig.args[0]


# --- Structure -------------------------------------------------------------------------


@pytest.mark.parametrize("table", sorted(EXPECTED_COLUMNS))
def test_columns_match_spec(conn, table):
    rows = _rows(
        conn,
        "SELECT COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :table",
        table=table,
    )
    actual = {name: (column_type, nullable == "YES") for name, column_type, nullable in rows}
    assert actual == EXPECTED_COLUMNS[table]


def test_tables_are_innodb_utf8mb4_0900_ai_ci(conn):
    rows = _rows(
        conn,
        "SELECT TABLE_NAME, ENGINE, TABLE_COLLATION FROM information_schema.TABLES "
        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME != 'alembic_version'",
    )
    assert {row[0] for row in rows} == set(EXPECTED_COLUMNS)
    assert {(engine, collation) for _, engine, collation in rows} == {
        ("InnoDB", "utf8mb4_0900_ai_ci")
    }


def test_text_columns_use_utf8mb4_0900_ai_ci(conn):
    rows = _rows(
        conn,
        "SELECT DISTINCT CHARACTER_SET_NAME, COLLATION_NAME FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME != 'alembic_version' "
        "AND COLLATION_NAME IS NOT NULL",
    )
    assert rows == [("utf8mb4", "utf8mb4_0900_ai_ci")]


def test_primary_keys(conn):
    actual = {
        table: columns
        for (table, name), (_, columns) in _indexes(conn).items()
        if name == "PRIMARY" and table != "alembic_version"
    }
    assert actual == EXPECTED_PRIMARY_KEYS


def test_id_columns_auto_increment(conn):
    rows = _rows(
        conn,
        "SELECT TABLE_NAME FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE() "
        "AND COLUMN_NAME = 'id' AND EXTRA LIKE '%auto_increment%'",
    )
    assert {row[0] for row in rows} == {t for t, cols in EXPECTED_COLUMNS.items() if "id" in cols}


def test_unique_keys(conn):
    actual = {
        (table, columns)
        for (table, name), (unique, columns) in _indexes(conn).items()
        if unique and name != "PRIMARY" and table != "alembic_version"
    }
    assert actual == EXPECTED_UNIQUE_KEYS


def test_indexed_columns(conn):
    leading = {(table, columns[0]) for (table, _), (_, columns) in _indexes(conn).items()}
    assert EXPECTED_INDEXED <= leading


def test_room_photos_indexed_by_room_and_sort_order(conn):
    composite = {(table, columns) for (table, _), (_, columns) in _indexes(conn).items()}
    assert ("room_photos", ("room_id", "sort_order")) in composite


def test_foreign_keys_restrict_on_delete_and_update(conn):
    rows = _rows(
        conn,
        "SELECT k.TABLE_NAME, k.COLUMN_NAME, k.REFERENCED_TABLE_NAME, k.REFERENCED_COLUMN_NAME, "
        "r.DELETE_RULE, r.UPDATE_RULE "
        "FROM information_schema.KEY_COLUMN_USAGE k "
        "JOIN information_schema.REFERENTIAL_CONSTRAINTS r "
        "ON r.CONSTRAINT_SCHEMA = k.CONSTRAINT_SCHEMA AND r.CONSTRAINT_NAME = k.CONSTRAINT_NAME "
        "WHERE k.TABLE_SCHEMA = DATABASE() AND k.REFERENCED_TABLE_NAME IS NOT NULL",
    )
    assert {(t, c, ref) for t, c, ref, *_ in rows} == EXPECTED_FOREIGN_KEYS
    assert {(ref_col, delete, update) for *_, ref_col, delete, update in rows} == {
        ("id", "RESTRICT", "RESTRICT")
    }


def test_column_defaults(conn):
    rows = _rows(
        conn,
        "SELECT TABLE_NAME, COLUMN_NAME, COLUMN_DEFAULT FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA = DATABASE() AND COLUMN_NAME IN "
        "('is_active', 'sort_order', 'email_notifications', 'must_change_password')",
    )
    defaults = {(table, column): default for table, column, default in rows}
    for (table, column), default in defaults.items():
        expected = "0" if column == "sort_order" else "1"
        assert default == expected, f"{table}.{column}"
    assert ("users", "email_notifications") in defaults
    assert ("users", "must_change_password") in defaults


# --- Behaviour -------------------------------------------------------------------------


def _insert(conn, table: str, **values) -> int:
    result = conn.execute(Base.metadata.tables[table].insert().values(**values))
    return result.inserted_primary_key[0]


def _location(conn, name_en="Head Office", name_kh="ការិយាល័យ") -> int:
    return _insert(conn, "locations", name_en=name_en, name_kh=name_kh, province="PHNOM_PENH")


def _building(conn, location_id, name_en="Building A") -> int:
    return _insert(conn, "buildings", location_id=location_id, name_en=name_en, name_kh="អគារ")


def _floor(conn, building_id, floor_label="1") -> int:
    return _insert(conn, "floors", building_id=building_id, floor_label=floor_label)


def _category(conn, name_en="Meeting room") -> int:
    return _insert(conn, "categories", name_en=name_en, name_kh="បន្ទប់ប្រជុំ")


def _room(conn, floor_id, category_id, name_en="Mekong Room", **values) -> int:
    values = {"capacity": 10, "start_time": time(8), "end_time": time(18), **values}
    return _insert(
        conn,
        "rooms",
        floor_id=floor_id,
        category_id=category_id,
        name_en=name_en,
        name_kh="បន្ទប់",
        **values,
    )


def _room_chain(conn) -> dict[str, int]:
    location_id = _location(conn)
    building_id = _building(conn, location_id)
    floor_id = _floor(conn, building_id)
    category_id = _category(conn)
    room_id = _room(conn, floor_id, category_id)
    return {"location": location_id, "building": building_id, "floor": floor_id, "room": room_id}


def _position(conn, name_en="Manager") -> int:
    return _insert(conn, "positions", name_en=name_en, name_kh="ប្រធាន")


def _user(conn, position_id, staff_id="EMP-1", email="a@company.com") -> int:
    return _insert(
        conn,
        "users",
        staff_id=staff_id,
        name_en="Sok Dara",
        name_kh="សុខ ដារ៉ា",
        position_id=position_id,
        email=email,
        password_hash="hash",
    )


def _fails(conn, code: int, statement) -> None:
    with pytest.raises(DBAPIError) as exc_info, conn.begin_nested():
        statement()
    assert _error_code(exc_info) == code


def test_defaults_applied_on_insert(conn):
    location_id = _location(conn)
    building_id = _building(conn, location_id)
    position_id = _position(conn)
    user_id = _user(conn, position_id)

    building = _rows(
        conn, "SELECT is_active, sort_order FROM buildings WHERE id = :id", id=building_id
    )
    assert building == [(1, 0)]
    user = _rows(
        conn,
        "SELECT email_notifications, must_change_password, is_active FROM users WHERE id = :id",
        id=user_id,
    )
    assert user == [(1, 1, 1)]


@pytest.mark.parametrize("duplicate", ["Head Office", "head office", "HEAD OFFICE", "Héad Office"])
def test_location_name_unique_ignoring_case_and_accents(conn, duplicate):
    _location(conn, "Head Office")
    _fails(conn, ER_DUP_ENTRY, lambda: _location(conn, duplicate))


def test_building_name_unique_per_location(conn):
    first, second = _location(conn, "Head Office"), _location(conn, "Branch")
    _building(conn, first, "Building A")
    _building(conn, second, "Building A")  # same name, other location: allowed
    _fails(conn, ER_DUP_ENTRY, lambda: _building(conn, first, "building a"))


def test_floor_label_unique_per_building(conn):
    location_id = _location(conn)
    first, second = _building(conn, location_id, "A"), _building(conn, location_id, "B")
    _floor(conn, first, "3rd floor")
    _floor(conn, second, "3rd floor")
    _fails(conn, ER_DUP_ENTRY, lambda: _floor(conn, first, "3RD FLOOR"))


def test_room_name_unique_per_floor(conn):
    chain = _room_chain(conn)
    other_floor = _floor(conn, chain["building"], "2")
    category_id = _category(conn, "Training room")
    _room(conn, other_floor, category_id, "Mekong Room")
    _fails(conn, ER_DUP_ENTRY, lambda: _room(conn, chain["floor"], category_id, "mekong room"))


@pytest.mark.parametrize(
    ("table", "values"),
    [
        ("categories", {"name_en": "Meeting room", "name_kh": "ក"}),
        ("equipment", {"name": "Projector"}),
        ("positions", {"name_en": "Manager", "name_kh": "ក"}),
        ("roles", {"code": "ADMIN", "name_en": "Admin", "name_kh": "Admin"}),
    ],
)
def test_global_names_unique_ignoring_case(conn, table, values):
    _insert(conn, table, **values)
    upper = {k: v.upper() for k, v in values.items()}
    _fails(conn, ER_DUP_ENTRY, lambda: _insert(conn, table, **upper))


def test_department_name_unique_per_location(conn):
    first, second = _location(conn, "Head Office"), _location(conn, "Branch")
    _insert(conn, "departments", location_id=first, name_en="Operations", name_kh="ក")
    _insert(conn, "departments", location_id=second, name_en="Operations", name_kh="ក")
    _fails(
        conn,
        ER_DUP_ENTRY,
        lambda: _insert(conn, "departments", location_id=first, name_en="operations", name_kh="ក"),
    )


def test_division_name_unique_per_department(conn):
    location_id = _location(conn)
    department_id = _insert(
        conn, "departments", location_id=location_id, name_en="Ops", name_kh="ក"
    )
    _insert(conn, "divisions", department_id=department_id, name_en="IT Division", name_kh="ក")
    _fails(
        conn,
        ER_DUP_ENTRY,
        lambda: _insert(
            conn, "divisions", department_id=department_id, name_en="it division", name_kh="ក"
        ),
    )


def test_user_email_and_staff_id_unique(conn):
    position_id = _position(conn)
    _user(conn, position_id, staff_id="EMP-1", email="a@company.com")
    _fails(
        conn,
        ER_DUP_ENTRY,
        lambda: _user(conn, position_id, staff_id="EMP-2", email="A@Company.com"),
    )
    _fails(
        conn,
        ER_DUP_ENTRY,
        lambda: _user(conn, position_id, staff_id="emp-1", email="b@company.com"),
    )


def test_user_can_hold_a_role_only_once(conn):
    user_id = _user(conn, _position(conn))
    role_id = _insert(conn, "roles", code="STAFF", name_en="Staff", name_kh="Staff")
    _insert(conn, "user_roles", user_id=user_id, role_id=role_id)
    _fails(
        conn, ER_DUP_ENTRY, lambda: _insert(conn, "user_roles", user_id=user_id, role_id=role_id)
    )


def test_room_can_have_equipment_only_once(conn):
    room_id = _room_chain(conn)["room"]
    equipment_id = _insert(conn, "equipment", name="Projector")
    _insert(conn, "room_equipment", room_id=room_id, equipment_id=equipment_id)
    _fails(
        conn,
        ER_DUP_ENTRY,
        lambda: _insert(conn, "room_equipment", room_id=room_id, equipment_id=equipment_id),
    )


def test_khmer_name_of_100_characters_fits(conn):
    khmer = "ក" * 100  # 300 bytes in UTF-8; the limit counts characters
    location_id = _location(conn, "Khmer", name_kh=khmer)
    assert _rows(conn, "SELECT name_kh FROM locations WHERE id = :id", id=location_id) == [(khmer,)]


def test_name_of_101_characters_is_refused(conn):
    _fails(
        conn,
        ER_DATA_TOO_LONG,
        lambda: _insert(conn, "locations", name_en="x" * 101, name_kh="k", province="KANDAL"),
    )


def test_room_capacity_must_be_at_least_1(conn):
    chain = _room_chain(conn)
    category_id = _category(conn, "Other")
    _fails(
        conn,
        ER_CHECK_CONSTRAINT_VIOLATED,
        lambda: _room(conn, chain["floor"], category_id, "Small", capacity=0),
    )


@pytest.mark.parametrize(("start", "end"), [(time(9), time(9)), (time(18), time(8))])
def test_room_start_time_before_end_time(conn, start, end):
    chain = _room_chain(conn)
    category_id = _category(conn, "Other")
    _fails(
        conn,
        ER_CHECK_CONSTRAINT_VIOLATED,
        lambda: _room(conn, chain["floor"], category_id, "Late", start_time=start, end_time=end),
    )


def test_room_without_owner_is_allowed(conn):
    room_id = _room_chain(conn)["room"]
    assert _rows(conn, "SELECT room_owner_id FROM rooms WHERE id = :id", id=room_id) == [(None,)]


def test_foreign_key_must_point_to_existing_row(conn):
    _fails(conn, ER_NO_REFERENCED_ROW_2, lambda: _building(conn, 999_999))


def test_parent_with_children_cannot_be_deleted(conn):
    chain = _room_chain(conn)
    _fails(
        conn,
        ER_ROW_IS_REFERENCED_2,
        lambda: _rows(conn, "DELETE FROM locations WHERE id = :id", id=chain["location"]),
    )


def test_room_photo_rows_can_be_deleted(conn):
    room_id = _room_chain(conn)["room"]
    photo_id = _insert(
        conn,
        "room_photos",
        room_id=room_id,
        url="/u/a.jpg",
        thumbnail_url="/u/a_t.jpg",
        sort_order=1,
    )
    conn.execute(text("DELETE FROM room_photos WHERE id = :id"), {"id": photo_id})
    assert _rows(conn, "SELECT id FROM room_photos WHERE id = :id", id=photo_id) == []


# --- Timestamps ------------------------------------------------------------------------


def test_utcnow_is_naive_utc_without_microseconds():
    now = utcnow()
    assert now.tzinfo is None
    assert now.microsecond == 0
    assert abs((datetime.now(UTC).replace(tzinfo=None) - now).total_seconds()) < 5


def test_timestamps_set_on_create_and_updated_only_on_real_change(conn):
    old = datetime(2026, 1, 1, 0, 0, 0)
    with Session(bind=conn, join_transaction_mode="create_savepoint") as session:
        location = Location(name_en="Head Office", name_kh="ក", province="PHNOM_PENH")
        session.add(location)
        session.flush()
        assert location.created_at is not None
        assert location.updated_at is not None

        location.updated_at = old
        session.flush()

        location.name_en = "Head Office"  # same value: no UPDATE, updated_at unchanged
        session.flush()
        assert session.scalar(select(Location.updated_at).where(Location.id == location.id)) == old

        location.name_en = "Main Office"
        session.flush()
        assert session.scalar(select(Location.updated_at).where(Location.id == location.id)) > old
