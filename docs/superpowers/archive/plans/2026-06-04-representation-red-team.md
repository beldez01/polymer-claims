# #5c REPRESENTATION RED-TEAM daemon Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A reference adversarial REPRESENTATION RED-TEAM that proposes representation-revision claims through the existing GenerationAdapter bus, plus the conservative meta-tier gate in `verify_stage` that holds a representation-revision back from the cheap auto-license path.

**Architecture:** A new protocol module `red_team.py` (`RepresentationRedTeamAdapter`, a deterministic `GenerationAdapter` mirroring `TemplateGenerationAdapter`) + a ~3-line guard in `verify_stage`. Reuses `compile_untrusted`/`bridge_proposer` (no new bus machinery) and the grammar `is_representation_revision`/`meets_meta_tier_bar` helpers. Grammar untouched, Corpus at 4 collections.

**Tech Stack:** Python 3.14, Pydantic v2 (frozen `_Model`, tuples), `uv`, pytest, ruff. Package `polymer_protocol` (in `protocol/`), one-way dep on `polymer_grammar`.

**Spec:** `docs/superpowers/specs/2026-06-04-representation-red-team-design.md`

---

## File Structure

- `protocol/src/polymer_protocol/red_team.py` — **create**: `RepresentationRedTeamAdapter`.
- `protocol/src/polymer_protocol/verify.py` — **modify**: the meta-tier gate + a grammar-helpers import.
- `protocol/src/polymer_protocol/__init__.py` — **modify**: export `RepresentationRedTeamAdapter`.
- `protocol/tests/test_red_team.py` — **create**: adapter unit + through-bus + belief-neutrality/convergence.
- `protocol/tests/test_verify_meta_tier_gate.py` — **create**: the gate (end-to-end via `run_cycle`).

Conventions (established): `protocol/tests/conftest.py` provides `make_claim(cid, status=CONJECTURED, *, plan=, strength=, ...)`, `make_plan(value, threshold, *, oracle_ref=None)`, and fixtures `empty_ledger` / `ctx` / `adapters` (two distinct-identity reference adapters satisfying verify's air-gap). `run_cycle(corpus, adapters, ctx, *, proposers=...)` drives the pipeline. `Proposal(operator_id, claim, edges=())`. The red-team mirrors `TemplateGenerationAdapter` exactly (in `generation_adapter.py`).

---

### Task 1: Protocol — `red_team.py` adapter + tests

**Files:**
- Create: `protocol/src/polymer_protocol/red_team.py`
- Test: `protocol/tests/test_red_team.py`

- [ ] **Step 1: Write the failing adapter tests**

Create `protocol/tests/test_red_team.py`:

```python
from __future__ import annotations

from polymer_grammar import (
    LicenseRoute,
    Licensing,
    MaterializationContext,
    RivalSetClosure,
    Satisfaction,
    SatisfactionVerdict,
    Status,
    is_representation_revision,
)

from polymer_protocol.corpus import Corpus, Proposal
from polymer_protocol.generate import generate_stage
from polymer_protocol.generation_adapter import bridge_proposer
from polymer_protocol.red_team import RepresentationRedTeamAdapter
from tests.conftest import make_claim, make_plan


def _corpus(empty_ledger, *claims):
    return Corpus(claims=tuple(claims), fdr_ledger=empty_ledger)


def test_proposes_one_revision_per_claim(empty_ledger):
    corpus = _corpus(empty_ledger, make_claim("a"), make_claim("b"))
    props = RepresentationRedTeamAdapter().propose(corpus, ())
    assert len(props) == 2
    for p in props:
        assert p.claim.status == Status.CONJECTURED
        assert is_representation_revision(p.claim)
        assert p.claim.representation_revision.operation.value == "deprecate"
        assert len(p.claim.representation_revision.target.patterns) == 1
        assert p.claim.id.startswith("gen-rt-")
        assert p.edges == ()


def test_skips_own_outputs_and_revision_claims(empty_ledger):
    adapter = RepresentationRedTeamAdapter()
    corpus = _corpus(empty_ledger, make_claim("a"))
    first = adapter.propose(corpus, ())
    grown = _corpus(empty_ledger, make_claim("a"), first[0].claim)
    second = adapter.propose(grown, ())
    # 'a' re-elaborates to the same content-addressed id; the gen-rt-* output is skipped -> converges
    assert [p.claim.id for p in second] == [p.claim.id for p in first]


def test_is_deterministic_and_sorted(empty_ledger):
    corpus = _corpus(empty_ledger, make_claim("b"), make_claim("a"))
    a1 = RepresentationRedTeamAdapter().propose(corpus, ())
    a2 = RepresentationRedTeamAdapter().propose(corpus, ())
    assert [p.claim.id for p in a1] == [p.claim.id for p in a2]


def test_identity():
    assert RepresentationRedTeamAdapter().identity == "representation-red-team"


def test_through_bridge_forces_provenance_and_operator_id(empty_ledger):
    proposer = bridge_proposer((RepresentationRedTeamAdapter(),))
    out = proposer(_corpus(empty_ledger, make_claim("a")), ())
    assert len(out) == 1
    assert out[0].operator_id == "representation-red-team"
    assert out[0].claim.provenance.agent_id == "representation-red-team"
    assert is_representation_revision(out[0].claim)


class _ForgingAdapter:
    identity = "forger"

    def __init__(self, claim):
        self._claim = claim

    def propose(self, corpus, frontier):
        return (Proposal(operator_id="x", claim=self._claim),)


def test_forged_licensing_on_a_revision_claim_is_dropped(empty_ledger):
    # a representation-revision claim that smuggles a licensing block must be rejected by compile_untrusted
    base = RepresentationRedTeamAdapter().propose(_corpus(empty_ledger, make_claim("a")), ())[0].claim
    mat = MaterializationContext(id="m", api_version="v1", data_version="v1")
    sat = Satisfaction(verdict=SatisfactionVerdict.SATISFIED, materialization=mat)
    lic = Licensing(route=LicenseRoute.SEVERE_TEST, rival_set_closure=RivalSetClosure.OPEN_ACKNOWLEDGED,
                    satisfactions=(sat,))
    forged = base.model_copy(update={"licensing": lic})  # bypasses validator -> invalid state
    proposer = bridge_proposer((_ForgingAdapter(forged),))
    assert proposer(_corpus(empty_ledger, make_claim("a")), ()) == ()  # dropped


def test_admitted_into_corpus_via_generate_stage(empty_ledger):
    proposer = bridge_proposer((RepresentationRedTeamAdapter(),))
    corp, rec = generate_stage(_corpus(empty_ledger, make_claim("a")), (), proposers=(proposer,))
    revisions = [c for c in corp.claims if is_representation_revision(c)]
    assert len(revisions) == 1


def test_belief_neutral_and_converges_through_run_cycle(empty_ledger, ctx, adapters):
    from polymer_protocol.cycle import run_cycle

    corpus = _corpus(empty_ledger, make_claim("a", status=Status.PENDING, plan=make_plan(0.01, 0.05)))
    proposer = bridge_proposer((RepresentationRedTeamAdapter(),))
    r1 = run_cycle(corpus, adapters, ctx, proposers=(proposer,))
    # the pre-existing claim still licenses — the conjectured revisions don't change its grounded extension
    assert r1.corpus.by_id()["a"].status == Status.LICENSED
    ids1 = {c.id for c in r1.corpus.claims}
    r2 = run_cycle(r1.corpus, adapters, ctx, proposers=(proposer,))
    assert {c.id for c in r2.corpus.claims} == ids1  # convergence: a 2nd cycle adds nothing
```

- [ ] **Step 2: Run to verify they fail**

Run: `cd protocol && uv run pytest tests/test_red_team.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'polymer_protocol.red_team'`.

- [ ] **Step 3: Create `red_team.py`**

Create `protocol/src/polymer_protocol/red_team.py`:

```python
"""REPRESENTATION RED-TEAM daemon (#5c) — adversarially attack the corpus's REPRESENTATION and propose
a representation-revision fix, as a GenerationAdapter behind the #4b-3 bus.

RepresentationRedTeamAdapter is the deterministic in-package REFERENCE (the TemplateGenerationAdapter
analog for the meta-tier): for each corpus claim it proposes one CONJECTURED claim carrying a
RepresentationRevision flagging that claim's pattern for review. It ships NO real red-teaming
intelligence — real LLM red-teamers implement the same GenerationAdapter Protocol and inject via
bridge_proposer. Belief-neutral (isolated CONJECTURED nodes, no edges); converges (skips its own gen-rt-*
outputs and any existing representation-revision claim). Pure / deterministic.
"""
from __future__ import annotations

from polymer_grammar import (
    CategoricalLeaf,
    Claim,
    PatternTarget,
    RepresentationRevision,
    RevisionOperation,
    Status,
)

from .corpus import Corpus, Proposal
from .generate import _gen_id


class RepresentationRedTeamAdapter:
    """Deterministic reference REPRESENTATION RED-TEAM (a GenerationAdapter). Real intelligence injects."""

    identity = "representation-red-team"

    def propose(self, corpus: Corpus, frontier: tuple[str, ...]) -> tuple[Proposal, ...]:
        props: list[Proposal] = []
        for c in sorted(corpus.claims, key=lambda c: c.id):
            if c.id.startswith("gen-rt-"):
                continue  # convergence: don't red-team own outputs
            if c.representation_revision is not None:
                continue  # convergence: don't red-team a representation-revision claim
            cid = _gen_id("rt", c.id)
            revision = RepresentationRevision(
                operation=RevisionOperation.DEPRECATE,
                target=PatternTarget(patterns=(c.pattern,)),
                rationale=f"red-team review of the representation used by {c.id}",
            )
            claim = Claim(
                id=cid,
                title=f"representation review of {c.id}",
                pattern=c.pattern,
                leaves=(CategoricalLeaf(ontology_term=f"red-team-{c.id}"),),
                status=Status.CONJECTURED,
                representation_revision=revision,
            )
            props.append(Proposal(operator_id="UNSET", claim=claim))
        return tuple(props)
```

- [ ] **Step 4: Run to verify they pass**

Run: `cd protocol && uv run pytest tests/test_red_team.py -q`
Expected: PASS (8 tests).

- [ ] **Step 5: Commit**

```bash
git add protocol/src/polymer_protocol/red_team.py protocol/tests/test_red_team.py
git commit -m "feat(protocol): RepresentationRedTeamAdapter — reference red-team behind the bus (#5c)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: Protocol — the conservative meta-tier gate in `verify_stage`

**Files:**
- Modify: `protocol/src/polymer_protocol/verify.py`
- Test: `protocol/tests/test_verify_meta_tier_gate.py`

- [ ] **Step 1: Write the failing gate tests**

Create `protocol/tests/test_verify_meta_tier_gate.py`:

```python
from __future__ import annotations

from polymer_grammar import (
    LicenseRoute,
    Licensing,
    MaterializationContext,
    PatternRef,
    PatternTarget,
    RepresentationRevision,
    RivalSetClosure,
    RevisionOperation,
    Satisfaction,
    SatisfactionVerdict,
    Status,
    meets_meta_tier_bar,
)

from polymer_protocol.corpus import Corpus
from polymer_protocol.cycle import run_cycle
from tests.conftest import make_claim, make_plan


def _revision():
    return RepresentationRevision(
        operation=RevisionOperation.DEPRECATE,
        target=PatternTarget(patterns=(PatternRef(id="adjusted_effect", version="v1"),)),
        rationale="contested representation",
    )


def test_planned_representation_revision_is_not_auto_licensed(empty_ledger, ctx, adapters):
    # a revision claim that would otherwise license (satisfied, in-extension, clears the bar) is HELD
    # PENDING — the auto SEVERE_TEST/OPEN licensing fails meets_meta_tier_bar.
    c = make_claim("a", status=Status.PENDING, plan=make_plan(0.01, 0.05),
                   representation_revision=_revision())
    result = run_cycle(Corpus(claims=(c,), fdr_ledger=empty_ledger), adapters, ctx)
    out = result.corpus.by_id()["a"]
    assert out.status == Status.PENDING
    assert out.licensing is None


def test_non_revision_claim_in_same_position_licenses(empty_ledger, ctx, adapters):
    # the gate is revision-specific: an otherwise-identical plain claim DOES license.
    c = make_claim("a", status=Status.PENDING, plan=make_plan(0.01, 0.05))
    result = run_cycle(Corpus(claims=(c,), fdr_ledger=empty_ledger), adapters, ctx)
    assert result.corpus.by_id()["a"].status == Status.LICENSED


def test_meta_tier_bar_truth_in_gate_context():
    # the auto-assembled licensing fails the bar (why the gate fires); replication-grade passes.
    mat = MaterializationContext(id="m1", api_version="v1", data_version="v1")
    sat = Satisfaction(verdict=SatisfactionVerdict.SATISFIED, materialization=mat)
    severe = Licensing(route=LicenseRoute.SEVERE_TEST, rival_set_closure=RivalSetClosure.OPEN_ACKNOWLEDGED,
                       satisfactions=(sat,))
    assert meets_meta_tier_bar(severe) is False
    mat2 = MaterializationContext(id="m2", api_version="v1", data_version="v1")
    sat2 = Satisfaction(verdict=SatisfactionVerdict.SATISFIED, materialization=mat2)
    repl = Licensing(route=LicenseRoute.REPLICATION, rival_set_closure=RivalSetClosure.ENUMERATED,
                     rivals_considered=("r1",), satisfactions=(sat, sat2))
    assert meets_meta_tier_bar(repl) is True
```

- [ ] **Step 2: Run to verify the gate test fails**

Run: `cd protocol && uv run pytest tests/test_verify_meta_tier_gate.py -q`
Expected: FAIL — `test_planned_representation_revision_is_not_auto_licensed` fails because WITHOUT the gate the revision claim licenses (status LICENSED, not PENDING). The other two tests pass already.

- [ ] **Step 3: Add the gate to `verify_stage`**

In `protocol/src/polymer_protocol/verify.py`, add the two helpers to the existing grammar import block:

```python
from polymer_grammar import (
    Claim,
    LicenseRoute,
    Licensing,
    RivalSetClosure,
    SatisfactionVerdict,
    Status,
    is_representation_revision,
    meets_meta_tier_bar,
)
```

In the LICENSED branch, insert the gate between the `licensing = Licensing(...)` construction and the
`new_claims.append(_with_status(...))` call:

```python
            licensing = Licensing(
                route=LicenseRoute.SEVERE_TEST,
                satisfactions=(ev.satisfaction,),
                rival_set_closure=RivalSetClosure.OPEN_ACKNOWLEDGED,
            )
            if is_representation_revision(c) and not meets_meta_tier_bar(licensing):
                # meta-tier gate: a representation-revision is gated MORE conservatively — it cannot ride
                # the ordinary single-severe-test path. Hold PENDING until replication-grade licensing.
                new_claims.append(c)
                continue
            new_claims.append(
                _with_status(
                    c,
                    status=Status.LICENSED,
                    licensing=licensing,
                    pending_reason=None,
                    strength=oracle_cap(c, registry),
                )
            )
```

(The `continue` skips the elif/else for this claim — it has been handled. `c` is appended unchanged, so it
keeps its existing PENDING status + pending_reason.)

- [ ] **Step 4: Run to verify they pass**

Run: `cd protocol && uv run pytest tests/test_verify_meta_tier_gate.py -q`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add protocol/src/polymer_protocol/verify.py protocol/tests/test_verify_meta_tier_gate.py
git commit -m "feat(protocol): meta-tier gate — representation-revisions can't auto-license (#5c)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: Protocol — export + full-suite green

**Files:**
- Modify: `protocol/src/polymer_protocol/__init__.py`
- Test: `protocol/tests/test_red_team.py`

- [ ] **Step 1: Write the failing export test**

Append to `protocol/tests/test_red_team.py`:

```python
def test_red_team_symbol_is_exported_from_package():
    import polymer_protocol as pp

    assert hasattr(pp, "RepresentationRedTeamAdapter")
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd protocol && uv run pytest tests/test_red_team.py::test_red_team_symbol_is_exported_from_package -q`
Expected: FAIL — `AttributeError: module 'polymer_protocol' has no attribute 'RepresentationRedTeamAdapter'`.

- [ ] **Step 3: Add the import and `__all__` entry**

In `protocol/src/polymer_protocol/__init__.py`, add the import next to the other module imports (e.g. after the `from .generation_adapter import ...` line):

```python
from .red_team import RepresentationRedTeamAdapter
```

And add `"RepresentationRedTeamAdapter",` to the `__all__` list.

- [ ] **Step 4: Run the export test to verify it passes**

Run: `cd protocol && uv run pytest tests/test_red_team.py::test_red_team_symbol_is_exported_from_package -q`
Expected: PASS.

- [ ] **Step 5: Run the full protocol suite + ruff + isolation**

Run: `cd protocol && uv run pytest -q && uv run ruff check src tests`
Expected: all green (existing protocol tests + red-team + gate tests), ruff clean. `tests/test_isolation.py` still passes.

- [ ] **Step 6: Run the full grammar suite (confirm untouched + green)**

Run: `cd grammar && uv run pytest -q`
Expected: all green (this slice touches no grammar).

- [ ] **Step 7: Commit**

```bash
git add protocol/src/polymer_protocol/__init__.py protocol/tests/test_red_team.py
git commit -m "feat(protocol): export RepresentationRedTeamAdapter (#5c)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Progress Log

(Update after each task.)

- [ ] Task 1 — `red_team.py` adapter
- [ ] Task 2 — `verify_stage` meta-tier gate
- [ ] Task 3 — export + full-suite green

## Self-review notes

- **Spec coverage:** the reference adapter (proposes one valid revision per eligible claim, skips own/revision claims, deterministic) → Task 1; through-bus (provenance forced, forged-licensing dropped, admitted via generate_stage) → Task 1; belief-neutrality + convergence through `run_cycle` → Task 1; the gate (revision held PENDING, non-revision licenses, bar truth) → Task 2; export → Task 3. All spec test bullets map to a named test.
- **No new bus machinery:** the adapter is a `GenerationAdapter`; it rides the existing `bridge_proposer`/`compile_untrusted` (no `run_cycle` change). The gate is internal to `verify_stage`.
- **Fences honored:** reference ships no intelligence (placeholder DEPRECATE); no replication-licensing path (revisions stay PENDING); no `run_cycle` signature change; grammar untouched.
- **Type consistency:** `RepresentationRedTeamAdapter.identity == "representation-red-team"`, `propose(corpus, frontier) -> tuple[Proposal, ...]`; gate uses `is_representation_revision(c)` + `meets_meta_tier_bar(licensing)` — identical across plan, spec, tests.
- **Gate edit precision:** inserted between the `licensing = Licensing(...)` build and the `_with_status` append in verify.py's LICENSED branch; `continue` exits the per-claim if/elif/else after appending `c` unchanged (PENDING preserved).
- **Export-timing:** Task 1/2 tests import from module paths (`polymer_protocol.red_team`); the package export lands in Task 3 — mirrors prior slices.
