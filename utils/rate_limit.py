# utils/rate_limit.py
from __future__ import annotations
import time, threading, random
from typing import Callable, Any

class RateLimiter:
    """
    Thread-safe token bucket limiter for calls/minute.
    Caps overall concurrency across all threads.
    """
    def __init__(self, rpm: int = 500):
        if rpm <= 0:
            raise ValueError("rpm must be > 0")
        self.capacity = float(rpm)
        self.tokens = float(rpm)
        self.fill_rate = float(rpm) / 60.0  # tokens per second
        self.last = time.monotonic()
        self.lock = threading.Lock()

    def acquire(self) -> None:
        while True:
            with self.lock:
                now = time.monotonic()
                elapsed = now - self.last
                if elapsed > 0:
                    self.tokens = min(self.capacity, self.tokens + elapsed * self.fill_rate)
                    self.last = now
                if self.tokens >= 1.0:
                    self.tokens -= 1.0
                    return
                # need to wait for at least one token
                deficit = 1.0 - self.tokens
                sleep_s = max(0.0, deficit / self.fill_rate)
            # sleep outside the lock
            time.sleep(min(sleep_s, 0.5))  # wake frequently to keep latency low


def default_retry_pred(exc: Exception) -> bool:
    """Retry on common transient / rate / network issues."""
    s = str(exc).lower()
    return (
        "rate limit" in s or "429" in s or "too many requests" in s or
        "temporar" in s or "timeout" in s or "timed out" in s or
        "unavailable" in s or "overloaded" in s or "connection" in s or
        "retry" in s
    )


def with_retries(
    call: Callable[[], Any],
    *,
    limiter: RateLimiter,
    max_retries: int = 6,
    base_delay: float = 0.5,
    max_delay: float = 20.0,
    jitter: float = 0.2,
    retry_pred: Callable[[Exception], bool] = default_retry_pred,
) -> Any:
    """
    Acquire rate limiter, call, and retry with exponential backoff + jitter on transient errors.
    """
    attempt = 0
    while True:
        limiter.acquire()
        try:
            return call()
        except Exception as e:
            if attempt >= max_retries or not retry_pred(e):
                raise
            delay = min(max_delay, base_delay * (2 ** attempt))
            # jitter in ±jitter range
            delay *= (1.0 + random.uniform(-jitter, jitter))
            time.sleep(delay)
            attempt += 1

