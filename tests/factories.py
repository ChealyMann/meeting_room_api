"""Test data in one line each. Every value can be overridden by keyword.

Parents are created when not given: `make_room()` builds a whole active
location -> building -> floor chain plus a category.
"""

from datetime import date, datetime, time
from itertools import count

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.constants.booking import FINAL, BookingRoute, BookingStatus, ITStatus, MeetingType
from app.constants.roles import RoleCode
from app.models import (
    Booking,
    BookingDoorPass,
    BookingSession,
    Building,
    Category,
    CateringOrder,
    CateringPackage,
    Department,
    Division,
    Equipment,
    Floor,
    ITService,
    ITTicket,
    Location,
    Position,
    PublicHoliday,
    Role,
    Room,
    User,
    user_roles,
)
from app.security import hash_password
from app.services import booking_codes, booking_scheduling, clock

DEFAULT_PASSWORD = "Password@123"

_sequence = count(1)
# Hashing is slow on purpose; hash the default password once per test run.
_default_hash: str | None = None


def _next() -> int:
    return next(_sequence)


def _save(session: Session, record):
    session.add(record)
    session.flush()
    return record


def _password_hash(password: str) -> str:
    global _default_hash
    if password != DEFAULT_PASSWORD:
        return hash_password(password)
    if _default_hash is None:
        _default_hash = hash_password(DEFAULT_PASSWORD)
    return _default_hash


# --- Places and rooms ------------------------------------------------------------------


def make_location(session: Session, **fields) -> Location:
    n = _next()
    values = {"name_en": f"Office {n}", "name_kh": f"ការិយាល័យ {n}", "province": "PHNOM_PENH"}
    return _save(session, Location(**{**values, **fields}))


def make_building(session: Session, location: Location | None = None, **fields) -> Building:
    n = _next()
    location = location or make_location(session)
    values = {"name_en": f"Building {n}", "name_kh": f"អគារ {n}", "location_id": location.id}
    return _save(session, Building(**{**values, **fields}))


def make_floor(session: Session, building: Building | None = None, **fields) -> Floor:
    n = _next()
    building = building or make_building(session)
    values = {"floor_label": f"Floor {n}", "building_id": building.id}
    return _save(session, Floor(**{**values, **fields}))


def make_category(session: Session, **fields) -> Category:
    n = _next()
    values = {"name_en": f"Category {n}", "name_kh": f"ប្រភេទ {n}"}
    return _save(session, Category(**{**values, **fields}))


def make_room(
    session: Session,
    floor: Floor | None = None,
    category: Category | None = None,
    owner: User | None = None,
    **fields,
) -> Room:
    n = _next()
    floor = floor or make_floor(session)
    category = category or make_category(session)
    values = {
        "name_en": f"Room {n}",
        "name_kh": f"បន្ទប់ {n}",
        "floor_id": floor.id,
        "category_id": category.id,
        "room_owner_id": owner.id if owner else None,
        "capacity": 10,
        "start_time": time(8, 0),
        "end_time": time(18, 0),
    }
    return _save(session, Room(**{**values, **fields}))


def make_equipment(session: Session, **fields) -> Equipment:
    return _save(session, Equipment(**{"name": f"Equipment {_next()}", **fields}))


# --- Booking catalogs ------------------------------------------------------------------


def make_catering_package(session: Session, **fields) -> CateringPackage:
    return _save(session, CateringPackage(**{"name": f"Package {_next()}", **fields}))


def make_it_service(session: Session, **fields) -> ITService:
    return _save(session, ITService(**{"name": f"IT service {_next()}", **fields}))


def make_holiday(session: Session, holiday_date: date, **fields) -> PublicHoliday:
    values = {"holiday_date": holiday_date, "name_km": f"Holiday {_next()}"}
    return _save(session, PublicHoliday(**{**values, **fields}))


# --- Organisation ----------------------------------------------------------------------


def make_department(session: Session, location: Location | None = None, **fields) -> Department:
    n = _next()
    location = location or make_location(session)
    values = {"name_en": f"Department {n}", "name_kh": f"នាយកដ្ឋាន {n}", "location_id": location.id}
    return _save(session, Department(**{**values, **fields}))


def make_division(session: Session, department: Department | None = None, **fields) -> Division:
    n = _next()
    department = department or make_department(session)
    values = {"name_en": f"Division {n}", "name_kh": f"ផ្នែក {n}", "department_id": department.id}
    return _save(session, Division(**{**values, **fields}))


def make_position(session: Session, **fields) -> Position:
    n = _next()
    values = {"name_en": f"Position {n}", "name_kh": f"មុខតំណែង {n}"}
    return _save(session, Position(**{**values, **fields}))


# --- Users and roles -------------------------------------------------------------------


def ensure_roles(session: Session) -> dict[str, int]:
    """The six roles, created if missing. Returns code -> id."""
    existing = dict(session.execute(select(Role.code, Role.id)).all())
    for code in RoleCode:
        if code not in existing:
            existing[code] = _save(
                session, Role(code=code, name_en=code.title(), name_kh=code.title())
            ).id
    return existing


def make_user(
    session: Session,
    roles=(),
    password: str = DEFAULT_PASSWORD,
    division: Division | None = None,
    position: Position | None = None,
    **fields,
) -> User:
    """An active user who does not need to change their password, unless told otherwise."""
    n = _next()
    position = position or make_position(session)
    values = {
        "staff_id": f"EMP-{n:05d}",
        "name_en": f"User {n}",
        "name_kh": f"អ្នកប្រើ {n}",
        "email": f"user{n}@company.com",
        "password_hash": _password_hash(password),
        "must_change_password": False,
        "position_id": position.id,
        "division_id": division.id if division else None,
    }
    user = _save(session, User(**{**values, **fields}))
    set_roles(session, user, roles)
    return user


def set_roles(session: Session, user: User, roles) -> None:
    """Replace the user's roles with `roles` (role codes)."""
    role_ids = ensure_roles(session)
    session.execute(user_roles.delete().where(user_roles.c.user_id == user.id))
    for code in dict.fromkeys(roles):
        session.execute(user_roles.insert().values(user_id=user.id, role_id=role_ids[code]))
    session.flush()


def make_pitika(session: Session, province: str = "PHNOM_PENH", **fields) -> User:
    """An active Pitika working in an office of `province`."""
    division = make_division(
        session, make_department(session, make_location(session, province=province))
    )
    return make_user(session, roles=[RoleCode.PITIKA], division=division, **fields)


# --- Bookings --------------------------------------------------------------------------


def make_bookable_room(
    session: Session,
    province: str = "PHNOM_PENH",
    private: bool = False,
    owner: User | None = None,
    **fields,
) -> Room:
    """A room that can be booked (active chain in `province`), open 08:00-18:00 with 10 seats.
    A private room with no `owner` gets a new ROOM_OWNER user."""
    floor = make_floor(session, make_building(session, make_location(session, province=province)))
    if private and owner is None:
        owner = make_user(session, roles=[RoleCode.ROOM_OWNER])
    return make_room(session, floor, owner=owner, is_private=private, **fields)


def _requester_info(user: User) -> dict:
    return {
        "name_en": user.name_en,
        "name_kh": user.name_kh,
        "staff_id": user.staff_id,
        "position": None,
        "division": None,
        "department": None,
        "office": None,
        "email": user.email,
        "phone": None,
    }


def make_booking(
    session: Session,
    room: Room,
    requester: User,
    *,
    status: BookingStatus,
    route: BookingRoute | None = None,
    sessions=((date(2026, 11, 10), time(9), time(10)),),
    catering: bool = False,
    it: bool = False,
    forwarded: bool = False,
    assigned_staff=(),
    food_approved_by: User | None = None,
    version: int = 1,
    **fields,
) -> Booking:
    """A booking in any status, saved directly (no rules run).

    `sessions` are (date, start, end) tuples; they block the room unless the status is
    REJECTED or CANCELLED. A CONFIRMED booking gets a door pass that ends with its last session.
    """
    n = _next()
    route = route or booking_scheduling.pick_route(room, requester.id, catering, it)
    values = {
        "reference_code": booking_codes.new_reference_code(session, clock.now_local()),
        "requester_id": requester.id,
        "room_id": room.id,
        "requester_info": _requester_info(requester),
        "meeting_title": f"Meeting {n}",
        "meeting_type": MeetingType.INTERNAL,
        "attendees": 5,
        "route": route,
        "status": status,
        "version": version,
    }
    booking = _save(session, Booking(**{**values, **fields}))

    blocking = status not in FINAL
    for day, start, end in sessions:
        session.add(
            BookingSession(
                booking_id=booking.id,
                room_id=room.id,
                date=day,
                start_time=start,
                end_time=end,
                is_blocking=blocking,
            )
        )
    if catering:
        order = CateringOrder(booking_id=booking.id, packages=[])
        if food_approved_by is not None:
            order.decided_by = food_approved_by.id
            order.decided_at = clock.now_utc()
        session.add(order)
    if it:
        ticket = ITTicket(
            booking_id=booking.id,
            requested_items=[],
            status=ITStatus.ASSIGNED if assigned_staff else ITStatus.RECEIVED,
            forwarded_at=clock.now_utc() if forwarded else None,
        )
        _save(session, ticket)
        ticket.staff.extend(assigned_staff)
    if status == BookingStatus.CONFIRMED:
        last_end = max(datetime.combine(day, end) for day, _start, end in sessions)
        session.add(
            BookingDoorPass(
                booking_id=booking.id,
                passcode=booking_codes.new_door_pass_code(session, booking.reference_code),
                expires_at=clock.local_to_utc(last_end),
            )
        )
    session.flush()
    session.refresh(booking)
    return booking
