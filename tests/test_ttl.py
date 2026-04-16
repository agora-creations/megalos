"""Tests for two-clause TTL expiry in expire_sessions."""

import logging
from datetime import datetime, timedelta, timezone

import pytest  # type: ignore[import-not-found]

from megalos_server import db, state


@pytest.fixture(autouse=True)
def fresh_db(monkeypatch):
    monkeypatch.setenv("MEGALOS_DB_PATH", ":memory:")
    monkeypatch.setenv("MEGALOS_SESSION_CAP", "10")
    db._reset_for_test()
    yield
    db._reset_for_test()


def _iso_ago(hours: float) -> str:
    return (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()


def test_expire_ttl_active_uses_updated_at(caplog):
    sid = state.create_session("wf", current_step="step1")
    state._set_updated_at_for_test(sid, _iso_ago(25))

    with caplog.at_level(logging.INFO, logger="megalos_server.state"):
        expired = state.expire_sessions(ttl_hours=24)

    assert sid in expired
    assert state.list_sessions() == []
    evict_records = [
        r for r in caplog.records if getattr(r, "event", None) == "session_eviction"
    ]
    assert len(evict_records) == 1
    assert evict_records[0].reason == "ttl_expired"
    assert evict_records[0].ttl_hours == 24


def test_expire_ttl_completed_uses_completed_at():
    # Completed session with fresh updated_at but stale completed_at.
    sid = state.create_session("wf")
    state.update_session(sid, current_step=state.COMPLETE)
    # Fresh updated_at (just stamped by update_session), stale completed_at.
    state._set_completed_at_for_test(sid, _iso_ago(25))
    # Keep updated_at fresh: do NOT backdate it. The two-clause SQL must pick
    # this row via the completed_at clause.
    expired = state.expire_sessions(ttl_hours=24)
    assert sid in expired


def test_expire_keeps_fresh(caplog):
    active = state.create_session("wf", current_step="step1")
    completed = state.create_session("wf")
    state.update_session(completed, current_step=state.COMPLETE)

    with caplog.at_level(logging.INFO, logger="megalos_server.state"):
        expired = state.expire_sessions(ttl_hours=24)

    assert expired == []
    ids = {row["session_id"] for row in state.list_sessions()}
    assert active in ids
    assert completed in ids
    evict_records = [
        r for r in caplog.records if getattr(r, "event", None) == "session_eviction"
    ]
    assert evict_records == []
