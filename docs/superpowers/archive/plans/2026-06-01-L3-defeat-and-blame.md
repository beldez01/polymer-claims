# Phase 5 — L3 Defeat Graph + Duhem Blame-Sets Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the L3 corpus layer to the v1.3 grammar — a strength-mediated (VAF) defeat graph whose grounded extension says which claims are IN, plus a represented-and-aggregated Duhem–Quine blame-set facility.

**Architecture:** Two new corpus-level modules of pure functions over data, mirroring `equivalence.py` (no new `Claim` fields). `defeat.py` holds the edge type + graph traversal (effective-defeat value filter, grounded extension, derived-rebut helper, L2 failed-satisfaction adapter). `blame.py` holds the set-algebra over supplied minimal blame-assignments. `equivalence.py` gains an additive `grounded_in` kwarg replacing its LICENSED-only "IN" stub.

**Tech Stack:** Python 3.12, pydantic v2 (`_Model` frozen + `extra="forbid"`), pytest, uv. Tests: `cd grammar && uv run pytest -q`; lint: `uv run ruff check src tests`.

**Spec:** `docs/superpowers/specs/2026-06-01-L3-defeat-and-blame-spec.md`

---

## File Structure

- Create: `grammar/src/polymer_grammar/defeat.py` — `DefeatEdgeKind`, `ATTACK_KINDS`, `DefeatEdge`, `effective_defeats`, `grounded_extension`, `derived_rebut_edges`, `undermine_edges_from_failed_satisfactions`.
- Create: `grammar/src/polymer_grammar/blame.py` — `BlameAssignment`, `BlameSet`, `BlameVerdict`, `aggregate_blame`, `duhem_status`.
- Modify: `grammar/src/polymer_grammar/equivalence.py` — add optional `grounded_in` kwarg to `equivalence_class` + `are_equivalent`.
- Modify: `grammar/src/polymer_grammar/__init__.py` — re-export the new symbols.
- Create: `grammar/tests/test_defeat.py`, `grammar/tests/test_blame.py`.
- Modify: `grammar/tests/test_equivalence.py` — add `grounded_in` cases.

All work on a feature branch `phase5-l3-defeat-blame`; merge `--no-ff` to `main` at the end (per the project's local-commit rhythm). Isolation guard (`test_isolation.py`) must stay green — no `polymer_formalclaim` import anywhere.

---

### Task 1: `DefeatEdge` type + edge kinds

**Files:**
- Create: `grammar/src/polymer_grammar/defeat.py`
- Test: `grammar/tests/test_defeat.py`

- [ ] **Step 1: Write the failing test**

```python
# grammar/tests/test_defeat.py
import pytest
from pydantic import ValidationError

from polymer_grammar.defeat import ATTACK_KINDS, DefeatEdge, DefeatEdgeKind


def test_edge_kinds_are_five_attacks_plus_support():
    assert {k.value for k in DefeatEdgeKind} == {
        "undermine", "undercut", "rebut", "reclassify", "reinterpret", "evidence_for",
    }
    assert DefeatEdgeKind.EVIDENCE_FOR not in ATTACK_KINDS
    assert len(ATTACK_KINDS) == 5


def test_edge_is_frozen_and_hashable():
    e = DefeatEdge(source="a", target="b", kind=DefeatEdgeKind.REBUT)
    assert isinstance(hash(e), int)
    with pytest.raises(ValidationError):
        DefeatEdge(source="a", target="b", kind=DefeatEdgeKind.REBUT, bogus=1)


def test_self_loop_rejected():
    with pytest.raises(ValidationError):
        DefeatEdge(source="a", target="a", kind=DefeatEdgeKind.UNDERMINE)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd grammar && uv run pytest tests/test_defeat.py -q`
Expected: FAIL (ModuleNotFoundError: No module named 'polymer_grammar.defeat')

- [ ] **Step 3: Write minimal implementation**

```python
# grammar/src/polymer_grammar/defeat.py
"""L3 — the value-based defeat graph over claims (spec §3.5).

A corpus-level module of pure functions over edges, mirroring equivalence.py — no
fields are added to Claim. Edges are attacks (undermine/undercut/rebut/reclassify/
reinterpret) or support (evidence_for). Which attacks actually DEFEAT is filtered by
the Phase-4 Pareto strength order (effective_defeats); the grounded extension over
those effective defeats says which claims are IN. Imports nothing from
polymer_formalclaim (isolation guard).
"""
from __future__ import annotations

from enum import Enum

from pydantic import model_validator

from .base import _Model


class DefeatEdgeKind(str, Enum):
    UNDERMINE = "undermine"      # attacks a premise / the data basis
    UNDERCUT = "undercut"        # attacks the inferential warrant
    REBUT = "rebut"              # asserts the contrary conclusion
    RECLASSIFY = "reclassify"    # disputes the pattern/profile applied
    REINTERPRET = "reinterpret"  # meaning moved, statistics unchanged
    EVIDENCE_FOR = "evidence_for"  # support, never a defeat


ATTACK_KINDS = frozenset(
    {
        DefeatEdgeKind.UNDERMINE,
        DefeatEdgeKind.UNDERCUT,
        DefeatEdgeKind.REBUT,
        DefeatEdgeKind.RECLASSIFY,
        DefeatEdgeKind.REINTERPRET,
    }
)


class DefeatEdge(_Model):
    source: str
    target: str
    kind: DefeatEdgeKind
    note: str | None = None

    @model_validator(mode="after")
    def _no_self_loop(self) -> "DefeatEdge":
        if self.source == self.target:
            raise ValueError(
                "a DefeatEdge must relate two DISTINCT claims (no self-defeat/self-support)"
            )
        return self
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd grammar && uv run pytest tests/test_defeat.py -q`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
cd ~/Desktop/polymer-claims
git add grammar/src/polymer_grammar/defeat.py grammar/tests/test_defeat.py
git commit -m "feat(grammar): L3 DefeatEdge type + edge kinds (attacks vs support)"
```

---

### Task 2: `effective_defeats` — the strength-mediated value filter

**Files:**
- Modify: `grammar/src/polymer_grammar/defeat.py`
- Test: `grammar/tests/test_defeat.py`

- [ ] **Step 1: Write the failing test**

```python
# append to grammar/tests/test_defeat.py
from polymer_grammar.defeat import effective_defeats
from polymer_grammar.strength import StrengthVector


def _sv(x):
    # uniform vector at level x on all six axes
    return StrengthVector(
        magnitude=x, uncertainty=x, evidence_against_null=x,
        severity=x, world_contact=x, explanatory_virtue=x,
    )


def test_attack_filtered_when_target_dominates_source():
    edges = [DefeatEdge(source="weak", target="strong", kind=DefeatEdgeKind.REBUT)]
    strength = {"weak": _sv(0.2), "strong": _sv(0.9)}
    # target (strong) dominates source (weak) -> attack does NOT defeat
    assert effective_defeats(edges, strength) == frozenset()


def test_attack_stands_when_source_dominates_target():
    edges = [DefeatEdge(source="strong", target="weak", kind=DefeatEdgeKind.REBUT)]
    strength = {"strong": _sv(0.9), "weak": _sv(0.2)}
    assert effective_defeats(edges, strength) == frozenset({("strong", "weak")})


def test_attack_stands_when_incomparable_or_missing_strength():
    # incomparable: a higher on some axis, b higher on another
    a = StrengthVector(magnitude=0.9, uncertainty=0.1, evidence_against_null=0.5,
                       severity=0.5, world_contact=0.5, explanatory_virtue=0.5)
    b = StrengthVector(magnitude=0.1, uncertainty=0.9, evidence_against_null=0.5,
                       severity=0.5, world_contact=0.5, explanatory_virtue=0.5)
    edges = [DefeatEdge(source="a", target="b", kind=DefeatEdgeKind.UNDERCUT)]
    assert effective_defeats(edges, {"a": a, "b": b}) == frozenset({("a", "b")})
    # missing strength -> attack stands
    assert effective_defeats(edges, {}) == frozenset({("a", "b")})


def test_evidence_for_is_never_a_defeat():
    edges = [DefeatEdge(source="x", target="y", kind=DefeatEdgeKind.EVIDENCE_FOR)]
    assert effective_defeats(edges, {"x": _sv(0.1), "y": _sv(0.9)}) == frozenset()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd grammar && uv run pytest tests/test_defeat.py -q`
Expected: FAIL (ImportError: cannot import name 'effective_defeats')

- [ ] **Step 3: Write minimal implementation**

Add to `grammar/src/polymer_grammar/defeat.py` (update imports + append functions):

```python
# update the top-of-file imports to:
from __future__ import annotations

from collections.abc import Iterable, Mapping
from enum import Enum

from pydantic import model_validator

from .base import _Model
from .strength import StrengthVector
```

```python
# append after the DefeatEdge class
def effective_defeats(
    edges: Iterable[DefeatEdge],
    strength: Mapping[str, StrengthVector | None],
) -> frozenset[tuple[str, str]]:
    """(source, target) attack pairs that survive the VAF value filter.

    An attack defeats UNLESS the target strength-dominates the source (Pareto). When
    either strength is absent or the two are incomparable, the attack stands — absence
    of proven superiority is not superiority. `evidence_for` is never a defeat.
    """
    out: set[tuple[str, str]] = set()
    for e in edges:
        if e.kind not in ATTACK_KINDS:
            continue
        s_src = strength.get(e.source)
        s_tgt = strength.get(e.target)
        if s_src is not None and s_tgt is not None and s_tgt.dominates(s_src):
            continue  # target proven stronger -> attack filtered out
        out.add((e.source, e.target))
    return frozenset(out)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd grammar && uv run pytest tests/test_defeat.py -q`
Expected: PASS (7 passed)

- [ ] **Step 5: Commit**

```bash
cd ~/Desktop/polymer-claims
git add grammar/src/polymer_grammar/defeat.py grammar/tests/test_defeat.py
git commit -m "feat(grammar): L3 effective_defeats (Pareto-strength VAF value filter)"
```

---

### Task 3: `grounded_extension` — Dung least fixpoint over effective defeats

**Files:**
- Modify: `grammar/src/polymer_grammar/defeat.py`
- Test: `grammar/tests/test_defeat.py`

- [ ] **Step 1: Write the failing test**

```python
# append to grammar/tests/test_defeat.py
from polymer_grammar.defeat import grounded_extension


def test_unattacked_claims_are_in():
    assert grounded_extension(["a", "b"], [], {}) == frozenset({"a", "b"})


def test_mutual_attack_both_out_when_attacks_stand():
    # a <-> b mutual attack; no strength -> no value filter, both attacks stand
    # -> classic Dung mutual attack: grounded extension is empty.
    edges = [
        DefeatEdge(source="a", target="b", kind=DefeatEdgeKind.REBUT),
        DefeatEdge(source="b", target="a", kind=DefeatEdgeKind.REBUT),
    ]
    assert grounded_extension(["a", "b"], edges, {}) == frozenset()


def test_reinstatement():
    # c -> a -> b, all attacks stand. grounded = {c, b}: a is OUT, so b is reinstated.
    edges = [
        DefeatEdge(source="c", target="a", kind=DefeatEdgeKind.REBUT),
        DefeatEdge(source="a", target="b", kind=DefeatEdgeKind.REBUT),
    ]
    assert grounded_extension(["a", "b", "c"], edges, {}) == frozenset({"c", "b"})


def test_value_filter_breaks_symmetry():
    # mutual attack, but 'strong' dominates 'weak': weak's attack on strong is filtered,
    # strong's attack on weak stands -> grounded = {strong}.
    edges = [
        DefeatEdge(source="weak", target="strong", kind=DefeatEdgeKind.REBUT),
        DefeatEdge(source="strong", target="weak", kind=DefeatEdgeKind.REBUT),
    ]
    strength = {"weak": _sv(0.2), "strong": _sv(0.9)}
    assert grounded_extension(["weak", "strong"], edges, strength) == frozenset({"strong"})


def test_edge_endpoints_not_in_claim_ids_still_participate():
    # synthetic attacker 'r' (not in claim_ids), no strength -> unattacked, IN, defeats 'a'
    edges = [DefeatEdge(source="r", target="a", kind=DefeatEdgeKind.UNDERMINE)]
    ext = grounded_extension(["a"], edges, {})
    assert "a" not in ext
    assert "r" in ext
```

> **Note (design clarification during execution):** grounded_extension uses the **single** `effective_defeats` relation (no separate strict-`>` predicate). Because the value filter uses `≥` (`dominates`), equal-strength mutual attacks are *filtered* (both claims stay IN — the contradiction is surfaced by the L3 blame-set layer, not the defeat graph). These structural tests therefore use empty strength so attacks stand; `test_value_filter_breaks_symmetry` covers the dominance case. The expected count after this task is **14 passed**.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd grammar && uv run pytest tests/test_defeat.py -q`
Expected: FAIL (ImportError: cannot import name 'grounded_extension')

- [ ] **Step 3: Write minimal implementation**

Add to `grammar/src/polymer_grammar/defeat.py` (add `defaultdict` import, append function):

```python
# add to imports
from collections import defaultdict
```

```python
# append
def grounded_extension(
    claim_ids: Iterable[str],
    edges: Iterable[DefeatEdge],
    strength: Mapping[str, StrengthVector | None],
) -> frozenset[str]:
    """The IN set under grounded semantics over effective defeats (PTIME least fixpoint).

    F(S) = { a | every effective-attacker of a is itself effectively-attacked by some
    member of S }. Start from the empty set and add acceptable arguments until fixpoint;
    monotone F + add-only => the unique grounded extension. Edge endpoints not in
    claim_ids (e.g. synthetic refutation nodes) participate as nodes.
    """
    defeats = effective_defeats(edges, strength)
    nodes: set[str] = set(claim_ids)
    attackers: dict[str, set[str]] = defaultdict(set)
    for src, tgt in defeats:
        attackers[tgt].add(src)
        nodes.add(src)
        nodes.add(tgt)

    accepted: set[str] = set()
    changed = True
    while changed:
        changed = False
        for a in nodes:
            if a in accepted:
                continue
            if all(
                any((c, b) in defeats for c in accepted)
                for b in attackers.get(a, ())
            ):
                accepted.add(a)
                changed = True
    return frozenset(accepted)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd grammar && uv run pytest tests/test_defeat.py -q`
Expected: PASS (11 passed)

- [ ] **Step 5: Commit**

```bash
cd ~/Desktop/polymer-claims
git add grammar/src/polymer_grammar/defeat.py grammar/tests/test_defeat.py
git commit -m "feat(grammar): L3 grounded_extension (PTIME Dung least fixpoint)"
```

---

### Task 4: `derived_rebut_edges` — opt-in L1 `incompatible_with` → mutual rebut

**Files:**
- Modify: `grammar/src/polymer_grammar/defeat.py`
- Test: `grammar/tests/test_defeat.py`

- [ ] **Step 1: Write the failing test**

```python
# append to grammar/tests/test_defeat.py
from polymer_grammar.claim import Claim
from polymer_grammar.defeat import derived_rebut_edges
from polymer_grammar.leaf import MeasurementBasis, QuantityLeaf
from polymer_grammar.pattern import PatternRef
from polymer_grammar.proposition import (
    Direction, NeighborEdge, NeighborEdgeKind, Proposition,
)
from polymer_grammar.status import Status


def _leaf():
    return QuantityLeaf(value=1.0, measurement_basis=MeasurementBasis.DERIVED, formula="f")


def _claim(cid, prop, status=Status.LICENSED):
    return Claim(
        id=cid, title=cid, pattern=PatternRef(id="p", version="v1"),
        leaves=(_leaf(),), status=status, conclusion=prop,
    )


def test_derived_rebut_between_incompatible_licensed_claims():
    # prop_b is what prop_a is incompatible_with (by content_hash)
    prop_b = Proposition(direction=Direction.NEGATIVE, estimand="e", descriptor="d-neg")
    prop_a = Proposition(
        direction=Direction.POSITIVE, estimand="e", descriptor="d-pos",
        neighborhood=(NeighborEdge(kind=NeighborEdgeKind.INCOMPATIBLE_WITH,
                                   target=prop_b.content_hash),),
    )
    a = _claim("a", prop_a)
    b = _claim("b", prop_b)
    edges = derived_rebut_edges([a, b])
    pairs = {(e.source, e.target, e.kind) for e in edges}
    assert ("a", "b", DefeatEdgeKind.REBUT) in pairs
    assert ("b", "a", DefeatEdgeKind.REBUT) in pairs


def test_no_derived_rebut_for_non_licensed_or_unmatched():
    from polymer_grammar.status import PendingReason

    prop_b = Proposition(direction=Direction.NEGATIVE, estimand="e", descriptor="d-neg")
    prop_a = Proposition(
        direction=Direction.POSITIVE, estimand="e", descriptor="d-pos",
        neighborhood=(NeighborEdge(kind=NeighborEdgeKind.INCOMPATIBLE_WITH,
                                   target=prop_b.content_hash),),
    )
    # `a` is PENDING (not LICENSED) -> excluded from derived rebut; needs a pending_reason
    a = Claim(
        id="a", title="a", pattern=PatternRef(id="p", version="v1"),
        leaves=(_leaf(),), status=Status.PENDING,
        pending_reason=PendingReason.UNTESTED, conclusion=prop_a,
    )
    b = _claim("b", prop_b)
    assert derived_rebut_edges([a, b]) == ()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd grammar && uv run pytest tests/test_defeat.py -q`
Expected: FAIL (ImportError: cannot import name 'derived_rebut_edges')

- [ ] **Step 3: Write minimal implementation**

Add to `grammar/src/polymer_grammar/defeat.py` (add imports for `Claim`, `NeighborEdgeKind`, `Status`; append function). To avoid a circular import, import `Claim` lazily inside the function via `TYPE_CHECKING` for the annotation only:

```python
# add to imports
from typing import TYPE_CHECKING

from .proposition import NeighborEdgeKind
from .status import Status

if TYPE_CHECKING:
    from .claim import Claim
```

```python
# append
def derived_rebut_edges(claims: "Iterable[Claim]") -> tuple[DefeatEdge, ...]:
    """Mutual `rebut` edges between LICENSED claims whose conclusions are materially
    incompatible (an L1 `incompatible_with` NeighborEdge resolving between their
    Proposition content_hashes). Opt-in: the caller merges these with authored edges
    before grounded_extension. Reads L1 neighborhoods; mutates nothing.
    """
    licensed = [
        c for c in claims if c.status == Status.LICENSED and c.conclusion is not None
    ]
    by_hash: dict[str, list[str]] = defaultdict(list)
    for c in licensed:
        by_hash[c.conclusion.content_hash].append(c.id)

    edges: list[DefeatEdge] = []
    seen: set[tuple[str, str]] = set()
    for c in licensed:
        for edge in c.conclusion.neighborhood:
            if edge.kind != NeighborEdgeKind.INCOMPATIBLE_WITH:
                continue
            for other_id in by_hash.get(edge.target, ()):
                if other_id == c.id:
                    continue
                for s, t in ((c.id, other_id), (other_id, c.id)):
                    if (s, t) not in seen:
                        seen.add((s, t))
                        edges.append(
                            DefeatEdge(
                                source=s, target=t, kind=DefeatEdgeKind.REBUT,
                                note="derived from incompatible_with",
                            )
                        )
    return tuple(edges)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd grammar && uv run pytest tests/test_defeat.py -q`
Expected: PASS (13 passed)

- [ ] **Step 5: Commit**

```bash
cd ~/Desktop/polymer-claims
git add grammar/src/polymer_grammar/defeat.py grammar/tests/test_defeat.py
git commit -m "feat(grammar): L3 derived_rebut_edges (opt-in, from L1 incompatible_with)"
```

---

### Task 5: `undermine_edges_from_failed_satisfactions` — L2 carry-forward adapter

**Files:**
- Modify: `grammar/src/polymer_grammar/defeat.py`
- Test: `grammar/tests/test_defeat.py`

- [ ] **Step 1: Write the failing test**

```python
# append to grammar/tests/test_defeat.py
from polymer_grammar.defeat import undermine_edges_from_failed_satisfactions
from polymer_grammar.licensing import MaterializationContext, Satisfaction, SatisfactionVerdict


def _sat(mid, verdict):
    return Satisfaction(
        verdict=verdict,
        materialization=MaterializationContext(id=mid, api_version="0.9", data_version="db@x"),
    )


def test_refuted_and_undetermined_become_undermine_edges():
    sats = [
        _sat("m1", SatisfactionVerdict.REFUTED),
        _sat("m2", SatisfactionVerdict.UNDETERMINED),
        _sat("m3", SatisfactionVerdict.SATISFIED),
    ]
    edges = undermine_edges_from_failed_satisfactions("claimX", sats)
    assert len(edges) == 2
    assert all(e.kind == DefeatEdgeKind.UNDERMINE and e.target == "claimX" for e in edges)
    assert {e.source for e in edges} == {"refutation:m1", "refutation:m2"}


def test_all_satisfied_yields_no_edges():
    sats = [_sat("m1", SatisfactionVerdict.SATISFIED)]
    assert undermine_edges_from_failed_satisfactions("claimX", sats) == ()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd grammar && uv run pytest tests/test_defeat.py -q`
Expected: FAIL (ImportError: cannot import name 'undermine_edges_from_failed_satisfactions')

- [ ] **Step 3: Write minimal implementation**

Add to `grammar/src/polymer_grammar/defeat.py` (add import, append function):

```python
# add to imports
from .licensing import Satisfaction, SatisfactionVerdict
```

```python
# append
def undermine_edges_from_failed_satisfactions(
    claim_id: str, satisfactions: Iterable[Satisfaction]
) -> tuple[DefeatEdge, ...]:
    """Failed licensing attempts (L2) become first-class `undermine` edges instead of
    being silently dropped. Each refuted/undetermined Satisfaction yields an edge from
    a synthetic `refutation:{materialization.id}` node attacking the claim's basis.
    """
    failed = {SatisfactionVerdict.REFUTED, SatisfactionVerdict.UNDETERMINED}
    edges: list[DefeatEdge] = []
    for s in satisfactions:
        if s.verdict in failed:
            edges.append(
                DefeatEdge(
                    source=f"refutation:{s.materialization.id}",
                    target=claim_id,
                    kind=DefeatEdgeKind.UNDERMINE,
                    note=f"{s.verdict.value} in {s.materialization.id}",
                )
            )
    return tuple(edges)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd grammar && uv run pytest tests/test_defeat.py -q`
Expected: PASS (15 passed)

- [ ] **Step 5: Commit**

```bash
cd ~/Desktop/polymer-claims
git add grammar/src/polymer_grammar/defeat.py grammar/tests/test_defeat.py
git commit -m "feat(grammar): L3 adapter — failed L2 satisfactions -> undermine edges"
```

---

### Task 6: Equivalence rerouting — additive `grounded_in` path

**Files:**
- Modify: `grammar/src/polymer_grammar/equivalence.py`
- Test: `grammar/tests/test_equivalence.py`

- [ ] **Step 1: Write the failing test**

```python
# append to grammar/tests/test_equivalence.py
from polymer_grammar.equivalence import EquivalenceClaim, are_equivalent, equivalence_class
from polymer_grammar.status import Status


def _eq(eid, left, right, status=Status.LICENSED):
    return EquivalenceClaim(id=eid, left=left, right=right, severity=0.5, status=status)


def test_grounded_in_overrides_licensed_only_stub():
    # edge is LICENSED, so default path links a~b...
    eqs = [_eq("e1", "a", "b")]
    assert are_equivalent("a", "b", eqs)  # default (LICENSED) path
    # ...but if the equivalence claim e1 is OUT of the grounded extension, it must NOT link
    assert not are_equivalent("a", "b", eqs, grounded_in=frozenset())
    assert are_equivalent("a", "b", eqs, grounded_in=frozenset({"e1"}))


def test_grounded_in_class_membership():
    eqs = [_eq("e1", "a", "b"), _eq("e2", "b", "c")]
    # only e1 is IN -> class of a is {a, b}, c excluded
    assert equivalence_class("a", eqs, grounded_in=frozenset({"e1"})) == frozenset({"a", "b"})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd grammar && uv run pytest tests/test_equivalence.py -q`
Expected: FAIL (TypeError: equivalence_class() got an unexpected keyword argument 'grounded_in')

- [ ] **Step 3: Write minimal implementation**

Modify `grammar/src/polymer_grammar/equivalence.py`. Replace the two functions with versions taking an optional keyword-only `grounded_in`:

```python
def equivalence_class(
    handle: str,
    equivalences: Iterable[EquivalenceClaim],
    *,
    grounded_in: frozenset[str] | None = None,
) -> frozenset[str]:
    """Connected component of `handle` over symmetric equivalence edges.

    An edge counts as "IN" when, if `grounded_in` is supplied, its claim id is a member
    of that grounded extension (the real L3 membership); otherwise (back-compat) when its
    status is LICENSED.
    """
    adj: dict[str, set[str]] = defaultdict(set)
    for eq in equivalences:
        counts = (
            eq.id in grounded_in
            if grounded_in is not None
            else eq.status == Status.LICENSED
        )
        if counts:
            adj[eq.left].add(eq.right)
            adj[eq.right].add(eq.left)
    seen = {handle}
    queue: deque[str] = deque([handle])
    while queue:
        node = queue.popleft()
        for nbr in adj[node]:
            if nbr not in seen:
                seen.add(nbr)
                queue.append(nbr)
    return frozenset(seen)


def are_equivalent(
    a: str,
    b: str,
    equivalences: Iterable[EquivalenceClaim],
    *,
    grounded_in: frozenset[str] | None = None,
) -> bool:
    """Reflexive / symmetric / transitive over IN equivalence edges (see equivalence_class)."""
    return b in equivalence_class(a, equivalences, grounded_in=grounded_in)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd grammar && uv run pytest tests/test_equivalence.py -q`
Expected: PASS (existing equivalence tests + 2 new, all green)

- [ ] **Step 5: Commit**

```bash
cd ~/Desktop/polymer-claims
git add grammar/src/polymer_grammar/equivalence.py grammar/tests/test_equivalence.py
git commit -m "feat(grammar): equivalence gains grounded_in path (replaces LICENSED-only stub)"
```

---

### Task 7: `blame.py` — Duhem blame-set representation + aggregation

**Files:**
- Create: `grammar/src/polymer_grammar/blame.py`
- Test: `grammar/tests/test_blame.py`

- [ ] **Step 1: Write the failing test**

```python
# grammar/tests/test_blame.py
import pytest
from pydantic import ValidationError

from polymer_grammar.blame import (
    BlameAssignment, BlameSet, BlameVerdict, aggregate_blame, duhem_status,
)
from polymer_grammar.status import PendingReason, Status


def test_empty_assignment_rejected():
    with pytest.raises(ValidationError):
        BlameAssignment(targets=())


def test_empty_blameset_rejected():
    with pytest.raises(ValidationError):
        BlameSet(contradiction_id="k", assignments=())


def test_single_assignment_is_fully_robust():
    bs = BlameSet(contradiction_id="k",
                  assignments=(BlameAssignment(targets=("c1", "c2")),))
    v = aggregate_blame(bs)
    assert v.robustly_blamed == frozenset({"c1", "c2"})
    assert v.underdetermined == frozenset()
    assert v.possibly_blamed == frozenset({"c1", "c2"})


def test_overlapping_assignments_split_robust_vs_underdetermined():
    bs = BlameSet(contradiction_id="k", assignments=(
        BlameAssignment(targets=("c1", "c2")),
        BlameAssignment(targets=("c1", "aux:assumptionA")),
    ))
    v = aggregate_blame(bs)
    assert v.robustly_blamed == frozenset({"c1"})                 # in every repair
    assert v.underdetermined == frozenset({"c2", "aux:assumptionA"})
    assert v.possibly_blamed == frozenset({"c1", "c2", "aux:assumptionA"})


def test_disjoint_assignments_all_underdetermined():
    bs = BlameSet(contradiction_id="k", assignments=(
        BlameAssignment(targets=("c1",)),
        BlameAssignment(targets=("c2",)),
    ))
    v = aggregate_blame(bs)
    assert v.robustly_blamed == frozenset()
    assert v.underdetermined == frozenset({"c1", "c2"})


def test_duhem_status_maps_underdetermined_and_robust():
    v = BlameVerdict(
        robustly_blamed=frozenset({"c1"}),
        possibly_blamed=frozenset({"c1", "c2"}),
        underdetermined=frozenset({"c2"}),
    )
    assert duhem_status("c2", v) == (Status.PENDING, PendingReason.DUHEM_UNDERDETERMINED)
    assert duhem_status("c1", v) == (Status.REJECTED, None)
    assert duhem_status("c3", v) is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd grammar && uv run pytest tests/test_blame.py -q`
Expected: FAIL (ModuleNotFoundError: No module named 'polymer_grammar.blame')

- [ ] **Step 3: Write minimal implementation**

```python
# grammar/src/polymer_grammar/blame.py
"""L3 — Duhem–Quine blame-sets (spec §3.5).

When a contradiction arises, blame can fall on any member of a claim/auxiliary bundle
(Duhem). The protocol SUPPLIES the candidate minimal blame-assignments (computing them
is NP-hard and would break PTIME); the grammar only does the tractable set algebra:
intersection = robustly blamed, union = possibly blamed, difference = underdetermined
(-> PENDING duhem_underdetermined). Targets may name claims OR auxiliary assumptions.
"""
from __future__ import annotations

from pydantic import model_validator

from .base import _Model
from .status import PendingReason, Status


class BlameAssignment(_Model):
    targets: tuple[str, ...]  # claim ids OR auxiliary-assumption ids
    note: str | None = None

    @model_validator(mode="after")
    def _nonempty(self) -> "BlameAssignment":
        if not self.targets:
            raise ValueError("a BlameAssignment must name >=1 target")
        return self


class BlameSet(_Model):
    contradiction_id: str
    assignments: tuple[BlameAssignment, ...]

    @model_validator(mode="after")
    def _has_assignment(self) -> "BlameSet":
        if not self.assignments:
            raise ValueError("a BlameSet must carry >=1 minimal blame-assignment")
        return self


class BlameVerdict(_Model):
    robustly_blamed: frozenset[str]   # in EVERY assignment -> robustly defeated / OUT
    possibly_blamed: frozenset[str]   # the union
    underdetermined: frozenset[str]   # union - intersection -> PENDING duhem_underdetermined


def aggregate_blame(blame: BlameSet) -> BlameVerdict:
    """intersection -> robustly_blamed; union -> possibly_blamed; difference -> underdetermined."""
    sets = [frozenset(a.targets) for a in blame.assignments]
    union = frozenset().union(*sets)
    intersection = sets[0]
    for s in sets[1:]:
        intersection = intersection & s
    return BlameVerdict(
        robustly_blamed=intersection,
        possibly_blamed=union,
        underdetermined=union - intersection,
    )


def duhem_status(
    claim_id: str, verdict: BlameVerdict
) -> tuple[Status, PendingReason | None] | None:
    """The (status, reason) the corpus fold should set for `claim_id`, or None if the
    claim is not implicated. Underdetermined -> PENDING duhem; robustly blamed -> REJECTED."""
    if claim_id in verdict.underdetermined:
        return (Status.PENDING, PendingReason.DUHEM_UNDERDETERMINED)
    if claim_id in verdict.robustly_blamed:
        return (Status.REJECTED, None)
    return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd grammar && uv run pytest tests/test_blame.py -q`
Expected: PASS (6 passed)

- [ ] **Step 5: Commit**

```bash
cd ~/Desktop/polymer-claims
git add grammar/src/polymer_grammar/blame.py grammar/tests/test_blame.py
git commit -m "feat(grammar): L3 Duhem blame-sets (represented + aggregated set algebra)"
```

---

### Task 8: Package exports + whole-package verification

**Files:**
- Modify: `grammar/src/polymer_grammar/__init__.py`

- [ ] **Step 1: Write the failing test**

```python
# append to grammar/tests/test_defeat.py
def test_public_api_exports():
    import polymer_grammar as pg

    for name in [
        "DefeatEdge", "DefeatEdgeKind", "effective_defeats", "grounded_extension",
        "derived_rebut_edges", "undermine_edges_from_failed_satisfactions",
        "BlameAssignment", "BlameSet", "BlameVerdict", "aggregate_blame", "duhem_status",
    ]:
        assert hasattr(pg, name), f"{name} not exported from polymer_grammar"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd grammar && uv run pytest tests/test_defeat.py::test_public_api_exports -q`
Expected: FAIL (AssertionError: DefeatEdge not exported from polymer_grammar)

- [ ] **Step 3: Write minimal implementation**

Add to `grammar/src/polymer_grammar/__init__.py` — new imports after the existing block, and new entries in `__all__`:

```python
from .defeat import (
    ATTACK_KINDS,
    DefeatEdge,
    DefeatEdgeKind,
    derived_rebut_edges,
    effective_defeats,
    grounded_extension,
    undermine_edges_from_failed_satisfactions,
)
from .blame import (
    BlameAssignment,
    BlameSet,
    BlameVerdict,
    aggregate_blame,
    duhem_status,
)
```

Add these strings to the `__all__` list:

```python
    "ATTACK_KINDS",
    "DefeatEdge",
    "DefeatEdgeKind",
    "derived_rebut_edges",
    "effective_defeats",
    "grounded_extension",
    "undermine_edges_from_failed_satisfactions",
    "BlameAssignment",
    "BlameSet",
    "BlameVerdict",
    "aggregate_blame",
    "duhem_status",
```

- [ ] **Step 4: Run the whole suite + lint to verify everything passes**

Run: `cd grammar && uv run pytest -q && uv run ruff check src tests`
Expected: PASS — all prior tests (87) + the new defeat/blame/equivalence tests green; ruff clean. Confirm `tests/test_isolation.py` is among the passing tests (no `polymer_formalclaim` import leaked in).

- [ ] **Step 5: Commit**

```bash
cd ~/Desktop/polymer-claims
git add grammar/src/polymer_grammar/__init__.py grammar/tests/test_defeat.py
git commit -m "feat(grammar): export L3 defeat + blame public API"
```

---

## Final integration

- [ ] **Merge to main** (no-ff, per project rhythm):

```bash
cd ~/Desktop/polymer-claims
git checkout main
git merge --no-ff phase5-l3-defeat-blame -m "merge: L3 VAF defeat graph + Duhem blame-sets (Phase 5)"
cd grammar && uv run pytest -q   # verify green on the merged result
git branch -d phase5-l3-defeat-blame
```

- [ ] **Update Progress Log** (below), `docs/superpowers/CONTINUE.md` (Phase 5 ✅, next = Phase 6 L4), the root README phase table, and memory `project_polymer_claims_knowledge_protocol`.

---

## Progress Log

_(Update after every completed task: check the box, note the commit SHA + any decisions.)_

- [x] Task 1 — DefeatEdge type + edge kinds — `d30aafb`
- [x] Task 2 — effective_defeats (Pareto value filter) — `ac1e838` + fix `059402f` (top-level test imports, equal-strength test)
- [x] Task 3 — grounded_extension (PTIME least fixpoint) — `b274b88` + fix `8d19c1a` (review caught a forked 2nd defeat predicate → corrected to single effective-defeat relation; tests use standing attacks + value-filter case)
- [x] Task 4 — derived_rebut_edges (opt-in, L1 incompatible_with) — `0cf57eb` + fix `6b0a87b` (unmatched-target + no-conclusion branch tests)
- [x] Task 5 — failed-satisfaction → undermine adapter — `7a6ae6e`
- [x] Task 6 — equivalence grounded_in rerouting — `143fbeb` + fix `1de6d55` (stale module docstring + status-override test)
- [x] Task 7 — blame.py (BlameSet + aggregate_blame + duhem_status) — `cb4f147`
- [x] Task 8 — exports + whole-package verify — `8aca3bd` + `ff29036` (guard ATTACK_KINDS)
- [x] Final — merged `--no-ff` to main (`1cb0b88`), 117 tests green + ruff clean on merged result, branch deleted; opus final review = READY TO MERGE (no critical/important issues). Docs + memory updated.
