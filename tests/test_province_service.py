"""get_user_province() and get_room_province() (spec section 5, "How a province is found")."""

from app.services.province import get_room_province, get_user_province


def test_user_province_comes_from_division_department_location(
    make_user, make_division, make_department, make_location
):
    location = make_location(province="SIEM_REAP")
    division = make_division(department=make_department(location=location))
    province = get_user_province(make_user(division=division))
    assert (province.code, province.name_en, province.name_kh) == (
        "SIEM_REAP",
        "Siem Reap",
        "សៀមរាប",
    )


def test_user_without_division_has_no_province(make_user):
    assert get_user_province(make_user()) is None


def test_user_province_follows_a_moved_department(
    make_user, make_division, make_department, make_location, db_session
):
    department = make_department(location=make_location(province="KANDAL"))
    user = make_user(division=make_division(department=department))
    department.location_id = make_location(province="KAMPOT").id
    db_session.flush()
    db_session.expire_all()
    assert get_user_province(user).code == "KAMPOT"


def test_room_province_comes_from_floor_building_location(
    make_room, make_floor, make_building, make_location
):
    location = make_location(province="BATTAMBANG")
    room = make_room(floor=make_floor(building=make_building(location=location)))
    assert get_room_province(room).code == "BATTAMBANG"


def test_room_province_follows_a_moved_building(
    make_room, make_floor, make_building, make_location, db_session
):
    building = make_building(location=make_location(province="KEP"))
    room = make_room(floor=make_floor(building=building))
    building.location_id = make_location(province="PAILIN").id
    db_session.flush()
    db_session.expire_all()
    assert get_room_province(room).code == "PAILIN"
