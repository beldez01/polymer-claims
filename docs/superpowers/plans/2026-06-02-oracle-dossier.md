# Oracle Dossier (Protocol #2) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bind `OperationNode.oracle_ref` to a real `OracleDossier` and cap a claim's empirical strength axes by its weakest oracle's validation tier, enforced at the LICENSED seam in `verify_stage`.

**Architecture:** A new grammar module `oracle.py` ships the dossier IR + pure capping math (`tier_ceiling`/`cap_strength`/`in_domain`/`referenced_oracle_ids`/`weakest_tier`); a thin protocol `oracle.py` ships the registry + resolution policy (`oracle_cap`), wired into `verify_stage`'s LICENSED branch and threaded through `run_cycle`. The whole mechanism is one pure idea — tier → empirical-axis ceiling applied via `StrengthVector.meet` — with unresolved/out-of-domain folding to effective `UNVALIDATED`. No new status, no new grammar field; `Corpus` stays at four collections.

**Tech Stack:** Python ≥3.12, Pydantic v2 (frozen, tuples-only), `uv`, pytest, ruff. Spans the `grammar/` (`polymer_grammar`) and `protocol/` (`polymer_protocol`) packages.

**Spec:** `docs/superpowers/specs/2026-06-02-oracle-dossier-design.md` (approved, committed `fd32172`).

**Working agreements (don't relearn):**
- All models subclass a frozen `_Model` (`extra="forbid"`, tuples not lists/dicts). Enums are `str, Enum` (JSON-faithful); ordering via an explicit rank dict (mirrors `revision._STATUS_TIER`).
- TDD: failing test first. After each task run the relevant suite + ruff:
  - grammar: `cd grammar && uv run pytest -q` + `uv run ruff check src tests`
  - protocol: `cd protocol && uv run pytest -q` + `uv run ruff check src tests`
- Commit after every task. Commit messages end (after a blank line) with:
  `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`
- `grammar/` must NEVER import `polymer_protocol` or `polymer_formalclaim`. `protocol/` depends one-way on `polymer_grammar`.
- Work from `/Users/zbb2/Desktop/polymer-claims`, stay on the implementation branch (don't branch/switch inside a task).

**Verified grammar APIs this plan uses:**
- `StrengthVector(magnitude, uncertainty, evidence_against_null, severity, world_contact, explanatory_virtue)` — all floats in [0,1]; `.meet(other)` = componentwise min; `AXES` = the 6 axis-name strings (exported from `polymer_grammar`).
- `EvaluationPlan.graph.nodes` → tuple of `OperationNode`; each `OperationNode` has `.oracle_ref: str | None` (already exists, Phase 8).
- `Subject` is a discriminated union; every variant has `.kind` (a literal string, e.g. `"genomic_region"`). Exported from `polymer_grammar`.
- `GenomicRegion(id: str, display: str, assembly: str, chrom: str, start: int, end: int, strand=".")` — the simplest concrete subject for tests (`kind == "genomic_region"`); `start <= end` required.
- `Claim` has `.strength` (`StrengthVector | None`), `.evaluation_plan` (`EvaluationPlan | None`), `.subject` (`Subject | None`).
- Operations builders for test plans: `OperationNode(id, impl, params, produces, oracle_ref)`, `ComputeGraph(nodes, terminal)`, `EvaluationPlan(graph, criterion)`, `SatisfactionCriterion(comparator, threshold)`, `Comparator.LT`, `ProducedLeafSpec(leaf_kind, measurement_basis)`, `MeasurementBasis.DERIVED`.
- Protocol conftest helpers (`protocol/tests/conftest.py`): `make_claim(cid, status=CONJECTURED, *, plan=None, pending_reason=None, strength=None, **extra)` and `make_plan(value, threshold, comparator=LT)`; fixtures `ctx`, `adapters`, `empty_ledger`.

---

## File Structure

```
grammar/src/polymer_grammar/
  oracle.py        # NEW — ValidationTier + ceilings + cap math (Task 1); dossier + domain + refs (Task 2)
  __init__.py      # MODIFY (Task 2) — export the 8 oracle symbols
grammar/tests/
  test_oracle.py   # NEW (Task 1 cap-math tests; Task 2 dossier/domain/refs tests)
protocol/src/polymer_protocol/
  oracle.py        # NEW (Task 3) — OracleRegistry + _effective_tier + oracle_cap
  verify.py        # MODIFY (Task 4) — verify_stage gains `oracles`; caps strength on LICENSED
  cycle.py         # MODIFY (Task 5) — run_cycle gains `oracles`, threads to verify_stage
  __init__.py      # MODIFY (Task 3) — export OracleRegistry/oracle_cap + re-export grammar oracle types
protocol/tests/
  conftest.py      # MODIFY (Task 3) — make_plan gains an oracle_ref kwarg
  test_oracle.py   # NEW (Task 3)
  test_verify.py   # MODIFY (Task 4)
  test_cycle.py    # MODIFY (Task 5)
```

---

### Task 1: Grammar — validation tiers + the strength-cap math

**Files:**
- Create: `grammar/src/polymer_grammar/oracle.py`
- Test: `grammar/tests/test_oracle.py`

- [ ] **Step 1: Write the failing tests**

Create `grammar/tests/test_oracle.py`:

```python
from polymer_grammar import StrengthVector, ValidationTier, cap_strength, tier_ceiling, weakest_tier


def test_weakest_tier_picks_lowest_rank():
    assert weakest_tier(
        [ValidationTier.GOLD, ValidationTier.INDIRECT, ValidationTier.ANCHORED]
    ) == ValidationTier.INDIRECT


def test_weakest_tier_single():
    assert weakest_tier([ValidationTier.BENCHMARKED]) == ValidationTier.BENCHMARKED


def test_weakest_tier_empty_is_gold_identity():
    # GOLD's ceiling is all-1.0, so "no oracle" -> GOLD -> no cap.
    assert weakest_tier([]) == ValidationTier.GOLD


def test_tier_ceiling_caps_empirical_leaves_theory_at_one():
    c = tier_ceiling(ValidationTier.INDIRECT)
    assert c.magnitude == 0.4
    assert c.uncertainty == 0.4
    assert c.evidence_against_null == 0.4
    assert c.world_contact == 0.4
    assert c.severity == 1.0            # theory axis uncapped
    assert c.explanatory_virtue == 1.0  # theory axis uncapped


def test_tier_ceiling_gold_is_all_one():
    c = tier_ceiling(ValidationTier.GOLD)
    assert all(
        getattr(c, ax) == 1.0
        for ax in ("magnitude", "uncertainty", "evidence_against_null",
                   "severity", "world_contact", "explanatory_virtue")
    )


def test_tier_ceiling_monotone_on_empirical_axis():
    order = [ValidationTier.UNVALIDATED, ValidationTier.INDIRECT,
             ValidationTier.BENCHMARKED, ValidationTier.ANCHORED, ValidationTier.GOLD]
    vals = [tier_ceiling(t).magnitude for t in order]
    assert vals == sorted(vals)
    assert vals[0] == 0.0 and vals[-1] == 1.0


def test_cap_strength_caps_only_empirical():
    s = StrengthVector(magnitude=0.9, uncertainty=0.9, evidence_against_null=0.9,
                       severity=0.9, world_contact=0.9, explanatory_virtue=0.9)
    capped = cap_strength(s, ValidationTier.INDIRECT)
    assert capped.magnitude == 0.4
    assert capped.uncertainty == 0.4
    assert capped.evidence_against_null == 0.4
    assert capped.world_contact == 0.4
    assert capped.severity == 0.9            # untouched
    assert capped.explanatory_virtue == 0.9  # untouched


def test_cap_strength_by_gold_is_unchanged():
    s = StrengthVector(magnitude=0.7, uncertainty=0.3, evidence_against_null=0.5,
                       severity=0.6, world_contact=0.2, explanatory_virtue=0.8)
    assert cap_strength(s, ValidationTier.GOLD) == s


def test_cap_strength_by_unvalidated_zeroes_empirical():
    s = StrengthVector(magnitude=0.7, uncertainty=0.7, evidence_against_null=0.7,
                       severity=0.7, world_contact=0.7, explanatory_virtue=0.7)
    capped = cap_strength(s, ValidationTier.UNVALIDATED)
    assert capped.magnitude == 0.0
    assert capped.world_contact == 0.0
    assert capped.severity == 0.7            # untouched
    assert capped.explanatory_virtue == 0.7


def test_cap_strength_none_is_none():
    assert cap_strength(None, ValidationTier.GOLD) is None
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd grammar && uv run pytest tests/test_oracle.py -q`
Expected: FAIL with `ImportError: cannot import name 'ValidationTier' from 'polymer_grammar'`.

- [ ] **Step 3: Write `grammar/src/polymer_grammar/oracle.py`**

```python
"""oracle.py — the oracle credibility dossier (unified spec §5 #2 / daemon D2).

Represents how an oracle (API endpoint / R routine / assay) was validated, and caps the
EMPIRICAL strength axes of any claim it grounds by the oracle's validation tier. The grammar
ships the IR + the pure capping math; the protocol decides policy (resolution + the
LICENSED-seam cap). The tier is about the APPARATUS, never the claim's literature precedent.
Imports nothing from polymer_formalclaim.
"""
from __future__ import annotations

from collections.abc import Iterable
from enum import Enum

from .strength import AXES, StrengthVector


class ValidationTier(str, Enum):
    UNVALIDATED = "unvalidated"      # no dossier / unresolved / out-of-domain
    INDIRECT = "indirect"            # checked against literature-reported / heuristic values
    BENCHMARKED = "benchmarked"      # against a computational ground-truth set
    ANCHORED = "anchored"            # against a direct wet-lab/clinical anchor, bounded domain
    GOLD = "gold"                    # gold-standard, broadly validated


# str-Enum (JSON-faithful) -> explicit rank for ordering, mirroring revision._STATUS_TIER.
_TIER_RANK = {
    ValidationTier.UNVALIDATED: 0,
    ValidationTier.INDIRECT: 1,
    ValidationTier.BENCHMARKED: 2,
    ValidationTier.ANCHORED: 3,
    ValidationTier.GOLD: 4,
}

# Empirical (apparatus-bounded) axes the ceiling caps. severity + explanatory_virtue are
# test-design / theory axes (set by argument, not apparatus) -> never capped.
_EMPIRICAL_AXES = ("magnitude", "uncertainty", "evidence_against_null", "world_contact")

# v1 empirical-axis ceiling per tier (monotone; endpoints pinned at 0.0/1.0; tunable).
_TIER_CEILING = {
    ValidationTier.UNVALIDATED: 0.0,
    ValidationTier.INDIRECT: 0.4,
    ValidationTier.BENCHMARKED: 0.6,
    ValidationTier.ANCHORED: 0.85,
    ValidationTier.GOLD: 1.0,
}


def weakest_tier(tiers: Iterable[ValidationTier]) -> ValidationTier:
    """The lowest-rank tier (a chain is only as strong as its weakest oracle). Empty -> GOLD,
    the no-constraint identity (GOLD's ceiling is all-1.0, so capping by it is a no-op)."""
    ts = list(tiers)
    if not ts:
        return ValidationTier.GOLD
    return min(ts, key=lambda t: _TIER_RANK[t])


def tier_ceiling(tier: ValidationTier) -> StrengthVector:
    """The per-axis strength ceiling a tier imposes: empirical axes carry the tier ceiling;
    theory axes (severity, explanatory_virtue) stay at 1.0 (uncapped)."""
    c = _TIER_CEILING[tier]
    return StrengthVector(**{ax: (c if ax in _EMPIRICAL_AXES else 1.0) for ax in AXES})


def cap_strength(
    strength: StrengthVector | None, tier: ValidationTier
) -> StrengthVector | None:
    """`strength` meet the tier ceiling (componentwise min) — caps only the empirical axes
    (theory-axis ceilings are 1.0). None in -> None out (nothing to cap)."""
    if strength is None:
        return None
    return strength.meet(tier_ceiling(tier))
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd grammar && uv run pytest tests/test_oracle.py -q`
Expected: 10 passed.

- [ ] **Step 5: Lint + commit**

```bash
cd grammar && uv run ruff check src tests
git add grammar/src/polymer_grammar/oracle.py grammar/tests/test_oracle.py
git commit -m "feat(grammar): oracle validation tiers + empirical-axis strength cap"
```

---

### Task 2: Grammar — the dossier IR, domain check, plan-ref walk + exports

**Files:**
- Modify: `grammar/src/polymer_grammar/oracle.py`
- Modify: `grammar/src/polymer_grammar/__init__.py`
- Test: `grammar/tests/test_oracle.py` (append)

- [ ] **Step 1: Append the failing tests to `grammar/tests/test_oracle.py`**

```python
import pytest
from polymer_grammar import (
    ApplicabilityDomain,
    Comparator,
    ComputeGraph,
    EvaluationPlan,
    GenomicRegion,
    MeasurementBasis,
    OperationNode,
    OracleDossier,
    ProducedLeafSpec,
    SatisfactionCriterion,
    in_domain,
    referenced_oracle_ids,
)
from pydantic import ValidationError


def _region():
    return GenomicRegion(
        id="r1", display="chr1:1-100", assembly="GRCh38", chrom="chr1", start=1, end=100
    )


def test_dossier_requires_nonempty_oracle_id():
    with pytest.raises(ValidationError):
        OracleDossier(oracle_id="", validation_tier=ValidationTier.GOLD)


def test_dossier_defaults_unbounded_domain():
    d = OracleDossier(oracle_id="o1", validation_tier=ValidationTier.GOLD)
    assert d.applicability_domain.subject_kinds == ()
    assert d.relative_uncertainty is None


def test_in_domain_unbounded_accepts_anything_including_none():
    dom = ApplicabilityDomain()  # no subject_kinds -> unbounded
    assert in_domain(dom, _region()) is True
    assert in_domain(dom, None) is True


def test_in_domain_bounded_matches_kind():
    dom = ApplicabilityDomain(subject_kinds=("genomic_region",))
    assert in_domain(dom, _region()) is True


def test_in_domain_bounded_rejects_other_kind_and_none():
    dom = ApplicabilityDomain(subject_kinds=("variant_vrs",))
    assert in_domain(dom, _region()) is False   # genomic_region not listed
    assert in_domain(dom, None) is False         # bounded + no subject -> conservative


def _plan_with_refs(*refs):
    nodes = tuple(
        OperationNode(
            id=f"n{i}", impl="builtin::const", params=(("value", "0.0"),),
            produces=ProducedLeafSpec(leaf_kind="quantity", measurement_basis=MeasurementBasis.DERIVED),
            oracle_ref=r,
        )
        for i, r in enumerate(refs)
    )
    return EvaluationPlan(
        graph=ComputeGraph(nodes=nodes, terminal="n0"),
        criterion=SatisfactionCriterion(comparator=Comparator.LT, threshold=0.05),
    )


def test_referenced_oracle_ids_collects_non_none():
    plan = _plan_with_refs("api-A", None, "engine-b")
    assert referenced_oracle_ids(plan) == frozenset({"api-A", "engine-b"})


def test_referenced_oracle_ids_empty_when_all_none():
    plan = _plan_with_refs(None, None)
    assert referenced_oracle_ids(plan) == frozenset()
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd grammar && uv run pytest tests/test_oracle.py -q`
Expected: FAIL with `ImportError: cannot import name 'OracleDossier' from 'polymer_grammar'`.

- [ ] **Step 3: Append the IR + helpers to `grammar/src/polymer_grammar/oracle.py`**

Add these imports to the existing import block at the top of the file:

```python
from pydantic import Field

from .operations import EvaluationPlan
from .subject import Subject
```

Append after `cap_strength`:

```python
class ApplicabilityDomain(_Model):
    """The bounded domain an oracle is qualified for. `subject_kinds` lists the Subject
    discriminator kinds it covers (empty = unbounded); `predicates` are prose qualifications
    for human audit (not machine-checked in the spine)."""

    subject_kinds: tuple[str, ...] = ()
    predicates: tuple[str, ...] = ()


class OracleDossier(_Model):
    """An oracle's credibility-qualification record. `oracle_id` matches an
    `OperationNode.oracle_ref`. `relative_uncertainty` is representable now; its propagation
    into executed leaves is deferred (spec §8)."""

    oracle_id: str = Field(min_length=1)
    validation_tier: ValidationTier
    applicability_domain: ApplicabilityDomain = Field(default_factory=ApplicabilityDomain)
    anchor: str | None = None
    relative_uncertainty: float | None = Field(default=None, ge=0.0)


def in_domain(domain: ApplicabilityDomain, subject: Subject | None) -> bool:
    """Is `subject` within the oracle's qualified domain? Unbounded domain (no subject_kinds)
    -> always True. A bounded domain qualifies only its listed Subject kinds; a claim with no
    subject can't be confirmed in a bounded domain -> False (conservative)."""
    if not domain.subject_kinds:
        return True
    if subject is None:
        return False
    return subject.kind in domain.subject_kinds


def referenced_oracle_ids(plan: EvaluationPlan) -> frozenset[str]:
    """The set of oracle_refs the plan's operation nodes name (None refs excluded)."""
    return frozenset(n.oracle_ref for n in plan.graph.nodes if n.oracle_ref is not None)
```

Also add `_Model` to the existing imports — change `from .strength import AXES, StrengthVector` to keep, and add a line `from .base import _Model` if not already present (Task 1 did not need it; the new models do). The top import block should now include `from .base import _Model`.

- [ ] **Step 4: Add the exports to `grammar/src/polymer_grammar/__init__.py`**

After the `from .governance import (...)` block, add:

```python
from .oracle import (
    ApplicabilityDomain,
    OracleDossier,
    ValidationTier,
    cap_strength,
    in_domain,
    referenced_oracle_ids,
    tier_ceiling,
    weakest_tier,
)
```

And add these 8 names to the `__all__` list:

```python
    "ApplicabilityDomain",
    "OracleDossier",
    "ValidationTier",
    "cap_strength",
    "in_domain",
    "referenced_oracle_ids",
    "tier_ceiling",
    "weakest_tier",
```

- [ ] **Step 5: Run to verify it passes**

Run: `cd grammar && uv run pytest tests/test_oracle.py -q`
Expected: all 17 (10 from Task 1 + 7 new) pass.

- [ ] **Step 6: Run the full grammar suite + isolation guard**

Run: `cd grammar && uv run pytest -q && uv run ruff check src tests`
Expected: all pass (240 prior + 17 oracle = 257), ruff clean. (Confirms the new module didn't break isolation or imports.)

- [ ] **Step 7: Commit**

```bash
git add grammar/src/polymer_grammar/oracle.py grammar/src/polymer_grammar/__init__.py grammar/tests/test_oracle.py
git commit -m "feat(grammar): OracleDossier IR + applicability domain + plan-ref walk + exports"
```

---

### Task 3: Protocol — the registry + the oracle_cap policy

**Files:**
- Create: `protocol/src/polymer_protocol/oracle.py`
- Modify: `protocol/src/polymer_protocol/__init__.py`
- Modify: `protocol/tests/conftest.py`
- Test: `protocol/tests/test_oracle.py`

- [ ] **Step 1: Add an `oracle_ref` kwarg to `make_plan` in `protocol/tests/conftest.py`**

Replace the existing `make_plan` with (only the signature and the `OperationNode(...)` gain `oracle_ref`):

```python
def make_plan(
    value: float, threshold: float, comparator: Comparator = Comparator.LT,
    *, oracle_ref: str | None = None,
) -> EvaluationPlan:
    """A one-node plan: a constant `value`, tested against `threshold`. `oracle_ref` lets a
    test attach an oracle to the node (still impl=builtin::const, so the reference adapters
    execute it)."""
    node = OperationNode(
        id="n0",
        impl="builtin::const",
        params=(("value", str(value)),),
        produces=ProducedLeafSpec(leaf_kind="quantity", measurement_basis=MeasurementBasis.DERIVED),
        oracle_ref=oracle_ref,
    )
    return EvaluationPlan(
        graph=ComputeGraph(nodes=(node,), terminal="n0"),
        criterion=SatisfactionCriterion(comparator=comparator, threshold=threshold),
    )
```

- [ ] **Step 2: Write the failing tests** — `protocol/tests/test_oracle.py`

```python
import pytest
from polymer_grammar import (
    ApplicabilityDomain,
    Comparator,
    ComputeGraph,
    EvaluationPlan,
    GenomicRegion,
    MeasurementBasis,
    OperationNode,
    OracleDossier,
    ProducedLeafSpec,
    SatisfactionCriterion,
    StrengthVector,
    ValidationTier,
)
from pydantic import ValidationError

from polymer_protocol import OracleRegistry, oracle_cap
from tests.conftest import make_claim, make_plan

SV = StrengthVector(magnitude=0.9, uncertainty=0.9, evidence_against_null=0.9,
                    severity=0.9, world_contact=0.9, explanatory_virtue=0.9)


def _dossier(oid, tier, kinds=()):
    return OracleDossier(
        oracle_id=oid, validation_tier=tier,
        applicability_domain=ApplicabilityDomain(subject_kinds=kinds),
    )


def test_registry_resolve_hit_and_miss():
    reg = OracleRegistry(dossiers=(_dossier("o1", ValidationTier.GOLD),))
    assert reg.resolve("o1").validation_tier == ValidationTier.GOLD
    assert reg.resolve("nope") is None


def test_registry_rejects_duplicate_ids():
    with pytest.raises(ValidationError):
        OracleRegistry(dossiers=(_dossier("o1", ValidationTier.GOLD),
                                 _dossier("o1", ValidationTier.INDIRECT)))


def test_oracle_cap_builtin_claim_unchanged():
    c = make_claim("a", strength=SV, plan=make_plan(0.01, 0.05))  # no oracle_ref
    assert oracle_cap(c, OracleRegistry()) == SV


def test_oracle_cap_gold_unchanged():
    c = make_claim("a", strength=SV, plan=make_plan(0.01, 0.05, oracle_ref="g"))
    reg = OracleRegistry(dossiers=(_dossier("g", ValidationTier.GOLD),))
    assert oracle_cap(c, reg) == SV


def test_oracle_cap_unresolved_zeroes_empirical():
    c = make_claim("a", strength=SV, plan=make_plan(0.01, 0.05, oracle_ref="ghost"))
    capped = oracle_cap(c, OracleRegistry())  # unresolved -> UNVALIDATED
    assert capped.magnitude == 0.0 and capped.world_contact == 0.0
    assert capped.severity == 0.9  # theory axis untouched


def test_oracle_cap_out_of_domain_is_unvalidated():
    region = GenomicRegion(id="r1", display="d", assembly="GRCh38", chrom="chr1", start=1, end=9)
    c = make_claim("a", strength=SV, plan=make_plan(0.01, 0.05, oracle_ref="g"), subject=region)
    reg = OracleRegistry(dossiers=(_dossier("g", ValidationTier.GOLD, kinds=("variant_vrs",)),))
    capped = oracle_cap(c, reg)  # region not in domain -> effective UNVALIDATED
    assert capped.magnitude == 0.0


def test_oracle_cap_weakest_of_two_wins():
    nodes = (
        OperationNode(id="n0", impl="builtin::const", params=(("value", "0.01"),),
                      produces=ProducedLeafSpec(leaf_kind="quantity", measurement_basis=MeasurementBasis.DERIVED),
                      oracle_ref="gold"),
        OperationNode(id="n1", impl="builtin::const", params=(("value", "0.0"),),
                      produces=ProducedLeafSpec(leaf_kind="quantity", measurement_basis=MeasurementBasis.DERIVED),
                      oracle_ref="weak"),
    )
    plan = EvaluationPlan(
        graph=ComputeGraph(nodes=nodes, terminal="n0"),
        criterion=SatisfactionCriterion(comparator=Comparator.LT, threshold=0.05),
    )
    c = make_claim("a", strength=SV, plan=plan)
    reg = OracleRegistry(dossiers=(_dossier("gold", ValidationTier.GOLD),
                                   _dossier("weak", ValidationTier.INDIRECT)))
    capped = oracle_cap(c, reg)
    assert capped.magnitude == 0.4  # weakest (INDIRECT) ceiling wins


def test_oracle_cap_strengthless_claim_is_none():
    c = make_claim("a", plan=make_plan(0.01, 0.05, oracle_ref="g"))  # strength None
    reg = OracleRegistry(dossiers=(_dossier("g", ValidationTier.GOLD),))
    assert oracle_cap(c, reg) is None
```

- [ ] **Step 3: Run to verify it fails**

Run: `cd protocol && uv run pytest tests/test_oracle.py -q`
Expected: FAIL with `ImportError: cannot import name 'OracleRegistry' from 'polymer_protocol'`.

- [ ] **Step 4: Write `protocol/src/polymer_protocol/oracle.py`**

```python
"""oracle.py — protocol-side oracle policy (spec §6).

The registry (passed into run_cycle like adapters, NEVER persisted in the Corpus) + the
resolution POLICY: an unresolved oracle_ref OR an oracle used outside its qualified domain
counts as effective UNVALIDATED (its validation doesn't apply here). `oracle_cap` returns the
strength to write for a claim after its weakest oracle's ceiling.
"""
from __future__ import annotations

from pydantic import model_validator

from polymer_grammar import (
    Claim,
    OracleDossier,
    StrengthVector,
    Subject,
    ValidationTier,
    cap_strength,
    in_domain,
    referenced_oracle_ids,
    weakest_tier,
)

from .base import _Model


class OracleRegistry(_Model):
    """Execution-environment knowledge of oracle validation. Resolved by id; passed into
    run_cycle, not stored in the Corpus."""

    dossiers: tuple[OracleDossier, ...] = ()

    @model_validator(mode="after")
    def _unique_ids(self) -> "OracleRegistry":
        ids = [d.oracle_id for d in self.dossiers]
        if len(ids) != len(set(ids)):
            dupes = sorted({i for i in ids if ids.count(i) > 1})
            raise ValueError(f"OracleRegistry oracle_ids must be unique; duplicates: {dupes}")
        return self

    def resolve(self, oracle_id: str) -> OracleDossier | None:
        return {d.oracle_id: d for d in self.dossiers}.get(oracle_id)


def _effective_tier(
    registry: OracleRegistry, oracle_id: str, subject: Subject | None
) -> ValidationTier:
    """Resolution policy: unresolved OR out-of-domain -> UNVALIDATED."""
    dossier = registry.resolve(oracle_id)
    if dossier is None:
        return ValidationTier.UNVALIDATED
    if not in_domain(dossier.applicability_domain, subject):
        return ValidationTier.UNVALIDATED
    return dossier.validation_tier


def oracle_cap(claim: Claim, registry: OracleRegistry) -> StrengthVector | None:
    """The strength to write for `claim` after its weakest oracle's ceiling. Returns the
    (possibly unchanged) strength; None only when the claim has no strength to cap. Pure-builtin
    claims (no oracle_ref) and claims with no plan get their strength back unchanged."""
    if claim.strength is None:
        return None
    if claim.evaluation_plan is None:
        return claim.strength
    refs = referenced_oracle_ids(claim.evaluation_plan)
    if not refs:
        return claim.strength
    tiers = [_effective_tier(registry, r, claim.subject) for r in refs]
    return cap_strength(claim.strength, weakest_tier(tiers))
```

- [ ] **Step 5: Add the exports to `protocol/src/polymer_protocol/__init__.py`**

After the existing `from .base import _Model, stable_sha` line, add a grammar-convenience re-export:

```python
# grammar oracle types a run_cycle caller builds to populate the registry
from polymer_grammar import ApplicabilityDomain, OracleDossier, ValidationTier
```

Add (alongside the other stage imports):

```python
from .oracle import OracleRegistry, oracle_cap
```

Add to `__all__`:

```python
    "ApplicabilityDomain",
    "OracleDossier",
    "ValidationTier",
    "OracleRegistry",
    "oracle_cap",
```

- [ ] **Step 6: Run to verify it passes + lint**

Run: `cd protocol && uv run pytest tests/test_oracle.py -q && uv run ruff check src tests`
Expected: 8 passed, ruff clean.

- [ ] **Step 7: Commit**

```bash
git add protocol/src/polymer_protocol/oracle.py protocol/src/polymer_protocol/__init__.py protocol/tests/conftest.py protocol/tests/test_oracle.py
git commit -m "feat(protocol): OracleRegistry + oracle_cap resolution policy"
```

---

### Task 4: Protocol — cap strength at the LICENSED seam in verify_stage

**Files:**
- Modify: `protocol/src/polymer_protocol/verify.py`
- Test: `protocol/tests/test_verify.py` (append)

- [ ] **Step 1: Append the failing tests to `protocol/tests/test_verify.py`**

```python
def test_oracle_grounded_license_caps_strength(empty_ledger, ctx, adapters):
    from polymer_grammar import OracleDossier, StrengthVector, ValidationTier
    from polymer_protocol import OracleRegistry

    sv = StrengthVector(magnitude=0.9, uncertainty=0.9, evidence_against_null=0.9,
                        severity=0.9, world_contact=0.9, explanatory_virtue=0.9)
    c = make_claim("a", status=Status.PENDING, plan=make_plan(0.01, 0.05, oracle_ref="api"), strength=sv)
    corpus = commit(Corpus(claims=(c,), fdr_ledger=empty_ledger))
    corpus, records = execute_ground(corpus, adapters, ctx)
    scaffolding = CycleScaffolding(grounded_extension=("a",))
    reg = OracleRegistry(dossiers=(OracleDossier(oracle_id="api", validation_tier=ValidationTier.INDIRECT),))
    out = verify_stage(corpus, scaffolding, records, reg)
    graded = out.by_id()["a"]
    assert graded.status == Status.LICENSED
    assert graded.strength.magnitude == 0.4         # capped by INDIRECT
    assert graded.strength.severity == 0.9          # theory axis untouched


def test_oracle_cap_is_noop_without_registry(empty_ledger, ctx, adapters):
    from polymer_grammar import StrengthVector

    sv = StrengthVector(magnitude=0.9, uncertainty=0.9, evidence_against_null=0.9,
                        severity=0.9, world_contact=0.9, explanatory_virtue=0.9)
    c = make_claim("a", status=Status.PENDING, plan=make_plan(0.01, 0.05, oracle_ref="api"), strength=sv)
    corpus = commit(Corpus(claims=(c,), fdr_ledger=empty_ledger))
    corpus, records = execute_ground(corpus, adapters, ctx)
    scaffolding = CycleScaffolding(grounded_extension=("a",))
    out = verify_stage(corpus, scaffolding, records)  # no oracles arg -> back-compat
    assert out.by_id()["a"].strength == sv            # unchanged
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd protocol && uv run pytest tests/test_verify.py -q`
Expected: FAIL — `verify_stage()` takes 3 positional args but 4 were given (the `reg` arg).

- [ ] **Step 3: Modify `verify.py`**

Add the import (after the existing `from .corpus import ...` line):

```python
from .oracle import OracleRegistry, oracle_cap
```

Change the `verify_stage` signature to accept the registry and normalize it:

```python
def verify_stage(
    corpus: Corpus,
    scaffolding: CycleScaffolding,
    exec_records: tuple[ExecRecord, ...],
    oracles: OracleRegistry | None = None,
) -> Corpus:
    registry = oracles or OracleRegistry()
    in_ext = set(scaffolding.grounded_extension)
```

(Keep the rest of the body; only the signature line + the new `registry = ...` line are added at the top.)

In the LICENSED branch, add the capped strength to the `_with_status` call:

```python
        if ev.satisfaction is not None and c.id in in_ext and c.provenance is not None:
            licensing = Licensing(
                route=LicenseRoute.SEVERE_TEST,
                satisfactions=(ev.satisfaction,),
                rival_set_closure=RivalSetClosure.OPEN_ACKNOWLEDGED,
            )
            new_claims.append(
                _with_status(
                    c,
                    status=Status.LICENSED,
                    licensing=licensing,
                    pending_reason=None,
                    strength=oracle_cap(c, registry),  # caps empirical axes by weakest oracle tier; None leaves None
                )
            )
```

(The REJECTED and PENDING branches are unchanged. `oracle_cap` returns `None` only when `c.strength` is already `None`, so an existing vector is never nulled, and builtin-only claims get their strength back unchanged.)

- [ ] **Step 4: Run to verify it passes**

Run: `cd protocol && uv run pytest tests/test_verify.py -q`
Expected: all pass (7 prior + 2 new = 9).

- [ ] **Step 5: Lint + commit**

```bash
cd protocol && uv run ruff check src tests
git add protocol/src/polymer_protocol/verify.py protocol/tests/test_verify.py
git commit -m "feat(protocol): verify_stage caps LICENSED strength by oracle tier"
```

---

### Task 5: Protocol — thread `oracles` through run_cycle + docs

**Files:**
- Modify: `protocol/src/polymer_protocol/cycle.py`
- Test: `protocol/tests/test_cycle.py` (append)
- Modify: `README.md`
- Modify: `docs/superpowers/CONTINUE.md`

- [ ] **Step 1: Append the failing test to `protocol/tests/test_cycle.py`**

```python
def test_run_cycle_caps_strength_with_registry(empty_ledger, ctx, adapters):
    from polymer_grammar import OracleDossier, StrengthVector, ValidationTier
    from polymer_protocol import OracleRegistry

    sv = StrengthVector(magnitude=0.9, uncertainty=0.9, evidence_against_null=0.9,
                        severity=0.9, world_contact=0.9, explanatory_virtue=0.9)
    c = make_claim("a", status=Status.PENDING, plan=make_plan(0.01, 0.05, oracle_ref="api"), strength=sv)
    reg = OracleRegistry(dossiers=(OracleDossier(oracle_id="api", validation_tier=ValidationTier.BENCHMARKED),))
    result = run_cycle(Corpus(claims=(c,), fdr_ledger=empty_ledger), adapters, ctx, oracles=reg)
    graded = result.corpus.by_id()["a"]
    assert graded.status == Status.LICENSED
    assert graded.strength.magnitude == 0.6           # BENCHMARKED ceiling
    assert graded.strength.explanatory_virtue == 0.9  # theory axis untouched
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd protocol && uv run pytest tests/test_cycle.py -q`
Expected: FAIL — `run_cycle()` got an unexpected keyword argument `oracles`.

- [ ] **Step 3: Modify `cycle.py`**

Add the import (after `from .integrate import integrate`):

```python
from .oracle import OracleRegistry
```

Change the `run_cycle` signature to accept the registry:

```python
def run_cycle(
    corpus: Corpus,
    adapters: tuple[Adapter, ...],
    ctx: MaterializationContext,
    oracles: OracleRegistry | None = None,
) -> CycleResult:
```

Pass it to `verify_stage` (the only call that needs it) — change the `verify_stage` call line:

```python
    corpus = verify_stage(corpus, scaffolding, records, oracles)
```

(No other stage changes; `oracles=None` defaults to the empty registry inside `verify_stage`.)

- [ ] **Step 4: Run to verify it passes + full protocol suite**

Run: `cd protocol && uv run pytest -q && uv run ruff check src tests`
Expected: all pass (51 prior + 8 oracle + 2 verify + 1 oracle-cycle = 62 total — note the actual count), ruff clean.

- [ ] **Step 5: Add an oracle note to `README.md`**

In the `## Protocol runtime (`polymer_protocol`)` section, after the EXECUTE/air-gap sentence, add one line:

```markdown
An optional oracle registry (`run_cycle(..., oracles=...)`) caps a licensed claim's **empirical** strength axes by the validation tier of the weakest oracle its plan references — unresolved or out-of-domain oracles count as `UNVALIDATED` (zero empirical strength). Builtin-only claims are unaffected.
```

Update the protocol status-table row test count from `49 tests` to the count printed in Step 4.

- [ ] **Step 6: Update `docs/superpowers/CONTINUE.md`**

In the "Current state" paragraph, after the sub-project #1 sentence, record sub-project #2 done:

```markdown
**Protocol sub-project #2 (Oracle dossier / D2) is DONE** — grammar `oracle.py` (OracleDossier IR + ValidationTier ladder + tier→empirical-axis strength cap + applicability domain) + protocol `oracle.py` (OracleRegistry + oracle_cap) wired into verify_stage's LICENSED seam and run_cycle (`oracles=`). The oracle tier caps a licensed claim's empirical strength via meet; unresolved/out-of-domain → effective UNVALIDATED; no new status/grammar field; builtin-only claims unaffected. Spec `docs/superpowers/specs/2026-06-02-oracle-dossier-design.md`, plan `docs/superpowers/plans/2026-06-02-oracle-dossier.md`. Merge commit: `<fill at merge>`.
```

Change the "▶ NEXT" heading from sub-project #2 to **sub-project #3 — SELECT (the pursuit/value engine)**, and in the 5-sub-project list mark #2 ✅ DONE and point the arrow at #3.

- [ ] **Step 7: Final lint + commit**

```bash
cd protocol && uv run ruff check src tests
git add protocol/src/polymer_protocol/cycle.py protocol/tests/test_cycle.py README.md docs/superpowers/CONTINUE.md
git commit -m "feat(protocol): thread oracles through run_cycle + docs (sub-project #2 complete)"
```

---

## Progress Log

_(Update after every task: check the boxes, record the commit SHA.)_

- [ ] Task 1 — grammar tiers + strength cap — commit: `____`
- [ ] Task 2 — grammar dossier + domain + refs + exports — commit: `____`
- [ ] Task 3 — protocol registry + oracle_cap — commit: `____`
- [ ] Task 4 — verify_stage cap — commit: `____`
- [ ] Task 5 — run_cycle thread + docs — commit: `____`

**Decisions / deviations:** _(record here as they happen)_

---

## Self-Review (plan author)

**Spec coverage** — every spec section maps to a task: §4 dossier IR → Task 2; §5 helpers (`tier_ceiling`/`cap_strength` → Task 1; `in_domain`/`referenced_oracle_ids`/`weakest_tier` → Tasks 1+2); §6 registry + `oracle_cap` + verify_stage + run_cycle → Tasks 3/4/5; §7 within-cycle interaction is inherent in the Task 4 placement (cap at the LICENSED seam, flows into integrate) — no separate task needed; §8 scope fence respected (no uncertainty propagation, no SPOT/daemon, no per-axis ceilings, cap only at LICENSED); §9 testing woven through every task.

**Type/name consistency** — `ValidationTier`, `OracleDossier`, `ApplicabilityDomain`, `tier_ceiling`, `cap_strength`, `in_domain`, `referenced_oracle_ids`, `weakest_tier` (grammar) and `OracleRegistry`, `oracle_cap` (protocol) used identically across tasks. `oracle_cap(claim, registry)` signature stable. `_EMPIRICAL_AXES` = (magnitude, uncertainty, evidence_against_null, world_contact) consistent everywhere. The `oracle_cap`-returns-None-iff-strength-None invariant (so `_with_status(strength=None)` never nulls an existing vector) is stated where it matters (Tasks 3 & 4).

**Back-compat** — every existing test uses builtin-only plans (`oracle_ref=None`) and no registry, so `oracle_cap` returns strength unchanged and `verify_stage`/`run_cycle` defaults are no-ops. Confirmed in Tasks 4/5 (the no-registry test) and by the full-suite runs in Tasks 2 & 5.

**Deliberate narrowing** — the cap is applied only on the LICENSED branch (spec §8 defers capping non-LICENSED claims); the within-cycle "membership decided pre-cap, claim may re-surface on frontier" consequence (spec §7) is intended and documented, not a task.
