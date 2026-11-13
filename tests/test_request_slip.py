"""GET /bookings/{id}/request-slip: the request slip (ប័ណ្ណស្នើ) as a Word file."""

import io
from datetime import date, datetime, time
from urllib.parse import quote

import pytest
from docx import Document
from PIL import Image

from app.constants.booking import BookingStatus
from app.services import booking_transitions as transitions

DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
SENT = datetime(2026, 9, 14, 3, 0)  # 14 Sep 2026, 10:00 in Phnom Penh
PAPER_LUNAR = "ថ្ងៃចន្ទ ៣កើត ខែភទ្របទ ឆ្នាំមមី អដ្ឋស័ក ព.ស.២៥៧០"


def url(booking) -> str:
    return f"/api/v1/bookings/{booking.id}/request-slip"


def _all_text(document) -> str:
    """Every text run in the body and the page footer, joined."""
    parts = [node.text or "" for node in document.element.iter() if node.tag.endswith("}t")]
    for section in document.sections:
        parts += [p.text for p in section.footer.paragraphs]
    return "".join(parts)


def _open(response):
    assert response.status_code == 200, response.text
    return Document(io.BytesIO(response.content))


def _write_png(settings, stored: str) -> None:
    path = settings.signature_dir / stored
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGBA", (300, 120), (0, 0, 0, 0)).save(path, "PNG")


@pytest.fixture
def confirmed(frozen, db_session, settings, make_bookable_room, make_booking, maker):
    """`confirmed(**booking fields)`: a booking sent 14 Sep 2026 and confirmed now."""

    def make(sessions=((date(2026, 11, 10), time(14), time(17)),), **fields):
        room = make_bookable_room(name_kh="ស្ទឹងមង្គលបុរី")
        values = {"meeting_title": "ជាមួយគណៈកម្មការប្រព័ន្ធទូទាត់", "attendees": 30, "created_at": SENT}
        booking = make_booking(
            room,
            maker,
            status=BookingStatus.PENDING_PITIKA,
            sessions=sessions,
            **{**values, **fields},
        )
        transitions.make_confirmed(db_session, booking, booking.version)
        db_session.flush()
        return booking

    return make


def test_booker_downloads_the_slip(client, auth_headers, confirmed, maker, org, settings):
    for stored in ("users/1/dept.png", "users/2/office.png", "users/3/dir.png", "users/9/me.png"):
        _write_png(settings, stored)
    booking = confirmed(catering=True)
    response = client.get(url(booking), headers=auth_headers(maker))
    assert response.headers["content-type"] == DOCX
    name = quote("ប័ណ្ណស្នើបន្ទប់ប្រជុំ_ស្ទឹងមង្គលបុរី_10_11_2026.docx")
    assert response.headers["content-disposition"] == (
        f'attachment; filename="request-slip-{booking.reference_code}.docx"; '
        f"filename*=UTF-8''{name}"
    )
    document = _open(response)
    text = _all_text(document)
    for expected in (
        "ធនាគារជាតិ នៃ កម្ពុជា",
        "ប័ណ្ណស្នើ",
        "លោកនាយកខុទ្ទកាល័យ",
        "លោកប្រធាននាយកដ្ឋានប្រព័ន្ធទូទាត់",
        "លោកស្រីប្រធានការិយាល័យគោលនយោបាយ",
        "សំណើសុំរៀបចំបន្ទប់ប្រជុំ “ស្ទឹងមង្គលបុរី” សម្រាប់កិច្ចប្រជុំជាមួយគណៈកម្មការប្រព័ន្ធទូទាត់។",
        "សមាជិកចូលរួមចំនួន ៣០ រូប។",
        "- នំ ផ្លែឈើ និងភេសជ្ជៈ។",
        PAPER_LUNAR,
        "រាជធានីភ្នំពេញ ថ្ងៃទី១៤ ខែកញ្ញា ឆ្នាំ២០២៦",
        "អ្នកធ្វើប័ណ្ណ",
        "សុខ ដារ៉ា",
        "មតិលោកស្រីប្រធានការិយាល័យ",
        "មតិលោកប្រធាននាយកដ្ឋាន",
        "មតិលោកនាយកខុទ្ទកាល័យ",
        "ឯកភាពតាមសំណើ។",
        "លោកស្រី ហេង សុខលីណា",
        "០៩/១១/២០២៦",
        "ប្រអប់សំបុត្រលេខ ២៥",
    ):
        assert expected in text, expected
    assert len(document.inline_shapes) == 5  # the logo, the booker and the three boxes


def test_admin_and_the_pitika_of_the_province_download(
    client, auth_headers, as_admin, confirmed, make_pitika, org
):
    booking = confirmed()
    assert client.get(url(booking), headers=as_admin).status_code == 200
    assert client.get(url(booking), headers=auth_headers(make_pitika())).status_code == 200


def test_others_do_not(client, auth_headers, confirmed, make_pitika, make_user, org, db_session):
    booking = confirmed()
    owner = make_user(roles=["ROOM_OWNER"])
    booking.room.room_owner_id = owner.id
    db_session.flush()
    assert client.get(url(booking), headers=auth_headers(owner)).status_code == 403
    far_pitika = make_pitika(province="KAMPOT")
    assert client.get(url(booking), headers=auth_headers(far_pitika)).status_code in (403, 404)
    stranger = make_user(roles=["STAFF"])
    assert client.get(url(booking), headers=auth_headers(stranger)).status_code == 404
    assert client.get(url(booking)).status_code == 401


@pytest.mark.parametrize(
    "status", [BookingStatus.PENDING_PITIKA, BookingStatus.REJECTED, BookingStatus.CANCELLED]
)
def test_only_a_confirmed_booking_has_a_slip(
    client, auth_headers, make_bookable_room, make_booking, maker, status
):
    booking = make_booking(make_bookable_room(), maker, status=status)
    response = client.get(url(booking), headers=auth_headers(maker))
    assert response.status_code == 404
    assert response.json()["error"]["message"] == "This booking is not confirmed yet."


def test_a_completed_booking_still_has_its_slip(client, auth_headers, confirmed, maker, org):
    booking = confirmed(sessions=((date(2026, 11, 2), time(9), time(10)),))  # ended a week ago
    assert client.get(url(booking), headers=auth_headers(maker)).status_code == 200


def test_old_booking_without_copies(
    client, auth_headers, db_session, settings, make_bookable_room, make_booking, maker
):
    """Confirmed before the slip existed: it downloads, with only the logo and the booker's
    signature from their profile now."""
    _write_png(settings, "users/9/me.png")
    booking = make_booking(make_bookable_room(), maker, status=BookingStatus.CONFIRMED)
    booking.requester_info = {"name_en": "Sok Dara", "name_kh": "សុខ ដារ៉ា"}
    db_session.flush()
    document = _open(client.get(url(booking), headers=auth_headers(maker)))
    assert len(document.inline_shapes) == 2
    assert "ឯកភាពតាមសំណើ។" not in _all_text(document)


def test_no_signature_files_means_no_pictures_but_the_words_stay(
    client, auth_headers, confirmed, maker, org
):
    document = _open(client.get(url(confirmed()), headers=auth_headers(maker)))
    assert len(document.inline_shapes) == 1  # the logo
    assert "លោក ចាន់ សុភក្ត្រ" in _all_text(document)


def test_twenty_sessions(client, auth_headers, confirmed, maker, org):
    """A long booking: a 200-character title and 20 sessions at different times."""
    sessions = tuple(
        (date(2026, 11, 10 + n // 2), time(8 + n % 2 * 5), time(11 + n % 2 * 5)) for n in range(20)
    )
    document = _open(
        client.get(
            url(confirmed(sessions=sessions, meeting_title="ក" * 200)), headers=auth_headers(maker)
        )
    )
    timetable = [
        t
        for t in document.element.iter()
        if t.tag.endswith("}tbl") and len(t.findall(".//{*}tr")) == 21
    ]
    assert len(timetable) == 1
    assert "ក" * 200 in _all_text(document)
