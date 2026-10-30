"""Create the organisation from scripts/seed_org.json: offices (locations), departments
and divisions of the National Bank of Cambodia.

- Head Office (Phnom Penh) with its departments and their divisions (HR "offices").
- Each branch in the file as its own office, with one department holding the 4 divisions
  all branches share. Users in those divisions get the branch's province. The file now holds
  only the Phnom Penh Branch (owner decision, 30 Oct 2026).

Safe to run many times: it adds what is missing (matched by English name within the same
parent, ignoring case) and never changes or turns off anything that exists. Run it by hand,
after `python -m scripts.seed`:

    python -m scripts.seed_org

The English names of divisions are draft translations; see `_about` in the JSON file.
"""

import json
import sys
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.constants.provinces import PROVINCE_CODES
from app.db import create_db_engine
from app.models import Department, Division, Location

ORG_FILE = Path(__file__).with_name("seed_org.json")


@dataclass
class OrgResult:
    locations: int = 0
    departments: int = 0
    divisions: int = 0


def load_org() -> dict:
    org = json.loads(ORG_FILE.read_text(encoding="utf-8"))
    provinces = [org["head_office"]["province"]] + [b["province"] for b in org["branches"]]
    unknown = sorted(set(provinces) - set(PROVINCE_CODES))
    if unknown:
        raise ValueError(f"{ORG_FILE.name}: unknown province codes {unknown}.")
    return org


def _get_or_add(session: Session, model, lookup: dict, values: dict):
    """The record matching `lookup` (case-insensitive, by collation), else a new one."""
    record = session.scalars(select(model).filter_by(**lookup)).first()
    if record is not None:
        return record, False
    record = model(**lookup, **values)
    session.add(record)
    session.flush()
    return record, True


def _add_location(session: Session, result: OrgResult, office: dict) -> Location:
    location, created = _get_or_add(
        session,
        Location,
        {"name_en": office["name_en"]},
        {"name_kh": office["name_kh"], "province": office["province"]},
    )
    result.locations += created
    return location


def _add_department(
    session: Session, result: OrgResult, location: Location, dept: dict, divisions: list[dict]
) -> None:
    department, created = _get_or_add(
        session,
        Department,
        {"location_id": location.id, "name_en": dept["name_en"]},
        {"name_kh": dept["name_kh"], "sort_order": dept.get("sort_order", 0)},
    )
    result.departments += created
    for item in divisions:
        _, created = _get_or_add(
            session,
            Division,
            {"department_id": department.id, "name_en": item["name_en"]},
            {
                "name_kh": item["name_kh"],
                "short_name": item.get("short_name"),
                "sort_order": item.get("sort_order", 0),
            },
        )
        result.divisions += created


def seed_org(session: Session, org: dict | None = None) -> OrgResult:
    """Insert the missing parts of the organisation. Flushes; the caller commits."""
    org = org or load_org()
    result = OrgResult()
    head_office = _add_location(session, result, org["head_office"])
    for dept in org["departments"]:
        _add_department(session, result, head_office, dept, dept["divisions"])
    for branch in org["branches"]:
        location = _add_location(session, result, branch)
        _add_department(session, result, location, branch, org["branch_divisions"])
    return result


def main() -> int:
    settings = get_settings()
    engine = create_db_engine(settings.database_url)
    try:
        with Session(engine) as session:
            result = seed_org(session)
            session.commit()
    finally:
        engine.dispose()
    print(
        f"Organisation: added {result.locations} offices, {result.departments} departments, "
        f"{result.divisions} divisions (existing records were left unchanged)."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
