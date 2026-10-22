import pytest
from argon2 import PasswordHasher
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import Settings
from app.models import Position, Role, User, user_roles
from scripts.seed import ADMIN_POSITION_NAME, SeedError, main, seed
from tests.conftest import TEST_DATABASE_URL, TEST_JWT_SECRET


def make_settings(**overrides) -> Settings:
    values = {
        "database_url": TEST_DATABASE_URL,
        "jwt_secret": TEST_JWT_SECRET,
        "first_admin_email": "  Admin@Company.COM ",
        "first_admin_password": "FirstAdmin@2026",
        "first_admin_staff_id": "ADMIN-001",
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


@pytest.fixture
def session(conn):
    with Session(bind=conn, join_transaction_mode="create_savepoint") as session:
        yield session


def count(session, model_or_table) -> int:
    return session.scalar(select(func.count()).select_from(model_or_table))


def admin(session) -> User:
    return session.scalars(select(User).where(User.email == "admin@company.com")).one()


def test_seed_creates_six_roles_in_order(session):
    seed(session, make_settings())
    roles = session.scalars(select(Role).order_by(Role.id)).all()
    assert [(r.code, r.name_en, r.name_kh) for r in roles] == [
        ("ADMIN", "Admin", "Admin"),
        ("ROOM_OWNER", "Room owner", "Room owner"),
        ("STAFF", "Staff", "Staff"),
        ("PITIKA", "Pitika", "Pitika"),
        ("IT_LEAD", "IT Lead", "IT Lead"),
        ("IT_STAFF", "IT Staff", "IT Staff"),
    ]
    assert all(role.is_active for role in roles)


def test_seed_creates_system_administrator_position(session):
    seed(session, make_settings())
    position = session.scalars(select(Position)).one()
    assert position.name_en == ADMIN_POSITION_NAME == "System Administrator"
    assert position.name_kh == position.name_en
    assert position.is_active


def test_seed_creates_first_admin(session):
    seed(session, make_settings())
    user = admin(session)
    assert user.staff_id == "ADMIN-001"
    assert user.division_id is None
    assert user.position_id == session.scalars(select(Position.id)).one()
    assert user.must_change_password is True
    assert user.is_active is True
    assert user.password_hash.startswith("$argon2id$")
    assert PasswordHasher().verify(user.password_hash, "FirstAdmin@2026")
    role_codes = session.scalars(
        select(Role.code).join(user_roles).where(user_roles.c.user_id == user.id)
    ).all()
    assert role_codes == ["ADMIN"]


def test_seed_twice_creates_nothing_new(session):
    first = seed(session, make_settings())
    second = seed(session, make_settings())
    assert count(session, Role) == 6
    assert count(session, Position) == 1
    assert count(session, User) == 1
    assert count(session, user_roles) == 1
    assert first.created_anything
    assert not second.created_anything


def test_seed_does_not_change_existing_role_names(session):
    session.add(Role(code="STAFF", name_en="Staff", name_kh="បុគ្គលិក"))
    session.flush()
    seed(session, make_settings())
    staff = session.scalars(select(Role).where(Role.code == "STAFF")).one()
    assert staff.name_kh == "បុគ្គលិក"
    assert count(session, Role) == 6


def test_seed_leaves_existing_admin_unchanged(session):
    seed(session, make_settings())
    user = admin(session)
    user.must_change_password = False
    original_hash = user.password_hash
    session.flush()

    seed(session, make_settings(first_admin_password="Different@2026", first_admin_staff_id="X"))
    session.refresh(user)
    assert user.password_hash == original_hash
    assert user.staff_id == "ADMIN-001"
    assert user.must_change_password is False


@pytest.mark.parametrize(
    "missing", ["first_admin_email", "first_admin_password", "first_admin_staff_id"]
)
@pytest.mark.parametrize("value", [None, "   "])
def test_seed_stops_when_admin_variable_missing(session, missing, value):
    with pytest.raises(SeedError, match=missing.upper()):
        seed(session, make_settings(**{missing: value}))
    assert count(session, Role) == 0
    assert count(session, User) == 0


@pytest.mark.parametrize(
    ("password", "message"),
    [
        ("Short@1", "8 to 128"),
        ("x" * 129, "8 to 128"),
        ("admin@company.com", "email"),
        ("ADMIN@company.com", "email"),
    ],
)
def test_seed_refuses_weak_admin_password(session, password, message):
    with pytest.raises(SeedError, match=message):
        seed(session, make_settings(first_admin_password=password))
    assert count(session, User) == 0


def test_seed_refuses_staff_id_used_by_another_user(session):
    session.add(Position(name_en="Manager", name_kh="ប្រធាន"))
    session.flush()
    position_id = session.scalars(select(Position.id)).one()
    session.add(
        User(
            staff_id="ADMIN-001",
            name_en="Someone",
            name_kh="Someone",
            email="someone@company.com",
            position_id=position_id,
            password_hash="x",
        )
    )
    session.flush()
    with pytest.raises(SeedError, match="ADMIN-001"):
        seed(session, make_settings())


def test_main_reports_missing_variable_and_fails(capsys):
    assert main(make_settings(first_admin_email=None)) == 1
    assert "FIRST_ADMIN_EMAIL" in capsys.readouterr().err
