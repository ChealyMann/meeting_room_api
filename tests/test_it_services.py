"""IT services: spec 9.15, decision B-13."""

from tests.booking_helpers import error, fields

URL = "/api/v1/it-services"
OUT_FIELDS = {
    "id",
    "name",
    "description",
    "sort_order",
    "is_active",
    "version",
    "created_at",
    "updated_at",
}
NEW = {"name": "Wi-Fi support", "description": "Network help", "sort_order": 1}


def test_create_service(client, as_admin):
    response = client.post(URL, json=NEW, headers=as_admin)
    assert response.status_code == 201
    body = response.json()
    assert set(body) == OUT_FIELDS
    assert (body["name"], body["version"], body["is_active"]) == ("Wi-Fi support", 1, True)


def test_name_2_to_200(client, as_admin):
    short = client.post(URL, json={"name": "A"}, headers=as_admin)
    assert error(short) == (422, "VALIDATION_ERROR")
    assert "name" in fields(short)
    assert client.post(URL, json={"name": "AB"}, headers=as_admin).status_code == 201
    assert client.post(URL, json={"name": "x" * 200}, headers=as_admin).status_code == 201
    assert "name" in fields(client.post(URL, json={"name": "x" * 201}, headers=as_admin))


def test_name_unique(client, as_admin):
    client.post(URL, json=NEW, headers=as_admin)
    response = client.post(URL, json={"name": "wi-fi SUPPORT"}, headers=as_admin)
    assert error(response) == (409, "DUPLICATE")
    assert fields(response) == {"name": "This name already exists."}


def test_patch_needs_version(client, as_admin, make_it_service):
    item = make_it_service()
    response = client.patch(f"{URL}/{item.id}", json={"name": "New name"}, headers=as_admin)
    assert error(response) == (422, "VALIDATION_ERROR")
    assert "version" in fields(response)


def test_patch_stale_version(client, as_admin, make_it_service):
    item = make_it_service()
    url = f"{URL}/{item.id}"
    first = client.patch(url, json={"version": 1, "name": "First"}, headers=as_admin)
    assert first.status_code == 200
    second = client.patch(url, json={"version": 1, "name": "Second"}, headers=as_admin)
    assert error(second) == (409, "STALE_VERSION")
    assert second.json()["error"]["message"] == "This item changed. Reload it."
    assert client.patch(url, json={"version": 2}, headers=as_admin).json()["name"] == "First"


def test_patch_raises_version(client, as_admin, make_it_service):
    item = make_it_service()
    response = client.patch(
        f"{URL}/{item.id}", json={"version": 1, "is_active": False}, headers=as_admin
    )
    assert (response.json()["version"], response.json()["is_active"]) == (2, False)


def test_patch_duplicate_name(client, as_admin, make_it_service, db_session):
    item = make_it_service(name="One")
    make_it_service(name="Two")
    db_session.commit()
    response = client.patch(
        f"{URL}/{item.id}", json={"version": 1, "name": "two"}, headers=as_admin
    )
    assert error(response) == (409, "DUPLICATE")


def test_patch_unknown(client, as_admin):
    response = client.patch(f"{URL}/999999", json={"version": 1}, headers=as_admin)
    assert error(response) == (404, "NOT_FOUND")


def test_staff_cannot_write(client, as_staff, make_it_service):
    item = make_it_service()
    assert error(client.post(URL, json=NEW, headers=as_staff)) == (403, "FORBIDDEN")
    response = client.patch(f"{URL}/{item.id}", json={"version": 1}, headers=as_staff)
    assert error(response) == (403, "FORBIDDEN")


def test_list_needs_a_token(client):
    assert error(client.get(URL)) == (401, "UNAUTHORIZED")


def test_staff_sees_only_active(client, as_staff, make_it_service):
    make_it_service(name="Zz On")
    make_it_service(name="Zz Off", is_active=False)
    for params in ({"search": "Zz"}, {"search": "Zz", "is_active": "false"}):
        body = client.get(URL, params=params, headers=as_staff).json()
        assert [item["name"] for item in body["items"]] == ["Zz On"]


def test_admin_filters_is_active(client, as_admin, make_it_service):
    make_it_service(name="Zz On")
    make_it_service(name="Zz Off", is_active=False)

    def names(query):
        body = client.get(URL, params={"search": "Zz", **query}, headers=as_admin).json()
        return [item["name"] for item in body["items"]]

    assert names({}) == ["Zz Off", "Zz On"]
    assert names({"is_active": "true"}) == ["Zz On"]
    assert names({"is_active": "false"}) == ["Zz Off"]


def test_list_shape_and_order(client, as_staff, make_it_service):
    make_it_service(name="Zz B", sort_order=2)
    make_it_service(name="Zz A", sort_order=2)
    make_it_service(name="Zz C", sort_order=1)
    body = client.get(URL, params={"search": "Zz"}, headers=as_staff).json()
    assert set(body) == {"items", "page", "size", "total"}
    assert set(body["items"][0]) == OUT_FIELDS
    assert [item["name"] for item in body["items"]] == ["Zz C", "Zz A", "Zz B"]


def test_html_refused(client, as_admin, make_it_service):
    response = client.post(URL, json={**NEW, "description": "<b>x</b>"}, headers=as_admin)
    assert error(response) == (422, "VALIDATION_ERROR")
    assert "description" in fields(response)
    item = make_it_service()
    response = client.patch(
        f"{URL}/{item.id}", json={"version": 1, "name": "<i>x</i>"}, headers=as_admin
    )
    assert "name" in fields(response)


def test_description_blank_becomes_null(client, as_admin):
    response = client.post(URL, json={"name": "Lunch", "description": "  "}, headers=as_admin)
    assert response.json()["description"] is None
