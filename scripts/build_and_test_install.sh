#!/usr/bin/env bash
# Local build + test-install harness for the polymer-claims umbrella.
#
# Builds the three distributions (grammar, protocol, umbrella) into wheels, then
# installs ALL THREE wheels TOGETHER into a throwaway venv from local files (NOT
# PyPI) and runs the installed console-script smokes. NO publish.
#
# Acceptance: `polymer-claims version`, `... validate <valid claim>`, and
# `... loop <small corpus> --budget 100` all succeed and the loop licenses >=1 claim.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FIXTURES="${REPO_ROOT}/tests/fixtures"
VALID_CLAIM="${FIXTURES}/valid_claim.json"
SMALL_CORPUS="${FIXTURES}/small_corpus.json"

VENV_DIR="$(mktemp -d "${TMPDIR:-/tmp}/polymer-claims-testinstall.XXXXXX")"

cleanup() {
  rm -rf "${VENV_DIR}"
}
trap cleanup EXIT

echo "==> repo root: ${REPO_ROOT}"

# ---------------------------------------------------------------------------
# (a) build all three wheels
# ---------------------------------------------------------------------------
for pkg in grammar protocol .; do
  echo "==> uv build (${pkg})"
  ( cd "${REPO_ROOT}/${pkg}" && uv build --wheel )
done

newest_wheel() {
  # newest .whl matching a glob in a dist dir
  ls -t "${REPO_ROOT}/$1/dist/"$2 2>/dev/null | head -n1
}

GRAMMAR_WHL="$(newest_wheel grammar 'polymer_grammar-*.whl')"
PROTOCOL_WHL="$(newest_wheel protocol 'polymer_protocol-*.whl')"
CLAIMS_WHL="$(newest_wheel . 'polymer_claims-*.whl')"

echo "==> grammar wheel:  ${GRAMMAR_WHL}"
echo "==> protocol wheel: ${PROTOCOL_WHL}"
echo "==> umbrella wheel: ${CLAIMS_WHL}"

for w in "${GRAMMAR_WHL}" "${PROTOCOL_WHL}" "${CLAIMS_WHL}"; do
  if [[ -z "${w}" || ! -f "${w}" ]]; then
    echo "ERROR: missing wheel: ${w}" >&2
    exit 1
  fi
done

# ---------------------------------------------------------------------------
# (b) throwaway venv + install the three local wheels together
# ---------------------------------------------------------------------------
echo "==> creating throwaway venv at ${VENV_DIR}"
uv venv "${VENV_DIR}" >/dev/null
PY="${VENV_DIR}/bin/python"
PCLAIMS="${VENV_DIR}/bin/polymer-claims"

echo "==> installing local wheels"
# Pass the THREE locally-built wheels explicitly so pip satisfies the
# polymer-* deps from these files (not PyPI). Third-party deps (pydantic) still
# resolve from the index — that is the only network resolution, and it is the
# correct one: we are NOT pulling any polymer-* package from PyPI.
uv pip install --python "${PY}" "${CLAIMS_WHL}" "${PROTOCOL_WHL}" "${GRAMMAR_WHL}"

# ---------------------------------------------------------------------------
# (c) installed console-script smokes
# ---------------------------------------------------------------------------
echo "==> smoke: version"
"${PCLAIMS}" version

echo "==> smoke: validate (valid claim)"
"${PCLAIMS}" validate "${VALID_CLAIM}"

echo "==> smoke: loop --budget 100 (must license >=1 claim)"
# stdout is now machine-clean JSON (the human `final status:` summary goes to
# stderr) — capture BOTH so the grep still sees the `licensed=1` summary line.
LOOP_OUT="$("${PCLAIMS}" loop "${SMALL_CORPUS}" --budget 100 2>&1)"
echo "${LOOP_OUT}"
if ! echo "${LOOP_OUT}" | grep -q "licensed=1"; then
  echo "ERROR: loop did not license >=1 claim" >&2
  exit 1
fi

# ---------------------------------------------------------------------------
# (d) done
# ---------------------------------------------------------------------------
echo "SUCCESS: polymer-claims installs from local wheels and the CLI works."
