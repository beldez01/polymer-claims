#!/usr/bin/env bash
# Single source of truth for the FormalClaim JSON Schema is the corpus copy.
# This script copies it into the distributed plugin and verifies no drift.
# Usage: scripts/sync_schema.sh [--check]
#   (no args) copy corpus schema -> plugin schema
#   --check   fail (exit 1) if the two differ, without copying
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CANON="$ROOT/corpus/schema/formal_claim_v1.2.schema.json"
PLUGIN="$ROOT/plugins/claim-harness/schemas/formal_claim_v1.2.json"

if [[ "${1:-}" == "--check" ]]; then
  if diff -q "$CANON" "$PLUGIN" >/dev/null; then
    echo "schema in sync"
  else
    echo "ERROR: plugin schema drifted from corpus canonical. Run scripts/sync_schema.sh." >&2
    exit 1
  fi
else
  cp "$CANON" "$PLUGIN"
  echo "synced $CANON -> $PLUGIN"
fi
