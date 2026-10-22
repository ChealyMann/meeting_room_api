"""Failed-login counter (spec section 9, "Login rate limit").

After `max_failures` failed logins for the same email and IP within `window_seconds`,
sign-in is refused until the oldest of those failures is older than the window.

Kept in memory: enough for one server process. A restart clears it, and several server
processes would each keep their own count (noted in the README).
"""

import math
import time
from collections import deque
from collections.abc import Callable, Hashable
from threading import Lock

_PURGE_EVERY = 1000  # recorded failures between clean-ups of forgotten keys


class LoginRateLimiter:
    def __init__(
        self,
        max_failures: int = 5,
        window_seconds: float = 15 * 60,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._max = max_failures
        self._window = window_seconds
        self._clock = clock
        self._failures: dict[Hashable, deque[float]] = {}
        self._lock = Lock()
        self._records = 0

    def retry_after(self, key: Hashable) -> int | None:
        """Seconds to wait if `key` is blocked now, else None."""
        with self._lock:
            now = self._clock()
            failures = self._recent(key, now)
            if len(failures) < self._max:
                return None
            unblocked_at = failures[-self._max] + self._window
            return max(1, math.ceil(unblocked_at - now))

    def record_failure(self, key: Hashable) -> None:
        with self._lock:
            now = self._clock()
            self._recent(key, now).append(now)
            self._records += 1
            if self._records % _PURGE_EVERY == 0:
                self._purge(now)

    def reset(self, key: Hashable) -> None:
        with self._lock:
            self._failures.pop(key, None)

    def tracked_keys(self) -> int:
        with self._lock:
            self._purge(self._clock())
            return len(self._failures)

    def _recent(self, key: Hashable, now: float) -> deque[float]:
        """The key's failures inside the window (older ones are dropped)."""
        failures = self._failures.setdefault(key, deque())
        while failures and failures[0] <= now - self._window:
            failures.popleft()
        return failures

    def _purge(self, now: float) -> None:
        for key in list(self._failures):
            if not self._recent(key, now):
                del self._failures[key]
