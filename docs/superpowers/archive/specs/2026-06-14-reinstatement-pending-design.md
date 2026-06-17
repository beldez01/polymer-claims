# Reinstatement → PENDING — the symmetric counterpart to defeat-as-de-license

> **Design spec, 2026-06-14.** Phase-2 arc-1 follow-on (Tier-1 safe slice from
> `docs/superpowers/2026-06-13-overnight-deferred-analysis.md`). Phase 2.2 made a *successful defeat*
> de-license a claim *through the ledger*. This is its mirror: when the **attacker** is itself later
> defeated, grounded semantics reinstates the original claim — and we reopen it to **PENDING so it
> re-tests** (never auto-relicense a possibly-stale license).
>
> **Status: shipped to `main`.** This is the design record; live build state + test counts in `docs/superpowers/CONTINUE.md`.

## Problem

Phase 2.2 (`integrate.py`): a LICENSED claim A that is grounded-OUT this cycle (its attacker B became
effective) flips to **REJECTED** and its e-LOND discovery is tombstoned. But argumentation is symmetric:
if B is *itself* later defeated, grounded semantics **reinstates** A (A re-enters the grounded
extension). Today nothing acts on that — A stays REJECTED forever, even though the corpus now accepts it.

Two gaps block the fix:

1. **REJECTED is undifferentiated.** Three code paths set `Status.REJECTED`, all with no recorded cause:
   - `integrate.py:_reject` — defeat-rejection (grounded-OUT) → **reinstatable**.
   - `verify.py` — `agreed_refuted` (data refuted it) → **terminal**; OR `c.id not in in_ext`
     (grounded-OUT at verify) → **reinstatable**.
   - the Duhem robust-blame verdict (`blame.py:duhem_status`) → **terminal**.

   Without a marker, reinstatement can't tell a *defeated* claim (reopen it) from a *refuted* one
   (leave it). This is load-bearing, not cosmetic: `grounded_extension` is **status-blind**, so a
   refuted claim with **no attackers** sits in the grounded `in_set` *every* cycle — a structural-only
   reinstatement rule would reopen refuted claims forever.

2. **No reinstatement pass.** Nothing scans for REJECTED claims that re-entered the grounded extension.

## Decision

- **Re-test, not auto-relicense** (the deferred-analysis fork, decided). A reinstated claim reopens to
  PENDING; Phase-2.4's live-dedup then lets it re-license *on current data* in a later cycle. Restoring
  the old `Licensing` would be unsound — its materialization may have drifted since rejection.
- **Mark the rejection cause in the grammar; decide reinstatability in the protocol** (the project's
  "grammar represents, protocol decides" principle). A `RejectionReason` enum records *why*; the
  reinstatement pass keys only on `DEFEAT_GROUNDED_OUT`.

## Approach (chosen: A)

- **A (chosen) — `RejectionReason` enum + a reinstatement block in INTEGRATE** mirroring the Phase-2.2
  `flipped_out → reject` block, using the same `restore_consistency` result.
- **B — structural-only, no marker.** Rejected: refuted-but-unattacked claims live in `in_set`
  permanently → spurious perpetual reopen.
- **C — auto-relicense (restore old `Licensing`).** Rejected: unsound against a possibly-drifted
  materialization; violates the content-address discipline. Re-test is the honest path.

## Components

### Grammar (pure, additive — `grammar/src/polymer_grammar/`)

- `RejectionReason(str, Enum)` in `status.py`: `DEFEAT_GROUNDED_OUT`, `REFUTED`, `ROBUSTLY_BLAMED`.
- `PendingReason` gains one value: `REINSTATED` (the reopened-to-PENDING state; symmetric to the drift
  daemon's `MATERIALIZATION_DRIFTED`).
- `Claim.rejection_reason: RejectionReason | None = None` (additive-optional) + a validator
  `_rejection_reason_only_when_rejected`: raises if a **non-REJECTED** claim carries a
  `rejection_reason`. **One-directional** (`rejection_reason ⟹ REJECTED`), NOT an iff — a REJECTED claim
  may still carry `None`, so every existing REJECTED-claim construction stays valid (hard "REJECTED
  requires a reason" tightening is deferred, per the repo's additive-fields invariant).

### Protocol (pure — `protocol/src/polymer_protocol/`)

**Stamp the cause at each rejection site** (additive `rejection_reason=` on the existing `model_copy`/
`_with_status`/`_reject` updates; default-None elsewhere keeps everything byte-identical):

- `integrate.py:_reject` → `rejection_reason=RejectionReason.DEFEAT_GROUNDED_OUT`.
- `verify.py` — **split** the current `elif agreed_refuted or c.id not in in_ext:` into two arms, with
  **refutation taking precedence** (if both hold, the data refuted it → terminal):
  - `agreed_refuted` ⇒ REJECTED, `rejection_reason=REFUTED`.
  - else `c.id not in in_ext` ⇒ REJECTED, `rejection_reason=DEFEAT_GROUNDED_OUT`.
- the Duhem robust-blame REJECTED verdict ⇒ `rejection_reason=ROBUSTLY_BLAMED` (terminal; stamped for
  legibility — reinstatement never keys on it). *Plan note:* locate where `duhem_status`'s
  `(REJECTED, …)` verdict is applied to claims and stamp there; if that consumer is absent/awkward,
  leaving robust-blame `None` is safe (still non-reinstatable) and the value-stamping is a trivial
  follow-up.

**Reinstatement block in `integrate.py`** (immediately alongside the existing `flipped_out` de-license
block, sharing `rr = restore_consistency(...)`):

```
reinstated = {
    c.id for c in rr.claims
    if c.id in rr.flipped_in                 # OUT→IN this cycle (in_set \ prior_in)
    and c.status == Status.REJECTED
    and c.rejection_reason == RejectionReason.DEFEAT_GROUNDED_OUT
    and c.evaluation_plan is not None        # has-plan gate (mirror drift's require_plan)
}
```

Reopen each atomically (mirroring `drift.reopen_drifted`):
`model_copy(update={status→PENDING, licensing→None, pending_reason→REINSTATED, rejection_reason→None})`
then re-validate (`Claim.model_validate(...)`, as `_reject`/`_with_status` already do). The de-license
and reinstatement sets are disjoint (`flipped_out` vs `flipped_in`), so both can be applied in one pass
over `rr.claims`.

**Ledger:** no new `retract_tests` call on reinstatement — A's e-LOND test was already tombstoned when
it was defeat-rejected (Phase 2.2), so it carries no *live* discovery. On reopen to PENDING, Phase-2.4's
`already_tested` dedup (keyed on non-retracted tests) grants A a **fresh** e-test when it re-executes.

### Out of scope (deferred)

- Reinstating a claim rejected by **refutation** or **robust blame** (terminal by decision).
- Reinstating **non-LICENSED** defeat-rejected claims that never had a plan (the has-plan gate skips
  them — a planless PENDING claim could never self-relicense, identical to drift's reasoning).
- Live-node surfacing of reinstatement (the integrate pass runs inside `run_cycle`, so the live node
  gets it for free; no viewer annotation in this slice).

## Invariants preserved

- grammar + protocol **pure + numpy-free**; **Corpus = 4 collections** (the marker rides the existing
  `Claim`; no new IR entity).
- **Back-compat:** `rejection_reason` defaults None → byte-identical for every claim not rejected by
  defeat; the new `PendingReason`/`RejectionReason`/`Status` enums are additive.
- **`LICENSED ⇒ a live e-LOND discovery`** holds across reinstatement (a reopened PENDING claim has no
  live discovery; it earns a fresh one only if it re-licenses).
- §2E / `independence_tier` and all prior phases untouched.

## Acceptance criteria

1. A claim A defeated by an effective attacker B is REJECTED with `rejection_reason=DEFEAT_GROUNDED_OUT`;
   when B is itself defeated, the next `run_cycle` reopens A to **PENDING** (`pending_reason=REINSTATED`,
   `rejection_reason=None`), and A **re-licenses** in a subsequent cycle (re-testing on current data).
2. A **refuted** claim (`rejection_reason=REFUTED`) that structurally sits in the grounded `in_set` is
   **NOT** reopened — the correctness guard against status-blind reinstatement.
3. A defeat-rejected claim with **no `evaluation_plan`** is not reopened (would strand).
4. Grammar: `rejection_reason` is rejected by the validator on a non-REJECTED claim; a REJECTED claim
   with `rejection_reason=None` still validates (back-compat).
5. `run_cycle` with no reinstatement opportunity is byte-identical to today; all existing
   grammar/protocol/umbrella suites stay green; `scripts/check-all.sh` ALL GREEN.
6. grammar/protocol pure + numpy-free; Corpus = 4; the de-license and reinstatement sets stay disjoint.

## Anchored file map (for the plan)

- `grammar/src/polymer_grammar/status.py` — `RejectionReason` enum, `PendingReason.REINSTATED`.
- `grammar/src/polymer_grammar/claim.py` — `Claim.rejection_reason` field + `_rejection_reason_only_when_rejected`
  validator (model after `_pending_reason_iff_pending` at ~`:47`).
- `grammar/src/polymer_grammar/__init__.py` — export `RejectionReason`.
- `protocol/src/polymer_protocol/integrate.py` — stamp `DEFEAT_GROUNDED_OUT` in `_reject`; add the
  reinstatement block beside the `flipped_out` block (`~:50-62`).
- `protocol/src/polymer_protocol/verify.py` — split the `agreed_refuted or not in_ext` branch (`~:230`),
  stamping `REFUTED` vs `DEFEAT_GROUNDED_OUT`.
- the Duhem robust-blame REJECTED consumer — stamp `ROBUSTLY_BLAMED` (locate in plan;
  `grammar/.../blame.py:duhem_status` returns the verdict).
- Reference precedents: `protocol/.../drift.py:reopen_drifted` (the reopen template),
  `docs/specs/2026-06-12-phase-2-2-defeat-evalue-refund-design.md` (the symmetric de-license),
  `grammar/.../revision.py` (`RevisionResult.flipped_in` / `flipped_out`).
