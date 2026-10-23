"""Rooms: tasks 53-57, spec section 13, rules R2, R3, R4, R7, R8, R12, R13."""

from datetime import datetime, time

import pytest
from sqlalchemy import insert

from app.models import RoomPhoto, room_equipment

URL = "/api/v1/rooms"
LIST_FIELDS = {
    "id",
    "name_en",
    "name_kh",
    "short_desc",
    "capacity",
    "size_sqm",
    "start_time",
    "end_time",
    "category",
    "floor",
    "building",
    "location",
    "province",
    "owner",
    "cover_photo",
    "is_active",
    "is_bookable",
}
DETAIL_FIELDS = LIST_FIELDS | {"description", "photos", "equipment", "created_at", "updated_at"}


def _error(response) -> tuple[int, str]:
    return response.status_code, response.json()["error"]["code"]


def _fields(response) -> dict:
    return response.json()["error"]["fields"]


@pytest.fixture
def office(make_location):
    return make_location(name_en="Head Office", name_kh="ការិយាល័យ", province="SIEM_REAP")


@pytest.fixture
def building(make_building, office):
    return make_building(location=office, name_en="Building A", name_kh="អគារ A", short_name="A")


@pytest.fixture
def floor(make_floor, building):
    return make_floor(building=building, floor_label="3rd floor")


@pytest.fixture
def category(make_category):
    return make_category(name_en="Meeting room", name_kh="បន្ទប់ប្រជុំ")


@pytest.fixture
def owner(make_user):
    return make_user(roles=["ROOM_OWNER"], name_en="Sok Dara", name_kh="សុខ ដារ៉ា")


@pytest.fixture
def as_owner(owner, auth_headers):
    return auth_headers(owner)


def new(floor, category, **overrides) -> dict:
    return {
        "name_en": "Mekong Room",
        "name_kh": "បន្ទប់មេគង្គ",
        "floor_id": floor.id,
        "category_id": category.id,
        "capacity": 12,
        "size_sqm": 40,
        "start_time": "08:00",
        "end_time": "18:00",
        "short_desc": "Bright room with a river view",
        "description": "Has a 75-inch screen and a whiteboard.",
        "door_code": "4821#",
        **overrides,
    }


# --- Task 53: POST /rooms --------------------------------------------------------------


def test_create_room(client, as_admin, floor, category, building, office, owner):
    body = new(floor, category, room_owner_id=owner.id)
    response = client.post(URL, json=body, headers=as_admin)
    assert response.status_code == 201
    room = response.json()
    assert set(room) == DETAIL_FIELDS
    assert (room["name_en"], room["capacity"], room["size_sqm"]) == ("Mekong Room", 12, 40)
    assert (room["start_time"], room["end_time"]) == ("08:00", "18:00")
    assert room["category"] == {"id": category.id, "name_en": "Meeting room", "name_kh": "បន្ទប់ប្រជុំ"}
    assert room["floor"] == {"id": floor.id, "floor_label": "3rd floor"}
    assert room["building"] == {
        "id": building.id,
        "name_en": "Building A",
        "name_kh": "អគារ A",
        "short_name": "A",
    }
    assert room["location"] == {"id": office.id, "name_en": "Head Office", "name_kh": "ការិយាល័យ"}
    assert room["province"]["code"] == "SIEM_REAP"
    assert room["owner"] == {"id": owner.id, "name_en": "Sok Dara", "name_kh": "សុខ ដារ៉ា"}
    assert (room["photos"], room["equipment"], room["cover_photo"]) == ([], [], None)
    assert (room["is_active"], room["is_bookable"]) == (True, True)
    assert room["description"] == "Has a 75-inch screen and a whiteboard."


def test_create_never_returns_door_code(client, as_admin, floor, category, db_session):
    from app.models import Room

    response = client.post(URL, json=new(floor, category), headers=as_admin)
    assert "door_code" not in response.text and "4821#" not in response.text
    assert db_session.get(Room, response.json()["id"]).door_code == "4821#"


def test_create_with_only_required_fields(client, as_admin, floor, category):
    body = {
        "name_en": "Small Room",
        "name_kh": "បន្ទប់តូច",
        "floor_id": floor.id,
        "category_id": category.id,
        "capacity": 4,
        "start_time": "07:30",
        "end_time": "17:00",
    }
    room = client.post(URL, json=body, headers=as_admin).json()
    assert (room["owner"], room["size_sqm"], room["short_desc"], room["description"]) == (
        None,
        None,
        None,
        None,
    )


@pytest.mark.parametrize(("value", "expected"), [("8:00", "08:00"), ("08:00:30", "08:00")])
def test_create_accepts_time_forms(client, as_admin, floor, category, value, expected):
    response = client.post(URL, json=new(floor, category, start_time=value), headers=as_admin)
    assert response.json()["start_time"] == expected


@pytest.mark.parametrize("value", ["24:00", "8", "08:60", "abc", "", "08:00:61", 800])
def test_create_invalid_time(client, as_admin, floor, category, value):
    response = client.post(URL, json=new(floor, category, start_time=value), headers=as_admin)
    assert _error(response) == (422, "VALIDATION_ERROR")
    assert set(_fields(response)) == {"start_time"}


@pytest.mark.parametrize(("start", "end"), [("08:00", "08:00"), ("18:00", "08:00")])
def test_create_start_not_before_end(client, as_admin, floor, category, start, end):
    body = new(floor, category, start_time=start, end_time=end)
    response = client.post(URL, json=body, headers=as_admin)
    assert _error(response) == (422, "VALIDATION_ERROR")
    assert _fields(response) == {"end_time": "Opening time must be before closing time."}


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("capacity", 0, "Must be 1 to 10000."),
        ("capacity", 10001, "Must be 1 to 10000."),
        ("size_sqm", 0, "Must be 1 to 100000."),
        ("size_sqm", 100001, "Must be 1 to 100000."),
    ],
)
def test_create_number_ranges(client, as_admin, floor, category, field, value, message):
    response = client.post(URL, json=new(floor, category, **{field: value}), headers=as_admin)
    assert _fields(response) == {field: message}


@pytest.mark.parametrize(
    ("field", "value"), [("capacity", 1), ("capacity", 10000), ("size_sqm", 100000)]
)
def test_create_number_bounds(client, as_admin, floor, category, field, value):
    response = client.post(URL, json=new(floor, category, **{field: value}), headers=as_admin)
    assert response.json()[field] == value


@pytest.mark.parametrize("value", ["abc", 1.5, None])
def test_create_capacity_must_be_whole_number(client, as_admin, floor, category, value):
    response = client.post(URL, json=new(floor, category, capacity=value), headers=as_admin)
    assert set(_fields(response)) == {"capacity"}


@pytest.mark.parametrize(
    ("field", "limit"),
    [
        ("name_en", 100),
        ("name_kh", 100),
        ("short_desc", 200),
        ("description", 1000),
        ("door_code", 50),
    ],
)
def test_create_text_limits(client, as_admin, floor, category, field, limit):
    ok = client.post(URL, json={**new(floor, category), field: "ក" * limit}, headers=as_admin)
    assert ok.status_code == 201, ok.text
    too_long = client.post(
        URL, json={**new(floor, category), field: "x" * (limit + 1)}, headers=as_admin
    )
    assert _fields(too_long) == {field: f"Too long (max {limit})."}


def test_create_blank_optional_text_is_null(client, as_admin, floor, category, db_session):
    from app.models import Room

    body = new(floor, category, short_desc="  ", door_code="   ")
    room = client.post(URL, json=body, headers=as_admin).json()
    assert room["short_desc"] is None
    assert db_session.get(Room, room["id"]).door_code is None


def test_create_on_unknown_floor(client, as_admin, floor, category):
    response = client.post(URL, json=new(floor, category, floor_id=999_999), headers=as_admin)
    assert _error(response) == (422, "VALIDATION_ERROR")
    assert _fields(response) == {"floor_id": "Floor not found."}


def test_create_on_inactive_floor(client, as_admin, make_floor, category):
    response = client.post(URL, json=new(make_floor(is_active=False), category), headers=as_admin)
    assert _error(response) == (409, "INACTIVE_REFERENCE")
    assert _fields(response) == {"floor_id": "This floor is inactive."}


def test_create_with_unknown_category(client, as_admin, floor, category):
    response = client.post(URL, json=new(floor, category, category_id=999_999), headers=as_admin)
    assert _fields(response) == {"category_id": "Room type not found."}


def test_create_with_inactive_category(client, as_admin, floor, make_category):
    response = client.post(URL, json=new(floor, make_category(is_active=False)), headers=as_admin)
    assert _error(response) == (409, "INACTIVE_REFERENCE")
    assert _fields(response) == {"category_id": "This room type is inactive."}


def test_create_under_inactive_building(client, as_admin, floor, category, building, db_session):
    # Only the floor is checked (R2); the room is simply not bookable.
    building.is_active = False
    db_session.flush()
    room = client.post(URL, json=new(floor, category), headers=as_admin).json()
    assert (room["is_active"], room["is_bookable"]) == (True, False)


def test_create_with_unknown_owner(client, as_admin, floor, category):
    response = client.post(URL, json=new(floor, category, room_owner_id=999_999), headers=as_admin)
    assert _error(response) == (422, "VALIDATION_ERROR")
    assert _fields(response) == {"room_owner_id": "User not found."}


@pytest.mark.parametrize(
    "user_fields", [{"roles": ["STAFF"]}, {"roles": ["ROOM_OWNER"], "is_active": False}]
)
def test_create_with_invalid_owner(client, as_admin, floor, category, make_user, user_fields):
    body = new(floor, category, room_owner_id=make_user(**user_fields).id)
    response = client.post(URL, json=body, headers=as_admin)
    assert _error(response) == (409, "OWNER_INVALID")
    assert _fields(response) == {"room_owner_id": "This user cannot own rooms."}


@pytest.mark.parametrize("name", ["Mekong Room", "mekong room", "MEKONG RÓOM"])
def test_create_duplicate_name_on_floor(client, as_admin, floor, category, name):
    client.post(URL, json=new(floor, category), headers=as_admin)
    response = client.post(URL, json=new(floor, category, name_en=name), headers=as_admin)
    assert _error(response) == (409, "DUPLICATE")
    assert _fields(response) == {"name_en": "This name already exists."}


def test_same_name_on_another_floor_is_allowed(client, as_admin, floor, category, make_floor):
    client.post(URL, json=new(floor, category), headers=as_admin)
    response = client.post(URL, json=new(make_floor(), category), headers=as_admin)
    assert response.status_code == 201


def test_create_missing_required_fields(client, as_admin):
    assert set(_fields(client.post(URL, json={}, headers=as_admin))) == {
        "name_en",
        "name_kh",
        "floor_id",
        "category_id",
        "capacity",
        "start_time",
        "end_time",
    }


@pytest.mark.parametrize(
    "field", ["id", "is_active", "is_bookable", "created_at", "cover_photo", "is_private"]
)
def test_create_refuses_unknown_and_server_fields(client, as_admin, floor, category, field):
    response = client.post(URL, json=new(floor, category, **{field: True}), headers=as_admin)
    assert _fields(response) == {field: "Unknown field."}


def test_create_needs_admin(client, as_owner, as_staff, floor, category):
    for headers in (as_owner, as_staff):
        assert _error(client.post(URL, json=new(floor, category), headers=headers)) == (
            403,
            "FORBIDDEN",
        )


def test_create_needs_a_token(client, floor, category):
    assert _error(client.post(URL, json=new(floor, category))) == (401, "UNAUTHORIZED")


# --- Task 54: GET /rooms ---------------------------------------------------------------


@pytest.fixture
def rooms(
    floor,
    category,
    owner,
    building,
    make_room,
    make_floor,
    make_building,
    make_location,
    make_category,
    make_equipment,
    db_session,
):
    other_floor = make_floor(building=building, floor_label="Ground")
    off_building = make_building(location=floor.building.location, is_active=False)
    far_office = make_location(province="KAMPOT")
    training = make_category(name_en="Training", is_active=False)
    result = {
        "mekong": make_room(
            floor=floor,
            category=category,
            owner=owner,
            name_en="Mekong Room",
            name_kh="បន្ទប់មេគង្គ",
            capacity=12,
            short_desc="River view",
        ),
        "tonle": make_room(floor=other_floor, category=training, name_en="Tonle Room", capacity=30),
        "angkor": make_room(floor=floor, category=category, name_en="Angkor Room", capacity=6),
        "closed": make_room(floor=floor, name_en="Closed Room", is_active=False),
        "offbuilding": make_room(
            floor=make_floor(building=off_building), name_en="Off Building Room"
        ),
        "kampot": make_room(
            floor=make_floor(building=make_building(location=far_office)),
            name_en="Kampot 50% Room",
        ),
    }
    projector, screen = make_equipment(name="Projector"), make_equipment(name="Screen")
    for room, items in (
        (result["mekong"], [projector, screen]),
        (result["angkor"], [projector]),
    ):
        for item in items:
            db_session.execute(insert(room_equipment).values(room_id=room.id, equipment_id=item.id))
    result["projector"], result["screen"] = projector, screen
    return result


def _names(response) -> list[str]:
    assert response.status_code == 200, response.text
    return [item["name_en"] for item in response.json()["items"]]


def test_list_shape(client, as_staff, rooms):
    response = client.get(URL, headers=as_staff)
    body = response.json()
    assert set(body) == {"items", "page", "size", "total"}
    assert body["total"] == 6
    assert set(body["items"][0]) == LIST_FIELDS
    assert "door_code" not in response.text


def test_list_sorted_by_name(client, as_staff, rooms):
    assert _names(client.get(URL, headers=as_staff)) == [
        "Angkor Room",
        "Closed Room",
        "Kampot 50% Room",
        "Mekong Room",
        "Off Building Room",
        "Tonle Room",
    ]


def test_list_item(client, as_staff, rooms, owner):
    item = client.get(URL, params={"search": "Mekong"}, headers=as_staff).json()["items"][0]
    assert item["owner"]["id"] == owner.id
    assert (item["start_time"], item["end_time"]) == ("08:00", "18:00")
    assert item["cover_photo"] is None
    assert item["is_bookable"] is True


def test_list_cover_photo(client, as_staff, rooms, db_session):
    room = rooms["mekong"]
    for order, name in ((2, "second"), (1, "first"), (3, "third")):
        db_session.add(
            RoomPhoto(
                room_id=room.id,
                url=f"/u/{name}.jpg",
                thumbnail_url=f"/u/{name}_t.jpg",
                sort_order=order,
            )
        )
    db_session.flush()
    item = client.get(URL, params={"search": "Mekong"}, headers=as_staff).json()["items"][0]
    assert item["cover_photo"] == {"url": "/u/first.jpg", "thumbnail_url": "/u/first_t.jpg"}


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("province=KAMPOT", ["Kampot 50% Room"]),
        ("min_capacity=12", ["Mekong Room", "Tonle Room"]),
        ("has_owner=true", ["Mekong Room"]),
        ("is_active=false", ["Closed Room"]),
        ("search=river", ["Mekong Room"]),
        ("search=មេគង្គ", ["Mekong Room"]),
        ("search=50%", ["Kampot 50% Room"]),
        ("search=%20%20", None),
    ],
)
def test_list_filters(client, as_staff, rooms, query, expected):
    names = _names(client.get(f"{URL}?{query}", headers=as_staff))
    assert names == (
        expected if expected is not None else _names(client.get(URL, headers=as_staff))
    )


def test_list_filter_ids(client, as_staff, rooms, floor, building, category, owner):
    assert _names(client.get(f"{URL}?floor_id={floor.id}", headers=as_staff)) == [
        "Angkor Room",
        "Closed Room",
        "Mekong Room",
    ]
    assert "Tonle Room" in _names(client.get(f"{URL}?building_id={building.id}", headers=as_staff))
    location_id = building.location_id
    assert "Kampot 50% Room" not in _names(
        client.get(f"{URL}?location_id={location_id}", headers=as_staff)
    )
    assert _names(client.get(f"{URL}?category_id={category.id}", headers=as_staff)) == [
        "Angkor Room",
        "Mekong Room",
    ]
    assert _names(client.get(f"{URL}?owner_id={owner.id}", headers=as_staff)) == ["Mekong Room"]


def test_list_has_no_owner(client, as_staff, rooms):
    assert "Mekong Room" not in _names(client.get(f"{URL}?has_owner=false", headers=as_staff))


def test_list_equipment_ids_needs_all(client, as_staff, rooms):
    both = f"{rooms['projector'].id},{rooms['screen'].id}"
    assert _names(client.get(f"{URL}?equipment_ids={both}", headers=as_staff)) == ["Mekong Room"]
    one = rooms["projector"].id
    assert _names(client.get(f"{URL}?equipment_ids={one}", headers=as_staff)) == [
        "Angkor Room",
        "Mekong Room",
    ]
    repeated = f"{one},{one}"
    assert len(_names(client.get(f"{URL}?equipment_ids={repeated}", headers=as_staff))) == 2


def test_list_bookable(client, as_staff, rooms):
    # Inactive room or building is excluded; an inactive category does not matter (R12).
    bookable = _names(client.get(f"{URL}?is_bookable=true", headers=as_staff))
    assert bookable == ["Angkor Room", "Kampot 50% Room", "Mekong Room", "Tonle Room"]
    unbookable = _names(client.get(f"{URL}?is_bookable=false", headers=as_staff))
    assert unbookable == ["Closed Room", "Off Building Room"]


def test_list_bookable_flag(client, as_staff, rooms):
    items = client.get(URL, headers=as_staff).json()["items"]
    flags = {item["name_en"]: item["is_bookable"] for item in items}
    assert flags["Off Building Room"] is False and flags["Tonle Room"] is True


def test_deactivated_location_makes_rooms_unbookable(client, as_staff, rooms, building, db_session):
    building.location.is_active = False
    db_session.flush()
    assert "Mekong Room" not in _names(client.get(f"{URL}?is_bookable=true", headers=as_staff))


def test_list_paging(client, as_staff, rooms):
    body = client.get(f"{URL}?size=4&page=2", headers=as_staff).json()
    assert (body["page"], body["size"], body["total"]) == (2, 4, 6)
    assert [item["name_en"] for item in body["items"]] == ["Off Building Room", "Tonle Room"]
    past = client.get(f"{URL}?page=9", headers=as_staff).json()
    assert (past["items"], past["total"]) == ([], 6)


@pytest.mark.parametrize(
    ("query", "field"),
    [
        ("equipment_ids=1,x", "equipment_ids"),
        ("equipment_ids=0", "equipment_ids"),
        ("province=MARS", "province"),
        ("min_capacity=0", "min_capacity"),
        ("min_capacity=abc", "min_capacity"),
        ("has_owner=maybe", "has_owner"),
        ("is_bookable=maybe", "is_bookable"),
        ("floor_id=abc", "floor_id"),
        ("owner_id=0", "owner_id"),
        ("size=0", "size"),
    ],
)
def test_list_bad_query(client, as_staff, query, field):
    response = client.get(f"{URL}?{query}", headers=as_staff)
    assert _error(response) == (422, "VALIDATION_ERROR")
    assert set(_fields(response)) == {field}


def test_list_needs_a_token(client):
    assert _error(client.get(URL)) == (401, "UNAUTHORIZED")


# --- Task 55: GET /rooms/{id} ----------------------------------------------------------


def test_get_room(client, as_staff, rooms, db_session):
    room = rooms["mekong"]
    for order in (2, 1):
        db_session.add(
            RoomPhoto(
                room_id=room.id,
                url=f"/u/{order}.jpg",
                thumbnail_url=f"/u/{order}_t.jpg",
                sort_order=order,
            )
        )
    db_session.flush()
    response = client.get(f"{URL}/{room.id}", headers=as_staff)
    assert response.status_code == 200
    body = response.json()
    assert set(body) == DETAIL_FIELDS
    assert [photo["sort_order"] for photo in body["photos"]] == [1, 2]
    assert set(body["photos"][0]) == {
        "id",
        "room_id",
        "url",
        "thumbnail_url",
        "sort_order",
        "created_at",
        "updated_at",
    }
    assert body["cover_photo"]["url"] == "/u/1.jpg"
    assert [item["name"] for item in body["equipment"]] == ["Projector", "Screen"]
    assert "door_code" not in response.text


def test_get_room_without_photos(client, as_staff, rooms):
    body = client.get(f"{URL}/{rooms['angkor'].id}", headers=as_staff).json()
    assert (body["cover_photo"], body["photos"]) == (None, [])


def test_get_unknown_room(client, as_staff):
    assert _error(client.get(f"{URL}/999999", headers=as_staff)) == (404, "NOT_FOUND")


@pytest.mark.parametrize("bad_id", ["abc", "0", "-1"])
def test_get_bad_id(client, as_staff, bad_id):
    assert _error(client.get(f"{URL}/{bad_id}", headers=as_staff)) == (422, "VALIDATION_ERROR")


def test_get_needs_a_token(client, rooms):
    assert _error(client.get(f"{URL}/{rooms['mekong'].id}")) == (401, "UNAUTHORIZED")


# --- Task 56: PATCH /rooms/{id} --------------------------------------------------------


@pytest.fixture
def room(make_room, floor, category, owner, db_session):
    room = make_room(
        floor=floor,
        category=category,
        owner=owner,
        name_en="Mekong Room",
        capacity=12,
        door_code="1111",
        short_desc="River view",
    )
    room.updated_at = datetime(2026, 1, 1)
    db_session.flush()
    return room


def patch(client, headers, room, body):
    return client.patch(f"{URL}/{room.id}", json=body, headers=headers)


def test_admin_patch(client, as_admin, room, make_floor, make_category, make_user):
    target_floor, target_category = make_floor(), make_category()
    new_owner = make_user(roles=["ROOM_OWNER"])
    body = {
        "name_en": "Bassac Room",
        "floor_id": target_floor.id,
        "category_id": target_category.id,
        "room_owner_id": new_owner.id,
        "capacity": 20,
        "start_time": "07:00",
        "end_time": "19:30",
    }
    response = patch(client, as_admin, room, body)
    assert response.status_code == 200, response.text
    result = response.json()
    assert set(result) == DETAIL_FIELDS
    assert (result["name_en"], result["capacity"]) == ("Bassac Room", 20)
    assert (result["floor"]["id"], result["category"]["id"]) == (
        target_floor.id,
        target_category.id,
    )
    assert result["owner"]["id"] == new_owner.id
    assert (result["start_time"], result["end_time"]) == ("07:00", "19:30")
    assert result["updated_at"] != "2026-01-01T00:00:00Z"


def test_patch_empty_body(client, as_admin, room):
    response = patch(client, as_admin, room, {})
    assert response.status_code == 200
    assert response.json()["updated_at"] == "2026-01-01T00:00:00Z"


def test_patch_same_values(client, as_admin, room):
    body = {"name_en": "Mekong Room", "capacity": 12, "start_time": "08:00:00", "door_code": "1111"}
    assert patch(client, as_admin, room, body).json()["updated_at"] == "2026-01-01T00:00:00Z"


@pytest.mark.parametrize(
    "field",
    [
        "name_en",
        "name_kh",
        "floor_id",
        "category_id",
        "capacity",
        "start_time",
        "end_time",
        "is_active",
    ],
)
def test_patch_null_for_required(client, as_admin, room, field):
    assert _fields(patch(client, as_admin, room, {field: None})) == {
        field: "This field is required."
    }


def test_patch_null_clears_optional(client, as_admin, room, db_session):
    body = {"size_sqm": None, "short_desc": None, "description": None, "door_code": None}
    result = patch(client, as_admin, room, body).json()
    assert (result["size_sqm"], result["short_desc"], result["description"]) == (None, None, None)
    db_session.refresh(room)
    assert room.door_code is None


def test_patch_remove_owner(client, as_admin, room):
    assert patch(client, as_admin, room, {"room_owner_id": None}).json()["owner"] is None


def test_patch_only_end_before_stored_start(client, as_admin, room):
    response = patch(client, as_admin, room, {"end_time": "07:00"})
    assert _error(response) == (422, "VALIDATION_ERROR")
    assert _fields(response) == {"end_time": "Opening time must be before closing time."}


def test_patch_only_start_after_stored_end(client, as_admin, room):
    response = patch(client, as_admin, room, {"start_time": "18:00"})
    assert _fields(response) == {"end_time": "Opening time must be before closing time."}


def test_patch_both_times_moving_past_stored(client, as_admin, room):
    body = patch(client, as_admin, room, {"start_time": "19:00", "end_time": "21:00"}).json()
    assert (body["start_time"], body["end_time"]) == ("19:00", "21:00")


def test_move_to_inactive_floor(client, as_admin, room, make_floor):
    response = patch(client, as_admin, room, {"floor_id": make_floor(is_active=False).id})
    assert _error(response) == (409, "INACTIVE_REFERENCE")
    assert _fields(response) == {"floor_id": "This floor is inactive."}


def test_move_to_floor_with_same_room_name(client, as_admin, room, make_floor, make_room):
    target = make_floor()
    make_room(floor=target, name_en="mekong room")
    response = patch(client, as_admin, room, {"floor_id": target.id})
    assert _error(response) == (409, "DUPLICATE")
    assert _fields(response) == {"name_en": "This name already exists."}


def test_change_to_inactive_category(client, as_admin, room, make_category):
    response = patch(client, as_admin, room, {"category_id": make_category(is_active=False).id})
    assert _error(response) == (409, "INACTIVE_REFERENCE")


def test_keep_inactive_category_and_floor(client, as_admin, room, category, floor, db_session):
    category.is_active = False
    floor.is_active = False
    db_session.flush()
    body = {"name_en": "Renamed", "category_id": category.id, "floor_id": floor.id}
    assert patch(client, as_admin, room, body).status_code == 200


def test_deactivate_and_reactivate(client, as_admin, room):
    off = patch(client, as_admin, room, {"is_active": False}).json()
    assert (off["is_active"], off["is_bookable"]) == (False, False)
    assert patch(client, as_admin, room, {"is_active": True}).json()["is_active"] is True


def test_reactivate_on_inactive_floor(client, as_admin, room, floor, db_session):
    room.is_active = False
    floor.is_active = False
    db_session.flush()
    response = patch(client, as_admin, room, {"is_active": True})
    assert _error(response) == (409, "INACTIVE_REFERENCE")
    assert _fields(response) == {"is_active": "The floor is inactive."}


def test_patch_invalid_owner(client, as_admin, room, make_user):
    response = patch(client, as_admin, room, {"room_owner_id": make_user(roles=["STAFF"]).id})
    assert _error(response) == (409, "OWNER_INVALID")


@pytest.mark.parametrize(
    ("body", "field"),
    [
        ({"capacity": 0}, "capacity"),
        ({"size_sqm": 100001}, "size_sqm"),
        ({"start_time": "24:00"}, "start_time"),
        ({"name_en": " "}, "name_en"),
        ({"door_code": "x" * 51}, "door_code"),
        ({"is_bookable": True}, "is_bookable"),
    ],
)
def test_patch_invalid_values(client, as_admin, room, body, field):
    assert set(_fields(patch(client, as_admin, room, body))) == {field}


def test_owner_edits_own_room(client, as_owner, room, make_category, db_session):
    body = {
        "name_en": "My Room",
        "name_kh": "បន្ទប់ខ្ញុំ",
        "short_desc": "Quiet",
        "description": "Nice",
        "capacity": 8,
        "size_sqm": 30,
        "start_time": "09:00",
        "end_time": "17:00",
        "door_code": "9999",
        "category_id": make_category().id,
    }
    response = patch(client, as_owner, room, body)
    assert response.status_code == 200, response.text
    assert response.json()["name_en"] == "My Room"
    db_session.refresh(room)
    assert room.door_code == "9999"


@pytest.mark.parametrize(
    "body",
    [
        {"room_owner_id": None},
        {"floor_id": 1},
        {"is_active": False},
        {"name_en": "Sneaky", "is_active": True},
    ],
)
def test_owner_cannot_send_admin_fields(client, as_owner, room, db_session, body):
    response = patch(client, as_owner, room, body)
    assert _error(response) == (403, "FORBIDDEN")
    db_session.refresh(room)
    assert (room.name_en, room.room_owner_id, room.is_active) == (
        "Mekong Room",
        room.owner.id,
        True,
    )


def test_owner_cannot_edit_others_room(client, as_owner, make_room, make_user):
    others = make_room(owner=make_user(roles=["ROOM_OWNER"]))
    assert _error(patch(client, as_owner, others, {"capacity": 2})) == (403, "FORBIDDEN")


def test_owner_cannot_edit_no_owner_room(client, as_owner, make_room):
    assert _error(patch(client, as_owner, make_room(), {"capacity": 2})) == (403, "FORBIDDEN")


def test_owner_who_lost_role(client, room, owner, auth_headers, db_session):
    from tests.factories import set_roles

    set_roles(db_session, owner, ["STAFF"])
    response = patch(client, auth_headers(owner), room, {"capacity": 2})
    assert _error(response) == (403, "FORBIDDEN")


def test_staff_cannot_patch(client, as_staff, room):
    assert _error(patch(client, as_staff, room, {"capacity": 2})) == (403, "FORBIDDEN")


def test_patch_unknown_room(client, as_admin, as_owner):
    for headers in (as_admin, as_owner):
        response = client.patch(f"{URL}/999999", json={}, headers=headers)
        assert _error(response) == (404, "NOT_FOUND")


def test_patch_needs_a_token(client, room):
    assert _error(client.patch(f"{URL}/{room.id}", json={})) == (401, "UNAUTHORIZED")


def test_no_delete(client, as_admin, room):
    assert _error(client.delete(f"{URL}/{room.id}", headers=as_admin)) == (
        405,
        "METHOD_NOT_ALLOWED",
    )


# --- Task 57: GET /rooms/{id}/door-code ------------------------------------------------


def test_admin_reads_door_code(client, as_admin, room):
    response = client.get(f"{URL}/{room.id}/door-code", headers=as_admin)
    assert response.status_code == 200
    assert response.json() == {"room_id": room.id, "door_code": "1111"}


def test_owner_reads_own_door_code(client, as_owner, room):
    assert client.get(f"{URL}/{room.id}/door-code", headers=as_owner).json()["door_code"] == "1111"


def test_door_code_not_set(client, as_admin, make_room):
    room = make_room()
    assert client.get(f"{URL}/{room.id}/door-code", headers=as_admin).json() == {
        "room_id": room.id,
        "door_code": None,
    }


def test_owner_cannot_read_others_door_code(client, as_owner, make_room):
    response = client.get(f"{URL}/{make_room(door_code='5').id}/door-code", headers=as_owner)
    assert _error(response) == (403, "FORBIDDEN")


def test_staff_cannot_read_door_code(client, as_staff, room):
    assert _error(client.get(f"{URL}/{room.id}/door-code", headers=as_staff)) == (403, "FORBIDDEN")


def test_door_code_unknown_room(client, as_admin):
    assert _error(client.get(f"{URL}/999999/door-code", headers=as_admin)) == (404, "NOT_FOUND")


def test_door_code_needs_a_token(client, room):
    assert _error(client.get(f"{URL}/{room.id}/door-code")) == (401, "UNAUTHORIZED")


def test_times_stored_without_seconds(client, as_admin, floor, category, db_session):
    from app.models import Room

    body = new(floor, category, start_time="08:15:45", end_time="17:00:59")
    room_id = client.post(URL, json=body, headers=as_admin).json()["id"]
    room = db_session.get(Room, room_id)
    assert (room.start_time, room.end_time) == (time(8, 15), time(17, 0))
