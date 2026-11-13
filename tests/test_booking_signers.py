"""The request slip's copies (snapshot rule): the booker's Khmer office names when the booking is
sent; the signers (who, title, signature file) and the confirm time when it is confirmed. Old
slips must not change when people move, offices are renamed, heads or signatures change."""

import pytest

from app.constants.booking import BookingStatus, SignerRole
from app.models import BookingSigner
from app.services import booking_transitions as transitions
from app.services import clock, user_signature
from app.services.booking import requester_info
from app.services.slip_settings import get_slip_settings


@pytest.fixture
def org(make_department, make_division, make_user, db_session):
    """An office (division) in a department, each with a head; a Director of Cabinet."""
    dept_head = make_user(name_kh="ចាន់ សុភក្ត្រ", title="Mr.", user_signature="users/1/dept.png")
    office_head = make_user(name_kh="ហេង សុខលីណា", title="Ms.", user_signature="users/2/office.png")
    director = make_user(name_kh="ពេជ្រ វិសាល", title="Mr.", user_signature="users/3/dir.png")
    department = make_department(name_kh="នាយកដ្ឋានប្រព័ន្ធទូទាត់", head_user_id=dept_head.id)
    division = make_division(
        department=department, name_kh="ការិយាល័យគោលនយោបាយ", head_user_id=office_head.id
    )
    get_slip_settings(db_session).director_user_id = director.id
    db_session.flush()
    return {
        "department": department,
        "division": division,
        "dept_head": dept_head,
        "office_head": office_head,
        "director": director,
    }


@pytest.fixture
def booker(make_user, org):
    return make_user(
        name_kh="សុខ ដារ៉ា", title="Mr.", division=org["division"], user_signature="users/9/me.png"
    )


def _confirm(db_session, booking):
    transitions.make_confirmed(db_session, booking, booking.version)
    db_session.flush()
    return {s.role: s for s in db_session.query(BookingSigner).filter_by(booking_id=booking.id)}


def test_send_keeps_khmer_office_names(booker, org):
    info = requester_info(booker)
    assert info["division_id"] == org["division"].id
    assert info["division_kh"] == "ការិយាល័យគោលនយោបាយ"
    assert info["department_id"] == org["department"].id
    assert info["department_kh"] == "នាយកដ្ឋានប្រព័ន្ធទូទាត់"


def test_send_without_division(make_user):
    info = requester_info(make_user())
    assert (
        info["division_id"],
        info["division_kh"],
        info["department_id"],
        info["department_kh"],
    ) == (None, None, None, None)


def test_confirm_keeps_time_and_four_signers(
    frozen, db_session, make_bookable_room, make_booking, booker, org
):
    booking = make_booking(make_bookable_room(), booker, status=BookingStatus.PENDING_PITIKA)
    signers = _confirm(db_session, booking)
    assert booking.status == BookingStatus.CONFIRMED
    assert booking.confirmed_at == clock.now_utc()
    assert set(signers) == {
        SignerRole.MAKER,
        SignerRole.OFFICE_HEAD,
        SignerRole.DEPARTMENT_HEAD,
        SignerRole.DIRECTOR,
    }
    assert (signers[SignerRole.MAKER].name_kh, signers[SignerRole.MAKER].signature_path) == (
        "សុខ ដារ៉ា",
        "users/9/me.png",
    )
    office = signers[SignerRole.OFFICE_HEAD]
    assert (office.user_id, office.name_kh, office.title, office.signature_path) == (
        org["office_head"].id,
        "ហេង សុខលីណា",
        "Ms.",
        "users/2/office.png",
    )
    assert signers[SignerRole.DEPARTMENT_HEAD].user_id == org["dept_head"].id
    assert signers[SignerRole.DIRECTOR].user_id == org["director"].id
    assert all(s.signed_at == booking.confirmed_at for s in signers.values())


def test_copies_survive_moves(
    frozen, db_session, make_bookable_room, make_booking, make_division, make_user, booker, org
):
    booking = make_booking(make_bookable_room(), booker, status=BookingStatus.PENDING_PITIKA)
    _confirm(db_session, booking)
    booker.division_id = make_division().id
    org["division"].head_user_id = make_user().id
    org["office_head"].name_kh = "ឈ្មោះថ្មី"
    org["office_head"].user_signature = "users/2/new.png"
    db_session.flush()
    office = (
        db_session.query(BookingSigner)
        .filter_by(booking_id=booking.id, role=SignerRole.OFFICE_HEAD)
        .one()
    )
    assert (office.user_id, office.name_kh, office.signature_path) == (
        org["office_head"].id,
        "ហេង សុខលីណា",
        "users/2/office.png",
    )


def test_heads_come_from_the_office_when_sent(
    frozen, db_session, make_bookable_room, make_booking, make_division, booker, org
):
    booking = make_booking(make_bookable_room(), booker, status=BookingStatus.PENDING_PITIKA)
    booker.division_id = make_division().id  # moved after sending, before confirm
    db_session.flush()
    signers = _confirm(db_session, booking)
    assert signers[SignerRole.OFFICE_HEAD].user_id == org["office_head"].id


def test_booker_is_office_head(frozen, db_session, make_bookable_room, make_booking, org):
    head = org["office_head"]
    head.division_id = org["division"].id
    db_session.flush()
    signers = _confirm(
        db_session, make_booking(make_bookable_room(), head, status=BookingStatus.PENDING_PITIKA)
    )
    assert signers[SignerRole.MAKER].user_id == signers[SignerRole.OFFICE_HEAD].user_id == head.id


def test_booker_without_division(
    frozen, db_session, make_bookable_room, make_booking, make_user, org
):
    signers = _confirm(
        db_session,
        make_booking(make_bookable_room(), make_user(), status=BookingStatus.PENDING_PITIKA),
    )
    assert set(signers) == {SignerRole.MAKER, SignerRole.DIRECTOR}


def test_unset_head_has_no_row(frozen, db_session, make_bookable_room, make_booking, booker, org):
    org["department"].head_user_id = None
    get_slip_settings(db_session).director_user_id = None
    db_session.flush()
    signers = _confirm(
        db_session, make_booking(make_bookable_room(), booker, status=BookingStatus.PENDING_PITIKA)
    )
    assert set(signers) == {SignerRole.MAKER, SignerRole.OFFICE_HEAD}


def test_last_review_confirms_and_records(
    frozen, db_session, make_bookable_room, make_booking, booker, org
):
    booking = make_booking(make_bookable_room(), booker, status=BookingStatus.PENDING_PITIKA)
    transitions.after_last_review(db_session, booking, booking.version)
    db_session.flush()
    assert db_session.query(BookingSigner).filter_by(booking_id=booking.id).count() == 4


def test_new_signature_keeps_the_old_file_a_slip_uses(
    frozen, db_session, settings, make_bookable_room, make_booking, booker, org
):
    """A signer uploads a new signature after confirm: the file their slip uses stays."""
    head = org["office_head"]
    old = settings.signature_dir / "users/2/office.png"
    old.parent.mkdir(parents=True, exist_ok=True)
    old.write_bytes(b"png")
    _confirm(
        db_session, make_booking(make_bookable_room(), booker, status=BookingStatus.PENDING_PITIKA)
    )
    user_signature.remove_signature(db_session, settings, head)
    assert old.is_file()
    assert head.user_signature is None


def test_an_unused_old_signature_is_still_deleted(db_session, settings, make_user):
    user = make_user(user_signature="users/5/old.png")
    old = settings.signature_dir / "users/5/old.png"
    old.parent.mkdir(parents=True, exist_ok=True)
    old.write_bytes(b"png")
    user_signature.remove_signature(db_session, settings, user)
    assert not old.exists()
