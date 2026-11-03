"""The clock for bookings (spec section 5).

Booking times are Phnom Penh local time (UTC+7, no daylight saving). Stored datetimes
are naive UTC. Read the time only through this module, so tests can freeze it.
"""

from collections.abc import Callable
from datetime import UTC, datetime, timedelta

LOCAL_OFFSET = timedelta(hours=7)


def _system_now() -> datetime:
    return datetime.now(UTC)


# Returns an aware UTC datetime. Tests replace it (see the `freeze_now` fixture).
_source: Callable[[], datetime] = _system_now


def now_utc() -> datetime:
    """Current UTC time, naive, whole seconds (same as `models.base.utcnow`)."""
    return _source().astimezone(UTC).replace(tzinfo=None, microsecond=0)


def now_local() -> datetime:
    """Current Phnom Penh time, naive."""
    return now_utc() + LOCAL_OFFSET


def local_to_utc(value: datetime) -> datetime:
    """A naive local datetime as naive UTC."""
    return value - LOCAL_OFFSET


def session_start(s) -> datetime:
    """Local start of a session: `s.date` at `s.start_time`."""
    return datetime.combine(s.date, s.start_time)


def session_end(s) -> datetime:
    """Local end of a session: `s.date` at `s.end_time`."""
    return datetime.combine(s.date, s.end_time)
