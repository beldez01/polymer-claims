# Faithful v1.2 → v1.3 re-ingest — findings

Date: 2026-06-02
Status: diagnostic result (closes the loop on `2026-06-01-v12-ingestion-findings.md`)
Script: `grammar/scripts/reingest_v12.py` (run: `cd grammar && uv run python scripts/reingest_v12.py`)

## What this is

The original probe (`2026-06-01-v12-ingestion-findings.md`) only checked field *coverage* and
found `subject` homeless in 47/47 claims. Since then we built the `subject` slot (10-variant
union), L3 defeat/blame, L4 revision, and the online-FDR ledger. This re-ingest **actually maps**
each of the 47 v1.2 claims into a real v1.3 `Claim` — now including a mapped `Subject` — and
re-measures faithfulness. Reads v1.2 JSON as data only (isolation guard respected).

## Headline result

- **47/47 claims construct a v1.3 `Claim`.**
- **47/47 v1.2 subjects map into the v1.3 `Subject` slot (100%)** — the gap the first probe
  flagged is closed. Kinds: **39 cohort, 4 composite, 4 literal**. The recursive composites (whose
  parts are literal claim-references with `structured` dicts) map cleanly, exercising
  `CompositeSubject` + the `tuple[tuple[str,str],...]` literal-structured adaptation end-to-end on
  real data.

## Still-homeless v1.2 fields (data-driven next-build signal)

| field | count | destination |
|---|---|---|
| `premises` | 47/47 | provenance — **Phase 7 #1** (`generated_by`) + Phase 8 |
| `operations` | 47/47 | compute graph — **Phase 8 evaluator** |
| `external_assumptions` | 47/47 | Duhem auxiliaries — first-class node still TODO (L3 follow-up) |
| `depends_on` | 47/47 | corpus-level L3 defeat/equivalence edges (not a Claim field — fine) |
| `posted_at`/`version`/`exp_number`/`notebook` | 39–47/47 | provenance metadata — **Phase 7 #1** |
| `context` (assembly) | 47/47 | no slot (minor) |
| `domain` | 47/47 | replaced by pattern + profile (by design) |
| vector-valued statistics | **29** | **L0 vector-`Leaf`** (still unbuilt) |

## Reading / implications

1. **The subject slot delivered.** 100% of real subjects now have a faithful home, including the
   hardest case (recursive composites). The biggest fidelity gap is genuinely closed.
2. **The next data-driven priorities are now clear:**
   - **Provenance (Phase 7 #1 `generated_by`/`search_cardinality`)** would absorb `premises`,
     `posted_at`, `version`, `exp_number`, `notebook` — the largest remaining homeless cluster.
   - **vector-`Leaf` (L0)** would absorb the 29 array-valued statistics.
   - **`operations`** is genuinely Phase-8 (the evaluator/compute graph) — don't force it earlier.
   - **`external_assumptions`** wants a first-class Duhem-auxiliary node (the standing L3 follow-up).
3. **Pattern/estimand are still placeholders** — no claim→pattern classifier exists; a faithful
   ingest still fabricates `PatternRef(id="ingested_unknown")`. That's a protocol/CANONICALIZE
   concern, not a grammar field.

## Bottom line

Faithfulness jumped from "skeleton-only" to "skeleton + 100% of subjects." The remaining gaps are
exactly two grammar additions (provenance, vector-`Leaf`) plus the Phase-8 evaluator — the
re-ingest turns the next-build decision from guesswork into a ranked, evidence-backed list.
