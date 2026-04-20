"""Client-side rate-limit throttling for panel_query.

Provider rate limits are enforced at ingress with 429 responses. The retry
layer recovers from individual 429s with exponential backoff, but it cannot
beat steady overshoot — a long run against Groq free-tier ceilings burns
through the daily token budget on every RPS violation. Throttle enforces
published RPS + TPM bounds client-side so calls fit under the limits.

    throttle = Throttle(max_rps=25, max_tpm=10000)
    results = panel_query(requests, throttle=throttle)

Either bound can be None (ignored). ``acquire(estimated_tokens)`` blocks
until both the 1-second RPS window and the 60-second TPM window have room
for the next call. Events older than their window are pruned on every
acquire — the throttle has no memory beyond the live windows.
"""

from __future__ import annotations

import threading
import time
from collections import deque

_RESPONSE_TOKEN_ALLOWANCE = 100
_CHARS_PER_TOKEN = 4


def estimate_tokens(prompt: str, response_allowance: int = _RESPONSE_TOKEN_ALLOWANCE) -> int:
    """Rough token estimate: prompt chars/4 plus a flat response allowance.

    Good enough for rate-limit throttling, where the 60-second TPM window
    absorbs small estimate errors. Not accurate enough for billing or
    context-window computation.
    """
    return max(1, len(prompt) // _CHARS_PER_TOKEN) + response_allowance


class Throttle:
    """Thread-safe rolling-window throttle for RPS and TPM ceilings."""

    def __init__(
        self,
        *,
        max_rps: float | None = None,
        max_tpm: int | None = None,
    ) -> None:
        self.max_rps = max_rps
        self.max_tpm = max_tpm
        self._lock = threading.Lock()
        self._calls: deque[float] = deque()
        self._tokens: deque[tuple[float, int]] = deque()

    def acquire(self, estimated_tokens: int = 0) -> None:
        """Block until a call can proceed; record the event on admission."""
        while True:
            with self._lock:
                now = time.monotonic()
                self._prune(now)
                wait = self._wait_needed(now, estimated_tokens)
                if wait <= 0:
                    self._calls.append(now)
                    if estimated_tokens > 0:
                        self._tokens.append((now, estimated_tokens))
                    return
            time.sleep(wait)

    def _prune(self, now: float) -> None:
        while self._calls and now - self._calls[0] > 1.0:
            self._calls.popleft()
        while self._tokens and now - self._tokens[0][0] > 60.0:
            self._tokens.popleft()

    def _wait_needed(self, now: float, estimated_tokens: int) -> float:
        wait = 0.0
        if self.max_rps is not None and len(self._calls) >= self.max_rps:
            wait = max(wait, 1.0 - (now - self._calls[0]) + 0.01)
        if self.max_tpm is not None and estimated_tokens > 0:
            # Single-call overshoot: admit anyway, caller eats any 429 via retry.
            if estimated_tokens > self.max_tpm:
                return wait
            current = sum(t for _, t in self._tokens)
            if current + estimated_tokens > self.max_tpm:
                oldest = self._tokens[0][0] if self._tokens else now
                wait = max(wait, 60.0 - (now - oldest) + 0.01)
        return wait
