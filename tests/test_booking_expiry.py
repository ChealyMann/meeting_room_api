"""The expiry job (spec section 10): T15, T17, BR-IT-06."""

import threading
from datetime import datetime, time, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app import expiry_runner
from app.constants.booking import EXPIRY_REASON, BookingStatus, ITStatus, RejectedBy
from app.expiry_runner import ExpiryRunner
from app.services import booking_expiry
from app.services import booking_transitions as transitions
from app.services.booking_expiry import ExpiryResult, run_once
from tests.booking_helpers import DAY

START = datetime.combine(DAY, time(9))  # the default session of make_booking


@pytest.fixture
def booking(make_user, make_bookable_room, make_booking):
    def build(status=BookingStatus.PENDING_PITIKA, **kwargs):
        return make_booking(
            make_bookable_room(), make_user(roles=["STAFF"]), status=status, **kwargs
        )

    return build


def test_t15_pending_rejected_at_start(freeze_now, booking, db_session):
    freeze_now(START - timedelta(days=1))
    b = booking()
    freeze_now(START)

    result = run_once(db_session)

    assert result == ExpiryResult(rejected=[b.id], confirmed=[])
    db_session.refresh(b)
    assert b.status == BookingStatus.REJECTED
    assert b.version == 2
    assert b.rejection.rejected_by == RejectedBy.SYSTEM
    assert b.rejection.actor_user_id is None
    assert b.rejection.reason == EXPIRY_REASON
    assert b.reviews == []
    assert all(not s.is_blocking for s in b.sessions)


def test_pending_owner_rejected(freeze_now, booking, db_session):
    freeze_now(START - timedelta(days=1))
    b = booking(status=BookingStatus.PENDING_OWNER)
    freeze_now(START + timedelta(minutes=5))

    assert run_once(db_session).rejected == [b.id]
    db_session.refresh(b)
    assert b.status == BookingStatus.REJECTED


def test_t17_setup_confirmed_with_pass(freeze_now, booking, db_session):
    freeze_now(START - timedelta(days=1))
    b = booking(status=BookingStatus.SETUP_IN_PROGRESS, it=True, forwarded=True)
    freeze_now(START)

    result = run_once(db_session)

    assert result == ExpiryResult(rejected=[], confirmed=[b.id])
    db_session.refresh(b)
    assert b.status == BookingStatus.CONFIRMED
    assert b.door_pass is not None
    assert b.rejection is None
    assert b.it_ticket.status == ITStatus.RECEIVED  # BR-IT-06: the ticket is not changed


def test_not_started_untouched(freeze_now, booking, db_session):
    freeze_now(START - timedelta(days=1))
    pending = booking()
    setup = booking(status=BookingStatus.SETUP_IN_PROGRESS, it=True, forwarded=True)
    confirmed = booking(status=BookingStatus.CONFIRMED, sessions=((DAY, time(7), time(8)),))
    freeze_now(START - timedelta(minutes=1))

    assert run_once(db_session) == ExpiryResult(rejected=[], confirmed=[])
    for b in (pending, setup, confirmed):
        version = b.version
        db_session.refresh(b)
        assert b.version == version
    assert (pending.status, setup.status) == (
        BookingStatus.PENDING_PITIKA,
        BookingStatus.SETUP_IN_PROGRESS,
    )


def test_uses_earliest_session(freeze_now, booking, db_session):
    freeze_now(START - timedelta(days=1))
    b = booking(sessions=((DAY + timedelta(days=1), time(9), time(10)), (DAY, time(9), time(10))))
    freeze_now(START)

    assert run_once(db_session).rejected == [b.id]


def test_skips_changed_booking(monkeypatch, freeze_now, booking, db_session):
    freeze_now(START - timedelta(days=1))
    changed = booking()
    others = [booking(), booking(status=BookingStatus.SETUP_IN_PROGRESS, it=True)]
    freeze_now(START)

    real_advance = transitions.advance

    def advance(session, b, version, **values):
        if b.id == changed.id:
            raise transitions._stale()  # a person acted first
        real_advance(session, b, version, **values)

    monkeypatch.setattr(transitions, "advance", advance)

    result = run_once(db_session)

    assert result == ExpiryResult(rejected=[others[0].id], confirmed=[others[1].id])
    db_session.refresh(changed)
    assert changed.status == BookingStatus.PENDING_PITIKA
    assert changed.rejection is None


def test_failing_booking_does_not_stop_the_others(
    monkeypatch, caplog, freeze_now, booking, db_session
):
    freeze_now(START - timedelta(days=1))
    broken = booking(status=BookingStatus.SETUP_IN_PROGRESS, it=True)  # the lowest id
    pending = booking()
    setup = booking(status=BookingStatus.SETUP_IN_PROGRESS, it=True)
    freeze_now(START)

    real_make_confirmed = transitions.make_confirmed

    def make_confirmed(session, b, version):
        if b.id == broken.id:
            raise RuntimeError("bad data")
        real_make_confirmed(session, b, version)

    monkeypatch.setattr(transitions, "make_confirmed", make_confirmed)

    result = run_once(db_session)

    assert result == ExpiryResult(rejected=[pending.id], confirmed=[setup.id])
    assert f"booking {broken.id} failed" in caplog.text
    db_session.rollback()  # only what run_once committed stays
    for b, status in (
        (broken, BookingStatus.SETUP_IN_PROGRESS),
        (pending, BookingStatus.REJECTED),
        (setup, BookingStatus.CONFIRMED),
    ):
        db_session.refresh(b)
        assert b.status == status


def test_script_prints_counts(capsys, monkeypatch, freeze_now, booking, db_session):
    from scripts import run_expiry

    freeze_now(START - timedelta(days=1))
    booking()
    freeze_now(START)
    monkeypatch.setattr(run_expiry, "SessionLocal", lambda: db_session)

    assert run_expiry.main() == 0
    assert capsys.readouterr().out.strip() == "Rejected: 1, confirmed: 0"


def test_runner_not_started_in_tests(app):
    with TestClient(app):
        assert app.state.expiry_runner is None


@pytest.fixture
def lock_is_free(monkeypatch, migrated_engine):
    """The runner uses its own lock name, so a dev server on the same MySQL cannot get in
    the way. Returns a check: is that lock free?"""
    monkeypatch.setattr(expiry_runner, "LOCK_NAME", "booking_expiry_test")

    def check() -> bool:
        with migrated_engine.connect() as connection:
            return connection.scalar(text("SELECT IS_FREE_LOCK('booking_expiry_test')")) == 1

    return check


def test_runner_holds_the_lock_until_stopped(monkeypatch, settings, lock_is_free):
    ran = threading.Event()
    monkeypatch.setattr(booking_expiry, "run_once", lambda session: ran.set())

    first = ExpiryRunner(settings)
    second = ExpiryRunner(settings)
    first.start()
    try:
        assert ran.wait(5)
        assert not lock_is_free()
        assert second.tick() is False  # only one process runs the job
    finally:
        second.stop()
        first.stop()
    assert lock_is_free()


def test_runner_keeps_the_lock_when_the_job_fails(
    monkeypatch, settings, migrated_engine, lock_is_free
):
    holders = []  # the MySQL connection that holds the lock, at each run
    two_runs = threading.Event()

    def fail(session):
        with migrated_engine.connect() as connection:
            sql = "SELECT IS_USED_LOCK('booking_expiry_test')"
            holders.append(connection.scalar(text(sql)))
        if len(holders) == 2:
            two_runs.set()
        raise RuntimeError("job failed")

    monkeypatch.setattr(booking_expiry, "run_once", fail)
    runner = ExpiryRunner(settings.model_copy(update={"expiry_interval_seconds": 1}))
    runner.start()
    try:
        assert two_runs.wait(5)
    finally:
        runner.stop()
    assert holders[0] is not None
    assert holders[0] == holders[1]  # the lock connection was kept
    assert lock_is_free()


def test_runner_start_twice_makes_one_thread(monkeypatch, settings, lock_is_free):
    monkeypatch.setattr(booking_expiry, "run_once", lambda session: None)

    def job_threads() -> int:
        return sum(t.name == "expiry-job" for t in threading.enumerate())

    before = job_threads()
    runner = ExpiryRunner(settings)
    runner.start()
    runner.start()
    try:
        assert job_threads() == before + 1
    finally:
        runner.stop()
    assert job_threads() == before


def test_lifespan_starts_and_stops_the_runner(monkeypatch, settings, lock_is_free):
    from app.main import create_app

    ran = threading.Event()
    monkeypatch.setattr(booking_expiry, "run_once", lambda session: ran.set())
    app = create_app(settings.model_copy(update={"expiry_job_enabled": True}))

    with TestClient(app):
        assert app.state.expiry_runner is not None
        assert ran.wait(5)
    assert app.state.expiry_runner is None
    assert lock_is_free()
