"""Regression guard for M002/S01/T02 audit: importing megalos_server must NOT
create server/megalos_sessions.db or open a thread-local DB connection.
Locks the import-hermeticity invariant into the suite so a later change that
adds an import-time db._get_conn() call (workspace pollution under coverage
runs, flaky test isolation) fails loudly.

Additionally covers the megalos_server <-> megalos_panel module boundary:
server source must never import the panel module (zero-LLM-imports invariant
on the core runtime), and shared tests/ files must not mix both universes
(prevents the fixtures-leak path where a panel test accidentally loads server
state or vice versa)."""
import ast
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB = REPO_ROOT / "server" / "megalos_sessions.db"
SERVER_SRC = REPO_ROOT / "megalos_server"
TESTS_DIR = REPO_ROOT / "tests"


def test_clean_import_is_hermetic():
    """Fresh subprocess import — no default-path DB file, no TLS connection.
    Subprocess bypasses conftest's MEGALOS_DB_PATH override, exercising the
    real default-path code path a production user would hit."""
    DEFAULT_DB.unlink(missing_ok=True)
    env = {k: v for k, v in os.environ.items() if k != "MEGALOS_DB_PATH"}
    script = (
        "import os, megalos_server, megalos_server.db, megalos_server.state;"
        f"assert not os.path.exists(r'{DEFAULT_DB}'), 'default DB created at import time';"
        "assert getattr(megalos_server.db._tls, 'conn', None) is None, 'TLS conn opened at import time';"
        "print('OK')"
    )
    r = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True, text=True, env=env, cwd=str(REPO_ROOT),
    )
    assert r.returncode == 0, f"stderr: {r.stderr}\nstdout: {r.stdout}"
    assert not DEFAULT_DB.exists(), "default-path DB appeared after subprocess import"


def _module_roots(path: Path) -> set[str]:
    """Parse a Python file and return the top-level module names it imports.

    Example: ``from megalos_panel.types import X`` -> {"megalos_panel"};
    ``import megalos_server.db`` -> {"megalos_server"}. Syntax errors or
    unreadable files surface as an explicit test failure, not a silent pass.
    """
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                roots.add(alias.name.split(".", 1)[0])
        elif isinstance(node, ast.ImportFrom):
            # Skip relative imports (node.module is None or node.level > 0).
            if node.level == 0 and node.module:
                roots.add(node.module.split(".", 1)[0])
    return roots


def test_server_source_does_not_import_panel():
    """Assertion A: no file under megalos_server/ imports megalos_panel.

    Preserves the zero-LLM-imports invariant on the core runtime — the server
    module must be installable and runnable without the [panel] extras.
    """
    offenders: list[str] = []
    for py in SERVER_SRC.rglob("*.py"):
        if "megalos_panel" in _module_roots(py):
            offenders.append(str(py.relative_to(REPO_ROOT)))
    assert not offenders, (
        "megalos_server source must not import megalos_panel "
        "(zero-LLM-imports invariant on core runtime). Offending files: "
        f"{offenders}"
    )


def test_tests_do_not_cross_server_panel_boundary():
    """Assertion B: no test_*.py file imports both megalos_server and
    megalos_panel. Additionally, test_panel_*.py files must not import
    megalos_server at all.

    Rationale: shared fixtures that reach across the boundary create a leak
    path where a panel test accidentally exercises server state, or a server
    test pulls in provider-SDK import cost. Either direction erodes the
    module-boundary guarantee. Scanning per test file is the mechanical
    enforcement; conftest.py is exempt because pytest requires it to be
    shared.
    """
    mixed: list[str] = []
    panel_importing_server: list[str] = []
    for py in TESTS_DIR.rglob("test_*.py"):
        rel = str(py.relative_to(REPO_ROOT))
        roots = _module_roots(py)
        imports_server = "megalos_server" in roots
        imports_panel = "megalos_panel" in roots
        if py.name.startswith("test_panel_"):
            if imports_server:
                panel_importing_server.append(rel)
        elif imports_server and imports_panel:
            mixed.append(rel)
    assert not mixed, (
        "test files must not import both megalos_server and megalos_panel "
        "(fixtures-leak path across the module boundary). Offending files: "
        f"{mixed}"
    )
    assert not panel_importing_server, (
        "test_panel_*.py files must not import megalos_server "
        "(panel tests exercise panel only). Offending files: "
        f"{panel_importing_server}"
    )
