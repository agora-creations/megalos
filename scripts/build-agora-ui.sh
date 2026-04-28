#!/usr/bin/env bash
# Build the agorá UI bundle from a pinned agora-ui SHA and stage it as
# Python package data under megalos_server/static_ui/.
#
# Per ADR D063: pinned-SHA build hook + sdist also ships built UI. The
# published wheel and sdist include the pre-built bundle so PyPI users
# do not need Node installed.
#
# Migration trigger: when this step exceeds ~2 min on CI, or when an
# enterprise deployment needs offline builds, swap the clone+npm path
# for downloading a tarball from a GitHub Releases artifact pinned by
# the same SHA.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION_FILE="${REPO_ROOT}/agora-ui-version.txt"
CHECKOUT_DIR="${REPO_ROOT}/build/agora-ui-checkout"
STATIC_DIR="${REPO_ROOT}/megalos_server/static_ui"
AGORA_UI_REPO="${AGORA_UI_REPO:-https://github.com/agora-creations/agora-ui.git}"

# --- Node 20+ guard ---------------------------------------------------------
if ! command -v node >/dev/null 2>&1; then
  echo "error: node not found on PATH; install Node 20+ to build the agorá UI bundle" >&2
  exit 1
fi

NODE_VERSION_RAW="$(node --version)"      # e.g. "v20.11.1"
NODE_MAJOR="${NODE_VERSION_RAW#v}"
NODE_MAJOR="${NODE_MAJOR%%.*}"
if [[ -z "${NODE_MAJOR}" || "${NODE_MAJOR}" -lt 20 ]]; then
  echo "error: Node 20+ required; found ${NODE_VERSION_RAW}" >&2
  exit 1
fi

# --- Pinned SHA -------------------------------------------------------------
if [[ ! -f "${VERSION_FILE}" ]]; then
  echo "error: ${VERSION_FILE} missing" >&2
  exit 1
fi
SHA="$(tr -d '[:space:]' < "${VERSION_FILE}")"
if [[ -z "${SHA}" ]]; then
  echo "error: agora-ui-version.txt is empty" >&2
  exit 1
fi

echo "==> agora-ui pinned SHA: ${SHA}"
echo "==> Node: ${NODE_VERSION_RAW}"

# --- Idempotent reset -------------------------------------------------------
rm -rf "${STATIC_DIR}"
mkdir -p "$(dirname "${CHECKOUT_DIR}")"

# --- Clone + checkout pinned SHA -------------------------------------------
# Escape hatch for CI: when AGORA_UI_SKIP_CLONE=1, skip the clone+checkout
# and trust that ${CHECKOUT_DIR} is already populated at the right SHA by
# an upstream step (e.g. actions/checkout in the smoke-wheel CI job, which
# uses the workflow's GITHUB_TOKEN to read the private agora-ui repo).
# Local + dev paths leave this unset and clone fresh.
if [[ "${AGORA_UI_SKIP_CLONE:-0}" == "1" ]]; then
  if [[ ! -d "${CHECKOUT_DIR}" ]]; then
    echo "error: AGORA_UI_SKIP_CLONE=1 but ${CHECKOUT_DIR} missing" >&2
    exit 1
  fi
  ACTUAL_SHA="$(git -C "${CHECKOUT_DIR}" rev-parse HEAD)"
  if [[ "${ACTUAL_SHA}" != "${SHA}" ]]; then
    echo "error: pre-staged checkout at SHA ${ACTUAL_SHA}, expected ${SHA}" >&2
    exit 1
  fi
  echo "==> Using pre-staged checkout at ${CHECKOUT_DIR}"
else
  rm -rf "${CHECKOUT_DIR}"
  echo "==> Cloning ${AGORA_UI_REPO}"
  git clone --quiet "${AGORA_UI_REPO}" "${CHECKOUT_DIR}"
  git -C "${CHECKOUT_DIR}" checkout --quiet "${SHA}"
fi

# --- Install + build --------------------------------------------------------
echo "==> npm ci"
( cd "${CHECKOUT_DIR}" && npm ci --no-audit --no-fund )

echo "==> npm run build"
( cd "${CHECKOUT_DIR}" && npm run build )

if [[ ! -d "${CHECKOUT_DIR}/dist" ]]; then
  echo "error: agora-ui build produced no dist/ directory" >&2
  exit 1
fi

# --- Stage as package data -------------------------------------------------
mkdir -p "${STATIC_DIR}"
cp -R "${CHECKOUT_DIR}/dist/." "${STATIC_DIR}/"

if [[ ! -f "${STATIC_DIR}/index.html" ]]; then
  echo "error: ${STATIC_DIR}/index.html missing after copy" >&2
  exit 1
fi

BUNDLE_BYTES="$(du -sk "${STATIC_DIR}" | awk '{print $1}')"
echo "==> agora-ui bundle staged: ${STATIC_DIR} (${BUNDLE_BYTES} KiB, SHA ${SHA})"
