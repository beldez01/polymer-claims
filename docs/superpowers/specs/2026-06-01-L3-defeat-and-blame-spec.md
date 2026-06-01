# Phase 5 — L3: VAF defeat graph + Duhem blame-sets — design spec

Date: 2026-06-01
Status: design (feeds `writing-plans`)
Layer: L3 (CORPUS) of the v1.3 grammar — see unified spec §3.5
Depends on: Phases 1–4 (`status`, `strength`, `proposition`/`equivalence`, `claim`)

## 1. Goal

Add the **corpus-level layer**: a value-based defeat graph over claims whose **grounded
extension** says which claims are currently *IN* (accepted), and a **Duhem–Quine blame-set**
representation that surfaces under-determined contradictions instead of laundering them into a
single verdict. This replaces the L1 stop-gap where equivalence "IN-ness" was `status==LICENSED`.

Two empirical anchors from the v1.2 ingestion probe (`2026-06-01-v12-ingestion-findings.md`):
all 47 claims carry `external_assumptions` (typed Duhem auxiliaries) and `depends_on` — exactly
the auxiliary + inter-claim structure this layer represents. So blame targets must be able to
name **auxiliary assumptions**, not only claims.

Like `equivalence.py`, this is a **corpus-level module of graph functions over an iterable of
edges**, not fields bolted onto `Claim`. Nothing here imports `polymer_formalclaim` (isolation
guard holds); all models are frozen, `extra="forbid"`, collections are tuples.

## 2. New module `grammar/defeat.py`

### 2.1 Edge kinds

```python
class DefeatEdgeKind(str, Enum):
    UNDERMINE   = "undermine"    # attacks a premise / the data basis
    UNDERCUT    = "undercut"     # attacks the inferential warrant (premise→conclusion link)
    REBUT       = "rebut"        # asserts the contrary conclusion
    RECLASSIFY  = "reclassify"   # disputes the pattern/profile applied (not the analytic/synthetic line)
    REINTERPRET = "reinterpret"  # meaning moved, statistics unchanged (spec §5.6; distinct from undercut)
    EVIDENCE_FOR = "evidence_for"  # SUPPORT, never a defeat — excluded from the attack relation
```

`UNDERMINE | UNDERCUT | REBUT | RECLASSIFY | REINTERPRET` are **attacks**. `EVIDENCE_FOR` is
support, recorded for provenance/strength but never contributes to defeat.

### 2.2 The edge

```python
class DefeatEdge(_Model):           # frozen, extra="forbid", hashable
    source: str                     # claim id (the attacker / supporter)
    target: str                     # claim id (the attacked / supported)
    kind: DefeatEdgeKind
    note: str | None = None
    # invariant: source != target (no self-defeat / self-support)
```

### 2.3 Effective defeat — the VAF value filter (fork A: strength-mediated)

A raw attack edge becomes an **effective defeat** only if the target does **not**
strength-dominate the source, using the Phase-4 `StrengthVector.dominates` partial order:

```
attack A → B is an EFFECTIVE DEFEAT  ⇔  NOT ( strength(B) dominates strength(A) )
```

- target strictly stronger on all axes (`strength(B).dominates(strength(A))`) → attack **fails**
  (the better-supported claim resists the weaker attacker).
- source dominates target, **or strengths are incomparable, or either claim has no strength
  vector** → attack **stands** (incomparability/absence is not a proof of the target's
  superiority, so the attack is not filtered out). This is the conservative, no-hidden-scalar
  reading consistent with the Pareto design.

`evidence_for` edges are never defeats regardless of strength.

```python
def effective_defeats(
    edges: Iterable[DefeatEdge],
    strength: Mapping[str, StrengthVector | None],
) -> frozenset[tuple[str, str]]:
    """(source, target) pairs that survive the value filter."""
```

### 2.4 Grounded extension

Standard Dung grounded extension over the **effective-defeat** relation: least fixpoint of the
characteristic function `F(S) = { a | every attacker of a is attacked by some member of S }`,
starting from ∅. PTIME (monotone `F`, at most |claims| iterations). Grounded extension is unique
and always exists.

```python
def grounded_extension(
    claim_ids: Iterable[str],
    edges: Iterable[DefeatEdge],
    strength: Mapping[str, StrengthVector | None],
) -> frozenset[str]:
    """The IN set: claims accepted under grounded semantics over effective defeats."""
```

Isolated/unattacked claims are always IN. (PTIME holds for any finite graph; the unified spec's
"bounded defeat in-degree" write-time cap is a *status-recompute monotonicity* hardening, **not**
required for grounded extension itself — deferred to a later tightening phase, §7.)

### 2.5 Auto-derived rebut from L1 neighborhoods (fork C: opt-in helper)

A pure helper, **not** invoked implicitly by `grounded_extension`, so the L1↔L3 coupling is
explicit at the call site:

```python
def derived_rebut_edges(claims: Iterable[Claim]) -> tuple[DefeatEdge, ...]:
    """Mutual `rebut` edges between LICENSED claims whose `conclusion` Propositions are
    mutually material-incompatible (an `incompatible_with` NeighborEdge resolving between
    their content_hashes). Caller merges these with authored edges before grounded_extension."""
```

Reads the L1 `Proposition.neighborhood` (`incompatible_with`). Only LICENSED↔LICENSED pairs;
emits a symmetric pair of `rebut` edges. Authored edges always take precedence on dedup.

### 2.6 Equivalence rerouting (replaces the L1 LICENSED-only stub)

`equivalence.py` gains a grounded-aware path, additively and back-compatibly:

```python
def equivalence_class(handle, equivalences, *, grounded_in: frozenset[str] | None = None): ...
def are_equivalent(a, b, equivalences, *, grounded_in: frozenset[str] | None = None): ...
```

- `grounded_in is None` (default): current behavior — an edge counts iff `eq.status == LICENSED`.
- `grounded_in` supplied (the grounded extension, with `EquivalenceClaim.id`s as nodes): an edge
  counts iff `eq.id in grounded_in`. This is the real "IN-ness" the L1 docstring promised. No
  signature break for existing callers.

## 3. Duhem–Quine blame-sets (fork B: represented + aggregated)

The grammar does **not** solve for minimal blame-assignments (NP-hard; would break PTIME). The
protocol/agent *supplies* candidate minimal blame-assignments; the grammar computes only the
tractable set aggregation.

```python
class BlameAssignment(_Model):       # one minimal repair: retracting these resolves the conflict
    targets: tuple[str, ...]         # claim ids OR auxiliary-assumption ids (ingestion refinement)
    note: str | None = None
    # invariant: targets non-empty

class BlameSet(_Model):              # all minimal blame-assignments for ONE contradiction
    contradiction_id: str
    assignments: tuple[BlameAssignment, ...]
    # invariant: >=1 assignment

class BlameVerdict(_Model):
    robustly_blamed: frozenset[str]    # in EVERY assignment   → robustly defeated / OUT
    possibly_blamed: frozenset[str]    # in the UNION
    underdetermined: frozenset[str]    # union − intersection  → PENDING duhem_underdetermined
```

```python
def aggregate_blame(blame: BlameSet) -> BlameVerdict:
    """intersection → robustly_blamed; union → possibly_blamed; difference → underdetermined."""
```

- one assignment → intersection = union → everything robustly blamed, nothing underdetermined
  (Duhem resolved: unique culprit).
- disjoint assignments → intersection ∅ → everything underdetermined (blame cannot be localized).

A small fold applies the verdict to claim statuses (a claim in `underdetermined` → `PENDING` with
`PendingReason.DUHEM_UNDERDETERMINED`, which already exists in `status.py`):

```python
def duhem_status(claim_id: str, verdict: BlameVerdict) -> tuple[Status, PendingReason | None] | None:
    """None if the claim isn't implicated; else the (status, reason) the corpus fold should set."""
```

## 4. Carried-forward from L2: where failed licensing attempts live

A refuted/undetermined `Satisfaction` (L2) must not be silently dropped. Adapter turns it into a
first-class `undermine` edge attacking the claim's empirical basis:

```python
def undermine_edges_from_failed_satisfactions(
    claim_id: str, satisfactions: Iterable[Satisfaction]
) -> tuple[DefeatEdge, ...]:
    """For each refuted/undetermined Satisfaction, an `undermine` edge
    source=f'refutation:{ctx.id}', target=claim_id, note=verdict+context."""
```

So failed licensing surfaces in the same defeat graph as everything else.

## 5. Module boundaries / what each unit does

- `defeat.py` — edge type + `effective_defeats` + `grounded_extension` + `derived_rebut_edges` +
  the L2 failed-satisfaction adapter. Pure functions over data; no `Claim` mutation.
- `blame.py` — `BlameAssignment`/`BlameSet`/`BlameVerdict` + `aggregate_blame` + `duhem_status`.
  (Kept separate from `defeat.py`: blame aggregation is set algebra over supplied repairs, not
  graph traversal. Distinct purpose, distinct file.)
- `equivalence.py` — gains the optional `grounded_in` kwarg only.
- No new fields on `Claim` in this phase (the graph is corpus-level, mirroring equivalence).

## 6. Testing (TDD — failing test first, per task)

- `effective_defeats`: target-dominates-source filters the attack; source-dominates / incomparable
  / missing-strength all let it stand; `evidence_for` never defeats.
- `grounded_extension`: unattacked → IN; A↔B mutual effective defeat (no dominance) → neither IN
  (classic); **reinstatement**: C→A, A→B with C unattacked → grounded = {C, B} (A is OUT, so B is
  reinstated); empty graph → ∅; self-loop rejected at `DefeatEdge` construction.
- `derived_rebut_edges`: LICENSED pair with mutual `incompatible_with` → symmetric rebut; non-
  LICENSED or no incompatibility → none.
- `equivalence` rerouting: default path unchanged (back-compat test stays green); `grounded_in`
  path drops an edge whose `eq.id` is OUT even if `status==LICENSED`.
- `aggregate_blame`: single / disjoint / overlapping assignments → correct intersection/union/diff;
  `duhem_status` flags underdetermined → PENDING+DUHEM_UNDERDETERMINED.
- failed-satisfaction adapter: refuted/undetermined → undermine edge; satisfied → none.
- isolation guard still passes; all new models frozen + hashable.

## 7. Follow-ups (tracked, none blocking)

- **Auxiliary assumptions as first-class nodes.** Blame targets are opaque ids now; representing
  `external_assumption` as a real grammar node (so blame and `undercut` can point at a typed
  auxiliary with its own confidence) is the natural next step — strongly indicated by the
  ingestion finding that all 47 claims carry them. Likely folds into Phase 7 provenance or a
  dedicated mini-phase.
- **Bounded defeat in-degree** write-time cap (status-recompute monotonicity) — deferred hardening.
- **VAF audiences / value-orderings beyond Pareto** — current "value" is the single Pareto strength
  order; named-audience value-orderings (logged dictatorship policy from §3.5) deferred.
- Off-roadmap gaps from ingestion (no `Claim.subject` slot; vector-valued `Leaf`) remain queued
  after L3.

## 8. Out of scope

L4 AGM/TMS revision (Phase 6); protocol-imposed provenance fields (Phase 7); the evaluator
(Phase 8); pattern-inference for raw claims; the subject slot and vector leaf.
