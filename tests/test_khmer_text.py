"""Khmer words for the request slip: numbers, dates, times and titles."""

from datetime import date, time

import pytest

from app.services.khmer_text import (
    KH_MONTHS,
    khmer_date,
    khmer_digits,
    khmer_short_date,
    khmer_time,
    khmer_title,
    khmer_weekday,
)


def test_digits():
    assert khmer_digits(2026) == "២០២៦"
    assert khmer_digits("08:30") == "០៨:៣០"


def test_dates():
    assert khmer_date(date(2026, 9, 14)) == "ថ្ងៃទី១៤ ខែកញ្ញា ឆ្នាំ២០២៦"
    assert khmer_short_date(date(2026, 9, 5)) == "០៥/០៩/២០២៦"
    assert khmer_weekday(date(2026, 9, 14)) == "ចន្ទ"  # as on the signed paper
    assert KH_MONTHS[10] == "វិច្ឆិកា"


@pytest.mark.parametrize(
    ("t", "text"),
    [
        (time(8, 0), "ម៉ោង ៨:០០ នាទីព្រឹក"),
        (time(12, 30), "ម៉ោង ១២:៣០ នាទីថ្ងៃត្រង់"),
        (time(14, 0), "ម៉ោង ២:០០ នាទីរសៀល"),
        (time(17, 0), "ម៉ោង ៥:០០ នាទីល្ងាច"),
        (time(19, 30), "ម៉ោង ៧:៣០ នាទីយប់"),
    ],
)
def test_times(t, text):
    assert khmer_time(t) == text


@pytest.mark.parametrize(
    ("title", "word"),
    [("Mr.", "លោក"), ("Ms.", "លោកស្រី"), ("Mrs.", "លោកស្រី"), ("Dr.", "បណ្ឌិត"), (None, "")],
)
def test_titles(title, word):
    assert khmer_title(title) == word
