"""Tests for the failed-sign-in limiter, using a controllable clock. No database is needed."""

from app.core.rate_limit import LoginRateLimiter


class FakeClock:
    """A clock that only moves when the test says so."""

    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def make_limiter(clock: FakeClock) -> LoginRateLimiter:
    return LoginRateLimiter(max_attempts=3, window_seconds=60, clock=clock)


def test_key_is_not_blocked_before_reaching_the_allowance() -> None:
    limiter = make_limiter(FakeClock())
    limiter.record_failure("k")
    limiter.record_failure("k")
    assert limiter.is_blocked("k") is False


def test_key_is_blocked_once_the_allowance_is_used() -> None:
    limiter = make_limiter(FakeClock())
    for _ in range(3):
        limiter.record_failure("k")
    assert limiter.is_blocked("k") is True


def test_block_lifts_when_failures_leave_the_window() -> None:
    clock = FakeClock()
    limiter = make_limiter(clock)
    for _ in range(3):
        limiter.record_failure("k")
    clock.now += 61
    assert limiter.is_blocked("k") is False


def test_old_failures_do_not_count_towards_new_ones() -> None:
    clock = FakeClock()
    limiter = make_limiter(clock)
    limiter.record_failure("k")
    limiter.record_failure("k")
    clock.now += 61
    limiter.record_failure("k")
    assert limiter.is_blocked("k") is False


def test_reset_forgets_failures_for_one_key_only() -> None:
    limiter = make_limiter(FakeClock())
    for _ in range(3):
        limiter.record_failure("a")
        limiter.record_failure("b")
    limiter.reset("a")
    assert limiter.is_blocked("a") is False
    assert limiter.is_blocked("b") is True


def test_keys_are_independent() -> None:
    limiter = make_limiter(FakeClock())
    for _ in range(3):
        limiter.record_failure("a")
    assert limiter.is_blocked("b") is False


def test_clear_forgets_everything() -> None:
    limiter = make_limiter(FakeClock())
    for _ in range(3):
        limiter.record_failure("a")
    limiter.clear()
    assert limiter.is_blocked("a") is False
