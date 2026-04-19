"""Structural enforcement of the SDK-free import invariant.

Importing ``megalos_panel.adapters`` must not transitively import ``anthropic``
or ``openai``. Adapter modules (``megalos_panel.adapters.claude``,
``.openai``, and ``.groq``) do import their SDK at module top, but they are
only loaded when ``dispatch()`` resolves a matching prefix. Consumers that
only need ``Adapter``, ``ADAPTERS``, or ``dispatch()`` itself can install the
bare ``megalos`` package without the ``[panel]`` extras.

The check runs in a fresh subprocess because pytest's own suite almost
certainly has the SDKs in ``sys.modules`` already — in-process inspection
would measure suite state, not import-surface state.
"""

import subprocess
import sys


def test_adapters_import_is_sdk_free() -> None:
    script = (
        "import sys\n"
        "import megalos_panel.adapters  # noqa: F401\n"
        "sdks = [m for m in ('anthropic', 'openai') if m in sys.modules]\n"
        "assert not sdks, f'adapters package transitively imported: {sdks}'\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"SDK-free invariant failed.\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )


def test_groq_adapter_does_not_import_anthropic() -> None:
    """The Groq adapter module reuses the openai SDK; it must not pull in anthropic."""
    script = (
        "import sys\n"
        "import megalos_panel.adapters.groq  # noqa: F401\n"
        "assert 'anthropic' not in sys.modules, (\n"
        "    f'groq adapter transitively imported anthropic'\n"
        ")\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"Groq adapter SDK isolation failed.\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )
