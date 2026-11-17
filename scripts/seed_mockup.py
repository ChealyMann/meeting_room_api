"""Demo data from the frontend mockup: offices, buildings, floors, room categories, equipment,
the 16 mockup rooms with their photos, and demo users (the mockup's 3 room owners and 7 IT
staff, plus a Pitika, an IT lead and 3 staff).

NOT for production. Run it by hand on a dev database, after `python -m scripts.seed` and
`python -m scripts.seed_org` (users are put in divisions of the Head Office):

    python -m scripts.seed_mockup

Rooms and IT staff come from scripts/seed_mockup.json, made from
frontend_mockup/meeting_room_mockup/js/data.js. Photos and IT staff avatars are read from that
mockup folder (it is not in git); a missing file is skipped. Demo users sign in with
DEMO_PASSWORD. Safe to run many times: records are matched by name or email and only added
when missing; photos are added only to rooms this run creates.
"""

import json
import re
import sys
import uuid
from dataclasses import dataclass
from datetime import time
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.constants.roles import RoleCode
from app.db import create_db_engine
from app.models import (
    Building,
    Category,
    Department,
    Division,
    Equipment,
    Floor,
    Location,
    Position,
    Role,
    Room,
    RoomPhoto,
    User,
    room_equipment,
    user_roles,
)
from app.security import hash_password
from app.services.room_photo import process_image
from app.services.user_avatar import make_avatar_jpeg

DATA_FILE = Path(__file__).with_name("seed_mockup.json")
MOCKUP_DIR = Path(__file__).resolve().parent.parent / "frontend_mockup" / "meeting_room_mockup"
DEMO_PASSWORD = "Demo@12345"
# Opening hours by room type (rooms keep their own hours; owner, 17 Nov 2026). Others 07:30-18:00.
HOURS_BY_CATEGORY = {
    "Executive Room": (time(8, 0), time(17, 0)),
    "Executive Suite": (time(8, 0), time(17, 0)),
    "Private Office": (time(8, 0), time(17, 0)),
    "Regional Boardroom": (time(8, 0), time(17, 0)),
    "Grand Hall": (time(7, 0), time(18, 0)),
    "Seminar Room": (time(8, 0), time(16, 30)),
}
DEFAULT_HOURS = (time(7, 30), time(18, 0))


def room_hours(category: str) -> tuple[time, time]:
    """Opening and closing time for a mockup room of this type."""
    return HOURS_BY_CATEGORY.get(category, DEFAULT_HOURS)


# Offices seed_org does not make: name_en -> (name_kh, province).
NEW_OFFICES = {
    "IT Department Building": ("អគារនាយកដ្ឋានព័ត៌មានវិទ្យា", "PHNOM_PENH"),
    "Sen Sok Building": ("អគារសែនសុខ", "PHNOM_PENH"),
    "Battambang Branch": ("សាខាធនាគារជាតិនៃកម្ពុជា ខេត្តបាត់ដំបង", "BATTAMBANG"),
    "Siem Reap Branch": ("សាខាធនាគារជាតិនៃកម្ពុជា ខេត្តសៀមរាប", "SIEM_REAP"),
}

CATEGORIES = {
    "Executive Room": "បន្ទប់ប្រជុំថ្នាក់ដឹកនាំ",
    "Team Room": "បន្ទប់ប្រជុំក្រុម",
    "Grand Hall": "សាលប្រជុំធំ",
    "Small Room": "បន្ទប់ប្រជុំតូច",
    "Tech Room": "បន្ទប់បច្ចេកវិទ្យា",
    "Visitor Room": "បន្ទប់ទទួលភ្ញៀវ",
    "Private Office": "ការិយាល័យឯកជន",
    "Regional Boardroom": "បន្ទប់ប្រជុំថ្នាក់តំបន់",
    "Executive Suite": "បន្ទប់ប្រជុំប្រតិបត្តិ",
    "Seminar Room": "បន្ទប់សិក្ខាសាលា",
}

# The mockup lists free-text features; they are grouped into these equipment items.
# (name, Lucide icon, words that match a feature, ignoring case)
EQUIPMENT = [
    ("Projector", "projector", ("projector",)),
    ("Wireless screen sharing", "cast", ("screen sharing", "wireless presentation")),
    ("Display screen", "monitor", ("tv", "display", "screen", "monitor")),
    ("Video conference camera", "video", ("camera", "video", "broadcast")),
    ("Microphones", "mic", ("microphone",)),
    ("Speakers", "speaker", ("speaker", "audio")),
    ("Whiteboard", "presentation", ("whiteboard",)),
    ("Wi-Fi", "wifi", ("wi-fi",)),
    ("Coffee and tea", "coffee", ("coffee", "beverage", "refreshment")),
    ("Stage and podium", "mic-vocal", ("stage", "podium", "lectern")),
    ("Network ports", "ethernet-port", ("ethernet",)),
    ("Air conditioning", "air-vent", ("air conditioning",)),
]
# A projector or screen-sharing feature already names its screen.
_SCREEN_OWNERS = {"Projector", "Wireless screen sharing"}

# name_en -> name_kh
POSITIONS = {
    "Executive Board Secretary": "លេខាធិការក្រុមប្រឹក្សាភិបាល",
    "Chief of CAFIU Security": "ប្រធានផ្នែកសន្តិសុខ CAFIU",
    "Senior Finance Officer": "មន្ត្រីហិរញ្ញវត្ថុជាន់ខ្ពស់",
    "IT Support": "មន្ត្រីគាំទ្រព័ត៌មានវិទ្យា",
    "IT Team Lead": "ប្រធានក្រុមព័ត៌មានវិទ្យា",
    "Protocol Officer": "មន្ត្រីពិធីការ",
    "Officer": "មន្ត្រី",
}

IT_DIVISION = ("Information Technology Department", "IT Administration and Operations")


@dataclass(frozen=True)
class DemoUser:
    staff_id: str
    title: str | None
    name_en: str
    name_kh: str
    email: str
    phone: str
    position: str
    division: tuple[str, str]  # (department name_en, division name_en)
    roles: tuple[RoleCode, ...]
    avatar: str | None = None  # inside MOCKUP_DIR


def _owner(staff_id, title, name_en, name_kh, email, phone, position, division):
    return DemoUser(
        staff_id, title, name_en, name_kh, email, phone, position, division, (RoleCode.ROOM_OWNER,)
    )


# The mockup's room owners (staff IDs match owner_staff_id in the JSON file).
OWNERS = [
    _owner(
        "OWNER-01",
        "H.E.",
        "Chea Serey",
        "ជា សេរី",
        "chea.serey@example.com",
        "Ext. 8801",
        "Executive Board Secretary",
        ("Cabinet", "Governor's Secretariat"),
    ),
    _owner(
        "OWNER-02",
        "Dr.",
        "Sokhom Phan",
        "ផាន់ សុខុម",
        "sokhom.phan@example.com",
        "Ext. 8502",
        "Chief of CAFIU Security",
        ("Department of Internal Affairs", "Administration"),
    ),
    _owner(
        "OWNER-VANCE",
        "Mr.",
        "Jonathan Vance",
        "ចូណាថាន វ៉ាន់",
        "jonathan.vance@example.com",
        "Ext. 8421",
        "Senior Finance Officer",
        ("Accounting Department", "Finance and Budget"),
    ),
]

# English names and emails for the mockup's IT staff (the mockup has Khmer names only).
IT_STAFF_EN = {
    "2503": ("Hy Mengsrey", "mengsrey.hy@example.com"),
    "CS 0133": ("Yen Boren", "boren.yen@example.com"),
    "2507": ("Chey Sovann", "sovann.chey@example.com"),
    "CS-0130": ("Vina Darith", "darith.vina@example.com"),
    "2192": ("Rotha Thanuch", "thanuch.rotha@example.com"),
    "CS-0134": ("Cheng Chhunputhirangsey", "chhunputhirangsey.cheng@example.com"),
    "2188": ("Yang Bunleng", "bunleng.yang@example.com"),
}

# Not in the mockup: one user for each other role, so every page can be tried.
OTHERS = [
    DemoUser(
        "DEMO-101",
        None,
        "Chan Sophea",
        "ចាន់ សុភា",
        "demo.pitika@example.com",
        "012 000 101",
        "Protocol Officer",
        ("Cabinet", "Protocol"),
        (RoleCode.PITIKA,),
    ),
    DemoUser(
        "DEMO-102",
        None,
        "Lim Dara",
        "លឹម ដារា",
        "demo.itlead@example.com",
        "012 000 102",
        "IT Team Lead",
        IT_DIVISION,
        (RoleCode.IT_LEAD,),
    ),
    DemoUser(
        "DEMO-103",
        None,
        "Heng Rathana",
        "ហេង រតនា",
        "demo.staff1@example.com",
        "012 000 103",
        "Officer",
        ("Statistics Department", "Monetary and Financial Statistics"),
        (RoleCode.STAFF,),
    ),
    DemoUser(
        "DEMO-104",
        None,
        "Meas Sreyneang",
        "មាស ស្រីនាង",
        "demo.staff2@example.com",
        "012 000 104",
        "Officer",
        ("Monetary Policy and Research Department", "Research"),
        (RoleCode.STAFF,),
    ),
    DemoUser(
        "DEMO-105",
        None,
        "Touch Bunthoeun",
        "ទូច ប៊ុនធឿន",
        "demo.staff3@example.com",
        "012 000 105",
        "Officer",
        ("Personnel Department", "Training"),
        (RoleCode.STAFF,),
    ),
]


@dataclass
class MockupResult:
    offices: int = 0
    buildings: int = 0
    floors: int = 0
    categories: int = 0
    equipment: int = 0
    users: int = 0
    rooms: int = 0
    photos: int = 0


class MockupError(Exception):
    """Something the person running the seed must fix first. Nothing is saved."""


def _one(session: Session, model, **where):
    return session.scalars(select(model).filter_by(**where)).first()


def _get_or_add(session: Session, model, lookup: dict, values: dict) -> tuple[object, bool]:
    record = _one(session, model, **lookup)
    if record is not None:
        return record, False
    record = model(**lookup, **values)
    session.add(record)
    session.flush()
    return record, True


def _floor_order(label: str) -> int:
    match = re.match(r"Floor (\d+)", label)
    return int(match.group(1)) if match else 0


def _equipment_names(features: list[str]) -> list[str]:
    names: list[str] = []
    for feature in features:
        text = feature.lower()
        hits = [name for name, _, words in EQUIPMENT if any(w in text for w in words)]
        if _SCREEN_OWNERS & set(hits):
            hits = [name for name in hits if name != "Display screen"]
        names += [name for name in hits if name not in names]
    return names


def _places(session: Session, offices: list[dict], result: MockupResult) -> dict:
    """Offices, buildings and floors. Returns {(office, building, floor label): Floor}."""
    floors: dict[tuple[str, str, str], Floor] = {}
    for spec in offices:
        location = _one(session, Location, name_en=spec["name_en"])
        if location is None:
            if spec["name_en"] not in NEW_OFFICES:
                raise MockupError(f'Office "{spec["name_en"]}" is missing: run scripts.seed_org.')
            name_kh, province = NEW_OFFICES[spec["name_en"]]
            location = Location(name_en=spec["name_en"], name_kh=name_kh, province=province)
            session.add(location)
            result.offices += 1
        location.address = location.address or spec["address"]
        location.map_query = location.map_query or spec["map_query"]
        session.flush()
        for order, b in enumerate(spec["buildings"], start=1):
            building, created = _get_or_add(
                session,
                Building,
                {"location_id": location.id, "name_en": b["name_en"]},
                {"name_kh": b["name_kh"], "short_name": b["short_name"], "sort_order": order},
            )
            result.buildings += created
            for label in b["floors"]:
                floor, created = _get_or_add(
                    session,
                    Floor,
                    {"building_id": building.id, "floor_label": label},
                    {"sort_order": _floor_order(label)},
                )
                result.floors += created
                floors[(spec["name_en"], b["name_en"], label)] = floor
    return floors


def _catalog(session: Session, result: MockupResult) -> tuple[dict, dict]:
    categories = {}
    for order, (name_en, name_kh) in enumerate(CATEGORIES.items(), start=1):
        categories[name_en], created = _get_or_add(
            session, Category, {"name_en": name_en}, {"name_kh": name_kh, "sort_order": order}
        )
        result.categories += created
    equipment = {}
    for order, (name, icon, _) in enumerate(EQUIPMENT, start=1):
        equipment[name], created = _get_or_add(
            session, Equipment, {"name": name}, {"icon": icon, "sort_order": order}
        )
        result.equipment += created
    return categories, equipment


def _division(session: Session, department: str, division: str) -> Division:
    found = session.scalars(
        select(Division)
        .join(Department, Division.department_id == Department.id)
        .where(Department.name_en == department, Division.name_en == division)
    ).first()
    if found is None:
        raise MockupError(f'Division "{division}" of "{department}" is missing: run seed_org.')
    return found


def _save_avatar(settings: Settings, user: User, avatar: str | None) -> None:
    source = MOCKUP_DIR / avatar if avatar else None
    if source is None or not source.is_file():
        if avatar:
            print(f"  skipped missing avatar {avatar}")
        return
    stored = f"users/{user.id}/{uuid.uuid4()}.jpg"
    path = settings.avatar_dir / stored
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(make_avatar_jpeg(source.read_bytes()))
    user.user_avatar = stored


def _users(session: Session, settings: Settings, it_staff: list[dict], result: MockupResult):
    """Returns {staff_id: User} for every demo user."""
    role_ids = {r.code: r.id for r in session.scalars(select(Role))}
    positions = {}
    for name_en, name_kh in POSITIONS.items():
        positions[name_en], _ = _get_or_add(
            session, Position, {"name_en": name_en}, {"name_kh": name_kh}
        )

    it_people = []
    for s in it_staff:
        name_en, email = IT_STAFF_EN[s["staff_id"]]
        it_people.append(
            DemoUser(
                s["staff_id"],
                None,
                name_en,
                s["name_kh"],
                email,
                s["phone"],
                "IT Support",
                IT_DIVISION,
                (RoleCode.IT_STAFF,),
                s["avatar"],
            )
        )
    people = OWNERS + it_people + OTHERS
    password_hash = hash_password(DEMO_PASSWORD)
    users: dict[str, User] = {}
    for p in people:
        user = _one(session, User, email=p.email)
        if user is None:
            user = User(
                staff_id=p.staff_id,
                title=p.title,
                name_en=p.name_en,
                name_kh=p.name_kh,
                email=p.email,
                phone=p.phone,
                position_id=positions[p.position].id,
                division_id=_division(session, *p.division).id,
                password_hash=password_hash,
                must_change_password=False,
            )
            session.add(user)
            session.flush()
            for role in p.roles:
                session.execute(user_roles.insert().values(user_id=user.id, role_id=role_ids[role]))
            _save_avatar(settings, user, p.avatar)
            result.users += 1
            print(f"  user {p.email} ({', '.join(p.roles)})")
        users[p.staff_id] = user
    return users


def _add_photos(settings: Settings, session: Session, room: Room, photos: list[str]) -> int:
    added = 0
    for order, photo in enumerate(photos, start=1):
        source = MOCKUP_DIR / photo
        if not source.is_file():
            print(f"  skipped missing photo {photo}")
            continue
        main, thumbnail = process_image(source.read_bytes())
        folder = settings.upload_dir / "rooms" / str(room.id)
        folder.mkdir(parents=True, exist_ok=True)
        name = uuid.uuid4()
        (folder / f"{name}.jpg").write_bytes(main)
        (folder / f"{name}_thumb.jpg").write_bytes(thumbnail)
        base = f"/uploads/rooms/{room.id}/{name}"
        session.add(
            RoomPhoto(
                room_id=room.id,
                url=f"{base}.jpg",
                thumbnail_url=f"{base}_thumb.jpg",
                sort_order=order,
            )
        )
        added += 1
    return added


def seed_mockup(session: Session, settings: Settings) -> MockupResult:
    """Insert the missing mockup data. Flushes; the caller commits."""
    data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    result = MockupResult()
    floors = _places(session, data["offices"], result)
    categories, equipment = _catalog(session, result)
    users = _users(session, settings, data["it_staff"], result)

    for r in data["rooms"]:
        floor = floors[(r["office"], r["building"], r["floor"])]
        if _one(session, Room, floor_id=floor.id, name_en=r["name_en"]) is not None:
            continue
        owner = users[r["owner_staff_id"]] if r["owner_staff_id"] else None
        room = Room(
            name_kh=r["name_kh"],
            name_en=r["name_en"],
            short_desc=r["short_desc"],
            description=r["description"],
            floor_id=floor.id,
            category_id=categories[r["category"]].id,
            room_owner_id=owner.id if owner else None,
            capacity=r["capacity"],
            size_sqm=r["size_sqm"],
            start_time=room_hours(r["category"])[0],
            end_time=room_hours(r["category"])[1],
            is_private=r["is_private"],
        )
        session.add(room)
        session.flush()
        for name in _equipment_names(r["features"]):
            session.execute(
                room_equipment.insert().values(room_id=room.id, equipment_id=equipment[name].id)
            )
        result.photos += _add_photos(settings, session, room, r["photos"])
        result.rooms += 1
        print(f"  room {r['name_en']} ({r['office']}, {r['floor']})")
    session.flush()
    return result


def main() -> int:
    settings = get_settings()
    engine = create_db_engine(settings.database_url)
    try:
        with Session(engine) as session:
            try:
                result = seed_mockup(session, settings)
            except MockupError as exc:
                session.rollback()
                print(f"Mockup seed stopped: {exc}", file=sys.stderr)
                return 1
            session.commit()
    finally:
        engine.dispose()
    print(
        f"Mockup data: added {result.offices} offices, {result.buildings} buildings, "
        f"{result.floors} floors, {result.categories} categories, {result.equipment} equipment, "
        f"{result.users} users, {result.rooms} rooms, {result.photos} photos. "
        f"Demo password: {DEMO_PASSWORD}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
