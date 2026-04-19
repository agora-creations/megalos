"""Unit tests for megalos_panel.retry.retry_with_backoff.

Covers per-exception-type budgets, mixed consumption in a single call,
non-retryable exception wrapping, and the exponential-backoff schedule
by monkeypatching time.sleep so tests never wait on real time.
"""

from __future__ import annotations

from typing import Callable

import pytest

from megalos_panel import retry as retry_mod
from megalos_panel.errors import PanelProviderError, RateLimitError, TransientError
from megalos_panel.retry import retry_with_backoff


@pytest.fixture
def no_sleep(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    """Capture sleep durations instead of actually sleeping."""
    captured: list[float] = []

    def fake_sleep(seconds: float) -> None:
        captured.append(seconds)

    monkeypatch.setattr(retry_mod.time, "sleep", fake_sleep)
    return captured


def _sequence_fn(outcomes: list[Callable[[], object]]) -> Callable[[], object]:
    """Return a callable that pops from ``outcomes`` on each invocation."""
    iterator = iter(outcomes)

    def call() -> object:
        step = next(iterator)
        return step()

    return call


def _raise(exc: Exception) -> Callable[[], object]:
    def step() -> object:
        raise exc

    return step


def _return(value: object) -> Callable[[], object]:
    def step() -> object:
        return value

    return step


def test_rate_limit_retry_then_success(no_sleep: list[float]) -> None:
    fn = _sequence_fn(
        [
            _raise(RateLimitError("429")),
            _raise(RateLimitError("429 again")),
            _return("ok"),
        ]
    )
    out = retry_with_backoff(
        fn,
        rate_limit_attempts=3,
        transient_attempts=5,
        backoff_cap=30.0,
        backoff_base=1.0,
        model="claude-opus-4-7",
    )
    assert out == "ok"
    # Two retries → two sleeps at 2^0 and 2^1 seconds.
    assert no_sleep == [1.0, 2.0]


def test_rate_limit_budget_exhausts_to_panel_provider_error(
    no_sleep: list[float],
) -> None:
    fn = _sequence_fn([_raise(RateLimitError(f"429 #{i}")) for i in range(3)])
    with pytest.raises(PanelProviderError) as exc_info:
        retry_with_backoff(
            fn,
            rate_limit_attempts=3,
            transient_attempts=5,
            backoff_cap=30.0,
            backoff_base=1.0,
            model="claude-opus-4-7",
        )
    err = exc_info.value
    assert err.model == "claude-opus-4-7"
    assert err.attempts == 3
    assert "429 #2" in err.last_error
    # Two sleeps between the three attempts; third failure raises.
    assert no_sleep == [1.0, 2.0]


def test_transient_budget_exhausts_to_panel_provider_error(
    no_sleep: list[float],
) -> None:
    fn = _sequence_fn([_raise(TransientError(f"timeout #{i}")) for i in range(5)])
    with pytest.raises(PanelProviderError) as exc_info:
        retry_with_backoff(
            fn,
            rate_limit_attempts=3,
            transient_attempts=5,
            backoff_cap=30.0,
            backoff_base=1.0,
            model="gpt-5",
        )
    err = exc_info.value
    assert err.model == "gpt-5"
    assert err.attempts == 5
    assert "timeout #4" in err.last_error
    assert no_sleep == [1.0, 2.0, 4.0, 8.0]


def test_mixed_budgets_coexist_in_one_call(no_sleep: list[float]) -> None:
    """A single call may consume up to the full rate-limit budget AND the
    full transient budget; the two counters do not share."""
    fn = _sequence_fn(
        [
            _raise(RateLimitError("429 a")),
            _raise(TransientError("timeout a")),
            _raise(RateLimitError("429 b")),
            _raise(TransientError("timeout b")),
            _raise(TransientError("timeout c")),
            _raise(TransientError("timeout d")),
            _return("ok"),
        ]
    )
    out = retry_with_backoff(
        fn,
        rate_limit_attempts=3,
        transient_attempts=5,
        backoff_cap=30.0,
        backoff_base=1.0,
        model="claude-opus-4-7",
    )
    assert out == "ok"
    # Six retries → six sleeps at 2^0..2^5.
    assert no_sleep == [1.0, 2.0, 4.0, 8.0, 16.0, 30.0]


def test_unknown_exception_wraps_with_attempts_one(no_sleep: list[float]) -> None:
    fn = _sequence_fn([_raise(ValueError("boom"))])
    with pytest.raises(PanelProviderError) as exc_info:
        retry_with_backoff(
            fn,
            rate_limit_attempts=3,
            transient_attempts=5,
            backoff_cap=30.0,
            backoff_base=1.0,
            model="claude-opus-4-7",
        )
    err = exc_info.value
    assert err.attempts == 1
    assert "boom" in err.last_error
    # Non-retryable → no backoff sleep.
    assert no_sleep == []


def test_backoff_caps_at_backoff_cap(no_sleep: list[float]) -> None:
    """Once 2^(attempt-1) * base exceeds the cap, every subsequent sleep
    equals the cap. The plan calls out this bound explicitly."""
    fn = _sequence_fn([_raise(TransientError("t")) for _ in range(5)])
    with pytest.raises(PanelProviderError):
        retry_with_backoff(
            fn,
            rate_limit_attempts=3,
            transient_attempts=5,
            backoff_cap=3.0,
            backoff_base=1.0,
            model="claude-opus-4-7",
        )
    assert no_sleep == [1.0, 2.0, 3.0, 3.0]


def test_first_call_success_does_not_sleep(no_sleep: list[float]) -> None:
    fn = _sequence_fn([_return("ok")])
    out = retry_with_backoff(
        fn,
        rate_limit_attempts=3,
        transient_attempts=5,
        backoff_cap=30.0,
        backoff_base=1.0,
        model="claude-opus-4-7",
    )
    assert out == "ok"
    assert no_sleep == []
