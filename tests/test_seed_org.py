"""scripts/seed_org.py: the organisation (offices, departments, divisions) from HR data."""

import unicodedata

import pytest
from sqlalchemy import func, select

from app.constants.provinces import PROVINCE_CODES
from app.models import Department, Division, Location
from app.services.province import get_user_province
from scripts.seed_demo import seed_demo
from scripts.seed_org import load_org, seed_org

ORG = load_org()
HEAD_DIVISIONS = sum(len(dept["divisions"]) for dept in ORG["departments"])
BRANCHES = len(ORG["branches"])
LOCATIONS = 1 + BRANCHES
DEPARTMENTS = len(ORG["departments"]) + BRANCHES
DIVISIONS = HEAD_DIVISIONS + BRANCHES * len(ORG["branch_divisions"])


def count(session, model) -> int:
    return session.scalar(select(func.count()).select_from(model))


def counts(session) -> tuple[int, int, int]:
    return count(session, Location), count(session, Department), count(session, Division)


def _key(name: str) -> str:
    """How MySQL's utf8mb4_0900_ai_ci compares names: ignoring case and accents."""
    decomposed = unicodedata.normalize("NFKD", name.casefold())
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch)).strip()


# --- The data file ---------------------------------------------------------------------


def test_data_has_the_whole_organisation():
    assert (len(ORG["departments"]), HEAD_DIVISIONS, BRANCHES) == (41, 156, 19)
    assert len(ORG["branch_divisions"]) == 4


def _all_named():
    yield ORG["head_office"], 100
    for dept in ORG["departments"]:
        yield dept, 100
        for division in dept["divisions"]:
            yield division, 100
    for division in ORG["branch_divisions"]:
        yield division, 100
    for branch in ORG["branches"]:
        yield branch, 100


@pytest.mark.parametrize("field", ["name_en", "name_kh"])
def test_names_fit_the_columns(field):
    for record, limit in _all_named():
        value = record[field]
        assert value == value.strip() and value, record
        assert len(value) <= limit, record


def test_short_names_fit():
    for record, _ in _all_named():
        assert len(record.get("short_name") or "") <= 20, record


def test_department_names_unique():
    names = [_key(dept["name_en"]) for dept in ORG["departments"]]
    assert len(names) == len(set(names))


def test_division_names_unique_in_each_department():
    for dept in ORG["departments"] + [{"name_en": "branch", "divisions": ORG["branch_divisions"]}]:
        names = [_key(division["name_en"]) for division in dept["divisions"]]
        assert len(names) == len(set(names)), dept["name_en"]


def test_branches_are_distinct_provinces():
    provinces = [branch["province"] for branch in ORG["branches"]]
    assert set(provinces) <= set(PROVINCE_CODES)
    assert len(provinces) == len(set(provinces))
    names = [_key(branch["name_en"]) for branch in ORG["branches"]] + [
        _key(ORG["head_office"]["name_en"])
    ]
    assert len(names) == len(set(names))


def test_sort_orders_in_range():
    for record, _ in _all_named():
        assert 0 <= record.get("sort_order", 0) <= 9999, record


# --- Seeding ---------------------------------------------------------------------------


def test_creates_the_organisation(db_session):
    result = seed_org(db_session)
    assert counts(db_session) == (LOCATIONS, DEPARTMENTS, DIVISIONS)
    assert (result.locations, result.departments, result.divisions) == (
        LOCATIONS,
        DEPARTMENTS,
        DIVISIONS,
    )


def test_running_twice_creates_nothing_new(db_session):
    seed_org(db_session)
    second = seed_org(db_session)
    assert (second.locations, second.departments, second.divisions) == (0, 0, 0)
    assert counts(db_session) == (LOCATIONS, DEPARTMENTS, DIVISIONS)


def test_head_office_departments_and_divisions(db_session):
    seed_org(db_session)
    head = db_session.scalars(select(Location).where(Location.name_en == "Head Office")).one()
    assert head.province == "PHNOM_PENH"
    it = db_session.scalars(
        select(Department).where(
            Department.location_id == head.id,
            Department.name_en == "Information Technology Department",
        )
    ).one()
    assert it.name_kh == "នាយកដ្ឋានព័ត៌មានវិទ្យា"
    divisions = db_session.scalars(
        select(Division).where(Division.department_id == it.id).order_by(Division.sort_order)
    ).all()
    assert [d.name_en for d in divisions][:3] == [
        "IT Administration and Operations",
        "Network Management",
        "Software Development",
    ]


def test_branches_give_users_their_province(db_session, make_user):
    seed_org(db_session)
    kampot = db_session.scalars(
        select(Division)
        .join(Department, Department.id == Division.department_id)
        .join(Location, Location.id == Department.location_id)
        .where(Location.name_en == "Kampot Branch", Division.name_en == "Operations")
    ).one()
    user = make_user(division=kampot, roles=["PITIKA"])
    assert get_user_province(user).code == "KAMPOT"


def test_works_with_the_demo_places(db_session):
    # seed_demo already has "Head Office", "Siem Reap Branch" and "Battambang Branch".
    seed_demo(db_session)
    demo_locations = count(db_session, Location)
    result = seed_org(db_session)
    assert result.locations == LOCATIONS - 3
    assert count(db_session, Location) == demo_locations + LOCATIONS - 3
    assert (result.departments, result.divisions) == (DEPARTMENTS, DIVISIONS)


def test_does_not_change_existing_records(db_session, make_location, make_department):
    head = make_location(name_en="Head Office", province="KANDAL")
    cabinet = make_department(location=head, name_en="CABINET", name_kh="Mine", sort_order=7)
    seed_org(db_session)
    db_session.refresh(head)
    db_session.refresh(cabinet)
    assert head.province == "KANDAL"
    assert (cabinet.name_en, cabinet.name_kh, cabinet.sort_order) == ("CABINET", "Mine", 7)
    assert count(db_session, Location) == LOCATIONS


def test_everything_is_active(db_session):
    seed_org(db_session)
    for model in (Location, Department, Division):
        assert set(db_session.scalars(select(model.is_active))) == {True}
