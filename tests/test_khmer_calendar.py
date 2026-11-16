"""The Khmer lunar date on the request slip (a port of momentkh 3.0.3)."""

import json
from datetime import date
from pathlib import Path

import pytest

from app.services.khmer_calendar import lunar_date, lunar_line

FIXTURE = Path(__file__).parent / "fixtures" / "khmer_lunar_2026_2027.json"


def test_signed_paper_date():  # the owner's signed scan
    assert lunar_line(date(2026, 9, 14)) == "ថ្ងៃចន្ទ ៣កើត ខែភទ្របទ ឆ្នាំមមី អដ្ឋស័ក ព.ស.២៥៧០"


def test_demo_dates():
    assert lunar_line(date(2026, 9, 16)) == "ថ្ងៃពុធ ៥កើត ខែភទ្របទ ឆ្នាំមមី អដ្ឋស័ក ព.ស.២៥៧០"
    assert lunar_line(date(2026, 11, 12)) == "ថ្ងៃព្រហស្បតិ៍ ៣កើត ខែកត្ដិក ឆ្នាំមមី អដ្ឋស័ក ព.ស.២៥៧០"


@pytest.mark.parametrize(
    ("day", "month", "phase"),
    [
        (date(2026, 5, 1), "ពិសាខ", "កើត"),  # Visak Bochea
        (date(2026, 10, 11), "ភទ្របទ", "រោច"),  # Pchum Ben
        (date(2026, 11, 24), "កត្ដិក", "កើត"),  # Water Festival
    ],
)
def test_full_moons_2026(day, month, phase):
    lunar = lunar_date(day)
    assert (lunar.day, lunar.month, lunar.phase) == (15, month, phase)


def test_every_day_matches_momentkh():
    rows = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert len(rows) == 730
    wrong = [r["date"] for r in rows if lunar_line(date.fromisoformat(r["date"])) != r["line"]]
    assert wrong == []
