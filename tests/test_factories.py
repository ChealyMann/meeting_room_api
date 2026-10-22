"""The test factories build valid records in one line each (spec section 18)."""

from sqlalchemy import select

from app.models import Role, user_roles


def test_make_room_builds_the_whole_chain(make_room):
    room = make_room()
    assert room.id
    assert room.floor.building.location.is_active
    assert room.category.is_active
    assert room.room_owner_id is None
    assert room.capacity >= 1
    assert room.start_time < room.end_time


def test_make_room_on_given_floor_with_owner(make_floor, make_room, make_user):
    floor = make_floor()
    owner = make_user(roles=["ROOM_OWNER"])
    room = make_room(floor=floor, owner=owner, name_en="Mekong Room", capacity=12)
    assert room.floor_id == floor.id
    assert room.room_owner_id == owner.id
    assert (room.name_en, room.capacity) == ("Mekong Room", 12)


def test_factories_make_unique_names(make_location, make_room):
    assert make_location().name_en != make_location().name_en
    first, second = make_room(), make_room()
    assert first.floor.building.location_id != second.floor.building.location_id


def test_make_building_and_floor_link_up(make_location, make_building, make_floor):
    location = make_location(province="SIEM_REAP")
    building = make_building(location=location)
    floor = make_floor(building=building)
    assert floor.building.location.province == "SIEM_REAP"


def test_make_department_and_division(make_division, make_department, make_location):
    location = make_location()
    department = make_department(location=location)
    division = make_division(department=department)
    assert division.department.location_id == location.id
    assert make_division().department.location.id


def test_make_user_with_division_and_roles(make_user, make_division, db_session):
    division = make_division()
    user = make_user(roles=["PITIKA", "STAFF"], division=division)
    assert user.division_id == division.id
    codes = db_session.scalars(
        select(Role.code).join(user_roles).where(user_roles.c.user_id == user.id)
    ).all()
    assert sorted(codes) == ["PITIKA", "STAFF"]


def test_make_equipment_and_category(make_equipment, make_category):
    assert make_equipment().is_active
    assert make_category(is_active=False).is_active is False
