"""GET /api/v1/provinces (spec section 12, rule R1)."""

URL = "/api/v1/provinces"


def test_lists_all_25_provinces(client, make_user, auth_headers):
    response = client.get(URL, headers=auth_headers(make_user()))
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"items", "total"}
    assert body["total"] == 25
    assert len(body["items"]) == 25
    assert body["items"][0] == {"code": "PHNOM_PENH", "name_en": "Phnom Penh", "name_kh": "ភ្នំពេញ"}
    rest = [item["name_en"] for item in body["items"][1:]]
    assert rest == sorted(rest)
    assert {"code": "SIEM_REAP", "name_en": "Siem Reap", "name_kh": "សៀមរាប"} in body["items"]


def test_ignores_paging_and_status_filters(client, make_user, auth_headers):
    response = client.get(f"{URL}?page=3&size=2&is_active=false", headers=auth_headers(make_user()))
    assert response.status_code == 200
    assert response.json()["total"] == 25
    assert len(response.json()["items"]) == 25


def test_any_role_can_read(client, make_user, auth_headers):
    for roles in ([], ["STAFF"], ["ADMIN"], ["IT_STAFF"]):
        assert client.get(URL, headers=auth_headers(make_user(roles=roles))).status_code == 200


def test_needs_a_token(client):
    assert client.get(URL).status_code == 401


def test_not_allowed_while_password_change_required(client, make_user, auth_headers):
    response = client.get(URL, headers=auth_headers(make_user(must_change_password=True)))
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "PASSWORD_CHANGE_REQUIRED"


def test_no_other_methods(client, make_user, auth_headers):
    headers = auth_headers(make_user(roles=["ADMIN"]))
    assert client.post(URL, json={}, headers=headers).status_code == 405
    assert client.delete(URL, headers=headers).status_code == 405
