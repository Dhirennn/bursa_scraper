"""Polite token-bucket throttle + tenacity-based retry for outbound calls."""

from __future__ import annotations

from functools import wraps
import threading
import time
from typing import Callable, TypeVar

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from bursa_picker.logging_setup import get_logger, incr

log = get_logger(__name__)

F = TypeVar("F", bound=Callable)


class TokenBucket:
    def __init__(self, rps: float) -> None:
        self.capacity = max(1.0, rps)
        self.tokens = self.capacity
        self.rps = rps
        self.last = time.monotonic()
        self.lock = threading.Lock()

    def take(self, n: int = 1) -> None:
        while True:
            with self.lock:
                now = time.monotonic()
                elapsed = now - self.last
                self.tokens = min(self.capacity, self.tokens + elapsed * self.rps)
                self.last = now
                if self.tokens >= n:
                    self.tokens -= n
                    return
                needed = (n - self.tokens) / self.rps
            time.sleep(needed)


_buckets: dict[str, TokenBucket] = {}
_buckets_lock = threading.Lock()


def get_bucket(key: str, rps: float) -> TokenBucket:
    with _buckets_lock:
        b = _buckets.get(key)
        if b is None:
            b = TokenBucket(rps)
            _buckets[key] = b
        return b


def throttle(key: str, rps: float):
    """Decorator: throttle by key (e.g., 'yfinance')."""
    bucket = get_bucket(key, rps)

    def decorate(fn: F) -> F:
        @wraps(fn)
        def wrapped(*args, **kwargs):
            bucket.take()
            return fn(*args, **kwargs)

        return wrapped  # type: ignore[return-value]

    return decorate


def with_retry(
    max_attempts: int = 4,
    backoff_base: float = 1.5,
    exceptions: tuple[type[BaseException], ...] = (Exception,),
):
    def decorate(fn: F) -> F:
        wrapped = retry(
            reraise=True,
            retry=retry_if_exception_type(exceptions),
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(multiplier=1.0, min=1.0, max=30.0, exp_base=backoff_base),
        )(fn)

        @wraps(fn)
        def inner(*args, **kwargs):
            try:
                result = wrapped(*args, **kwargs)
                incr("yfinance_calls")
                return result
            except Exception as e:
                incr("yfinance_failures")
                log.warning("retries exhausted for %s: %s", fn.__name__, e)
                raise

        return inner  # type: ignore[return-value]

    return decorate
