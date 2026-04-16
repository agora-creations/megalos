"""1000-cycle stress proof: bounded DB size, both eviction reasons fire, no raises.

Rides the autouse _isolated_db fixture for a tmp-path file-backed SQLite DB.
Forces eviction by setting MEGALOS_SESSION_CAP=50 and intermixing TTL sweeps
with backdated rows. Asserts row count, total on-disk footprint, and that
both `cap_exceeded` and `ttl_expired` log lines are emitted.
"""

import logging
import os

from megalos_server import db, state

CAP = 50
CYCLES = 1000
SIZE_LIMIT_BYTES = 5 * 1024 * 1024


def _db_footprint(path: str) -> int:
    return sum(
        os.path.getsize(p)
        for p in (path, path + "-wal", path + "-shm")
        if os.path.exists(p)
    )


def test_stress_bounded_growth_and_both_eviction_reasons(monkeypatch, caplog):
    monkeypatch.setenv("MEGALOS_SESSION_CAP", str(CAP))
    caplog.set_level(logging.INFO, logger="megalos_server.state")

    raised: list[BaseException] = []
    for i in range(CYCLES):
        try:
            sid = state.create_session("stress_wf", current_step="step1")
            if i % 2 == 0:
                # Drives completed-pool eviction priority.
                state.update_session(sid, current_step=state.COMPLETE)
            if i > 0 and i % 100 == 0:
                # Backdate a few rows so the TTL sweep has something to hit.
                for s in state.list_sessions()[:5]:
                    state._set_updated_at_for_test(
                        s["session_id"], "2020-01-01T00:00:00+00:00"
                    )
                    if s["status"] == "completed":
                        state._set_completed_at_for_test(
                            s["session_id"], "2020-01-01T00:00:00+00:00"
                        )
                state.expire_sessions(ttl_hours=1)
        except BaseException as exc:  # noqa: BLE001 - we want to surface anything
            raised.append(exc)

    assert raised == [], f"loop raised: {raised!r}"

    # 1. Row count bounded by cap.
    conn = db._get_conn()
    row_count = conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
    assert row_count <= CAP, f"row count {row_count} exceeds cap {CAP}"

    # 2. On-disk footprint bounded after a checkpoint.
    conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    db_path = os.environ["MEGALOS_DB_PATH"]
    footprint = _db_footprint(db_path)
    assert footprint < SIZE_LIMIT_BYTES, (
        f"DB grew to {footprint} bytes — eviction or checkpoint regressed"
    )

    # 3. Both eviction reasons must have fired at least once.
    reasons = [
        getattr(r, "reason", None)
        for r in caplog.records
        if getattr(r, "event", None) == "session_eviction"
    ]
    assert reasons.count("cap_exceeded") >= 1, "no cap_exceeded eviction logged"
    assert reasons.count("ttl_expired") >= 1, "no ttl_expired eviction logged"
