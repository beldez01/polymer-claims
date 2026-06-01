# L1 — Molecular Proposition + Equivalence (Phase 2 Spec)

Date: 2026-06-01
Status: Phase spec for review
Refines: `2026-05-31-unified-claim-foundations-spec.md` §3.2 (SEMANTICS / L1).
Builds on: Phase 1 (`grammar/` package, merged `8ffb666`) — uses the frozen, now-hashable `_Model`, `Status`, `PendingReason`, and `Claim`.

---

## 0. What this phase is

Phase 1 gave claims an empirical anchor (L0 leaf), a pattern, a strength vector, and a status. It did **not** give the *conclusion* a typed identity. Right now two claims asserting the same thing are only relatable by byte-equality — which the grammar keystone explicitly rejects (Halvorson 2012: theoretical equivalence cannot be defined by structural/hash identity).

**L1 makes the conclusion a *molecular Proposition*** (Dummett): typed content **plus** a bounded, version-pinned *inferential neighborhood* (its material-incompatibility / consequence links to other propositions). And it makes **"same claim?" an asserted, defeasible question** — answered by whether a *licensed equivalence* holds, never by a hash. The byte-hash survives only as a dedup/cache key.

Two design forks were resolved before writing this (user-confirmed 2026-06-01):
- **Equivalence = a lightweight first-class `EquivalenceClaim`** (proposition refs + severity + defeasible status), *not* a full meta-Claim. Promotable later once "subject = set of claims" exists.
- **Conclusion typing stays minimal** (direction + estimand-ref + descriptor + neighborhood); full subject + typed-role modeling is a separate later phase.

### Success criterion (inherited)
- **Sensitivity:** the conclusion can carry its real inferential commitments (what it rules out, what it entails), not just a flat statement.
- **Specificity:** identity is an *asserted, contestable* relation, so the schema never silently declares two differently-meant claims "the same" (or two same-meant claims different) on a structural accident.

### Distinction to keep clear
The L1 **inferential neighborhood** (`incompatible_with` / `entails`) is about *meaning* (Brandom/Dummett material inference between propositions). It is **not** the L3 evidential **defeat graph** (`undermine/undercut/rebut/reclassify/reinterpret` between claims). L1 = semantic content; L3 = evidential standing. They are separate layers and separate edge vocabularies.

---

## 1. Primitives

### 1.1 `Proposition` (the molecular conclusion content)

```
Direction        = positive | negative | null
NeighborEdgeKind = incompatible_with | entails        # material inference; NOT L3 defeat

NeighborEdge = { kind: NeighborEdgeKind, target: str, label: str | None }
   # target = the content_hash of another Proposition (a stable, computable handle)

Proposition = {
    direction:   Direction,
    estimand:    str,                       # names the estimand (ideally a registered pattern's estimand)
    descriptor:  str,                       # the typed-but-natural conclusion statement
    neighborhood: tuple[NeighborEdge, ...] = ()   # bounded, version-pinned inferential links
}
```

Two derived handles (computed, deterministic — **not** identity, per the design):
- `content_hash` — sha256 over canonical JSON of `{direction, estimand, descriptor}` (sorted keys). Dedup/cache key.
- `neighborhood_hash` — sha256 over the canonical, **order-independent** serialization of the neighborhood edge set. Pins the inferential-neighborhood version; changes iff the neighborhood changes.

`Proposition` is frozen (inherits `_Model`) → immutable + hashable. `neighborhood` is a tuple (deep-immutable, per the F1 hardening).

### 1.2 `EquivalenceClaim` (lightweight, first-class, defeasible)

```
EquivalenceClaim = {
    id:             str,
    left:           str,                    # a Proposition content_hash
    right:          str,                    # a Proposition content_hash
    severity:       float in [0, 1],        # graded confidence of coreference
    status:         Status,                 # defeasible: CONJECTURED..LICENSED/REJECTED
    pending_reason: PendingReason | None = None,
    note:           str | None = None,
}
```
Invariants (model validators, mirroring `Claim`):
- `left != right` (an equivalence to self is meaningless → `ValueError`).
- the same PENDING↔reason lifecycle invariant as `Claim` (PENDING requires a reason; non-PENDING forbids one).

### 1.3 Equivalence resolution (the "same claim?" answer)

Pure functions over a collection of `EquivalenceClaim`s — identity is *computed from asserted, licensed edges*, never from hashes:

```
equivalence_class(handle: str, equivalences) -> frozenset[str]
    # connected component of `handle` over the SYMMETRIC graph of equivalence
    # edges whose status == LICENSED (transitive closure). The component IS the
    # equivalence_class_id material (used later by the protocol's CANONICALIZE).

are_equivalent(a: str, b: str, equivalences) -> bool
    # b in equivalence_class(a, equivalences)   (reflexive, symmetric, transitive)
```
Only `LICENSED` equivalence edges count as "IN" for this phase (a stand-in for L3 grounded-extension membership, which arrives with the VAF layer). CONJECTURED/PENDING/REJECTED equivalences do **not** merge classes.

### 1.4 Wiring into `Claim`

Add one **optional, additive** field (keeps all 34 Phase-1 tests green; a later phase tightens it to required once every construction path supplies a conclusion):

```
Claim.conclusion: Proposition | None = None
```

No other `Claim` change. The neighborhood lives on the Proposition; equivalence lives in standalone `EquivalenceClaim`s — `Claim` gains no relations list in this phase.

---

## 2. Module layout (additive to `grammar/`)

```
grammar/src/polymer_grammar/
  proposition.py     # Direction, NeighborEdgeKind, NeighborEdge, Proposition (+ content_hash, neighborhood_hash)
  equivalence.py     # EquivalenceClaim, equivalence_class(), are_equivalent()
  claim.py           # MODIFY: add conclusion: Proposition | None = None
  __init__.py        # MODIFY: export the new names
tests/
  test_proposition.py
  test_equivalence.py
  test_claim_conclusion.py   # the conclusion wiring + back-compat
```

Isolation rule still enforced by the existing `test_isolation.py` (no `polymer_formalclaim` import).

---

## 3. Acceptance criteria

- A `Proposition` builds with content + neighborhood; `content_hash` is stable across rebuilds and independent of neighborhood; `neighborhood_hash` is order-independent (same edges in any order → same hash) and changes when an edge is added.
- `Proposition` is hashable and immutable (tuple neighborhood rejects in-place mutation).
- An `EquivalenceClaim` rejects `left == right`; enforces the PENDING↔reason invariant.
- `equivalence_class` returns the transitive component over LICENSED edges only; PENDING/REJECTED edges don't merge; `are_equivalent` is reflexive/symmetric/transitive over that set.
- `Claim` accepts an optional `conclusion`; **all existing Phase-1 tests still pass** (back-compat).
- Full suite green; ruff clean; isolation guard still passes.

---

## 4. Non-goals (this phase)

- **Not** a full meta-Claim equivalence (deferred until "subject = set of claims" exists).
- **Not** subject refs / typed role slots in the conclusion (separate later phase).
- **Not** the L3 VAF defeat graph — neighborhood edges here are *material-inference* (meaning), not evidential defeat; "IN" is stubbed as `status==LICENSED` until L3 lands.
- **Not** making `conclusion` required (additive/optional now; tightened later).
- **Not** auto-deriving neighborhood edges or equivalences — both are authored/asserted in this phase.

---

## 5. Connections to library

- Realizes unified spec §3.2 (L1) + the schema-overview L1 panel.
- `equivalence_class` produces the `equivalence_class_id` the protocol's CANONICALIZE stage (knowledge-generation protocol §Stage 2) will consume.
- Feeds the (later) L3 VAF layer, which will replace `status==LICENSED` with true grounded-extension "IN" membership.
- Plan: `docs/superpowers/plans/2026-06-01-L1-proposition-equivalence.md` (next).
