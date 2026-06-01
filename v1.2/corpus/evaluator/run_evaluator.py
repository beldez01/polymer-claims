"""CI wrapper around `polymer_formalclaim.evaluate`.

Invoked by `.github/workflows/evaluate.yml`. Takes a list of changed
`domains/**/claims/*.json` files, validates each against the pinned
v1.2 JSON Schema, runs the evaluator, writes sibling `.evaluation.json`
files, and emits a machine-readable verdict payload on stdout.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from polymer_formalclaim import FormalClaim, evaluate


def _evaluate_one(path: Path, timeout_per_claim: int) -> dict:
    t0 = time.monotonic()
    try:
        claim = FormalClaim.model_validate(json.loads(path.read_text()))
    except Exception as exc:
        return {
            "slug": path.stem,
            "verdict": "REJECTED",
            "reason": "SCHEMA_INVALID",
            "error": f"{type(exc).__name__}: {exc}",
            "elapsed_s": round(time.monotonic() - t0, 3),
        }

    result = evaluate(claim)
    # Write sibling evaluation file so the PR carries a reviewable artifact.
    sibling = path.with_name(path.stem + ".evaluation.json")
    sibling.write_text(result.model_dump_json(indent=2) + "\n")

    elapsed = time.monotonic() - t0
    if elapsed > timeout_per_claim:
        return {
            "slug": path.stem,
            "verdict": "PENDING",
            "reason": "TIMEOUT_EXCEEDED",
            "elapsed_s": round(elapsed, 3),
        }
    return {
        "slug": path.stem,
        "verdict": result.verdict,
        "conjuncts_total": len(result.conjuncts),
        "conjuncts_true": sum(1 for c in result.conjuncts if c.result is True),
        "materialization_status": result.materialization_status,
        "evaluator_version": result.evaluator_version,
        "schema_version": result.schema_version,
        "elapsed_s": round(elapsed, 3),
    }


def _aggregate_verdict(results: list[dict]) -> str:
    """Any REJECTED → REJECTED; any PENDING → PENDING; else LICENSED."""
    if any(r["verdict"] == "REJECTED" for r in results):
        return "REJECTED"
    if any(r["verdict"] == "PENDING" for r in results):
        return "PENDING"
    return "LICENSED"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--files", required=True, help="Newline- or space-separated changed .json paths")
    parser.add_argument("--schema", required=False, help="Path to pinned JSON Schema (reserved for v0.3)")
    parser.add_argument("--json-out", required=True)
    parser.add_argument("--timeout-per-claim", type=int, default=60)
    args = parser.parse_args()

    raw = args.files.replace("\n", " ").strip()
    paths = [Path(p) for p in raw.split() if p.endswith(".json") and not p.endswith(".evaluation.json")]

    results: list[dict] = [_evaluate_one(p, args.timeout_per_claim) for p in paths]
    payload = {
        "aggregate_verdict": _aggregate_verdict(results) if results else "LICENSED",
        "results": results,
    }
    Path(args.json_out).write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps(payload, indent=2))
    # Exit 0 regardless of verdict — the workflow uses the JSON output to set
    # the status check. Non-zero here would fail the job prematurely.
    return 0


if __name__ == "__main__":
    sys.exit(main())
