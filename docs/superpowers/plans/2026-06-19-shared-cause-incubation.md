# Literature-Shared-Cause Gate + Incubation/Ranking Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the §5a *literature*-shared-cause leak — a hypothesis records the cohorts its motivating prior was established on; overlap with the test cohort → CONFIRMATORY license + capped `severity` axis — and feed the same data-blind signal into SELECT ranking + budget-aware top-k registration.

**Architecture:** One new grammar primitive (`Provenance.prior_cohorts`) + a pure `shared_cause.py` module. The VERIFY gate is authoritative on `dimnames_hash` (post-execution). SELECT ranking is a data-blind pre-execution predictor that resolves a candidate's `DataHandle.ref` to a cohort id via an **injected** `cohort_of_ref` mapping (protocol stays pure — the catalog lives in the umbrella). Everything additive/optional → byte-identical when no `prior_cohorts` exist.

**Tech Stack:** Python 3 (pydantic frozen `_Model`, stdlib only — numpy-free), `uv run pytest`/`ruff`; viewer is Next 16 / React Three Fiber (`tsc --noEmit` + `next build`).

## Global Constraints

- **Corpus = exactly 4 collections** (claims, defeat_edges, equivalences, fdr_ledger). No 5th collection.
- **`grammar/` + `protocol/` are pure/deterministic + numpy-free**; `grammar/` never imports `polymer_formalclaim`; `protocol/` depends one-way on `grammar/` (isolation-tested).
- **All models subclass frozen `_Model` (`extra="forbid"`); collections are tuples**; no `dict`/`list` fields on models.
- **New cross-cutting fields land additive/optional** (`X | None = None` or `tuple[...] = ()`); **opt-in features default to byte-identical behavior when off.**
- **Per-package gate:** `uv run pytest -q` + `uv run ruff check src tests`; **full gate:** `scripts/check-all.sh`. TDD: failing test first.
- **Merge to `main` `--no-ff`**; `main` is pushed to `origin` (`origin/main == main`). `check-all.sh` is the pre-merge gate (no active CI).
- **Naming (verbatim):** field `prior_cohorts`; field `severity_provenance`; enum `SeverityProvenance` with members `HELD_OUT = "held_out"`, `CONFIRMATORY = "confirmatory"`; `PendingReason.SHARED_CAUSE_CONFIRMATORY = "shared_cause_confirmatory"`; constants `CONFIRMATORY_SEVERITY_CEILING = 0.2` (grammar), `CONFIRMATORY_RANK_PENALTY = 0.5` (protocol/select). The only strength axis capped is **`severity`**.

---

### Task 1: Grammar — `shared_cause.py` (the pure check + tier + cap)

**Files:**
- Create: `grammar/src/polymer_grammar/shared_cause.py`
- Modify: `grammar/src/polymer_grammar/__init__.py` (export the new names)
- Test: `grammar/tests/test_shared_cause.py`

**Interfaces:**
- Consumes: `StrengthVector` from `grammar/src/polymer_grammar/strength.py` (6 axes, all `float` in `[0,1]`, higher-is-better).
- Produces:
  - `class SeverityProvenance(str, Enum)`: `HELD_OUT = "held_out"`, `CONFIRMATORY = "confirmatory"`.
  - `CONFIRMATORY_SEVERITY_CEILING: float = 0.2` (module constant, documented tunable).
  - `shared_cause_overlap(prior_cohorts: tuple[str, ...], test_cohorts: tuple[str, ...]) -> bool`
  - `severity_provenance_of(prior_cohorts: tuple[str, ...], test_cohorts: tuple[str, ...]) -> SeverityProvenance | None`
  - `cap_severity_for_confirmatory(strength: StrengthVector) -> StrengthVector`

- [ ] **Step 1: Write the failing test**

Create `grammar/tests/test_shared_cause.py`:

```python
from polymer_grammar import (
    CONFIRMATORY_SEVERITY_CEILING,
    SeverityProvenance,
    StrengthVector,
    cap_severity_for_confirmatory,
    severity_provenance_of,
    shared_cause_overlap,
)


def test_overlap_is_set_intersection():
    assert shared_cause_overlap(("a", "b"), ("b", "c")) is True
    assert shared_cause_overlap(("a",), ("c",)) is False
    assert shared_cause_overlap((), ("c",)) is False
    assert shared_cause_overlap(("a",), ()) is False


def test_tier_none_when_no_prior():
    # empty prior_cohorts => inert (None) => byte-identical when off
    assert severity_provenance_of((), ("x",)) is None


def test_tier_confirmatory_on_overlap_else_held_out():
    assert severity_provenance_of(("x",), ("x", "y")) is SeverityProvenance.CONFIRMATORY
    assert severity_provenance_of(("x",), ("y",)) is SeverityProvenance.HELD_OUT
    # prior present but no detectable test cohort => no detected overlap => HELD_OUT
    assert severity_provenance_of(("x",), ()) is SeverityProvenance.HELD_OUT


def _full(severity: float) -> StrengthVector:
    return StrengthVector(
        magnitude=0.9, certainty=0.9, evidence_against_null=0.9,
        severity=severity, world_contact=0.9, explanatory_virtue=0.9,
    )


def test_cap_lowers_only_severity():
    capped = cap_severity_for_confirmatory(_full(0.8))
    assert capped.severity == CONFIRMATORY_SEVERITY_CEILING
    # every other axis byte-unchanged
    for ax in ("magnitude", "certainty", "evidence_against_null", "world_contact", "explanatory_virtue"):
        assert getattr(capped, ax) == 0.9


def test_cap_is_a_floor_min_never_raises_severity():
    already_low = _full(0.05)
    assert cap_severity_for_confirmatory(already_low).severity == 0.05
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd grammar && uv run pytest tests/test_shared_cause.py -q`
Expected: FAIL — `ImportError` (names not defined in `polymer_grammar`).

- [ ] **Step 3: Write minimal implementation**

Create `grammar/src/polymer_grammar/shared_cause.py`:

```python
"""§5a literature-shared-cause: did the hypothesis's motivating prior share a cohort with the
test data? If so the "severe test" is closer to confirmation — annotate CONFIRMATORY and cap the
`severity` strength axis (the precise axis the shared-cause leak corrupts). Pure, stdlib only;
imports nothing from polymer_formalclaim. First concrete edge of north-star §E's common-cause DAG.
"""
from __future__ import annotations

from enum import Enum

from .strength import StrengthVector

# Tunable: a CONFIRMATORY test is a weak severe test, so its `severity` axis is capped to this
# ceiling (the [0,1] axis is higher-is-better; 0.2 sits in the un-severe band).
CONFIRMATORY_SEVERITY_CEILING: float = 0.2


class SeverityProvenance(str, Enum):
    """Whether the hypothesis source was held out from the test data (a genuine severe test) or
    shares a cohort with it (confirmatory). Orthogonal to IndependenceTier (which is about the
    agreeing legs, not the hypothesis origin)."""

    HELD_OUT = "held_out"
    CONFIRMATORY = "confirmatory"


def shared_cause_overlap(prior_cohorts: tuple[str, ...], test_cohorts: tuple[str, ...]) -> bool:
    """True iff the hypothesis's prior-derivation cohorts intersect the test cohorts (exact ids)."""
    return bool(set(prior_cohorts) & set(test_cohorts))


def severity_provenance_of(
    prior_cohorts: tuple[str, ...], test_cohorts: tuple[str, ...]
) -> SeverityProvenance | None:
    """None when there is no prior-derivation provenance to assess (inert — byte-identical when off).
    Else CONFIRMATORY on overlap, HELD_OUT otherwise (HELD_OUT = no overlap *detected*)."""
    if not prior_cohorts:
        return None
    if shared_cause_overlap(prior_cohorts, test_cohorts):
        return SeverityProvenance.CONFIRMATORY
    return SeverityProvenance.HELD_OUT


def cap_severity_for_confirmatory(strength: StrengthVector) -> StrengthVector:
    """Return a copy with `severity` floored to CONFIRMATORY_SEVERITY_CEILING; all other axes
    untouched. A no-op when the current severity is already <= the ceiling."""
    return strength.model_copy(
        update={"severity": min(strength.severity, CONFIRMATORY_SEVERITY_CEILING)}
    )
```

In `grammar/src/polymer_grammar/__init__.py`, add the import (next to the other module imports, e.g. after the `from .strength import ...` line) and the `__all__` entries:

```python
from .shared_cause import (
    CONFIRMATORY_SEVERITY_CEILING,
    SeverityProvenance,
    cap_severity_for_confirmatory,
    severity_provenance_of,
    shared_cause_overlap,
)
```

Add these five names to the `__all__` list (keep it alphabetical if the file is):
`"CONFIRMATORY_SEVERITY_CEILING"`, `"SeverityProvenance"`, `"cap_severity_for_confirmatory"`, `"severity_provenance_of"`, `"shared_cause_overlap"`.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd grammar && uv run pytest tests/test_shared_cause.py -q && uv run ruff check src tests`
Expected: PASS, ruff clean.

- [ ] **Step 5: Confirm isolation + numpy-free preserved**

Run: `cd grammar && uv run pytest tests/test_isolation.py -q`
Expected: PASS (new module imports only `.strength` + stdlib `enum`).

- [ ] **Step 6: Commit**

```bash
git add grammar/src/polymer_grammar/shared_cause.py grammar/src/polymer_grammar/__init__.py grammar/tests/test_shared_cause.py
git commit -m "feat(grammar): shared_cause module — SeverityProvenance + overlap + severity cap (Phase D slice 2)"
```

---

### Task 2: Grammar — additive model fields (`prior_cohorts`, `severity_provenance`, `PendingReason`)

**Files:**
- Modify: `grammar/src/polymer_grammar/provenance.py:26-44` (add `prior_cohorts`)
- Modify: `grammar/src/polymer_grammar/licensing.py:79-85` (add `severity_provenance`)
- Modify: `grammar/src/polymer_grammar/status.py:17-31` (add `PendingReason.SHARED_CAUSE_CONFIRMATORY`)
- Test: `grammar/tests/test_shared_cause_fields.py`

**Interfaces:**
- Consumes: `SeverityProvenance` (Task 1).
- Produces:
  - `Provenance.prior_cohorts: tuple[str, ...] = ()`
  - `Licensing.severity_provenance: SeverityProvenance | None = None`
  - `PendingReason.SHARED_CAUSE_CONFIRMATORY = "shared_cause_confirmatory"`

- [ ] **Step 1: Write the failing test**

Create `grammar/tests/test_shared_cause_fields.py`:

```python
from polymer_grammar import (
    GenerationMode,
    PendingReason,
    Provenance,
    SeverityProvenance,
)
from polymer_grammar.licensing import (
    LicenseRoute,
    Licensing,
    MaterializationContext,
    RivalSetClosure,
    Satisfaction,
    SatisfactionVerdict,
)


def test_prior_cohorts_defaults_empty_and_accepts_tuple():
    p = Provenance(generated_by=GenerationMode.IMPORTED, search_cardinality=1)
    assert p.prior_cohorts == ()
    p2 = Provenance(
        generated_by=GenerationMode.LITERATURE_EXTRACTED,
        search_cardinality=1,
        prior_cohorts=("cohortA", "cohortB"),
    )
    assert p2.prior_cohorts == ("cohortA", "cohortB")


def _sat(dimnames: str | None = None) -> Satisfaction:
    return Satisfaction(
        verdict=SatisfactionVerdict.SATISFIED,
        materialization=MaterializationContext(
            id="M1", api_version="v1", data_version="d1", dimnames_hash=dimnames
        ),
    )


def test_licensing_severity_provenance_defaults_none_and_accepts_enum():
    lic = Licensing(
        route=LicenseRoute.SEVERE_TEST,
        satisfactions=(_sat(),),
        rival_set_closure=RivalSetClosure.OPEN_ACKNOWLEDGED,
    )
    assert lic.severity_provenance is None
    lic2 = lic.model_copy(update={"severity_provenance": SeverityProvenance.CONFIRMATORY})
    assert lic2.severity_provenance is SeverityProvenance.CONFIRMATORY


def test_pending_reason_has_shared_cause_member():
    assert PendingReason.SHARED_CAUSE_CONFIRMATORY.value == "shared_cause_confirmatory"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd grammar && uv run pytest tests/test_shared_cause_fields.py -q`
Expected: FAIL — `prior_cohorts`/`severity_provenance` rejected by `extra="forbid"` and `SHARED_CAUSE_CONFIRMATORY` missing.

- [ ] **Step 3: Write minimal implementation**

In `grammar/src/polymer_grammar/provenance.py`, add the field to `Provenance` (after `rationale`, before the validator):

```python
    # §5a literature-shared-cause: cohort identities (dimnames_hash namespace) that this
    # hypothesis's motivating prior was established on. Empty => no shared-cause info (inert).
    # Operator/agent-asserted (same trust model as adapter independence).
    prior_cohorts: tuple[str, ...] = ()
```

In `grammar/src/polymer_grammar/licensing.py`, add the import and the field. At the top imports add:

```python
from .shared_cause import SeverityProvenance
```

In the `Licensing` model (after `independence_tier`, before `note`):

```python
    severity_provenance: SeverityProvenance | None = None
```

In `grammar/src/polymer_grammar/status.py`, add to `PendingReason` (after `REINSTATED`):

```python
    # verify withheld a license under strict_shared_cause: the hypothesis prior shares a cohort
    # with the test data (confirmatory, not a held-out severe test)
    SHARED_CAUSE_CONFIRMATORY = "shared_cause_confirmatory"
```

> NOTE: `licensing.py` now imports `shared_cause.py`. Confirm no import cycle: `shared_cause.py` imports only `.strength` (Task 1), not `.licensing` — so `licensing -> shared_cause -> strength` is acyclic.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd grammar && uv run pytest tests/test_shared_cause_fields.py -q`
Expected: PASS.

- [ ] **Step 5: Run the full grammar suite (byte-identity of existing behavior)**

Run: `cd grammar && uv run pytest -q && uv run ruff check src tests`
Expected: PASS — every existing test green (additive fields default inert).

- [ ] **Step 6: Commit**

```bash
git add grammar/src/polymer_grammar/provenance.py grammar/src/polymer_grammar/licensing.py grammar/src/polymer_grammar/status.py grammar/tests/test_shared_cause_fields.py
git commit -m "feat(grammar): prior_cohorts + Licensing.severity_provenance + SHARED_CAUSE_CONFIRMATORY (Phase D slice 2)"
```

---

### Task 3: Protocol — VERIFY shared-cause gate

**Files:**
- Modify: `protocol/src/polymer_protocol/verify.py` (imports; add `_apply_shared_cause`; wire into the main license path; add `strict_shared_cause` param)
- Test: `protocol/tests/test_verify_shared_cause.py`

**Interfaces:**
- Consumes: `SeverityProvenance`, `severity_provenance_of`, `cap_severity_for_confirmatory` (grammar); existing `verify_stage(corpus, scaffolding, exec_records, oracles=None, adapter_registry=None, evidence=None, replications=None)`.
- Produces: `verify_stage(..., strict_shared_cause: bool = False)`; a licensed claim with non-empty `prior_cohorts` carries `licensing.severity_provenance` and (when CONFIRMATORY) a `severity`-capped strength; `strict_shared_cause=True` withholds CONFIRMATORY claims to PENDING with `PendingReason.SHARED_CAUSE_CONFIRMATORY`.

- [ ] **Step 1: Write the failing test**

Create `protocol/tests/test_verify_shared_cause.py`. This reuses the existing verify test harness conventions — build a corpus whose claim executes to a SATISFIED, agreed numeric result with a `dimnames_hash`, then call `verify_stage`. Use the existing helper module if one exists; otherwise construct via the public builders shown here.

```python
from polymer_grammar import (
    GenerationMode,
    Provenance,
    SeverityProvenance,
    Status,
)
from polymer_grammar.licensing import MaterializationContext
from polymer_protocol.verify import verify_stage

from tests.helpers_verify import (  # reuse the existing verify-test fixture builders
    licensable_corpus,   # -> (Corpus, CycleScaffolding, exec_records) for one claim "c1"
    with_dimnames,        # stamps a dimnames_hash onto c1's exec satisfaction
)


def _set_prior(corpus, claim_id, prior_cohorts):
    claims = tuple(
        c.model_copy(update={
            "provenance": (c.provenance or Provenance(
                generated_by=GenerationMode.LITERATURE_EXTRACTED, search_cardinality=1
            )).model_copy(update={"prior_cohorts": prior_cohorts})
        }) if c.id == claim_id else c
        for c in corpus.claims
    )
    return corpus.model_copy(update={"claims": claims})


def test_overlap_marks_confirmatory_and_caps_severity():
    corpus, scaff, recs = licensable_corpus()
    corpus, recs = with_dimnames(corpus, recs, "c1", "cohortX")
    corpus = _set_prior(corpus, "c1", ("cohortX",))  # prior overlaps the test cohort
    out = verify_stage(corpus, scaff, recs)
    c1 = out.by_id()["c1"]
    assert c1.status == Status.LICENSED
    assert c1.licensing.severity_provenance is SeverityProvenance.CONFIRMATORY
    assert c1.strength is not None and c1.strength.severity <= 0.2


def test_no_overlap_marks_held_out_no_cap():
    corpus, scaff, recs = licensable_corpus()
    corpus, recs = with_dimnames(corpus, recs, "c1", "cohortX")
    corpus = _set_prior(corpus, "c1", ("cohortY",))  # disjoint
    out = verify_stage(corpus, scaff, recs)
    c1 = out.by_id()["c1"]
    assert c1.status == Status.LICENSED
    assert c1.licensing.severity_provenance is SeverityProvenance.HELD_OUT


def test_strict_mode_withholds_confirmatory():
    from polymer_grammar import PendingReason
    corpus, scaff, recs = licensable_corpus()
    corpus, recs = with_dimnames(corpus, recs, "c1", "cohortX")
    corpus = _set_prior(corpus, "c1", ("cohortX",))
    out = verify_stage(corpus, scaff, recs, strict_shared_cause=True)
    c1 = out.by_id()["c1"]
    assert c1.status == Status.PENDING
    assert c1.pending_reason == PendingReason.SHARED_CAUSE_CONFIRMATORY


def test_no_prior_cohorts_is_byte_identical():
    corpus, scaff, recs = licensable_corpus()
    corpus, recs = with_dimnames(corpus, recs, "c1", "cohortX")
    out = verify_stage(corpus, scaff, recs)  # no prior_cohorts set
    c1 = out.by_id()["c1"]
    assert c1.status == Status.LICENSED
    assert c1.licensing.severity_provenance is None  # inert
```

> If `tests/helpers_verify.py` with `licensable_corpus`/`with_dimnames` does not already exist, create it in this step by extracting the corpus-builder already used by the existing `protocol/tests/test_verify*.py` (find it with `grep -rln "def .*licensable\|verify_stage(" protocol/tests`). The helper must return a corpus whose claim `c1` executes to an agreed SATISFIED numeric result and is in the grounded extension, so it licenses today. `with_dimnames` rewrites the exec record's `evaluation.satisfaction.materialization` to carry the given `dimnames_hash`.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd protocol && uv run pytest tests/test_verify_shared_cause.py -q`
Expected: FAIL — `verify_stage` has no `strict_shared_cause` kwarg / `severity_provenance` stays `None`.

- [ ] **Step 3: Write minimal implementation**

In `protocol/src/polymer_protocol/verify.py`, extend the grammar import block (the `from polymer_grammar import (...)` at the top) with:

```python
    SeverityProvenance,
    cap_severity_for_confirmatory,
    severity_provenance_of,
```

Add the helper above `verify_stage` (e.g. after `_with_status`):

```python
def _apply_shared_cause(
    claim: Claim,
    licensing: Licensing,
    strength: StrengthVector | None,
    strict: bool,
) -> tuple[Licensing, StrengthVector | None, bool]:
    """Annotate the license with its severity-provenance tier and (when CONFIRMATORY) cap the
    `severity` axis. Returns (licensing', strength', withhold). Inert when prior_cohorts is empty."""
    prior = claim.provenance.prior_cohorts if claim.provenance is not None else ()
    if not prior:
        return licensing, strength, False
    test_cohorts = tuple(
        s.materialization.dimnames_hash
        for s in licensing.satisfactions
        if s.materialization.dimnames_hash is not None
    )
    tier = severity_provenance_of(prior, test_cohorts)
    licensing = licensing.model_copy(update={"severity_provenance": tier})
    if tier == SeverityProvenance.CONFIRMATORY:
        if strict:
            return licensing, strength, True
        if strength is not None:
            strength = cap_severity_for_confirmatory(strength)
    return licensing, strength, False
```

Change the `verify_stage` signature to add the flag (append after `replications`):

```python
    replications: dict[str, tuple[Satisfaction, ...]] | None = None,
    strict_shared_cause: bool = False,
) -> Corpus:
```

In the main license path, replace the block that currently builds `licensing` and appends the LICENSED claim (the lines from `licensing = Licensing(...)` through the final `new_claims.append(_with_status(c, status=Status.LICENSED, ...))`). The new shape:

```python
            licensing = Licensing(
                route=LicenseRoute.SEVERE_TEST,
                satisfactions=sats,
                rival_set_closure=RivalSetClosure.OPEN_ACKNOWLEDGED,
                independence_tier=independence_tier_of(sats),
            )
            recorded = _recorded_strength(c)
            licensing, recorded, withhold = _apply_shared_cause(
                c, licensing, recorded, strict_shared_cause
            )
            if withhold:
                new_claims.append(_with_status(
                    c, status=Status.PENDING,
                    pending_reason=PendingReason.SHARED_CAUSE_CONFIRMATORY, licensing=None,
                ))
                continue
            if is_representation_revision(c):
                # ... (the existing MDL-gate block stays UNCHANGED — representation revisions are a
                # niche that does not carry methylation prior_cohorts; it builds its own mdl_licensing
                # and calls _recorded_strength(c) itself.)
                ...
            new_claims.append(
                _with_status(
                    c,
                    status=Status.LICENSED,
                    licensing=licensing,
                    pending_reason=None,
                    strength=recorded,
                )
            )
```

> Keep the existing MDL-gate body verbatim; only (a) move `licensing` construction to before it, (b) insert the `_apply_shared_cause` + `withhold` lines, and (c) feed the final non-MDL append `strength=recorded` instead of re-calling `_recorded_strength(c)`.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd protocol && uv run pytest tests/test_verify_shared_cause.py -q`
Expected: PASS (all four cases).

- [ ] **Step 5: Run the full protocol suite (byte-identity when off)**

Run: `cd protocol && uv run pytest -q && uv run ruff check src tests`
Expected: PASS — every existing verify test green (no `prior_cohorts` => inert).

- [ ] **Step 6: Commit**

```bash
git add protocol/src/polymer_protocol/verify.py protocol/tests/test_verify_shared_cause.py protocol/tests/helpers_verify.py
git commit -m "feat(protocol): VERIFY shared-cause gate — CONFIRMATORY tier + severity cap + strict withhold (Phase D slice 2)"
```

---

### Task 4: Protocol — data-blind severity-aware SELECT ranking

**Files:**
- Modify: `protocol/src/polymer_protocol/select.py` (import `DataHandle`; add `_severity_factor` + `CONFIRMATORY_RANK_PENALTY`; thread `cohort_of_ref` into `select_stage`; multiply into density)
- Test: `protocol/tests/test_select_shared_cause.py`

**Interfaces:**
- Consumes: `DataHandle` from `polymer_grammar`; `Provenance.prior_cohorts` (Task 2); existing `select_stage(corpus, *, cost_model, budget, value_weights, cost_weights, ledger=..., reserve_fraction=0.0, cell_cap_fraction=1.0)`.
- Produces: `select_stage(..., cohort_of_ref: Mapping[str, str] | None = None)`. With the mapping, a candidate whose plan `DataHandle.ref` resolves to a cohort in its own `prior_cohorts` gets a `CONFIRMATORY_RANK_PENALTY` (0.5) density multiplier; default `None` => factor 1.0 => byte-identical ordering.

- [ ] **Step 1: Write the failing test**

Create `protocol/tests/test_select_shared_cause.py`:

```python
from polymer_protocol.select import ValueWeights, select_stage

from tests.helpers_select import (  # reuse existing select-test fixture builders
    two_equal_candidates,  # -> Corpus with c_held, c_conf: identical value/cost; each plan has a
                           # DataHandle(ref="ds1"); both carry prior_cohorts via provenance:
                           #   c_held.prior_cohorts = ("other",)   (disjoint from ds1's cohort)
                           #   c_conf.prior_cohorts = ("cohortX",) (== cohort_of_ref["ds1"])
    SIMPLE_COST,           # a CostModel resolving every claim to cost 1.0
    SIMPLE_COST_WEIGHTS,
)


def _rank(record, claim_id):
    return next(d.rank for d in record.decisions if d.claim_id == claim_id)


def test_confirmatory_candidate_ranks_below_held_out():
    corpus = two_equal_candidates()
    _, rec = select_stage(
        corpus, cost_model=SIMPLE_COST, budget=None,
        value_weights=ValueWeights(), cost_weights=SIMPLE_COST_WEIGHTS,
        cohort_of_ref={"ds1": "cohortX"},
    )
    assert _rank(rec, "c_held") < _rank(rec, "c_conf")  # held-out ranked first


def test_ranking_is_data_blind_default_is_byte_identical():
    corpus = two_equal_candidates()
    # No cohort_of_ref => severity factor inert => ordering is the pre-feature ordering.
    _, rec_off = select_stage(
        corpus, cost_model=SIMPLE_COST, budget=None,
        value_weights=ValueWeights(), cost_weights=SIMPLE_COST_WEIGHTS,
    )
    # the factor reads only provenance + plan identity, never executes; passing the map must not
    # require any materialized data — same call, identical decisions for the disjoint candidate.
    assert _rank(rec_off, "c_held") == _rank(rec_off, "c_held")
    # and with the map, the held-out candidate's own rank is unchanged vs off for the disjoint one
    _, rec_on = select_stage(
        corpus, cost_model=SIMPLE_COST, budget=None,
        value_weights=ValueWeights(), cost_weights=SIMPLE_COST_WEIGHTS,
        cohort_of_ref={"ds1": "cohortX"},
    )
    assert _rank(rec_on, "c_held") <= _rank(rec_off, "c_held")
```

> Build `tests/helpers_select.py` if absent (extract from the existing `protocol/tests/test_select*.py`). `two_equal_candidates` must yield two PENDING candidates with an `evaluation_plan` whose graph has one node with a `DataHandle(ref="ds1")` input, equal cost and equal value-vector (so neither is on the Pareto front — equal vectors mutually dominate — and density is the only differentiator). `SIMPLE_COST` resolves both to 1.0.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd protocol && uv run pytest tests/test_select_shared_cause.py -q`
Expected: FAIL — `select_stage` has no `cohort_of_ref` kwarg.

- [ ] **Step 3: Write minimal implementation**

In `protocol/src/polymer_protocol/select.py`, add imports + the typing import at the top:

```python
from collections.abc import Mapping
```

Extend the grammar import to include `DataHandle`:

```python
from polymer_grammar import (
    Claim,
    DataHandle,
    GenerationMode,
    Provenance,
    Status,
    requires_safety_review,
)
```

Add the module constant + helper (near `_density`):

```python
# Tunable: a candidate whose plan target cohort overlaps its own prior-derivation cohorts is a
# confirmatory (weak severe) test, so its fill-order density is discounted. 1.0 == inert.
CONFIRMATORY_RANK_PENALTY: float = 0.5


def _severity_factor(claim: Claim, cohort_of_ref: Mapping[str, str]) -> float:
    """Data-blind: reads only the claim's prior_cohorts provenance and its plan's DataHandle refs
    (resolved to cohort ids via the injected map). Never executes / reads test data. 1.0 unless a
    confirmatory overlap is provable from metadata."""
    prior = claim.provenance.prior_cohorts if claim.provenance is not None else ()
    if not prior or not cohort_of_ref or claim.evaluation_plan is None:
        return 1.0
    targets = {
        cohort_of_ref[i.ref]
        for n in claim.evaluation_plan.graph.nodes
        for i in n.inputs
        if isinstance(i, DataHandle) and i.ref in cohort_of_ref
    }
    if not targets:
        return 1.0
    return CONFIRMATORY_RANK_PENALTY if (set(prior) & targets) else 1.0
```

Thread the param into `select_stage`. Change the signature (append after `cell_cap_fraction`):

```python
    cell_cap_fraction: float = 1.0,
    cohort_of_ref: Mapping[str, str] | None = None,
) -> tuple[Corpus, SelectionRecord]:
```

Right after `candidates = [...]` and the `m == 0` guard, build the factor map:

```python
    cmap = cohort_of_ref or {}
    sev_of = {c.id: _severity_factor(c, cmap) for c in candidates}
```

Multiply the factor into the fill-order density (the inner `density` function):

```python
    def density(item) -> float:
        c, value, cost, cell, credit = item
        return _density(value, cost, value_weights) * credit * sev_of[c.id]
```

> The Pareto `front_ids` (computed on the raw value vector) is intentionally NOT penalized — the factor only affects fill-order density, exactly like `credit` today. Two equal-value candidates are both off-front (equal vectors mutually dominate), so density (hence the factor) decides their order.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd protocol && uv run pytest tests/test_select_shared_cause.py -q`
Expected: PASS.

- [ ] **Step 5: Run the full protocol suite (byte-identity when off)**

Run: `cd protocol && uv run pytest -q && uv run ruff check src tests`
Expected: PASS — existing select tests green (no `cohort_of_ref` => `sev_of` all 1.0).

- [ ] **Step 6: Commit**

```bash
git add protocol/src/polymer_protocol/select.py protocol/tests/test_select_shared_cause.py protocol/tests/helpers_select.py
git commit -m "feat(protocol): data-blind severity-aware SELECT ranking via injected cohort_of_ref (Phase D slice 2)"
```

---

### Task 5: Protocol — budget-aware incubation commit (`register_selected`)

**Files:**
- Modify: `protocol/src/polymer_protocol/register.py` (add `register_selected`)
- Modify: `protocol/src/polymer_protocol/__init__.py` (export `register_selected`)
- Test: `protocol/tests/test_register_selected.py`

**Interfaces:**
- Consumes: existing `register_hypotheses(corpus, claim_ids=None)`; `SelectionRecord` (`corpus.py`) with `decisions: tuple[SelectionDecision, ...]`, each `SelectionDecision(claim_id, selected, value, cost, rank, cell, lane)`.
- Produces: `register_selected(corpus: Corpus, record: SelectionRecord, *, k: int | None = None) -> Corpus` — registers (e-LOND slot) only the SELECT-selected claims in rank order, optionally truncated to top-`k`. Non-selected candidates are never charged.

- [ ] **Step 1: Write the failing test**

Create `protocol/tests/test_register_selected.py`:

```python
from polymer_protocol.register import register_selected
from polymer_protocol.select import ValueWeights, select_stage

from tests.helpers_select import SIMPLE_COST, SIMPLE_COST_WEIGHTS, two_equal_candidates


def _pending_ids(corpus):
    return {t.claim_id for t in corpus.fdr_ledger.tests if t.e_value is None and not t.retracted}


def test_registers_only_selected_topk():
    corpus = two_equal_candidates()  # both selected when budget is unbounded
    out, rec = select_stage(
        corpus, cost_model=SIMPLE_COST, budget=None,
        value_weights=ValueWeights(), cost_weights=SIMPLE_COST_WEIGHTS,
        cohort_of_ref={"ds1": "cohortX"},
    )
    # pursue only the top-1 by rank -> exactly one e-LOND slot charged
    reg = register_selected(out, rec, k=1)
    pending = _pending_ids(reg)
    assert len(pending) == 1
    # the charged one is the rank-0 (held-out) candidate
    assert "c_held" in pending and "c_conf" not in pending


def test_unselected_candidates_are_not_charged():
    corpus = two_equal_candidates()
    # tiny budget so SELECT picks only one candidate
    out, rec = select_stage(
        corpus, cost_model=SIMPLE_COST, budget=1.0,
        value_weights=ValueWeights(), cost_weights=SIMPLE_COST_WEIGHTS,
        cohort_of_ref={"ds1": "cohortX"},
    )
    reg = register_selected(out, rec)
    selected = {d.claim_id for d in rec.decisions if d.selected}
    assert _pending_ids(reg) == selected
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd protocol && uv run pytest tests/test_register_selected.py -q`
Expected: FAIL — `cannot import name 'register_selected'`.

- [ ] **Step 3: Write minimal implementation**

In `protocol/src/polymer_protocol/register.py`, extend the corpus import and add the function:

```python
from .corpus import Corpus, SelectionRecord
```

```python
def register_selected(
    corpus: Corpus, record: SelectionRecord, *, k: int | None = None
) -> Corpus:
    """Budget-aware incubation commit: register (e-LOND slot, slice-1 register_test) only the
    SELECT-selected claims, in rank order, optionally truncated to top-k. Non-selected/incubated
    candidates are NOT charged — honest because SELECT ranking is data-blind (it did not peek at
    the outcome)."""
    ranked = [
        d.claim_id for d in sorted(record.decisions, key=lambda d: d.rank) if d.selected
    ]
    if k is not None:
        ranked = ranked[:k]
    return register_hypotheses(corpus, ranked)
```

In `protocol/src/polymer_protocol/__init__.py`, add `register_selected` to the `from .register import ...` line and to `__all__`.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd protocol && uv run pytest tests/test_register_selected.py -q && uv run ruff check src tests`
Expected: PASS, ruff clean.

- [ ] **Step 5: Commit**

```bash
git add protocol/src/polymer_protocol/register.py protocol/src/polymer_protocol/__init__.py protocol/tests/test_register_selected.py
git commit -m "feat(protocol): register_selected — budget-aware top-k incubation commit (Phase D slice 2)"
```

---

### Task 6: Viewer — surface `severity_provenance` (minimal, mirror `independence_tier`)

**Files:**
- Modify: `protocol/src/polymer_protocol/topology.py:40-56` (add `TopologyNode.severity_provenance`) + `:110-129` (populate it)
- Modify: `viewer/src/lib/topology.ts:41` · `viewer/src/lib/interpolate.ts:40,133,155,181` · `viewer/src/components/scene/Nodes.tsx:178,196` · `viewer/src/components/scene/Edges.tsx:43` · `viewer/src/components/chrome/RightRail.tsx:447-448` (mirror `independence_tier`)
- Test: `protocol/tests/test_topology_severity_provenance.py`

**Interfaces:**
- Consumes: `Licensing.severity_provenance` (Task 2).
- Produces: `TopologyNode.severity_provenance: str | None`; viewer RightRail shows the tier next to `independence_tier`.

> Contract version stays `"1.0"`: the field is optional both directions (Python defaults `None`; the viewer reads `?? null`), so old sample timelines load without warning. No sample regeneration.

- [ ] **Step 1: Write the failing test**

Create `protocol/tests/test_topology_severity_provenance.py`:

```python
from polymer_grammar import SeverityProvenance

from polymer_protocol.topology import export_topology  # the public export entrypoint

from tests.helpers_verify import licensable_corpus, with_dimnames  # from Task 3
from polymer_protocol.verify import verify_stage
from polymer_grammar import GenerationMode, Provenance


def _licensed_confirmatory_corpus():
    corpus, scaff, recs = licensable_corpus()
    corpus, recs = with_dimnames(corpus, recs, "c1", "cohortX")
    claims = tuple(
        c.model_copy(update={"provenance": Provenance(
            generated_by=GenerationMode.LITERATURE_EXTRACTED, search_cardinality=1,
            prior_cohorts=("cohortX",),
        )}) if c.id == "c1" else c
        for c in corpus.claims
    )
    corpus = corpus.model_copy(update={"claims": claims})
    return verify_stage(corpus, scaff, recs)


def test_topology_node_carries_severity_provenance():
    corpus = _licensed_confirmatory_corpus()
    export = export_topology(corpus)
    n = next(n for n in export.nodes if n.id == "c1")
    assert n.severity_provenance == SeverityProvenance.CONFIRMATORY.value


def test_topology_node_severity_provenance_none_when_absent():
    from tests.helpers_verify import licensable_corpus as lc
    corpus, scaff, recs = lc()
    out = verify_stage(corpus, scaff, recs)
    export = export_topology(out)
    n = next(n for n in export.nodes if n.id == "c1")
    assert n.severity_provenance is None
```

> Confirm the public export entrypoint name with `grep -n "^def export_topology\|def export_topology" protocol/src/polymer_protocol/topology.py`; if it differs, use that name. If `export_topology` requires a `positions`/layout argument, pass the same default the existing topology tests use (`grep -rn "export_topology(" protocol/tests`).

- [ ] **Step 2: Run test to verify it fails**

Run: `cd protocol && uv run pytest tests/test_topology_severity_provenance.py -q`
Expected: FAIL — `TopologyNode` has no `severity_provenance` (`extra="forbid"`).

- [ ] **Step 3: Write minimal implementation (Python)**

In `protocol/src/polymer_protocol/topology.py`, add the field to `TopologyNode` (after `independence_tier`):

```python
    severity_provenance: str | None = None
```

In `_extract_nodes`, add to the `TopologyNode(...)` constructor (after the `independence_tier=...` block):

```python
                severity_provenance=(
                    c.licensing.severity_provenance.value
                    if c.licensing is not None and c.licensing.severity_provenance is not None
                    else None
                ),
```

- [ ] **Step 4: Run the Python test to verify it passes**

Run: `cd protocol && uv run pytest tests/test_topology_severity_provenance.py -q && uv run pytest -q`
Expected: PASS, full protocol suite green.

- [ ] **Step 5: Mirror the viewer TS sites**

In each TS file, add `severity_provenance` immediately alongside every `independence_tier` occurrence, with the same `?? null` pattern:

- `viewer/src/lib/topology.ts:41` — in the node type, after `independence_tier?: string | null;` add:
  ```ts
  severity_provenance?: string | null;
  ```
- `viewer/src/lib/interpolate.ts` — at lines 40, 133, 155, 181, mirror each `independence_tier` line. The type field (line ~40):
  ```ts
  severity_provenance: string | null;
  ```
  and each object literal (lines ~133, ~155, ~181) that has `independence_tier: nX.independence_tier ?? null,` gets a sibling:
  ```ts
  severity_provenance: nX.severity_provenance ?? null,
  ```
  (use the same `na`/`nb` variable that the neighboring `independence_tier` line uses).
- `viewer/src/components/scene/Nodes.tsx` — line ~178 (type) add `severity_provenance?: string | null;`; line ~196 (mapping) add `severity_provenance: n.severity_provenance ?? null,`.
- `viewer/src/components/scene/Edges.tsx` — line ~43 add `severity_provenance: n.severity_provenance ?? null,`.
- `viewer/src/components/chrome/RightRail.tsx` — after the `independence_tier` row (lines 447-448) add a sibling row:
  ```tsx
  <div style={label}>severity_provenance</div>
  <TierPill tier={node.severity_provenance ?? null} />
  ```
  (Reuse the existing `TierPill`; it already renders a nullable string tier.)

- [ ] **Step 6: Typecheck + build the viewer**

Run: `cd viewer && npm run typecheck && npm run build`
Expected: both succeed (the additive optional field threads through every site).

- [ ] **Step 7: Commit**

```bash
git add protocol/src/polymer_protocol/topology.py protocol/tests/test_topology_severity_provenance.py viewer/src/lib/topology.ts viewer/src/lib/interpolate.ts viewer/src/components/scene/Nodes.tsx viewer/src/components/scene/Edges.tsx viewer/src/components/chrome/RightRail.tsx
git commit -m "feat(viewer): surface severity_provenance alongside independence_tier (Phase D slice 2)"
```

---

### Task 7: Full gate + byte-identity golden + docs

**Files:**
- Test: `protocol/tests/test_shared_cause_byte_identical.py`
- Modify: `docs/superpowers/CONTINUE.md` (Current state + NEXT + Done checklist)

**Interfaces:** none new — this task verifies the whole slice and updates the running build log.

- [ ] **Step 1: Write the byte-identical golden test**

Create `protocol/tests/test_shared_cause_byte_identical.py` — a `run_cycle` (or verify+select pass) with NO `prior_cohorts` and NO `cohort_of_ref` must equal a run from before this feature. Use the existing end-to-end cycle fixture:

```python
from tests.helpers_cycle import run_one_cycle  # the existing whole-cycle fixture/helper


def test_cycle_with_no_prior_cohorts_is_unchanged():
    # No claim carries prior_cohorts and no cohort_of_ref is supplied -> every new code path is
    # inert. The resulting corpus (claims, ledger, statuses, strengths, licensing) must match the
    # pre-feature golden exactly.
    before = run_one_cycle(feature_off=True)   # baseline path (no shared-cause inputs)
    after = run_one_cycle()                    # same inputs, feature code present but inert
    assert before == after
```

> If no `helpers_cycle.run_one_cycle` exists, assert byte-identity directly: build a small corpus that licenses one claim with `prior_cohorts == ()`, run `verify_stage(...)` and `select_stage(...)`, and assert `licensing.severity_provenance is None`, the strength vector is unchanged from the pre-cap value, and the `SelectionRecord.decisions` order matches a `select_stage` call without `cohort_of_ref`. (The existing per-package suites already enforce this broadly; this test makes the inert-when-off contract explicit.)

- [ ] **Step 2: Run the test**

Run: `cd protocol && uv run pytest tests/test_shared_cause_byte_identical.py -q`
Expected: PASS.

- [ ] **Step 3: Run the full gate**

Run: `bash scripts/check-all.sh`
Expected: GREEN — grammar + protocol + umbrella pytest, ruff, isolation tests, viewer typecheck + build all pass. Record the new test counts (grammar/protocol totals will be higher than the 261/372/377 baseline).

- [ ] **Step 4: Update `docs/superpowers/CONTINUE.md`**

In **Current state**, bump the test counts to the `check-all.sh` output and add a one-line "Phase D slice 2 shipped" note. In **▶ NEXT → Recently shipped**, prepend:

```
**Phase D slice 2 — literature-shared-cause gate + incubation/ranking: a hypothesis records the
cohorts its motivating prior was established on (`Provenance.prior_cohorts`); overlap with the test
cohort → `severity_provenance=CONFIRMATORY` license + `severity`-axis cap (strict mode withholds).
The same data-blind signal feeds SELECT ranking (injected `cohort_of_ref`) + `register_selected`
budget-aware top-k commit. First concrete edge of north-star §E. Additive/byte-identical when off;
merged YYYY-MM-DD.**
```

In the **Done checklist** (Phase 2 epistemic-core section), add a `✅` bullet mirroring the slice-1 entry, citing spec+plan `docs/superpowers/{specs,plans}/2026-06-19-shared-cause-incubation*`. Update the **Deferred Phase-D slices** line to drop "literature-shared-cause" and keep incubation-strict-mode / live-agent wiring / fuzzy literature→cohort resolution / full §E DAG.

- [ ] **Step 5: Commit the docs**

```bash
git add docs/superpowers/CONTINUE.md protocol/tests/test_shared_cause_byte_identical.py
git commit -m "docs(CONTINUE): Phase D slice 2 shipped — shared-cause gate + incubation/ranking"
```

- [ ] **Step 6: Merge to main (`--no-ff`) + push**

```bash
# from the feature branch:
git checkout main && git merge --no-ff - -m "Merge Phase D slice 2: literature-shared-cause gate + incubation/ranking"
bash scripts/check-all.sh        # re-confirm green on the merge commit
git push origin main
```

---

## Self-Review

**Spec coverage:**
- §3.1 `Provenance.prior_cohorts` → Task 2. ✅
- §3.2 `shared_cause.py` (enum, overlap, `severity_provenance_of`, ceiling, cap) → Task 1. ✅
- §3.3 `Licensing.severity_provenance` → Task 2. ✅
- §4.1 VERIFY gate (tier stamp + severity cap + strict withhold + byte-identity) → Task 3. ✅
- §4.2 data-blind SELECT ranking + injected `cohort_of_ref` → Task 4. ✅
- §4.3 `register_selected` budget-aware top-k → Task 5. ✅
- §5 viewer passthrough + minimal display → Task 6. ✅
- §7 success criteria 1-8 → Tasks 3 (1,2,3), 4 (4,5), 5 (6), 1/7 (7 byte-identical), 1+3 (8 invariants). ✅
- §6 invariants (Corpus=4, numpy-free, isolation) → Task 1 step 5 + Task 7 step 3. ✅

**Placeholder scan:** the `...` in Task 3 step 3 explicitly marks the *unchanged* existing MDL block (instructed verbatim-keep), not omitted new code. Helper-builder fallbacks (Tasks 3/4/6) give exact `grep` locators + the precise contract the helper must satisfy — not "TBD". No "add error handling"/"write tests for the above" anywhere.

**Type consistency:** `prior_cohorts: tuple[str, ...]` and `cohort_of_ref: Mapping[str, str]` are dimnames-namespace strings end-to-end; `SeverityProvenance` members `HELD_OUT`/`CONFIRMATORY` used identically in grammar (Task 1/2), protocol (Task 3), and `.value` strings in topology/viewer (Task 6); `register_selected(corpus, record, *, k=None)` signature matches its Task-5 call sites; `severity_provenance_of`/`cap_severity_for_confirmatory`/`shared_cause_overlap` signatures identical across Tasks 1, 3, 4. Constants `CONFIRMATORY_SEVERITY_CEILING = 0.2` (grammar) and `CONFIRMATORY_RANK_PENALTY = 0.5` (protocol/select) referenced consistently.
