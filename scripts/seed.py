"""Create the six roles, the "System Administrator" position and the first Admin (spec section 8).

Safe to run many times: it inserts what is missing and changes nothing that exists.

Usage (from the project folder):  python -m scripts.seed
"""

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.constants.roles import RoleCode
from app.db import create_db_engine
from app.models import Position, Role, User, user_roles
from app.security import hash_password

ROLES_FILE = Path(__file__).with_name("seed_roles.json")
ADMIN_POSITION_NAME = "System Administrator"
ADMIN_NAME = "System Administrator"


class SeedError(Exception):
    """A problem the person running the seed must fix. Nothing is saved."""


@dataclass
class SeedResult:
    roles_created: list[str] = field(default_factory=list)
    position_created: bool = False
    admin_created: bool = False

    @property
    def created_anything(self) -> bool:
        return bool(self.roles_created or self.position_created or self.admin_created)


@dataclass(frozen=True)
class _Admin:
    email: str
    password: str
    staff_id: str


def _admin_from_settings(settings: Settings) -> _Admin:
    values = {
        "FIRST_ADMIN_EMAIL": settings.first_admin_email,
        "FIRST_ADMIN_PASSWORD": settings.first_admin_password,
        "FIRST_ADMIN_STAFF_ID": settings.first_admin_staff_id,
    }
    missing = [name for name, value in values.items() if not (value and value.strip())]
    if missing:
        raise SeedError(f"Set {', '.join(missing)} in the environment or .env, then run again.")

    email = settings.first_admin_email.strip().lower()
    password = settings.first_admin_password  # never trimmed
    staff_id = settings.first_admin_staff_id.strip()

    if len(email) > 254 or "@" not in email:
        raise SeedError("FIRST_ADMIN_EMAIL must be a valid email of at most 254 characters.")
    if len(staff_id) > 20:
        raise SeedError("FIRST_ADMIN_STAFF_ID must be at most 20 characters.")
    # Rule R18 for every new password.
    if not 8 <= len(password) <= 128:
        raise SeedError("FIRST_ADMIN_PASSWORD must be 8 to 128 characters.")
    if password.lower() == email:
        raise SeedError("FIRST_ADMIN_PASSWORD cannot be the same as the email.")
    return _Admin(email=email, password=password, staff_id=staff_id)


def _load_roles() -> list[dict[str, str]]:
    roles = json.loads(ROLES_FILE.read_text(encoding="utf-8"))
    codes = [role.get("code") for role in roles]
    if codes != [code.value for code in RoleCode]:
        raise SeedError(
            f"{ROLES_FILE.name} must list exactly these codes in order: {list(RoleCode)}."
        )
    return roles


def seed(session: Session, settings: Settings) -> SeedResult:
    """Insert what is missing. Flushes but does not commit; the caller commits."""
    admin = _admin_from_settings(settings)
    roles = _load_roles()
    admin_exists = session.scalar(select(User.id).where(User.email == admin.email)) is not None
    if not admin_exists:
        taken = session.scalar(select(User.email).where(User.staff_id == admin.staff_id))
        if taken is not None:
            raise SeedError(f"Staff ID {admin.staff_id} is already used by {taken}.")

    result = SeedResult()

    existing_codes = set(session.scalars(select(Role.code)))
    for role in roles:
        if role["code"] not in existing_codes:
            session.add(Role(code=role["code"], name_en=role["name_en"], name_kh=role["name_kh"]))
            result.roles_created.append(role["code"])
    session.flush()

    position = session.scalars(
        select(Position).where(Position.name_en == ADMIN_POSITION_NAME)
    ).first()
    if position is None:
        position = Position(name_en=ADMIN_POSITION_NAME, name_kh=ADMIN_POSITION_NAME)
        session.add(position)
        session.flush()
        result.position_created = True

    if not admin_exists:
        user = User(
            staff_id=admin.staff_id,
            name_en=ADMIN_NAME,
            name_kh=ADMIN_NAME,
            email=admin.email,
            position_id=position.id,
            division_id=None,
            password_hash=hash_password(admin.password),
            must_change_password=True,
        )
        session.add(user)
        session.flush()
        admin_role_id = session.scalar(select(Role.id).where(Role.code == RoleCode.ADMIN))
        session.execute(user_roles.insert().values(user_id=user.id, role_id=admin_role_id))
        result.admin_created = True

    return result


def main(settings: Settings | None = None) -> int:
    settings = settings or get_settings()
    engine = create_db_engine(settings.database_url)
    try:
        with Session(engine) as session:
            try:
                result = seed(session, settings)
            except SeedError as exc:
                session.rollback()
                print(f"Seed stopped: {exc}", file=sys.stderr)
                return 1
            session.commit()
    finally:
        engine.dispose()

    if not result.created_anything:
        print("Seed: nothing to do, everything already exists.")
        return 0
    if result.roles_created:
        print(f"Seed: created roles {', '.join(result.roles_created)}.")
    if result.position_created:
        print(f'Seed: created position "{ADMIN_POSITION_NAME}".')
    if result.admin_created:
        print(
            f"Seed: created the first Admin ({settings.first_admin_email.strip().lower()}). "
            "They must change the password at first sign-in."
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
