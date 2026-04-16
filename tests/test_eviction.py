"""Tests for total-session cap eviction in create_session."""

import logging
from datetime import datetime, timedelta, timezone

import pytest  # type: ignore[import-not-found]

from megalos_server import db, state


@pytest.fixture(autouse=True)
def fresh_db(monkeypatch):
    monkeypatch.setenv("MEGALOS_DB_PATH", ":memory:")
    monkeypatch.setenv("MEGALOS_SESSION_CAP", "3")
    db._reset_for_test()
    yield
    db._reset_for_test()


def _iso_ago(hours: float) -> str:
    return (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()


def test_cap_evicts_oldest_completed_first():
    # s1 completed and old; s2, s3 active.
    s1 = state.create_session("wf")
    state.update_session(s1, current_step=state.COMPLETE)
    state._set_completed_at_for_test(s1, _iso_ago(10))
    state._set_updated_at_for_test(s1, _iso_ago(10))

    s2 = state.create_session("wf", current_step="step1")
    state._set_updated_at_for_test(s2, _iso_ago(5))

    s3 = state.create_session("wf", current_step="step1")
    state._set_updated_at_for_test(s3, _iso_ago(1))

    s4 = state.create_session("wf", current_step="step1")

    ids = {row["session_id"] for row in state.list_sessions()}
    assert s1 not in ids  # oldest completed — evicted
    assert s2 in ids
    assert s3 in ids
    assert s4 in ids


def test_cap_falls_through_to_active_when_no_completed():
    # All three active; no completed pool, so oldest active gets evicted.
    s1 = state.create_session("wf", current_step="step1")
    state._set_updated_at_for_test(s1, _iso_ago(10))

    s2 = state.create_session("wf", current_step="step1")
    state._set_updated_at_for_test(s2, _iso_ago(5))

    s3 = state.create_session("wf", current_step="step1")
    state._set_updated_at_for_test(s3, _iso_ago(1))

    s4 = state.create_session("wf", current_step="step1")

    ids = {row["session_id"] for row in state.list_sessions()}
    assert s1 not in ids  # oldest active — evicted
    assert s2 in ids
    assert s3 in ids
    assert s4 in ids


def test_cap_eviction_emits_log_line(caplog):
    # Fill to cap with active sessions of distinguishable ages.
    s1 = state.create_session("wf", current_step="step1")
    state._set_updated_at_for_test(s1, _iso_ago(10))
    state.create_session("wf", current_step="step1")
    state.create_session("wf", current_step="step1")

    with caplog.at_level(logging.INFO, logger="megalos_server.state"):
        state.create_session("wf", current_step="step1")

    evict_records = [
        r for r in caplog.records if getattr(r, "event", None) == "session_eviction"
    ]
    assert len(evict_records) == 1
    rec = evict_records[0]
    assert rec.reason == "cap_exceeded"
    assert rec.count == 1
    assert rec.session_cap == 3
    assert s1 in rec.session_ids
