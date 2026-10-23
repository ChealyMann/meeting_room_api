"""GET /api/v1/me (spec sections 10 and 11)."""

import re
from datetime import datetime

URL = "/api/v1/me"

USER_DETAIL_FIELDS = {
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
UTC_Z = re.compile(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ")


def test_full_profile(
    client,
    make_user,
    make_division,
    make_department,
    make_location,
    make_room,
    auth_headers,
    db_session,
):
    location = make_location(province="SIEM_REAP")
    department = make_department(location=location, name_en="Operations", name_kh="ប្រតិបត្តិការ")
    division = make_division(department=department, name_en="IT Division", name_kh="ផ្នែកព័ត៌មានវិទ្យា")
    user = make_user(
        roles=["PITIKA", "STAFF", "ROOM_OWNER"],
        division=division,
        staff_id="EMP-00123",
        title="Mr.",
        name_en="Sok Dara",
        name_kh="សុខ ដារ៉ា",
        email="sok.dara@company.com",
        phone="012 345 678",
        last_login_at=datetime(2026, 10, 21, 1, 45),
    )
    first, second = make_room(owner=user), make_room(owner=user)
    make_room()  # someone else's room

    response = client.get(URL, headers=auth_headers(user))
    assert response.status_code == 200
    body = response.json()
    assert set(body) == USER_DETAIL_FIELDS
    assert body["id"] == user.id
    assert (body["staff_id"], body["title"], body["name_en"], body["name_kh"]) == (
        "EMP-00123",
        "Mr.",
        "Sok Dara",
        "សុខ ដារ៉ា",
    )
    assert body["email"] == "sok.dara@company.com"
    assert (body["secondary_email"], body["avatar_url"]) == (None, None)
    assert body["phone"] == "012 345 678"
    assert body["email_notifications"] is True
    assert body["division"] == {
        "id": division.id,
        "name_en": "IT Division",
        "name_kh": "ផ្នែកព័ត៌មានវិទ្យា",
    }
    assert body["department"] == {
        "id": department.id,
        "name_en": "Operations",
        "name_kh": "ប្រតិបត្តិការ",
    }
    assert body["position"] == {
        "id": user.position.id,
        "name_en": user.position.name_en,
        "name_kh": user.position.name_kh,
    }
    assert body["province"] == {"code": "SIEM_REAP", "name_en": "Siem Reap", "name_kh": "សៀមរាប"}
    assert [role["code"] for role in body["roles"]] == ["ROOM_OWNER", "STAFF", "PITIKA"]
    assert set(body["roles"][0]) == {"code", "name_en", "name_kh"}
    assert body["owned_room_ids"] == sorted([first.id, second.id])
    assert body["is_active"] is True
    assert body["must_change_password"] is False
    assert body["last_login_at"] == "2026-10-21T01:45:00Z"
    assert UTC_Z.fullmatch(body["created_at"])
    assert UTC_Z.fullmatch(body["updated_at"])


def test_role_names_come_from_the_roles_table(client, make_user, auth_headers, db_session):
    from sqlalchemy import select

    from app.models import Role

    user = make_user(roles=["STAFF"])
    staff = db_session.scalars(select(Role).where(Role.code == "STAFF")).one()
    staff.name_kh = "បុគ្គលិក"
    db_session.flush()
    roles = client.get(URL, headers=auth_headers(user)).json()["roles"]
    assert roles == [{"code": "STAFF", "name_en": staff.name_en, "name_kh": "បុគ្គលិក"}]


def test_user_without_division_roles_or_rooms(client, make_user, auth_headers):
    body = client.get(URL, headers=auth_headers(make_user())).json()
    assert body["division"] is None
    assert body["department"] is None
    assert body["province"] is None
    assert body["roles"] == []
    assert body["owned_room_ids"] == []
    assert body["last_login_at"] is None


def test_allowed_while_password_change_required(client, make_user, auth_headers):
    user = make_user(must_change_password=True)
    response = client.get(URL, headers=auth_headers(user))
    assert response.status_code == 200
    assert response.json()["must_change_password"] is True


def test_needs_a_token(client):
    assert client.get(URL).status_code == 401


def test_never_returns_the_password_hash(client, make_user, auth_headers):
    user = make_user()
    response = client.get(URL, headers=auth_headers(user))
    assert "password" not in response.text.replace("must_change_password", "")
    assert user.password_hash not in response.text
