# Gap-ledger precision — `gap_kind` dedup + canonical registry (design)

**Status:** approved (brainstorm 2026-07-12). Small self-contained cleanup of `aggregate_gaps`.

## Problem

`src/polymer_claims/synbio/gap_ledger.py::aggregate_gaps` has two defects, both surfaced during the synbio ramp:
1. **Dedup on prose.** It keys on `(expansion_class, constraint)` free text, so five differently-worded records of the *same* strain never collapse — 11 raw gaps → 11 "canonical" (zero merge). The interval family (floor/range/one-sided-bound) is one strain phrased five ways.
2. **No reconciliation with the canonical numbering.** It renumbers from `start_index=5` without regard to the established gap-log numbers, so the interval strain surfaced as new GAP-5/6/9/10/12 rather than the pre-existing GAP-3, and re-running today would renumber the six survivors GAP-5…10 instead of their real 7/8/11/13/14/15.

The "fixed list" is only as fixed as the wording.

## Fix

**1. Controlled `gap_kind` tag.** Add optional `gap_kind: str | None = None` to `SchemaFit`
(`src/polymer_claims/synbio/manifest.py`). The extractor assigns a short controlled tag; dedup keys on it.

**2. Canonical registry** in `gap_ledger.py` — the source of truth for kind → stable number:

```python
CANONICAL_GAP_KINDS: dict[str, str] = {
    "reported-quantity-pattern":    "GAP-1",
    "context-conditioning":         "GAP-2",
    "interval-bound":               "GAP-3",   # unifies old GAP-5/6/9/10/12
    "reported-defeater-provisional":"GAP-4",
    "analytic-basis":               "GAP-7",
    "gene-locus-context":           "GAP-8",
    "stratification":               "GAP-11",
    "endpoint-type":                "GAP-13",
    "composite-quantity":           "GAP-14",
    "categorical-mapping":          "GAP-15",
}
```

**3. New `aggregate_gaps` behavior:**
- Skip non-gap entries (unchanged).
- Dedup key: the normalized `gap_kind` when present; else the legacy prose key `(expansion_class, constraint)`.
- Numbering: a recognized `gap_kind` gets its **stable** `CANONICAL_GAP_KINDS[kind]` (same number regardless of how many entries carry it or how they're worded). An untagged or unrecognized-kind gap gets the next free sequential number, computed as `max(canonical numbers, start_index-1) + 1` and incremented per new key — so it never collides with a canonical number.
- `GapRecord` gains a `gap_kind: str | None` field (records the tag that keyed it).

**4. Re-tag the six surviving manifest gap entries** with `gap_kind` so the new path engages:

| entry | gap_kind | → |
|---|---|---|
| sb-plm03-snv-two-bits | `analytic-basis` | GAP-7 |
| sb-plm03-tet2-truncating-fraction | `gene-locus-context` | GAP-8 |
| sb-plm06-hla-loh-prevalence | `stratification` | GAP-11 |
| sb-plm08-ckit-lnp-hspc-transfection | `endpoint-type` | GAP-13 |
| sb-plm08-lnp-four-component-molar-ratio | `composite-quantity` | GAP-14 |
| sb-plm08-sort-lipid-biodistribution | `categorical-mapping` | GAP-15 |

After re-tagging, `aggregate_gaps` over the real manifests returns exactly GAP-7/8/11/13/14/15 — matching the gap-log doc.

## Backward-compat

`gap_kind` defaults `None`; an untagged gap dedups via the legacy prose key and numbers sequentially. The
change is additive to `SchemaFit` and byte-safe for existing manifests (they omit the key). Note: `gap_kind` is
`schema_fit` metadata — it is NOT part of the built `Claim`, so **no universe regeneration is needed** and no
claim serialization changes.

## Invariants

- `grammar/` and `protocol/` untouched. `Corpus` stays 4. Umbrella-side only.
- No change to built claims, leaf serialization, or the merged universe.

## Scope / tasks

1. `SchemaFit.gap_kind` field + `gap_ledger.py` registry & new `aggregate_gaps` + rewritten `test_gap_ledger.py`.
2. Re-tag the six manifest entries + an integration test (real manifests → the six canonical ids, deduped) + gap-log doc note + continuity.
