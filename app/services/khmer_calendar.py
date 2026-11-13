"""The Khmer lunar date (ចន្ទគតិ) for the request slip: "ថ្ងៃចន្ទ ៣កើត ខែភទ្របទ ឆ្នាំមមី អដ្ឋស័ក ព.ស.២៥៧០".

A port of the Gregorian → lunar part of momentkh 3.0.3 (https://github.com/ThyrithSor/momentkh),
which carries this notice:

    MIT License. Copyright (c) ThyrithSor.
    Permission is hereby granted, free of charge, to any person obtaining a copy of this software
    and associated documentation files (the "Software"), to deal in the Software without
    restriction ... The above copyright notice and this permission notice shall be included in all
    copies or substantial portions of the Software. THE SOFTWARE IS PROVIDED "AS IS", WITHOUT
    WARRANTY OF ANY KIND.

The steps follow the library one for one (same names, same rounding), so a difference can be
traced. tests/fixtures/khmer_lunar_2026_2027.json holds the library's answer for every day of
2026 and 2027 (scripts/make_lunar_fixture.cjs); the tests compare all of them. A date is taken at
00:00 local time, as the library does with no hour given.
"""

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from functools import cache

from app.services.khmer_text import khmer_digits

MONTH_NAMES = (
    "មិគសិរ",
    "បុស្ស",
    "មាឃ",
    "ផល្គុន",
    "ចេត្រ",
    "ពិសាខ",
    "ជេស្ឋ",
    "អាសាឍ",
    "ស្រាពណ៍",
    "ភទ្របទ",
    "អស្សុជ",
    "កត្ដិក",
    "បឋមាសាឍ",
    "ទុតិយាសាឍ",
)
ANIMAL_NAMES = ("ជូត", "ឆ្លូវ", "ខាល", "ថោះ", "រោង", "ម្សាញ់", "មមី", "មមែ", "វក", "រកា", "ច", "កុរ")
SAK_NAMES = (
    "សំរឹទ្ធិស័ក",
    "ឯកស័ក",
    "ទោស័ក",
    "ត្រីស័ក",
    "ចត្វាស័ក",
    "បញ្ចស័ក",
    "ឆស័ក",
    "សប្តស័ក",
    "អដ្ឋស័ក",
    "នព្វស័ក",
)
WEEKDAY_NAMES = ("អាទិត្យ", "ចន្ទ", "អង្គារ", "ពុធ", "ព្រហស្បតិ៍", "សុក្រ", "សៅរ៍")  # Sunday first
PHASE_NAMES = ("កើត", "រោច")

CHEIT, PISAKH, JESTH, SRAP, KADEUK, PATHAMASADH, TUTIYASADH = 4, 5, 6, 8, 11, 12, 13

# The library's fixed New Year moments for some years (day, month, year, hour, minute).
_NEW_YEAR_MOMENTS = {
    1879: (12, 4, 1879, 11, 36),
    1897: (13, 4, 1897, 2, 0),
    2011: (14, 4, 2011, 13, 12),
    2012: (14, 4, 2012, 19, 11),
    2013: (14, 4, 2013, 2, 12),
    2014: (14, 4, 2014, 8, 7),
    2015: (14, 4, 2015, 14, 2),
    2024: (13, 4, 2024, 22, 17),
}


@dataclass(frozen=True)
class LunarDate:
    weekday: str
    day: int  # 1-15
    phase: str  # កើត / រោច
    month: str
    animal: str
    sak: str
    be_year: int


# --- Julian day numbers ---------------------------------------------------------------


def _jdn(year: int, month: int, day: int) -> int:
    a = (14 - month) // 12
    y = year + 4800 - a
    m = month + 12 * a - 3
    return day + (153 * m + 2) // 5 + 365 * y + y // 4 - y // 100 + y // 400 - 32045


def _from_jdn(jdn: int) -> tuple[int, int, int]:
    a = jdn + 32044
    b = (4 * a + 3) // 146097
    c = a - (146097 * b) // 4
    d = (4 * c + 3) // 1461
    e = c - (1461 * d) // 4
    m = (5 * e + 2) // 153
    day = e - (153 * m + 2) // 5 + 1
    month = m + 3 - 12 * (m // 10)
    year = 100 * b + d - 4800 + m // 10
    return year, month, day


# --- Year rules (Buddhist era) ---------------------------------------------------------


def _aharkun(be: int) -> int:
    return (be * 292207 + 499) // 800 + 4


def _kromthupul(be: int) -> int:
    return 800 - (be * 292207 + 499) % 800


def _avoman(be: int) -> int:
    return (_aharkun(be) * 11 + 25) % 692


def _bodithey(be: int) -> int:
    aharkun = _aharkun(be)
    return ((aharkun * 11 + 25) // 692 + aharkun + 29) % 30


def _leap_day_by_calculation(be: int) -> bool:
    avoman = _avoman(be)
    if avoman == 0 and _avoman(be - 1) == 137:
        return True
    if _kromthupul(be) <= 207:
        return avoman < 127
    if avoman == 137 and _avoman(be + 1) == 0:
        return False
    return avoman < 138


def _leap_month(be: int) -> bool:
    bodithey, following = _bodithey(be), _bodithey(be + 1)
    if bodithey == 25 and following == 5:
        return False
    return (bodithey == 24 and following == 6) or bodithey >= 25 or bodithey < 6


@cache
def _leap_type(be: int) -> int:
    """1: a leap month (អធិកមាស); 2: a leap day (ចន្ទ្រាធិមាស); 0: neither."""
    if _leap_month(be):
        return 1
    if _leap_day_by_calculation(be):
        return 2
    if _leap_month(be - 1):
        year = be - 1
        while True:
            if _leap_day_by_calculation(year):
                return 2
            year -= 1
            if not _leap_month(year):
                return 0
    return 0


def _days_in_month(month: int, be: int) -> int:
    leap = _leap_type(be)
    if month == JESTH and leap == 2:
        return 30
    if month in (PATHAMASADH, TUTIYASADH):
        return 30 if leap == 1 else 0
    return 29 if month % 2 == 0 else 30


def _days_in_year(be: int) -> int:
    return {1: 384, 2: 355}.get(_leap_type(be), 354)


def _next_month(month: int, be: int) -> int:
    if month == JESTH and _leap_type(be) == 1:
        return PATHAMASADH
    if month == KADEUK:
        return 0
    if month == PATHAMASADH:
        return TUTIYASADH
    if month == TUTIYASADH:
        return SRAP
    return month + 1


def _maybe_be(year: int, month: int) -> int:
    return year + 543 if month <= 4 else year + 544


# --- New Year (Jolak Sakaraj year rules) -----------------------------------------------


def _aharkun_js(js: int) -> int:
    return (js * 292207 + 373) // 800 + 1


def _avoman_js(js: int) -> int:
    return (_aharkun_js(js) * 11 + 650) % 692


def _kromthupul_js(js: int) -> int:
    return 800 - (292207 * js + 373) % 800


def _bodithey_js(js: int) -> int:
    aharkun = _aharkun_js(js)
    return (aharkun + (11 * aharkun + 650) // 692) % 30


def _adhikameas(js: int) -> bool:
    bodithey, following = _bodithey_js(js), _bodithey_js(js + 1)
    if bodithey == 24 and following == 6:
        return True
    if bodithey == 25 and following == 5:
        return False
    return bodithey > 24 or bodithey < 6


def _chantrathimeas(js: int) -> bool:
    avoman, following, previous = _avoman_js(js), _avoman_js(js + 1), _avoman_js(js - 1)
    solar_leap = _kromthupul_js(js) <= 207
    if avoman == 0 and previous == 137:
        return True
    if solar_leap:
        return avoman < 127
    if avoman == 137 and following == 0:
        return False
    if avoman < 138:
        return True
    return previous == 137 and avoman == 0


def _sun_info(js: int, sotin: int) -> tuple[int, int, int]:
    """(sun inauguration in libda, angsar, libda) for one sotin, as the library works it out."""
    r2 = 800 * sotin + _kromthupul_js(js - 1)
    reasey, r3 = r2 // 24350, r2 % 24350
    angsar, r4 = r3 // 811, r3 % 811
    libda = r4 // 14 - 3
    average = 30 * 60 * reasey + 60 * angsar + libda
    s1 = 30 * 60 * 2 + 60 * 20
    left_over = average - s1 + (30 * 60 * 12 if average < s1 else 0)
    kaen = left_over // (30 * 60)
    if kaen in (0, 1, 2):
        rs = kaen
    elif kaen in (3, 4, 5):
        rs = 30 * 60 * 6 - left_over
    elif kaen in (6, 7, 8):
        rs = left_over - 30 * 60 * 6
    elif kaen in (9, 10, 11):
        rs = 30 * 60 * 11 + 60 * 29 + 60 - left_over
    else:
        rs = -1
    last_reasey, last_angsar, last_libda = (
        _js_div(rs, 30 * 60),
        _js_div(_js_mod(rs, 30 * 60), 60),
        _js_mod(rs, 60),
    )
    if last_angsar >= 15:
        khan, pouichalip = 2 * last_reasey + 1, 60 * (last_angsar - 15) + last_libda
    else:
        khan, pouichalip = 2 * last_reasey, 60 * last_angsar + last_libda
    chhaya = [(35, 0), (32, 35), (27, 67), (22, 94), (13, 116), (5, 129)]
    multiplicity, base = chhaya[khan] if 0 <= khan <= 5 else (0, 134)
    phol = _js_div(pouichalip * multiplicity, 900) + base
    inauguration = average - phol if kaen <= 5 else average + phol
    return inauguration, _js_div(_js_mod(inauguration, 30 * 60), 60), _js_mod(inauguration, 60)


def _js_div(a: int, b: int) -> int:
    """Math.floor(a / b), as the library divides."""
    return a // b


def _js_mod(a: int, b: int) -> int:
    """JavaScript's %: the sign of `a` (Python's % takes the sign of `b`)."""
    result = abs(a) % abs(b)
    return -result if a < 0 else result


@cache
def _new_year(ce_year: int) -> tuple[datetime, datetime]:
    """(the moment of Moha Songkran, midnight of Lerng Sak) for a Gregorian year."""
    js = ce_year - 638
    sotins = [363, 364, 365, 366] if _kromthupul_js(js - 1) <= 207 else [362, 363, 364, 365]
    infos = [_sun_info(js, s) for s in sotins]
    hour = minute = 0
    for _, angsar, libda in infos:
        if angsar == 0:
            minutes = 24 * 60 - libda * 24
            hour, minute = _js_div(minutes, 60) % 24, _js_mod(minutes, 60)
            break
    bodithey = _bodithey_js(js)
    if _adhikameas(js - 1) and _chantrathimeas(js - 1):
        bodithey = (bodithey + 1) % 30
    lerng_day, lerng_month = (bodithey - 1, 4) if bodithey >= 6 else (bodithey, 5)
    new_year_days = 4 if infos[0][1] == 0 else 3
    epoch_month, epoch_day_number = _lunar_month_and_day(ce_year, 4, 17)
    diff = ((epoch_month - 4) * 29 + epoch_day_number) - ((lerng_month - 4) * 29 + lerng_day)
    new_year_jdn = _jdn(ce_year, 4, 17) - (diff + new_year_days - 1)
    if ce_year in _NEW_YEAR_MOMENTS:
        d, m, y, hour, minute = _NEW_YEAR_MOMENTS[ce_year]
        new_year_jdn = _jdn(y, m, d)
    ny, nm, nd = _from_jdn(new_year_jdn)
    ly, lm, ld = _from_jdn(new_year_jdn + new_year_days - 1)
    return datetime(ny, nm, nd, hour, minute), datetime(ly, lm, ld)


# --- Gregorian → lunar -----------------------------------------------------------------


def _lunar_month_and_day(year: int, month: int, day: int) -> tuple[int, int]:
    """(lunar month index, day number 0-29) by walking from 1 Jan 1900 = 1កើត ខែបុស្ស."""
    epoch = _jdn(1900, 1, 1)
    diff = _jdn(year, month, day) - epoch
    lunar_month = 1
    if diff > 0:
        while True:
            ey, em, _ = _from_jdn(epoch)
            days = _days_in_year(_maybe_be(ey + 1, em))
            if diff > days:
                diff -= days
                epoch += days
            else:
                break
    elif diff < 0:
        while diff < 0:
            ey, em, _ = _from_jdn(epoch)
            days = _days_in_year(_maybe_be(ey, em))
            diff += days
            epoch -= days
    while diff > 0:
        ey, em, _ = _from_jdn(epoch)
        be = _maybe_be(ey, em)
        days = _days_in_month(lunar_month, be)
        if diff > days:
            diff -= days
            epoch += days
            lunar_month = _next_month(lunar_month, be)
        else:
            break
    final_be = _maybe_be(year, month)
    total = _days_in_month(lunar_month, final_be)
    if diff >= total:
        diff %= total
        lunar_month = _next_month(lunar_month, final_be)
    return lunar_month, diff


@cache
def _visakha_bochea(year: int) -> datetime:
    """Midnight of 1រោច ខែពិសាខ, when the Buddhist year goes up."""
    for month in (4, 5, 6):
        next_first = date(year + (month == 12), month % 12 + 1, 1)
        for day in range(1, (next_first - timedelta(days=1)).day + 1):
            lunar_month, day_number = _lunar_month_and_day(year, month, day)
            if lunar_month == PISAKH and day_number == 15:
                return datetime(year, month, day)
    return datetime(year, 4, 15)


def lunar_date(day: date) -> LunarDate:
    lunar_month, day_number = _lunar_month_and_day(day.year, day.month, day.day)
    moment = datetime(day.year, day.month, day.day)
    bochea = _visakha_bochea(day.year)
    be_year = day.year + 544 if moment >= bochea else day.year + 543
    js_year = be_year - 1182
    animal = (be_year + 4) % 12
    new_year, lerng_sak = _new_year(day.year)
    if new_year <= moment <= bochea:
        animal = (animal + 1) % 12
    if lerng_sak <= moment <= bochea:
        js_year += 1
    phase = 0 if day_number < 15 else 1
    return LunarDate(
        weekday=WEEKDAY_NAMES[(day.weekday() + 1) % 7],
        day=day_number + 1 if phase == 0 else day_number - 14,
        phase=PHASE_NAMES[phase],
        month=MONTH_NAMES[lunar_month],
        animal=ANIMAL_NAMES[animal],
        sak=SAK_NAMES[js_year % 10],
        be_year=be_year,
    )


def lunar_line(day: date) -> str:
    """Like ថ្ងៃចន្ទ ៣កើត ខែភទ្របទ ឆ្នាំមមី អដ្ឋស័ក ព.ស.២៥៧០."""
    lunar = lunar_date(day)
    return (
        f"ថ្ងៃ{lunar.weekday} {khmer_digits(lunar.day)}{lunar.phase} ខែ{lunar.month} "
        f"ឆ្នាំ{lunar.animal} {lunar.sak} ព.ស.{khmer_digits(lunar.be_year)}"
    )
