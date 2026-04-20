"""Unit tests for megalos_panel.throttle.Throttle.

Covers RPS gating, TPM gating, rolling-window pruning, pathological
oversize handling, and the prompt-length token estimator. ``time.sleep``
is monkeypatched to capture durations without waiting, and
``time.monotonic`` is driven by a hand-rolled fake clock so windows
progress deterministically.
"""

from __future__ import annotations

import pytest  # type: ignore[import-not-found]

from megalos_panel import throttle as throttle_mod
from megalos_panel.throttle import Throttle, estimate_tokens


@pytest.fixture
def fake_clock(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    """A mutable [now] container driving time.monotonic inside throttle."""
    state = [0.0]
    monkeypatch.setattr(throttle_mod.time, "monotonic", lambda: state[0])
    return state


@pytest.fixture
def sleep_log(
    monkeypatch: pytest.MonkeyPatch, fake_clock: list[float]
) -> list[float]:
    """Replace sleep with a clock-advancing capture so the test can assert waits."""
    captured: list[float] = []

    def fake_sleep(seconds: float) -> None:
        captured.append(seconds)
        fake_clock[0] += seconds

    monkeypatch.setattr(throttle_mod.time, "sleep", fake_sleep)
    return captured


def test_estimate_tokens_heuristic() -> None:
    assert estimate_tokens("") == 1 + 100  # max(1, 0) + 100
    assert estimate_tokens("abcd") == 1 + 100
    assert estimate_tokens("a" * 400) == 100 + 100
    assert estimate_tokens("a" * 400, response_allowance=20) == 100 + 20


def test_no_bounds_admits_immediately(
    fake_clock: list[float], sleep_log: list[float]
) -> None:
    throttle = Throttle()
    for _ in range(10):
        throttle.acquire(estimated_tokens=500)
    assert sleep_log == []


def test_rps_gates_over_window(
    fake_clock: list[float], sleep_log: list[float]
) -> None:
    throttle = Throttle(max_rps=3)
    for _ in range(3):
        throttle.acquire()
    assert sleep_log == []
    throttle.acquire()
    assert len(sleep_log) == 1
    assert 1.0 < sleep_log[0] < 1.1


def test_rps_window_rolls_after_one_second(
    fake_clock: list[float], sleep_log: list[float]
) -> None:
    throttle = Throttle(max_rps=2)
    throttle.acquire()
    throttle.acquire()
    fake_clock[0] += 1.5
    throttle.acquire()
    assert sleep_log == []


def test_tpm_gates_on_token_budget(
    fake_clock: list[float], sleep_log: list[float]
) -> None:
    throttle = Throttle(max_tpm=1000)
    throttle.acquire(estimated_tokens=400)
    throttle.acquire(estimated_tokens=400)
    assert sleep_log == []
    throttle.acquire(estimated_tokens=400)
    assert len(sleep_log) == 1
    assert 60.0 < sleep_log[0] < 60.1


def test_tpm_window_rolls_after_sixty_seconds(
    fake_clock: list[float], sleep_log: list[float]
) -> None:
    throttle = Throttle(max_tpm=500)
    throttle.acquire(estimated_tokens=400)
    fake_clock[0] += 60.5
    throttle.acquire(estimated_tokens=400)
    assert sleep_log == []


def test_pathological_oversize_admits_immediately(
    fake_clock: list[float], sleep_log: list[float]
) -> None:
    throttle = Throttle(max_tpm=100)
    throttle.acquire(estimated_tokens=500)
    assert sleep_log == []


def test_rps_and_tpm_together(
    fake_clock: list[float], sleep_log: list[float]
) -> None:
    throttle = Throttle(max_rps=10, max_tpm=300)
    throttle.acquire(estimated_tokens=100)
    throttle.acquire(estimated_tokens=100)
    throttle.acquire(estimated_tokens=100)
    throttle.acquire(estimated_tokens=100)
    assert len(sleep_log) == 1
    assert 60.0 < sleep_log[0] < 60.1


def test_zero_estimated_tokens_skips_tpm_tracking(
    fake_clock: list[float], sleep_log: list[float]
) -> None:
    throttle = Throttle(max_tpm=100)
    for _ in range(20):
        throttle.acquire(estimated_tokens=0)
    assert sleep_log == []


def test_panel_query_threads_throttle_through(monkeypatch: pytest.MonkeyPatch) -> None:
    """Integration: panel_query calls throttle.acquire once per invocation."""
    from megalos_panel import panel_query
    from megalos_panel.types import PanelRequest

    class StubAdapter:
        def __init__(self) -> None:
            pass

        def invoke(self, request: PanelRequest) -> str:
            return f"ok:{request.request_id}"

    monkeypatch.setattr(
        "megalos_panel.panel.adapters.dispatch",
        lambda model: StubAdapter,
    )

    acquire_calls: list[int] = []

    class SpyThrottle(Throttle):
        def acquire(self, estimated_tokens: int = 0) -> None:
            acquire_calls.append(estimated_tokens)

    requests = [
        PanelRequest(
            request_id=f"r{i}",
            model="claude-3-5-sonnet-20240620",
            prompt="hello " * (i + 1),
        )
        for i in range(3)
    ]
    throttle = SpyThrottle()
    results = panel_query(requests, throttle=throttle)
    assert len(results) == 3
    assert all(r.error is None for r in results.values())
    assert len(acquire_calls) == 3
    assert all(n > 0 for n in acquire_calls)
