# Common-Cause §E — Earn REPLICATED on Low Shared-Cause Overlap — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the REPLICATED tier (which licenses multiplying two cohorts' e-values) require distinct `dimnames_hash` **AND** low pairwise shared-cause overlap between the runs' declared factor sets — else REPRODUCED, with the e-value product withheld.

**Architecture:** A pure graded-overlap primitive (`shared_cause_jaccard` + `SHARED_CAUSE_TAU`) in `grammar/shared_cause.py`; everything touching `Satisfaction`/`MaterializationContext` (the new factor field, `cohorts_error_independent`, `max_shared_cause_overlap`, the overlap-aware `independence_tier_of`) in `grammar/licensing.py` — keeping `licensing → shared_cause → strength` acyclic. The umbrella `replication.py` gates the e-value multiplication on the SAME grammar predicate, so the tier label and the evidence never disagree. Additive/byte-identical when no factors are declared.

**Tech Stack:** Python 3 (pydantic frozen `_Model`, stdlib only — numpy-free); `uv run pytest`/`ruff`; viewer Next 16 (`tsc --noEmit` + `next build`).

## Global Constraints

- **Corpus = exactly 4 collections.** No new collection; factors ride `MaterializationContext`, overlap rides `Licensing`.
- **`grammar/` pure/deterministic + numpy-free**; never imports `polymer_formalclaim`; `protocol/` and umbrella depend one-way on `grammar/`. **Import cycle ban:** `shared_cause.py` must NOT import `licensing` (it imports only `.strength`); the licensing-aware logic lives in `licensing.py`, which already imports `SeverityProvenance` from `shared_cause`.
- **Frozen `_Model` (`extra="forbid"`); collections are tuples; no dict/list fields on models.**
- **Additive/optional, byte-identical when off:** with no `shared_cause_factors` declared anywhere, `cohorts_error_independent` returns `None` and every new path reduces to today's behavior (REPLICATED on distinct dimnames, e-values multiplied). The full existing §2E suite must stay green unchanged.
- **Per-package gate:** `uv run pytest -q` + `uv run ruff check src tests`; **full gate:** `scripts/check-all.sh`. TDD: failing test first.
- **Merge to `main` `--no-ff`**; push to `origin` (`origin/main == main`). `check-all.sh` is the pre-merge gate.
- **Naming (verbatim):** `MaterializationContext.shared_cause_factors: tuple[str, ...] = ()`; `Licensing.shared_cause_overlap: float | None = None`; `SHARED_CAUSE_TAU: float = 0.5` (in `shared_cause.py`); `shared_cause_jaccard(a, b) -> float`; `cohorts_error_independent(satisfactions) -> bool | None`; `max_shared_cause_overlap(satisfactions) -> float | None`. Threshold semantics: pairwise Jaccard **`< SHARED_CAUSE_TAU` ⇒ independent**.

---

### Task 1: Grammar — graded factor-set overlap (`shared_cause.py`)

**Files:**
- Modify: `grammar/src/polymer_grammar/shared_cause.py` (add constant + function)
- Modify: `grammar/src/polymer_grammar/__init__.py` (export `shared_cause_jaccard`, `SHARED_CAUSE_TAU`)
- Test: `grammar/tests/test_shared_cause_jaccard.py`

**Interfaces:**
- Produces: `SHARED_CAUSE_TAU: float = 0.5`; `shared_cause_jaccard(a: tuple[str, ...], b: tuple[str, ...]) -> float` (`|A∩B|/|A∪B|`, `0.0` when both empty).

- [ ] **Step 1: Write the failing test**

Create `grammar/tests/test_shared_cause_jaccard.py`:

```python
from polymer_grammar import SHARED_CAUSE_TAU, shared_cause_jaccard


def test_jaccard_identical_is_one():
    assert shared_cause_jaccard(("a", "b"), ("a", "b")) == 1.0


def test_jaccard_disjoint_is_zero():
    assert shared_cause_jaccard(("a", "b"), ("c", "d")) == 0.0


def test_jaccard_partial():
    # {a,b,c} ∩ {b,c,d} = {b,c} (2); ∪ = {a,b,c,d} (4) -> 0.5
    assert shared_cause_jaccard(("a", "b", "c"), ("b", "c", "d")) == 0.5


def test_jaccard_both_empty_is_zero():
    assert shared_cause_jaccard((), ()) == 0.0


def test_jaccard_one_empty_is_zero():
    assert shared_cause_jaccard(("a",), ()) == 0.0


def test_jaccard_ignores_duplicates_and_order():
    assert shared_cause_jaccard(("a", "a", "b"), ("b", "a")) == 1.0


def test_tau_default():
    assert SHARED_CAUSE_TAU == 0.5
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd grammar && uv run pytest tests/test_shared_cause_jaccard.py -q`
Expected: FAIL — `ImportError` (`SHARED_CAUSE_TAU`/`shared_cause_jaccard` not in `polymer_grammar`).

- [ ] **Step 3: Write minimal implementation**

In `grammar/src/polymer_grammar/shared_cause.py`, append (after `cap_severity_for_confirmatory`):

```python
# §E (north-star common-cause): Reichenbach screening-off, first concrete form. The graded
# shared-cause overlap between two runs' causal-dependency factor sets. Pairwise overlap below
# SHARED_CAUSE_TAU ⇒ the runs' errors are treated as independent (license may multiply their
# e-values). Operator-asserted factors; derived overlap. Tunable.
SHARED_CAUSE_TAU: float = 0.5


def shared_cause_jaccard(a: tuple[str, ...], b: tuple[str, ...]) -> float:
    """Jaccard overlap |A∩B|/|A∪B| of two factor-tag sets; 0.0 when the union is empty."""
    sa, sb = set(a), set(b)
    union = sa | sb
    if not union:
        return 0.0
    return len(sa & sb) / len(union)
```

In `grammar/src/polymer_grammar/__init__.py`, add to the `from .shared_cause import (...)` block and `__all__`:
`SHARED_CAUSE_TAU`, `shared_cause_jaccard`.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd grammar && uv run pytest tests/test_shared_cause_jaccard.py -q && uv run pytest tests/test_isolation.py -q && uv run ruff check src tests`
Expected: PASS, isolation green (module still imports only `.strength` + stdlib), ruff clean.

- [ ] **Step 5: Commit**

```bash
git add grammar/src/polymer_grammar/shared_cause.py grammar/src/polymer_grammar/__init__.py grammar/tests/test_shared_cause_jaccard.py
git commit -m "feat(grammar): shared_cause_jaccard + SHARED_CAUSE_TAU — graded factor-set overlap (§E)"
```

---

### Task 2: Grammar — overlap-aware independence (`licensing.py`)

**Files:**
- Modify: `grammar/src/polymer_grammar/licensing.py` (field on `MaterializationContext`; field on `Licensing`; `cohorts_error_independent`; `max_shared_cause_overlap`; overlap-aware `independence_tier_of`)
- Modify: `grammar/src/polymer_grammar/__init__.py` (export `cohorts_error_independent`, `max_shared_cause_overlap`)
- Test: `grammar/tests/test_independence_overlap.py`

**Interfaces:**
- Consumes: `shared_cause_jaccard`, `SHARED_CAUSE_TAU` (Task 1).
- Produces:
  - `MaterializationContext.shared_cause_factors: tuple[str, ...] = ()`
  - `Licensing.shared_cause_overlap: float | None = None`
  - `cohorts_error_independent(satisfactions: tuple[Satisfaction, ...]) -> bool | None` — `None` if <2 distinct cohorts OR any distinct-cohort representative has empty factors; else `True` iff every pairwise Jaccard `< SHARED_CAUSE_TAU`, else `False`.
  - `max_shared_cause_overlap(satisfactions) -> float | None` — max pairwise Jaccard among distinct-cohort reps (same `None` cases).
  - `independence_tier_of(satisfactions)` — **same signature**, now overlap-aware.

- [ ] **Step 1: Write the failing test**

Create `grammar/tests/test_independence_overlap.py`:

```python
from polymer_grammar import (
    IndependenceTier,
    cohorts_error_independent,
    independence_tier_of,
    max_shared_cause_overlap,
)
from polymer_grammar.licensing import (
    MaterializationContext,
    Satisfaction,
    SatisfactionVerdict,
)


def _sat(dimnames: str, factors: tuple[str, ...] = ()) -> Satisfaction:
    return Satisfaction(
        verdict=SatisfactionVerdict.SATISFIED,
        materialization=MaterializationContext(
            id=f"M-{dimnames}", api_version="v1", data_version="d1",
            dimnames_hash=dimnames, shared_cause_factors=factors,
        ),
    )


def test_factors_absent_is_byte_identical_replicated():
    # two distinct cohorts, NO factors -> today's behavior: REPLICATED, indep None
    sats = (_sat("cohortA"), _sat("cohortB"))
    assert cohorts_error_independent(sats) is None
    assert independence_tier_of(sats) is IndependenceTier.REPLICATED
    assert max_shared_cause_overlap(sats) is None


def test_low_overlap_earns_replicated():
    # jaccard({a,b,c},{c,d,e}) = 1/5 = 0.2 < 0.5
    sats = (_sat("cohortA", ("a", "b", "c")), _sat("cohortB", ("c", "d", "e")))
    assert cohorts_error_independent(sats) is True
    assert independence_tier_of(sats) is IndependenceTier.REPLICATED
    assert max_shared_cause_overlap(sats) == 0.2


def test_high_overlap_denies_replicated():
    # jaccard({a,b,c},{a,b,d}) = 2/4 = 0.5 -> NOT < 0.5 -> not independent
    sats = (_sat("cohortA", ("a", "b", "c")), _sat("cohortB", ("a", "b", "d")))
    assert cohorts_error_independent(sats) is False
    assert independence_tier_of(sats) is IndependenceTier.REPRODUCED
    assert max_shared_cause_overlap(sats) == 0.5


def test_partial_factor_adoption_falls_back_to_none():
    # one cohort declares factors, the other does not -> can't assess -> None (byte-identical)
    sats = (_sat("cohortA", ("a", "b")), _sat("cohortB"))
    assert cohorts_error_independent(sats) is None
    assert independence_tier_of(sats) is IndependenceTier.REPLICATED


def test_single_cohort_is_reproduced():
    sats = (_sat("cohortA", ("a",)),)
    assert cohorts_error_independent(sats) is None
    assert independence_tier_of(sats) is IndependenceTier.REPRODUCED


def test_materialization_factors_default_empty():
    m = MaterializationContext(id="M", api_version="v1", data_version="d1")
    assert m.shared_cause_factors == ()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd grammar && uv run pytest tests/test_independence_overlap.py -q`
Expected: FAIL — `shared_cause_factors` rejected by `extra="forbid"` / `cohorts_error_independent` not importable.

- [ ] **Step 3: Write minimal implementation**

In `grammar/src/polymer_grammar/licensing.py`:

Extend the import at the top (line 20 area):

```python
from .shared_cause import SHARED_CAUSE_TAU, SeverityProvenance, shared_cause_jaccard
```

Add the field to `MaterializationContext` (after `dimnames_hash`, line 38):

```python
    # §E common-cause: namespaced causal-dependency tags this run's result depends on
    # (e.g. "manifest:HM450", "norm:noob", "ref:GRCh38", "lib:numpy-lstsq", "prior:idh-hypermeth").
    # Operator-asserted. Empty => not assessable (inert). The flat first form of the common-cause DAG.
    shared_cause_factors: tuple[str, ...] = ()
```

Replace `independence_tier_of` (lines 69-77) with the helper trio + the overlap-aware tier:

```python
def _distinct_cohort_reps(
    satisfactions: tuple["Satisfaction", ...]
) -> list["Satisfaction"]:
    """One representative Satisfaction per distinct non-None dimnames_hash, deterministic
    (ascending dimnames_hash, first occurrence)."""
    reps: dict[str, "Satisfaction"] = {}
    for s in satisfactions:
        h = s.materialization.dimnames_hash
        if h is not None and h not in reps:
            reps[h] = s
    return [reps[h] for h in sorted(reps)]


def cohorts_error_independent(
    satisfactions: tuple["Satisfaction", ...]
) -> bool | None:
    """§E: are the distinct cohorts' errors independent (low shared-cause overlap)?
    None  -> not assessable: <2 distinct cohorts, OR any representative has empty factors
             (partial adoption falls back to today's behavior — byte-identical when off).
    True  -> every pairwise Jaccard < SHARED_CAUSE_TAU.
    False -> some pair's Jaccard >= SHARED_CAUSE_TAU (the runs share too much cause)."""
    reps = _distinct_cohort_reps(satisfactions)
    if len(reps) < 2:
        return None
    factors = [r.materialization.shared_cause_factors for r in reps]
    if any(not f for f in factors):
        return None
    for i in range(len(factors)):
        for j in range(i + 1, len(factors)):
            if shared_cause_jaccard(factors[i], factors[j]) >= SHARED_CAUSE_TAU:
                return False
    return True


def max_shared_cause_overlap(
    satisfactions: tuple["Satisfaction", ...]
) -> float | None:
    """The max pairwise Jaccard among distinct-cohort representatives, or None when not
    assessable (matches cohorts_error_independent's None cases). Recorded on the license."""
    reps = _distinct_cohort_reps(satisfactions)
    if len(reps) < 2:
        return None
    factors = [r.materialization.shared_cause_factors for r in reps]
    if any(not f for f in factors):
        return None
    return max(
        shared_cause_jaccard(factors[i], factors[j])
        for i in range(len(factors))
        for j in range(i + 1, len(factors))
    )


def independence_tier_of(satisfactions: tuple["Satisfaction", ...]) -> IndependenceTier:
    """REPLICATED iff >=2 DISTINCT non-None dimnames_hash AND the cohorts are error-independent.
    cohorts_error_independent is None (factors absent / partial) => today's behavior (REPLICATED on
    distinct cohorts — byte-identical when off); False (high overlap) => REPRODUCED (the §E gate)."""
    cohorts = {
        s.materialization.dimnames_hash
        for s in satisfactions
        if s.materialization.dimnames_hash is not None
    }
    if len(cohorts) < 2:
        return IndependenceTier.REPRODUCED
    if cohorts_error_independent(satisfactions) is False:
        return IndependenceTier.REPRODUCED
    return IndependenceTier.REPLICATED
```

Add the field to `Licensing` (after `severity_provenance`, line 86):

```python
    shared_cause_overlap: float | None = None
```

In `grammar/src/polymer_grammar/__init__.py`, add `cohorts_error_independent` and `max_shared_cause_overlap` to the licensing import block + `__all__` (next to the existing `independence_tier_of` export).

- [ ] **Step 4: Run test to verify it passes**

Run: `cd grammar && uv run pytest tests/test_independence_overlap.py -q`
Expected: PASS (all six cases).

- [ ] **Step 5: Run the full grammar suite (byte-identity of §2E)**

Run: `cd grammar && uv run pytest -q && uv run ruff check src tests`
Expected: PASS — every existing licensing/§2E test green (no factors ⇒ `independence_tier_of` unchanged); the `_replicated_tier_needs_two_distinct_cohorts` validator still holds.

- [ ] **Step 6: Commit**

```bash
git add grammar/src/polymer_grammar/licensing.py grammar/src/polymer_grammar/__init__.py grammar/tests/test_independence_overlap.py
git commit -m "feat(grammar): overlap-aware independence_tier_of + cohorts_error_independent + factor field (§E)"
```

---

### Task 3: Umbrella — gate the e-value multiplication (`replication.py`)

**Files:**
- Modify: `src/polymer_claims/replication.py` (consult `cohorts_error_independent` before multiplying; carry cohort-B factors)
- Test: `src/tests/test_replication_shared_cause.py` (path per the existing replication test location — confirm with `grep -rl "build_replication_inputs" src/tests tests` and place beside it)

**Interfaces:**
- Consumes: `cohorts_error_independent` (Task 2); `MaterializationContext.shared_cause_factors` (Task 2).
- Produces: `build_replication_inputs` multiplies `e₁·e₂` only when `cohorts_error_independent((sat_a, sat_b))` is NOT `False`; on `False` it keeps the single `e₁` but still records `sat_b` in `replications[cid]`.

- [ ] **Step 1: Write the failing test**

First locate the existing §2E replication test (`grep -rl "build_replication_inputs" src/tests tests`) and read it to reuse its contract fixtures + corpus builder. Create `test_replication_shared_cause.py` beside it. The test must prove the gate via the grammar predicate AND that the multiplication site honors it. Use this structure (adapt the helpers/fixtures to the existing harness):

```python
from polymer_grammar import (
    MaterializationContext,
    Satisfaction,
    SatisfactionVerdict,
    cohorts_error_independent,
)


def _sat(dimnames, factors):
    return Satisfaction(
        verdict=SatisfactionVerdict.SATISFIED,
        materialization=MaterializationContext(
            id=f"M-{dimnames}", api_version="v1", data_version="d1",
            dimnames_hash=dimnames, shared_cause_factors=factors,
        ),
    )


def test_gate_predicate_high_overlap_denies():
    # the predicate the umbrella consults: high overlap -> False -> do not multiply
    a = _sat("A", ("manifest:HM450", "norm:noob", "ref:GRCh38"))
    b = _sat("B", ("manifest:HM450", "norm:noob", "lib:numpy"))  # jaccard 2/4 = 0.5 -> False
    assert cohorts_error_independent((a, b)) is False


def test_gate_predicate_low_overlap_allows():
    a = _sat("A", ("manifest:HM450", "norm:noob", "ref:GRCh38"))
    b = _sat("B", ("manifest:EPIC", "norm:funnorm", "ref:GRCh37"))  # disjoint -> True
    assert cohorts_error_independent((a, b)) is True
```

PLUS an integration assertion on `build_replication_inputs` itself using the existing §2E fixture: with the existing factor-less binding, the product is still applied (byte-identical). If the existing fixture's contracts can be extended to carry `shared_cause_factors` (or `base_ctx` given factors + the cohort-B materialization given overlapping factors), add a case asserting `evidence[cid]` is the UN-multiplied `e₁` (no product) when overlap is high, while `replications[cid] == (sat_b,)` is still set. If wiring real-contract factors proves too involved, assert byte-identity on the existing fixture (product applied) and rely on the grammar predicate tests above for the gate logic — note this choice in your report.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd <repo root> && uv run pytest <new test path> -q`
Expected: the integration assertion for the high-overlap no-multiply case FAILS (today `build_replication_inputs` always multiplies). The predicate-only tests pass once Task 2 is merged.

- [ ] **Step 3: Write minimal implementation**

In `src/polymer_claims/replication.py`:

Extend the grammar import block (lines 15-20) to add `cohorts_error_independent`:

```python
from polymer_grammar import (
    DataHandle,
    MaterializationContext,
    Satisfaction,
    SatisfactionVerdict,
    cohorts_error_independent,
)
```

In `build_replication_inputs`, where `sat_b` is built and the product is applied (lines 100-110), carry cohort-B factors and gate the multiply:

```python
        sat_b = Satisfaction(
            verdict=SatisfactionVerdict.SATISFIED,
            materialization=MaterializationContext(
                id=f"{base_ctx.id}-repl-{contract_b.contract_uid}",
                api_version=base_ctx.api_version,
                data_version=base_ctx.data_version,
                dimnames_hash=contract_b.dimnames_hash,
                shared_cause_factors=getattr(contract_b, "shared_cause_factors", ()),
            ),
        )
        replications[cid] = (sat_b,)
        # §E: only multiply the cohorts' e-values when their errors are independent (low shared-cause
        # overlap). cohorts_error_independent is None when factors are absent -> multiply as today
        # (byte-identical); False (high overlap) -> keep the single e1 so the evidence matches the
        # REPRODUCED tier independence_tier_of will stamp.
        sat_a = Satisfaction(verdict=SatisfactionVerdict.SATISFIED, materialization=base_ctx)
        if cohorts_error_independent((sat_a, sat_b)) is not False:
            evidence[cid] = evidence[cid] * e2
```

> Note: `getattr(contract_b, "shared_cause_factors", ())` defaults to `()` because SE-Contracts do not yet carry factors — so the umbrella gate is wired but **inert until contracts/runs declare factors** (an operational follow-up). The grammar mechanism (Task 2) is fully tested regardless.
>
> **Post-implementation update (2026-06-20):** bundled SE-Contracts now carry flat
> `shared_cause_factors`, and `materialization_map` propagates cohort-A factors into verify's
> satisfaction context. The gate is active for bundled contract-backed runs; factor provenance remains
> operator-authored.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest <new test path> -q` and the existing §2E replication test file.
Expected: PASS; the existing replication test stays green (byte-identical — factors absent ⇒ product applied).

- [ ] **Step 5: Run the umbrella suite**

Run: `uv run pytest -q && uv run ruff check src tests` (from the umbrella package root).
Expected: PASS, ruff clean.

- [ ] **Step 6: Commit**

```bash
git add src/polymer_claims/replication.py <new test path>
git commit -m "feat(replication): gate e-value multiplication on cohorts_error_independent (§E)"
```

---

### Task 4: Visibility — record `shared_cause_overlap` on the license + topology + viewer

**Files:**
- Modify: `protocol/src/polymer_protocol/verify.py` (set `shared_cause_overlap=max_shared_cause_overlap(sats)` on the SEVERE_TEST `Licensing`)
- Modify: `protocol/src/polymer_protocol/topology.py` (`TopologyNode.shared_cause_overlap` + populate)
- Modify: viewer TS sites mirroring `severity_provenance`/`independence_tier`: `viewer/src/lib/topology.ts`, `viewer/src/lib/interpolate.ts`, `viewer/src/components/scene/Nodes.tsx`, `viewer/src/components/scene/Edges.tsx`, `viewer/src/components/chrome/RightRail.tsx`
- Test: `protocol/tests/test_topology_shared_cause_overlap.py`

**Interfaces:**
- Consumes: `max_shared_cause_overlap` (Task 2); `Licensing.shared_cause_overlap` (Task 2).
- Produces: licensed claims carry `licensing.shared_cause_overlap`; `TopologyNode.shared_cause_overlap: float | None`; viewer RightRail shows it.

- [ ] **Step 1: Write the failing test**

Create `protocol/tests/test_topology_shared_cause_overlap.py`. Reuse `protocol/tests/helpers_verify.py` (`licensable_corpus`, `with_dimnames`) from Phase D slice 2; to get a 2-cohort REPLICATED claim with overlap, build a claim whose licensing carries two satisfactions with factors. Confirm the topology export entrypoint name (`grep -n "def export_topology" protocol/src/polymer_protocol/topology.py`) and how existing topology tests call it.

```python
from polymer_protocol.topology import export_topology

from tests.helpers_verify import licensable_corpus, with_dimnames
from polymer_protocol.verify import verify_stage


def test_topology_node_shared_cause_overlap_none_when_single_cohort():
    corpus, scaff, recs = licensable_corpus()
    out = verify_stage(corpus, scaff, recs)
    export = export_topology(out)
    n = next(n for n in export.nodes if n.id == "c1")
    assert n.shared_cause_overlap is None  # single cohort -> not assessable
```

(Add a 2-cohort overlap case if the harness can supply a replication satisfaction with factors via the verify `replications=` map; otherwise the single-cohort None case + the Task-2 grammar tests cover the recording logic. Note the choice in your report.)

- [ ] **Step 2: Run test to verify it fails**

Run: `cd protocol && uv run pytest tests/test_topology_shared_cause_overlap.py -q`
Expected: FAIL — `TopologyNode` has no `shared_cause_overlap` (`extra="forbid"`).

- [ ] **Step 3: Write minimal implementation (Python)**

In `protocol/src/polymer_protocol/verify.py`, import `max_shared_cause_overlap` (extend the `from polymer_grammar import (...)` block) and set it on the SEVERE_TEST `Licensing` (the construction around `independence_tier=independence_tier_of(sats)`):

```python
            licensing = Licensing(
                route=LicenseRoute.SEVERE_TEST,
                satisfactions=sats,
                rival_set_closure=RivalSetClosure.OPEN_ACKNOWLEDGED,
                independence_tier=independence_tier_of(sats),
                shared_cause_overlap=max_shared_cause_overlap(sats),
            )
```

In `protocol/src/polymer_protocol/topology.py`, add to `TopologyNode` (after `independence_tier`):

```python
    shared_cause_overlap: float | None = None
```

and in `_extract_nodes`, in the `TopologyNode(...)` constructor (after `independence_tier=...`):

```python
                shared_cause_overlap=(
                    c.licensing.shared_cause_overlap if c.licensing is not None else None
                ),
```

- [ ] **Step 4: Run the Python tests**

Run: `cd protocol && uv run pytest tests/test_topology_shared_cause_overlap.py -q && uv run pytest -q && uv run ruff check src tests`
Expected: PASS, full protocol suite green.

- [ ] **Step 5: Mirror the viewer TS sites**

Mirror `severity_provenance` (added in slice 2) at each site, with the `?? null` pattern:
- `viewer/src/lib/topology.ts` — node type: `shared_cause_overlap?: number | null;`
- `viewer/src/lib/interpolate.ts` — `InterpNode` type: `shared_cause_overlap: number | null;`; in each object literal that copies `severity_provenance` (the lerp/entering/exiting branches), add `shared_cause_overlap: nX.shared_cause_overlap ?? null,` using the same `na`/`nb` variable.
- `viewer/src/components/scene/Nodes.tsx` — param type `shared_cause_overlap?: number | null;` + mapping `shared_cause_overlap: n.shared_cause_overlap ?? null,`.
- `viewer/src/components/scene/Edges.tsx` — mapping `shared_cause_overlap: n.shared_cause_overlap ?? null,`.
- `viewer/src/components/chrome/RightRail.tsx` — after the `severity_provenance` row, add a row showing `shared_cause_overlap` (render the number, or `—` when null; reuse the existing label style):
  ```tsx
  <div style={label}>shared_cause_overlap</div>
  <div>{node.shared_cause_overlap ?? '—'}</div>
  ```

- [ ] **Step 6: Typecheck + build the viewer**

Run: `cd viewer && npm run typecheck && npm run build`
Expected: both succeed.

- [ ] **Step 7: Commit**

```bash
git add protocol/src/polymer_protocol/verify.py protocol/src/polymer_protocol/topology.py protocol/tests/test_topology_shared_cause_overlap.py viewer/src/lib/topology.ts viewer/src/lib/interpolate.ts viewer/src/components/scene/Nodes.tsx viewer/src/components/scene/Edges.tsx viewer/src/components/chrome/RightRail.tsx
git commit -m "feat(viewer): record + surface shared_cause_overlap on the license (§E)"
```

---

### Task 5: Full gate + byte-identity golden + docs

**Files:**
- Test: `grammar/tests/test_independence_byte_identical.py`
- Modify: `docs/superpowers/CONTINUE.md`

- [ ] **Step 1: Write the byte-identity golden test**

Create `grammar/tests/test_independence_byte_identical.py` — pin that, with NO factors, the §2E behavior is exactly today's:

```python
from polymer_grammar import IndependenceTier, independence_tier_of
from polymer_grammar.licensing import (
    MaterializationContext, Satisfaction, SatisfactionVerdict,
)


def _sat(dimnames):
    return Satisfaction(
        verdict=SatisfactionVerdict.SATISFIED,
        materialization=MaterializationContext(
            id=f"M-{dimnames}", api_version="v1", data_version="d1", dimnames_hash=dimnames,
        ),
    )


def test_two_distinct_cohorts_no_factors_is_replicated():
    # the §2E contract pre-§E: distinct dimnames + no factors -> REPLICATED (byte-identical)
    assert independence_tier_of((_sat("A"), _sat("B"))) is IndependenceTier.REPLICATED


def test_one_cohort_is_reproduced():
    assert independence_tier_of((_sat("A"),)) is IndependenceTier.REPRODUCED


def test_same_cohort_twice_is_reproduced():
    assert independence_tier_of((_sat("A"), _sat("A"))) is IndependenceTier.REPRODUCED
```

- [ ] **Step 2: Run the test**

Run: `cd grammar && uv run pytest tests/test_independence_byte_identical.py -q`
Expected: PASS.

- [ ] **Step 3: Run the full gate**

Run: `bash scripts/check-all.sh`
Expected: GREEN — grammar + protocol + umbrella pytest, ruff, isolation, viewer typecheck + build. Record the final test counts.

- [ ] **Step 4: Update `docs/superpowers/CONTINUE.md`**

- Bump the "Current state" test counts to the `check-all.sh` output; note §E common-cause slice shipped (ship date 2026-06-19).
- In "▶ NEXT → Recently shipped", prepend a bullet:

```
**§E common-cause (earn REPLICATED on low shared-cause overlap): each run declares
`MaterializationContext.shared_cause_factors`; REPLICATED (which licenses multiplying e1·e2)
now requires distinct dimnames AND every pairwise Jaccard < SHARED_CAUSE_TAU=0.5, else REPRODUCED;
the umbrella gates the e-value product on the same `cohorts_error_independent` predicate.
`Licensing.shared_cause_overlap` recorded + viewer-surfaced. Second concrete edge of north-star §E.
Additive/byte-identical when off; merged 2026-06-19.**
```

- Add a Done-checklist `✅` entry citing spec+plan `docs/superpowers/{specs,plans}/2026-06-19-common-cause-replicated*`.
- Update the standing §2E/REPLICATED caveat to note REPLICATED is now overlap-gated when factors are declared (operator-asserted factors; populating contracts with factors is an operational follow-up); keep deferred: the real per-implementation causal DAG, the formal screening-off probability derivation, per-adapter factor sets / `adapters_independent` grading.

- [ ] **Step 5: Commit the docs + golden**

```bash
git add docs/superpowers/CONTINUE.md grammar/tests/test_independence_byte_identical.py
git commit -m "docs(CONTINUE): §E common-cause shipped — REPLICATED gated on low shared-cause overlap"
```

> Do NOT merge — the controller runs a final whole-branch review, then merges.

---

## Self-Review

**Spec coverage:**
- §4.1 `shared_cause_jaccard` + `SHARED_CAUSE_TAU` → Task 1. ✅
- §4.2 `MaterializationContext.shared_cause_factors`, `Licensing.shared_cause_overlap`, `cohorts_error_independent`, `max_shared_cause_overlap`, overlap-aware `independence_tier_of` → Task 2. ✅
- §3 import-cycle split (jaccard in shared_cause, satisfaction-aware logic in licensing) → Tasks 1 + 2. ✅
- §4.3 validator interaction (stricter, still holds) → Task 2 Step 5. ✅
- §5 umbrella multiplication gate → Task 3. ✅
- §6 verify records `shared_cause_overlap` → Task 4. ✅
- §7 viewer passthrough → Task 4. ✅
- §9 success criteria 1-7 → Task 2 (1,2,5,6), Task 3 (3), Task 1/5 (4 byte-identical), Task 2/Task1 (7 invariants). ✅
- §8 invariants (Corpus=4, numpy-free, isolation, §2E orthogonality) → Task 1 Step 4 + Task 2 Step 5 + Task 5 Step 3. ✅

**Placeholder scan:** Task 3 and Task 4 give explicit fallbacks (grep locators + the exact contract the test must satisfy + "note the choice in your report") for the integration cases whose fixtures must be located — not "TBD". No "add error handling"/"write tests for the above".

**Type consistency:** `shared_cause_factors: tuple[str, ...]` and `shared_cause_overlap: float | None` used identically in grammar (Task 2), protocol (Task 4), topology/viewer (Task 4, `number | null`); `cohorts_error_independent`/`max_shared_cause_overlap`/`shared_cause_jaccard` signatures identical across Tasks 1-4; `SHARED_CAUSE_TAU = 0.5` referenced consistently; threshold semantics `< τ ⇒ independent` consistent in Task 2 logic + Task 1/2 tests (Jaccard exactly `0.5` → NOT independent).
