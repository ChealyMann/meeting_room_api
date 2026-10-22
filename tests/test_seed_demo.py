"""scripts/seed_demo.py: development demo data for places."""

from sqlalchemy import func, select

from app.models import Building, Floor, Location
from scripts.seed_demo import DEMO_PLACES, seed_demo


def count(session, model) -> int:
    return session.scalar(select(func.count()).select_from(model))


def expected_counts() -> tuple[int, int, int]:
    buildings = [b for place in DEMO_PLACES for b in place["buildings"]]
    floors = [f for b in buildings for f in b["floors"]]
    return len(DEMO_PLACES), len(buildings), len(floors)


def test_creates_offices_buildings_and_floors(db_session):
    result = seed_demo(db_session)
    assert (
        count(db_session, Location),
        count(db_session, Building),
        count(db_session, Floor),
    ) == expected_counts()
    assert (result.locations, result.buildings, result.floors) == expected_counts()


def test_running_twice_creates_nothing_new(db_session):
    seed_demo(db_session)
    second = seed_demo(db_session)
    assert (second.locations, second.buildings, second.floors) == (0, 0, 0)
    assert (
        count(db_session, Location),
        count(db_session, Building),
        count(db_session, Floor),
    ) == expected_counts()


def test_demo_data_is_linked_correctly(db_session):
    seed_demo(db_session)
    head = db_session.scalars(select(Location).where(Location.name_en == "Head Office")).one()
    assert head.province == "PHNOM_PENH"
    buildings = db_session.scalars(select(Building).where(Building.location_id == head.id)).all()
    assert {b.name_en for b in buildings} >= {"Building A", "Building B"}
    building_a = next(b for b in buildings if b.name_en == "Building A")
    labels = db_session.scalars(
        select(Floor.floor_label).where(Floor.building_id == building_a.id)
    ).all()
    assert "Ground floor" in labels


def test_has_active_and_inactive_records_to_try_filters(db_session):
    seed_demo(db_session)
    statuses = set(db_session.scalars(select(Building.is_active)))
    assert statuses == {True, False}


def test_covers_several_provinces(db_session):
    seed_demo(db_session)
    assert len(set(db_session.scalars(select(Location.province)))) >= 3


def test_does_not_change_existing_records(db_session, make_location):
    existing = make_location(name_en="Head Office", address="My own address", province="KANDAL")
    seed_demo(db_session)
    db_session.refresh(existing)
    assert (existing.address, existing.province) == ("My own address", "KANDAL")
    assert count(db_session, Location) == expected_counts()[0]


def test_keeps_names_unique_ignoring_case(db_session, make_location):
    make_location(name_en="HEAD OFFICE")
    seed_demo(db_session)  # must not fail on the case-insensitive unique key
    assert count(db_session, Location) == expected_counts()[0]
