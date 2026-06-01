---
name: validate-claim
description: Use to run the FormalClaim evaluator locally on a draft. Returns LICENSED / REJECTED / PENDING with a machine-readable diagnostic. Call this before /submit-claim.
---

# Validate a FormalClaim

Runs the bundled evaluator (`polymer-formalclaim validate`) on a claim file and returns the verdict.

## Usage

```
/validate-claim ./claims/drafts/<slug>.json
```

Or, programmatically via the `claim-ir` MCP server's `evaluate_claim` tool.

## What happens

1. JSON Schema validation against `schemas/formal_claim_v1.2.json`. Any schema violation → **REJECTED** with `SCHEMA_INVALID`.
2. Inference-tree walk against pinned `Statistic.value`s. Three-valued logic:
   - All conjuncts true → **LICENSED**
   - Any conjunct false → **REJECTED** with `CONJUNCT_FALSE` + the failing path
   - Any conjunct null (missing stat, unresolved transform) → **PENDING**
3. (v0.2) Materialization mode — re-computes each `EstimatorOp` against the live Polymer API; drift reported; mode is `skipped_ineligible` unless every premise has `provenance_state ∈ {canonical_db, fly_postgres}`.

## Output shape

```json
{
  "verdict": "LICENSED" | "REJECTED" | "PENDING",
  "conjuncts": [ { "lhs_stat_id": "...", "op": "...", "rhs_value": 0.65, "result": true }, ... ],
  "materialization_status": "skipped_pinned_only" | "complete" | "partial" | "skipped_ineligible" | "error",
  "materialization_error": "... reason ..." | null,
  "reason_codes": ["CONJUNCT_FALSE", ...],
  "failing_conjuncts": [ { "path": "...", "fix_hint": "..." }, ... ]
}
```

## On REJECTED / PENDING

The output includes `reason_codes` and per-failing-conjunct `fix_hint`. For machine-autonomous fixes (schema typos, missing stat, stale api_version), the `author-claim` skill can iterate up to 3 rounds. After the budget is exhausted, page the user.

For substantive failures (`EFFECT_SIZE_BELOW_THRESHOLD`, `CONJUNCT_FALSE` on a pre-registered threshold), the claim is genuinely falsified. Either flag it as a null-result claim (`claim_type: null_result`) and re-submit — null results are first-class — or drop it.
