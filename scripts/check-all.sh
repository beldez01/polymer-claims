#!/usr/bin/env bash
#
# check-all.sh — local "is everything green" gate for polymer-claims.
#
# WHAT: runs every test + lint suite (umbrella, grammar, protocol, the
#       load-bearing grammar isolation invariant) plus the viewer
#       typecheck + build, in order, with section headers. Exits non-zero
#       on the FIRST failure; prints "ALL GREEN" only if everything passes.
#
# WHY:  this repo has no working CI. The GitHub account is flagged, which
#       suppresses GitHub Actions account-wide, so server-side CI is
#       impossible. This script is the manual substitute — run it before
#       committing/handing off to confirm the tree is healthy.
#
# usage: bash scripts/check-all.sh
#
set -euo pipefail

ROOT=/Users/zbb2/Desktop/polymer-claims

echo "== root (umbrella) =="
cd "$ROOT" && uv run --project . pytest tests/ -q && uv run --project . ruff check src tests

echo "== grammar =="
cd "$ROOT/grammar" && uv run pytest -q && uv run ruff check src tests

echo "== protocol =="
cd "$ROOT/protocol" && uv run pytest -q && uv run ruff check src tests

echo "== grammar isolation =="
cd "$ROOT/grammar" && uv run pytest tests/test_isolation.py -q

echo "== viewer =="
cd "$ROOT/viewer" && npm run typecheck && npm run build

echo "ALL GREEN"
