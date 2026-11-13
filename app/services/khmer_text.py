"""Khmer words for the request slip (ប័ណ្ណស្នើ): numbers, dates, times and titles.

Times read like the signed paper: "ម៉ោង ២:០០ នាទីរសៀល" (12-hour, with the part of the day).
"""

from datetime import date, time

_DIGITS = str.maketrans("0123456789", "០១២៣៤៥៦៧៨៩")

KH_MONTHS = (
    "មករា",
    "កុម្ភៈ",
    "មីនា",
    "មេសា",
    "ឧសភា",
    "មិថុនា",
    "កក្កដា",
    "សីហា",
    "កញ្ញា",
    "តុលា",
    "វិច្ឆិកា",
    "ធ្នូ",
)
# Monday first, like date.weekday().
_WEEKDAYS = ("ច័ន្ទ", "អង្គារ", "ពុធ", "ព្រហស្បតិ៍", "សុក្រ", "សៅរ៍", "អាទិត្យ")
_TITLES = {"Mr.": "លោក", "Ms.": "លោកស្រី", "Mrs.": "លោកស្រី", "Dr.": "បណ្ឌិត"}


def khmer_digits(value: int | str) -> str:
    return str(value).translate(_DIGITS)


def khmer_date(day: date) -> str:
    """Like ថ្ងៃទី១៤ ខែកញ្ញា ឆ្នាំ២០២៦."""
    return f"ថ្ងៃទី{khmer_digits(day.day)} ខែ{KH_MONTHS[day.month - 1]} ឆ្នាំ{khmer_digits(day.year)}"


def khmer_short_date(day: date) -> str:
    """Like ១៥/០៩/២០២៦, as written under a signature."""
    return khmer_digits(day.strftime("%d/%m/%Y"))


def khmer_weekday(day: date) -> str:
    return _WEEKDAYS[day.weekday()]


def _part_of_day(hour: int) -> str:
    if hour < 12:
        return "ព្រឹក"
    if hour < 13:
        return "ថ្ងៃត្រង់"
    if hour < 17:
        return "រសៀល"
    if hour < 19:
        return "ល្ងាច"
    return "យប់"


def khmer_time(t: time) -> str:
    """Like ម៉ោង ២:០០ នាទីរសៀល."""
    hour = t.hour % 12 or 12
    return f"ម៉ោង {khmer_digits(hour)}:{khmer_digits(f'{t.minute:02d}')} នាទី{_part_of_day(t.hour)}"


def khmer_title(title: str | None) -> str:
    """The word before a person's role or name: Mr. → លោក, Ms./Mrs. → លោកស្រី, Dr. → បណ្ឌិត."""
    return _TITLES.get(title or "", "")
