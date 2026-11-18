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


W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


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
    """Confirmed before the slip existed: it downloads, with the booker's signature from their
    profile now, and the boxes signed by the people set now (fill empty boxes, 18 Nov 2026);
    their signature files were never written here, so only the logo and the booker's show."""
    _write_png(settings, "users/9/me.png")
    booking = make_booking(make_bookable_room(), maker, status=BookingStatus.CONFIRMED)
    booking.requester_info = {"name_en": "Sok Dara", "name_kh": "សុខ ដារ៉ា"}
    db_session.flush()
    document = _open(client.get(url(booking), headers=auth_headers(maker)))
    assert len(document.inline_shapes) == 2
    assert "ឯកភាពតាមសំណើ។" in _all_text(document)


def test_no_signature_files_means_no_pictures_but_the_words_stay(
    client, auth_headers, confirmed, maker, org
):
    document = _open(client.get(url(confirmed()), headers=auth_headers(maker)))
    assert len(document.inline_shapes) == 1  # the logo
    assert "លោក ចាន់ សុភក្ត្រ" in _all_text(document)


def _size_of(document, text: str) -> int:
    """The Khmer font size (half-points) of the first run holding `text`."""
    for run in document.element.iter("{*}r"):
        if text in "".join(t.text or "" for t in run.iter("{*}t")):
            return int(run.find("{*}rPr/{*}szCs").get(f"{{{W}}}val"))
    raise AssertionError(text)


def test_twenty_sessions(client, auth_headers, confirmed, maker, org):
    """The longest booking the app allows: a 200-character title and 20 sessions at different
    times. The timetable prints two sessions to a row, and the whole slip shrinks to one page."""
    sessions = tuple(
        (date(2026, 11, 10 + n // 2), time(8 + n % 2 * 5), time(11 + n % 2 * 5)) for n in range(20)
    )
    long = _open(
        client.get(
            url(confirmed(sessions=sessions, meeting_title="ក" * 200)), headers=auth_headers(maker)
        )
    )
    timetable = [
        t
        for t in long.element.iter()
        if t.tag.endswith("}tbl") and len(t.findall(".//{*}tr")) == 11
    ]
    assert len(timetable) == 1
    assert len(timetable[0].find("{*}tr").findall("{*}tc")) == 6
    assert "ក" * 200 in _all_text(long)
    short = _open(client.get(url(confirmed()), headers=auth_headers(maker)))
    assert _size_of(long, "ស្នើសុំរៀបចំ") < _size_of(short, "ស្នើសុំរៀបចំ")


def test_opinions_are_written_in_a_pen_font(client, auth_headers, confirmed, maker, org):
    """The opinion boxes' comments and dates look hand-written (Khmer OS Freehand); the rest of
    the slip keeps the paper's fonts."""
    document = _open(client.get(url(confirmed()), headers=auth_headers(maker)))

    def fonts_of(text: str) -> set[str]:
        found = set()
        for run in document.element.iter("{*}r"):
            if text in "".join(t.text or "" for t in run.iter("{*}t")):
                fonts = run.find("{*}rPr/{*}rFonts")
                found.add(fonts.get(f"{{{W}}}cs"))
        return found

    assert fonts_of("ឯកភាពតាមសំណើ។") == {"Khmer OS Freehand"}
    assert fonts_of("០៩/១១/២០២៦") == {"Khmer OS Freehand"}
    assert fonts_of("សមាជិកចូលរួមចំនួន") == {"Khmer OS Battambang"}
    assert fonts_of("ពេជ្រ វិសាល") == {"Khmer OS Muol Light"}


def test_both_heads_comments_are_three_lines_of_one_size(
    client, auth_headers, confirmed, maker, org
):
    """The department head's and the office head's comments: three lines each (two breaks), in
    one shared size, so the two boxes look the same (owner, 13 Nov 2026)."""
    document = _open(client.get(url(confirmed()), headers=auth_headers(maker)))
    boxes = [
        p
        for p in document.element.iter("{*}p")
        if "សូមគោរពជូន" in "".join(t.text or "" for t in p.iter("{*}t"))
    ]
    assert len(boxes) == 2
    for box in boxes:
        assert len(list(box.iter("{*}br"))) == 2
    sizes = {s.get(f"{{{W}}}val") for box in boxes for s in box.iter("{*}szCs")}
    assert len(sizes) == 1


def test_a_long_title_shrinks_the_heads_comments_and_labels():
    """A long title (លោកជំទាវ) would wrap the comments to four lines and the office head's label
    to two, pushing the slip onto a second page: both get smaller instead."""
    from app.services.request_slip_data import SlipSigner, _pass_up
    from app.services.request_slip_docx import (
        LABEL_CM_PER_LETTER,
        OFFICE_BOX_CM,
        PEN_SIZE,
        _fit_size,
        heads_comment_size,
    )

    def head(to):
        return SlipSigner(comment=_pass_up(to), name="x", title="", signature=None, date="")

    class Data:
        department_head = head("នាយកខុទ្ទកាល័យ")
        office_head = head("ប្រធាននាយកដ្ឋាន")

    assert heads_comment_size(Data) == PEN_SIZE
    # At the small pen size even លោកជំទាវ fits; a line longer than the box still shrinks.
    Data.department_head, Data.office_head = (
        head("លោកជំទាវនាយកខុទ្ទកាល័យ"),
        head("លោកជំទាវប្រធាននាយកដ្ឋាន ប្រធាននាយកដ្ឋាន"),
    )
    assert heads_comment_size(Data) < PEN_SIZE
    label = "មតិលោកជំទាវប្រធានការិយាល័យ"
    assert _fit_size([label], 10.5, OFFICE_BOX_CM, LABEL_CM_PER_LETTER) < 10.5
    assert _fit_size(["មតិប្រធានការិយាល័យ"], 10.5, OFFICE_BOX_CM, LABEL_CM_PER_LETTER) == 10.5


def test_signatures_are_in_the_pen_blue():
    """Signatures print in the same blue as the comments (owner, 18 Nov 2026), whatever colour
    the stored picture is; see-through stays see-through."""
    from app.services.request_slip_docx import INK_BLUE, blue_ink

    black = Image.new("RGBA", (4, 1), (0, 0, 0, 0))
    black.putpixel((1, 0), (0, 0, 0, 255))
    black.putpixel((2, 0), (40, 40, 40, 128))
    buffer = io.BytesIO()
    black.save(buffer, "PNG")
    out = Image.open(blue_ink(buffer.getvalue())).convert("RGBA")
    blue = (INK_BLUE[0], INK_BLUE[1], INK_BLUE[2])
    assert out.getpixel((1, 0)) == (*blue, 255)
    assert out.getpixel((2, 0)) == (*blue, 128)
    assert out.getpixel((0, 0))[3] == 0
