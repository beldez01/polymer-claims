# Engineering Backlog — Instrumenting the Nine Whispers

**Date:** 2026-07-07
**Status:** Design / backlog. Approved for build (triage accepted). Each item is scoped to a
single implementation plan; item ① is the first to take through writing-plans.
**Origin:** A `/neg2` peripheral-vision read of the foundations corpus surfaced nine interstitial
tensions ("whispers"). This document triages them into *buildable seams* and *philosophical
notes*, and specifies the five buildable ones as work items anchored to the code they extend.

> **Read this when** the question is "what do we actually build to address the neg2 whispers?" —
> not "what did the scrying find" (that is the whisper list in §0).

---

## 0. The nine whispers (source)

The peripheral-vision read named nine tensions in the foundations corpus. Restated in one line each:

1. **Residue economics** — the alpha-wealth/FDR budget governs *licensing*; the PENDING graveyard R4 says to maintain "with the same rigor as positive results" has no budget and accretes unboundedly.
2. **Tolerance in the kernel** — determinism is bedrock in the foundations, an open problem in the infra doc; the bridge (a tolerance) is a leg-shared parameter.
3. **Compiler/runtime = early/later Wittgenstein** — the two-word banner encodes the region-of-logical-space vs meaning-as-use split the measurement doc flags and MAP.md forgets.
4. **The moat is the tacit floor** — the pathologist's nose (linchpin moat) is exactly the collective-tacit residue R4 says resists mechanization; the wedge→substrate arc bets against the project's own epistemology.
5. **Independence is the un-recomputable premise** — the gate recomputes everything except the one input it most depends on; independence is *judged*, and judgment is the untrusted scaffolding.
6. **Non-ergodicity vs `q`-as-actuarial** — the biological floor needs a non-stationary world; epistemic underwriting needs a stationary one.
7. **Overdetermination as frontier-tell** — six floors are convened because no single one reaches the living cell; the chorus is a compass needle at the frontier.
8. **H¹ = the Duhemian blame-set** — the sheaf obstruction (global inconsistency, no local witness) and the blame-set (fault with no localizable culprit) are the same shape, uncoupled.
9. **Forbidden vs unobserved** — the morphospace "forbidden region" needs a modal claim the licensing-not-meaning firewall was built to refuse; there is no severity-backed licensed negative.

---

## 1. Triage

Grounding each whisper against the code moved one off the build list and confirmed the rest.

| # | Whisper | Verdict | Why |
|---|---|---|---|
| 8 | H¹ ↔ blame-set | **BUILD ①** | `Obstruction` and `BlameSet` both exist; coupling absent; `ROBUSTLY_BLAMED` reserved-not-wired |
| 5 | independence premise | **BUILD ②** | leg-independence now attested (R5.1); shared-cause overlap still operator-asserted vs tunable τ |
| 1 | residue economics | **BUILD ③** | `protocol/economics.py` scheduler exists but budgets actionable claims, not the graveyard |
| 6 | `q` stationarity | **BUILD ④** | `q` quoted as actuarial; no drift-epoch/validity-window stamped on it |
| 9 | forbidden vs unobserved | **BUILD ⑤** | only `SubjectRequirement(mode="forbidden")` exists; no severity-backed licensed negative |
| 2 | kernel tolerance | **NOTE** | agreement is `both_satisfy_criterion` against a *pre-registered* criterion — already the prescribed fix; residual concern is doc-level |
| 3 | compiler/runtime = Wittgenstein | **NOTE** | conceptual; belongs in a foundations doc |
| 4 | moat = tacit floor | **NOTE** | strategic; belongs in the linchpin doc |
| 7 | overdetermination | **NOTE** | meta-observation about the residualism argument's shape |

The three notes and the W2 downgrade are collected in §7. The five builds follow.

---

## 2. Item ① — Couple H¹ obstructions to the Duhem blame-set

**Whisper 8. The smallest, most surgical item; it lights up already-reserved code.**

### What exists

- `src/polymer_claims/sheaf_spectrum.py::_frustration_obstructions` emits
  `Obstruction(claim_ids, edges, magnitude)` — a frustrated fundamental cycle (A≈B≈C≈A whose
  labels do not close), i.e. a global inconsistency **with no local witness**. Impure (numpy).
- `grammar/src/polymer_grammar/blame.py::aggregate_blame(BlameSet) -> BlameVerdict` — pure set
  algebra: intersection = `robustly_blamed`, union = `possibly_blamed`, difference =
  `underdetermined` → `PENDING duhem_underdetermined`. The docstring already states "the protocol
  SUPPLIES the candidate blame-assignments."
- `grammar/src/polymer_grammar/status.py::RejectionReason.ROBUSTLY_BLAMED` — commented
  "terminal; reserved, **not yet wired**."

Nothing converts an `Obstruction` into a candidate `BlameSet`. That is the seam.

### The change

A frustrated cycle is a Duhemian bundle: the contradiction is real but blame can fall on any
member and there is no local witness to isolate the culprit. The mapping:

- The obstruction's `claim_ids` become the **union** blame candidate — every member is
  `possibly_blamed`.
- With a single obstruction there is no intersection to isolate, so the members land in
  `underdetermined` → `PENDING duhem_underdetermined`. Robust blame (`ROBUSTLY_BLAMED`) fires only
  when a claim sits in the intersection of **multiple** independent obstructions/blame-assignments.

Build a pure adapter `obstruction_to_blame_candidate(claim_ids, edges) -> BlameSet` that emits one
`BlameAssignment` per plausible minimal culprit set the cycle admits (at minimum: the whole-cycle
union assignment). Keep it **pure** — it takes plain tuples, builds a `BlameSet`, and lives in the
grammar so `aggregate_blame` consumes it directly. The umbrella (`sheaf_spectrum.py`) passes
`Obstruction.claim_ids`/`.edges` across the purity boundary as plain data.

Then wire `ROBUSTLY_BLAMED`: a claim in `BlameVerdict.robustly_blamed` transitions to
`REJECTED(robustly_blamed)` (terminal, but **demoted not erased** — the audit-trail invariant from
epistemology.md §4). This closes the reserved status.

### Done when

- A synthetic frustrated 3-cycle (the drift-1→1→1→2 loop from epistemology.md §6) produces a
  `BlameSet` whose union is the three claim ids and routes them to `PENDING
  duhem_underdetermined`.
- Two overlapping obstructions sharing one claim drive that claim to `ROBUSTLY_BLAMED` while the
  non-shared members stay `PENDING`.
- Grammar purity preserved (no numpy import crosses into grammar; `test_sheaf.py` + a new
  `test_blame_from_obstruction.py` green).

### Scope guard

Does **not** compute minimal blame-assignments in general (NP-hard; the protocol supplies richer
candidates — the docstring's existing contract). Item ① supplies only the cycle-union candidate and
the intersection-of-multiple robust-blame path. It does not touch the sheaf math.

---

## 3. Item ② — Promote the shared-cause assertion to a first-class defeasible claim

**Whisper 5. The load-bearing risk named in every doc. Companion to the two existing independence
specs.**

### What exists

- Leg-level independence was hardened on main (R5.1): genuinely different n-DMP rank and
  region-delta-beta Hodges-Lehmann legs, per-leg attested evidence. **This item does not touch
  that** — leg independence is now real and attested.
- `grammar/src/polymer_grammar/shared_cause.py` — the *shared-cause* overlap
  (`shared_cause_jaccard`, `SHARED_CAUSE_TAU = 0.5`) is computed from **operator-asserted factor
  tags** and a tunable threshold. Independence-to-multiply is a **judged bool**, not a recomputed
  or defeasible quantity.
- `docs/superpowers/specs/2026-06-29-adapter-independence-hardening-notes.md` — a prior `/neg`
  read that already split the danger into correlated **variance** (detectable by perturbing shared
  inputs) vs correlated **bias** (invisible to agreement; needs an external anchor). It is a
  "recommendation set, not a plan."

### The change

The un-recomputable premise cannot be made recomputable (that would solve the problem the notes
prove unsolvable). The achievable move is the de Bruijn move applied to independence itself: stop
treating the shared-cause verdict as a silent gate parameter and **make it a claim in the corpus**
— defeasible, evidence-bearing, attackable — so the premise sits inside the graph it licenses.

Concretely:

- An `independence` claim asserting "legs A and B are error-independent for this test" carries its
  own evidence: the **correlated-variance probe** from the hardening notes (perturb shared inputs,
  measure joint movement) as its licensable evidence leg.
- Its verdict caps the multiply-e-values decision instead of a bare `τ` threshold — the strength
  cap already exists (`CONFIRMATORY_SEVERITY_CEILING` is the pattern to mirror).
- Correlated **bias** remains explicitly un-instrumentable from within (the notes' finding); the
  independence claim records that residue as an open defeater surface, not a solved axis. This is
  R2 applied to the gate's own blind spot.

### Done when

- A shared-input perturbation test yields an e-value that licenses (or withholds) an
  `independence` claim, and that claim's status gates whether two legs' e-values may multiply in
  `replication.py`.
- A defeat filed against an `independence` claim (e.g. "both legs read the same reference genome")
  is a first-class edge that, when it wins, withdraws the multiply and drops the dependent license
  to single-leg standing.
- The correlated-bias residue is recorded as a named open defeater, not silently absorbed.

### Scope guard

Does **not** claim to detect correlated bias without an external anchor (impossible by
construction). Does **not** re-open leg-level independence (already hardened). Stays on the
shared-cause/multiply decision only.

---

## 4. Item ③ — Give the residue a budget line

**Whisper 1.**

### What exists

`protocol/economics.py` — `next_action(SchedulerState, SchedulerWeights) -> ActionKind` schedules
corpus attention (DRIFT re-checks, etc.). Its weights bias toward actionable, largely LICENSED
claims. The PENDING graveyard has no attention term: it accretes, and R4's "maintain the residue
with the same rigor as positive results" has no mechanical counterpart.

### The change

Add a **residue-value** term to `SchedulerWeights` so PENDING claims (especially
`duhem_underdetermined` and `contested`) earn scheduled re-examination proportional to a
residue-value signal — e.g. how many licensed claims depend on the contested region, or how stale
the pending verdict is against drift. The graveyard stops being write-only.

This is the R3 engine (conversion of residue to claim) given a throttle: the scheduler already
converts drift into re-runs; item ③ lets it convert *residue* into re-tests on a budget rather
than never.

### Done when

- `next_action` can return a re-examination action targeting a PENDING claim when its
  residue-value clears the weighted bar.
- A `duhem_underdetermined` claim with many dependents is scheduled ahead of an isolated
  `untested` one.
- `test_economics.py` extended; existing scheduler behavior unchanged when the residue weight is 0
  (byte-identical-when-off discipline, matching `severity_provenance_of`'s inert-when-absent
  pattern).

### Scope guard

A **budget**, not a mandate — it schedules attention, it does not auto-relicense. Does not add
storage-GC (retention is a separate question; the whisper was about *attention economics*, not
disk).

---

## 5. Item ④ — Attach a stationarity horizon to `q`

**Whisper 6.**

### What exists

`q` (corpus FDR) is quoted as an actuarial/insurable quantity (linchpin §6.2). Drift re-opens
licenses continuously; Kauffman non-ergodicity (residualism §4) says the target is non-stationary.
`q` carries no explicit validity window. `MaterializationContext(api_version, data_version)`
already versions the world.

### The change

Stamp the corpus `q` (and per-claim strength where surfaced) with a **drift-epoch / validity
horizon** derived from the `MaterializationContext` versions its constituent licenses depend on:
`q` is valid *as of* a content-address frontier and *expires* when a watched dependency drifts.
The actuarial framing then carries its stationarity assumption as a logged, expiring parameter
rather than an implicit one — "insurable until the next drift event on these hashes."

### Done when

- A reported `q` carries the set of content-addresses whose drift would invalidate it, and a
  boolean "current as of frontier F."
- A drift event on a constituent hash marks the prior `q` stale (not wrong — *expired*), mirroring
  how a license re-opens.

### Scope guard

Does not attempt to *forecast* the non-stationary future (impossible). It makes the horizon
**explicit and expiring**, which is the honest actuarial move — a quoted rate with a stated
as-of-date, not a stationary guarantee.

---

## 6. Item ⑤ — Distinguish "forbidden" from "unobserved"

**Whisper 9. The largest — net-new. Its home is the claim-type menu.**

### What exists

- The only "forbidden" in code is `SubjectRequirement(mode="forbidden")` in `capability.py` —
  capability conformance, unrelated to morphospace.
- `status.py` has `PendingReason.UNTESTED` but **no severity-backed licensed negative**. An empty
  morphospace region is indistinguishable from an untested one — the classic morphospace weakness
  the measurement doc flags (§7.8).
- `docs/superpowers/specs/2026-06-29-claim-type-menu-design.md` defines a claim type as
  *pattern + independent adapter pair + oracle*. A licensed negative is a new **pattern** there.

### The change

A **high-confidence-negative** claim path: a pattern whose criterion is a severe test for
*absence* (the effect is bounded below a threshold with earned severity), licensable through the
same air-gap + e-value machinery. "Forbidden" = a licensed negative with high severity;
"unobserved" = `PENDING untested`. The morphospace trichotomy
(occupied/empty-reachable/forbidden) then maps to real corpus states instead of collapsing to
occupied-vs-not.

This is the one item that touches the **licensing-not-meaning firewall** (the W9 tension): a
licensed negative is a modal claim about what the region cannot contain. The design must state
explicitly that a licensed negative asserts *earned warrant for absence at a severity*, not
metaphysical impossibility — keeping it a licensing status, not a meaning verdict. That framing is
the whole point of doing ⑤ last: it needs ①–④'s machinery and a careful firewall statement.

### Done when

- A negative pattern licenses on a real EWAS non-effect (effect bounded < threshold, severe,
  air-gapped) and lands as a distinct status from `PENDING untested`.
- The viewer/morphospace can render "forbidden" (licensed negative) separately from "empty"
  (untested).
- The firewall statement is written into the grammar docstring: licensed-negative = warranted
  absence at severity, not impossibility.

### Scope guard

Does not resolve forbidden-vs-unobserved *in general* (undecidable in the limit). It gives the
severity-backed operational separation the measurement doc asks for, and no more.

---

## 7. The notes (non-build whispers)

These three are real and belong in the corpus, but as prose, not code. Recommended homes:

- **W2 — kernel tolerance.** Add a paragraph to `epistemology.md` §8 or `compute-boundary.md`:
  agreement is `both_satisfy_criterion` against a *pre-registered* criterion, so the tolerance is
  a locked, declared object — but that one criterion is shared by both legs, so it is itself a
  decorrelation surface. Name it; it is the residual W2 concern the code already 90% answers.
- **W3 — compiler/runtime = early/later Wittgenstein.** A short section in `measurement-foundation.md`
  (which already flags the split in §7.5) noting that MAP.md's "compiler and runtime" banner *is*
  that split — the compiler is the region view, the runtime the web view.
- **W4 — moat = tacit floor.** A candid paragraph in the linchpin thesis §8 (risk): the wedge's
  unfair advantage (the pathologist's nose) is the collective-tacit residue R4 says resists
  mechanization, so the wedge→substrate arc is partly a bet against the project's own epistemology
  — worth owning, as residualism owns its other open seams.
- **W7 — overdetermination as frontier-tell.** One honest sentence in `residualism.md`'s
  provenance note: the six-floor chorus is convened *because* no single floor reaches the living
  cell, and that is itself the map of where the argument is still being earned.

---

## 8. Sequence and dependencies

```
① H¹→blame      (surgical; proves the pattern; no deps)
   │
② independence  (load-bearing; deps: none hard, but riskiest to sprawl)
   │
③ residue budget (deps: none; benefits from ① since duhem_underdetermined feeds residue-value)
   │
④ q horizon      (deps: none; independent extension)
   │
⑤ licensed neg   (largest; deps: benefits from ①–④'s machinery + a firewall statement)
```

Order: **① → ② → ③ → ④ → ⑤.** ① first to validate the "instrument a whisper" pattern on the
smallest change against already-reserved code; ⑤ last because it is net-new and touches the
firewall. The four notes (§7) can be written any time, independently.

---

## See also

- `docs/superpowers/foundations/residualism.md` — R1–R4, the PENDING graveyard, the tacit floor (W1, W4, W7).
- `docs/superpowers/foundations/epistemology.md` — non-tautological verification, de Bruijn kernel, decorrelation (W2, W5).
- `docs/superpowers/foundations/measurement-foundation.md` — parameterization seam, morphospace, Wittgenstein split (W3, W9).
- `docs/superpowers/foundations/compute-boundary.md` — existence vs correctness, the verification floor (W2, W6).
- `docs/superpowers/specs/2026-06-29-adapter-independence-hardening-notes.md` — bias/variance split behind ②.
- `docs/superpowers/specs/2026-06-29-claim-type-menu-design.md` — pattern/adapter/oracle framing behind ⑤.
