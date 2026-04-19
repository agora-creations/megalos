"""Retry budget constants and helper for panel provider calls.

Constants are the contract: 3 attempts for rate-limit (429) errors,
5 attempts for transient network errors (timeout, connection reset, 5xx),
exponential backoff capped at 30 seconds with a 1-second base.

retry_with_backoff is the composition helper. It maintains two independent
per-exception-type budgets in a single call — a provider run can consume
up to 3 rate-limit retries AND up to 5 transient retries within the same
invocation. Backoff delay is computed from the attempt counter shared
across both error types: min(backoff_base * 2^(attempt-1), backoff_cap).
On budget exhaustion (either bucket), the last underlying exception is
wrapped into PanelProviderError so upstream code sees a single failure
type. Non-retryable exceptions are also wrapped into PanelProviderError
(attempts=1) so callers never have to distinguish adapter-internal from
generic failures.
"""

from __future__ import annotations

import time
from typing import Callable, TypeVar

from .errors import PanelProviderError, RateLimitError, TransientError

RATE_LIMIT_ATTEMPTS = 3
TRANSIENT_ATTEMPTS = 5
BACKOFF_CAP_SECONDS = 30
BACKOFF_BASE_SECONDS = 1

T = TypeVar("T")


def retry_with_backoff(
    fn: Callable[[], T],
    *,
    rate_limit_attempts: int,
    transient_attempts: int,
    backoff_cap: float,
    backoff_base: float = 1.0,
    model: str = "unknown",
) -> T:
    """Call ``fn`` with per-type retry budgets and exponential backoff.

    ``rate_limit_attempts`` and ``transient_attempts`` are independent
    budgets — each counts only its own exception type. Total attempt
    count is the sum of calls made (initial + retries across both
    buckets). Backoff between attempts uses
    ``min(backoff_base * 2 ** (attempt - 1), backoff_cap)`` seconds,
    where ``attempt`` is the 1-indexed number of the call that just
    raised. On budget exhaustion for either bucket, the last underlying
    exception is wrapped into ``PanelProviderError(model, attempts,
    last_error)``. Non-retryable exceptions are wrapped into
    ``PanelProviderError`` with ``attempts=1``.
    """
    rate_limit_used = 0
    transient_used = 0
    total_attempts = 0

    while True:
        total_attempts += 1
        try:
            return fn()
        except RateLimitError as exc:
            rate_limit_used += 1
            if rate_limit_used >= rate_limit_attempts:
                raise PanelProviderError(
                    model=model,
                    attempts=total_attempts,
                    last_error=str(exc),
                ) from exc
            _sleep_backoff(total_attempts, backoff_base, backoff_cap)
        except TransientError as exc:
            transient_used += 1
            if transient_used >= transient_attempts:
                raise PanelProviderError(
                    model=model,
                    attempts=total_attempts,
                    last_error=str(exc),
                ) from exc
            _sleep_backoff(total_attempts, backoff_base, backoff_cap)
        except Exception as exc:
            raise PanelProviderError(
                model=model,
                attempts=1,
                last_error=str(exc),
            ) from exc


def _sleep_backoff(attempt: int, base: float, cap: float) -> None:
    delay = min(base * (2 ** (attempt - 1)), cap)
    time.sleep(delay)
