from __future__ import annotations

import time

from bursa_picker.data.ratelimit import TokenBucket, throttle, with_retry
from bursa_picker.logging_setup import reset_metrics, snapshot_metrics


def test_token_bucket_throttles() -> None:
    b = TokenBucket(rps=10.0)
    start = time.monotonic()
    for _ in range(20):
        b.take()
    elapsed = time.monotonic() - start
    assert elapsed >= 1.0 - 0.2


def test_throttle_decorator_runs() -> None:
    calls = []

    @throttle("test_unique_key_1", rps=100.0)
    def f(x):
        calls.append(x)
        return x * 2

    assert f(3) == 6
    assert calls == [3]


def test_with_retry_succeeds_after_transient() -> None:
    reset_metrics()
    state = {"n": 0}

    @with_retry(max_attempts=4, exceptions=(ValueError,))
    def flaky():
        state["n"] += 1
        if state["n"] < 3:
            raise ValueError("transient")
        return "ok"

    assert flaky() == "ok"
    assert state["n"] == 3
    assert snapshot_metrics()["yfinance_calls"] == 1
    assert snapshot_metrics()["yfinance_failures"] == 0


def test_with_retry_gives_up_and_records_failure() -> None:
    reset_metrics()

    @with_retry(max_attempts=2, exceptions=(RuntimeError,))
    def always_fails():
        raise RuntimeError("nope")

    try:
        always_fails()
    except RuntimeError:
        pass

    assert snapshot_metrics()["yfinance_failures"] == 1
