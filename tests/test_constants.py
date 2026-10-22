import json

from app.constants.provinces import PROVINCE_CODES, PROVINCES, get_province
from app.constants.roles import RoleCode
from tests.conftest import ROOT


def test_there_are_25_provinces_with_unique_codes():
    assert len(PROVINCES) == 25
    assert len(PROVINCE_CODES) == 25


def test_phnom_penh_first_then_a_to_z():
    assert PROVINCES[0].code == "PHNOM_PENH"
    rest = [province.name_en for province in PROVINCES[1:]]
    assert rest == sorted(rest)


def test_every_province_has_english_and_khmer_names():
    for province in PROVINCES:
        assert province.name_en.strip()
        assert province.name_kh.strip()
        assert province.code == province.code.upper()


def test_province_names_match_spec_samples():
    assert get_province("PHNOM_PENH").name_kh == "ភ្នំពេញ"
    assert get_province("SIEM_REAP").name_en == "Siem Reap"
    assert get_province("SIEM_REAP").name_kh == "សៀមរាប"
    assert get_province("TBONG_KHMUM").name_kh == "ត្បូងឃ្មុំ"


def test_unknown_province_code():
    assert get_province("MARS") is None
    assert "MARS" not in PROVINCE_CODES


def test_role_codes_in_seed_order():
    assert [role.value for role in RoleCode] == [
        "ADMIN",
        "ROOM_OWNER",
        "STAFF",
        "PITIKA",
        "IT_LEAD",
        "IT_STAFF",
    ]


def test_seed_roles_file_matches_role_codes():
    roles = json.loads((ROOT / "scripts" / "seed_roles.json").read_text(encoding="utf-8"))
    assert [role["code"] for role in roles] == [code.value for code in RoleCode]
    assert [role["name_en"] for role in roles] == [
        "Admin",
        "Room owner",
        "Staff",
        "Pitika",
        "IT Lead",
        "IT Staff",
    ]
    # Khmer names are not decided yet: name_kh repeats name_en until the client sends them.
    assert all(role["name_kh"] == role["name_en"] for role in roles)
