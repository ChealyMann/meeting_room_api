"""Every value on the request slip, in Khmer, built from the booking's copies."""

from dataclasses import replace
from datetime import date, datetime, time

import pytest

from app.constants.booking import BookingStatus
from app.services import booking_transitions as transitions
from app.services.request_slip_data import build_slip_data
from app.services.request_slip_docx import SMALLEST, fit_scale

SENT = datetime(2026, 9, 14, 3, 0)  # UTC: 14 Sep 2026, 10:00 in Phnom Penh
PASS_UP = "មេត្តាពិនិត្យ និងសម្រេចដោយអនុគ្រោះ។"


@pytest.fixture
def slip(frozen, db_session, settings, make_bookable_room, make_booking, maker):
    """`slip(sessions=..., **booking fields)`: a booking sent 14 Sep 2026, confirmed now (9 Nov
    2026), and its slip data."""

    def build(sessions=((date(2026, 9, 15), time(14), time(17)),), requester=None, **fields):
        room = make_bookable_room(name_kh="ស្ទឹងមង្គលបុរី")
        values = {"meeting_title": "ជាមួយគណៈកម្មការប្រព័ន្ធទូទាត់", "attendees": 30, "created_at": SENT}
        booking = make_booking(
            room,
            requester or maker,
            status=BookingStatus.PENDING_PITIKA,
            sessions=sessions,
            **{**values, **fields},
        )
        transitions.make_confirmed(db_session, booking, booking.version)
        db_session.flush()
        build.booking = booking
        return build_slip_data(db_session, settings, booking)

    return build


def test_one_afternoon_like_the_signed_paper(slip, org):
    data = slip(catering=True)
    assert data.subject == (
        "សំណើសុំរៀបចំបន្ទប់ប្រជុំ “ស្ទឹងមង្គលបុរី” សម្រាប់កិច្ចប្រជុំជាមួយគណៈកម្មការប្រព័ន្ធទូទាត់។ "
        "កិច្ចប្រជុំនឹងប្រព្រឹត្តទៅនៅថ្ងៃទី១៥ ខែកញ្ញា ឆ្នាំ២០២៦ វេលាម៉ោង ២:០០ នាទីរសៀល ដល់ម៉ោង ៥:០០ នាទីល្ងាច។ "
        "សមាជិកចូលរួមចំនួន ៣០ រូប។"
    )
    assert (data.timetable, data.people_line) == ([], None)
    assert data.requests == ["- នំ ផ្លែឈើ និងភេសជ្ជៈ។"]
    assert data.director_title == "លោក"
    assert data.department_line == "លោកប្រធាននាយកដ្ឋានប្រព័ន្ធទូទាត់"
    assert data.office_line == "លោកស្រីប្រធានការិយាល័យគោលនយោបាយ"
    assert data.closing == [
        f"អាស្រ័យដូចបានជម្រាបជូនខាងលើ សូម លោកនាយកខុទ្ទកាល័យ {PASS_UP}",
        "សូម លោកនាយកខុទ្ទកាល័យ មេត្តាទទួលនូវការគោរពដ៏ខ្ពង់ខ្ពស់អំពីយើងខ្ញុំ។",
    ]


def test_dates_come_from_the_day_it_was_sent(slip):
    data = slip()
    assert data.lunar_line == "ថ្ងៃចន្ទ ៣កើត ខែភទ្របទ ឆ្នាំមមី អដ្ឋស័ក ព.ស.២៥៧០"
    assert data.city_date == "រាជធានីភ្នំពេញ ថ្ងៃទី១៤ ខែកញ្ញា ឆ្នាំ២០២៦"


def test_opinion_boxes_are_signed_on_the_confirm_day(slip, org):
    data = slip()
    office, department, director = data.office_head, data.department_head, data.director
    # Both heads write the same three lines, as on the paper (owner, 13 Nov 2026).
    assert office.comment.split("\n") == [
        "សូមគោរពជូន",
        "លោកប្រធាននាយកដ្ឋាន មេត្តាពិនិត្យ",
        "និងសម្រេចដោយអនុគ្រោះ។",
    ]
    assert department.comment.split("\n") == [
        "សូមគោរពជូន",
        "លោកនាយកខុទ្ទកាល័យ មេត្តាពិនិត្យ",
        "និងសម្រេចដោយអនុគ្រោះ។",
    ]
    assert director.comment == "ឯកភាពតាមសំណើ។"
    assert (office.title, office.name) == ("លោកស្រី", "ហេង សុខលីណា")
    assert (department.title, department.name) == ("លោក", "ចាន់ សុភក្ត្រ")
    assert (director.title, director.name) == ("លោក", "ពេជ្រ វិសាល")
    assert office.date == department.date == director.date == "០៩/១១/២០២៦"
    assert (data.department_head_title, data.office_head_title) == ("លោក", "លោកស្រី")


def test_maker_is_the_booker(slip):
    data = slip()
    assert (data.maker.name, data.maker.comment, data.maker.date) == ("សុខ ដារ៉ា", None, None)


def test_several_days_at_one_time(slip):
    days = tuple((date(2026, 11, d), time(8), time(12)) for d in (23, 24, 25))
    assert (
        "កិច្ចប្រជុំនឹងប្រព្រឹត្តទៅរយៈពេល ៣ថ្ងៃ ចាប់ពីថ្ងៃទី២៣ ដល់ថ្ងៃទី២៥ ខែវិច្ឆិកា ឆ្នាំ២០២៦ "
        "វេលាម៉ោង ៨:០០ នាទីព្រឹក ដល់ម៉ោង ១២:០០ នាទីថ្ងៃត្រង់។ សមាជិកចូលរួមចំនួន ៣០ រូប។"
    ) in slip(sessions=days).subject


def test_a_range_over_two_months_names_both(slip):
    days = ((date(2026, 11, 30), time(8), time(12)), (date(2026, 12, 1), time(8), time(12)))
    assert "ចាប់ពីថ្ងៃទី៣០ ខែវិច្ឆិកា ឆ្នាំ២០២៦ ដល់ថ្ងៃទី១ ខែធ្នូ ឆ្នាំ២០២៦ វេលា" in slip(sessions=days).subject


def test_different_times_make_a_timetable(slip):
    days = (
        (date(2026, 11, 16), time(12, 30), time(18)),
        (date(2026, 11, 13), time(12, 30), time(18)),
        (date(2026, 11, 17), time(7, 30), time(18)),
    )
    data = slip(sessions=days)
    assert data.subject.endswith("កិច្ចប្រជុំនឹងប្រព្រឹត្តទៅរយៈពេល ៣ថ្ងៃ តាមកាលវិភាគខាងក្រោម៖")
    assert data.timetable == [
        ("១", "ថ្ងៃសុក្រ ថ្ងៃទី១៣ ខែវិច្ឆិកា ឆ្នាំ២០២៦", "១២:៣០ ថ្ងៃត្រង់ – ៦:០០ ល្ងាច"),
        ("២", "ថ្ងៃចន្ទ ថ្ងៃទី១៦ ខែវិច្ឆិកា ឆ្នាំ២០២៦", "១២:៣០ ថ្ងៃត្រង់ – ៦:០០ ល្ងាច"),
        ("៣", "ថ្ងៃអង្គារ ថ្ងៃទី១៧ ខែវិច្ឆិកា ឆ្នាំ២០២៦", "៧:៣០ ព្រឹក – ៦:០០ ល្ងាច"),
    ]
    assert data.people_line == "សមាជិកចូលរួមចំនួន ៣០ រូប។"


@pytest.mark.parametrize(
    ("asked", "lines"),
    [
        ({}, ["- មិនមាន។"]),
        ({"it": True}, ["- អ្នកបច្ចេកទេស IT និងឧបករណ៍ IT។"]),
        ({"catering": True, "it": True}, ["- នំ ផ្លែឈើ និងភេសជ្ជៈ។", "- អ្នកបច្ចេកទេស IT និងឧបករណ៍ IT។"]),
    ],
)
def test_requests_list_only_what_was_asked(slip, asked, lines):
    assert slip(**asked).requests == lines


def test_signature_files(slip, settings, org):
    """A file that exists is used; one that is gone is skipped (no picture, no crash)."""
    file = settings.signature_dir / "users/2/office.png"
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_bytes(b"png")
    data = slip()
    assert data.office_head.signature == file.resolve()
    assert data.department_head.signature is None  # users/1/dept.png was never written
    assert data.maker.signature is None


def _png(settings, stored: str):
    file = settings.signature_dir / stored
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_bytes(b"png")
    return file.resolve()


def test_an_empty_signature_is_filled_with_the_new_one(slip, db_session, settings, maker, org):
    """Fill empty ones only (owner, 13 Nov 2026): who had no signature at confirm time gets the
    one they upload later; a signature kept at confirm time never changes."""
    office_then = _png(settings, "users/2/office.png")
    org["dept_head"].user_signature = None
    maker.user_signature = None
    db_session.flush()
    slip()

    org["dept_head"].user_signature = "users/1/new.png"
    maker.user_signature = "users/9/new.png"
    org["office_head"].user_signature = "users/2/new.png"
    new = {k: _png(settings, f"users/{k}/new.png") for k in (1, 2, 9)}
    db_session.flush()
    data = build_slip_data(db_session, settings, slip.booking)
    assert data.department_head.signature == new[1]  # was empty: filled
    assert data.maker.signature == new[9]  # was empty: filled
    assert data.office_head.signature == office_then  # was kept: stays


def test_slip_reads_only_copies(slip, db_session, settings, make_user, org):
    slip()
    org["department"].name_kh = "នាយកដ្ឋានថ្មី"
    org["division"].head_user_id = make_user(name_kh="អ្នកថ្មី").id
    org["office_head"].title = "Mr."
    db_session.flush()
    data = build_slip_data(db_session, settings, slip.booking)
    assert data.department_line == "លោកប្រធាននាយកដ្ឋានប្រព័ន្ធទូទាត់"
    assert (data.office_head.name, data.office_head.title) == ("ហេង សុខលីណា", "លោកស្រី")


def test_booker_without_division(slip, make_user, org):
    data = slip(requester=make_user(name_kh="គ្មានការិយាល័យ"))
    assert data.department_line == "ប្រធាននាយកដ្ឋាន ...................."
    assert data.office_line == "ប្រធានការិយាល័យ ...................."
    assert (data.office_head, data.department_head) == (None, None)
    assert data.director is not None


def test_old_booking_without_copies(db_session, settings, make_bookable_room, make_booking, maker):
    """Confirmed before the slip existed: no signer rows. Boxes empty; the booker's signature
    and office come from their profile now."""
    file = settings.signature_dir / "users/9/me.png"
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_bytes(b"png")
    booking = make_booking(make_bookable_room(), maker, status=BookingStatus.CONFIRMED)
    booking.requester_info = {"name_en": "Sok Dara", "name_kh": "សុខ ដារ៉ា"}
    db_session.flush()
    data = build_slip_data(db_session, settings, booking)
    assert (data.office_head, data.department_head, data.director) == (None, None, None)
    assert data.maker.signature == file.resolve()
    assert data.office_line == "ប្រធានការិយាល័យគោលនយោបាយ"
    assert data.director_title == "លោក"


def test_timetable_has_a_short_form_for_long_bookings(slip):
    """Many sessions print two to a row on the slip: the short weekday, the date in numbers,
    24-hour times."""
    days = (
        (date(2026, 11, 13), time(12, 30), time(18)),
        (date(2026, 11, 17), time(7, 30), time(18)),
    )
    assert slip(sessions=days).timetable_short == [
        ("១", "សុ ១៣/១១/២០២៦", "១២:៣០–១៨:០០"),
        ("២", "អ ១៧/១១/២០២៦", "០៧:៣០–១៨:០០"),
    ]


def test_no_timetable_no_short_form(slip):
    assert slip().timetable_short == []


def test_a_short_slip_stays_near_full_size(slip):
    assert 0.9 <= fit_scale(slip(catering=True, it=True)) <= 1.0


def test_a_long_slip_shrinks_but_never_below_the_smallest(slip):
    days = tuple(
        (date(2026, 11, 2 + n), time(8 + n % 2 * 5), time(11 + n % 2 * 5)) for n in range(20)
    )
    data = slip(sessions=days, meeting_title="ក" * 200)
    assert SMALLEST < fit_scale(data) < 0.8
    assert fit_scale(replace(data, requests=["- ក"] * 100)) == SMALLEST
