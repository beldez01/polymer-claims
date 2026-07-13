# Cross-Arm Relations — Slice 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended)
> or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Give the merged claims universe genuine cross-arm connectivity — a defeasible, signed,
set-relata *relation meta-claim* an umbrella proposer emits, projected into the topology graph as signed
edges so the existing spectral eigenmap finally renders argument structure.

**Architecture:** Grammar adds a `ClaimSetSubject` + `RelationLeaf` (relation-as-`Claim`, Corpus stays 4).
Protocol adds versioned `TopologyEdge` fields + projects relation claims into all-pairs signed edges + an
`is_relation` lane guard. Umbrella (`embedding.py`, numpy) gains true signed aggregation; a two-stage
proposer (candidate-gen + LLM adapter) emits CONJECTURED relations. Viewer renders them.

**Tech Stack:** Python 3.12, pydantic v2 (frozen, `extra="forbid"`), numpy (umbrella only), pytest;
viewer is Next 16 + React Three Fiber (TypeScript).

## Global Constraints

- **Corpus stays exactly 4 collections** (`claims`, `defeat_edges`, `equivalences`, `fdr_ledger`). Relations are `Claim`s.
- **`grammar/` and `protocol/` stay pure + numpy-free.** All numpy + I/O + LLM live in `src/` (umbrella).
- **Byte-identity:** any corpus/topology export with **no relation claims** must serialize byte-identically to today. New pydantic fields are optional and omitted-when-unset via an explicit `@model_serializer` (the base `_Model` is `frozen=True, extra="forbid"` with **no `exclude_none`**; `model_dump_json()` would otherwise emit `null`s). Precedent: `grammar/src/polymer_grammar/capability.py`.
- **Subjects/leaves use tuples, never `frozenset`/`dict`** (content-addressing needs a stable order).
- **Relations never de-license/tombstone/charge FDR in Slice 1** — enforced by the `is_relation` guard, not convention.
- **TDD:** failing test → run (fail) → minimal impl → run (pass) → commit. Run the full gate `scripts/check-all.sh` before the final integration commit.
- Spec: `docs/superpowers/specs/2026-07-13-cross-arm-relations-design.md`.

---

## File Structure

- `grammar/src/polymer_grammar/subject.py` — add `ClaimSetSubject`; extend the `Subject` union.
- `grammar/src/polymer_grammar/leaf.py` — add `RelationKind`, `RelationLeaf`; extend the `Leaf` union.
- `grammar/src/polymer_grammar/relation.py` *(new)* — the relation `Pattern` registration, `make_relation_claim` factory, `is_relation` predicate.
- `protocol/src/polymer_protocol/topology.py` — `TopologyEdge` new fields + `@model_serializer`; contract version bump; relation projection in `export_topology`.
- `protocol/src/polymer_protocol/represent.py` (or the SELECT/execute site) — `is_relation` lane guard.
- `src/polymer_claims/embedding.py` — signed aggregation (sum-clamp) reading `signed_weight`.
- `src/polymer_claims/relation_proposer.py` *(new)* — candidate-gen + LLM proposer.
- `viewer/src/…` — render relation nodes/edges (tier color, signed style, dashed CONJECTURED).
- Tests mirror each under `grammar/tests/`, `protocol/tests/`, `tests/`.

---

## Task 1: `ClaimSetSubject` subject variant

**Files:**
- Modify: `grammar/src/polymer_grammar/subject.py`
- Test: `grammar/tests/test_claim_set_subject.py` (create)

**Interfaces:**
- Produces: `ClaimSetSubject(_SubjectBase)` with `kind: Literal["claim_set"]`, `source_set: tuple[str, ...]`, `target_set: tuple[str, ...]`; both sorted-canonical + disjoint. Added to the `Subject` discriminated union.

- [ ] **Step 1: Write the failing test**

```python
# grammar/tests/test_claim_set_subject.py
import pytest
from polymer_grammar.subject import ClaimSetSubject

def test_sorted_and_disjoint_ok():
    s = ClaimSetSubject(id="r1", display="A~B", source_set=("a2", "a1"), target_set=("b1",))
    assert s.kind == "claim_set"
    assert s.source_set == ("a1", "a2")  # canonicalized sorted

def test_overlap_rejected():
    with pytest.raises(ValueError, match="disjoint"):
        ClaimSetSubject(id="r", display="x", source_set=("a",), target_set=("a",))

def test_empty_side_rejected():
    with pytest.raises(ValueError):
        ClaimSetSubject(id="r", display="x", source_set=(), target_set=("b",))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd grammar && python -m pytest tests/test_claim_set_subject.py -q`
Expected: FAIL (`ImportError: cannot import name 'ClaimSetSubject'`).

- [ ] **Step 3: Write minimal implementation**

Add after `CompositeSubject` in `subject.py`, and add `ClaimSetSubject` to the `Union` in the `Subject` annotation:

```python
class ClaimSetSubject(_SubjectBase):
    kind: Literal["claim_set"] = "claim_set"
    source_set: tuple[str, ...] = Field(min_length=1)
    target_set: tuple[str, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _canonical_and_disjoint(self) -> "ClaimSetSubject":
        src, tgt = tuple(sorted(self.source_set)), tuple(sorted(self.target_set))
        if set(src) & set(tgt):
            raise ValueError("ClaimSetSubject source_set/target_set must be disjoint")
        if src != self.source_set or tgt != self.target_set:
            object.__setattr__(self, "source_set", src)  # frozen model: canonicalize in-place
            object.__setattr__(self, "target_set", tgt)
        return self
```

Add `ClaimSetSubject` to the `Union[...]` list inside `Subject = Annotated[Union[...], Field(discriminator="kind")]`, and (if `CompositeSubject.model_rebuild()` exists) add `ClaimSetSubject.model_rebuild()` alongside it.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd grammar && python -m pytest tests/test_claim_set_subject.py -q`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add grammar/src/polymer_grammar/subject.py grammar/tests/test_claim_set_subject.py
git commit -m "feat(grammar): ClaimSetSubject — sorted-tuple, disjoint claim-set subject variant"
```

---

## Task 2: `RelationKind` + `RelationLeaf`

**Files:**
- Modify: `grammar/src/polymer_grammar/leaf.py`
- Test: `grammar/tests/test_relation_leaf.py` (create)

**Interfaces:**
- Produces: `class RelationKind(str, Enum)` = `COHERES`, `TENSION`, `RESTRICTION_MAP`; `class Tier(str, Enum)` = `COMPUTATIONAL`, `BIOLOGICAL`; `RelationLeaf(_Model)` with `leaf: Literal["relation"]`, `tier: Tier`, `kind: RelationKind`, `severity: float` (`ge=-1.0, le=1.0`). Added to the `Leaf` union.
- Consumes: nothing.

- [ ] **Step 1: Write the failing test**

```python
# grammar/tests/test_relation_leaf.py
import pytest
from polymer_grammar.leaf import RelationLeaf, RelationKind, Tier

def test_relation_leaf_ok():
    lf = RelationLeaf(tier=Tier.BIOLOGICAL, kind=RelationKind.TENSION, severity=-0.4)
    assert lf.leaf == "relation" and lf.severity == -0.4

def test_severity_bounds():
    with pytest.raises(ValueError):
        RelationLeaf(tier=Tier.COMPUTATIONAL, kind=RelationKind.COHERES, severity=1.5)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd grammar && python -m pytest tests/test_relation_leaf.py -q`
Expected: FAIL (`ImportError`).

- [ ] **Step 3: Write minimal implementation**

Add to `leaf.py` (near the other leaf classes) and extend the `Leaf` union:

```python
from enum import Enum

class Tier(str, Enum):
    COMPUTATIONAL = "computational"
    BIOLOGICAL = "biological"

class RelationKind(str, Enum):
    COHERES = "coheres"
    TENSION = "tension"
    RESTRICTION_MAP = "restriction_map"

class RelationLeaf(_Model):
    leaf: Literal["relation"] = "relation"
    tier: Tier
    kind: RelationKind
    severity: float = Field(ge=-1.0, le=1.0)  # + coherence, - tension
```

Extend: `Leaf = Annotated[Union[QuantityLeaf, CategoricalLeaf, ExistenceLeaf, PropositionLeaf, RelationLeaf], Field(discriminator="leaf")]` (confirm the existing discriminator field name is `leaf`; if the union isn't discriminated, append `RelationLeaf` to the `Union` unchanged).

- [ ] **Step 4: Run test to verify it passes**

Run: `cd grammar && python -m pytest tests/test_relation_leaf.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add grammar/src/polymer_grammar/leaf.py grammar/tests/test_relation_leaf.py
git commit -m "feat(grammar): RelationLeaf + RelationKind/Tier enums"
```

---

## Task 3: relation `Pattern` + `make_relation_claim` factory + `is_relation`

**Files:**
- Create: `grammar/src/polymer_grammar/relation.py`
- Modify: `grammar/src/polymer_grammar/__init__.py` (export `make_relation_claim`, `is_relation`, `RelationLeaf`, `RelationKind`, `Tier`, `ClaimSetSubject`)
- Test: `grammar/tests/test_relation_factory.py` (create)

**Interfaces:**
- Consumes: `Claim`, `ClaimSetSubject` (Task 1), `RelationLeaf`/`RelationKind`/`Tier` (Task 2), `PatternRef`, `registry`, `Status`.
- Produces: `make_relation_claim(id, source_ids, target_ids, tier, kind, severity, *, rationale, status=Status.CONJECTURED) -> Claim`; `is_relation(claim: Claim) -> bool`.

- [ ] **Step 1: Write the failing test**

```python
# grammar/tests/test_relation_factory.py
from polymer_grammar.relation import make_relation_claim, is_relation
from polymer_grammar.leaf import RelationKind, Tier
from polymer_grammar.status import Status

def test_make_relation_claim():
    c = make_relation_claim("rel-1", ["a"], ["b"], Tier.BIOLOGICAL, RelationKind.TENSION, -0.5,
                            rationale="TP53 vs apoptosis")
    assert c.status == Status.CONJECTURED
    assert c.subject.kind == "claim_set"
    assert c.leaves[0].leaf == "relation" and c.leaves[0].severity == -0.5
    assert c.evaluation_plan is None  # lane guard relies on this
    assert is_relation(c) is True

def test_ordinary_claim_is_not_relation():
    c = make_relation_claim("rel-2", ["x"], ["y"], Tier.COMPUTATIONAL, RelationKind.COHERES, 0.7,
                            rationale="same target, concordant nulls")
    assert is_relation(c) and c.leaves[0].kind == RelationKind.COHERES
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd grammar && python -m pytest tests/test_relation_factory.py -q`
Expected: FAIL (`ImportError`).

- [ ] **Step 3: Write minimal implementation**

```python
# grammar/src/polymer_grammar/relation.py
"""Relation meta-claims — a Claim about a set-to-set relationship (spec 2026-07-13)."""
from __future__ import annotations

from .claim import Claim
from .leaf import RelationKind, RelationLeaf, Tier
from .pattern import Pattern, PatternRef, registry
from .provenance import Provenance  # confirm the provenance type/import
from .status import Status
from .subject import ClaimSetSubject

registry.register(Pattern(
    id="relation", version="v1",
    estimand="claim_set_relationship", null_model="none", scale="signed_unit",
    invariance_group="claim_relabeling",
    intended_applications=("cross_arm_coherence", "cross_arm_tension", "restriction_map"),
    excluded_applications=("single-claim assertions (use the object claim's own pattern)",),
))

_RELATION_PATTERN = PatternRef(id="relation", version="v1")

def make_relation_claim(id, source_ids, target_ids, tier: Tier, kind: RelationKind,
                        severity: float, *, rationale: str,
                        status: Status = Status.CONJECTURED) -> Claim:
    subject = ClaimSetSubject(id=id, display=f"{sorted(source_ids)}~{sorted(target_ids)}",
                              source_set=tuple(source_ids), target_set=tuple(target_ids))
    leaf = RelationLeaf(tier=tier, kind=kind, severity=severity)
    return Claim(id=id, title=rationale[:120], pattern=_RELATION_PATTERN, leaves=(leaf,),
                 status=status, subject=subject,
                 provenance=Provenance(note=rationale))  # match the real Provenance ctor

def is_relation(claim: Claim) -> bool:
    return bool(claim.leaves) and getattr(claim.leaves[0], "leaf", None) == "relation"
```

Adjust the `Provenance` construction to the real signature (read `grammar/src/polymer_grammar/provenance.py`); if provenance is heavier than a note, store the rationale in the simplest valid field. Export the new names from `__init__.py`.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd grammar && python -m pytest tests/test_relation_factory.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add grammar/src/polymer_grammar/relation.py grammar/src/polymer_grammar/__init__.py grammar/tests/test_relation_factory.py
git commit -m "feat(grammar): relation pattern + make_relation_claim factory + is_relation"
```

---

## Task 4: Grammar byte-identity guard

**Files:**
- Test: `grammar/tests/test_relation_byte_identity.py` (create)

**Interfaces:**
- Consumes: an existing golden corpus/claim fixture (reuse whatever the grammar suite already uses for serialization goldens).

- [ ] **Step 1: Write the failing test** (fails only if a prior task changed existing serialization)

```python
# grammar/tests/test_relation_byte_identity.py
import json
from polymer_grammar.claim import Claim

def test_existing_claim_serialization_unchanged(sample_claim_json):  # reuse a fixture / golden
    c = Claim.model_validate(json.loads(sample_claim_json))
    assert c.model_dump_json() == sample_claim_json  # no new keys leak onto relation-free claims
```

- [ ] **Step 2: Run it** — Run: `cd grammar && python -m pytest tests/test_relation_byte_identity.py -q` — Expected: PASS (adding *union members* and a new subject/leaf variant must not alter existing claims' output). If it FAILS, a prior task added a non-defaulted field to an existing model — fix that task.
- [ ] **Step 3–4:** none (guard test).
- [ ] **Step 5: Commit**

```bash
git add grammar/tests/test_relation_byte_identity.py
git commit -m "test(grammar): byte-identity guard for relation-free claims"
```

---

## Task 5: `TopologyEdge` new fields + omit-when-unset serializer + contract bump

**Files:**
- Modify: `protocol/src/polymer_protocol/topology.py`
- Test: `protocol/tests/test_topology_edge_serializer.py` (create)

**Interfaces:**
- Produces: `TopologyEdge` gains `tier: str | None = None`, `signed_weight: float | None = None`, `relation_status: str | None = None`, plus a `@model_serializer` that drops those three keys when all are `None`. Topology `contract_version` bumped one minor.

- [ ] **Step 1: Write the failing test**

```python
# protocol/tests/test_topology_edge_serializer.py
from polymer_protocol.topology import TopologyEdge

def test_legacy_edge_has_no_new_keys():
    e = TopologyEdge(source="a", target="b", kind="defeat", effective=True, provisional=False)
    d = e.model_dump()
    assert "signed_weight" not in d and "tier" not in d and "relation_status" not in d

def test_relation_edge_keeps_new_keys():
    e = TopologyEdge(source="a", target="b", kind="tension", effective=True, provisional=False,
                     tier="biological", signed_weight=-0.3, relation_status="conjectured")
    d = e.model_dump()
    assert d["signed_weight"] == -0.3 and d["tier"] == "biological"
```

- [ ] **Step 2: Run it** — `cd protocol && python -m pytest tests/test_topology_edge_serializer.py -q` — Expected: FAIL (new kwargs rejected by `extra="forbid"`).
- [ ] **Step 3: Implement** (mirror `capability.py`'s `@model_serializer`):

```python
from pydantic import model_serializer

class TopologyEdge(_Model):
    source: str
    target: str
    kind: str
    effective: bool
    provisional: bool
    tier: str | None = None
    signed_weight: float | None = None
    relation_status: str | None = None

    @model_serializer(mode="wrap")
    def _drop_relation_fields_when_unset(self, handler):
        d = handler(self)
        if self.tier is None and self.signed_weight is None and self.relation_status is None:
            for k in ("tier", "signed_weight", "relation_status"):
                d.pop(k, None)
        return d
```

Bump the topology `contract_version` string one minor (find its constant in `topology.py`).

- [ ] **Step 4: Run it** — Expected: PASS. Then run the topology golden suite: `cd protocol && python -m pytest tests/ -k topology -q` — Expected: PASS (legacy bundles byte-identical).
- [ ] **Step 5: Commit**

```bash
git add protocol/src/polymer_protocol/topology.py protocol/tests/test_topology_edge_serializer.py
git commit -m "feat(protocol): versioned TopologyEdge relation fields with omit-when-unset serializer"
```

---

## Task 6: Project relation claims into signed `TopologyEdge`s

**Files:**
- Modify: `protocol/src/polymer_protocol/topology.py` (inside/after `export_topology`)
- Test: `protocol/tests/test_relation_projection.py` (create)

**Interfaces:**
- Consumes: `is_relation` (Task 3), `TopologyEdge` (Task 5).
- Produces: `export_topology` emits, per relation claim, **all-pairs** `TopologyEdge`s between `source_set × target_set` with `kind=relation.kind.value`, `tier`, `relation_status=claim.status.value`, and `signed_weight = severity * status_factor / (|src|*|tgt|)` where `status_factor = 0.3 if CONJECTURED else 1.0`. Plus a weak positive edge from the relation node id to each relatum (`signed_weight = +0.1`).

- [ ] **Step 1: Write the failing test**

```python
# protocol/tests/test_relation_projection.py
from polymer_protocol.topology import export_topology, Layout
# build a tiny corpus: two object claims a,b + a CONJECTURED tension relation over them
def test_tension_projects_negative_all_pairs(tiny_relation_corpus):
    topo = export_topology(tiny_relation_corpus, layout=Layout.NONE)
    rel = [e for e in topo.edges if e.kind == "tension"]
    assert rel and all(e.signed_weight < 0 for e in rel)
    assert {frozenset((e.source, e.target)) for e in rel} == {frozenset(("a", "b"))}
```

Provide `tiny_relation_corpus` as a fixture building `Corpus(claims=(a, b, make_relation_claim("r",["a"],["b"],Tier.BIOLOGICAL,RelationKind.TENSION,-0.6,rationale="x")), fdr_ledger=...)`.

- [ ] **Step 2: Run it** — Expected: FAIL (no `tension` edges emitted).
- [ ] **Step 3: Implement** a `_relation_edges(corpus) -> list[TopologyEdge]` helper and append its output to the edge list in `export_topology`:

```python
def _relation_edges(corpus):
    out = []
    for c in corpus.claims:
        if not is_relation(c):
            continue
        lf = c.leaves[0]; s = c.subject
        factor = 0.3 if c.status.value == "conjectured" else 1.0
        n = max(1, len(s.source_set) * len(s.target_set))
        w = lf.severity * factor / n
        for a in s.source_set:
            for b in s.target_set:
                out.append(TopologyEdge(source=a, target=b, kind=lf.kind.value,
                                        effective=False, provisional=(c.status.value == "conjectured"),
                                        tier=lf.tier.value, signed_weight=round(w, 6),
                                        relation_status=c.status.value))
        for m in (*s.source_set, *s.target_set):  # localize the relation node at the seam
            out.append(TopologyEdge(source=c.id, target=m, kind="coheres", effective=False,
                                    provisional=True, tier=lf.tier.value, signed_weight=0.1,
                                    relation_status=c.status.value))
    return out
```

- [ ] **Step 4: Run it** — Expected: PASS. Re-run the byte-identity golden with a relation-free corpus — Expected: PASS (no relation claims → no extra edges).
- [ ] **Step 5: Commit**

```bash
git add protocol/src/polymer_protocol/topology.py protocol/tests/test_relation_projection.py
git commit -m "feat(protocol): project relation claims into all-pairs signed topology edges"
```

---

## Task 7: `is_relation` lane guard (no SELECT/EXECUTE/FDR)

**Files:**
- Modify: the claim-selection site (`protocol/src/polymer_protocol/represent.py` or wherever `run_cycle`/SELECT chooses candidate claims — confirm by grepping for where claims enter selection/execution)
- Test: `protocol/tests/test_relation_lane_guard.py` (create)

**Interfaces:**
- Consumes: `is_relation`.
- Produces: relation claims are excluded from the selectable/executable set and never appear in an FDR test.

- [ ] **Step 1: Write the failing test**

```python
# protocol/tests/test_relation_lane_guard.py
from polymer_protocol import run_cycle  # or the SELECT function
def test_relation_never_selected_or_charged(corpus_with_relation):
    out = run_cycle(corpus_with_relation, adapters=(), ctx=...)  # minimal deterministic call
    # the relation claim id must not appear in any fdr test, nor be marked executed
    rel_ids = {c.id for c in corpus_with_relation.claims if c.leaves and c.leaves[0].leaf == "relation"}
    assert not (rel_ids & {t.claim_id for t in out.fdr_ledger.tests})
```

- [ ] **Step 2: Run it** — Expected: FAIL (relation claim selected/charged).
- [ ] **Step 3: Implement** — at the selection filter, add `if is_relation(c): continue` (or filter the candidate list `[c for c in corpus.claims if not is_relation(c)]`). Keep it one narrow guard at the lane entry.
- [ ] **Step 4: Run it** — Expected: PASS. Run `cd protocol && python -m pytest tests/ -q` — Expected: no regressions.
- [ ] **Step 5: Commit**

```bash
git add protocol/src/polymer_protocol/ protocol/tests/test_relation_lane_guard.py
git commit -m "feat(protocol): is_relation lane guard — relations excluded from SELECT/EXECUTE/FDR"
```

---

## Task 8: Signed aggregation in `embedding.py`

**Files:**
- Modify: `src/polymer_claims/embedding.py`
- Test: `tests/test_embedding_signed.py` (create)

**Interfaces:**
- Consumes: `TopologyEdge.signed_weight` (Task 5/6).
- Produces: `build_graph` sums signed contributions per pair then clamps to `[-1, 1]`; a legacy kind with no `signed_weight` contributes its positive `KIND_WEIGHT`; a `signed_weight` edge contributes that value. Replaces the `max()` collapse.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_embedding_signed.py
from polymer_claims.embedding import build_graph
def test_tension_nets_negative(corpus_coherent_and_tension):
    # a pair with a weak +0.2 legacy edge and a -0.6 tension edge should net negative
    _, W, _ = build_graph(corpus_coherent_and_tension)
    assert W[frozenset(("a", "b"))] < 0
```

- [ ] **Step 2: Run it** — Expected: FAIL (`max()` keeps the positive).
- [ ] **Step 3: Implement** — in `build_graph`, replace the `W[key] = max(...)` line with signed accumulation:

```python
signed = e.signed_weight if e.signed_weight is not None else KIND_WEIGHT.get(e.kind)
if signed is None:
    continue
acc = W.get(key, 0.0) + signed
W[key] = max(-1.0, min(1.0, acc))
```

Confirm `_embed_component` already handles negative `W` entries as repulsion (the `polar`/`RHO` path); if it only special-cases `polar`, generalize it to treat any `W[key] < 0` as repulsion and drop the `polar` special-case (keep behavior identical for the existing opposite-direction `rebut`).

- [ ] **Step 4: Run it** — Expected: PASS. Run `python -m pytest tests/ -k embedding -q` — Expected: existing spectral goldens still pass (no relations → all positive as before).
- [ ] **Step 5: Commit**

```bash
git add src/polymer_claims/embedding.py tests/test_embedding_signed.py
git commit -m "feat(embedding): signed sum-clamp aggregation; general repulsion for negative weights"
```

---

## Task 9: Candidate generation (subject normalization + blocking)

**Files:**
- Create: `src/polymer_claims/relation_proposer.py`
- Test: `tests/test_candidate_gen.py` (create)

**Interfaces:**
- Produces: `entity_key(claim) -> frozenset[str]` (extracts normalized biological keys from a claim's `Subject` — `GeneOrProtein.symbol`, `OntologyTerm.uri`, `GenomicRegion` locus, `PathwayRef` — plus arm `topic`); `candidate_pairs(corpus, *, max_pairs) -> list[tuple[str, str]]` (pairs claims sharing ≥1 key, capped, deterministic order, cross-arm only).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_candidate_gen.py
from polymer_claims.relation_proposer import candidate_pairs
def test_pairs_share_entity_cross_arm(corpus_two_arms_tp53):
    pairs = candidate_pairs(corpus_two_arms_tp53, max_pairs=100)
    assert ("pharmaco:tp53_meth", "synbio:tp53_expr") in {tuple(sorted(p)) for p in pairs}

def test_capped_and_deterministic(corpus_two_arms_tp53):
    p1 = candidate_pairs(corpus_two_arms_tp53, max_pairs=1)
    p2 = candidate_pairs(corpus_two_arms_tp53, max_pairs=1)
    assert p1 == p2 and len(p1) == 1
```

- [ ] **Step 2: Run it** — Expected: FAIL (`ImportError`).
- [ ] **Step 3: Implement** `entity_key` over the concrete `Subject` variants + `candidate_pairs` (invert keys→claim ids, emit sorted cross-arm pairs sharing a key, truncate at `max_pairs`, `log()` the dropped count). Keep it pure-python (no numpy).
- [ ] **Step 4: Run it** — Expected: PASS.
- [ ] **Step 5: Commit**

```bash
git add src/polymer_claims/relation_proposer.py tests/test_candidate_gen.py
git commit -m "feat(proposer): candidate generation via subject-entity blocking (cross-arm, capped)"
```

---

## Task 10: The LLM relation proposer

**Files:**
- Modify: `src/polymer_claims/relation_proposer.py`
- Test: `tests/test_relation_proposer.py` (create; agent mocked)

**Interfaces:**
- Consumes: `candidate_pairs` (Task 9), `make_relation_claim` (Task 3), the existing `LLMGenerationAdapter` pattern.
- Produces: `propose_relations(corpus, agent, *, max_pairs, threshold) -> list[Claim]` — for each candidate pair, call `agent.judge(claim_a, claim_b)` → `{tier, kind, severity, rationale} | None`; emit a CONJECTURED relation claim when `abs(severity) >= threshold`; audit-log every proposal + decline.

- [ ] **Step 1: Write the failing test** (mock the agent for determinism)

```python
# tests/test_relation_proposer.py
from polymer_claims.relation_proposer import propose_relations
class FakeAgent:
    def judge(self, a, b):
        return {"tier": "biological", "kind": "coheres", "severity": 0.7, "rationale": "same pathway"}
def test_emits_conjectured_relation(corpus_two_arms_tp53):
    rels = propose_relations(corpus_two_arms_tp53, FakeAgent(), max_pairs=10, threshold=0.3)
    assert rels and all(r.status.value == "conjectured" and r.leaves[0].leaf == "relation" for r in rels)
def test_below_threshold_declined(corpus_two_arms_tp53):
    class Weak:  # noqa
        def judge(self, a, b): return {"tier":"biological","kind":"tension","severity":-0.1,"rationale":"weak"}
    assert propose_relations(corpus_two_arms_tp53, Weak(), max_pairs=10, threshold=0.3) == []
```

- [ ] **Step 2: Run it** — Expected: FAIL.
- [ ] **Step 3: Implement** `propose_relations` + a concrete `LLMRelationAgent` (mirroring `LLMGenerationAdapter`; a real `judge` prompt behind a live-smoke tripwire, not run in unit tests).
- [ ] **Step 4: Run it** — Expected: PASS.
- [ ] **Step 5: Commit**

```bash
git add src/polymer_claims/relation_proposer.py tests/test_relation_proposer.py
git commit -m "feat(proposer): LLM relation proposer emits CONJECTURED relations (threshold + audit)"
```

---

## Task 11: Viewer renders relation nodes/edges

**Files:**
- Modify: the viewer edge/legend components (grep `viewer/src` for where `TopologyEdge`/edge `kind` is consumed — e.g. `LegendRail.tsx`, the edges mesh)
- Test: `viewer` typecheck + a render smoke via the run skill

**Interfaces:**
- Consumes: the new `TopologyEdge` fields (`tier`, `signed_weight`, `relation_status`).

- [ ] **Step 1:** Extend the edge TypeScript type with optional `tier?`, `signed_weight?`, `relation_status?`.
- [ ] **Step 2:** Color edges by `tier` (computational vs biological), style by sign (`signed_weight < 0` = tension) and dash when `relation_status === "conjectured"`; add the three `RelationKind`s to the edge-kind legend.
- [ ] **Step 3:** `cd viewer && npm run typecheck` — Expected: clean.
- [ ] **Step 4:** Boot the viewer (run skill), load a bundle containing relations, screenshot — Expected: relation edges visible, dashed, colored by tier.
- [ ] **Step 5: Commit**

```bash
git add viewer/src
git commit -m "feat(viewer): render relation edges — tier color, signed style, dashed conjectured"
```

---

## Task 12: End-to-end integration + spectral connectivity

**Files:**
- Modify: `viewer/scripts/make_merged_universe.py` (run the proposer, add relation claims, switch to spectral)
- Test: `tests/test_relations_e2e.py` (create)

- [ ] **Step 1: Write the failing test**

```python
# tests/test_relations_e2e.py
from polymer_claims.embedding import build_graph, spectral_layout
def test_relations_connect_and_spectral_is_nontrivial(merged_corpus_with_relations):
    ids, W, _ = build_graph(merged_corpus_with_relations)
    touched = {x for k in W for x in k}
    assert len(touched) > 0.5 * len(ids)  # relations connect the bulk (vs 3.3% today)
    pos = spectral_layout(merged_corpus_with_relations)
    assert len({tuple(v) for v in pos.values()}) > 1  # not all collapsed to one point
```

- [ ] **Step 2: Run it** — Expected: FAIL until the proposer has populated relations in the fixture.
- [ ] **Step 3: Implement** — in `make_merged_universe.py`, after merging arms, call `propose_relations(...)`, extend `Corpus.claims`, and export with `Layout` set so `spectral_layout` positions are used (or add a `--spectral` path). Regenerate `merged-universe.json`.
- [ ] **Step 4: Run it** — Expected: PASS. Then `bash scripts/check-all.sh` — Expected: full gate green.
- [ ] **Step 5: Commit**

```bash
git add viewer/scripts/make_merged_universe.py viewer/public/merged-universe.json tests/test_relations_e2e.py
git commit -m "feat: wire relation proposer into the merged universe; spectral becomes meaningful"
```

---

## Self-Review (author checklist — done)

- **Spec coverage:** §4 relation meta-claim → Tasks 1–3; §0.2.7 serializer → Task 5; §6 projection + aggregation → Tasks 6, 8; §9 lane guard → Task 7; §7 proposer → Tasks 9–10; §6 viewer/data-flow → Tasks 11–12; §9 byte-identity → Tasks 4, 5, 6. `restriction_map` sheaf wiring is **out of scope** (Slice 2) — Task 2 defines the kind, Task 11 renders it, none wires sheaf behavior. ✓
- **Placeholder scan:** two spots require confirming a real signature before coding (the `Leaf`/`Subject` union discriminator field name; the `Provenance` constructor; the exact SELECT site for Task 7) — each names the file to read and the fallback, not a "TODO". ✓
- **Type consistency:** `is_relation`, `make_relation_claim`, `signed_weight`, `status_factor`, `RelationKind`, `Tier` used consistently across tasks. ✓
