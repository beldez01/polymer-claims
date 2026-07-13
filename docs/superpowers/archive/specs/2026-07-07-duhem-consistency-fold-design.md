# Duhem Consistency Fold — wiring the H¹ coupling into run_cycle

**Date:** 2026-07-07
**Status:** Design / approved for build. Follow-up to item ① of the neg2 backlog.
**Depends on:** `2026-07-07-h1-blame-set-coupling.md` (item ①, merged) — this makes that
coupling *live*.

> **Read this when** the question is "how does a sheaf H¹ inconsistency actually change a
> claim's status in the running loop?" Item ① built the pure coupling and tested it; nothing
> called it. This wires it into the cycle so a frustrated cycle demotes the claims it implicates.

## 0. Consistency with the Spine

Checked against `docs/the-spine-one-pager.pdf`. This fold sits in the spine's **Layer 5 ·
Coherence & time** ("survives & still true?" — failure: *ignored contradictions*; lock: *defeat
graph (grounded) + Refund-Validity + drift daemon*). It operationalizes the sheaf-H¹ coherence
half of that layer: today the consistency gauge is *reported*; this makes it *act*.

Two spine commitments bind the design, and one corrects it:

- **"We produce warrant, not truth. Rejected means unwarranted-for-now, never false."** The
  demote-only decision (§2.2) is exactly this — a duhem-implicated claim is suspended to a
  reopenable `PENDING`, never condemned. Consistent.
- **Refund-Validity (the spine's named theorem): "a defeat refunds the ledger *only if it entails
  the null*."** A duhem coherence suspension does **not** entail any claim's effect-null — it is a
  *warrant-only* move ("the effect is there but the claims can't all mean what they say at once").
  Per `refund-validity.md` §6/§8 and `epistemic-core-derivation.pdf` §5, warrant-only defeats
  de-license in the graph but **leave the `FDRTest` live** (only `NULL_BEARING_KINDS = {rebut}`
  refunds; `defeat.py:54`). So this fold is **ledger-neutral** — it must not tombstone. (This
  corrects an earlier draft of §4 that refunded on demote — the exact bug §6 names.)

Also checked against `docs/epistemic-core-derivation.pdf`:

- **The conservation thesis (§4): the believed state is `({eᵢ}, D)`, and the `Discover` predicate
  is the only place statistical belief moves.** The fold touches **neither** — it emits no new
  `eᵢ` and writes no `D` (warrant-only ⇒ no retract). It changes only *graph* standing
  (`LICENSED → PENDING`), which is exactly the layer the derivation's page-7 split already
  governs: "de-licenses in the graph… but its `FDRTest` stays live." So a duhem-suspended claim is
  correctly a **live discovery in the ledger while `PENDING` in the graph** — the coupling does not
  introduce a second belief-removal mechanism inside the `(eᵢ, D)` unification; it rides the
  existing warrant-only graph layer.
- **Why a fold and not a defeat edge.** An H¹ obstruction has *no local witness* — blame is
  non-localizable across the cycle. A defeat edge (source → target) would falsely localize it, so
  the fold uses the distinct `PendingReason.DUHEM_UNDERDETERMINED` verdict (already in the grammar,
  separate from `DEFEAT_GROUNDED_OUT`) rather than authoring defeat edges. This is the grammar's
  own pre-existing distinction, honored.

---

## 1. What exists after item ①

- `polymer_protocol.blame_bridge` — `blame_set_from_obstruction`, `blame_verdict_from_obstructions`,
  `duhem_statuses_from_obstructions`. Pure, unit-tested, and **called by nothing in the live loop**.
- `polymer_protocol.sheaf` (pure) — `extract_sheaf(corpus) -> SheafStructure`, and the
  `Obstruction`/`SheafStructure` types.
- `polymer_claims.sheaf_spectrum` (umbrella, numpy) — `consistency_report`, and — by accident of
  placement — the numpy-free `_frustration_obstructions` + `_cycle_ids` graph walk.
- `run_cycle` (`cycle.py`) — phases end with `verify_stage` then `integrate`. `integrate`
  (`integrate.py`) is the model to mirror: `_reject` flips a defeated license to `REJECTED` and
  `retract_tests` tombstones its e-LOND discovery; `_reinstate` reopens a `DEFEAT_GROUNDED_OUT`
  claim to `PENDING REINSTATED` when its attacker falls. `_reinstate` deliberately does **not**
  reopen `refuted` / `robustly_blamed` / `hypothesis_altered` (terminal).

## 2. The four decisions (settled)

1. **Port the detector into pure protocol** so `run_cycle` can detect obstructions with no numpy
   and no umbrella round-trip.
2. **Demote-only, reversible.** The live fold only demotes to `PENDING duhem_underdetermined`;
   it never auto-applies terminal `ROBUSTLY_BLAMED`. That heuristic terminal-rejection path stays
   in `duhem_statuses_from_obstructions` for a future manual/stronger-evidence flow.
3. **Run the fold after `integrate`** — on the defeat-settled survivor set, so consistency is
   checked on what actually holds.
4. **Provenance minimal** — record implicated contradiction-ids in the `StageAudit` note; no new
   `Claim` field (the reopen mechanism re-checks live obstructions, so it stores nothing).

---

## 3. Component 1 — port the frustration detector to pure protocol

**Move** `_frustration_obstructions` and its helper `_cycle_ids` from
`src/polymer_claims/sheaf_spectrum.py` into `protocol/src/polymer_protocol/sheaf.py`, exposed as a
public `frustration_obstructions(structure: SheafStructure) -> tuple[Obstruction, ...]`. They use
only `deque`/`dict`/`sorted`/`frozenset` — **no numpy**, verified.

**Umbrella becomes a caller.** `sheaf_spectrum.consistency_report` currently calls its local
`_frustration_obstructions`; change it to import `frustration_obstructions` from
`polymer_protocol`. Single source of truth; removes the duplication. The numpy code
(`_coboundary`, `_spectrum_core`, `_energy`) stays in the umbrella untouched.

**Tests:** the existing frustration tests in `tests/test_sheaf_spectrum.py` that exercise
`_frustration_obstructions`/`consistency_report` must still pass unchanged (behavior is identical —
same function, new home). Add a direct pure-protocol test in `protocol/tests/` that calls
`frustration_obstructions(extract_sheaf(corpus))` on a small frustrated corpus, so the detector has
coverage that does not route through numpy.

### Done when
- `frustration_obstructions` lives in `polymer_protocol.sheaf`, exported from `polymer_protocol`.
- `consistency_report` imports it from protocol; `tests/test_sheaf_spectrum.py` green, unchanged.
- Protocol has a numpy-free test of the detector.
- No numpy import appears anywhere in `protocol/`.

### Scope guard
Pure relocation + re-export. Do **not** change the detection algorithm, signed-BFS labels, cycle
dedup, or the `Obstruction` shape. Byte-identical obstructions before and after.

---

## 4. Component 2 — the pure fold `apply_duhem_consistency`

New function in a new pure module `protocol/src/polymer_protocol/duhem_fold.py`, shaped like
`integrate`:

```
def apply_duhem_consistency(corpus: Corpus) -> tuple[Corpus, DuhemFoldAudit]:
    ...
```

Algorithm:
1. `obstructions = frustration_obstructions(extract_sheaf(corpus))`.
2. `implicated = blame_verdict_from_obstructions(obstructions).possibly_blamed` — the union of all
   claim-ids in any frustrated cycle. (Demote-only uses the union; the robust/underdetermined split
   is not acted on here.)
3. **Demote:** for each claim whose `status == LICENSED` and `id in implicated`, flip to
   `PENDING duhem_underdetermined`, clear `licensing`, via a `_demote_duhem(c)` helper that mirrors
   `_reject` (but to PENDING, not REJECTED, and with `pending_reason=DUHEM_UNDERDETERMINED`).
4. **Reopen:** for each claim with `status == PENDING` and `pending_reason == DUHEM_UNDERDETERMINED`
   and `id not in implicated` (its cycle resolved) and `evaluation_plan is not None`, reopen to
   `PENDING REINSTATED` via a `_reopen_duhem(c)` helper mirroring `_reinstate`. (Demote and reopen
   are disjoint by the `in implicated` / `not in implicated` split — applied in one pass, like
   integrate's flipped_out/flipped_in.)
5. **No e-LOND refund — the fold is ledger-neutral.** A duhem suspension is *warrant-only*: it does
   not entail any claim's effect-null. By Refund-Validity (`refund-validity.md` §6, §8) a
   warrant-only defeat de-licenses in the graph but **leaves the `FDRTest` live** — tombstoning it
   would be the exact bug §6 names ("the effect is there and means something else" is not
   grounds for a refund). So `apply_duhem_consistency` does **not** call `retract_tests` and does
   **not** touch `corpus.fdr_ledger`. A demoted claim is correctly a live discovery in the ledger
   while `PENDING` in the graph — precisely the "rejected in the graph, test stays live" case §6
   endorses.
6. Return the updated corpus (new claims; **ledger unchanged**) and a `DuhemFoldAudit` carrying the
   demoted ids, reopened ids, and the implicated contradiction-ids (the `"h1:…"` strings) for the
   `StageAudit` note.

### Done when
- A LICENSED claim inside a frustrated cycle demotes to `PENDING duhem_underdetermined`, licensing
  cleared, **and its `FDRTest` stays live** (assert the ledger's live discovery count is unchanged
  by the fold — the warrant-only / Refund-Validity invariant).
- A `PENDING duhem_underdetermined` claim whose cycle has resolved reopens to `PENDING REINSTATED`.
- No claim is ever set to `REJECTED` by this fold (demote-only invariant — assert in a test).
- A claim PENDING for an unrelated reason, or LICENSED but not implicated, is untouched.
- Pure: no numpy, no `polymer_claims` import.

### Scope guard
Demote-only, ledger-neutral. Does not call the terminal `ROBUSTLY_BLAMED` path. Does not call
`retract_tests` or otherwise mutate `fdr_ledger` (warrant-only → no refund, per Refund-Validity).
Does not add a `Claim` provenance field. Does not write the defeat graph or equivalence edges (it
reads the sheaf, which is derived from them, but writes only claim status).

---

## 5. Component 3 — wire into `run_cycle`

After the `integrate(...)` call (`cycle.py:176`) and its `StageAudit`, add:

```python
corpus, duhem_audit = apply_duhem_consistency(corpus)
audit.append(StageAudit(
    stage="duhem_consistency",
    note=f"{len(duhem_audit.demoted)} demoted (duhem), {len(duhem_audit.reopened)} reopened"
         + (f"; contradictions {sorted(duhem_audit.contradiction_ids)}" if duhem_audit.contradiction_ids else ""),
    count=len(duhem_audit.demoted),
))
```

Runs on the post-`integrate` (defeat-settled) corpus. No signature change to `run_cycle` (the fold
takes only the corpus). The `CycleResult`'s existing per-claim `licensed`/`rejected` roll-up
(`cycle.py:196-197`) already reads final status, so a demoted claim correctly drops out of
`licensed` with no change there.

### Done when
- A `run_cycle` integration test drives a corpus into a frustrated cycle: a claim that was LICENSED
  is `PENDING duhem_underdetermined` after the cycle, and the `duhem_consistency` StageAudit reports
  it. Then a follow-up cycle that harmonizes the values (cycle resolves) reopens it to
  `PENDING REINSTATED`.
- Existing `run_cycle` tests (`test_cycle.py`, `test_run_cycle_output_valid.py`) still green.

### Scope guard
One `StageAudit`, one call site, after integrate. No reordering of existing phases.

---

## 6. File structure

| File | Responsibility | Create/Modify |
|---|---|---|
| `protocol/src/polymer_protocol/sheaf.py` | add `frustration_obstructions` (+ `_cycle_ids` helper), moved from umbrella | Modify |
| `src/polymer_claims/sheaf_spectrum.py` | delete local `_frustration_obstructions`/`_cycle_ids`; import from protocol | Modify |
| `protocol/src/polymer_protocol/duhem_fold.py` | `apply_duhem_consistency` + `_demote_duhem`/`_reopen_duhem` + `DuhemFoldAudit` | Create |
| `protocol/src/polymer_protocol/cycle.py` | call the fold after integrate + StageAudit | Modify |
| `protocol/src/polymer_protocol/__init__.py` | export `frustration_obstructions`, `apply_duhem_consistency`, `DuhemFoldAudit` | Modify |
| `protocol/tests/test_frustration_obstructions.py` | numpy-free detector test | Create |
| `protocol/tests/test_duhem_fold.py` | demote / reopen / never-reject / untouched-claims | Create |
| `protocol/tests/test_cycle.py` | integration: frustrated cycle → demote → resolve → reopen | Modify |
| `tests/test_sheaf_spectrum.py` | unchanged assertions; confirm still green after the move | (verify) |

## 7. Related cleanup (optional, from the whole-branch review)

Finding #4 (blame_bridge re-implements set algebra the grammar owns) is orthogonal to this wiring
and is **not** in scope here. If touched at all, it is a one-task cleanup expressing
`blame_verdict_from_obstructions`'s ≥2-cycle case via `aggregate_blame(BlameSet(...))`. Left as a
noted follow-up, not a requirement of this spec.

## 8. Risks / the one thing to watch

The e-LOND question is **settled by Refund-Validity, not left to judgment**: a duhem suspension is
warrant-only, so the fold does not touch the ledger (§4 step 5, §0). This removes the double-count
hazard entirely — there is no refund to get wrong. A test should assert the ledger's live-discovery
count is *unchanged* across a demote and across a reopen.

The residual watch moves to the **reopen → re-verify** path: because the demoted claim's `FDRTest`
stayed live, a reopened (`PENDING REINSTATED`) claim that clears verification again must **not
register a new test** — its discovery already exists. Confirm the reopen flows through the same
verify path that drift-reopened claims use (which already faces this), and add a test asserting a
demote→resolve→reopen→re-license round-trip leaves `n_tests` and the live-discovery count where they
started (no phantom second registration).

## See also
- `docs/superpowers/specs/2026-07-07-h1-blame-set-coupling.md` — item ① (the coupling this wires).
- `docs/superpowers/specs/2026-07-07-neg-whisper-backlog-design.md` — the parent backlog.
- `evalue-claim-graph/refund-validity.md` — the e-LOND refund gate (§4) to honor in §4 step 5.
- `protocol/src/polymer_protocol/integrate.py` — the `_reject`/`_reinstate`/refund pattern mirrored here.
