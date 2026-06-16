# Protocol Runtime — Sub-project #1: Corpus + the Assessment Spine — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `polymer_protocol`, a new sibling package that runs a `Corpus` of grammar `Claim`s through seven pure assessment stages (`represent → canonicalize → safety_gate → commit → execute_ground → verify_stage → integrate`) wired into one deterministic `run_cycle`, writing only existing grammar IR and reusing the Phase-8 air-gapped `verify()` for execution.

**Architecture:** A one-way-dependent runtime over `polymer_grammar`. The persistent state is a frozen `Corpus` (claims, defeat_edges, equivalences, fdr_ledger); each stage is a total `Corpus → …` function; ephemeral per-cycle products (the argumentation scaffolding, execution records, the unresolved-attack frontier, the human-gated lane, a stage audit) are returned in a `CycleResult`, never stored. GENERATE and SELECT are stubbed open ports: claims enter exogenously (already carrying `evaluation_plan`s), and the dumb driver executes every committed, non-gated PENDING claim.

**Tech Stack:** Python ≥3.12, Pydantic v2 (frozen models, `extra="forbid"`, tuples-only), `uv` for env/test, `pytest`, `ruff`. Path-depends on the local `grammar/` package.

**Spec:** `docs/superpowers/specs/2026-06-02-protocol-spine-design.md` (approved, committed `f65a6b1`).

**Working agreements (don't relearn):**
- All models subclass a frozen `_Model` (`extra="forbid"`, tuples not lists/dicts). No `dict`/`list` model fields.
- TDD: failing test first. Run `cd protocol && uv run pytest -q` and `uv run ruff check src tests` after each task.
- Commit after every task. Commit messages end with the trailer:
  `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`
- The runtime imports `polymer_grammar` one-way; the grammar must NEVER import `polymer_protocol` (isolation-tested).
- Status transitions must round-trip through `Claim` validation (Pydantic `model_copy(update=…)` does NOT re-validate — use the `_with_status` helper introduced in Task 8).

**Grammar API this plan calls (verified signatures):**
- `Claim(id, title, pattern: PatternRef, leaves: tuple[Leaf,...] (min 1), status: Status, pending_reason, strength, conclusion, licensing, roles, subject, provenance, governance, evaluation_plan)`. Validators: `status==PENDING ⇔ pending_reason set`; `licensing` only when `status==LICENSED`.
- `Status.{CONJECTURED,EXPLORATORY,PENDING,LICENSED,REJECTED}`; `PendingReason.{UNTESTED,CONTESTED,…}`.
- `PatternRef(id, version)`; leaves: `CategoricalLeaf(ontology_term)`, `ExistenceLeaf(state)`, `QuantityLeaf(value, measurement_basis, …)`, `PropositionLeaf(data, warrant)`.
- `StrengthVector(magnitude, uncertainty, evidence_against_null, severity, world_contact, explanatory_virtue)` all in [0,1]; `.dominates(other)`.
- `defeat.grounded_extension(claim_ids: Iterable[str], edges: Iterable[DefeatEdge], strength: Mapping[str, StrengthVector|None]) -> frozenset[str]`.
- `defeat.effective_defeats(edges, strength) -> frozenset[tuple[str,str]]`; `defeat.derived_rebut_edges(claims) -> tuple[DefeatEdge,...]`; `DefeatEdge(source, target, kind: DefeatEdgeKind)` (no self-loop).
- `governance.requires_safety_review(governance: Governance) -> bool`; `Governance(hazard_class, access_scope, note)`.
- `provenance.Provenance(generated_by: GenerationMode, agent_id, method, version, search_cardinality: int≥1, preregistration_hash)`; `GenerationMode.{HUMAN_AUTHORED,AGENT_GENERATED,LITERATURE_EXTRACTED,MIGRATED,IMPORTED}`.
- `operations.EvaluationPlan(graph: ComputeGraph, criterion: SatisfactionCriterion)`; `ComputeGraph(nodes, terminal)` with `.content_hash` property; `OperationNode(id, impl, inputs, params: tuple[tuple[str,str],...], produces: ProducedLeafSpec, oracle_ref)`; `ProducedLeafSpec(leaf_kind, measurement_basis, unit, dimension)`; `SatisfactionCriterion(comparator: Comparator, threshold, reference_leaf_index, tolerance)`; `Comparator.{LT,LE,EQ,NE,GE,GT,WITHIN_TOL}`.
- `evaluate.verify(plan, ctx: MaterializationContext, adapters: tuple[Adapter,...], *, claim_leaves=()) -> VerifiedEvaluation`. Raises `SelfLicensingError` if <2 distinct adapter identities. `VerifiedEvaluation(results: tuple[EvaluationResult,...], agreement: bool, satisfaction: Satisfaction|None, disagreement: str|None)`. `EvaluationResult(verdict: SatisfactionVerdict, terminal: ExecValue, nodes, adapter_identity, status)`; `ExecValue(value: float|str|None, dimension)`. Reference adapters: `IdentityAdapter()` (identity="identity"), `ReferenceAdapter(identity="reference", perturb=0.0)`.
- `licensing.Licensing(route: LicenseRoute, satisfactions: tuple[Satisfaction,...] (≥1, all SATISFIED), rival_set_closure: RivalSetClosure, rivals_considered, note)`; `LicenseRoute.{SEVERE_TEST,REPLICATION}`; `RivalSetClosure.{ENUMERATED,ONTOLOGY_BOUNDED,OPEN_ACKNOWLEDGED}`; `MaterializationContext(id, api_version, data_version, note)`; `Satisfaction(verdict, materialization)`; `SatisfactionVerdict.{SATISFIED,REFUTED,UNDETERMINED}`.
- `revision.restore_consistency(claims, edges, *, prior_in=None) -> RevisionResult`; `RevisionResult(claims, edges, retraction, in_set, flipped_in, flipped_out)`.
- `fdr.process_test(ledger: FDRLedger, claim_id: str, p_value: float in [0,1]) -> FDRLedger`; `FDRLedger(target_fdr: float in (0,1], procedure="lond", tests)` with `.n_tests`, `.n_discoveries`, `.discoveries`.
- `equivalence.EquivalenceClaim(id, left, right, severity in [0,1], status: Status, pending_reason, note)` (distinct endpoints); `equivalence.equivalence_class(handle, equivalences, *, grounded_in=None) -> frozenset[str]`.

---

## File Structure

```
polymer-claims/
  grammar/                         # existing — polymer_grammar (UNCHANGED)
  protocol/                        # NEW package
    pyproject.toml                 # polymer-protocol; path-dep on ../grammar
    src/polymer_protocol/
      __init__.py                  # re-exports the public surface
      base.py                      # re-export grammar _Model + stable_sha helper
      corpus.py                    # Corpus + CycleScaffolding + ExecRecord + StageAudit + CycleResult
      represent.py                 # represent()
      canonicalize.py              # canonicalize()
      safety.py                    # safety_gate()
      commit.py                    # commit()
      execute.py                   # execute_ground()
      verify.py                    # verify_stage()
      integrate.py                 # integrate()
      cycle.py                     # run_cycle()
    tests/
      conftest.py                  # shared claim/plan/corpus fixtures
      test_isolation.py            # grammar must NOT import polymer_protocol
      test_corpus.py
      test_represent.py
      test_canonicalize.py
      test_safety.py
      test_commit.py
      test_execute.py
      test_verify.py
      test_integrate.py
      test_cycle.py
```

Each file has one responsibility (one stage per file). `corpus.py` holds the state + ephemeral types because they change together and every stage imports them.

---

### Task 1: Package scaffold + isolation guard

**Files:**
- Create: `protocol/pyproject.toml`
- Create: `protocol/src/polymer_protocol/__init__.py`
- Create: `protocol/src/polymer_protocol/base.py`
- Create: `protocol/tests/test_isolation.py`

- [ ] **Step 1: Write `protocol/pyproject.toml`**

```toml
[project]
name = "polymer-protocol"
version = "0.1.0"
description = "Polymer Claims protocol runtime — the assessment spine over polymer_grammar."
requires-python = ">=3.12"
dependencies = ["polymer-grammar", "pydantic>=2.6"]

[tool.uv.sources]
polymer-grammar = { path = "../grammar", editable = true }

[dependency-groups]
dev = ["pytest>=8", "ruff>=0.6"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/polymer_protocol"]

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
```

- [ ] **Step 2: Write `protocol/src/polymer_protocol/base.py`**

```python
"""Project base for the protocol runtime.

Re-uses the grammar's frozen-model discipline (one-way dependency: protocol → grammar)
so protocol models share the exact ConfigDict (extra="forbid", frozen, tuples-only).
Also ships the one canonical content-hash helper used by canonicalize/commit.
"""
from __future__ import annotations

import hashlib
import json

from polymer_grammar.base import _Model  # re-export — single source of frozen discipline

__all__ = ["_Model", "stable_sha"]


def stable_sha(obj: object) -> str:
    """Deterministic SHA-256 over a JSON-canonicalized object (sorted keys)."""
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
```

- [ ] **Step 3: Write a minimal `protocol/src/polymer_protocol/__init__.py`**

```python
"""polymer_protocol — the protocol runtime (assessment spine) over polymer_grammar."""
from __future__ import annotations

__version__ = "0.1.0"

from .base import _Model, stable_sha

__all__ = ["_Model", "stable_sha", "__version__"]
```

- [ ] **Step 4: Write `protocol/tests/test_isolation.py`** (mirror the grammar's guard, reversed direction)

```python
"""Guard the one-way boundary: polymer_grammar must NOT depend on polymer_protocol."""
from __future__ import annotations

import pathlib
import re

# protocol/tests/ -> protocol/ -> polymer-claims/ -> grammar/src/polymer_grammar
GRAMMAR_SRC = (
    pathlib.Path(__file__).resolve().parent.parent.parent
    / "grammar"
    / "src"
    / "polymer_grammar"
)

_IMPORT_RE = re.compile(
    r"^\s*(import\s+polymer_protocol|from\s+polymer_protocol)",
    re.MULTILINE,
)


def test_grammar_does_not_import_protocol():
    offenders = []
    for py in GRAMMAR_SRC.rglob("*.py"):
        if _IMPORT_RE.search(py.read_text(encoding="utf-8")):
            offenders.append(py.name)
    assert offenders == [], f"grammar must not import polymer_protocol; offenders: {offenders}"


def test_protocol_can_import_grammar():
    import polymer_grammar  # one-way dependency is allowed

    assert polymer_grammar.__version__
```

- [ ] **Step 5: Sync the env and run the isolation test**

Run: `cd protocol && uv sync && uv run pytest tests/test_isolation.py -v`
Expected: both tests PASS (env resolves the `../grammar` path dependency; grammar has no protocol imports).

- [ ] **Step 6: Lint**

Run: `cd protocol && uv run ruff check src tests`
Expected: no errors.

- [ ] **Step 7: Commit**

```bash
git add protocol/pyproject.toml protocol/src/polymer_protocol protocol/tests/test_isolation.py protocol/uv.lock
git commit -m "feat(protocol): scaffold polymer_protocol package + one-way isolation guard"
```

---

### Task 2: The `Corpus` and ephemeral cycle types

**Files:**
- Create: `protocol/src/polymer_protocol/corpus.py`
- Create: `protocol/tests/conftest.py`
- Create: `protocol/tests/test_corpus.py`

`Corpus` holds the four grammar collections. Referential-integrity rule (corpus-level, which the grammar can't enforce alone): claim ids are unique; equivalence `left`/`right` resolve to claim ids; defeat-edge `target` resolves to a claim id; defeat-edge `source` resolves to a claim id OR is a synthetic node id (contains `":"`, e.g. `refutation:<materialization-id>` produced by the grammar's `undermine_edges_from_failed_satisfactions`).

- [ ] **Step 1: Write `protocol/tests/conftest.py`** (shared fixtures used across all stage tests)

```python
"""Shared fixtures: minimal claims, evaluation plans, adapters, and corpora."""
from __future__ import annotations

import pytest
from polymer_grammar import (
    CategoricalLeaf,
    Claim,
    Comparator,
    ComputeGraph,
    EvaluationPlan,
    FDRLedger,
    IdentityAdapter,
    MaterializationContext,
    MeasurementBasis,
    OperationNode,
    PatternRef,
    PendingReason,
    ProducedLeafSpec,
    ReferenceAdapter,
    SatisfactionCriterion,
    Status,
    StrengthVector,
)

from polymer_protocol.corpus import Corpus

_PATTERN = PatternRef(id="adjusted_effect", version="v1")


def make_claim(
    cid: str,
    status: Status = Status.CONJECTURED,
    *,
    plan: EvaluationPlan | None = None,
    pending_reason: PendingReason | None = None,
    strength: StrengthVector | None = None,
    **extra,
) -> Claim:
    if status == Status.PENDING and pending_reason is None:
        pending_reason = PendingReason.UNTESTED
    return Claim(
        id=cid,
        title=f"claim {cid}",
        pattern=_PATTERN,
        leaves=(CategoricalLeaf(ontology_term=f"term-{cid}"),),
        status=status,
        pending_reason=pending_reason,
        strength=strength,
        evaluation_plan=plan,
        **extra,
    )


def make_plan(value: float, threshold: float, comparator: Comparator = Comparator.LT) -> EvaluationPlan:
    """A one-node plan: a constant `value`, tested against `threshold`."""
    node = OperationNode(
        id="n0",
        impl="builtin::const",
        params=(("value", str(value)),),
        produces=ProducedLeafSpec(leaf_kind="quantity", measurement_basis=MeasurementBasis.DERIVED),
    )
    return EvaluationPlan(
        graph=ComputeGraph(nodes=(node,), terminal="n0"),
        criterion=SatisfactionCriterion(comparator=comparator, threshold=threshold),
    )


@pytest.fixture
def ctx() -> MaterializationContext:
    return MaterializationContext(id="M1", api_version="v1", data_version="d1")


@pytest.fixture
def adapters() -> tuple:
    """Two distinct-identity reference adapters — satisfies verify()'s air-gap."""
    return (IdentityAdapter(), ReferenceAdapter(identity="reference"))


@pytest.fixture
def empty_ledger() -> FDRLedger:
    return FDRLedger(target_fdr=0.05)


@pytest.fixture
def empty_corpus(empty_ledger) -> Corpus:
    return Corpus(fdr_ledger=empty_ledger)
```

- [ ] **Step 2: Write `protocol/tests/test_corpus.py`**

```python
import pytest
from polymer_grammar import (
    DefeatEdge,
    DefeatEdgeKind,
    EquivalenceClaim,
    FDRLedger,
    Status,
)
from pydantic import ValidationError

from polymer_protocol.corpus import Corpus
from tests.conftest import make_claim


def test_corpus_by_id_indexes_claims(empty_ledger):
    a, b = make_claim("a"), make_claim("b")
    corpus = Corpus(claims=(a, b), fdr_ledger=empty_ledger)
    assert corpus.by_id() == {"a": a, "b": b}


def test_corpus_rejects_duplicate_claim_ids(empty_ledger):
    with pytest.raises(ValidationError, match="unique"):
        Corpus(claims=(make_claim("a"), make_claim("a")), fdr_ledger=empty_ledger)


def test_corpus_rejects_dangling_defeat_target(empty_ledger):
    edge = DefeatEdge(source="a", target="ghost", kind=DefeatEdgeKind.REBUT)
    with pytest.raises(ValidationError, match="ghost"):
        Corpus(claims=(make_claim("a"),), defeat_edges=(edge,), fdr_ledger=empty_ledger)


def test_corpus_allows_synthetic_defeat_source(empty_ledger):
    # refutation:<id> synthetic source is produced by the grammar; must be permitted.
    edge = DefeatEdge(source="refutation:M1", target="a", kind=DefeatEdgeKind.UNDERMINE)
    corpus = Corpus(claims=(make_claim("a"),), defeat_edges=(edge,), fdr_ledger=empty_ledger)
    assert corpus.defeat_edges == (edge,)


def test_corpus_rejects_dangling_equivalence_endpoint(empty_ledger):
    eq = EquivalenceClaim(id="e1", left="a", right="ghost", severity=1.0, status=Status.LICENSED)
    with pytest.raises(ValidationError, match="ghost"):
        Corpus(claims=(make_claim("a"),), equivalences=(eq,), fdr_ledger=empty_ledger)


def test_corpus_is_frozen(empty_ledger):
    corpus = Corpus(claims=(make_claim("a"),), fdr_ledger=empty_ledger)
    with pytest.raises(ValidationError):
        corpus.claims = ()
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `cd protocol && uv run pytest tests/test_corpus.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'polymer_protocol.corpus'`.

- [ ] **Step 4: Write `protocol/src/polymer_protocol/corpus.py`**

```python
"""The Corpus (persistent protocol state) + the ephemeral per-cycle products.

Corpus is a pure bundle of existing grammar IR — no new grammar fields. The four
collections are the whole persistent state; everything a cycle computes that is not
itself grammar IR (scaffolding, execution records, frontier, audit) is ephemeral and
returned in CycleResult, never stored — keeping each cycle reversible.
"""
from __future__ import annotations

from pydantic import Field, model_validator

from polymer_grammar import (
    Claim,
    DefeatEdge,
    EquivalenceClaim,
    FDRLedger,
    VerifiedEvaluation,
)

from .base import _Model


class Corpus(_Model):
    claims: tuple[Claim, ...] = ()
    defeat_edges: tuple[DefeatEdge, ...] = ()
    equivalences: tuple[EquivalenceClaim, ...] = ()
    fdr_ledger: FDRLedger

    def by_id(self) -> dict[str, Claim]:
        """Derived id → claim index (not a stored field)."""
        return {c.id: c for c in self.claims}

    @model_validator(mode="after")
    def _unique_claim_ids(self) -> "Corpus":
        ids = [c.id for c in self.claims]
        if len(ids) != len(set(ids)):
            dupes = sorted({i for i in ids if ids.count(i) > 1})
            raise ValueError(f"Corpus claim ids must be unique; duplicates: {dupes}")
        return self

    @model_validator(mode="after")
    def _referential_integrity(self) -> "Corpus":
        ids = {c.id for c in self.claims}
        for e in self.defeat_edges:
            if e.target not in ids:
                raise ValueError(f"defeat edge target {e.target!r} is not a claim id")
            # source may be a claim OR a synthetic node id (convention: contains ':')
            if e.source not in ids and ":" not in e.source:
                raise ValueError(f"defeat edge source {e.source!r} is not a claim id")
        for eq in self.equivalences:
            for endpoint in (eq.left, eq.right):
                if endpoint not in ids:
                    raise ValueError(
                        f"equivalence endpoint {endpoint!r} is not a claim id"
                    )
        return self


class CycleScaffolding(_Model):
    """Ephemeral REPRESENT output — argumentation structure, written nowhere."""

    grounded_extension: tuple[str, ...] = ()  # claim ids IN the grounded extension
    frontier: tuple[str, ...] = ()            # unresolved-attack frontier (claim ids)


class ExecRecord(_Model):
    """Bridge from EXECUTE to VERIFY/INTEGRATE: a claim id + its Phase-8 result."""

    claim_id: str
    evaluation: VerifiedEvaluation


class StageAudit(_Model):
    """Human-readable per-stage trace line."""

    stage: str
    note: str
    count: int = Field(default=0, ge=0)


class CycleResult(_Model):
    corpus: Corpus
    frontier: tuple[str, ...] = ()    # next cycle's GENERATE/SELECT target (keystone closure)
    gated_lane: tuple[str, ...] = ()  # claim ids barred from autonomous execution (SAFETY)
    audit: tuple[StageAudit, ...] = ()
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `cd protocol && uv run pytest tests/test_corpus.py -v`
Expected: all 6 PASS.

- [ ] **Step 6: Lint + commit**

```bash
cd protocol && uv run ruff check src tests
git add protocol/src/polymer_protocol/corpus.py protocol/tests/conftest.py protocol/tests/test_corpus.py
git commit -m "feat(protocol): Corpus state + ephemeral cycle types (scaffolding, exec record, audit, result)"
```

---

### Task 3: `represent()` — argumentation scaffolding + frontier

**Files:**
- Create: `protocol/src/polymer_protocol/represent.py`
- Create: `protocol/tests/test_represent.py`

`represent` writes nothing. It computes the VAF grounded extension and the unresolved-attack frontier (claim ids that are the target of an *effective* defeat and are NOT in the grounded extension). Both are returned as deterministically-sorted tuples. (The two-axis calibrated posterior and "newly-incident attack" cross-cycle delta are deferred to SELECT/#3 and the daemons/#5 — see spec §6.1.)

- [ ] **Step 1: Write `protocol/tests/test_represent.py`**

```python
from polymer_grammar import DefeatEdge, DefeatEdgeKind, Status, StrengthVector

from polymer_protocol.corpus import Corpus
from polymer_protocol.represent import represent
from tests.conftest import make_claim


def test_no_attacks_everyone_in_extension_empty_frontier(empty_ledger):
    corpus = Corpus(claims=(make_claim("a"), make_claim("b")), fdr_ledger=empty_ledger)
    scaffolding = represent(corpus)
    assert scaffolding.grounded_extension == ("a", "b")
    assert scaffolding.frontier == ()


def test_effective_attack_puts_target_on_frontier(empty_ledger):
    # b attacks a; neither has strength, so the attack is effective -> a is OUT, on frontier.
    edge = DefeatEdge(source="b", target="a", kind=DefeatEdgeKind.REBUT)
    corpus = Corpus(
        claims=(make_claim("a"), make_claim("b")),
        defeat_edges=(edge,),
        fdr_ledger=empty_ledger,
    )
    scaffolding = represent(corpus)
    assert "b" in scaffolding.grounded_extension
    assert "a" not in scaffolding.grounded_extension
    assert scaffolding.frontier == ("a",)


def test_target_dominates_source_attack_filtered_out(empty_ledger):
    strong = StrengthVector(magnitude=0.9, uncertainty=0.9, evidence_against_null=0.9,
                            severity=0.9, world_contact=0.9, explanatory_virtue=0.9)
    weak = StrengthVector(magnitude=0.1, uncertainty=0.1, evidence_against_null=0.1,
                          severity=0.1, world_contact=0.1, explanatory_virtue=0.1)
    edge = DefeatEdge(source="b", target="a", kind=DefeatEdgeKind.REBUT)
    corpus = Corpus(
        claims=(make_claim("a", strength=strong), make_claim("b", strength=weak)),
        defeat_edges=(edge,),
        fdr_ledger=empty_ledger,
    )
    scaffolding = represent(corpus)
    # a strength-dominates b, so b's attack is filtered: a stays IN, frontier empty.
    assert scaffolding.grounded_extension == ("a", "b")
    assert scaffolding.frontier == ()
```

- [ ] **Step 2: Run to verify failure**

Run: `cd protocol && uv run pytest tests/test_represent.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'polymer_protocol.represent'`.

- [ ] **Step 3: Write `protocol/src/polymer_protocol/represent.py`**

```python
"""REPRESENT (deterministic part): build the VAF argumentation scaffolding.

Writes nothing. Computes the grounded extension over effective defeats and the
unresolved-attack frontier (effective-defeat targets that are NOT grounded). The
calibrated two-axis posterior and the cross-cycle 'newly-incident attack' set are
deferred (spec §6.1) — SELECT (#3) and the daemons (#5).
"""
from __future__ import annotations

from polymer_grammar import effective_defeats, grounded_extension

from .corpus import Corpus, CycleScaffolding


def represent(corpus: Corpus) -> CycleScaffolding:
    claim_ids = [c.id for c in corpus.claims]
    id_set = set(claim_ids)
    strength = {c.id: c.strength for c in corpus.claims}
    grounded = grounded_extension(claim_ids, corpus.defeat_edges, strength)
    defeats = effective_defeats(corpus.defeat_edges, strength)
    frontier = {
        tgt for _src, tgt in defeats if tgt in id_set and tgt not in grounded
    }
    return CycleScaffolding(
        grounded_extension=tuple(sorted(grounded & id_set)),
        frontier=tuple(sorted(frontier)),
    )
```

- [ ] **Step 4: Run to verify pass**

Run: `cd protocol && uv run pytest tests/test_represent.py -v`
Expected: all 3 PASS.

- [ ] **Step 5: Lint + commit**

```bash
cd protocol && uv run ruff check src tests
git add protocol/src/polymer_protocol/represent.py protocol/tests/test_represent.py
git commit -m "feat(protocol): represent() — grounded extension + unresolved-attack frontier"
```

---

### Task 4: `canonicalize()` — structural-key equivalence collapse

**Files:**
- Create: `protocol/src/polymer_protocol/canonicalize.py`
- Create: `protocol/tests/test_canonicalize.py`

Compute a structural canonical key per claim from existing content hashes (`pattern.id` + `pattern.version` + `subject` dump + `conclusion.content_hash` + `evaluation_plan.graph.content_hash`). Claims sharing a key are linked into one equivalence class by recording `EquivalenceClaim` edges from the lowest-id representative to each duplicate (added to `equivalences`). **Spine narrowing (spec §6.2):** the spine records the equivalence relation — it does NOT physically delete claims or merge provenance (that is the grammar's identity philosophy: "same claim" = a licensed equivalence edge, never deletion). Physical node-collapse + provenance-merge ride the semantic/EIG dedup in SELECT (#3). Idempotent: an already-recorded `{left,right}` pair is not duplicated.

- [ ] **Step 1: Write `protocol/tests/test_canonicalize.py`**

```python
from polymer_grammar import Status, are_equivalent

from polymer_protocol.canonicalize import canonicalize
from polymer_protocol.corpus import Corpus
from tests.conftest import make_claim, make_plan


def test_structurally_identical_claims_become_one_equivalence_class(empty_ledger):
    plan = make_plan(0.01, 0.05)
    # a and b are structurally identical except for id (same pattern/leaf-less-key/plan).
    a = make_claim("a", status=Status.PENDING, plan=plan)
    b = make_claim("b", status=Status.PENDING, plan=plan)
    corpus = Corpus(claims=(a, b), fdr_ledger=empty_ledger)
    out = canonicalize(corpus)
    assert len(out.equivalences) == 1
    eq = out.equivalences[0]
    assert {eq.left, eq.right} == {"a", "b"}
    assert eq.status == Status.LICENSED
    # they are now in one equivalence class (back-compat LICENSED gating)
    assert are_equivalent("a", "b", out.equivalences)


def test_distinct_claims_are_not_collapsed(empty_ledger):
    a = make_claim("a", status=Status.PENDING, plan=make_plan(0.01, 0.05))
    b = make_claim("b", status=Status.PENDING, plan=make_plan(0.99, 0.05))
    corpus = Corpus(claims=(a, b), fdr_ledger=empty_ledger)
    out = canonicalize(corpus)
    assert out.equivalences == ()


def test_canonicalize_is_idempotent(empty_ledger):
    plan = make_plan(0.01, 0.05)
    corpus = Corpus(
        claims=(make_claim("a", status=Status.PENDING, plan=plan),
                make_claim("b", status=Status.PENDING, plan=plan)),
        fdr_ledger=empty_ledger,
    )
    once = canonicalize(corpus)
    twice = canonicalize(once)
    assert once.equivalences == twice.equivalences
```

- [ ] **Step 2: Run to verify failure**

Run: `cd protocol && uv run pytest tests/test_canonicalize.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Write `protocol/src/polymer_protocol/canonicalize.py`**

```python
"""CANONICALIZE (structural part): collapse structurally-identical claims into one
equivalence class by recording EquivalenceClaim edges.

Records the equivalence relation only — no physical node deletion, no provenance merge
(the grammar's identity philosophy: identity = a licensed equivalence edge, never a
hash/deletion). Semantic/EIG dedup is deferred to SELECT (#3) — spec §6.2. Idempotent.
"""
from __future__ import annotations

from collections import defaultdict

from polymer_grammar import Claim, EquivalenceClaim, Status

from .base import stable_sha
from .corpus import Corpus


def _structural_key(c: Claim) -> str:
    return stable_sha(
        [
            c.pattern.id,
            c.pattern.version,
            c.subject.model_dump(mode="json") if c.subject is not None else None,
            c.conclusion.content_hash if c.conclusion is not None else None,
            c.evaluation_plan.graph.content_hash if c.evaluation_plan is not None else None,
        ]
    )


def canonicalize(corpus: Corpus) -> Corpus:
    buckets: dict[str, list[str]] = defaultdict(list)
    for c in corpus.claims:
        buckets[_structural_key(c)].append(c.id)

    existing_pairs = {frozenset((eq.left, eq.right)) for eq in corpus.equivalences}
    new_edges: list[EquivalenceClaim] = []
    for key, ids in buckets.items():
        if len(ids) < 2:
            continue
        ids = sorted(ids)
        rep = ids[0]
        for other in ids[1:]:
            if frozenset((rep, other)) in existing_pairs:
                continue
            new_edges.append(
                EquivalenceClaim(
                    id=f"struct-eq:{rep}:{other}",
                    left=rep,
                    right=other,
                    severity=1.0,  # exact structural identity
                    status=Status.LICENSED,
                    note="structural-key collapse",
                )
            )
    if not new_edges:
        return corpus
    return corpus.model_copy(
        update={"equivalences": corpus.equivalences + tuple(new_edges)}
    )
```

- [ ] **Step 4: Run to verify pass**

Run: `cd protocol && uv run pytest tests/test_canonicalize.py -v`
Expected: all 3 PASS.

- [ ] **Step 5: Lint + commit**

```bash
cd protocol && uv run ruff check src tests
git add protocol/src/polymer_protocol/canonicalize.py protocol/tests/test_canonicalize.py
git commit -m "feat(protocol): canonicalize() — structural-key equivalence collapse (edge-recording, idempotent)"
```

---

### Task 5: `safety_gate()` — hazard partition

**Files:**
- Create: `protocol/src/polymer_protocol/safety.py`
- Create: `protocol/tests/test_safety.py`

Partition claims via `governance.requires_safety_review`. Hazard-flagged claims (high / dual_use) are barred from autonomous execution regardless of value and returned as the `gated_lane` (sorted). The corpus is returned unchanged (the gate writes nothing to claims — it uses the existing `governance` posture).

- [ ] **Step 1: Write `protocol/tests/test_safety.py`**

```python
from polymer_grammar import Governance, HazardClass

from polymer_protocol.corpus import Corpus
from polymer_protocol.safety import safety_gate
from tests.conftest import make_claim


def test_clean_claims_are_not_gated(empty_ledger):
    corpus = Corpus(claims=(make_claim("a"), make_claim("b")), fdr_ledger=empty_ledger)
    out, gated = safety_gate(corpus)
    assert gated == ()
    assert out is corpus  # unchanged


def test_high_hazard_claim_is_gated(empty_ledger):
    hot = make_claim("h", governance=Governance(hazard_class=HazardClass.HIGH))
    dual = make_claim("d", governance=Governance(hazard_class=HazardClass.DUAL_USE))
    safe = make_claim("s", governance=Governance(hazard_class=HazardClass.LOW))
    corpus = Corpus(claims=(hot, dual, safe), fdr_ledger=empty_ledger)
    _out, gated = safety_gate(corpus)
    assert gated == ("d", "h")  # sorted; LOW is not gated
```

- [ ] **Step 2: Run to verify failure**

Run: `cd protocol && uv run pytest tests/test_safety.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Write `protocol/src/polymer_protocol/safety.py`**

```python
"""SAFETY-GATE: bar hazard-flagged claims from autonomous execution.

Uses the grammar's governance predicate. Hazard-flagged claims (high/dual_use) go to the
human-review lane regardless of value; the corpus is returned unchanged (the gate reads
the existing governance posture, writes nothing) — spec §6.3.
"""
from __future__ import annotations

from polymer_grammar import requires_safety_review

from .corpus import Corpus


def safety_gate(corpus: Corpus) -> tuple[Corpus, tuple[str, ...]]:
    gated = tuple(
        sorted(
            c.id
            for c in corpus.claims
            if c.governance is not None and requires_safety_review(c.governance)
        )
    )
    return corpus, gated
```

- [ ] **Step 4: Run to verify pass**

Run: `cd protocol && uv run pytest tests/test_safety.py -v`
Expected: both PASS.

- [ ] **Step 5: Lint + commit**

```bash
cd protocol && uv run ruff check src tests
git add protocol/src/polymer_protocol/safety.py protocol/tests/test_safety.py
git commit -m "feat(protocol): safety_gate() — hazard partition into the human-review lane"
```

---

### Task 6: `commit()` — hash-lock the pre-registered test

**Files:**
- Create: `protocol/src/polymer_protocol/commit.py`
- Create: `protocol/tests/test_commit.py`

For each claim that is PENDING, carries an `evaluation_plan`, and is not already locked, compute a stable hash over `[graph.content_hash, criterion dump]` and write it to `provenance.preregistration_hash`. If `provenance` is absent, create a minimal one: `Provenance(generated_by=GenerationMode.IMPORTED, search_cardinality=1, preregistration_hash=lock)` — `IMPORTED` because the claim entered exogenously, `search_cardinality=1` is the conservative/honest default (no inflated search budget). Idempotent: a claim that already has a `preregistration_hash` is left untouched (post-hoc divergence on a locked plan is what VERIFY's anti-HARKing check detects — `commit` must never overwrite an existing lock). Spec §6.4.

- [ ] **Step 1: Write `protocol/tests/test_commit.py`**

```python
from polymer_grammar import GenerationMode, Provenance, Status

from polymer_protocol.commit import commit
from polymer_protocol.corpus import Corpus
from tests.conftest import make_claim, make_plan


def test_commit_locks_pending_claim_without_provenance(empty_ledger):
    c = make_claim("a", status=Status.PENDING, plan=make_plan(0.01, 0.05))
    out = commit(Corpus(claims=(c,), fdr_ledger=empty_ledger))
    locked = out.by_id()["a"]
    assert locked.provenance is not None
    assert locked.provenance.generated_by == GenerationMode.IMPORTED
    assert locked.provenance.search_cardinality == 1
    assert locked.provenance.preregistration_hash is not None


def test_commit_preserves_existing_provenance(empty_ledger):
    prov = Provenance(generated_by=GenerationMode.HUMAN_AUTHORED, search_cardinality=7)
    c = make_claim("a", status=Status.PENDING, plan=make_plan(0.01, 0.05), provenance=prov)
    out = commit(Corpus(claims=(c,), fdr_ledger=empty_ledger))
    locked = out.by_id()["a"]
    assert locked.provenance.generated_by == GenerationMode.HUMAN_AUTHORED
    assert locked.provenance.search_cardinality == 7  # untouched
    assert locked.provenance.preregistration_hash is not None


def test_commit_is_idempotent_and_does_not_overwrite_lock(empty_ledger):
    c = make_claim("a", status=Status.PENDING, plan=make_plan(0.01, 0.05))
    once = commit(Corpus(claims=(c,), fdr_ledger=empty_ledger))
    twice = commit(once)
    assert (
        once.by_id()["a"].provenance.preregistration_hash
        == twice.by_id()["a"].provenance.preregistration_hash
    )
    # second pass changes nothing
    assert once.by_id()["a"] == twice.by_id()["a"]


def test_commit_skips_claims_without_a_plan(empty_ledger):
    c = make_claim("a", status=Status.PENDING)  # no evaluation_plan
    out = commit(Corpus(claims=(c,), fdr_ledger=empty_ledger))
    assert out.by_id()["a"].provenance is None
```

- [ ] **Step 2: Run to verify failure**

Run: `cd protocol && uv run pytest tests/test_commit.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Write `protocol/src/polymer_protocol/commit.py`**

```python
"""DESIGN/COMMIT: hash-lock the pre-registered test (anti-HARKing).

For a PENDING claim carrying an evaluation_plan, write a stable lock over the plan's
graph hash + criterion into provenance.preregistration_hash (minting a minimal,
conservative Provenance if absent). Idempotent — never overwrites an existing lock;
post-hoc divergence on the locked plan is VERIFY's job to catch. Spec §6.4.
"""
from __future__ import annotations

from polymer_grammar import Claim, GenerationMode, Provenance, Status

from .base import stable_sha
from .corpus import Corpus


def _lock(claim: Claim) -> str:
    plan = claim.evaluation_plan
    return stable_sha(
        [plan.graph.content_hash, plan.criterion.model_dump(mode="json")]
    )


def _is_locked(claim: Claim) -> bool:
    return claim.provenance is not None and claim.provenance.preregistration_hash is not None


def commit(corpus: Corpus) -> Corpus:
    new_claims = []
    changed = False
    for c in corpus.claims:
        if c.status != Status.PENDING or c.evaluation_plan is None or _is_locked(c):
            new_claims.append(c)
            continue
        lock = _lock(c)
        if c.provenance is None:
            prov = Provenance(
                generated_by=GenerationMode.IMPORTED,
                search_cardinality=1,
                preregistration_hash=lock,
            )
        else:
            prov = c.provenance.model_copy(update={"preregistration_hash": lock})
        new_claims.append(c.model_copy(update={"provenance": prov}))
        changed = True
    if not changed:
        return corpus
    return corpus.model_copy(update={"claims": tuple(new_claims)})
```

- [ ] **Step 4: Run to verify pass**

Run: `cd protocol && uv run pytest tests/test_commit.py -v`
Expected: all 4 PASS.

- [ ] **Step 5: Lint + commit**

```bash
cd protocol && uv run ruff check src tests
git add protocol/src/polymer_protocol/commit.py protocol/tests/test_commit.py
git commit -m "feat(protocol): commit() — idempotent hash-lock of the pre-registered test"
```

---

### Task 7: `execute_ground()` — the Phase-8 air-gapped gate

**Files:**
- Create: `protocol/src/polymer_protocol/execute.py`
- Create: `protocol/tests/test_execute.py`

For each committed (locked) PENDING claim that carries an `evaluation_plan` and is NOT safety-gated, run `verify(plan, ctx, adapters, claim_leaves=claim.leaves)` and collect the `VerifiedEvaluation` into an `ExecRecord`. EXECUTE writes no status — it produces evidence; VERIFY decides status. The corpus is returned unchanged alongside the records. **Precondition:** the caller supplies ≥2 distinct-identity adapters (else `verify` raises `SelfLicensingError` — the air-gap; this is a configuration error, not claim evidence, so it propagates). Spec §6.5.

- [ ] **Step 1: Write `protocol/tests/test_execute.py`**

```python
import pytest
from polymer_grammar import Governance, HazardClass, SelfLicensingError, Status

from polymer_protocol.commit import commit
from polymer_protocol.corpus import Corpus
from polymer_protocol.execute import execute_ground
from tests.conftest import make_claim, make_plan


def test_executes_committed_pending_claim(empty_ledger, ctx, adapters):
    c = make_claim("a", status=Status.PENDING, plan=make_plan(0.01, 0.05))
    corpus = commit(Corpus(claims=(c,), fdr_ledger=empty_ledger))
    _out, records = execute_ground(corpus, adapters, ctx)
    assert len(records) == 1
    rec = records[0]
    assert rec.claim_id == "a"
    # value 0.01 < threshold 0.05, two distinct adapters agree -> Satisfaction minted
    assert rec.evaluation.satisfaction is not None


def test_skips_uncommitted_claim(empty_ledger, ctx, adapters):
    c = make_claim("a", status=Status.PENDING, plan=make_plan(0.01, 0.05))  # NOT committed
    corpus = Corpus(claims=(c,), fdr_ledger=empty_ledger)
    _out, records = execute_ground(corpus, adapters, ctx)
    assert records == ()


def test_skips_safety_gated_claim(empty_ledger, ctx, adapters):
    c = make_claim(
        "a", status=Status.PENDING, plan=make_plan(0.01, 0.05),
        governance=Governance(hazard_class=HazardClass.HIGH),
    )
    corpus = commit(Corpus(claims=(c,), fdr_ledger=empty_ledger))
    _out, records = execute_ground(corpus, adapters, ctx)
    assert records == ()


def test_refuted_plan_mints_no_satisfaction(empty_ledger, ctx, adapters):
    c = make_claim("a", status=Status.PENDING, plan=make_plan(0.99, 0.05))  # 0.99 < 0.05 is false
    corpus = commit(Corpus(claims=(c,), fdr_ledger=empty_ledger))
    _out, records = execute_ground(corpus, adapters, ctx)
    assert records[0].evaluation.satisfaction is None


def test_single_adapter_raises_self_licensing(empty_ledger, ctx):
    from polymer_grammar import IdentityAdapter

    c = make_claim("a", status=Status.PENDING, plan=make_plan(0.01, 0.05))
    corpus = commit(Corpus(claims=(c,), fdr_ledger=empty_ledger))
    with pytest.raises(SelfLicensingError):
        execute_ground(corpus, (IdentityAdapter(),), ctx)
```

- [ ] **Step 2: Run to verify failure**

Run: `cd protocol && uv run pytest tests/test_execute.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Write `protocol/src/polymer_protocol/execute.py`**

```python
"""EXECUTE/GROUND: run the Phase-8 air-gapped gate over committed, non-gated claims.

Reuses evaluate.verify() — the two-implementation agreement gate that mints a Satisfaction
only on cross-adapter agreement + SATISFIED (no self-licensing). Produces evidence
(ExecRecords); writes no status (VERIFY decides). Caller must supply >=2 distinct-identity
adapters or verify() raises SelfLicensingError. Spec §6.5.
"""
from __future__ import annotations

from polymer_grammar import (
    Adapter,
    Claim,
    MaterializationContext,
    Status,
    requires_safety_review,
    verify,
)

from .corpus import Corpus, ExecRecord


def _is_executable(claim: Claim) -> bool:
    if claim.status != Status.PENDING or claim.evaluation_plan is None:
        return False
    # must be committed (locked) and not safety-gated
    if claim.provenance is None or claim.provenance.preregistration_hash is None:
        return False
    if claim.governance is not None and requires_safety_review(claim.governance):
        return False
    return True


def execute_ground(
    corpus: Corpus,
    adapters: tuple[Adapter, ...],
    ctx: MaterializationContext,
) -> tuple[Corpus, tuple[ExecRecord, ...]]:
    records = []
    for c in corpus.claims:
        if not _is_executable(c):
            continue
        evaluation = verify(c.evaluation_plan, ctx, adapters, claim_leaves=c.leaves)
        records.append(ExecRecord(claim_id=c.id, evaluation=evaluation))
    return corpus, tuple(records)
```

- [ ] **Step 4: Run to verify pass**

Run: `cd protocol && uv run pytest tests/test_execute.py -v`
Expected: all 5 PASS.

- [ ] **Step 5: Lint + commit**

```bash
cd protocol && uv run ruff check src tests
git add protocol/src/polymer_protocol/execute.py protocol/tests/test_execute.py
git commit -m "feat(protocol): execute_ground() — Phase-8 air-gapped verify over committed claims"
```

---

### Task 8: `verify_stage()` — status decision + Licensing assembly

**Files:**
- Create: `protocol/src/polymer_protocol/verify.py`
- Create: `protocol/tests/test_verify.py`

Decide each executed claim's `status` (spec §6.6):
- **LICENSED** requires ALL of: a minted `Satisfaction` (agreement + SATISFIED) AND grounded-extension membership AND `provenance` present (the selection-aware honesty gate — `search_cardinality` is recorded; it is type-guaranteed ≥1 whenever `provenance` exists). On LICENSED, assemble `Licensing(route=SEVERE_TEST, satisfactions=(satisfaction,), rival_set_closure=OPEN_ACKNOWLEDGED)` (one materialization → severe test; rivals not enumerated → open-acknowledged, the honest default). The cardinality-*scaled* threshold is deferred to SELECT/#3 — the spine enforces only presence.
- **REJECTED** if the executed verdict is a refutation (agreement on REFUTED) OR the claim is outside the grounded extension.
- **PENDING** otherwise (undetermined / partial / two-impl disagreement → triage; the claim already carries a valid `pending_reason`, so it is left unchanged).

Because Pydantic `model_copy(update=…)` does NOT re-run validators, status changes go through a `_with_status` helper that round-trips the updated claim through `Claim.model_validate`, guaranteeing no invalid `(status, pending_reason, licensing)` combination escapes.

- [ ] **Step 1: Write `protocol/tests/test_verify.py`**

```python
from polymer_grammar import LicenseRoute, SatisfactionVerdict, Status

from polymer_protocol.commit import commit
from polymer_protocol.corpus import Corpus, CycleScaffolding
from polymer_protocol.execute import execute_ground
from polymer_protocol.verify import verify_stage
from tests.conftest import make_claim, make_plan


def _run_to_records(claim, empty_ledger, ctx, adapters):
    corpus = commit(Corpus(claims=(claim,), fdr_ledger=empty_ledger))
    return execute_ground(corpus, adapters, ctx)


def test_satisfied_in_extension_becomes_licensed(empty_ledger, ctx, adapters):
    c = make_claim("a", status=Status.PENDING, plan=make_plan(0.01, 0.05))
    corpus, records = _run_to_records(c, empty_ledger, ctx, adapters)
    scaffolding = CycleScaffolding(grounded_extension=("a",))
    out = verify_stage(corpus, scaffolding, records)
    graded = out.by_id()["a"]
    assert graded.status == Status.LICENSED
    assert graded.pending_reason is None
    assert graded.licensing is not None
    assert graded.licensing.route == LicenseRoute.SEVERE_TEST
    assert graded.licensing.satisfactions[0].verdict == SatisfactionVerdict.SATISFIED


def test_satisfied_but_outside_extension_is_rejected(empty_ledger, ctx, adapters):
    c = make_claim("a", status=Status.PENDING, plan=make_plan(0.01, 0.05))
    corpus, records = _run_to_records(c, empty_ledger, ctx, adapters)
    scaffolding = CycleScaffolding(grounded_extension=())  # a is OUT
    out = verify_stage(corpus, scaffolding, records)
    assert out.by_id()["a"].status == Status.REJECTED


def test_refuted_claim_is_rejected(empty_ledger, ctx, adapters):
    c = make_claim("a", status=Status.PENDING, plan=make_plan(0.99, 0.05))
    corpus, records = _run_to_records(c, empty_ledger, ctx, adapters)
    scaffolding = CycleScaffolding(grounded_extension=("a",))
    out = verify_stage(corpus, scaffolding, records)
    graded = out.by_id()["a"]
    assert graded.status == Status.REJECTED
    assert graded.licensing is None


def test_two_impl_disagreement_stays_pending(empty_ledger, ctx):
    from polymer_grammar import IdentityAdapter, ReferenceAdapter

    c = make_claim("a", status=Status.PENDING, plan=make_plan(0.01, 0.05))
    corpus = commit(Corpus(claims=(c,), fdr_ledger=empty_ledger))
    # perturbed reference adapter -> terminal values disagree -> no mint, disagreement set
    disagreeing = (IdentityAdapter(), ReferenceAdapter(identity="reference", perturb=10.0))
    corpus, records = execute_ground(corpus, disagreeing, ctx)
    assert records[0].evaluation.agreement is False
    scaffolding = CycleScaffolding(grounded_extension=("a",))
    out = verify_stage(corpus, scaffolding, records)
    assert out.by_id()["a"].status == Status.PENDING


def test_claim_without_record_is_untouched(empty_ledger, ctx, adapters):
    executed = make_claim("a", status=Status.PENDING, plan=make_plan(0.01, 0.05))
    bystander = make_claim("b", status=Status.CONJECTURED)
    corpus = commit(Corpus(claims=(executed, bystander), fdr_ledger=empty_ledger))
    corpus, records = execute_ground(corpus, adapters, ctx)
    scaffolding = CycleScaffolding(grounded_extension=("a", "b"))
    out = verify_stage(corpus, scaffolding, records)
    assert out.by_id()["b"].status == Status.CONJECTURED
```

- [ ] **Step 2: Run to verify failure**

Run: `cd protocol && uv run pytest tests/test_verify.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Write `protocol/src/polymer_protocol/verify.py`**

```python
"""VERIFY: decide each executed claim's status + assemble Licensing.

LICENSED <=> minted Satisfaction (agreement + SATISFIED) AND grounded-extension membership
AND provenance present (search_cardinality recorded — the selection-aware honesty gate).
REJECTED <=> refuted, or outside the grounded extension. Else PENDING (triage). This is the
Licensing-assembly + status-flip that Phase 8 deliberately left to the protocol. Spec §6.6.
"""
from __future__ import annotations

from polymer_grammar import (
    Claim,
    LicenseRoute,
    Licensing,
    RivalSetClosure,
    SatisfactionVerdict,
    Status,
)

from .corpus import Corpus, CycleScaffolding, ExecRecord


def _with_status(claim: Claim, **update) -> Claim:
    """Apply a status/licensing/pending_reason update AND re-run Claim validators
    (model_copy alone skips validation)."""
    return Claim.model_validate(claim.model_copy(update=update).model_dump())


def verify_stage(
    corpus: Corpus,
    scaffolding: CycleScaffolding,
    exec_records: tuple[ExecRecord, ...],
) -> Corpus:
    in_ext = set(scaffolding.grounded_extension)
    rec_by_id = {r.claim_id: r for r in exec_records}
    new_claims = []
    for c in corpus.claims:
        rec = rec_by_id.get(c.id)
        if rec is None:
            new_claims.append(c)
            continue
        ev = rec.evaluation
        agreed_refuted = (
            ev.agreement
            and ev.results
            and ev.results[0].verdict == SatisfactionVerdict.REFUTED
        )
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
                )
            )
        elif agreed_refuted or c.id not in in_ext:
            new_claims.append(
                _with_status(c, status=Status.REJECTED, licensing=None, pending_reason=None)
            )
        else:
            new_claims.append(c)  # stays PENDING — already carries a valid pending_reason
    return corpus.model_copy(update={"claims": tuple(new_claims)})
```

- [ ] **Step 4: Run to verify pass**

Run: `cd protocol && uv run pytest tests/test_verify.py -v`
Expected: all 5 PASS.

- [ ] **Step 5: Lint + commit**

```bash
cd protocol && uv run ruff check src tests
git add protocol/src/polymer_protocol/verify.py protocol/tests/test_verify.py
git commit -m "feat(protocol): verify_stage() — status decision + Licensing assembly"
```

---

### Task 9: `integrate()` — revision contest + FDR ledger advance

**Files:**
- Create: `protocol/src/polymer_protocol/integrate.py`
- Create: `protocol/tests/test_integrate.py`

Admit graded claims and run corpus revision (spec §6.7):
1. Recompute derived rebut edges from current (post-VERIFY) claims (`derived_rebut_edges`), merged with authored edges (dedup by `(source, target, kind)`), so newly-LICENSED claims' material incompatibilities become rebut edges.
2. Run the entrenchment contest on any introduced inconsistency: `restore_consistency(claims, merged_edges, prior_in=frozenset(scaffolding.grounded_extension))` — the newcomer yields per AGM. Use its `claims` (consistent core) and `edges` (kept).
3. Advance the online-FDR ledger: one `process_test(ledger, claim_id, p_value)` per newly-executed claim, in deterministic (`claim_id`-sorted) order. The p-value is the executed **terminal value** (`evaluation.results[0].terminal.value`); claims whose terminal value is non-numeric or outside `[0, 1]` are skipped (logged via the return, not raised).

**Spine deferrals (documented, not wired):** Duhem blame (`aggregate_blame`/`duhem_status`) needs protocol-supplied `BlameSet`s — the spine `Corpus` carries no blame input, so blame is a no-op here and rides #4/#5. Library-learning, units commensuration, and empirical-null calibration are out (spec §7).

`integrate` returns the new `Corpus` and the list of skipped-claim ids (so `run_cycle` can audit them). Signature: `integrate(corpus, scaffolding, exec_records) -> tuple[Corpus, tuple[str, ...]]`.

- [ ] **Step 1: Write `protocol/tests/test_integrate.py`**

```python
from polymer_grammar import Status

from polymer_protocol.corpus import Corpus, CycleScaffolding, ExecRecord
from polymer_protocol.integrate import integrate
from tests.conftest import make_claim, make_plan


def _exec_record_with_value(claim_id, value, ctx, adapters, empty_ledger):
    """Helper: produce a real ExecRecord by executing a const-`value` plan."""
    from polymer_protocol.commit import commit
    from polymer_protocol.execute import execute_ground

    c = make_claim(claim_id, status=Status.PENDING, plan=make_plan(value, 0.05))
    corpus = commit(Corpus(claims=(c,), fdr_ledger=empty_ledger))
    _out, records = execute_ground(corpus, adapters, ctx)
    return records[0]


def test_fdr_ledger_advances_one_test_per_executed_claim(empty_ledger, ctx, adapters):
    rec = _exec_record_with_value("a", 0.01, ctx, adapters, empty_ledger)
    licensed = make_claim("a", status=Status.LICENSED)  # post-VERIFY status
    corpus = Corpus(claims=(licensed,), fdr_ledger=empty_ledger)
    scaffolding = CycleScaffolding(grounded_extension=("a",))
    out, skipped = integrate(corpus, scaffolding, (rec,))
    assert out.fdr_ledger.n_tests == 1
    assert out.fdr_ledger.tests[0].claim_id == "a"
    assert out.fdr_ledger.tests[0].p_value == 0.01
    assert skipped == ()


def test_non_pvalue_terminal_is_skipped(empty_ledger, ctx, adapters):
    # terminal value 7.0 is outside [0,1] -> not a valid p-value -> skipped, logged.
    rec = _exec_record_with_value("a", 7.0, ctx, adapters, empty_ledger)
    c = make_claim("a", status=Status.PENDING)
    corpus = Corpus(claims=(c,), fdr_ledger=empty_ledger)
    scaffolding = CycleScaffolding(grounded_extension=("a",))
    out, skipped = integrate(corpus, scaffolding, (rec,))
    assert out.fdr_ledger.n_tests == 0
    assert skipped == ("a",)


def test_integrate_keeps_consistent_claims(empty_ledger, ctx, adapters):
    rec = _exec_record_with_value("a", 0.01, ctx, adapters, empty_ledger)
    corpus = Corpus(claims=(make_claim("a", status=Status.LICENSED),), fdr_ledger=empty_ledger)
    scaffolding = CycleScaffolding(grounded_extension=("a",))
    out, _skipped = integrate(corpus, scaffolding, (rec,))
    assert "a" in out.by_id()  # no inconsistency -> claim survives
```

- [ ] **Step 2: Run to verify failure**

Run: `cd protocol && uv run pytest tests/test_integrate.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Write `protocol/src/polymer_protocol/integrate.py`**

```python
"""INTEGRATE: admit graded claims, run the AGM revision contest, advance the FDR ledger.

Recomputes derived rebut edges, runs restore_consistency (newcomer yields per AGM), and
processes one online-FDR test per executed claim using its executed terminal value as the
p-value. Duhem blame needs protocol-supplied BlameSets (no input surface in the spine
Corpus) and is deferred to #4/#5. Spec §6.7.
"""
from __future__ import annotations

from polymer_grammar import derived_rebut_edges, process_test, restore_consistency

from .corpus import Corpus, CycleScaffolding, ExecRecord


def _merge_edges(authored, derived):
    seen = {(e.source, e.target, e.kind) for e in authored}
    out = list(authored)
    for e in derived:
        key = (e.source, e.target, e.kind)
        if key not in seen:
            seen.add(key)
            out.append(e)
    return tuple(out)


def _terminal_value(record: ExecRecord):
    results = record.evaluation.results
    if not results:
        return None
    return results[0].terminal.value


def integrate(
    corpus: Corpus,
    scaffolding: CycleScaffolding,
    exec_records: tuple[ExecRecord, ...],
) -> tuple[Corpus, tuple[str, ...]]:
    # 1. derived rebut edges from the post-VERIFY claims, merged with authored.
    merged = _merge_edges(corpus.defeat_edges, derived_rebut_edges(corpus.claims))

    # 2. entrenchment contest (newcomer yields per AGM).
    rr = restore_consistency(
        corpus.claims, merged, prior_in=frozenset(scaffolding.grounded_extension)
    )

    # 3. online-FDR: one test per executed claim, deterministic order, valid p-values only.
    ledger = corpus.fdr_ledger
    skipped = []
    for rec in sorted(exec_records, key=lambda r: r.claim_id):
        val = _terminal_value(rec)
        if isinstance(val, (int, float)) and not isinstance(val, bool) and 0.0 <= val <= 1.0:
            ledger = process_test(ledger, rec.claim_id, float(val))
        else:
            skipped.append(rec.claim_id)

    new_corpus = corpus.model_copy(
        update={"claims": rr.claims, "defeat_edges": rr.edges, "fdr_ledger": ledger}
    )
    return new_corpus, tuple(skipped)
```

- [ ] **Step 4: Run to verify pass**

Run: `cd protocol && uv run pytest tests/test_integrate.py -v`
Expected: all 3 PASS.

- [ ] **Step 5: Lint + commit**

```bash
cd protocol && uv run ruff check src tests
git add protocol/src/polymer_protocol/integrate.py protocol/tests/test_integrate.py
git commit -m "feat(protocol): integrate() — derived edges + AGM contest + FDR ledger advance"
```

---

### Task 10: `run_cycle()` — chain the stages

**Files:**
- Create: `protocol/src/polymer_protocol/cycle.py`
- Create: `protocol/tests/test_cycle.py` (the per-stage chaining; full integration + determinism land in Task 11)

Chain the stages exactly per spec §6.8, threading the ephemeral values, building a `StageAudit` per stage, and recomputing `represent` on the post-INTEGRATE corpus to emit the next-cycle frontier (the keystone closure). `represent` writes nothing, so calling it twice is free and keeps the cycle reversible.

```
scaffolding      = represent(corpus)
corpus           = canonicalize(corpus)
corpus, gated    = safety_gate(corpus)
corpus           = commit(corpus)
corpus, records  = execute_ground(corpus, adapters, ctx)   # only non-gated, committed
corpus           = verify_stage(corpus, scaffolding, records)
corpus, skipped  = integrate(corpus, scaffolding, records)
frontier         = represent(corpus).frontier
```

- [ ] **Step 1: Write `protocol/tests/test_cycle.py`**

```python
from polymer_grammar import Status

from polymer_protocol.corpus import Corpus
from polymer_protocol.cycle import run_cycle
from tests.conftest import make_claim, make_plan


def test_cycle_licenses_a_satisfied_claim(empty_ledger, ctx, adapters):
    c = make_claim("a", status=Status.PENDING, plan=make_plan(0.01, 0.05))
    result = run_cycle(Corpus(claims=(c,), fdr_ledger=empty_ledger), adapters, ctx)
    assert result.corpus.by_id()["a"].status == Status.LICENSED
    assert result.corpus.fdr_ledger.n_tests == 1
    assert result.gated_lane == ()
    # audit records one line per stage
    assert {a.stage for a in result.audit} == {
        "represent", "canonicalize", "safety_gate", "commit",
        "execute_ground", "verify_stage", "integrate",
    }


def test_cycle_reports_gated_lane(empty_ledger, ctx, adapters):
    from polymer_grammar import Governance, HazardClass

    hot = make_claim(
        "h", status=Status.PENDING, plan=make_plan(0.01, 0.05),
        governance=Governance(hazard_class=HazardClass.HIGH),
    )
    result = run_cycle(Corpus(claims=(hot,), fdr_ledger=empty_ledger), adapters, ctx)
    assert result.gated_lane == ("h",)
    # gated claim was NOT executed -> still PENDING, no FDR test
    assert result.corpus.by_id()["h"].status == Status.PENDING
    assert result.corpus.fdr_ledger.n_tests == 0
```

- [ ] **Step 2: Run to verify failure**

Run: `cd protocol && uv run pytest tests/test_cycle.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Write `protocol/src/polymer_protocol/cycle.py`**

```python
"""run_cycle: chain the deterministic assessment stages into one total Corpus transform.

Threads the ephemeral scaffolding/records; emits the post-INTEGRATE unresolved-attack
frontier as the cycle's primary output (the keystone closure — the next cycle's
GENERATE/SELECT target). GENERATE and SELECT are not in this sub-project: claims enter
exogenously and every committed, non-gated PENDING claim is executed. Spec §6.8.
"""
from __future__ import annotations

from polymer_grammar import Adapter, MaterializationContext, Status

from .canonicalize import canonicalize
from .commit import commit
from .corpus import Corpus, CycleResult, StageAudit
from .execute import execute_ground
from .integrate import integrate
from .represent import represent
from .safety import safety_gate
from .verify import verify_stage


def run_cycle(
    corpus: Corpus,
    adapters: tuple[Adapter, ...],
    ctx: MaterializationContext,
) -> CycleResult:
    audit: list[StageAudit] = []

    scaffolding = represent(corpus)
    audit.append(
        StageAudit(
            stage="represent",
            note=f"{len(scaffolding.grounded_extension)} grounded, {len(scaffolding.frontier)} on frontier",
            count=len(scaffolding.frontier),
        )
    )

    before_eq = len(corpus.equivalences)
    corpus = canonicalize(corpus)
    audit.append(
        StageAudit(
            stage="canonicalize",
            note=f"{len(corpus.equivalences) - before_eq} equivalence edge(s) added",
            count=len(corpus.equivalences) - before_eq,
        )
    )

    corpus, gated = safety_gate(corpus)
    audit.append(StageAudit(stage="safety_gate", note=f"{len(gated)} gated", count=len(gated)))

    n_pending = sum(1 for c in corpus.claims if c.status == Status.PENDING)
    corpus = commit(corpus)
    audit.append(StageAudit(stage="commit", note=f"{n_pending} pending claim(s) seen", count=n_pending))

    corpus, records = execute_ground(corpus, adapters, ctx)
    audit.append(StageAudit(stage="execute_ground", note=f"{len(records)} executed", count=len(records)))

    corpus = verify_stage(corpus, scaffolding, records)
    n_licensed = sum(1 for c in corpus.claims if c.status == Status.LICENSED)
    audit.append(StageAudit(stage="verify_stage", note=f"{n_licensed} licensed", count=n_licensed))

    corpus, skipped = integrate(corpus, scaffolding, records)
    audit.append(
        StageAudit(
            stage="integrate",
            note=f"{corpus.fdr_ledger.n_tests} FDR test(s); {len(skipped)} skipped",
            count=len(skipped),
        )
    )

    frontier = represent(corpus).frontier
    return CycleResult(
        corpus=corpus,
        frontier=frontier,
        gated_lane=gated,
        audit=tuple(audit),
    )
```

- [ ] **Step 4: Run to verify pass**

Run: `cd protocol && uv run pytest tests/test_cycle.py -v`
Expected: both PASS.

- [ ] **Step 5: Lint + commit**

```bash
cd protocol && uv run ruff check src tests
git add protocol/src/polymer_protocol/cycle.py protocol/tests/test_cycle.py
git commit -m "feat(protocol): run_cycle() — chain the seven stages + emit the keystone frontier"
```

---

### Task 11: Public surface, determinism guarantee, and docs

**Files:**
- Modify: `protocol/src/polymer_protocol/__init__.py`
- Modify: `protocol/tests/test_cycle.py` (add the determinism + frontier-closure tests)
- Modify: `README.md`
- Modify: `docs/superpowers/CONTINUE.md`

- [ ] **Step 1: Add the determinism + frontier-closure tests to `protocol/tests/test_cycle.py`**

```python
def test_cycle_is_deterministic(empty_ledger, ctx, adapters):
    def build():
        return Corpus(
            claims=(
                make_claim("a", status=Status.PENDING, plan=make_plan(0.01, 0.05)),
                make_claim("b", status=Status.PENDING, plan=make_plan(0.99, 0.05)),
            ),
            fdr_ledger=empty_ledger,
        )

    first = run_cycle(build(), adapters, ctx)
    second = run_cycle(build(), adapters, ctx)
    assert first == second  # same (corpus, adapters, ctx) -> identical CycleResult


def test_frontier_is_emitted_for_an_unresolved_attack(empty_ledger, ctx, adapters):
    from polymer_grammar import DefeatEdge, DefeatEdgeKind

    # b (CONJECTURED, no plan) attacks a; nothing defends a -> a is on the frontier.
    a = make_claim("a")
    b = make_claim("b")
    edge = DefeatEdge(source="b", target="a", kind=DefeatEdgeKind.REBUT)
    corpus = Corpus(claims=(a, b), defeat_edges=(edge,), fdr_ledger=empty_ledger)
    result = run_cycle(corpus, adapters, ctx)
    assert result.frontier == ("a",)
```

- [ ] **Step 2: Run the full test suite**

Run: `cd protocol && uv run pytest -q`
Expected: all tests PASS (Tasks 1–11). Note the total count.

- [ ] **Step 3: Update `protocol/src/polymer_protocol/__init__.py` to export the public surface**

```python
"""polymer_protocol — the protocol runtime (assessment spine) over polymer_grammar."""
from __future__ import annotations

__version__ = "0.1.0"

from .base import _Model, stable_sha
from .canonicalize import canonicalize
from .commit import commit
from .corpus import (
    Corpus,
    CycleResult,
    CycleScaffolding,
    ExecRecord,
    StageAudit,
)
from .cycle import run_cycle
from .execute import execute_ground
from .integrate import integrate
from .represent import represent
from .safety import safety_gate
from .verify import verify_stage

__all__ = [
    "_Model",
    "stable_sha",
    "__version__",
    "Corpus",
    "CycleResult",
    "CycleScaffolding",
    "ExecRecord",
    "StageAudit",
    "represent",
    "canonicalize",
    "safety_gate",
    "commit",
    "execute_ground",
    "verify_stage",
    "integrate",
    "run_cycle",
]
```

- [ ] **Step 4: Verify the package imports cleanly through the public surface**

Run: `cd protocol && uv run python -c "import polymer_protocol as p; print(sorted(p.__all__))"`
Expected: prints the export list with no ImportError.

- [ ] **Step 5: Add a "Protocol runtime" section to `README.md`**

Add a short section after the grammar section describing: the `protocol/` package, the `Corpus` + seven-stage spine, the `run_cycle` entry point, that EXECUTE reuses the Phase-8 air-gap, and that GENERATE/SELECT are stubbed open ports (sub-projects #3/#4). Keep it to ~10 lines, matching the existing README tone. Reference the spec path `docs/superpowers/specs/2026-06-02-protocol-spine-design.md`.

- [ ] **Step 6: Update `docs/superpowers/CONTINUE.md`**

Update the "Current state" and "NEXT" lines: protocol sub-project #1 (Corpus + assessment spine) is DONE — package `polymer_protocol` builds the seven-stage `run_cycle` over the grammar, isolation-tested, N tests green. Set NEXT to sub-project #2 (Oracle dossier, binds `OperationNode.oracle_ref`) per the decomposition. Record the merge commit once Task 11 lands.

- [ ] **Step 7: Final lint + commit**

```bash
cd protocol && uv run ruff check src tests
git add protocol/src/polymer_protocol/__init__.py protocol/tests/test_cycle.py README.md docs/superpowers/CONTINUE.md
git commit -m "feat(protocol): public surface + determinism guarantee + docs (sub-project #1 complete)"
```

---

## Progress Log

_(Update after every task: check the boxes, record the commit SHA + any decisions.)_

- [ ] Task 1 — package scaffold + isolation guard — commit: `____`
- [ ] Task 2 — Corpus + ephemeral types — commit: `____`
- [ ] Task 3 — represent() — commit: `____`
- [ ] Task 4 — canonicalize() — commit: `____`
- [ ] Task 5 — safety_gate() — commit: `____`
- [ ] Task 6 — commit() — commit: `____`
- [ ] Task 7 — execute_ground() — commit: `____`
- [ ] Task 8 — verify_stage() — commit: `____`
- [ ] Task 9 — integrate() — commit: `____`
- [ ] Task 10 — run_cycle() — commit: `____`
- [ ] Task 11 — public surface + determinism + docs — commit: `____`

**Decisions / deviations:** _(record here as they happen)_

---

## Self-Review Notes (plan author)

**Spec coverage** — every spec §6 stage maps to a task: §6.1 represent→T3, §6.2 canonicalize→T4, §6.3 safety_gate→T5, §6.4 commit→T6, §6.5 execute_ground→T7, §6.6 verify_stage→T8, §6.7 integrate→T9, §6.8 run_cycle→T10. Corpus + ephemeral types (§4, §5)→T2. Package/isolation (§2, §3)→T1. Testing (§8)→woven through + T11 determinism. Connections (§9: frontier emission, Phase-8 reuse)→T7/T10/T11.

**Deliberate narrowings (documented in-task, faithful to the spec's "spine boundary" fences):**
- canonicalize records equivalence edges only — no physical node deletion / provenance-merge (rides #3). Matches the grammar's identity philosophy and the §8 test ("collapse to one equivalence class").
- integrate wires Duhem blame as a documented deferral (no `BlameSet` input surface in the spine Corpus).
- `integrate` returns `(Corpus, skipped_ids)` — one extra return vs the spec's `Corpus` signature, so `run_cycle` can audit FDR-skipped claims. This is an additive, internal-only refinement; the stage remains pure and total.

**Type consistency** — `Corpus`, `CycleScaffolding`, `ExecRecord`, `StageAudit`, `CycleResult` defined in T2 and used unchanged downstream. Stage signatures match §6 (with the integrate refinement noted). All grammar calls use verified signatures from the API block above.
