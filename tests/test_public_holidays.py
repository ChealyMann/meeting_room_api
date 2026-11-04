"""Public holidays: spec 9.15."""

from datetime import date

from tests.booking_helpers import error, fields

URL = "/api/v1/public-holidays"
OUT_FIELDS = {"id", "holiday_date", "name_km", "name_en", "remarks", "created_at", "updated_at"}
NEW = {"holiday_date": "2027-01-01", "name_km": "ទិវាចូលឆ្នាំសកល"}


def test_create_holiday(client, as_admin):
    response = client.post(URL, json=NEW, headers=as_admin)
    assert response.status_code == 201
    body = response.json()
    assert set(body) == OUT_FIELDS
    assert (body["holiday_date"], body["name_en"], body["remarks"]) == ("2027-01-01", None, None)
    full = {"holiday_date": "2027-01-02", "name_km": "ក", "name_en": "B", "remarks": "C"}
    assert client.post(URL, json=full, headers=as_admin).json()["name_en"] == "B"


def test_name_km_required(client, as_admin):
    response = client.post(URL, json={"holiday_date": "2027-01-01"}, headers=as_admin)
    assert error(response) == (422, "VALIDATION_ERROR")
    assert "name_km" in fields(response)


def test_bad_date(client, as_admin):
    response = client.post(URL, json={**NEW, "holiday_date": "2027-13-40"}, headers=as_admin)
    assert "holiday_date" in fields(response)


def test_holiday_date_unique(client, as_admin):
    client.post(URL, json=NEW, headers=as_admin)
    response = client.post(URL, json={**NEW, "name_km": "ផ្សេង"}, headers=as_admin)
    assert error(response) == (409, "DUPLICATE")
    assert fields(response) == {"holiday_date": "This date already has a holiday."}


def test_html_refused(client, as_admin):
    response = client.post(URL, json={**NEW, "remarks": "<b>x</b>"}, headers=as_admin)
    assert "remarks" in fields(response)


def test_staff_cannot_write(client, as_staff, make_holiday):
    item = make_holiday(date(2027, 5, 1))
    assert error(client.post(URL, json=NEW, headers=as_staff)) == (403, "FORBIDDEN")
    assert error(client.patch(f"{URL}/{item.id}", json={}, headers=as_staff)) == (403, "FORBIDDEN")
    assert error(client.delete(f"{URL}/{item.id}", headers=as_staff)) == (403, "FORBIDDEN")


def test_list_by_year_sorted_by_date(client, as_staff, make_holiday):
    make_holiday(date(2027, 5, 1))
    make_holiday(date(2027, 1, 1))
    make_holiday(date(2028, 1, 1))
    body = client.get(URL, params={"year": 2027}, headers=as_staff).json()
    assert set(body) == {"items", "page", "size", "total"}
    assert [item["holiday_date"] for item in body["items"]] == ["2027-01-01", "2027-05-01"]
    assert set(body["items"][0]) == OUT_FIELDS
    everything = client.get(URL, params={"size": 100}, headers=as_staff).json()
    dates = [item["holiday_date"] for item in everything["items"]]
    assert dates == sorted(dates) and "2028-01-01" in dates


def test_list_bad_year(client, as_staff):
    assert error(client.get(URL, params={"year": "abc"}, headers=as_staff)) == (
        422,
        "VALIDATION_ERROR",
    )


def test_list_needs_a_token(client):
    assert error(client.get(URL)) == (401, "UNAUTHORIZED")


def test_patch_holiday(client, as_admin, make_holiday):
    item = make_holiday(date(2027, 5, 1), name_en="Old", remarks="r")
    response = client.patch(
        f"{URL}/{item.id}", json={"name_en": None, "name_km": "ថ្មី"}, headers=as_admin
    )
    body = response.json()
    assert (body["name_km"], body["name_en"], body["remarks"]) == ("ថ្មី", None, "r")


def test_patch_date_to_taken_date(client, as_admin, make_holiday, db_session):
    make_holiday(date(2027, 5, 1))
    item = make_holiday(date(2027, 5, 2))
    db_session.commit()
    response = client.patch(
        f"{URL}/{item.id}", json={"holiday_date": "2027-05-01"}, headers=as_admin
    )
    assert error(response) == (409, "DUPLICATE")
    assert fields(response) == {"holiday_date": "This date already has a holiday."}


def test_patch_null_for_required(client, as_admin, make_holiday):
    item = make_holiday(date(2027, 5, 1))
    for field in ("holiday_date", "name_km"):
        response = client.patch(f"{URL}/{item.id}", json={field: None}, headers=as_admin)
        assert field in fields(response)


def test_patch_unknown(client, as_admin):
    assert error(client.patch(f"{URL}/999999", json={}, headers=as_admin)) == (404, "NOT_FOUND")


def test_delete_holiday(client, as_admin, make_holiday):
    item = make_holiday(date(2031, 5, 1))
    response = client.delete(f"{URL}/{item.id}", headers=as_admin)
    assert response.status_code == 204 and response.content == b""
    body = client.get(URL, params={"year": 2031}, headers=as_admin).json()
    assert body["items"] == [] and body["total"] == 0


def test_delete_unknown(client, as_admin):
    assert error(client.delete(f"{URL}/999999", headers=as_admin)) == (404, "NOT_FOUND")
