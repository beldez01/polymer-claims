# GENERATE #4a Proposer Bus Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the flywheel loop with a GENERATE stage — a pure proposer bus (+ `compile_to_IR` discard log + exogenous injection port + two pure operators: rival-generation and frontier-attack) wired into `run_cycle`, replacing the "claims enter by stuffing the Corpus" stub.

**Architecture:** All new code is protocol-side (`polymer_protocol`), zero grammar changes. Generated origin rides on the existing `provenance` (`generated_by`/`method`/`agent_id`); the discard log is ephemeral on `CycleResult`. Proposers are passed into `run_cycle` like `adapters`/`cost_model` — the bus is the seam where embedding/LLM proposers plug in later. Determinism via content-addressed claim ids; convergence via id de-dup + operators skipping their own outputs. Generated claims are CONJECTURED/no-plan, so they are inert this cycle and first act next cycle.

**Tech Stack:** Python 3.14, Pydantic v2 (frozen `_Model`), `uv`, `pytest`. Stdlib only. One-way dependency `polymer_protocol` → `polymer_grammar`.

**Spec:** `docs/superpowers/specs/2026-06-03-generate-proposer-bus-design.md`

---

## Conventions for every task

- Work in `protocol/`. Tests: `cd /Users/zbb2/Desktop/polymer-claims/protocol && uv run pytest -q`. Single: `uv run pytest tests/<file>::<test> -v`.
- New models subclass `_Model` from `polymer_protocol.base` (frozen, `extra="forbid"`, tuples not lists).
- Keep `ruff` clean: `uv run ruff check src tests`.
- Commit after each task with the message shown. Commits are LOCAL only — do not push.
- v1 named constants (spec §8): `GEN_ID_PREFIX = "gen"`, id-hash slice `16`. Operator ids `"rival-generation"` / `"frontier-attack"`. Define as module-level constants, never bare literals.

---

## File Structure

| File | New/Modify | Responsibility |
|---|---|---|
| `src/polymer_protocol/corpus.py` | modify | `Proposal`, `DiscardEntry`, `GenerationRecord`; `generation` on `CycleResult` |
| `src/polymer_protocol/generate.py` | new | `Proposer` type alias, `_corpus_fingerprint`, `_gen_id`, `_ensure_provenance`, `compile_to_IR`, `generate_stage` |
| `src/polymer_protocol/proposers.py` | new | `rival_generation`, `frontier_attack` |
| `src/polymer_protocol/cycle.py` | modify | insert `generate_stage` after `represent`; thread `proposers`/`injected`/`generation_cap`; return `GenerationRecord` |
| `src/polymer_protocol/__init__.py` | modify | export the new public symbols |
| `tests/test_corpus.py` | modify | record-type tests |
| `tests/test_generate.py` | new | bus + compile_to_IR tests |
| `tests/test_proposers.py` | new | operator tests |
| `tests/test_cycle.py` | modify | integration tests |

---

### Task 1: `corpus.py` — proposal + generation record types

**Files:**
- Modify: `src/polymer_protocol/corpus.py`
- Test: `tests/test_corpus.py`

These types live in `corpus.py` (not `generate.py`) to keep imports acyclic — `generate.py` imports `Corpus`, and `CycleResult` needs `GenerationRecord`. Same pattern as `SelectionRecord`/`ExecRecord`. `corpus.py` already imports `Claim` and `DefeatEdge` from `polymer_grammar` and `Field` from pydantic.

- [ ] **Step 1: Write the failing tests** — append to `tests/test_corpus.py`:

```python
from polymer_protocol.corpus import DiscardEntry, GenerationRecord, Proposal
from tests.conftest import make_claim


def test_proposal_holds_claim_and_edges():
    from polymer_grammar import DefeatEdge, DefeatEdgeKind
    c = make_claim("x")
    e = DefeatEdge(source="x", target="y", kind=DefeatEdgeKind.REBUT)
    p = Proposal(operator_id="op", claim=c, edges=(e,))
    assert p.operator_id == "op"
    assert p.claim.id == "x"
    assert p.edges[0].target == "y"


def test_proposal_defaults_no_edges():
    p = Proposal(operator_id="op", claim=make_claim("x"))
    assert p.edges == ()


def test_generation_record_defaults_empty():
    r = GenerationRecord()
    assert r.proposed == 0
    assert r.admitted == ()
    assert r.discarded == ()


def test_cycle_result_defaults_empty_generation():
    from polymer_grammar import FDRLedger
    from polymer_protocol.corpus import Corpus, CycleResult
    res = CycleResult(corpus=Corpus(fdr_ledger=FDRLedger(target_fdr=0.05)))
    assert res.generation == GenerationRecord()
```

- [ ] **Step 2: Run to verify they fail**

Run: `cd /Users/zbb2/Desktop/polymer-claims/protocol && uv run pytest tests/test_corpus.py::test_generation_record_defaults_empty -v`
Expected: FAIL — `ImportError: cannot import name 'GenerationRecord'`

- [ ] **Step 3: Implement** — in `corpus.py`, add these classes after `SelectionRecord` (and before `CycleResult`):

```python
class Proposal(_Model):
    """A candidate from a proposer: a generated claim + any defeat edges it implies."""

    operator_id: str
    claim: Claim
    edges: tuple[DefeatEdge, ...] = ()


class DiscardEntry(_Model):
    operator_id: str
    claim_id: str
    reason: str


class GenerationRecord(_Model):
    proposed: int = Field(default=0, ge=0)
    admitted: tuple[str, ...] = ()
    discarded: tuple[DiscardEntry, ...] = ()
```

Then add a field to the existing `CycleResult` (keep its current fields; add at the end of its field list):

```python
    generation: GenerationRecord = GenerationRecord()
```

- [ ] **Step 4: Run to verify they pass**

Run: `uv run pytest tests/test_corpus.py -v`
Expected: PASS (existing + 4 new)

- [ ] **Step 5: Commit**

```bash
cd /Users/zbb2/Desktop/polymer-claims
git add protocol/src/polymer_protocol/corpus.py protocol/tests/test_corpus.py
git commit -m "feat(protocol): Proposal + GenerationRecord on CycleResult

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: `generate.py` — the bus + compile_to_IR

**Files:**
- Create: `src/polymer_protocol/generate.py`
- Test: `tests/test_generate.py`

`generate_stage` runs proposers (caller order) + exogenous injections through `compile_to_IR`, folds survivors in, returns `(Corpus, GenerationRecord)`. Tested here with inline lambda proposers (the real operators come in Tasks 3–4).

- [ ] **Step 1: Write the failing tests** — create `tests/test_generate.py`:

```python
from polymer_grammar import DefeatEdge, DefeatEdgeKind, FDRLedger, Status

from polymer_protocol.corpus import Corpus, Proposal
from polymer_protocol.generate import generate_stage
from tests.conftest import make_claim, make_plan


def _corpus(claims, edges=()):
    return Corpus(claims=tuple(claims), defeat_edges=tuple(edges),
                  fdr_ledger=FDRLedger(target_fdr=0.05))


def test_no_proposers_is_noop():
    corp = _corpus([make_claim("a")])
    out, rec = generate_stage(corp, frontier=())
    assert out is corp           # identity preserved when nothing admitted
    assert rec.proposed == 0
    assert rec.admitted == ()


def test_bus_admits_a_valid_proposal():
    corp = _corpus([make_claim("a")])
    prop = lambda corpus, frontier: (Proposal(operator_id="op", claim=make_claim("b")),)
    out, rec = generate_stage(corp, frontier=(), proposers=(prop,))
    assert set(out.by_id()) == {"a", "b"}
    assert rec.admitted == ("b",)
    assert rec.proposed == 1


def test_duplicate_id_is_discarded():
    corp = _corpus([make_claim("a")])
    prop = lambda corpus, frontier: (Proposal(operator_id="op", claim=make_claim("a")),)
    out, rec = generate_stage(corp, frontier=(), proposers=(prop,))
    assert out is corp
    assert rec.admitted == ()
    assert rec.discarded[0].reason == "duplicate"


def test_unresolved_edge_is_discarded():
    corp = _corpus([make_claim("a")])
    # proposal "b" carries an edge to a non-existent target "ghost"
    edge = DefeatEdge(source="b", target="ghost", kind=DefeatEdgeKind.REBUT)
    prop = lambda corpus, frontier: (Proposal(operator_id="op", claim=make_claim("b"), edges=(edge,)),)
    out, rec = generate_stage(corp, frontier=(), proposers=(prop,))
    assert out is corp
    assert rec.discarded[0].reason == "unresolved-edge"


def test_admitted_edge_is_added():
    corp = _corpus([make_claim("a")])
    edge = DefeatEdge(source="b", target="a", kind=DefeatEdgeKind.REBUT)
    prop = lambda corpus, frontier: (Proposal(operator_id="op", claim=make_claim("b"), edges=(edge,)),)
    out, rec = generate_stage(corp, frontier=(), proposers=(prop,))
    assert "b" in out.by_id()
    assert any(e.source == "b" and e.target == "a" for e in out.defeat_edges)


def test_injected_claim_gets_provenance_and_admitted():
    corp = _corpus([make_claim("a")])
    injected = make_claim("inj", status=Status.PENDING, plan=make_plan(0.01, 0.05))  # provenance None
    out, rec = generate_stage(corp, frontier=(), injected=(injected,))
    assert "inj" in out.by_id()
    assert out.by_id()["inj"].provenance is not None  # IMPORTED stamped


def test_generation_cap_truncates():
    corp = _corpus([make_claim("a")])
    prop = lambda corpus, frontier: (
        Proposal(operator_id="op", claim=make_claim("b")),
        Proposal(operator_id="op", claim=make_claim("c")),
    )
    out, rec = generate_stage(corp, frontier=(), proposers=(prop,), cap=1)
    assert len(rec.admitted) == 1
    assert any(d.reason == "cap" for d in rec.discarded)
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest tests/test_generate.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'polymer_protocol.generate'`

- [ ] **Step 3: Implement** — create `src/polymer_protocol/generate.py`:

```python
"""GENERATE: the proposer bus — the open generation port that closes the flywheel.

Runs passed-in proposers (caller order) + exogenous injections through compile_to_IR and
folds survivors into the corpus. Pure Corpus -> (Corpus, GenerationRecord). Proposers are
the seam where external/LLM proposers plug in later (like the Adapter Protocol). Generated
claims are CONJECTURED/no-plan -> inert this cycle, first act next cycle. Spec §3.
"""
from __future__ import annotations

from collections.abc import Callable

from polymer_grammar import Claim, GenerationMode, Provenance

from .base import stable_sha
from .corpus import Corpus, DiscardEntry, GenerationRecord, Proposal

GEN_ID_PREFIX = "gen"
_ID_HASH_LEN = 16

# A proposer: (corpus, frontier-claim-ids) -> proposals.
Proposer = Callable[[Corpus, tuple[str, ...]], tuple[Proposal, ...]]


def _corpus_fingerprint(corpus: Corpus) -> str:
    """Deterministic fingerprint of the corpus's claim-id set (origin trace)."""
    return stable_sha(sorted(c.id for c in corpus.claims))[:_ID_HASH_LEN]


def _gen_id(operator_short: str, *parts: str) -> str:
    """Content-addressed id for a generated claim — deterministic, collision-resistant."""
    return f"{GEN_ID_PREFIX}-{operator_short}-{stable_sha(list(parts))[:_ID_HASH_LEN]}"


def _ensure_provenance(claim: Claim) -> Claim:
    """Stamp a minimal IMPORTED provenance on an injected claim that lacks one."""
    if claim.provenance is not None:
        return claim
    prov = Provenance(generated_by=GenerationMode.IMPORTED, search_cardinality=1)
    return claim.model_copy(update={"provenance": prov})


def compile_to_IR(proposal: Proposal, present_ids: set[str]) -> str | None:
    """Pressure-sensor: return a discard reason, or None if the proposal is admissible.

    `present_ids` is the live id set (existing + already-admitted this pass)."""
    if proposal.claim.id in present_ids:
        return "duplicate"
    for e in proposal.edges:
        # an edge resolves iff its target is an existing claim or the claim being added
        if e.target not in present_ids and e.target != proposal.claim.id:
            return "unresolved-edge"
    return None


def generate_stage(
    corpus: Corpus,
    frontier: tuple[str, ...],
    *,
    proposers: tuple[Proposer, ...] = (),
    injected: tuple[Claim, ...] = (),
    cap: int | None = None,
) -> tuple[Corpus, GenerationRecord]:
    proposals: list[Proposal] = []
    for prop in proposers:
        proposals.extend(prop(corpus, frontier))
    for claim in injected:
        proposals.append(Proposal(operator_id="exogenous", claim=_ensure_provenance(claim)))

    present_ids = set(corpus.by_id())
    new_claims = list(corpus.claims)
    new_edges = list(corpus.defeat_edges)
    admitted: list[str] = []
    discarded: list[DiscardEntry] = []

    for p in proposals:
        if cap is not None and len(admitted) >= cap:
            discarded.append(DiscardEntry(operator_id=p.operator_id, claim_id=p.claim.id, reason="cap"))
            continue
        reason = compile_to_IR(p, present_ids)
        if reason is not None:
            discarded.append(DiscardEntry(operator_id=p.operator_id, claim_id=p.claim.id, reason=reason))
            continue
        new_claims.append(p.claim)
        new_edges.extend(p.edges)
        present_ids.add(p.claim.id)
        admitted.append(p.claim.id)

    record = GenerationRecord(
        proposed=len(proposals),
        admitted=tuple(sorted(admitted)),
        discarded=tuple(sorted(discarded, key=lambda d: (d.claim_id, d.reason))),
    )
    if not admitted:
        return corpus, record  # identity preserved when nothing folded in
    new_corpus = corpus.model_copy(
        update={"claims": tuple(new_claims), "defeat_edges": tuple(new_edges)}
    )
    return new_corpus, record
```

- [ ] **Step 4: Run to verify they pass**

Run: `uv run pytest tests/test_generate.py -v`
Expected: PASS (7 tests). Also `uv run ruff check src tests`.

- [ ] **Step 5: Commit**

```bash
cd /Users/zbb2/Desktop/polymer-claims
git add protocol/src/polymer_protocol/generate.py protocol/tests/test_generate.py
git commit -m "feat(protocol): generate_stage proposer bus + compile_to_IR

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: `proposers.py` — rival_generation

**Files:**
- Create: `src/polymer_protocol/proposers.py`
- Test: `tests/test_proposers.py`

For each claim with a conclusion, emit a CONJECTURED rival for each OTHER `Direction` value, marked `incompatible_with` the source conclusion. Skips claims without a conclusion and its own prior outputs (the convergence guard).

- [ ] **Step 1: Write the failing tests** — create `tests/test_proposers.py`:

```python
from polymer_grammar import (
    Direction, FDRLedger, NeighborEdgeKind, Proposition, Status,
)

from polymer_protocol.corpus import Corpus
from polymer_protocol.proposers import rival_generation
from tests.conftest import make_claim


def _corpus(claims):
    return Corpus(claims=tuple(claims), fdr_ledger=FDRLedger(target_fdr=0.05))


def _concl(direction):
    return Proposition(direction=direction, estimand="beta", descriptor="X on Y")


def test_rival_emits_other_two_directions():
    c = make_claim("c", conclusion=_concl(Direction.POSITIVE))
    props = rival_generation(_corpus([c]), ())
    dirs = {p.claim.conclusion.direction for p in props}
    assert dirs == {Direction.NEGATIVE, Direction.NULL}
    assert all(p.claim.status == Status.CONJECTURED for p in props)


def test_rival_marks_incompatible_with_source():
    c = make_claim("c", conclusion=_concl(Direction.POSITIVE))
    props = rival_generation(_corpus([c]), ())
    for p in props:
        ne = p.claim.conclusion.neighborhood
        assert len(ne) == 1
        assert ne[0].kind == NeighborEdgeKind.INCOMPATIBLE_WITH
        assert ne[0].target == c.conclusion.content_hash


def test_rival_skips_claims_without_conclusion():
    c = make_claim("c")  # no conclusion
    assert rival_generation(_corpus([c]), ()) == ()


def test_rival_skips_its_own_output():
    # a claim already produced by rival-generation must not breed rivals-of-rivals
    c = make_claim("c", conclusion=_concl(Direction.POSITIVE))
    props = rival_generation(_corpus([c]), ())
    rival = props[0].claim
    # feed the rival back in alongside the original
    props2 = rival_generation(_corpus([c, rival]), ())
    # only the ORIGINAL c spawns rivals; the rival is skipped
    sources = {p.claim.id for p in props2}
    assert all(not s.startswith("gen-rival") or s in {p.claim.id for p in props} for s in sources)
    # exactly the same 2 rivals as before (the rival itself spawned none)
    assert {p.claim.id for p in props2} == {p.claim.id for p in props}


def test_rival_ids_are_deterministic():
    c = make_claim("c", conclusion=_concl(Direction.POSITIVE))
    a = {p.claim.id for p in rival_generation(_corpus([c]), ())}
    b = {p.claim.id for p in rival_generation(_corpus([c]), ())}
    assert a == b
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest tests/test_proposers.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'polymer_protocol.proposers'`

- [ ] **Step 3: Implement** — create `src/polymer_protocol/proposers.py`:

```python
"""Pure endogenous proposers for the GENERATE bus (spec §3.2).

rival_generation enriches the rival pool L2 rival_set_closure needs; frontier_attack plants
inert candidate defenses at unresolved-frontier nodes (the keystone closure, made mechanical).
Both deterministic, both skip their own prior outputs so the corpus converges. Spec §3.2/§3.6.
"""
from __future__ import annotations

from polymer_grammar import (
    CategoricalLeaf,
    Claim,
    DefeatEdge,
    DefeatEdgeKind,
    Direction,
    GenerationMode,
    NeighborEdge,
    NeighborEdgeKind,
    Provenance,
    Status,
)

from .corpus import Corpus, Proposal
from .generate import _corpus_fingerprint, _gen_id

RIVAL_OP = "rival-generation"
FRONTIER_OP = "frontier-attack"


def _generated_by(corpus: Corpus, operator_id: str) -> Provenance:
    return Provenance(
        generated_by=GenerationMode.AGENT_GENERATED,
        agent_id=operator_id,
        method=f"{operator_id}@{_corpus_fingerprint(corpus)}",
        search_cardinality=1,
    )


def _is_own_output(claim: Claim, operator_id: str) -> bool:
    return (
        claim.provenance is not None
        and claim.provenance.method is not None
        and claim.provenance.method.startswith(operator_id)
    )


def rival_generation(corpus: Corpus, frontier: tuple[str, ...]) -> tuple[Proposal, ...]:
    proposals: list[Proposal] = []
    for c in corpus.claims:
        if c.conclusion is None or _is_own_output(c, RIVAL_OP):
            continue
        for d in Direction:
            if d == c.conclusion.direction:
                continue
            ne = NeighborEdge(
                kind=NeighborEdgeKind.INCOMPATIBLE_WITH, target=c.conclusion.content_hash
            )
            rival_concl = c.conclusion.model_copy(update={"direction": d, "neighborhood": (ne,)})
            rival = Claim(
                id=_gen_id("rival", c.id, d.value),
                title=f"rival({d.value}) of {c.id}",
                pattern=c.pattern,
                leaves=c.leaves,
                status=Status.CONJECTURED,
                subject=c.subject,
                conclusion=rival_concl,
                provenance=_generated_by(corpus, RIVAL_OP),
            )
            proposals.append(Proposal(operator_id=RIVAL_OP, claim=rival))
    return tuple(proposals)
```

- [ ] **Step 4: Run to verify they pass**

Run: `uv run pytest tests/test_proposers.py -v`
Expected: PASS (5 tests). Also `uv run ruff check src tests`.

- [ ] **Step 5: Commit**

```bash
cd /Users/zbb2/Desktop/polymer-claims
git add protocol/src/polymer_protocol/proposers.py protocol/tests/test_proposers.py
git commit -m "feat(protocol): rival_generation proposer

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: `proposers.py` — frontier_attack

**Files:**
- Modify: `src/polymer_protocol/proposers.py`
- Test: `tests/test_proposers.py`

For each frontier node, find its claim-sourced attackers and emit an inert CONJECTURED defense claim + a `D --rebut--> B` edge. Skips synthetic (`:`-source) attackers.

- [ ] **Step 1: Write the failing tests** — append to `tests/test_proposers.py`:

```python
from polymer_grammar import DefeatEdge, DefeatEdgeKind
from polymer_protocol.proposers import frontier_attack


def _corpus_e(claims, edges):
    from polymer_grammar import FDRLedger
    return Corpus(claims=tuple(claims), defeat_edges=tuple(edges),
                  fdr_ledger=FDRLedger(target_fdr=0.05))


def test_frontier_attack_emits_defense_and_edge():
    # b attacks a; a is on the frontier -> emit D that rebuts b
    a, b = make_claim("a"), make_claim("b")
    edges = (DefeatEdge(source="b", target="a", kind=DefeatEdgeKind.REBUT),)
    props = frontier_attack(_corpus_e([a, b], edges), frontier=("a",))
    assert len(props) == 1
    p = props[0]
    assert p.claim.status == Status.CONJECTURED
    assert p.claim.strength is None  # inert: cannot defeat b until licensed
    assert len(p.edges) == 1
    assert p.edges[0].source == p.claim.id and p.edges[0].target == "b"
    assert p.edges[0].kind == DefeatEdgeKind.REBUT


def test_frontier_attack_skips_synthetic_sources():
    # an undermine edge from a failed satisfaction has a synthetic ":" source
    a = make_claim("a")
    edges = (DefeatEdge(source="refutation:x", target="a", kind=DefeatEdgeKind.UNDERMINE),)
    props = frontier_attack(_corpus_e([a], edges), frontier=("a",))
    assert props == ()


def test_frontier_attack_deterministic_ids():
    a, b = make_claim("a"), make_claim("b")
    edges = (DefeatEdge(source="b", target="a", kind=DefeatEdgeKind.REBUT),)
    corp = _corpus_e([a, b], edges)
    id1 = frontier_attack(corp, ("a",))[0].claim.id
    id2 = frontier_attack(corp, ("a",))[0].claim.id
    assert id1 == id2
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest tests/test_proposers.py::test_frontier_attack_emits_defense_and_edge -v`
Expected: FAIL — `ImportError: cannot import name 'frontier_attack'`

- [ ] **Step 3: Implement** — append to `src/polymer_protocol/proposers.py`:

```python
def frontier_attack(corpus: Corpus, frontier: tuple[str, ...]) -> tuple[Proposal, ...]:
    by_id = corpus.by_id()
    attackers_of: dict[str, list[str]] = {}
    for e in corpus.defeat_edges:
        if ":" in e.source:
            continue  # skip synthetic sources (e.g. refutation:<id>) — not claim-rebuttable
        attackers_of.setdefault(e.target, []).append(e.source)
    proposals: list[Proposal] = []
    for f in frontier:
        for b in attackers_of.get(f, []):
            if b not in by_id:
                continue
            did = _gen_id("fa", f, b)
            d_claim = Claim(
                id=did,
                title=f"challenge to {b}",
                pattern=by_id[b].pattern,
                leaves=(CategoricalLeaf(ontology_term=f"frontier-attack-{b}"),),
                status=Status.CONJECTURED,
                provenance=_generated_by(corpus, FRONTIER_OP),
            )
            edge = DefeatEdge(source=did, target=b, kind=DefeatEdgeKind.REBUT)
            proposals.append(Proposal(operator_id=FRONTIER_OP, claim=d_claim, edges=(edge,)))
    return tuple(proposals)
```

- [ ] **Step 4: Run to verify they pass**

Run: `uv run pytest tests/test_proposers.py -v`
Expected: PASS (8 tests total). Also `uv run ruff check src tests`.

- [ ] **Step 5: Commit**

```bash
cd /Users/zbb2/Desktop/polymer-claims
git add protocol/src/polymer_protocol/proposers.py protocol/tests/test_proposers.py
git commit -m "feat(protocol): frontier_attack proposer

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 5: `cycle.py` — wire GENERATE into run_cycle

**Files:**
- Modify: `src/polymer_protocol/cycle.py`
- Test: `tests/test_cycle.py`

Insert `generate_stage` right after `represent` (using `scaffolding.frontier`); thread `proposers`/`injected`/`generation_cap`; return the `GenerationRecord`. Generated claims are CONJECTURED/strengthless, so they don't invalidate the represent scaffolding (the added edges are inert under `effective_defeats`; the added claims aren't executed).

- [ ] **Step 1: Write the failing tests** — append to `tests/test_cycle.py`:

```python
from polymer_protocol.proposers import frontier_attack, rival_generation


def test_audit_includes_generate_stage(empty_ledger, ctx, adapters):
    c = make_claim("a", status=Status.PENDING, plan=make_plan(0.01, 0.05))
    result = run_cycle(Corpus(claims=(c,), fdr_ledger=empty_ledger), adapters, ctx)
    assert "generate_stage" in {a.stage for a in result.audit}


def test_injected_claim_flows_through_and_licenses(empty_ledger, ctx, adapters):
    # an exogenous PENDING-with-plan claim enters via the port and licenses this cycle
    injected = make_claim("inj", status=Status.PENDING, plan=make_plan(0.01, 0.05))
    result = run_cycle(Corpus(fdr_ledger=empty_ledger), adapters, ctx, injected=(injected,))
    assert result.corpus.by_id()["inj"].status == Status.LICENSED
    assert result.generation.proposed == 1
    assert result.generation.admitted == ("inj",)


def test_frontier_attack_plants_a_defense(empty_ledger, ctx, adapters):
    from polymer_grammar import DefeatEdge, DefeatEdgeKind
    # b (CONJECTURED, no plan) attacks a -> a on frontier -> frontier_attack plants D rebut b
    a, b = make_claim("a"), make_claim("b")
    edge = DefeatEdge(source="b", target="a", kind=DefeatEdgeKind.REBUT)
    corpus = Corpus(claims=(a, b), defeat_edges=(edge,), fdr_ledger=empty_ledger)
    result = run_cycle(corpus, adapters, ctx, proposers=(frontier_attack,))
    # a new gen-fa-* claim and an edge into b appear
    assert any(cid.startswith("gen-fa-") for cid in result.corpus.by_id())
    assert any(e.target == "b" for e in result.corpus.defeat_edges)


def test_generation_converges(empty_ledger, ctx, adapters):
    from polymer_grammar import Direction, Proposition
    c = make_claim("c", conclusion=Proposition(direction=Direction.POSITIVE, estimand="b", descriptor="d"))
    corpus = Corpus(claims=(c,), fdr_ledger=empty_ledger)
    c1 = run_cycle(corpus, adapters, ctx, proposers=(rival_generation,))
    n1 = len(c1.corpus.claims)
    c2 = run_cycle(c1.corpus, adapters, ctx, proposers=(rival_generation,))
    assert len(c2.corpus.claims) == n1  # second cycle adds nothing — convergent
    assert c2.generation.admitted == ()


def test_default_generation_is_noop(empty_ledger, ctx, adapters):
    c = make_claim("a", status=Status.PENDING, plan=make_plan(0.01, 0.05))
    result = run_cycle(Corpus(claims=(c,), fdr_ledger=empty_ledger), adapters, ctx)
    assert result.generation.proposed == 0
    assert result.corpus.by_id()["a"].status == Status.LICENSED  # #3a path unaffected
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest tests/test_cycle.py::test_audit_includes_generate_stage -v`
Expected: FAIL — `generate_stage` not in audit / `run_cycle` lacks `proposers` kwarg.

- [ ] **Step 3: Implement** — modify `cycle.py`:

Add the import (with the other `from .` imports):

```python
from .generate import Proposer, generate_stage
```

Update the signature (add the three keyword-only params after the #3a block):

```python
def run_cycle(
    corpus: Corpus,
    adapters: tuple[Adapter, ...],
    ctx: MaterializationContext,
    oracles: OracleRegistry | None = None,
    *,
    cost_model: CostModel | None = None,
    budget: float | None = None,
    value_weights: ValueWeights = ValueWeights(),
    cost_weights: CostWeights = CostWeights(),
    proposers: tuple[Proposer, ...] = (),
    injected: tuple[Claim, ...] = (),
    generation_cap: int | None = None,
) -> CycleResult:
```

Add `Claim` to the grammar import at the top (it currently imports `Adapter, MaterializationContext, Status`):

```python
from polymer_grammar import Adapter, Claim, MaterializationContext, Status
```

Insert the GENERATE stage immediately AFTER the `represent` audit append (before `canonicalize`):

```python
    corpus, generation = generate_stage(
        corpus, scaffolding.frontier,
        proposers=proposers, injected=injected, cap=generation_cap,
    )
    audit.append(StageAudit(stage="generate_stage",
        note=f"{len(generation.admitted)} admitted, {len(generation.discarded)} discarded",
        count=len(generation.admitted)))
```

Update the scaffolding-validity comment (currently above `verify_stage`) to account for GENERATE:

```python
    # scaffolding stays valid: canonicalize/safety/commit/execute change neither defeat_edges
    # nor claim ids, and generate only ADDS CONJECTURED claims + strengthless (inert) edges,
    # so the grounded_extension of the executed claims is unchanged since represent().
```

Add `generation=generation` to the returned `CycleResult(...)`:

```python
    return CycleResult(
        corpus=corpus,
        frontier=frontier,
        gated_lane=gated_lane,
        audit=tuple(audit),
        selection=selection,
        generation=generation,
    )
```

Also refresh the stale module docstring (lines ~4-8) — replace the sentence "GENERATE remains out of this sub-project — claims still enter exogenously." with:

```
GENERATE (the proposer bus) is now wired in right after REPRESENT: it runs passed-in
proposers + the exogenous injection port through compile_to_IR and folds new CONJECTURED
claims into the corpus (inert this cycle, first act next cycle). Spec §6.8 + SELECT #3a + GENERATE #4a.
```

- [ ] **Step 4: Run to verify they pass**

Run: `uv run pytest tests/test_cycle.py -v`
Expected: new tests pass AND all existing cycle tests pass. Then FULL suite `uv run pytest -q` — everything green (default empty generation is a no-op). `uv run ruff check src tests` clean.

- [ ] **Step 5: Commit**

```bash
cd /Users/zbb2/Desktop/polymer-claims
git add protocol/src/polymer_protocol/cycle.py protocol/tests/test_cycle.py
git commit -m "feat(protocol): wire generate_stage into run_cycle

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 6: `__init__.py` — exports + full-suite green

**Files:**
- Modify: `src/polymer_protocol/__init__.py`
- Test: whole suite

- [ ] **Step 1: Write the failing test** — append to `tests/test_generate.py`:

```python
def test_public_exports():
    import polymer_protocol as p
    for name in ["generate_stage", "compile_to_IR", "Proposal", "GenerationRecord",
                 "DiscardEntry", "rival_generation", "frontier_attack"]:
        assert hasattr(p, name), name
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/test_generate.py::test_public_exports -v`
Expected: FAIL — `assert hasattr(p, 'generate_stage')` is False.

- [ ] **Step 3: Add the exports** — in `src/polymer_protocol/__init__.py`:

Add imports (with the other `from .` imports; MERGE the corpus names into the existing `from .corpus import (...)` tuple):

```python
from .generate import compile_to_IR, generate_stage
from .proposers import frontier_attack, rival_generation
```

The existing `from .corpus import (...)` must additionally include `DiscardEntry, GenerationRecord, Proposal` (merge into that one import, keep tidy).

Append to `__all__`:

```python
    "generate_stage",
    "compile_to_IR",
    "Proposal",
    "GenerationRecord",
    "DiscardEntry",
    "rival_generation",
    "frontier_attack",
```

- [ ] **Step 4: Run the FULL gate**

```bash
cd /Users/zbb2/Desktop/polymer-claims/protocol
uv run pytest -q
uv run ruff check src tests
uv run pytest tests/test_isolation.py -q
```
Expected: ALL tests pass; ruff clean; isolation guard (3 tests) passes — no new grammar import of protocol. If `test_public_exports` fails you missed a name; if isolation fails you introduced a bad import — STOP and report.

- [ ] **Step 5: Commit**

```bash
cd /Users/zbb2/Desktop/polymer-claims
git add protocol/src/polymer_protocol/__init__.py protocol/tests/test_generate.py
git commit -m "feat(protocol): export GENERATE #4a public surface

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 7: README + CONTINUE docs

**Files:**
- Modify: `README.md`
- Modify: `docs/superpowers/CONTINUE.md`

- [ ] **Step 1: Get the protocol test count**

Run: `cd /Users/zbb2/Desktop/polymer-claims/protocol && uv run pytest -q 2>&1 | tail -1` — note the "N passed" number; call it `<N>`.

- [ ] **Step 2: Update `README.md`**

In the "Protocol runtime" section, update the protocol table row to:

```markdown
| `protocol/` | `polymer_protocol` | ✅ Sub-projects #1 + #2 + #3a + #4a (assessment spine + oracle dossier + SELECT + GENERATE proposer bus) — <N> tests |
```

Add this paragraph after the SELECT paragraph:

> `run_cycle` no longer requires claims to be pre-loaded. The **GENERATE** stage (right after
> REPRESENT) runs a bus of passed-in proposers plus an exogenous injection port
> (`run_cycle(..., proposers=, injected=)`) through `compile_to_IR`, folding new CONJECTURED
> claims into the corpus — inert this cycle, first acting next. Two pure operators ship:
> *rival-generation* (the direction-flipped rivals `rival_set_closure` needs) and *frontier-attack*
> (an inert candidate defense at each unresolved-frontier node — the keystone closure made
> mechanical). Content-addressed ids + a skip-own-output guard keep the corpus convergent, not
> growing. Embedding/LLM operators plug in behind the bus seam; the representation-revision lane is
> deferred (it needs the grammar's `representation_revision` meta-tier).

- [ ] **Step 3: Update `docs/superpowers/CONTINUE.md`**

Mark #4a DONE on branch `feat/generate-proposer-bus-4a` (merge SHA `<merge-sha pending>`). Repoint the IMMEDIATE NEXT ACTION toward the open next: **#3b SELECT** (QD/heterodox/Goodhart/cross-cycle belief), **#4b GENERATE** (embedding/LLM operators + credit ledger), **#5 daemons**, or the **grammar `representation_revision` meta-tier** (which unblocks operator-5's representation-revision lane). List the load-bearing #4a decisions: (1) pure proposer-bus core, intelligent operators behind the seam; (2) two pure operators — rival-generation + frontier-attack; (3) exogenous port = real validated entry path; (4) `compile_to_IR` + discard log produced now, mined later; (5) content-addressed ids + skip-own-output convergence guard; (6) zero grammar changes. Keep the existing CONTINUE format.

- [ ] **Step 4: Commit**

```bash
cd /Users/zbb2/Desktop/polymer-claims
git add README.md docs/superpowers/CONTINUE.md
git commit -m "docs: record GENERATE #4a in README + CONTINUE primer

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Final review

After Task 7, dispatch the whole-package Opus review (per subagent-driven-development), then `superpowers:finishing-a-development-branch` (merge no-ff to main, verify the full suite on the merged result, delete the branch). Update the memory file `project_polymer_claims_knowledge_protocol.md` + `MEMORY.md` with the #4a merge SHA and the load-bearing decisions.

## Progress Log

- (fill in per task: commit SHA + any decisions/deviations)
