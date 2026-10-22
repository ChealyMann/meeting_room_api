from app.services.login_rate_limit import LoginRateLimiter

KEY = ("sok.dara@company.com", "10.0.0.1")
WINDOW = 15 * 60


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def make_limiter() -> tuple[LoginRateLimiter, FakeClock]:
    clock = FakeClock()
    return LoginRateLimiter(max_failures=5, window_seconds=WINDOW, clock=clock), clock


def test_not_blocked_before_five_failures():
    limiter, _ = make_limiter()
    for _ in range(4):
        limiter.record_failure(KEY)
    assert limiter.retry_after(KEY) is None


def test_blocked_after_five_failures():
    limiter, _ = make_limiter()
    for _ in range(5):
        limiter.record_failure(KEY)
    assert limiter.retry_after(KEY) == WINDOW


def test_retry_after_counts_down_from_the_oldest_failure():
    limiter, clock = make_limiter()
    limiter.record_failure(KEY)
    clock.now += 100
    for _ in range(4):
        limiter.record_failure(KEY)
    clock.now += 50
    assert limiter.retry_after(KEY) == WINDOW - 150


def test_unblocked_when_the_window_passes():
    limiter, clock = make_limiter()
    for _ in range(5):
        limiter.record_failure(KEY)
    clock.now += WINDOW
    assert limiter.retry_after(KEY) is None


def test_failures_older_than_the_window_do_not_count():
    limiter, clock = make_limiter()
    for _ in range(4):
        limiter.record_failure(KEY)
    clock.now += WINDOW + 1
    limiter.record_failure(KEY)
    assert limiter.retry_after(KEY) is None


def test_retry_after_is_at_least_one_second():
    limiter, clock = make_limiter()
    for _ in range(5):
        limiter.record_failure(KEY)
    clock.now += WINDOW - 0.2
    assert limiter.retry_after(KEY) == 1


def test_reset_clears_failures():
    limiter, _ = make_limiter()
    for _ in range(5):
        limiter.record_failure(KEY)
    limiter.reset(KEY)
    assert limiter.retry_after(KEY) is None


def test_keys_are_separate():
    limiter, _ = make_limiter()
    for _ in range(5):
        limiter.record_failure(KEY)
    assert limiter.retry_after(("sok.dara@company.com", "10.0.0.2")) is None
    assert limiter.retry_after(("other@company.com", "10.0.0.1")) is None


def test_old_keys_are_forgotten():
    limiter, clock = make_limiter()
    limiter.record_failure(("a@company.com", "1.1.1.1"))
    clock.now += WINDOW + 1
    limiter.record_failure(KEY)
    assert limiter.tracked_keys() == 1
