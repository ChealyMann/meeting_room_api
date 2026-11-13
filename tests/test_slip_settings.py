"""The Request slip settings: who signs as Director of Cabinet, and the address line."""

import pytest

URL = "/api/v1/slip-settings"
DEFAULT_ADDRESS = (
    "ប្រអប់សំបុត្រលេខ ២៥, ផ្ទះលេខ ៨៨ ផ្លូវលេខ ១០២ កែងផ្លូវលេខ ១៩ សង្កាត់វត្តភ្នំ ខណ្ឌដូនពេញ "
    "រាជធានីភ្នំពេញ, ទូរស័ព្ទ ៖ (៨៥៥-២៣) ៧២២ ៥៦៣, ទូរស័ព្ទ / ទូរសារ ៖ (៨៥៥-២៣) ៩២៦ ១១៧"
)


def _fields(response) -> dict:
    return response.json()["error"]["fields"]


def test_first_read_has_the_default_address_and_no_director(client, as_admin):
    body = client.get(URL, headers=as_admin).json()
    assert body["address_kh"] == DEFAULT_ADDRESS
    assert body["director"] is None
    assert set(body) == {"director", "address_kh", "updated_at"}


def test_set_the_director_and_address(client, as_admin, make_user):
    director = make_user(name_en="Pich Visal", name_kh="ពេជ្រ វិសាល")
    body = {"director_user_id": director.id, "address_kh": "  ផ្ទះលេខ ៨៨  "}
    saved = client.put(URL, json=body, headers=as_admin)
    assert saved.status_code == 200
    again = client.get(URL, headers=as_admin).json()
    assert again["director"] == {"id": director.id, "name_en": "Pich Visal", "name_kh": "ពេជ្រ វិសាល"}
    assert again["address_kh"] == "ផ្ទះលេខ ៨៨"


def test_clear_the_director(client, as_admin, make_user):
    director = make_user()
    client.put(URL, json={"director_user_id": director.id, "address_kh": "x"}, headers=as_admin)
    cleared = client.put(URL, json={"director_user_id": None, "address_kh": "x"}, headers=as_admin)
    assert cleared.json()["director"] is None


def test_inactive_director(client, as_admin, make_user):
    gone = make_user(is_active=False)
    response = client.put(
        URL, json={"director_user_id": gone.id, "address_kh": "x"}, headers=as_admin
    )
    assert response.status_code == 409
    assert _fields(response) == {"director_user_id": "This user is inactive."}


@pytest.mark.parametrize("address", ["", "   ", "x" * 501])
def test_address_is_1_to_500_characters(client, as_admin, address):
    response = client.put(
        URL, json={"director_user_id": None, "address_kh": address}, headers=as_admin
    )
    assert response.status_code == 422
    assert "address_kh" in _fields(response)


def test_staff_cannot_read_or_change(client, as_staff):
    assert client.get(URL, headers=as_staff).status_code == 403
    body = {"director_user_id": None, "address_kh": "x"}
    assert client.put(URL, json=body, headers=as_staff).status_code == 403
