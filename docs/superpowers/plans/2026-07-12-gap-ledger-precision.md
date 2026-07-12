# Gap-ledger precision (`gap_kind` dedup + canonical registry) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Make `aggregate_gaps` dedup on a controlled `gap_kind` tag (not free-text prose) and assign stable canonical GAP-N via a registry, so the "fixed list" is actually fixed.

**Architecture:** Additive `gap_kind` field on `SchemaFit`; a `CANONICAL_GAP_KINDS` registry in `gap_ledger.py`; `aggregate_gaps` dedups on `gap_kind` (legacy prose fallback when absent) and numbers tagged gaps from the registry, untagged/unknown from a non-colliding sequential base. Umbrella-side only; no built-claim or universe change.

**Tech Stack:** Python 3.12, pydantic v2. Spec: `docs/superpowers/specs/2026-07-12-gap-ledger-precision-design.md`.

## Global Constraints

- `grammar/` and `protocol/` untouched, pure + numpy-free. `Corpus` stays 4. Umbrella-side only.
- `gap_kind` is `schema_fit` metadata — NOT part of the built `Claim`; **no universe regeneration**, no claim-serialization change.
- Additive + optional; existing manifests (no `gap_kind`) load unchanged and dedup via the legacy prose key.
- Test command: `cd /Users/zbb2/Desktop/polymer-claims && uv run --project . pytest tests/synbio/ -q`.

---

### Task 1: `SchemaFit.gap_kind` + registry + new `aggregate_gaps`

**Files:**
- Modify: `src/polymer_claims/synbio/manifest.py` (`SchemaFit`)
- Modify: `src/polymer_claims/synbio/gap_ledger.py`
- Test: `tests/synbio/test_gap_ledger.py` (rewrite for the new contract)

**Interfaces:**
- Produces: `SchemaFit.gap_kind: str | None`; `CANONICAL_GAP_KINDS: dict[str,str]`; `GapRecord.gap_kind: str | None`; `aggregate_gaps(entries, start_index=5) -> list[GapRecord]` (dedup on gap_kind, canonical numbering).

- [ ] **Step 1: Rewrite the test** (`tests/synbio/test_gap_ledger.py`) for the new contract:

```python
from polymer_claims.synbio.manifest import ManifestEntry
from polymer_claims.synbio.gap_ledger import aggregate_gaps, CANONICAL_GAP_KINDS


def _entry(id, status, constraint=None, cls=None, gap_kind=None):
    return ManifestEntry.model_validate({
        "id": id, "title": id, "tier": 1, "topic": "computing",
        "leaf": {"kind": "quantity"}, "source": "PLM-VI",
        "schema_fit": {"status": status, "constraint": constraint,
                       "expansion_class": cls, "gap_kind": gap_kind,
                       "current_ir_behavior": "x", "candidate_resolution": "y",
                       "purity_cost": "z"},
    })


def test_tagged_kinds_get_canonical_numbers_and_dedup_across_paraphrases():
    entries = [
        _entry("a", "clean"),
        _entry("b", "gap", "worded one way",     "domain",  gap_kind="analytic-basis"),
        _entry("c", "gap", "worded ANOTHER way", "domain",  gap_kind="analytic-basis"),  # same kind, diff prose
        _entry("d", "gap", "x",                  "subject", gap_kind="gene-locus-context"),
    ]
    gaps = aggregate_gaps(entries)
    # b and c collapse (same gap_kind despite different prose); numbers are canonical, not renumbered.
    assert [g.id for g in gaps] == ["GAP-7", "GAP-8"]
    assert gaps[0].gap_kind == "analytic-basis"


def test_untagged_falls_back_to_prose_key_and_non_colliding_numbers():
    entries = [
        _entry("b", "gap", "no half-life field", "general"),
        _entry("c", "gap", "no half-life field", "general"),   # dup of b (prose)
        _entry("d", "gap", "no ontology slot",   "subject"),
    ]
    gaps = aggregate_gaps(entries)
    ids = [g.id for g in gaps]
    assert len(ids) == 2                                        # deduped by prose
    canon_max = max(int(v.split("-", 1)[1]) for v in CANONICAL_GAP_KINDS.values())
    assert all(int(i.split("-", 1)[1]) > canon_max for i in ids)  # never collide with GAP-1..15


def test_unknown_tagged_kind_gets_fresh_number():
    gaps = aggregate_gaps([_entry("z", "gap", "novel", "general", gap_kind="totally-new-kind")])
    assert len(gaps) == 1 and gaps[0].id.startswith("GAP-")
    assert gaps[0].gap_kind == "totally-new-kind"
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd /Users/zbb2/Desktop/polymer-claims && uv run --project . pytest tests/synbio/test_gap_ledger.py -v`
Expected: FAIL — `CANONICAL_GAP_KINDS` and `SchemaFit.gap_kind` don't exist; `GapRecord` has no `gap_kind`.

- [ ] **Step 3a: Add `gap_kind` to `SchemaFit`** in `src/polymer_claims/synbio/manifest.py` (after `purity_cost`):

```python
    expansion_class: str | None = None  # general | analysis | subject | domain
    purity_cost: str | None = None
    gap_kind: str | None = None  # controlled dedup tag (see gap_ledger.CANONICAL_GAP_KINDS)
```

- [ ] **Step 3b: Rewrite `src/polymer_claims/synbio/gap_ledger.py`:**

```python
"""Aggregate manifest schema_fit gaps into the fixed, deduplicated gap list (GAP-N).

Dedup on a controlled `gap_kind` tag so the same strain recorded (and worded) many ways collapses to
one canonical, stably-numbered entry. `CANONICAL_GAP_KINDS` is the source of truth for kind -> number;
a recognized kind always gets its canonical GAP-N. Untagged gaps fall back to the legacy prose key and
number sequentially from a base that never collides with a canonical number.
"""
from __future__ import annotations

from dataclasses import dataclass

from .manifest import ManifestEntry

# Controlled vocabulary: gap_kind -> stable canonical GAP-N. GAP-5/6/9/10/12 do not appear — they were
# the interval/range/floor/bound family, now unified under `interval-bound` (GAP-3, resolved 2026-07-12).
CANONICAL_GAP_KINDS: dict[str, str] = {
    "reported-quantity-pattern":     "GAP-1",
    "context-conditioning":          "GAP-2",
    "interval-bound":                "GAP-3",
    "reported-defeater-provisional": "GAP-4",
    "analytic-basis":                "GAP-7",
    "gene-locus-context":            "GAP-8",
    "stratification":                "GAP-11",
    "endpoint-type":                 "GAP-13",
    "composite-quantity":            "GAP-14",
    "categorical-mapping":           "GAP-15",
}


@dataclass(frozen=True)
class GapRecord:
    id: str
    constraint: str
    current_ir_behavior: str | None
    candidate_resolution: str | None
    expansion_class: str | None
    purity_cost: str | None
    gap_kind: str | None


def _prose_key(sf) -> tuple[str, str]:
    return ((sf.expansion_class or "").strip().lower(),
            (sf.constraint or "").strip().lower())


def aggregate_gaps(entries: list[ManifestEntry], start_index: int = 5) -> list[GapRecord]:
    canonical_nums = [int(v.split("-", 1)[1]) for v in CANONICAL_GAP_KINDS.values()]
    next_free = max(max(canonical_nums, default=0), start_index - 1) + 1
    seen: dict[object, GapRecord] = {}
    for e in entries:
        sf = e.schema_fit
        if sf.status != "gap":
            continue
        kind = (sf.gap_kind or "").strip().lower()
        key: object = kind or _prose_key(sf)
        if key in seen:
            continue
        gap_id = CANONICAL_GAP_KINDS.get(kind)
        if gap_id is None:
            gap_id = f"GAP-{next_free}"
            next_free += 1
        seen[key] = GapRecord(
            id=gap_id,
            constraint=sf.constraint or "",
            current_ir_behavior=sf.current_ir_behavior,
            candidate_resolution=sf.candidate_resolution,
            expansion_class=sf.expansion_class,
            purity_cost=sf.purity_cost,
            gap_kind=sf.gap_kind,
        )
    return list(seen.values())
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd /Users/zbb2/Desktop/polymer-claims && uv run --project . pytest tests/synbio/test_gap_ledger.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Regression — synbio dir green**

Run: `cd /Users/zbb2/Desktop/polymer-claims && uv run --project . pytest tests/synbio/ -q`
Expected: PASS (existing count + the rewritten gap-ledger tests; 2 xfail from the interval tripwires remain). Note: `test_ingest.py`/`test_manifest.py` may reference `GapRecord`/`SchemaFit` — confirm they still pass (the new `gap_kind` field is optional so `ManifestEntry.model_validate` calls without it are unaffected).

- [ ] **Step 6: Commit**

```bash
git add src/polymer_claims/synbio/manifest.py src/polymer_claims/synbio/gap_ledger.py tests/synbio/test_gap_ledger.py
git commit -m "feat(synbio): gap_kind dedup + canonical GAP-N registry in aggregate_gaps"
```

---

### Task 2: Re-tag the six surviving gap entries + integration test + docs

**Files:**
- Modify: `data/synbio_compendia/manifests/plm-03-sensing.json`, `plm-06-computing.json`, `plm-08-delivery.json`
- Test: `tests/synbio/test_gap_ledger.py` (add one integration test)
- Modify: `docs/superpowers/notes/2026-07-10-synbio-grammar-gaps.md`, `docs/superpowers/CONTINUE.md`

**Interfaces:**
- Consumes: `aggregate_gaps` / `CANONICAL_GAP_KINDS` (Task 1).

- [ ] **Step 1: Add the integration test** to `tests/synbio/test_gap_ledger.py`:

```python
def test_real_manifests_aggregate_to_canonical_ids():
    from pathlib import Path
    from polymer_claims.synbio.manifest import load_manifest
    paths = sorted((Path(__file__).resolve().parents[2]
                    / "data/synbio_compendia/manifests").glob("*.json"))
    gaps = aggregate_gaps([e for p in paths for e in load_manifest(p)])
    assert {g.id for g in gaps} == {"GAP-7", "GAP-8", "GAP-11", "GAP-13", "GAP-14", "GAP-15"}
    assert all(g.gap_kind for g in gaps)   # every surviving gap is now tagged
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd /Users/zbb2/Desktop/polymer-claims && uv run --project . pytest tests/synbio/test_gap_ledger.py::test_real_manifests_aggregate_to_canonical_ids -v`
Expected: FAIL — the six entries have no `gap_kind` yet, so they dedup via prose and number from the non-colliding base (GAP-16+), not the canonical ids.

- [ ] **Step 3: Add `gap_kind` to the six surviving gap entries.** In each entry's `schema_fit` object, add a `"gap_kind"` key:

| file | entry id | add to schema_fit |
|---|---|---|
| plm-03-sensing.json | `sb-plm03-snv-two-bits` | `"gap_kind": "analytic-basis"` |
| plm-03-sensing.json | `sb-plm03-tet2-truncating-fraction` | `"gap_kind": "gene-locus-context"` |
| plm-06-computing.json | `sb-plm06-hla-loh-prevalence` | `"gap_kind": "stratification"` |
| plm-08-delivery.json | `sb-plm08-ckit-lnp-hspc-transfection` | `"gap_kind": "endpoint-type"` |
| plm-08-delivery.json | `sb-plm08-lnp-four-component-molar-ratio` | `"gap_kind": "composite-quantity"` |
| plm-08-delivery.json | `sb-plm08-sort-lipid-biodistribution` | `"gap_kind": "categorical-mapping"` |

Add the key inside the existing `"schema_fit": { ... }` object (any position; keep the JSON valid).

- [ ] **Step 4: Run to verify it passes**

Run: `cd /Users/zbb2/Desktop/polymer-claims && uv run --project . pytest tests/synbio/test_gap_ledger.py -v && uv run --project . pytest tests/synbio/ -q`
Expected: PASS (integration test green; full synbio dir green, 2 xfail from interval tripwires remain).

- [ ] **Step 5: Doc note.** In `docs/superpowers/notes/2026-07-10-synbio-grammar-gaps.md`, under the "Harvest verdict + two aggregator findings" section, update the second bullet (the `aggregate_gaps` dedup finding) to note it is now RESOLVED: dedup keys on a controlled `gap_kind` tag reconciled against a canonical registry (`CANONICAL_GAP_KINDS`), so `aggregate_gaps` over the corpus returns the stable canonical ids (GAP-7/8/11/13/14/15) and paraphrases of one strain collapse. In `docs/superpowers/CONTINUE.md`, add a one-line note to the current-state block that the aggregator precision follow-up shipped.

- [ ] **Step 6: Commit**

```bash
git add data/synbio_compendia/manifests tests/synbio/test_gap_ledger.py docs/superpowers/notes/2026-07-10-synbio-grammar-gaps.md docs/superpowers/CONTINUE.md
git commit -m "feat(synbio): tag surviving gaps with gap_kind; aggregator returns canonical ids"
```

---

## Self-review (against the spec)

- **`gap_kind` field + registry + new dedup/numbering** → Task 1. ✔
- **Backward-compat (untagged → prose fallback, non-colliding numbers)** → Task 1 Step 1 test 2 + logic. ✔
- **Re-tag 6 entries + canonical-ids integration test** → Task 2. ✔
- **No built-claim / universe change** → Global Constraints; `gap_kind` is schema_fit-only (not read by `build_claim`). ✔
- **Type consistency:** `gap_kind: str | None` identical on `SchemaFit` (Task 1) and `GapRecord` (Task 1); `CANONICAL_GAP_KINDS` keys match the six tags applied in Task 2. ✔
