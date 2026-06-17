# M1 — structural equivalence gets an honest status (`Status.STRUCTURAL`)

> **Status:** design spec, 2026-06-11. Slice 1a of the credibility-arc roadmap
> (`docs/superpowers/roadmaps/2026-06-11-credibility-arc-roadmap.md`). Closes the "beat a
> criterion" gap's cheapest leg: a `LICENSED` edge that never passed a criterion.
> **Status: shipped to `main`.** This is the design record; live build state + test counts in `docs/superpowers/CONTINUE.md`.

## Problem

`canonicalize` (`protocol/src/polymer_protocol/canonicalize.py:53–86`) collapses structurally
identical claims by minting an equivalence edge:

```python
EquivalenceClaim(
    id=f"struct-eq:{rep}:{other}",
    left=rep, right=other,
    severity=1.0,                 # exact structural identity
    status=Status.LICENSED,       # ← the problem
    note="structural-key collapse",
)
```

The structural identity is real — two claims share a structural key, so they are identical *by
construction*. But stamping the edge `LICENSED` reuses the exact word the evidential pipeline
*earns* through `verify_stage` (a severe-test / replication-grade `(σ, M)` satisfaction). Under the
system's core invariant — **LICENSED means a real, fully-pinned analysis beat a pre-registered
criterion** — this is a false-license path: a `LICENSED` artifact that passed no criterion at all.

The confusion is not academic. The moment a consumer reasons over "the licensed edges," it
conflates *evidentially licensed* with *structurally identical* — two different epistemic acts
wearing one label.

## Why a third status (not LICENSED, not CONJECTURED)

A structural-key collapse is neither:

- **not `LICENSED`** — it passed no evidential test; `EquivalenceClaim` has no `licensing` block to
  carry one, so its `LICENSED` already meant something different from a `Claim`'s `LICENSED`. That
  silent divergence is precisely what we are removing.
- **not `CONJECTURED`** — it is not an unverified guess. It is verified *by construction* (identical
  structural keys), with `severity=1.0`. Labeling it `CONJECTURED` would be as dishonest in the
  other direction, and would leave the edge inert (see "back-compat gate" below).

So it earns its own status: **`STRUCTURAL`** — *true by construction; not an evidential license.*

## Current consumers (blast radius)

Verified read of the repo as of 2026-06-11:

- `equivalence_class` / `are_equivalent` (`grammar/.../equivalence.py:50–91`) gate an edge as "IN"
  on `status == Status.LICENSED` in their back-compat path (when `grounded_in` is not supplied).
  **These functions have no live callers** inside grammar / protocol / umbrella beyond the
  `__init__` re-export — the back-compat gate is currently **dormant**. The fix must still keep it
  *correct* for the day a consumer arrives.
- `topology.py:131–137` emits **every** equivalence as an edge regardless of status; the viewer
  colors equivalence edges by **edge-kind** (`EDGE_COLOR.equivalence = '#A1A1AA'`, neutral gray,
  `viewer/src/config/theme.ts:142`), never by the equivalence's status.
- `corpus.py:60` checks only **referential integrity** of equivalence endpoints — no status filter.
- No other site filters `corpus.equivalences` by status.

Net: relabeling the minted edge breaks **no running consumer**. This is a semantics fix with a tiny
surface.

## Design

Additive only. No new `Corpus` collection, no new fields, no protocol public-API change. Grammar
one-way isolation preserved.

### 1. Grammar — new `Status.STRUCTURAL`

`grammar/src/polymer_grammar/status.py` — add one enum member:

```python
class Status(str, Enum):
    CONJECTURED = "conjectured"
    EXPLORATORY = "exploratory"
    PENDING = "pending"
    LICENSED = "licensed"
    REJECTED = "rejected"
    STRUCTURAL = "structural"   # true by construction (e.g. a structural-key equivalence);
                                # NOT an evidential license. Valid only on EquivalenceClaim.
```

### 2. Grammar — fence `STRUCTURAL` out of `Claim`

`Status` is shared by `Claim` and `EquivalenceClaim`. A *Claim* is never "true by construction"
(its truth is exactly what the pipeline tests), so a `Claim` carrying `status=STRUCTURAL` is
meaningless and must be rejected. Add a validator to `Claim` (`claim.py`, alongside
`_pending_reason_iff_pending` / `_licensing_only_when_licensed`):

```python
@model_validator(mode="after")
def _structural_only_on_equivalence(self) -> "Claim":
    if self.status == Status.STRUCTURAL:
        raise ValueError(
            "status=STRUCTURAL is valid only on an EquivalenceClaim "
            "(a Claim is never true by construction); got a Claim"
        )
    return self
```

`EquivalenceClaim` accepts `STRUCTURAL` with no change — its `_pending_reason_iff_pending` validator
already tolerates any non-`PENDING` status, and `_distinct_endpoints` is orthogonal.

### 3. Grammar — keep the collapse effective in `equivalence_class`

Broaden the dormant back-compat IN gate (`equivalence.py:64–68`) so a structural edge still merges
its endpoints when a future consumer computes equivalence classes:

```python
counts = (
    eq.id in grounded_in
    if grounded_in is not None
    else eq.status in (Status.LICENSED, Status.STRUCTURAL)
)
```

The `grounded_in` (real L3 membership) path is unchanged. Rationale: a structural identity *should*
make its endpoints the same handle — that is the whole point of the collapse — independent of any
evidential license. The docstring updates to name both IN statuses.

### 4. Protocol — mint `STRUCTURAL`

`canonicalize.py:78` — change `status=Status.LICENSED` to `status=Status.STRUCTURAL`. `severity=1.0`,
`id`, `note` unchanged. One-line change; the only behavioral edit in the protocol package.

### 5. Tests

- **Update** existing assertions that expect the minted `LICENSED`:
  `protocol/tests/test_canonicalize.py`, `protocol/tests/test_cycle.py`.
- **Add** (grammar):
  - a `Claim` constructed with `status=STRUCTURAL` raises `ValidationError`;
  - an `EquivalenceClaim` with `status=STRUCTURAL` is valid;
  - `equivalence_class` / `are_equivalent` count a `STRUCTURAL` edge as IN (back-compat path,
    `grounded_in=None`); a `CONJECTURED` edge still does **not**.
- **Add** (protocol):
  - `canonicalize` mints `status=STRUCTURAL` (not `LICENSED`) for a structural collapse;
  - the collapse is otherwise unchanged (same ids, same `severity=1.0`, same dedup against
    `existing_pairs`).

## Deliberate non-changes (fences)

- **Viewer + `CONTRACT_VERSION` untouched.** Equivalence edges are colored by edge-kind, not status;
  and because `STRUCTURAL` is fenced out of `Claim`, it never appears as a *node* status, so
  `STATUS_COLOR` needs no new key and the topology contract version does not move. (If a future
  slice ever surfaces equivalence status in the UI, add the key then.)
- **`topology.py` untouched** — it already emits all equivalences regardless of status.
- **`Corpus` stays 4 collections**; no new fields anywhere; grammar imports nothing new from
  protocol; isolation guard unaffected.
- **No change to how equivalences are *created* elsewhere** — only `canonicalize`'s structural
  collapse mints `STRUCTURAL`. An evidentially-asserted equivalence (Halvorson identity) would still
  be `LICENSED` via its own (future) evidential route.

## Risks & mitigations

- **A future consumer that treats `STRUCTURAL` as a full license.** Mitigated by the name and the
  fence: `STRUCTURAL` is distinct from `LICENSED` at the type level, so any consumer must opt in to
  counting it (as `equivalence_class` now explicitly does, with a documented rationale).
- **Serialized corpora on disk with `status="licensed"` struct-eq edges.** None are persisted as
  canonical fixtures that assert this (the viewer sample fixtures are claim-node topologies, not raw
  corpora). If any are found during implementation, regenerate them — note it in the plan's Progress
  Log.

## Acceptance

- `canonicalize` mints `Status.STRUCTURAL` for structural collapses; no path mints a `LICENSED`
  equivalence without an evidential test.
- A `Claim` cannot be `STRUCTURAL`; an `EquivalenceClaim` can.
- `equivalence_class` still merges structural-edge endpoints.
- Full suite green (grammar + protocol + umbrella), ruff clean, isolation guard green, viewer
  typecheck/build unaffected (`bash scripts/check-all.sh` → ALL GREEN).
