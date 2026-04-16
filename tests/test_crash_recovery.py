"""Crash-recovery proof: SIGTERM mid-workflow, then re-read the session.

Two variants:
1. Round-trip via the parent's existing connection (warm read).
2. Cold reopen via db._reset_for_test() to exercise a parent-restart path.

Both ride the autouse `_isolated_db` fixture so the DB path is a tmp file.
The child subprocess is launched with the SAME MEGALOS_DB_PATH passed
explicitly via env=, so reader and writer bind to the identical file.
"""

import os
import signal
import subprocess
import sys

import pytest  # type: ignore[import-not-found]

from megalos_server import db, state

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_CHILD_SCRIPT = """
import sys, time
from megalos_server import state
sid = state.create_session("recovery_wf", current_step="first")
state.update_session(sid, step_data={"marker": "pre_crash"})
sys.stdout.write(sid + "\\n")
sys.stdout.flush()
time.sleep(60)
"""


def _spawn_child() -> subprocess.Popen:
    env = {**os.environ}
    return subprocess.Popen(
        [sys.executable, "-c", _CHILD_SCRIPT],
        cwd=REPO_ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def _read_sid_or_fail(child: subprocess.Popen) -> str:
    assert child.stdout is not None
    line = child.stdout.readline()
    if not line:
        child.kill()
        err = child.stderr.read() if child.stderr else ""
        pytest.fail(f"Child produced no session_id. stderr:\n{err}")
    return line.strip()


def _terminate_or_fail(child: subprocess.Popen) -> int:
    child.terminate()
    try:
        rc = child.wait(timeout=5)
    except subprocess.TimeoutExpired:
        child.kill()
        pytest.fail("Child did not exit within 5s of SIGTERM")
    return rc


def test_session_survives_sigterm_warm_read():
    child = _spawn_child()
    try:
        sid = _read_sid_or_fail(child)
        rc = _terminate_or_fail(child)
        # POSIX: signal-terminated processes report negative signal value.
        assert rc == -signal.SIGTERM, f"unexpected returncode {rc}"

        session = state.get_session(sid)
        assert session["session_id"] == sid
        assert session["workflow_type"] == "recovery_wf"
        assert session["current_step"] == "first"
        assert session["step_data"] == {"marker": "pre_crash"}

        ids = {row["session_id"] for row in state.list_sessions()}
        assert sid in ids
    finally:
        if child.poll() is None:
            child.kill()


def test_session_survives_sigterm_cold_reopen():
    """Same round-trip, but the parent closes its connection before reading
    so the read happens through a freshly-opened sqlite3 handle. Catches
    bugs where a warm WAL-aware reader sees data a cold opener cannot."""
    child = _spawn_child()
    try:
        sid = _read_sid_or_fail(child)
        rc = _terminate_or_fail(child)
        assert rc == -signal.SIGTERM

        # Force a cold reopen on the parent's thread-local connection.
        db._reset_for_test()

        session = state.get_session(sid)
        assert session["session_id"] == sid
        assert session["step_data"] == {"marker": "pre_crash"}
    finally:
        if child.poll() is None:
            child.kill()
