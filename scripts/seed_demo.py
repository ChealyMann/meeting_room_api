"""Demo data for development: offices, buildings and floors to try the API with. Only Phnom
Penh (owner decision, 30 Oct 2026).

NOT for production. Run it by hand on a dev database, after `python -m scripts.seed`:

    python -m scripts.seed_demo

Safe to run many times: it adds what is missing (matched by name, ignoring case) and never
changes or turns off anything that exists. Rooms, equipment and users come in later tasks.
"""

import sys
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import create_db_engine
from app.models import Building, Floor, Location

# Each office has buildings; each building has floors (label, sort order).
DEMO_PLACES = [
    {
        "name_en": "Head Office",
        "name_kh": "ការិយាល័យកណ្ដាល",
        "province": "PHNOM_PENH",
        "address": "No. 12, Street 214, Phnom Penh",
        "map_query": "11.5564,104.9282",
        "description": "Main office in Phnom Penh",
        "buildings": [
            {
                "name_en": "Building A",
                "name_kh": "អគារ A",
                "short_name": "A",
                "sort_order": 1,
                "floors": [
                    ("Ground floor", 0),
                    ("1st floor", 1),
                    ("2nd floor", 2),
                    ("3rd floor", 3),
                ],
            },
            {
                "name_en": "Building B",
                "name_kh": "អគារ B",
                "short_name": "B",
                "sort_order": 2,
                "floors": [("Ground floor", 0), ("1st floor", 1)],
            },
            {
                # Inactive, to try `?is_active=false` and the "not bookable" rule later.
                "name_en": "Old Annex",
                "name_kh": "អគារចាស់",
                "short_name": "OLD",
                "sort_order": 9,
                "is_active": False,
                "floors": [("Ground floor", 0)],
            },
        ],
    },
    {
        "name_en": "Phnom Penh Branch",
        "name_kh": "សាខាធនាគារជាតិនៃកម្ពុជា រាជធានីភ្នំពេញ",
        "province": "PHNOM_PENH",
        "address": "Phnom Penh",
        "map_query": "11.5564,104.9282",
        "buildings": [
            {
                "name_en": "Main Building",
                "name_kh": "អគារធំ",
                "short_name": "M",
                "sort_order": 1,
                "floors": [("Ground floor", 0), ("1st floor", 1)],
            },
        ],
    },
]


@dataclass
class DemoResult:
    locations: int = 0
    buildings: int = 0
    floors: int = 0


def _get_or_add(session: Session, model, lookup: dict, values: dict):
    """The record matching `lookup` (case-insensitive, by collation), else a new one."""
    record = session.scalars(select(model).filter_by(**lookup)).first()
    if record is not None:
        return record, False
    record = model(**lookup, **values)
    session.add(record)
    session.flush()
    return record, True


def seed_demo(session: Session) -> DemoResult:
    """Insert the missing demo places. Flushes; the caller commits."""
    result = DemoResult()
    for place in DEMO_PLACES:
        place = dict(place)
        buildings = place.pop("buildings")
        location, created = _get_or_add(session, Location, {"name_en": place.pop("name_en")}, place)
        result.locations += created
        for spec in buildings:
            spec = dict(spec)
            floors = spec.pop("floors")
            building, created = _get_or_add(
                session,
                Building,
                {"location_id": location.id, "name_en": spec.pop("name_en")},
                spec,
            )
            result.buildings += created
            for label, sort_order in floors:
                _, created = _get_or_add(
                    session,
                    Floor,
                    {"building_id": building.id, "floor_label": label},
                    {"sort_order": sort_order},
                )
                result.floors += created
    return result


def main() -> int:
    settings = get_settings()
    engine = create_db_engine(settings.database_url)
    try:
        with Session(engine) as session:
            result = seed_demo(session)
            session.commit()
    finally:
        engine.dispose()
    print(
        f"Demo data: added {result.locations} offices, {result.buildings} buildings, "
        f"{result.floors} floors (existing records were left unchanged)."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
