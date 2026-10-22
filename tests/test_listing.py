"""List helpers (spec section 4): paging, search, default order, id lists, is_active filter."""

import pytest
from sqlalchemy import select

from app.errors import AppError
from app.models import Building, Equipment, Location
from app.services.listing import (
    apply_active_filter,
    apply_default_order,
    apply_search,
    paginate,
    parse_ids,
)


@pytest.fixture
def locations(make_location):
    return [
        make_location(name_en="Alpha Office", name_kh="អាល់ហ្វា", address="Street 1"),
        make_location(name_en="Beta Office", name_kh="បេតា", address="50% Road"),
        make_location(name_en="Gamma_Branch", name_kh="ហ្គាម៉ា", address=None),
        make_location(name_en="Delta Office", name_kh="ដែលតា", address="Back\\slash Ave"),
        make_location(name_en="Epsilon Office", name_kh="អេបស៊ីឡុង", is_active=False),
    ]


def _names(session, query) -> list[str]:
    return [location.name_en for location in session.scalars(query)]


def _ordered():
    return select(Location).order_by(Location.name_en)


# --- paginate --------------------------------------------------------------------------


def test_paginate_first_page(db_session, locations):
    page = paginate(db_session, _ordered(), page=1, size=2)
    assert [item.name_en for item in page["items"]] == ["Alpha Office", "Beta Office"]
    assert (page["page"], page["size"], page["total"]) == (1, 2, 5)


def test_paginate_last_partial_page(db_session, locations):
    page = paginate(db_session, _ordered(), page=3, size=2)
    assert [item.name_en for item in page["items"]] == ["Gamma_Branch"]
    assert page["total"] == 5


def test_paginate_past_the_end(db_session, locations):
    page = paginate(db_session, _ordered(), page=9, size=20)
    assert page["items"] == []
    assert page["total"] == 5


def test_paginate_total_counts_filtered_rows(db_session, locations):
    query = _ordered().where(Location.is_active.is_(True))
    assert paginate(db_session, query, page=1, size=20)["total"] == 4


# --- apply_search ----------------------------------------------------------------------

COLUMNS = [Location.name_en, Location.name_kh, Location.address]


def test_search_matches_any_listed_column(db_session, locations):
    assert _names(db_session, apply_search(_ordered(), "office", COLUMNS)) == [
        "Alpha Office",
        "Beta Office",
        "Delta Office",
        "Epsilon Office",
    ]
    assert _names(db_session, apply_search(_ordered(), "បេតា", COLUMNS)) == ["Beta Office"]
    assert _names(db_session, apply_search(_ordered(), "street", COLUMNS)) == ["Alpha Office"]


def test_search_is_trimmed(db_session, locations):
    assert _names(db_session, apply_search(_ordered(), "  beta  ", COLUMNS)) == ["Beta Office"]


@pytest.mark.parametrize("term", [None, "", "   "])
def test_empty_search_is_no_filter(db_session, locations, term):
    assert len(_names(db_session, apply_search(_ordered(), term, COLUMNS))) == 5


def test_percent_matches_literally(db_session, locations):
    assert _names(db_session, apply_search(_ordered(), "50%", COLUMNS)) == ["Beta Office"]
    assert _names(db_session, apply_search(_ordered(), "%", COLUMNS)) == ["Beta Office"]


def test_underscore_matches_literally(db_session, locations):
    assert _names(db_session, apply_search(_ordered(), "a_b", COLUMNS)) == ["Gamma_Branch"]
    assert _names(db_session, apply_search(_ordered(), "_", COLUMNS)) == ["Gamma_Branch"]


def test_backslash_matches_literally(db_session, locations):
    assert _names(db_session, apply_search(_ordered(), "k\\s", COLUMNS)) == ["Delta Office"]


# --- default order ---------------------------------------------------------------------


def test_default_order_sort_order_then_name_then_id(db_session, make_location, make_building):
    location = make_location()
    c = make_building(location=location, name_en="C", sort_order=1)
    b = make_building(location=location, name_en="B", sort_order=2)
    a = make_building(location=location, name_en="A", sort_order=2)
    z = make_building(location=location, name_en="Z", sort_order=0)
    query = apply_default_order(
        select(Building).where(Building.location_id == location.id), Building
    )
    assert [row.id for row in db_session.scalars(query)] == [z.id, c.id, a.id, b.id]


def test_default_order_without_sort_order(db_session, locations):
    query = apply_default_order(select(Location), Location)
    assert _names(db_session, query) == sorted(location.name_en for location in locations)


def test_default_order_for_single_language_name(db_session, make_equipment):
    projector = make_equipment(name="Projector", sort_order=1)
    board = make_equipment(name="Whiteboard", sort_order=0)
    tv = make_equipment(name="TV", sort_order=1)
    query = apply_default_order(select(Equipment), Equipment)
    ids = [e.id for e in db_session.scalars(query) if e.id in {projector.id, board.id, tv.id}]
    assert ids == [board.id, projector.id, tv.id]


# --- is_active filter ------------------------------------------------------------------


def test_active_filter(db_session, locations):
    assert len(_names(db_session, apply_active_filter(_ordered(), Location, None))) == 5
    assert len(_names(db_session, apply_active_filter(_ordered(), Location, True))) == 4
    assert _names(db_session, apply_active_filter(_ordered(), Location, False)) == [
        "Epsilon Office"
    ]


# --- parse_ids -------------------------------------------------------------------------


def test_parse_ids():
    assert parse_ids("1,4,7", "equipment_ids") == [1, 4, 7]
    assert parse_ids(" 1 , 4 ", "equipment_ids") == [1, 4]
    assert parse_ids("4,1,4", "equipment_ids") == [4, 1]


@pytest.mark.parametrize("raw", [None, "", "  "])
def test_parse_ids_empty(raw):
    assert parse_ids(raw, "equipment_ids") is None


@pytest.mark.parametrize("raw", ["1,x", "1,,2", "0", "-1", "1.5", "１"])
def test_parse_ids_refuses_non_ids(raw):
    with pytest.raises(AppError) as exc_info:
        parse_ids(raw, "equipment_ids")
    error = exc_info.value
    assert (error.status, error.code) == (422, "VALIDATION_ERROR")
    assert list(error.fields) == ["equipment_ids"]
