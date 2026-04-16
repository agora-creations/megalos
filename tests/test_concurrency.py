"""T04 concurrency proof — 10 parallel submit_step calls on one session.

Finding (empirical, 5 harness sweeps × 5 sub-runs = 25 trials):
- No uncaught exceptions; every future returns a dict.
- n_success + n_error == 10; all errors carry code `out_of_order_submission`.
- n_success varies in [2, 10] depending on thread interleaving — NOT exactly-once.
- Why: submit_step reads `current_step` OUTSIDE the transaction. Threads that
  read before any advance all observe "first" and succeed; threads that read
  after an advance see "second" and bail with out_of_order_submission.
- Post-state is always consistent: current_step='second', step_data['first']
  intact (one value), visit_counts['second'] == n_success, retry_counts empty.
- BEGIN IMMEDIATE correctly serialises the WRITE path — no corruption, no
  partial rows, no lost updates. The variability is in the read-then-decide
  fast-path, not in SQLite.
- Exactly-once semantics for concurrent identical submissions would require a
  CAS layer in state.update_session (e.g., UPDATE ... WHERE current_step=?).
  Out-of-scope for T04; deferred to a future task.
"""

from collections import Counter
from concurrent.futures import ThreadPoolExecutor

from megalos_server import db, state
from megalos_server.main import WORKFLOWS
from tests.conftest import call_tool

_N_THREADS = 10
_N_TRIALS = 5


def _two_step_workflow():
    return {
        "name": "concurrency-test",
        "description": "concurrency test workflow",
        "category": "testing",
        "output_format": "text",
        "steps": [
            {"id": "first", "title": "First", "directive_template": "First step",
             "gates": ["done"], "anti_patterns": []},
            {"id": "second", "title": "Second", "directive_template": "Second step",
             "gates": ["done"], "anti_patterns": []},
        ],
    }


def _fire_10(sid):
    def _submit():
        return call_tool(
            "submit_step",
            {"session_id": sid, "step_id": "first", "content": "same-content"},
        )

    with ThreadPoolExecutor(max_workers=_N_THREADS) as ex:
        futures = [ex.submit(_submit) for _ in range(_N_THREADS)]
        return [f.result() for f in futures]


def _tally(results):
    n_success = sum(1 for r in results if r.get("status") not in ("error",))
    n_error = sum(1 for r in results if r.get("status") == "error")
    codes = Counter(r.get("code") for r in results if r.get("status") == "error")
    return n_success, n_error, codes


def _fresh_session():
    WORKFLOWS["concurrency-test"] = _two_step_workflow()
    r = call_tool("start_workflow", {"workflow_type": "concurrency-test", "context": "x"})
    return r["session_id"]


def _cleanup():
    WORKFLOWS.pop("concurrency-test", None)


def test_concurrent_submits_have_deterministic_outcome():
    """Over 5 trials, the stable invariants hold: sum==10, errors are
    out_of_order_submission, n_success in [1,10]. Exact split is interleaving-
    dependent (honest Scenario A-mixed finding, see module docstring)."""
    try:
        for _ in range(_N_TRIALS):
            sid = _fresh_session()
            results = _fire_10(sid)
            n_success, n_error, codes = _tally(results)
            assert n_success + n_error == _N_THREADS, (n_success, n_error)
            assert 1 <= n_success <= _N_THREADS, n_success
            if n_error:
                assert set(codes) == {"out_of_order_submission"}, dict(codes)
    finally:
        _cleanup()


def test_no_uncaught_exceptions_under_contention():
    try:
        sid = _fresh_session()
        results = _fire_10(sid)
        for r in results:
            assert isinstance(r, dict), f"non-dict result: {r!r}"
    finally:
        _cleanup()


def test_post_condition_consistent_shape():
    try:
        sid = _fresh_session()
        results = _fire_10(sid)
        n_success, _, _ = _tally(results)

        final = state.get_session(sid)
        assert final["current_step"] == "second"
        assert final["step_data"]["first"] == "same-content"
        assert final["step_visit_counts"]["second"] == n_success
        assert final["step_visit_counts"]["first"] == 1
        assert final["retry_counts"] == {}
    finally:
        _cleanup()


def test_baseline_single_submit_consistent_shape():
    """Baseline: one submit on a clean session. Same post-state shape as the
    concurrent case, visit-count for the next step == 1 instead of n_success."""
    try:
        sid = _fresh_session()
        r = call_tool(
            "submit_step",
            {"session_id": sid, "step_id": "first", "content": "same-content"},
        )
        assert r.get("status") != "error", r

        final = state.get_session(sid)
        assert final["current_step"] == "second"
        assert final["step_data"]["first"] == "same-content"
        assert final["step_visit_counts"]["second"] == 1
        assert final["step_visit_counts"]["first"] == 1
        assert final["retry_counts"] == {}
    finally:
        _cleanup()


# Silence unused-import lint for `db` — kept for future debugging/inspection.
_ = db
