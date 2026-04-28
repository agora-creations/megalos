# megalos-server dev-workflow targets (D065 — three-layer dev workflow).
#
# This Makefile is a developer convenience for the three-layer loop:
#
#   Layer 1 — Vite cross-origin (fastest iteration):
#       (in agora-ui)    npm run dev
#       (in megalos)     MEGALOS_DEV_CORS=true uv run python megalos_server/main.py
#
#   Layer 2 — Source-tree production-shape:
#       make dev-ui                    # build agorá UI bundle into static_ui/
#       uv run python megalos_server/main.py
#       open http://localhost:8000/
#
#   Layer 3 — Clean-venv wheel smoke (CI parity):
#       make smoke-wheel               # build wheel, install in tempdir venv, assert.
#
# Production deploys install the published wheel from PyPI; this Makefile is
# NOT used in production. See docs/CONFIGURATION.md for details.

.PHONY: dev-ui smoke-wheel

dev-ui:
	bash scripts/build-agora-ui.sh
	@echo ""
	@echo "==> agorá UI bundle staged at megalos_server/static_ui/."
	@echo "    Restart megalos-server (uv run python megalos_server/main.py) to pick up changes."

smoke-wheel:
	bash scripts/smoke-wheel.sh
