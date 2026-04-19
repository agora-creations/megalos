"""Thread-pool fan-out for concurrent panel provider calls.

fan_out submits one worker per PanelRequest to a ThreadPoolExecutor and
collects results into a dict keyed by request_id. Errors raised inside a
worker are caught and surfaced as PanelResult(error=...) rather than
propagating — fan_out never raises, because a single provider failure
should not abort the rest of the batch.

ThreadPoolExecutor (not asyncio) is a deliberate design choice. Provider
calls are IO-bound, so the GIL releases during network waits — threads
give us concurrency without paying the cost of async coloring every
caller up the stack. The sync function signature keeps panel_query
usable from synchronous orchestration code, which matches the rest of
the megalos codebase.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Callable

from .types import PanelRequest, PanelResult


def fan_out(
    requests: list[PanelRequest],
    per_request_fn: Callable[[PanelRequest], PanelResult],
    *,
    max_workers: int = 8,
) -> dict[str, PanelResult]:
    """Run ``per_request_fn`` concurrently over ``requests``.

    Returns a dict mapping ``request.request_id`` to the worker's
    ``PanelResult``. Worker exceptions are converted into
    ``PanelResult(selection='', raw_response='', error=str(exc))`` so
    the returned dict always has one entry per input request.
    """
    if not requests:
        return {}

    results: dict[str, PanelResult] = {}
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        future_to_request_id = {
            pool.submit(_safe_call, per_request_fn, req): req.request_id
            for req in requests
        }
        for future in future_to_request_id:
            request_id = future_to_request_id[future]
            results[request_id] = future.result()
    return results


def _safe_call(
    per_request_fn: Callable[[PanelRequest], PanelResult],
    request: PanelRequest,
) -> PanelResult:
    try:
        return per_request_fn(request)
    except Exception as exc:
        return PanelResult(selection="", raw_response="", error=str(exc))
