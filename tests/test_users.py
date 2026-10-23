"""Users: tasks 47-52, spec section 14, rules R2, R5, R6, R9, R10, R11, R18."""

from datetime import datetime

import pytest

from app.errors import AppError

URL = "/api/v1/users"
LOGIN = "/api/v1/auth/login"
DETAIL_FIELDS = {
    "id",
    "staff_id",
    "title",
    "name_en",
    "name_kh",
    "email",
    "secondary_email",
    "phone",
    "avatar_url",
    "signature_url",
    "email_notifications",
    "division",
    "department",
    "position",
    "province",
    "roles",
    "owned_room_ids",
    "is_active",
    "must_change_password",
    "last_login_at",
    "created_at",
    "updated_at",
}
CHANGED_FIELDS = DETAIL_FIELDS | {"rooms_unassigned"}
LIST_FIELDS = {
    "id",
    "staff_id",
    "title",
    "name_en",
    "name_kh",
    "email",
    "division",
    "position",
    "province",
    "role_codes",
    "is_active",
    "last_login_at",
}


def _error(response) -> tuple[int, str]:
    return response.status_code, response.json()["error"]["code"]


def _fields(response) -> dict:
    return response.json()["error"]["fields"]


@pytest.fixture
def admin(make_user):
    return make_user(roles=["ADMIN"], name_en="Acting Admin")


@pytest.fixture
def headers(admin, auth_headers):
    return auth_headers(admin)


@pytest.fixture
def position(make_position):
    return make_position(name_en="Officer", name_kh="មន្ត្រី")


@pytest.fixture
def division(make_location, make_department, make_division):
    office = make_location(name_en="Siem Reap Branch", province="SIEM_REAP")
    department = make_department(location=office, name_en="Operations", name_kh="ប្រតិបត្តិការ")
    return make_division(department=department, name_en="IT Division", name_kh="ផ្នែក IT")


def new(position, **overrides) -> dict:
    return {
        "staff_id": "EMP-00150",
        "title": "Ms.",
        "name_en": "Chan Sreymom",
        "name_kh": "ចាន់ ស្រីមុំ",
        "email": "Chan.Sreymom@Company.com",
        "secondary_email": None,
        "phone": "098 765 432",
        "avatar_url": None,
        "position_id": position.id,
        "email_notifications": True,
        "temporary_password": "Welcome@2026",
        **overrides,
    }


# --- Task 47: POST /users --------------------------------------------------------------


def test_create_user(client, headers, position, division):
    response = client.post(URL, json=new(position, division_id=division.id), headers=headers)
    assert response.status_code == 201
    body = response.json()
    assert set(body) == DETAIL_FIELDS
    assert body["email"] == "chan.sreymom@company.com"
    assert (body["staff_id"], body["title"], body["name_en"], body["phone"]) == (
        "EMP-00150",
        "Ms.",
        "Chan Sreymom",
        "098 765 432",
    )
    assert body["position"] == {"id": position.id, "name_en": "Officer", "name_kh": "មន្ត្រី"}
    assert body["division"]["id"] == division.id
    assert body["department"]["name_en"] == "Operations"
    assert body["province"]["code"] == "SIEM_REAP"
    assert (body["roles"], body["owned_room_ids"]) == ([], [])
    assert (body["is_active"], body["must_change_password"], body["last_login_at"]) == (
        True,
        True,
        None,
    )


def test_create_never_returns_password(client, headers, position):
    response = client.post(URL, json=new(position), headers=headers)
    assert "password_hash" not in response.text
    assert "Welcome@2026" not in response.text


def test_create_with_only_required_fields(client, headers, position):
    body = {
        "staff_id": "EMP-1",
        "name_en": "Sok",
        "name_kh": "សុខ",
        "email": "sok@company.com",
        "position_id": position.id,
        "temporary_password": "Welcome@2026",
    }
    response = client.post(URL, json=body, headers=headers).json()
    assert (response["title"], response["division"], response["department"]) == (None, None, None)
    assert (response["province"], response["secondary_email"], response["phone"]) == (
        None,
        None,
        None,
    )
    assert response["email_notifications"] is True


def test_new_user_signs_in_with_temporary_password(client, headers, position):
    client.post(URL, json=new(position), headers=headers)
    login = {"email": "chan.sreymom@company.com", "password": "Welcome@2026"}
    response = client.post(LOGIN, json=login)
    assert response.status_code == 200
    assert response.json()["must_change_password"] is True


def test_temporary_password_is_not_trimmed(client, headers, position):
    client.post(URL, json=new(position, temporary_password=" Welcome@2026 "), headers=headers)
    email = "chan.sreymom@company.com"
    assert client.post(LOGIN, json={"email": email, "password": "Welcome@2026"}).status_code == 401
    assert (
        client.post(LOGIN, json={"email": email, "password": " Welcome@2026 "}).status_code == 200
    )


@pytest.mark.parametrize("email", ["chan.sreymom@company.com", "CHAN.SREYMOM@COMPANY.COM"])
def test_create_duplicate_email(client, headers, position, email):
    client.post(URL, json=new(position), headers=headers)
    response = client.post(URL, json=new(position, staff_id="EMP-2", email=email), headers=headers)
    assert _error(response) == (409, "DUPLICATE")
    assert _fields(response) == {"email": "This email already exists."}


@pytest.mark.parametrize("staff_id", ["EMP-00150", "emp-00150"])
def test_create_duplicate_staff_id(client, headers, position, staff_id):
    client.post(URL, json=new(position), headers=headers)
    body = new(position, staff_id=staff_id, email="other@company.com")
    response = client.post(URL, json=body, headers=headers)
    assert _error(response) == (409, "DUPLICATE")
    assert _fields(response) == {"staff_id": "This staff ID already exists."}


@pytest.mark.parametrize("secondary", ["chan.sreymom@company.com", " CHAN.Sreymom@company.COM "])
def test_secondary_email_must_differ(client, headers, position, secondary):
    response = client.post(URL, json=new(position, secondary_email=secondary), headers=headers)
    assert _error(response) == (422, "VALIDATION_ERROR")
    assert _fields(response) == {"secondary_email": "Second email must be different."}


def test_create_with_unknown_position(client, headers, position):
    response = client.post(URL, json=new(position, position_id=999_999), headers=headers)
    assert _error(response) == (422, "VALIDATION_ERROR")
    assert _fields(response) == {"position_id": "Job position not found."}


def test_create_with_inactive_position(client, headers, make_position):
    response = client.post(URL, json=new(make_position(is_active=False)), headers=headers)
    assert _error(response) == (409, "INACTIVE_REFERENCE")
    assert _fields(response) == {"position_id": "This job position is inactive."}


def test_create_with_unknown_division(client, headers, position):
    response = client.post(URL, json=new(position, division_id=999_999), headers=headers)
    assert _fields(response) == {"division_id": "Division not found."}


def test_create_with_inactive_division(client, headers, position, make_division):
    body = new(position, division_id=make_division(is_active=False).id)
    response = client.post(URL, json=body, headers=headers)
    assert _error(response) == (409, "INACTIVE_REFERENCE")
    assert _fields(response) == {"division_id": "This division is inactive."}


@pytest.mark.parametrize("title", ["Mr.", "Ms.", "Mrs.", "Dr."])
def test_create_valid_titles(client, headers, position, title):
    response = client.post(URL, json=new(position, title=title), headers=headers)
    assert response.json()["title"] == title


@pytest.mark.parametrize("title", ["Mister", "mr.", "Mr", "Prof."])
def test_create_invalid_title(client, headers, position, title):
    response = client.post(URL, json=new(position, title=title), headers=headers)
    assert _fields(response) == {"title": "Must be one of Mr., Ms., Mrs., Dr."}


def test_create_blank_title_is_null(client, headers, position):
    assert client.post(URL, json=new(position, title="  "), headers=headers).json()["title"] is None


@pytest.mark.parametrize(
    ("password", "message"),
    [
        ("Short@1", "Password must be 8 to 128 characters."),
        ("x" * 129, "Password must be 8 to 128 characters."),
        ("chan.sreymom@company.com", "Password cannot be your email."),
        ("CHAN.SREYMOM@company.com", "Password cannot be your email."),
    ],
)
def test_create_bad_temporary_password(client, headers, position, password, message):
    response = client.post(URL, json=new(position, temporary_password=password), headers=headers)
    assert _fields(response) == {"temporary_password": message}


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("staff_id", "x" * 21),
        ("name_en", "x" * 101),
        ("phone", "1" * 21),
        ("email", "not-an-email"),
        ("email", "a@b"),
        ("secondary_email", "nope"),
        ("avatar_url", "ftp://x.com/a.jpg"),
        ("avatar_url", "//evil.com/a.jpg"),
        ("email_notifications", "maybe"),
        ("name_kh", "   "),
    ],
)
def test_create_invalid_fields(client, headers, position, field, value):
    response = client.post(URL, json=new(position, **{field: value}), headers=headers)
    assert _error(response) == (422, "VALIDATION_ERROR")
    assert set(_fields(response)) == {field}


def test_create_khmer_name_of_100_characters(client, headers, position):
    assert (
        client.post(URL, json=new(position, name_kh="ក" * 100), headers=headers).status_code == 201
    )


def test_create_missing_required_fields(client, headers):
    assert set(_fields(client.post(URL, json={}, headers=headers))) == {
        "staff_id",
        "name_en",
        "name_kh",
        "email",
        "position_id",
        "temporary_password",
    }


@pytest.mark.parametrize(
    "field",
    ["id", "password_hash", "must_change_password", "is_active", "roles", "role_codes", "password"],
)
def test_create_refuses_unknown_and_server_fields(client, headers, position, field):
    response = client.post(URL, json=new(position, **{field: "x"}), headers=headers)
    assert _fields(response) == {field: "Unknown field."}


def test_create_needs_admin(client, as_staff, position):
    assert _error(client.post(URL, json=new(position), headers=as_staff)) == (403, "FORBIDDEN")


def test_create_needs_a_token(client, position):
    assert _error(client.post(URL, json=new(position))) == (401, "UNAUTHORIZED")


# --- Task 48: GET /users ---------------------------------------------------------------


@pytest.fixture
def people(admin, division, make_user, make_division, make_location, make_department, position):
    kampot = make_division(department=make_department(location=make_location(province="KAMPOT")))
    return {
        "dara": make_user(
            name_en="Sok Dara",
            name_kh="សុខ ដារ៉ា",
            staff_id="EMP-00123",
            email="sok.dara@company.com",
            division=division,
            position=position,
            roles=["PITIKA", "STAFF"],
        ),
        "lina": make_user(
            name_en="Chea Lina", email="lina@company.com", division=kampot, roles=["PITIKA"]
        ),
        "vuthy": make_user(
            name_en="Keo Vuthy", email="vuthy@company.com", roles=["ROOM_OWNER"], is_active=False
        ),
        "nodiv": make_user(name_en="Ly Nodiv", email="nodiv@company.com", roles=["STAFF"]),
    }


def _names(response) -> list[str]:
    assert response.status_code == 200, response.text
    return [item["name_en"] for item in response.json()["items"]]


def test_list_shape(client, headers, people, division, position):
    body = client.get(URL, params={"search": "EMP-00123"}, headers=headers).json()
    assert set(body) == {"items", "page", "size", "total"}
    item = body["items"][0]
    assert set(item) == LIST_FIELDS
    assert item["role_codes"] == ["STAFF", "PITIKA"]  # seed order
    assert item["division"] == {"id": division.id, "name_en": "IT Division", "name_kh": "ផ្នែក IT"}
    assert item["position"]["id"] == position.id
    assert item["province"]["code"] == "SIEM_REAP"
    assert "password_hash" not in client.get(URL, headers=headers).text


def test_list_sorted_by_name(client, headers, people):
    assert _names(client.get(URL, headers=headers)) == [
        "Acting Admin",
        "Chea Lina",
        "Keo Vuthy",
        "Ly Nodiv",
        "Sok Dara",
    ]


def test_list_filter_active(client, headers, people):
    assert _names(client.get(f"{URL}?is_active=false", headers=headers)) == ["Keo Vuthy"]
    assert "Keo Vuthy" not in _names(client.get(f"{URL}?is_active=true", headers=headers))


@pytest.mark.parametrize(
    ("term", "expected"),
    [
        ("dara", ["Sok Dara"]),
        ("ដារ៉ា", ["Sok Dara"]),
        ("emp-00123", ["Sok Dara"]),
        ("LINA@company", ["Chea Lina"]),
        ("  vuthy ", ["Keo Vuthy"]),
    ],
)
def test_list_search(client, headers, people, term, expected):
    assert _names(client.get(URL, params={"search": term}, headers=headers)) == expected


def test_list_filter_role(client, headers, people):
    assert _names(client.get(f"{URL}?role=PITIKA", headers=headers)) == ["Chea Lina", "Sok Dara"]


def test_list_filter_province(client, headers, people):
    assert _names(client.get(f"{URL}?province=SIEM_REAP", headers=headers)) == ["Sok Dara"]


def test_list_role_and_province(client, headers, people, make_user, division):
    make_user(name_en="Inactive Pitika", division=division, roles=["PITIKA"], is_active=False)
    query = f"{URL}?role=PITIKA&province=SIEM_REAP"
    assert _names(client.get(query, headers=headers)) == ["Inactive Pitika", "Sok Dara"]


def test_user_without_division_matches_no_province(client, headers, people):
    for code in ("PHNOM_PENH", "KAMPOT"):
        assert "Ly Nodiv" not in _names(client.get(f"{URL}?province={code}", headers=headers))


def test_list_filter_division_department_position(client, headers, people, division, position):
    assert _names(client.get(f"{URL}?division_id={division.id}", headers=headers)) == ["Sok Dara"]
    query = f"{URL}?department_id={division.department_id}"
    assert _names(client.get(query, headers=headers)) == ["Sok Dara"]
    assert _names(client.get(f"{URL}?position_id={position.id}", headers=headers)) == ["Sok Dara"]


def test_list_paging(client, headers, people):
    body = client.get(f"{URL}?size=2&page=3", headers=headers).json()
    assert (body["page"], body["size"], body["total"]) == (3, 2, 5)
    assert [item["name_en"] for item in body["items"]] == ["Sok Dara"]


def test_list_page_past_the_end(client, headers, people):
    body = client.get(f"{URL}?page=9", headers=headers).json()
    assert (body["items"], body["total"]) == ([], 5)


@pytest.mark.parametrize(
    ("query", "field"),
    [
        ("role=MANAGER", "role"),
        ("role=staff", "role"),
        ("province=MARS", "province"),
        ("division_id=abc", "division_id"),
        ("department_id=0", "department_id"),
        ("position_id=-1", "position_id"),
        ("size=101", "size"),
        ("is_active=x", "is_active"),
    ],
)
def test_list_bad_query(client, headers, query, field):
    response = client.get(f"{URL}?{query}", headers=headers)
    assert _error(response) == (422, "VALIDATION_ERROR")
    assert set(_fields(response)) == {field}


@pytest.mark.parametrize("role", ["STAFF", "ROOM_OWNER", "PITIKA", "IT_LEAD", "IT_STAFF"])
def test_list_needs_admin(client, make_user, auth_headers, role):
    response = client.get(URL, headers=auth_headers(make_user(roles=[role])))
    assert _error(response) == (403, "FORBIDDEN")


def test_list_needs_a_token(client):
    assert _error(client.get(URL)) == (401, "UNAUTHORIZED")


# --- Task 49: GET /users/{id} ----------------------------------------------------------


def test_get_user(client, headers, people, division, make_room):
    dara = people["dara"]
    room = make_room(owner=dara)
    response = client.get(f"{URL}/{dara.id}", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert set(body) == DETAIL_FIELDS
    assert [role["code"] for role in body["roles"]] == ["STAFF", "PITIKA"]
    assert body["owned_room_ids"] == [room.id]
    assert body["province"]["code"] == "SIEM_REAP"
    assert "password_hash" not in response.text


def test_get_inactive_user(client, headers, people):
    assert client.get(f"{URL}/{people['vuthy'].id}", headers=headers).json()["is_active"] is False


def test_get_unknown_user(client, headers):
    assert _error(client.get(f"{URL}/999999", headers=headers)) == (404, "NOT_FOUND")


@pytest.mark.parametrize("bad_id", ["abc", "0", "-1"])
def test_get_bad_id(client, headers, bad_id):
    assert _error(client.get(f"{URL}/{bad_id}", headers=headers)) == (422, "VALIDATION_ERROR")


def test_get_needs_admin(client, as_staff, admin):
    assert _error(client.get(f"{URL}/{admin.id}", headers=as_staff)) == (403, "FORBIDDEN")


def test_get_needs_a_token(client, admin):
    assert _error(client.get(f"{URL}/{admin.id}")) == (401, "UNAUTHORIZED")


# --- Task 50: PUT /users/{id}/roles ----------------------------------------------------


@pytest.fixture
def member(make_user, division):
    return make_user(name_en="Member", division=division, roles=["STAFF"])


def put_roles(client, headers, user, codes):
    return client.put(f"{URL}/{user.id}/roles", json={"role_codes": codes}, headers=headers)


def test_set_roles(client, headers, member):
    response = put_roles(client, headers, member, ["IT_STAFF", "STAFF"])
    assert response.status_code == 200
    body = response.json()
    assert set(body) == CHANGED_FIELDS
    assert [role["code"] for role in body["roles"]] == ["STAFF", "IT_STAFF"]
    assert body["rooms_unassigned"] == []


def test_set_roles_duplicates_saved_once(client, headers, member):
    body = put_roles(client, headers, member, ["STAFF", "STAFF"]).json()
    assert [role["code"] for role in body["roles"]] == ["STAFF"]


def test_set_no_roles(client, headers, member):
    assert put_roles(client, headers, member, []).json()["roles"] == []


@pytest.mark.parametrize("codes", [["MANAGER"], ["STAFF", "staff"], ["ADMIN", ""]])
def test_set_unknown_role(client, headers, member, codes):
    response = put_roles(client, headers, member, codes)
    assert _error(response) == (422, "VALIDATION_ERROR")
    assert _fields(response) == {"role_codes": "Unknown role."}


@pytest.mark.parametrize("body", [{}, {"role_codes": None}, {"role_codes": "STAFF"}])
def test_set_roles_bad_body(client, headers, member, body):
    response = client.put(f"{URL}/{member.id}/roles", json=body, headers=headers)
    assert set(_fields(response)) == {"role_codes"}


@pytest.mark.parametrize("role", ["PITIKA", "IT_LEAD", "IT_STAFF"])
def test_role_needs_division(client, headers, make_user, role):
    user = make_user(roles=["STAFF"])
    response = put_roles(client, headers, user, ["STAFF", role])
    assert _error(response) == (409, "DIVISION_REQUIRED")
    assert _fields(response) == {"role_codes": "This role needs a division."}


def test_remove_room_owner_clears_rooms(client, headers, make_user, make_room, db_session):
    owner = make_user(roles=["ROOM_OWNER", "STAFF"])
    second, first = make_room(owner=owner), make_room(owner=owner)
    body = put_roles(client, headers, owner, ["STAFF"]).json()
    assert body["rooms_unassigned"] == sorted([first.id, second.id])
    assert body["owned_room_ids"] == []
    db_session.refresh(first)
    assert first.room_owner_id is None
    # Giving the role back does not restore the rooms.
    again = put_roles(client, headers, owner, ["ROOM_OWNER", "STAFF"]).json()
    assert (again["owned_room_ids"], again["rooms_unassigned"]) == ([], [])


def test_keep_room_owner_keeps_rooms(client, headers, make_user, make_room):
    owner = make_user(roles=["ROOM_OWNER"])
    room = make_room(owner=owner)
    body = put_roles(client, headers, owner, ["ROOM_OWNER", "STAFF"]).json()
    assert (body["owned_room_ids"], body["rooms_unassigned"]) == ([room.id], [])


def test_remove_own_admin(client, headers, admin):
    response = put_roles(client, headers, admin, ["STAFF"])
    assert _error(response) == (409, "SELF_ACTION_NOT_ALLOWED")
    assert _fields(response) == {"role_codes": "You cannot do this to yourself."}


def test_change_own_roles_keeping_admin(client, headers, admin):
    body = put_roles(client, headers, admin, ["ADMIN", "STAFF"]).json()
    assert [role["code"] for role in body["roles"]] == ["ADMIN", "STAFF"]


def test_remove_admin_from_another_admin(client, headers, make_user):
    other = make_user(roles=["ADMIN"])
    assert put_roles(client, headers, other, ["STAFF"]).status_code == 200


def test_new_roles_apply_on_next_request(client, headers, member, auth_headers):
    member_headers = auth_headers(member)
    assert client.get(URL, headers=member_headers).status_code == 403
    put_roles(client, headers, member, ["ADMIN"])
    assert client.get(URL, headers=member_headers).status_code == 200


def test_last_admin_cannot_lose_admin(db_session, make_user):
    from app.services import user as user_service

    last = make_user(roles=["ADMIN"])
    make_user(roles=["ADMIN"], is_active=False)  # inactive admins do not count
    actor = make_user(roles=["STAFF"])
    with pytest.raises(AppError) as error:
        user_service.set_user_roles(db_session, last.id, ["STAFF"], actor_id=actor.id)
    assert (error.value.status, error.value.code) == (409, "LAST_ADMIN")


def test_set_roles_unknown_user(client, headers):
    response = client.put(f"{URL}/999999/roles", json={"role_codes": []}, headers=headers)
    assert _error(response) == (404, "NOT_FOUND")


def test_set_roles_needs_admin(client, as_staff, member):
    assert _error(put_roles(client, as_staff, member, ["ADMIN"])) == (403, "FORBIDDEN")


def test_set_roles_needs_a_token(client, member):
    response = client.put(f"{URL}/{member.id}/roles", json={"role_codes": []})
    assert _error(response) == (401, "UNAUTHORIZED")


# --- Task 51: PATCH /users/{id} --------------------------------------------------------


@pytest.fixture
def user(make_user, division, position, db_session):
    user = make_user(
        staff_id="EMP-00200",
        name_en="Sok Dara",
        email="sok.dara@company.com",
        title="Mr.",
        phone="011 111 111",
        division=division,
        position=position,
        roles=["STAFF"],
    )
    user.updated_at = datetime(2026, 1, 1)
    db_session.flush()
    return user


def patch(client, headers, user, body):
    return client.patch(f"{URL}/{user.id}", json=body, headers=headers)


def test_patch_user(client, headers, user):
    body = {"name_en": "Sok Dara II", "email": " Dara.New@Company.com ", "phone": "012 000 000"}
    response = patch(client, headers, user, body)
    assert response.status_code == 200
    result = response.json()
    assert set(result) == CHANGED_FIELDS
    assert (result["name_en"], result["email"], result["phone"]) == (
        "Sok Dara II",
        "dara.new@company.com",
        "012 000 000",
    )
    assert result["staff_id"] == "EMP-00200"
    assert result["rooms_unassigned"] == []
    assert result["updated_at"] != "2026-01-01T00:00:00Z"


def test_patch_empty_body(client, headers, user):
    response = patch(client, headers, user, {})
    assert response.status_code == 200
    assert response.json()["updated_at"] == "2026-01-01T00:00:00Z"


def test_patch_same_values(client, headers, user, division):
    body = {"name_en": "Sok Dara", "email": "SOK.DARA@company.com", "division_id": division.id}
    assert patch(client, headers, user, body).json()["updated_at"] == "2026-01-01T00:00:00Z"


@pytest.mark.parametrize(
    "field",
    ["staff_id", "name_en", "name_kh", "email", "position_id", "email_notifications", "is_active"],
)
def test_patch_null_for_required(client, headers, user, field):
    assert _fields(patch(client, headers, user, {field: None})) == {
        field: "This field is required."
    }


@pytest.mark.parametrize(
    "field", ["title", "secondary_email", "phone", "avatar_url", "division_id"]
)
def test_patch_null_clears_optional(client, headers, user, field):
    response = patch(client, headers, user, {field: None})
    assert response.status_code == 200, response.text
    key = "division" if field == "division_id" else field
    assert response.json()[key] is None


def test_clearing_division_clears_department_and_province(client, headers, user):
    body = patch(client, headers, user, {"division_id": None}).json()
    assert (body["division"], body["department"], body["province"]) == (None, None, None)


@pytest.mark.parametrize(
    "field", ["temporary_password", "password_hash", "must_change_password", "id", "roles"]
)
def test_patch_refuses_unknown_and_server_fields(client, headers, user, field):
    assert _fields(patch(client, headers, user, {field: "x"})) == {field: "Unknown field."}


def test_patch_duplicate_email(client, headers, user, make_user):
    make_user(email="taken@company.com")
    response = patch(client, headers, user, {"email": "TAKEN@company.com"})
    assert _error(response) == (409, "DUPLICATE")
    assert _fields(response) == {"email": "This email already exists."}


def test_patch_duplicate_staff_id(client, headers, user, make_user):
    make_user(staff_id="EMP-77777")
    response = patch(client, headers, user, {"staff_id": "emp-77777"})
    assert _fields(response) == {"staff_id": "This staff ID already exists."}


def test_patch_secondary_email_equal_to_stored_email(client, headers, user):
    response = patch(client, headers, user, {"secondary_email": "Sok.Dara@company.com"})
    assert _fields(response) == {"secondary_email": "Second email must be different."}


def test_patch_email_equal_to_stored_secondary(client, headers, user, db_session):
    user.secondary_email = "dara@gmail.com"
    db_session.flush()
    response = patch(client, headers, user, {"email": "dara@gmail.com"})
    assert _fields(response) == {"email": "Second email must be different."}


def test_patch_swap_emails(client, headers, user, db_session):
    user.secondary_email = "dara@gmail.com"
    db_session.flush()
    body = {"email": "dara@gmail.com", "secondary_email": "sok.dara@company.com"}
    assert patch(client, headers, user, body).status_code == 200


def test_patch_inactive_position(client, headers, user, make_position):
    response = patch(client, headers, user, {"position_id": make_position(is_active=False).id})
    assert _error(response) == (409, "INACTIVE_REFERENCE")


def test_patch_unknown_division(client, headers, user):
    assert _fields(patch(client, headers, user, {"division_id": 999_999})) == {
        "division_id": "Division not found."
    }


def test_patch_keeps_inactive_references(client, headers, user, division, position, db_session):
    division.is_active = False
    position.is_active = False
    db_session.flush()
    body = {"name_en": "Renamed", "division_id": division.id, "position_id": position.id}
    assert patch(client, headers, user, body).status_code == 200


@pytest.mark.parametrize("role", ["PITIKA", "IT_LEAD", "IT_STAFF"])
def test_remove_division_from_user_who_needs_it(client, headers, user, role, db_session):
    from tests.factories import set_roles

    set_roles(db_session, user, [role])
    response = patch(client, headers, user, {"division_id": None})
    assert _error(response) == (409, "DIVISION_REQUIRED")
    assert _fields(response) == {"division_id": "This role needs a division."}


def test_deactivate_user_clears_rooms(client, headers, user, make_room, db_session):
    rooms = [make_room(owner=user), make_room(owner=user)]
    response = patch(client, headers, user, {"is_active": False})
    assert response.status_code == 200
    body = response.json()
    assert body["is_active"] is False
    assert body["rooms_unassigned"] == sorted(room.id for room in rooms)
    for room in rooms:
        db_session.refresh(room)
        assert room.room_owner_id is None
    # Reactivating does not restore them.
    again = patch(client, headers, user, {"is_active": True}).json()
    assert (again["owned_room_ids"], again["rooms_unassigned"]) == ([], [])


def test_deactivated_user_token_stops_working(client, headers, user, auth_headers):
    user_headers = auth_headers(user)
    assert client.get("/api/v1/me", headers=user_headers).status_code == 200
    patch(client, headers, user, {"is_active": False})
    assert _error(client.get("/api/v1/me", headers=user_headers)) == (401, "UNAUTHORIZED")


def test_deactivate_self(client, headers, admin):
    response = patch(client, headers, admin, {"is_active": False})
    assert _error(response) == (409, "SELF_ACTION_NOT_ALLOWED")
    assert _fields(response) == {"is_active": "You cannot do this to yourself."}


def test_edit_self_without_deactivating(client, headers, admin):
    assert patch(client, headers, admin, {"phone": "012"}).status_code == 200


def test_deactivate_another_admin(client, headers, make_user):
    assert (
        patch(client, headers, make_user(roles=["ADMIN"]), {"is_active": False}).status_code == 200
    )


def test_last_admin_cannot_be_deactivated(db_session, make_user):
    from app.services import user as user_service

    last = make_user(roles=["ADMIN"])
    actor = make_user(roles=["STAFF"])
    with pytest.raises(AppError) as error:
        user_service.update_user(db_session, last.id, {"is_active": False}, actor_id=actor.id)
    assert (error.value.status, error.value.code) == (409, "LAST_ADMIN")
    assert error.value.fields == {"is_active": "You cannot remove the last Admin."}


def test_patch_unknown_user(client, headers):
    assert _error(client.patch(f"{URL}/999999", json={}, headers=headers)) == (404, "NOT_FOUND")


def test_patch_needs_admin(client, as_staff, user):
    assert _error(patch(client, as_staff, user, {"phone": "1"})) == (403, "FORBIDDEN")


def test_patch_needs_a_token(client, user):
    assert _error(client.patch(f"{URL}/{user.id}", json={})) == (401, "UNAUTHORIZED")


def test_no_delete(client, headers, user):
    assert _error(client.delete(f"{URL}/{user.id}", headers=headers)) == (405, "METHOD_NOT_ALLOWED")


# --- Task 52: POST /users/{id}/reset-password ------------------------------------------


def reset(client, headers, user, password="Reset@2026"):
    return client.post(
        f"{URL}/{user.id}/reset-password", json={"temporary_password": password}, headers=headers
    )


def test_reset_password(client, headers, user, auth_headers, db_session):
    old_headers = auth_headers(user)
    response = reset(client, headers, user)
    assert response.status_code == 204
    assert response.content == b""
    db_session.refresh(user)
    assert user.must_change_password is True
    assert _error(client.get("/api/v1/me", headers=old_headers)) == (401, "UNAUTHORIZED")
    login = client.post(LOGIN, json={"email": "sok.dara@company.com", "password": "Reset@2026"})
    assert login.status_code == 200
    assert login.json()["must_change_password"] is True


def test_reset_password_of_inactive_user(client, headers, make_user, db_session):
    inactive = make_user(is_active=False)
    old_hash = inactive.password_hash
    assert reset(client, headers, inactive).status_code == 204
    db_session.refresh(inactive)
    assert inactive.password_hash != old_hash


def test_admin_resets_own_password(client, headers, admin):
    assert reset(client, headers, admin).status_code == 204
    assert _error(client.get(URL, headers=headers)) == (401, "UNAUTHORIZED")


@pytest.mark.parametrize(
    ("password", "message"),
    [
        ("Short@1", "Password must be 8 to 128 characters."),
        ("y" * 129, "Password must be 8 to 128 characters."),
        ("Sok.Dara@Company.com", "Password cannot be your email."),
    ],
)
def test_reset_bad_password(client, headers, user, password, message):
    assert _fields(reset(client, headers, user, password)) == {"temporary_password": message}


@pytest.mark.parametrize(
    "body", [{}, {"temporary_password": None}, {"temporary_password": "Reset@2026", "x": 1}]
)
def test_reset_bad_body(client, headers, user, body):
    response = client.post(f"{URL}/{user.id}/reset-password", json=body, headers=headers)
    assert _error(response) == (422, "VALIDATION_ERROR")


def test_reset_unknown_user(client, headers):
    response = client.post(
        f"{URL}/999999/reset-password", json={"temporary_password": "Reset@2026"}, headers=headers
    )
    assert _error(response) == (404, "NOT_FOUND")


def test_reset_needs_admin(client, as_staff, user):
    assert _error(reset(client, as_staff, user)) == (403, "FORBIDDEN")


def test_reset_needs_a_token(client, user):
    response = client.post(
        f"{URL}/{user.id}/reset-password", json={"temporary_password": "Reset@2026"}
    )
    assert _error(response) == (401, "UNAUTHORIZED")
