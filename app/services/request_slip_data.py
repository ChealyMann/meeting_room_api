"""Every value on the request slip (ប័ណ្ណស្នើ), in Khmer, for one confirmed booking.

It reads the booking's copies only (the snapshot rule): the booker's office names kept when the
booking was sent (`requester_info`), and the signers kept when it was confirmed
(`booking_signers`). People moving, offices renamed, heads or signatures changed later do not
change a slip. A booking from before the copies existed falls back to the booker's profile now
and gets empty opinion boxes.

Wording follows the owner's signed paper (13 Nov 2026); see docs/superpowers/plans/
2026-11-13-request-slip.md, "Owner decisions".
"""

from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.constants.booking import SignerRole
from app.models import Booking, BookingSigner
from app.services.clock import LOCAL_OFFSET
from app.services.khmer_calendar import lunar_line
from app.services.khmer_text import (
    khmer_date,
    khmer_digits,
    khmer_short_date,
    khmer_time,
    khmer_title,
    khmer_weekday,
)
from app.services.slip_settings import get_slip_settings

DOTS = "...................."
PASS_UP = "មេត្តាពិនិត្យ និងសម្រេចដោយអនុគ្រោះ។"
DIRECTOR = "នាយកខុទ្ទកាល័យ"
FOOD_LINE = "- នំ ផ្លែឈើ និងភេសជ្ជៈ។"
IT_LINE = "- អ្នកបច្ចេកទេស IT និងឧបករណ៍ IT។"
NOTHING_LINE = "- មិនមាន។"


@dataclass(frozen=True)
class SlipSigner:
    """The booker (comment and date None) or one signed opinion box."""

    comment: str | None
    name: str
    title: str  # លោក / លោកស្រី / បណ្ឌិត / ""
    signature: Path | None  # a PNG that exists, or None
    date: str | None  # "១៥/០៩/២០២៦"


@dataclass(frozen=True)
class SlipData:
    director_title: str
    department_head_title: str
    office_head_title: str
    department_line: str  # "លោកប្រធាននាយកដ្ឋាន…"; dots when the booker has none
    office_line: str
    subject: str  # the whole sentence; ends with the people when there is no timetable
    timetable: list[tuple[str, str, str]]  # (ល.រ, កាលបរិច្ឆេទ, វេលាម៉ោង); only when times differ
    people_line: str | None  # only with a timetable
    requests: list[str]
    closing: list[str]
    lunar_line: str
    city_date: str
    address: str
    maker: SlipSigner
    director: SlipSigner | None
    department_head: SlipSigner | None
    office_head: SlipSigner | None


def _local_day(utc: datetime) -> date:
    return (utc + LOCAL_OFFSET).date()


def _signature_file(settings: Settings, stored: str | None) -> Path | None:
    """The file behind a stored path, when it is inside SIGNATURE_DIR and still there."""
    if not stored:
        return None
    root = settings.signature_dir.resolve()
    path = (root / stored).resolve()
    return path if path.is_relative_to(root) and path.is_file() else None


def _short_time(value) -> str:
    """A time in a timetable cell, like ១២:៣០ ថ្ងៃត្រង់."""
    return khmer_time(value).removeprefix("ម៉ោង ").replace(" នាទី", " ")


def _when(sessions: list) -> tuple[str, list[tuple[str, str, str]]]:
    """The sentence saying when the meeting is, and the timetable rows if it needs them."""
    first, last = sessions[0], sessions[-1]
    time_words = f"វេលា{khmer_time(first.start_time)} ដល់{khmer_time(first.end_time)}"
    if len(sessions) == 1:
        return f"កិច្ចប្រជុំនឹងប្រព្រឹត្តទៅនៅ{khmer_date(first.date)} {time_words}។", []
    days = khmer_digits(len({s.date for s in sessions}))
    one_time = all(
        (s.start_time, s.end_time) == (first.start_time, first.end_time) for s in sessions
    )
    if one_time and len({s.date for s in sessions}) == len(sessions):
        same_month = (first.date.year, first.date.month) == (last.date.year, last.date.month)
        start = f"ថ្ងៃទី{khmer_digits(first.date.day)}" if same_month else khmer_date(first.date)
        span = f"ចាប់ពី{start} ដល់{khmer_date(last.date)}"
        return f"កិច្ចប្រជុំនឹងប្រព្រឹត្តទៅរយៈពេល {days}ថ្ងៃ {span} {time_words}។", []
    rows = [
        (
            khmer_digits(number),
            f"ថ្ងៃ{khmer_weekday(s.date)} {khmer_date(s.date)}",
            f"{_short_time(s.start_time)} – {_short_time(s.end_time)}",
        )
        for number, s in enumerate(sessions, start=1)
    ]
    return f"កិច្ចប្រជុំនឹងប្រព្រឹត្តទៅរយៈពេល {days}ថ្ងៃ តាមកាលវិភាគខាងក្រោម៖", rows


def _office_names(booking: Booking) -> tuple[str | None, str | None]:
    """(department, office) in Khmer: the copy from when it was sent, else the profile now."""
    info = booking.requester_info or {}
    if "division_kh" in info:
        return info.get("department_kh"), info.get("division_kh")
    division = booking.requester.division
    return (division.department.name_kh if division else None), (
        division.name_kh if division else None
    )


def build_slip_data(session: Session, settings: Settings, booking: Booking) -> SlipData:
    rows = session.scalars(select(BookingSigner).where(BookingSigner.booking_id == booking.id))
    signers = {row.role: row for row in rows}
    slip_settings = get_slip_settings(session)

    def title_of(role: SignerRole) -> str:
        return khmer_title(signers[role].title) if role in signers else ""

    director_title = title_of(SignerRole.DIRECTOR)
    if SignerRole.DIRECTOR not in signers:
        # Nobody signed as director: the title of the one set now, else the paper's "លោក".
        current = slip_settings.director
        director_title = (khmer_title(current.title) if current else "") or "លោក"
    department_title, office_title = (
        title_of(SignerRole.DEPARTMENT_HEAD),
        title_of(SignerRole.OFFICE_HEAD),
    )

    def box(role: SignerRole, comment: str) -> SlipSigner | None:
        row = signers.get(role)
        if row is None:
            return None
        return SlipSigner(
            comment=comment,
            name=row.name_kh,
            title=khmer_title(row.title),
            signature=_signature_file(settings, row.signature_path),
            date=khmer_short_date(_local_day(row.signed_at)),
        )

    maker_row = signers.get(SignerRole.MAKER)
    maker = SlipSigner(
        comment=None,
        name=maker_row.name_kh if maker_row else booking.requester.name_kh,
        title="",
        signature=_signature_file(
            settings,
            maker_row.signature_path if maker_row else booking.requester.user_signature,
        ),
        date=None,
    )

    department_kh, division_kh = _office_names(booking)
    sessions = sorted(booking.sessions, key=lambda s: (s.date, s.start_time))
    when, timetable = _when(sessions)
    people = f"សមាជិកចូលរួមចំនួន {khmer_digits(booking.attendees)} រូប។"
    subject = f"សំណើសុំរៀបចំបន្ទប់ប្រជុំ “{booking.room.name_kh}” សម្រាប់កិច្ចប្រជុំ{booking.meeting_title}។ {when}"
    requests = [
        line
        for line, asked in (
            (FOOD_LINE, booking.catering_order is not None),
            (IT_LINE, booking.it_ticket is not None),
        )
        if asked
    ] or [NOTHING_LINE]
    sent = _local_day(booking.created_at)
    return SlipData(
        director_title=director_title,
        department_head_title=department_title,
        office_head_title=office_title,
        department_line=f"{department_title}ប្រធាន{department_kh or 'នាយកដ្ឋាន ' + DOTS}",
        office_line=f"{office_title}ប្រធាន{division_kh or 'ការិយាល័យ ' + DOTS}",
        subject=subject if timetable else f"{subject} {people}",
        timetable=timetable,
        people_line=people if timetable else None,
        requests=requests,
        closing=[
            f"អាស្រ័យដូចបានជម្រាបជូនខាងលើ សូម {director_title}{DIRECTOR} {PASS_UP}",
            f"សូម {director_title}{DIRECTOR} មេត្តាទទួលនូវការគោរពដ៏ខ្ពង់ខ្ពស់អំពីយើងខ្ញុំ។",
        ],
        lunar_line=lunar_line(sent),
        city_date=f"រាជធានីភ្នំពេញ {khmer_date(sent)}",
        address=slip_settings.address_kh,
        maker=maker,
        director=box(SignerRole.DIRECTOR, "ឯកភាពតាមសំណើ។"),
        department_head=box(
            SignerRole.DEPARTMENT_HEAD, f"សូមគោរពជូន {director_title}{DIRECTOR} {PASS_UP}"
        ),
        office_head=box(
            SignerRole.OFFICE_HEAD, f"សូមគោរពជូន {department_title}ប្រធាននាយកដ្ឋាន {PASS_UP}"
        ),
    )
