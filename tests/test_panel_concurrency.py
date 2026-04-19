"""Unit tests for megalos_panel.concurrency.fan_out.

Exercises the load-bearing contract: one PanelResult per input request
keyed by request_id, worker exceptions become PanelResult(error=...)
rather than propagating, and empty input returns an empty dict.
"""

from __future__ import annotations

from megalos_panel.concurrency import fan_out
from megalos_panel.types import PanelRequest, PanelResult


def _ok(req: PanelRequest) -> PanelResult:
    return PanelResult(
        selection=f"pick-{req.request_id}",
        raw_response=f"raw-{req.request_id}",
        error=None,
    )


def test_fan_out_returns_dict_keyed_by_request_id() -> None:
    reqs = [
        PanelRequest(prompt="a", model="claude-opus-4-7", request_id="r1"),
        PanelRequest(prompt="b", model="gpt-5", request_id="r2"),
        PanelRequest(prompt="c", model="claude-opus-4-7", request_id="r3"),
    ]
    out = fan_out(reqs, _ok, max_workers=4)
    assert set(out) == {"r1", "r2", "r3"}
    assert out["r1"].selection == "pick-r1"
    assert out["r2"].selection == "pick-r2"
    assert out["r3"].selection == "pick-r3"
    assert all(r.error is None for r in out.values())


def test_fan_out_empty_list_returns_empty_dict() -> None:
    assert fan_out([], _ok) == {}


def test_fan_out_worker_exception_becomes_panel_result_error() -> None:
    def boom(req: PanelRequest) -> PanelResult:
        raise RuntimeError(f"worker failed for {req.request_id}")

    reqs = [PanelRequest(prompt="x", model="gpt-5", request_id="r1")]
    out = fan_out(reqs, boom)
    assert set(out) == {"r1"}
    result = out["r1"]
    assert result.selection == ""
    assert result.raw_response == ""
    assert result.error is not None
    assert "worker failed for r1" in result.error


def test_fan_out_mixed_success_and_failure() -> None:
    def mixed(req: PanelRequest) -> PanelResult:
        if req.request_id == "bad":
            raise RuntimeError("nope")
        return PanelResult(selection="s", raw_response="r", error=None)

    reqs = [
        PanelRequest(prompt="a", model="claude-opus-4-7", request_id="ok1"),
        PanelRequest(prompt="b", model="claude-opus-4-7", request_id="bad"),
        PanelRequest(prompt="c", model="gpt-5", request_id="ok2"),
    ]
    out = fan_out(reqs, mixed)
    assert set(out) == {"ok1", "bad", "ok2"}
    assert out["ok1"].error is None
    assert out["ok2"].error is None
    assert out["bad"].error is not None
    assert "nope" in out["bad"].error
    assert out["bad"].selection == ""
    assert out["bad"].raw_response == ""


def test_fan_out_default_request_ids_round_trip() -> None:
    """Default request_id is a uuid4 hex; fan_out must use whichever id
    the request actually carries, not reassign."""
    reqs = [
        PanelRequest(prompt=f"p{i}", model="claude-opus-4-7") for i in range(3)
    ]
    out = fan_out(reqs, _ok)
    assert set(out) == {r.request_id for r in reqs}
    for r in reqs:
        assert out[r.request_id].selection == f"pick-{r.request_id}"


def test_fan_out_runs_all_requests() -> None:
    """Sanity check: N requests → N results; per_request_fn invoked N times."""
    call_count = 0

    def counting(req: PanelRequest) -> PanelResult:
        nonlocal call_count
        call_count += 1
        return PanelResult(selection="s", raw_response="r", error=None)

    reqs = [
        PanelRequest(prompt=f"p{i}", model="claude-opus-4-7", request_id=f"r{i}")
        for i in range(10)
    ]
    out = fan_out(reqs, counting, max_workers=4)
    assert len(out) == 10
    assert call_count == 10
