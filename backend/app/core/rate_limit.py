"""Throttling of repeated failed sign-in attempts.

Without a limit, an attacker can try passwords at machine speed. This module keeps a
sliding-window count of recent failures per key (the caller's address combined with the
email being tried) and reports when a key has used up its allowance.

Limitation: the counts live in the memory of a single API process. That is correct for one
instance and for development, but a deployment running several instances would need a
shared store (for example Redis or a database table) so the allowance is enforced across
all of them.
"""

import time
from collections import deque
from collections.abc import Callable
from functools import lru_cache
from threading import Lock

from app.core.config import get_settings

# When this many distinct keys are being tracked, expired entries are swept out so memory
# use cannot grow without bound under a flood of attempts with random emails.
_SWEEP_THRESHOLD = 10_000


class LoginRateLimiter:
    """Sliding-window limiter for failed sign-in attempts.

    Args:
        max_attempts: Failures allowed within the window before the key is blocked.
        window_seconds: Length of the sliding window.
        clock: Source of the current time in seconds. A monotonic clock by default, so
            changes to the system clock cannot reset or extend a block. Replaceable in tests.
    """

    def __init__(
        self,
        max_attempts: int,
        window_seconds: int,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._max_attempts = max_attempts
        self._window = window_seconds
        self._clock = clock
        self._failures: dict[str, deque[float]] = {}
        # Requests are handled on multiple threads, so access to the shared dictionary
        # must be serialised.
        self._lock = Lock()

    def _prune(self, key: str, now: float) -> deque[float]:
        """Drop failures that have left the window and return what remains for ``key``."""
        recent = self._failures.get(key)
        if recent is None:
            return deque()
        while recent and now - recent[0] >= self._window:
            recent.popleft()
        if not recent:
            del self._failures[key]
            return deque()
        return recent

    def is_blocked(self, key: str) -> bool:
        """Return True when ``key`` has reached its allowance of recent failures."""
        with self._lock:
            return len(self._prune(key, self._clock())) >= self._max_attempts

    def record_failure(self, key: str) -> None:
        """Record one failed attempt for ``key`` at the current time."""
        with self._lock:
            now = self._clock()
            if len(self._failures) >= _SWEEP_THRESHOLD:
                for stale_key in list(self._failures):
                    self._prune(stale_key, now)
            self._prune(key, now)
            self._failures.setdefault(key, deque()).append(now)

    def reset(self, key: str) -> None:
        """Forget all recorded failures for ``key``, for example after a successful sign-in."""
        with self._lock:
            self._failures.pop(key, None)

    def clear(self) -> None:
        """Forget everything. Intended for tests."""
        with self._lock:
            self._failures.clear()


@lru_cache
def get_login_limiter() -> LoginRateLimiter:
    """Return the process-wide limiter, configured from the application settings."""
    settings = get_settings()
    return LoginRateLimiter(
        max_attempts=settings.login_max_failed_attempts,
        window_seconds=settings.login_window_seconds,
    )
