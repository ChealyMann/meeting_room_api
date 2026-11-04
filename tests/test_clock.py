from datetime import date, datetime, time
from types import SimpleNamespace

from app.services import clock


def test_now_local_is_utc_plus_7(freeze_now):
    freeze_now(datetime(2026, 11, 10, 6, 30))
    assert clock.now_local() == datetime(2026, 11, 10, 6, 30)
    assert clock.now_utc() == datetime(2026, 11, 9, 23, 30)


def test_now_utc_is_naive_and_whole_seconds():
    value = clock.now_utc()
    assert value.tzinfo is None
    assert value.microsecond == 0


def test_local_to_utc():
    assert clock.local_to_utc(datetime(2026, 11, 10, 9, 0)) == datetime(2026, 11, 10, 2, 0)


def test_session_start_and_end():
    s = SimpleNamespace(date=date(2026, 11, 10), start_time=time(9, 0), end_time=time(10, 30))
    assert clock.session_start(s) == datetime(2026, 11, 10, 9, 0)
    assert clock.session_end(s) == datetime(2026, 11, 10, 10, 30)
