"""Reference codes and door pass codes (spec 8.3, B-28)."""

import re
import secrets
from datetime import datetime, timedelta

import pytest

from app.constants.booking import BookingStatus
from app.models import BookingDoorPass
from app.services import booking_codes, clock
from tests.booking_helpers import NOW


def test_reference_code_format(db_session):
    code = booking_codes.new_reference_code(db_session, NOW)
    assert re.fullmatch(r"NBC-26-\d{5}", code)


def test_reference_code_uses_the_local_year(db_session):
    code = booking_codes.new_reference_code(db_session, datetime(2031, 1, 2, 8, 0))
    assert code.startswith("NBC-31-")


def test_reference_code_skips_a_taken_code(
    db_session, monkeypatch, frozen, make_bookable_room, make_user, make_booking
):
    # The taken code is fixed, so the second draw can never be it.
    make_booking(
        make_bookable_room(),
        make_user(),
        status=BookingStatus.PENDING_PITIKA,
        reference_code="NBC-26-55555",
    )
    draws = iter([45555, 4321, 7777])  # 45555 + 10000 = 55555 is taken
    monkeypatch.setattr(secrets, "randbelow", lambda _n: next(draws))
    assert booking_codes.new_reference_code(db_session, NOW) == "NBC-26-14321"


def test_reference_code_gives_up_after_20_tries(db_session, monkeypatch):
    monkeypatch.setattr(booking_codes, "_reference_taken", lambda _session, _code: True)
    with pytest.raises(RuntimeError):
        booking_codes.new_reference_code(db_session, NOW)


def test_door_pass_format(db_session):
    code = booking_codes.new_door_pass_code(db_session, "NBC-26-48213")
    assert re.fullmatch(r"NBC-[1-9]\d{4}", code)


def _add_pass(db_session, booking, passcode, expires_at):
    db_session.add(BookingDoorPass(booking_id=booking.id, passcode=passcode, expires_at=expires_at))
    db_session.flush()


def test_door_pass_skips_active_codes(
    db_session, monkeypatch, frozen, make_bookable_room, make_user, make_booking
):
    booking = make_booking(make_bookable_room(), make_user(), status=BookingStatus.PENDING_PITIKA)
    _add_pass(db_session, booking, "NBC-55555", clock.now_utc() + timedelta(hours=1))
    draws = iter([45555, 12345])  # 45555 + 10000 = 55555 is taken
    monkeypatch.setattr(secrets, "randbelow", lambda _n: next(draws))
    assert booking_codes.new_door_pass_code(db_session, "NBC-26-48213") == "NBC-22345"


def test_door_pass_may_reuse_an_expired_code(
    db_session, monkeypatch, frozen, make_bookable_room, make_user, make_booking
):
    booking = make_booking(make_bookable_room(), make_user(), status=BookingStatus.PENDING_PITIKA)
    _add_pass(db_session, booking, "NBC-55555", clock.now_utc() - timedelta(hours=1))
    monkeypatch.setattr(secrets, "randbelow", lambda _n: 45555)
    assert booking_codes.new_door_pass_code(db_session, "NBC-26-48213") == "NBC-55555"


def test_door_pass_differs_from_the_reference_code(db_session, monkeypatch):
    """BR-DP-01: the pass's 5 digits are never the last 5 digits of the reference code."""
    draws = iter([38213, 11111])  # the first draw gives NBC-48213: the digits of NBC-26-48213
    monkeypatch.setattr(secrets, "randbelow", lambda _n: next(draws))
    assert booking_codes.new_door_pass_code(db_session, "NBC-26-48213") == "NBC-21111"
