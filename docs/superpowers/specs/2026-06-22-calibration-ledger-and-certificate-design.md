# Calibration Ledger + Certificate — Design Spec

**Status:** Design / approved for planning. v1.4
**Date:** 2026-06-22
**Author:** Z. Belden (brainstormed with Claude)

> Revised through multiple adversarial review passes. **This body reflects the current (v1.4)
> design only**; the per-pass version history is in the **Changelog appendix** at the end. The two
> load-bearing corrections settled by v1.3–v1.4: the synthetic-data resolver actually reaches the
> adapters (a scoped **contract-root contextvar**, not a `base_dir` arg), and the DEFINITIONAL
> statistic is **realized FDR = mean per-batch FDP over *mixed* batches** — named by the
> `realized_fdr` calibration target (all-null degenerates to FDP=1 and cannot validate it). The
> harness pass-rule is the deterministic `mean_fdp ≤ target_q + tolerance` (fixed seed); a report
> summarizes a single `target_q`.

**Arc:** North-Star arc 1 (epistemic core, `q`-calibration) + the build-path critical-path
certificate. Closes `docs/superpowers/2026-06-21-build-path-and-grounding-recommendations.md`
§1 (the one proof that de-risks everything) and §2.1 (the one genuinely missing piece —
`q`-calibration).

> **One line.** Make the corpus's headline metric `q` *validated, not asserted*, by
> calibrating it against constructed ground truth where truth is constructible, tracking
> warrant stability where only continued pressure is available — and emit the result as a
> single-claim, human-legible, attestable **certificate**: the spreadable proof that closes
> the critical path.

---

## 0. Why this, why now

Per the build-path brief, the critical path is: *the kernel licenses one real claim on real
public data, with a real independence check and an honest `q`, emitted as a shareable
certificate.* Checking each component against `main`:

| Component | Status |
|---|---|
| Real claim on real public data | ✅ Done — n-DMP EARNED at REPRODUCED on real TCGA-LAML betas |
| Real independence check | ✅ Done — §E common-cause shared-cause gate |
| Honest `q` | ⚠️ Computed by the FDR math, **not validated against ground truth** (build-path §2.1) |
| Emitted as a shareable certificate | ❌ Not built — `attestation.py` is a provenance bundle, carries no `q`, no single-claim legible surface |

This spec builds the two open pieces. They are inseparable: a certificate over an
*asserted* `q` would be "a confident lie" (build-path §2.2); a calibration story with no
artifact to carry it is invisible.

---

## 1. The epistemic frame (the load-bearing decision)

`q` cannot be calibrated against a single notion of "ground truth," because both naive
routes are flawed and `foundations/epistemology.md` names both:

- **External-authority resolution** (a later "definitive" study declares truth) smuggles in
  a **foundationalist oracle the project explicitly disclaims** (§3: claiming access to
  truth is "the dishonesty the project exists to refuse"; §8 de Bruijn caveat: a reproducible
  build of fabricated data is still reproducible — an external pronouncement has no superior
  warrant).
- **Internal kernel-verdict resolution** (defeated → false; survives → true) is the
  **coherentist tautology** (§1: "a self-consistent web of falsehoods"; §2-B: agreement is
  not truth).

The project's actual move (§3, §5) is never *"we know the truth"* — it is *"we **measure**
severity and independence and **label the warrant**."* Calibration follows the same
discipline: **do not pick a single resolution source and call it ground truth — record
resolutions in warrant tiers, report calibration per tier, never pool.**

### 1.1 The three tiers (each calibrates a *different* thing)

| Tier | Resolution source | Calibration target | Feeds headline `q`? | Honest warrant |
|---|---|---|---|---|
| **DEFINITIONAL** | Synthetic harness — truth known by construction | `realized_fdr` | **Yes** | The one place absolute ground truth honestly exists (we built the data). Calibrates the **machine**. |
| **ANCHORED** | The corpus's own recomputation-grounded pressure events — defeat, drift, red-team (and the drift→re-license/supersede cycle) | `warrant_survival` | No | Defeasible, anchored, attackable — measures how often licensed claims survive continued adjudication. **Not** truth. |
| **ATTESTED** | External attested outcomes (e.g. ClinVar reclassification, a later study) | `external_disagreement` | No | Recorded as external references that *can later be represented as defeasible claims*, never final truth, never superior to ANCHORED. (Schema only this slice — no ingestion source exists yet.) |

The product line: **`q` is a typed reliability statement over warrant classes — definitional
calibration where truth is constructible, field calibration where only continued pressure is
available.** Polymer does not say "we found truth"; it says "we can state exactly what kind
of warrant this claim has, what pressure it has survived, and how that class of warrant has
historically behaved."

### 1.2 The anti-laundering invariant

The danger is that future docs/certificates quietly relabel ANCHORED *survival* as *truth*
calibration. We prevent this with `feeds_headline_q` as a **computed property** (not a stored
field — a persisted bool can go stale or be hand-edited; finding 5), derived purely from
`(resolution_kind, calibration_target)` and enforced at the render boundary:

- **Definition (computed):** `feeds_headline_q := (resolution_kind == definitional ∧ calibration_target == realized_fdr)`.
- **Render-side:** the certificate renderer **recomputes** `feeds_headline_q` from the record's
  kind/target and surfaces **only** the DEFINITIONAL **realized FDR** (mean per-batch FDP) as *the* headline `q`;
  `q_anchored`/`q_attested` always appear under a distinct "warrant stability / field
  calibration" heading, structurally never as the headline. The renderer never trusts a stored
  bool.

---

## 2. Scope (decided)

- **Depth:** the full **resolution-ready ledger** (not a one-off harness) — the actuarial
  backbone, so calibration accrues as real claims resolve over time.
- **Tiers wired this slice:** **DEFINITIONAL fully wired** (the bootstrap *and* the only
  headline-`q` feeder) **+ ANCHORED wired** — failure resolutions (`failed`/`superseded`) from the
  corpus's own defeat/drift events produce a real `q_anchored` from day one; `upheld`
  (survived-pressure) signals are wired as they become observable (§10 scope note). **ATTESTED:**
  schema + validator + report slot only; ingestion deferred.
- **Harness fidelity:** **end-to-end** — synthetic *data* runs through the **real** gate
  (real `betting_evalue`/`count_enrichment_evalue`, the two-adapter air-gap, the real e-LOND
  ledger). Only the data is constructed; nothing about the gate is mocked.
- **Out of scope:** ATTESTED ingestion; a hazard/survival model for `q_anchored` (slice
  reports the raw ratio + exposure caveat); real cryptographic signing (that remains
  attestation arc-2 slice 3).

---

## 3. Architecture (Approach 1 — pure core + umbrella shell)

Mirrors the sheaf-gauge precedent exactly (pure `protocol/sheaf.py` + impure
`polymer_claims/sheaf_spectrum.py` behind `[embed]`).

**Cross-cutting principle: calibration is an instrument, not a gate.** It *measures* the
gate's reliability; it never changes a claim's status or confers standing. The certificate
*reports* calibration; calibration never *licenses*. The de Bruijn kernel is untouched
(`epistemology.md` §8). Consequently the calibration ledger is a **separate meta-structure,
not a fifth `Corpus` collection** — the hard 4-collection invariant is preserved.

| Piece | Location | Purity |
|---|---|---|
| `ResolutionRecord`, `CalibrationLedger`, `CalibrationReport`, `TierStat`, enums | `protocol/src/polymer_protocol/calibration.py` | **Pure**, numpy-free, deterministic |
| `calibration_summary(ledger) -> CalibrationReport` | same | **Pure** |
| `anchored_resolutions(prev_corpus, curr_corpus, cycle, pressure_context) -> tuple[ResolutionRecord, ...]` | same | **Pure** — but *fed* cause via `pressure_context` (a snapshot diff alone can't recover cause; finding 6) |
| `Certificate` DTO (composes Statement + CalibrationReport + params + interpretation) | `src/polymer_claims/attestation.py` (composes the umbrella-side `Statement` already defined there; imports the pure `CalibrationReport` from `protocol/`) | frozen DTO, stdlib-only |
| DEFINITIONAL synthetic harness (data generator + end-to-end gate run) | `src/polymer_claims/calibration_harness.py` | **Impure**, behind `[calibrate]` (numpy) |
| Persistence (JSONL) + ANCHORED tap call site | `src/polymer_claims/calibration_store.py` + `NodeRunner` hook | **Impure** |
| Certificate rendering (text/json/dsse) + `certify` CLI | `src/polymer_claims/` extending `attestation.py` + `cli.py` | **Impure** |

**Packaging (finding 7).** `pyproject.toml` currently has `serve`/`llm`/`embed` extras. Add
`calibrate = ["numpy>=1.26"]` (same pin as `embed`). The `dev` group already includes
`numpy>=1.26`, so calibration tests run under `dev` with no further change; `[calibrate]` exists
so a user who wants the harness without the spectral-layout stack can install just it. The base
import stays numpy-free (`calibration_harness.py`/`calibration_store.py` are not re-exported from
`__init__`, matching `methyl_adapters.py`).

---

## 4. Data model (`protocol/calibration.py`, pure)

Time-like values are passed-in cycle indices (no clock — purity invariant). All models are
frozen `_Model` (`extra="forbid"`); collections are tuples.

### 4.1 Enums

```
ResolutionKind:     definitional | anchored | attested
CalibrationTarget:  realized_fdr | warrant_survival | external_disagreement
ResolutionVerdict:  upheld | failed | unresolved | superseded
PressureKind:       defeat | drift | red_team        # narrowed (finding 7): the actual observed
                                                     # LICENSED→non-LICENSED causes; no generic
                                                     # "demotion", no STRUCTURAL (not a license),
                                                     # no "reinstatement" (that opens a NEW epoch)
```

### 4.2 `ResolutionRecord`

A record is keyed to one **license epoch** — a single licensing episode of a claim. A claim
defeated then later reinstated-and-relicensed has *two* epochs; this is how warrant survival
stays well-defined across the reopen/re-license cycle. **Epoch numbers are allocated by
`calibration_store`, not by the pure diff** (a snapshot diff cannot tell a same-epoch persistence
from a relicense or a post-restart duplicate) — see §6 for the allocation rule.

```
subject_claim_id:   str
license_epoch:      int                          # which licensing episode (increments on re-license)
resolution_kind:    ResolutionKind
calibration_target: CalibrationTarget
verdict:            ResolutionVerdict
stated_q:           float                        # target_fdr the license was issued under
observed_at_cycle:  int                          # passed-in monotonic index (no clock)
# additive/optional, present-only-when-kind (validated):
constructed_truth:  bool | None = None            # definitional — the known ground truth
model_id:           str | None = None             # definitional — which GeneratingModelParams (finding 9)
batch_id:           str | None = None             # definitional — which synthetic batch (for per-batch FDP, finding 2)
pressure_kind:      PressureKind | None = None     # anchored — the survived/failed pressure event (finding 6)
attestation_ref:    str | None = None             # attested — external reference (finding 12)
source_claim_id:    str | None = None             # attested — set iff the attested event is itself a corpus claim (forward-compat)

# computed, NOT stored (finding 5):
@property feeds_headline_q := (resolution_kind == definitional ∧ calibration_target == realized_fdr)
```

**Validator invariants:**
1. target↔kind coupling: `definitional→realized_fdr`, `anchored→warrant_survival`,
   `attested→external_disagreement`.
2. present-only-when-kind: `constructed_truth`/`model_id`/`batch_id` iff `definitional`;
   `pressure_kind` iff `anchored`; `attestation_ref` (and optional `source_claim_id`) iff
   `attested`. (`batch_id` is required on DEFINITIONAL records — the per-batch FDP fold depends
   on it.)
3. `unresolved` verdict is valid only for `anchored`/`attested` (a DEFINITIONAL record always
   has known truth → always `upheld` or `failed`).

**Records are created only for claims the gate LICENSED** — calibration is about the
reliability of *earned* standing.

**`verdict` semantics (per finding 1–2, the key correction):**
- DEFINITIONAL: `upheld` = licensed and truly true; `failed` = licensed but truly null (a false
  license). Truth is always known → never `unresolved`.
- ANCHORED: a record opens `unresolved` at license issuance and is resolved **only by a pressure
  event** — `failed` = a pressure event demoted it (LICENSED→REJECTED via `DEFEAT_GROUNDED_OUT`,
  or LICENSED→PENDING via drift with no re-license); `upheld` = a pressure event occurred and the
  license was **retained** (a defeat attempt failed to ground it out / a drift re-check came back
  clean / a red-team attack failed); `superseded` = drift-reopened then re-licensed under new
  content (the epoch closes `superseded`, a *new* epoch opens `unresolved` — not a failure).
  **A still-live license with no pressure event stays `unresolved` forever** — it is never
  emitted as `upheld`, so `q_anchored` does not drift with tick frequency.

### 4.3 `CalibrationLedger`

```
records:            tuple[ResolutionRecord, ...]
generating_models:  tuple[GeneratingModelParams, ...] = ()   # one per DEFINITIONAL batch (finding 9)
default_target_q:   float | None = None   # optional CLI/report-default hint only — NOT an invariant (finding 1)
```

The ledger may accrete batches/records at **different** `stated_q` values, so there is no single
ledger-level target (finding 1): `default_target_q` is only a convenience default for
`calibration_summary(..., target_q=...)` and the `certify`/`calibrate` CLIs; the authoritative
target is always the one passed to a report, which filters records on `stated_q == target_q`.

`GeneratingModelParams` (frozen): `model_id, n_per_group, n_probes_per_region, effect_size,
dispersion, fraction_true, tau, target_fdr, n_generated, seed_set` — the named assumption behind
each DEFINITIONAL batch; DEFINITIONAL records reference it by `model_id`. The ledger accretes
many batches over time.

**Persistence model (finding 1):** the on-disk store is an **append-only event log**.
`calibration_summary` folds the log to **one current verdict per `(subject_claim_id,
license_epoch)`** (latest event wins), so re-emitting an event on resolution never double-counts
and ANCHORED records are never produced per-tick.

### 4.4 `CalibrationReport` + `TierStat` (the pure aggregation output)

```
TierStat:
    n_total:        int                  # tier denominator population (see per-tier meaning)
    n_failed:       int
    n_unresolved:   int                  # anchored/attested only (DEFINITIONAL: 0)
    n_superseded:   int = 0              # anchored only — terminal, reported separately (finding 6)
    realized_rate:  float | None         # None when the denominator is 0 (DEFINITIONAL: mean per-batch FDP)
    pooled_rate:    float | None = None  # DEFINITIONAL — Σfailed/Σlicensed, secondary view (finding 2)
    # uncertainty on realized_rate (finding 5) — a point estimate alone lets a lucky small run certify.
    # Methods are stdlib-only (finding 3): "normal_0.95" over per-batch FDPs (DEFINITIONAL),
    # "wilson_0.95" for a single binomial proportion (ANCHORED). No SciPy/Beta quantiles.
    ci_low:         float | None = None
    ci_high:        float | None = None
    ci_method:      str | None = None
    n_batches:      int | None = None    # DEFINITIONAL — how many mixed batches contributed
    n_generated:    int | None = None    # DEFINITIONAL only (finding 8)
CalibrationReport:
    target_q, observation_span_cycles: int | None,
    definitional: TierStat, anchored: TierStat, attested: TierStat
```

`calibration_summary(ledger, *, target_q) -> CalibrationReport` (pure), per-tier field meaning
made explicit to keep the denominators honest. **A report summarizes one `target_q` (finding 4):**
FDP is defined relative to a specific e-LOND target, so DEFINITIONAL records are included in the
FDR estimate **only when `stated_q == target_q`** — you cannot average `FDP_b` across batches run
at different targets. Records at other `stated_q` values belong to *separate* reports
(`GeneratingModelParams.target_fdr` pins each batch's target; the validator requires a batch's
records to share one `stated_q`). The same single-`target_q` scoping applies to the ANCHORED/
ATTESTED tiers within a report.
- **DEFINITIONAL (finding 2 — FDR, not pooled fraction).** `n_generated` = claims the harness
  produced; `n_total` = `n_licensed`; `n_failed` = `n_false_licensed`. The headline `realized_rate`
  = the **realized FDR = mean over batches of `FDP_b`** (`FDP_b = false_licensed_b / licensed_b`,
  `0` when `licensed_b=0`), grouped by `batch_id`; `n_batches` = number of mixed batches. The
  interval (`ci_low`/`ci_high`/`ci_method`) is a **normal-approximation interval over the N
  per-batch FDPs** (`mean ± 1.96·sd/√N`) — pure stdlib `math`, no SciPy (finding 3). The **pooled**
  fraction `Σfailed/Σlicensed` is kept as a secondary field (`pooled_rate`), and discovery/power
  (`n_licensed_true / n_true_generated`) stays separate in the harness log — neither is the
  headline.
- **ANCHORED** — `n_total` = resolved-by-pressure population = `n_failed + n_upheld`;
  **`superseded` is terminal but is NOT a warrant failure** — it is reported as `n_superseded`
  and **excluded from the failure-rate denominator** (finding 6); `n_unresolved` = open/live
  epochs; `realized_rate` = `n_failed / (n_failed + n_upheld)` with a **Wilson** interval (stdlib).
  `observation_span_cycles` = span of `observed_at_cycle`, the explicit **exposure caveat**
  (warrant survival is exposure-dependent; the slice reports the raw ratio + interval + counts +
  span, not a hazard model).
- **ATTESTED** — stub (`n_total = 0`) until ingestion exists.
- **Pooling is structurally impossible** — there is no field on `CalibrationReport` that combines
  tiers.

---

## 5. DEFINITIONAL synthetic harness (`calibration_harness.py`, impure, `[calibrate]`)

**Data-generating model** (the disclosed assumption): two groups; per-sample, per-probe betas
from a **Beta distribution** (bounded `[0,1]`, matching the betting e-value's boundedness
assumption). Each synthetic region-claim is **true** (Δβ ≥ τ injected → `constructed_truth=True`)
or **null** (Δβ = 0 → `constructed_truth=False`), mixed at `fraction_true`.

**Fixture seam (how synthetic data reaches the *real* gate).** This is the slice's one delicate
production touch, and a `base_dir` argument is **not** sufficient: the adapters resolve betas deep
inside execution — `RegionMeanDiff`/`RegionLmCoef` → `_load_betas(node)` →
`load_contract(handle.ref)` (`methyl_adapters.py:55`) — so a `base_dir` passed to some *other*
call site never reaches them. The adapters all funnel through the module-level `load_contract(ref)`,
which resolves under `contracts._DIR` and is `lru_cache`d by uid (`contracts/__init__.py:65`).
Tests inject temp contracts by monkeypatching `_DIR` — test-only, unsafe for a production harness.

So the seam is a **scoped contract-root**: a `contextvar` (`_contract_root`, default `_DIR`) read
by the resolver, set for the duration of a batch via a context manager `using_contract_root(path)`.
Because the adapters call the same `load_contract`, the override reaches them automatically, with no
adapter signature change and byte-identical behavior when unset. **Two correctness requirements
(finding 4):** (a) the `lru_cache` key must become `(uid, root)` — not `uid` alone — or a temp
contract and a bundled contract sharing a uid would alias; and (b) synthetic contracts are written
with **content-derived unique uids** anyway, so they never collide with bundled uids and the cache
stays sound. The harness **materializes synthetic SE-Contract files** (manifest + betas TSV, in the
bundled format) under a temp dir, enters `using_contract_root(temp)`, and runs the real gate
end-to-end. One synthetic SE-Contract = one cohort with many regions (= many claims); batches
accumulate to the per-batch counts below. *(The plan pins the contract file format against the
`contracts` package and confirms the contextvar is honored on every adapter path. An injectable
in-memory contract index remains a noted optimization if temp-file I/O dominates at scale.)*

**The statistic the certificate validates is FDR, estimated over *mixed* batches (finding 2).**
The certificate's promise — "≤ q of LICENSED claims are false" — is the **false-discovery
proportion** `FDP = false_licensed / licensed`, and what e-LOND controls is `FDR = E[FDP] ≤ q`.
Under an **all-null** model every license is false, so FDP collapses to 1 whenever any license
occurs — all-null cannot validate the licensed-claim false-rate. So the DEFINITIONAL run is **N
mixed batches** (each `fraction_true ∈ (0,1)`, an independent synthetic cohort): each batch runs
the real gate end-to-end and yields `FDP_b = false_licensed_b / licensed_b` (defined `0` when
`licensed_b = 0`). The headline `q_definitional` = **mean of `FDP_b` over the N batches** (the
Monte-Carlo estimate of `E[FDP]`), with an interval from the across-batch spread (§4.4). Each
LICENSED claim still emits a DEFINITIONAL `ResolutionRecord` (`upheld` if truly true, `failed` if
truly null; `stated_q=target_fdr`; `model_id` = the batch's model), tagged with its batch id so the
fold can compute per-batch FDP. The harness also reports the **pooled** licensed-claim false
fraction `Σfailed / Σlicensed` as a secondary view, and — separately — an **all-null control**
(per-comparison false-positive behavior), which is a *control*, not the headline. Each batch is
~10³ claims; N batches (≈ 12) → a tight, honestly-bounded `q_definitional`.

**Determinism:** the betting e-value is already seed-averaged; the harness threads a fixed
seed set so `q_definitional` is reproducible (the certificate cites it → must be stable /
content-addressable).

**Honesty:** never tunes to pass. If the realized FDR (mean per-batch FDP) exceeds `target_q`, that
is a real finding (the gate miscalibrated on this generating model), reported plainly (Phase A's
"honest failure is an acceptable outcome").

CLI: `polymer-claims calibrate --synthetic --n 10000 --q 0.05 [--fraction-true … --effect-size …]`
→ writes DEFINITIONAL records + the batch's `GeneratingModelParams` to the calibration store.

---

## 6. ANCHORED tap (pure logic in `protocol/calibration.py`; persistence + call site in `calibration_store.py` / `NodeRunner`)

`anchored_resolutions(prev_corpus, curr_corpus, cycle, pressure_context)` is **pure** — but a
bare snapshot diff cannot recover *why* a license moved (finding 6), so the impure callers feed
it `pressure_context`: the cause information already available at the right sites —
`RejectionReason.DEFEAT_GROUNDED_OUT` (on the rejected claim, from `integrate.py`/`verify.py`)
for defeat, `NodeRunner.last_drift` (a `DriftRecord`) for drift, and the red-team daemon's
outcome for a red-team attempt. The pure function maps `(transition, cause)` → records; the
impure layer owns observing the cause.

**Event-identity, not per-tick (findings 1–2).** ANCHORED records are emitted **only at two
moments**, never every tick:
1. **License issuance** — when a claim *enters* LICENSED, open one `unresolved` record for its
   `(subject_claim_id, license_epoch)`.
2. **A pressure event** — when a known pressure event touches that epoch, emit its resolving
   record:

| Observed transition | `pressure_context` cause | verdict | `pressure_kind` |
|---|---|---|---|
| LICENSED → REJECTED | `DEFEAT_GROUNDED_OUT` | `failed` | `defeat` |
| LICENSED → PENDING (no re-license) | `last_drift` for this claim | `failed` | `drift` |
| LICENSED → PENDING → re-LICENSED (new content) | `last_drift` + re-license | `superseded` (epoch closes; new epoch opens `unresolved`) | `drift` |
| Defeat attempt fired but claim **retained** LICENSED | attacker present, claim still IN | `upheld` | `defeat` |
| Drift re-check came back **clean** | `last_drift` clean for this claim | `upheld` | `drift` |
| Red-team attack **failed** | red-team outcome | `upheld` | `red_team` |

A still-LICENSED claim that has met **no** pressure event stays `unresolved` — it is never
emitted as `upheld`, so `q_anchored` cannot drift with tick frequency. `upheld` means *survived
a defined pressure event*, not *persisted*. Reinstatement is not a verdict here: a reopened claim
that re-licenses opens a **new** `license_epoch` (a fresh `unresolved` record).

**Epoch allocation (finding 3) — owned by `calibration_store` (impure, stateful).** The store
persists, per `subject_claim_id`, the last allocated `license_epoch` and an **epoch-identity key**.
The identity key is the content-address (`semantic_run_id`) when the license carries one; for a
license **without** a full CES content-address, the store falls back to a deterministic identity
tuple `(claim_id, fdr_test_index, materialization-identity, claim-content-hash)` (finding 6) — so
epoch tracking is well-defined for every license, content-addressed or not. *(Certificate emission
still prefers content-addressed licenses; non-addressed ones are tracked via the fallback and
flagged as such.)* The rule:
- a claim **enters LICENSED from a non-LICENSED state** → allocate a **new** epoch (`last+1`,
  or `0` if unseen);
- a claim is **re-LICENSED after drift under a changed epoch-identity key** → allocate a **new**
  epoch (the old one already closed `superseded`/`failed`);
- a claim **seen still-LICENSED at the same epoch-identity key** → the **same** epoch (no new
  record — idempotent across ticks *and* across process restarts, since the mapping is
  persisted). This is what makes the tap safe to call every tick and after a restart.

**Persistence:** append-only JSONL **event log** (under `data/calibration/`, gitignored like
other local run data). `calibration_summary` folds events to the latest verdict per
`(subject_claim_id, license_epoch)` — so a record that opens `unresolved` and later resolves
`failed`/`upheld`/`superseded` is counted once, at its latest state.

---

## 7. The certificate (`Certificate` DTO pure; rendering + CLI impure, extending `attestation.py`)

A single-claim, human-legible **and** machine-verifiable artifact = existing attestation
(in-toto Statement v1 / SLSA Provenance v1 / DRS / DSSE) **+** the calibration block. The pure
`Certificate` DTO composes:

1. **Individual standing** (existing `attestation.py`): claim id, e-value cleared, e-LOND
   α/threshold beaten, content-address (`dimnames_hash`/`profile_hash`/`semantic_run_id`),
   independence tier, the air-gap credential pair — the Statement already built.
2. **Corpus calibration block** (new): the three `TierStat`s + the DEFINITIONAL
   `GeneratingModelParams` (the named assumption).
3. **Interpretation line:** *"Definitional calibration validates the gate under known
   constructed truth. Anchored/attested calibration measures warrant stability under future
   pressure."*

Rendered form (human-legible) — denominators stated explicitly so the realized FDR and the
pooled false fraction are unambiguous (finding 8):
```
Corpus target q: 0.05
Calibration evidence:
  DEFINITIONAL: 12 mixed batches, 9,840 generated → 6,142 licensed; 251 false licenses
                → realized FDR (mean per-batch FDP) 0.043, 95% CI [0.031, 0.055]
                  (pooled false fraction 0.041 = 251 / 6,142)
  ANCHORED:     238 epochs resolved under pressure; 11 failed
                → warrant-failure rate 0.046, 95% CI [0.026, 0.081] (= 11 / 238);
                  17 superseded (re-licensed under new content, excluded); 1,094 unresolved (span: 412 cycles)
  ATTESTED:     0 attested events yet
Interpretation: definitional validates the gate under constructed truth (realized FDR);
                anchored/attested measure warrant stability under future pressure, not truth.
```

**Render-side no-laundering invariant:** the renderer **recomputes** `feeds_headline_q` from each
tier's kind/target (never a stored bool; finding 5) and surfaces only the DEFINITIONAL
realized FDR (mean per-batch FDP) as *the* headline `q`; `q_anchored`/`q_attested` always appear
under a distinct "warrant stability / field calibration" heading. The calibration block is cited against a
**content-addressed snapshot** of the ledger at issue time → reproducible.

CLI: `polymer-claims certify <claim-id> [--corpus PATH] [--calibration LEDGER] [--format text|json|dsse]`
— default human-legible text to stdout.

**DSSE certificate payload (finding 4) — the calibration block must be inside the signed bytes.**
The existing `dsse_envelope(statement)` wraps *only* an in-toto Statement; if `certify --format
dsse` reused it, the calibration evidence would not be in the signed payload. So this slice adds a
**new payload type**: `Certificate` serializes to its own JSON (the Statement **+** the
`CalibrationReport` **+** `GeneratingModelParams` **+** the content-address digest of the ledger
snapshot **+** interpretation), and a new `certificate_dsse_envelope(certificate)` wraps it with a
distinct `payloadType` (e.g. `application/vnd.polymer.certificate+json`), `signatures: []`
(signing-ready, slice-3 deferred). A third party decodes `payload` → the full Certificate and can
re-verify both the claim's content-address **and** that the calibration block matches the
committed ledger digest. The existing `dsse_envelope` is untouched.

**Byte-identical scope (finding 10), stated precisely.** The new public names are
`Certificate`, `build_certificate`, `certificate_dsse_envelope`, and the `certify` CLI. They must
not touch `build_attestation_bundle`, `build_attestation_records`, `build_attestation_statements`,
`dsse_envelope`, or any existing DSSE serialization — existing `export-attestation` output stays
**byte-identical** (golden-tested). When no calibration ledger is supplied, `certify` degrades to
a standing-only certificate (the attestation Statement, no calibration block).

---

## 8. Testing (TDD — failing test first)

**Pure (`protocol/calibration.py`):**
- Validator: target↔kind coupling enforced; present-only-when-kind violations rejected;
  `unresolved` rejected on a DEFINITIONAL record. `feeds_headline_q` is a **computed property** —
  test it returns True only for `(definitional, realized_fdr)` and that no constructor path
  can store a conflicting value (there is no settable field).
- `calibration_summary`: three tiers correct, **never pooled across tiers**; `realized_rate=None`
  at empty denominator; **DEFINITIONAL `realized_rate = mean(FDP_b)` grouped by `batch_id`** and
  `pooled_rate = n_false_licensed / n_licensed` (the secondary view — assert the two differ on a
  fixture with uneven batch sizes, so the headline can't silently revert to the pooled bug);
  `q_anchored = n_failed / (n_failed + n_upheld)` excludes `unresolved`; **event-fold** collapses an
  open→resolved pair for one `(claim_id, license_epoch)` to a single latest-state count;
  `observation_span_cycles` correct.
- `anchored_resolutions` (given `pressure_context`): defeat→`failed`/`defeat`,
  drift-no-relicense→`failed`/`drift`, drift-then-relicense→`superseded` + new-epoch `unresolved`,
  defeat-attempt-retained→`upheld`/`defeat`, drift-clean→`upheld`/`drift`,
  red-team-failed→`upheld`/`red_team`, **still-LICENSED-no-pressure → emits nothing (stays
  `unresolved`)** — on hand-built corpus-pair + `pressure_context` fixtures.

**Impure (umbrella, skip-if-`[calibrate]`-absent):**
- Harness determinism: same seed → **byte-identical** ledger.
- **Calibration pass-bar, statistically valid (findings 2 + 4).** FDR control is a **long-run
  expectation** `E[FDP] ≤ q`, *not* a guarantee every finite batch's FDP ≤ q; and an **all-null**
  model has FDP=1 whenever any license occurs, so it cannot test the licensed-claim false rate. So:
  1. **Deterministic smoke fixture** — a fixed-seed cohort engineered so the gate's behavior is
     determined; assert the plumbing end-to-end (e-value path, air-gap, e-LOND, record emission) on
     known counts. Deterministic, no statistics.
  2. **Mixed-batch FDR check** — run *N* **mixed** batches (`fraction_true ∈ (0,1)`) under a
     **fixed seed**, which makes `mean_fdp` a *deterministic* number (not a random draw). The
     **exact acceptance rule is `mean_fdp ≤ target_q + tolerance`** (a small absolute margin, e.g.
     `0.01`, absorbing the fixed-seed point estimate's distance from `q` at the chosen N/batch-size)
     — a gate whose realized FDR sits clearly above `q` fails. This is stronger than a CI-overlap
     rule (`ci_low ≤ q` would let a wide-CI underpowered run with `mean_fdp ≫ q` pass — too weak;
     finding 2) and is non-flaky because the seed fixes the number. The 95% CI is **reported**
     alongside (for the certificate/human reader), not used as the gate. The broken-gate control
     (bar 5) asserts the **opposite**, `mean_fdp > target_q + tolerance`, proving detection.
     *(Distinct from the certificate, which is **report-only** — realized FDR + CI, no embedded
     pass/fail; calibration is an instrument, not a gate. This rule is the harness's own pytest
     assertion, never a gate on a claim.)*
  3. **All-null control** — run all-null batches and assert licenses are *rare* (per-comparison
     false-positive behavior bounded), reported as a **control**, explicitly *not* as the headline
     realized FDR.
  4. **Power sanity** — an all-true batch → high discovery and ~0 false licenses.
  5. **Miscalibration detection** — a **deliberately broken/permissive** gate fixture (evidence
     forced to clear the threshold under the null) → false licenses appear and are *reported*,
     proving the harness *detects* miscalibration rather than hiding it.
- Store JSONL **event-log** round-trip + append + fold semantics (open then resolve → one count).
- Certificate golden render; **assert the renderer never surfaces `q_anchored`/`q_attested` as
  the headline `q`** (recomputes `feeds_headline_q`). **DSSE (finding 5):** existing
  `dsse_envelope` decodes to the bare **Statement** (unchanged); the new
  `certificate_dsse_envelope` decodes to the full **Certificate** (Statement + calibration report +
  ledger-snapshot digest), and the embedded digest matches the cited ledger snapshot.
- `certify` CLI smoke test (with and without a calibration ledger).
- Existing `export-attestation` output **byte-identical** with calibration code present (golden
  over `build_attestation_bundle`/`records`/`statements`/`dsse_envelope`).

Gate: per-package `uv run pytest -q` + `uv run ruff check src tests`; full `scripts/check-all.sh`.

---

## 9. Invariants honored

- **Calibration is an instrument, not a gate** — never changes a claim's status; the kernel
  stays small.
- `Corpus` stays **exactly 4 collections** — the ledger is a separate meta-structure.
- grammar/protocol stay **pure, deterministic, numpy-free**; all impurity (synthetic data,
  e-value computation, persistence, rendering) is umbrella-side; numpy behind the new
  `[calibrate]` extra (the real e-value path in `evidence.py` already requires numpy).
- New fields land **additive/optional** with present-only-when-Y validators; **byte-identical
  when off** (existing `export-attestation` output unchanged — new APIs only).
- **No laundering** of warrant survival into truth calibration — `feeds_headline_q` is a
  **computed property** (never a stored bool) and the renderer recomputes it; only DEFINITIONAL
  **realized-FDR** calibration can be the headline `q`.
- **Honesty over polish** — a miscalibrated `q_definitional` is reported, not tuned away; the
  generating model is disclosed as a named assumption.

---

## 10. Deferred / follow-ups

- ATTESTED ingestion (needs a real external-resolution source); promote `source_claim_id` to a
  first-class link if attested events become corpus claims.
- Hazard/survival model for `q_anchored` (exposure-weighted) — replaces the raw-ratio +
  span caveat.
- **Stronger DEFINITIONAL uncertainty.** The normal-approx CI over N≈12 per-batch FDPs is
  *descriptive*, not a validity proof (small N, bounded/skewed FDPs). It is adequate for the
  report-only certificate; before any external-facing `q` claim, increase N and/or use a better
  interval (e.g. bootstrap over batches). Calibration is an instrument, so this is a sharpening, not
  a correctness gap.
- **`upheld` observability (scope note).** `failed`/`superseded` resolutions are directly
  observable (a license moves out of LICENSED with a known cause). `upheld` requires observing a
  *survived* pressure event (a defeat attempt that fired but was grounded back IN, a drift
  re-check that came back clean, a failed red-team attack) — signals the node may not surface
  today. The plan must confirm these are observable from `integrate`/`drift`/red-team outputs; if
  some are not yet, the first cut resolves `failed`/`superseded`/`unresolved` and wires each
  `upheld` signal as it becomes available (the math is unchanged — fewer events in `n_total`,
  honestly reported).
- Injectable in-memory contract index for the harness (optimization over temp SE-Contract files,
  if file I/O dominates at 10⁴ scale).
- Real cryptographic signing of the certificate (attestation arc-2 slice 3 — Sigstore/Rekor).
- Per-claim credence on the certificate (vs corpus-level calibration) — a later credence-layer
  arc.

---

## 11. References

- `docs/superpowers/2026-06-21-build-path-and-grounding-recommendations.md` §1, §2.1, §2.2
- `docs/superpowers/foundations/epistemology.md` §1–3, §7, §8
- `docs/superpowers/2026-06-12-phase-2-north-star.md` §2(C) credence-primary, §2(E) independence
- `docs/superpowers/2026-06-16-linchpin-thesis-three-layer-arc.md` §6.2 epistemic underwriting
- Existing substrate: `src/polymer_claims/attestation.py`, `evidence.py`, `replication.py`,
  `grammar/src/polymer_grammar/fdr.py`, `protocol/src/polymer_protocol/sheaf.py` (precedent)

---

## Appendix — Changelog (version history)

The body above is the current design; this records what each review pass changed.

- **v1.0** — initial design from brainstorming: warrant-tiered calibration ledger
  (DEFINITIONAL/ANCHORED/ATTESTED), end-to-end synthetic harness, single-claim certificate over
  the attestation substrate.
- **v1.1 (review pass 1)** — ANCHORED event-identity per *license epoch* (no per-tick records;
  `upheld` = survived pressure, not persistence); concrete harness fixture seam; corrected the
  all-null test wording; `feeds_headline_q` → computed property; DEFINITIONAL denominators split
  into generated/licensed/false-licensed; multiple generating models; precise byte-identical
  scope; `[calibrate]` extra; ATTESTED wording softened + `source_claim_id`.
- **v1.2 (review pass 2)** — `license_epoch` allocation owned by `calibration_store`; DSSE
  `Certificate` payload type; uncertainty intervals; `superseded` reported separately; explicit
  packaging change. *(Two residuals — the resolver not reaching the adapters, and FDR-vs-pooled —
  were caught in pass 3.)*
- **v1.3 (review pass 3)** — the synthetic-data resolver is a **scoped contract-root contextvar**
  the adapters actually pick up (not a `base_dir` arg), with an `(uid, root)` cache key; the
  DEFINITIONAL statistic is **realized FDR = mean per-batch FDP over mixed batches** (all-null
  cannot validate the licensed-claim false rate), pooled fraction kept as secondary; intervals
  narrowed to stdlib Wilson/normal-approx; epoch-identity fallback tuple for non-content-addressed
  licenses; DSSE test wording corrected; changelog moved to this appendix.
- **v1.4 (review passes 4–5)** — consistency + precision: stale DEFINITIONAL formula and overloaded
  "false-license rate" wording purged (headline is **realized FDR**, secondary is **pooled false
  fraction**); the calibration target renamed `realized_fdr` (was the now-misleading
  `false_license_rate`); the harness pass-rule tightened from the too-weak `ci_low ≤ q` to the
  deterministic **`mean_fdp ≤ target_q + tolerance`** (fixed seed), CI report-only; a report
  **summarizes a single `target_q`** (FDPs are not averaged across e-LOND targets); `batch_id`
  added to the definitional-only validator; ledger `target_q` demoted to an optional
  `default_target_q` hint (the ledger may hold mixed-`q` batches); v1.1 banner removed from the body.
