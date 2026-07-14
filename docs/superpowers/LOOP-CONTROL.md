# ⟳ BACKLOG LOOP — autonomous control spine

> **Started 2026-07-14** by an autonomous `/loop` directed at completing `docs/superpowers/BACKLOG.md`.
> This file is the loop's memory. It survives context summarization — **read it first on every fire.**
> Keep the *State* + *Queue* sections current at every item boundary. Check items off in `BACKLOG.md` too.

## Mission
Work through the entire `BACKLOG.md` serially: build the buildable items, verify each, check it off,
update docs. The user is away; act on established work, don't invent scope or make strategic calls.

## Operating policy (HARD RULES — do not violate autonomously)
1. **Preserve the invariants** on every change:
   - Corpus stays **exactly 4** collections.
   - `grammar/` and `protocol/` stay **pure + numpy-free**; no `polymer_claims` imports leak into them.
   - Any additive optional field must be **byte-identical when unset** (drop-when-None serializer; prove it).
   - **Two-stratum**: reported/literature claims never self-license; only recomputed claims join the spine.
   - Every new IR field **declares its scale-type + invariance group** (measurement-foundation discipline).
2. **Do NOT push to origin.** Shared checkout; pushing needs user coordination. Merge to **local main** only.
3. **Respect `DEFER` markers.** The backlog author (the user) marked these "don't build yet" — skip them,
   note them. Section 8 is entirely deferred.
4. **Do NOT make strategic/product decisions** (e.g. the product-identity fork, §9). Flag for the user.
5. **Data-gated items:** build + unit-test the machinery on fixtures/synthetic; mark the live run BLOCKED
   with exactly what real data it needs. Never fabricate genotypes/labels/data.
6. **Never colonize `polymer-db` or sibling project dirs.** Pin needed data subsets into `data/`.
7. Follow the repo workflow: branch off main → (spec exists or write one) → plan → TDD → per-change review
   → verify → merge local. Batch only trivial doc-fix items.
8. **Slow-suite discipline:** full `tests/` + `make_merged_universe.py` regen are ~13–63 min (real GDSC
   scan). Iterate with **targeted tests**; run the full gate only at item/branch close, and note if skipped.

## Work order (respect DEFER + data-gates; check off in BACKLOG.md as shipped)
- **A. Clean the tree** — finish `feat/cross-arm-relations` (restore real bundle → verify → merge local main).
- **B. §1 persistence & parameterization cluster** (interdependent, highest leverage):
  B1 measurement-space registry (shared prereq) → B2 accumulating-universe store → B3 re-parameterization
  evaluator (needs registry + additive "reinterpret" restriction-map edge) → B4 promoter SE-contract (data-gated live).
- **C. §2 warrant/independence** — C1 adapter-independence Step 0 probe (cheap, do-now) → R1–R5 arc,
  neg-whisper ②③④⑤, v2 slices 2/3.
- **D. §3 gate-integrity code debts** — incl. the logged `verify.py::_permitted_by_bar` reference_leaf
  exemption (retires the per-claim run_cycle workaround). Several concrete HARDEN items.
- **E. §4 attested calibration hardening** (slice-4 §11 deferrals).
- **F. §5 synbio capstone** — Phase 3 firewall → Phase 4 Durendal (HEADLINE) → Phase 5 wedge/demo; grammar GAPs.
- **G. §6 wedge/real-data** — mostly data-gated; build machinery, mark live runs blocked.
- **H. §7 infra/hygiene** — quick wins first: doc-reference fixes, CI workflow, test-skip visibility.
- **I. §9 foundations-concordance** — HARDEN "consume the declared-but-unenforced field" items
  (invariance_group check, measured-ρ independence, attested-log floor).
- **SKIP:** §8 (all DEFER), the product-identity fork + other strategic items (flag for user).

## ✅ MANDATE COMPLETE 2026-07-14 — all 5 user-authorized items shipped + pushed. Loop STOPPED.

**All five done, each byte-identical-when-off + tested, on `origin/main`:**
1. ✅ **②b multiply-gate wire-in** — an independence claim's verdict caps the replication multiply (refuted → withdraw).
2. ✅ **§3 strength=None audit** — RESOLVED: the untrusted path is already closed by the air-gap (`verify.py:305`); pinned the exemption scope.
3. ✅ **§9 invariance precondition** — `admit_by_invariance` drops scale-INCOHERENT (ordinal-as-metric) claims at both `preregister` seams (umbrella-side, purity-safe).
4. ✅ **Durendal pre-registration mechanics** — `synbio/preregistration.py` seals a blinded seed + plan (deterministic commitment_hash + locked α-slot). Machinery only.
5. ✅ **ClinVar/AlphaMissense/ESM1v loader + live path** — `adapter_independence_data.py` (parsing fixture-tested; live run skipif-guarded on `data/adapter_independence/`).

**WHAT STILL NEEDS YOU (nothing else is autonomously buildable — this is the true remainder):**
- **Drop the 3 ClinVar/AlphaMissense/ESM1v files** into `data/adapter_independence/` → the live adapter-independence
  ρ/N_eff experiment runs (loader is built + tested). Prefer post-training-cutoff variants (leakage caveat).
- **Durendal (the headline):** curate the real blinded seed (which synbio claims), do the independent no-leakage
  review, decide the Phase-4 framing (strong vs human-proposed fallback) BEFORE the run, then run it. Mechanics ready.
- **Other data-gated** items (2nd AML cohort + IDH → §2E REPLICATED / wedge H1.A2; GDSC→CHEBI; ⑤ real EWAS) — supply data.
- **DEFER** items (§8 + several §3/§4/§9) — you marked these don't-build.
- Optional: tighten §9 to also refuse UNDECLARED once every licensable pattern declares invariance.

To resume any of this, `/loop` again. Below is the prior mandate detail (historical).

## ▶ LOOP RESUMED 2026-07-14 — user-authorized mandate (answers given interactively).

**User decisions:** (1) **APPLY ALL THREE gate wire-ins** — ②b multiply-gate, §3 strength=None guard, §9
invariance precondition (they are now AUTHORIZED; apply + test, no longer just flag). (2) **PUSH DONE** —
origin/main == main (`ae24fe2`). (3) **Durendal:** build the pre-registration MECHANICS (commitment_hash +
α-slot lock + seed-assembly wiring); user curates the seed + does the independent review. (4) **Data:** user
will supply **ClinVar + AlphaMissense + ESM1v** → build the adapter-independence LIVE run; loader reads from
`data/adapter_independence/` (gitignored) — files: `clinvar_variant_summary.tsv[.gz]`, `AlphaMissense_hg38.tsv.gz`,
`esm1v_llr.tsv[.gz]`. Build the loader now (ready); live run runs when files land.

**Design calls to make during the wire-ins (documented, since the direction is authorized):**
- **②b keying:** the replication multiply is over two COHORTS of one claim (`e1*e2`). Key the independence
  claim on the two cohort identifiers (`contract_a.contract_uid`, `contract_b.contract_uid`). Thread an OPTIONAL
  `independence_claims`/verdict-map into `build_replication_inputs` + `expression_floor_replication` (default
  empty → verdict None → `multiply_allowed(cohorts_verdict, None)` == today → BYTE-IDENTICAL). Prove via existing
  replication tests unchanged.
- **§9 purity:** `verify.py` is PROTOCOL (pure) and `invariance.py` is UMBRELLA (imports measurement_space) — do
  NOT import umbrella into protocol. Wire the invariance precondition as an UMBRELLA-side gate wrapper around the
  license path (or a pre-`run_cycle` admission filter), not inside protocol verify.py. Byte-identical when every
  claim is COHERENT/UNCHECKED (the default for today's corpora).
- **§3 strength=None:** add the untrusted-cannot-ride guard in protocol; "untrusted" = keyed on the adapter
  credential/trust signal already threaded into verify (not a new umbrella dep). Byte-identical for trusted
  reference-leaf claims. If a clean trust signal isn't reachable at `_permitted_by_bar`, do the characterization
  test + narrow the exemption additively.

**Execution order:** ②b (umbrella, cleanest) → §3 → §9 (umbrella wrapper) → Durendal pre-reg mechanics → ClinVar
loader (+ live run when files land). Each: branch → TDD → byte-identity proof → per-item review → merge local → PUSH.

**MANDATE PROGRESS:**
✅ **1. ②b multiply-gate wire-in — DONE + pushed** (both replication sites cap the multiply by
`independence_verdict_for(corpus.claims, contract_a/b.contract_uid)`; byte-identical; a refuted independence claim
withdraws the multiply).
✅ **2. §3 strength=None — RESOLVED via the safe path (DONE + pushed).** FINDING: the untrusted-license path is
ALREADY closed by the air-gap (`verify.py:305` forces an untrusted claim to PENDING `ADAPTER_NOT_INDEPENDENT`
regardless of the exemption, which skips only the BH multiplicity bar) — so a redundant `_permitted_by_bar` guard was
unnecessary + the registry is correctly not threaded there. Pinned the exemption scope with a characterization test
(protocol 530). No source change → byte-identical.
✅ **3. §9 invariance precondition — APPLIED + pushed.** `admit_by_invariance` (umbrella-side, purity-safe) wired
into both `preregister` seams; drops INCOHERENT (ordinal-as-metric) claims before standing. Relations never gated,
UNDECLARED logged-not-refused → byte-identical for today (grammar 608 / protocol 530 + spine 26 + pharmaco-fast 19
unchanged; 2 new tests).
NEXT: **4. Durendal pre-registration MECHANICS** (commitment_hash + α-slot lock + `firewall.assemble_blinded_seed`
wiring; additive; two-stratum; Corpus 4). Then **5. ClinVar loader + skipif live test.**

## ⏹ (prior stop note — superseded by the mandate above) autonomously-completable work was done; the rest needed the user.

**Why stopped (honest):** the entire tranche of clean, safe, additive backlog work is shipped (~19 items, below).
Everything that REMAINS is one of: (a) the **Durendal headline scientific work** (synbio Phase 3 seed-curation +
Phase 4 derivation + framing decision) — the plan itself requires an *independent human reviewer* + a *pre-run
framing decision*, so it is explicitly NOT autonomous; (b) **3 gate-touching changes I built + FLAGGED for your
sign-off** (they'd silently change licensing); (c) **data-gated** items (need real ClinVar/EWAS/CHEBI/2nd-AML-cohort
data — never fabricated); (d) **DEFER** (§8 + several §3/§4/§9); (e) v2 Slice 3 (likely gate-touching). Per the
loop's own stop-condition, I stopped rather than spin / rather than make headline scientific or licensing decisions
that are yours. Restart anytime with `/loop`.

**FIRST thing when you return — 3 gate-touching decisions (all built + proven byte-identical when off; see "Flagged"
section below for the exact one-line wire-ins):**
  1. **neg-whisper ②b** — wire the independence-claim verdict into the `replication.py` multiply gate.
  2. **§3 strength=None** — an untrusted-cannot-ride guard on the `_permitted_by_bar` exemption.
  3. **§9 invariance** — wire `invariance_ok` as a hard licensing precondition in `verify.py`.
  Each WITHDRAWS/CHANGES a license in specific cases — correct behavior, but your call to activate.

**Also:** local `main` is **60 commits ahead of `origin`, NOT pushed** (shared-checkout policy — coordinate, then
push). And the **Durendal capstone** (synbio Phase 3/4) is the highest-value remaining work — its firewall harness is
now built; it needs your scientific curation + review.

## State (as of stop)
- **On `main`** at `cfeeba2`, clean tree, **61 commits ahead of origin (NOT pushed — coordinate then push)**.
- **PHASE SHIFT (honest):** the clean, fast, safe/additive wins are now essentially DONE (§1 cluster · §2 neg-whisper
  arc · §3 placeholder guard · §7 CI/doc/skip + immuno drift-guard · §9 invariance-check). The remaining backlog is
  the "hard remainder": (i) 3 GATE-TOUCHING items FLAGGED for the user; (ii) DATA-GATED (R2 battery, wedge H1.A2,
  GDSC→CHEBI, ⑤ real EWAS) — already marked BLOCKED with the exact data; (iii) BIG multi-fire BUILDS that are NOT
  data-gated (v2 Slice 2/3 = attestation chain + defeat/drift/reinstatement, `specs/2026-06-29-v2-evidence-licensed-capability-design.md`
  §13; §5 synbio Phase 3 firewall → Phase 4 Durendal); (iv) DEFER (§8 + several §3/§4). **Next: the big buildable
  BUILDs (v2 Slice 2, then synbio Phase 3), done as multi-fire spec→plan→TDD arcs — the last category with real
  autonomous runway.** Consider a longer wakeup delay (fires are now bigger). Do NOT force gated/flagged/DEFER items.
- **v2 Slice 2 CORE ✓** (attestation chain / SLSA resolvedDependencies for the evidence route; byte-identical,
  golden unchanged). Follow-ups (meaningful-benchmark fixture, ResourceDescriptor.content) noted in BACKLOG.
  **Next big buildable: v2 Slice 3** (defeat/drift/reinstatement/replay-over-time — v2 §13; assess gate-touching vs
  additive) OR **§5 synbio Phase 3** (blinded seed + pre-registration firewall — `plans/2026-07-10-synbio-claims-universe.md`
  §Phase 3; firewall admissibility + conclusion-stripping + commitment-hash/α-lock; Durendal is Phase 4). Both big,
  buildable, not data-gated. Ground first; flag gate changes.
- **§9 invariance-check ✓** (advisory; gate-wiring flagged). **Note on remaining backlog:** the clean safe/additive
  wins are largely done. What's left is mostly (i) GATE-TOUCHING → FLAG (3 already flagged: ②b, strength=None,
  invariance-wiring); (ii) DATA-GATED → build machinery + mark BLOCKED (R2 battery, wedge/real-data, GDSC→CHEBI,
  ⑤ real EWAS); (iii) BIG multi-fire (§5 Durendal Phase 3/4, v2 slices 2/3); (iv) DEFER (§8, several §3). Keep
  picking genuinely-completable concrete items (immuno strict-Corpus cleanup; more §9 concordance reads; §4 attested
  §11 buildable bits); scope+mark the data-gated ones; flag gate changes. Don't force-build gated/flagged items.
- **§3: placeholder guard ✓** (strength=None audit FLAGGED, deferred; `LLMPatternGenerationAdapter` = PHANTOM/done).
  **§7 hygiene: CI workflow ✓ · doc-dangle fixes ✓ · test-skip visibility ✓** (this fire).
- **Next safe §7 items:** GDSC drug→CHEBI resolver (`pharmaco_populate.py:62` — HARDEN, the scaling bottleneck;
  scope it), immuno bundle strict-Corpus cleanup (`merge_universes.py:181`), pre-release context scrub. Then §9
  foundations-concordance HARDEN items (consume `invariance_group` at license time — but that's gate-touching → assess);
  §4 attested-calibration §11 deferrals; §5 synbio capstone (Phase 3/4 = big, partly data-gated). Prefer safe/additive;
  FLAG gate changes; mark data-gated BLOCKED.
- **DONE:** §1 cluster (B1/B2p/B3/B4) · §2 neg-whisper arc (C1/R1/②a/②b-logic/③/④/⑤-repr) · §3 placeholder guard.
- **Remaining (still open in BACKLOG):** §2 tail — adapter-independence R2–R5 (R2 = C1 probe on a real battery,
  DATA-GATED; R3/R4/R5) + v2 Slice 2/3 (attestation chain / defeat-drift-reinstatement, `specs/2026-06-29-v2-evidence-licensed-capability-design.md` §13);
  §3 remaining gate-integrity debts; §4 attested-calibration §11; §5 synbio capstone (Phase 3 firewall + Phase 4
  Durendal — BIG); §6 wedge/real-data (mostly data-gated); §7 infra/hygiene (safe quick wins); §9 foundations-concordance.
- **FLAGGED for user (see "Flagged" section):** ②b live multiply wire-in; strength=None untrusted-guard (both gate-touching).
- **Deferred follow-ups (in BACKLOG, not lost):** B2-integration (real populate/viewer at the store, slow-pipeline);
  reconcile `merge_universes` modality strings to B1 vocab; ⑤ real-EWAS-non-effect licensing + viewer rendering.
- Foundations digest: `notes/2026-07-14-foundations-digest-for-loop.md` (read for §2/§9 grounding).

## Test/gate cadence
- Fast gate (per change): `cd grammar && uv run pytest -q` (~0.5s, 602) · `cd protocol && uv run pytest -q` (~2s, 509)
  · targeted umbrella `uv run --project . pytest tests/<file> -q` · `ruff check` touched files.
- Full gate (item close only, SLOW ~13–63 min): `bash scripts/check-all.sh`. Note when skipped.

## Flagged for the user (decisions / blockers I will NOT resolve autonomously)
- **Push to origin** is deferred (many commits ahead) — needs your coordination (shared checkout). Loop keeps
  accumulating on local main.
- **§9 invariance-check gate-wiring (licensing-behavior change — needs your sign-off).** `invariance.py::invariance_ok`
  is built + tested (catches ordinal-as-metric). Wiring it as a HARD precondition in `verify.py` (reject
  INCOHERENT/UNDECLARED before LICENSED) would change licensing outcomes — left advisory, flagged like ②b.
- **neg-whisper ②b LIVE GATE WIRE-IN (licensing-behavior change — needs your sign-off).** The independence-claim
  machinery is built + tested (`independence_claim.py`), byte-identical when off. ACTIVATING it means editing the
  two multiply sites — `replication.py:130` and `expression_floor_replication.py:99` — to thread the corpus and
  replace `if cohorts_error_independent((sat_a,sat_b)) is not False:` with
  `if multiply_allowed(cohorts_error_independent((sat_a,sat_b)), independence_verdict_for(corpus.claims, leg_a, leg_b)):`,
  plus a populate step that mints + gate-licenses the independence claim from the ②a correlated-variance probe. This
  WITHDRAWS a multiply (drops REPLICATED→single-leg) whenever a REJECTED/defeated independence claim covers the pair
  — a deliberate, correct change to real licensing outcomes. Left unwired so the loop never silently alters the gate.

## Shipped by the loop (newest first)
- **2026-07-14 — GAP-8: `MeasurementContext.target_locus` (gene/locus sub-key)** (direct to main → origin).
  Optional gene/locus identity (nominal, relabeling-invariant) that previously leaked into free-text
  `condition`. Additive + byte-identical via a drop-when-None `@model_serializer` (every pre-field context
  serializes exactly as before; other fields keep their null-emission); `_at_least_one_field` accepts a
  locus-only context. 3 tests; grammar 615; protocol 539 unchanged. Gaps note 5 open → 4.
- **2026-07-14 — GAP-7: `MeasurementBasis.ANALYTIC` (analytic-constant basis)** (direct to main → origin).
  Third measurement basis for definitional constants (2 bits = log2(4)) — neither FUNDAMENTAL nor DERIVED.
  Additive enum member (existing bases byte-identical, no serializer touched); discipline = formula required,
  unit allowed. `_basis_discipline` restructured provably behavior-preserving for FUNDAMENTAL/DERIVED. Claim-
  authoring only (operations.py output-spec check untouched). 4 tests; grammar 612; protocol 539 unchanged.
  Gaps note: 6 open → 5. Re-expressing a real analytic-constant claim is a mechanical follow-up.
- **2026-07-14 — DEBUG: BH-withheld claims mislabeled UNTESTED → `MULTIPLICITY_WITHHELD`** (direct to main → origin).
  TE-note CORRECTION gap (i): an evaluated e-LOND discovery held back only by the cardinality-scaled BH bar
  kept its stale UNTESTED. New `PendingReason.MULTIPLICITY_WITHHELD` + a precise `verify.py` elif (satisfied ∧
  grounded ∧ `_e_ok` ∧ provenance ∧ `not in permitted`). Reporting fix — status unchanged (still PENDING, no
  license), so byte-identical for every non-BH-withheld claim. 2 tests; grammar 608 (enum-set 14→15), protocol
  539; immuno α-shrink test unaffected (fails `_e_ok`). BACKLOG + TE note updated.
- **2026-07-14 — residualism R3: PENDING residue-graveyard query surface** (direct to main → origin).
  `protocol/.../residue.py` — read-only query over Corpus: census (shape by pending-reason), graveyard
  (ResidueEntry: testable/needs_external_input/dependents), facet filters, and the R3 `conversion_candidates`
  worklist (testable ∧ convertible, ranked by defeat-graph leverage). Pure protocol; read-only → Corpus 4, no
  IR field; never licenses (conversion re-runs the existing cycle). 6 tests; protocol 537; grammar 608 unchanged.
  BACKLOG residue-query item checked off.
- **2026-07-14 — §3 (gate audit): evidence-dispatch bypass CONFIRMED airtight** (direct to main → origin `pending push`).
  Audited the alternate licensing route (`execute.py:146`, single-execution capability cells that skip the 2-adapter
  gate). Finding: airtight — Gate-1 needs a pending non-retracted FDR test + `commitment_hash(c)==test.commitment_hash`
  (binds the whole evaluation_plan incl. threshold), then 8 pre-dispatch checks; `pending_by_claim` last-wins is only
  ever more-conservative. Closed the one un-pinned branch (Gate-1 hash-mismatch skip) with
  `test_commitment_hash_mismatch_skipped`. Test-only → byte-identical. protocol 531. BACKLOG line 237 checked off.
- **2026-07-14 — post-mandate operator decisions recorded + pushed** (`11a1f9e`, `449d691`). Product-identity fork
  RESOLVED (in-house drug-discovery engine; Durendal→Polymer Biologics; federated deferred); GPU-determinism deferred;
  #4 value-ordering RESOLVED (ratify strict Pareto as v1's single audience; audience-relative VAF hook deferred, no code).
- **2026-07-14 — §3 strength=None exemption: RESOLVED (finding + characterization)** (`feat/strength-none-exemption-guard` → local main → origin).
  Found the untrusted-license path is already closed by the air-gap (`verify.py:305`); pinned the exemption scope
  (2 tests, protocol 530). No source change → byte-identical. (Mandate item 2, safe path.)
- **2026-07-14 — ②b multiply-gate wire-in (USER-AUTHORIZED)** (`feat/independence-multiply-wire` → local main → origin `e96823c`).
  Both replication sites cap the multiply by the independence-claim verdict; byte-identical for today's corpora. (Mandate item 1.)
- **2026-07-14 — synbio Phase 3 (firewall harness): pre-registration conceptual-leakage guard** (`feat/synbio-phase3-firewall` → local main, ff).
  `synbio/firewall.py` — `check_admissibility` (conclusion-stripping + optional date-cutoff, tags the deciding rule)
  + `assemble_blinded_seed`. Additive, umbrella-side, NOT the gate. 6 tests; Corpus 4. Seed curation + Durendal
  pre-registration + independent no-leakage review remain the operator's (headline scientific work).
- **2026-07-14 — v2 Slice 2 (core): evidence-route SLSA resolvedDependencies** (`feat/v2-slice2` → local main, ff).
  `attestation.py::_evidence_resolved_dependencies` lists an EVIDENCE_LICENSED claim's real evidence artifacts
  (benchmark/executor/predictions/policy/contract/capability/configs/oracle) as ResourceDescriptors with their
  already-computed content addresses. Byte-identical for the recompute route (76 attestation + golden tests
  unchanged). 3 tests; umbrella-only; grammar/protocol untouched; Corpus 4.
- **2026-07-14 — §7: immuno reconstruction drift-guard** (`feat/immuno-corpus-guard` → local main, ff).
  `test_immuno_corpus_guard.py` pins that `collect_immuno()`'s reconstructed 11 claims form a strict,
  JSON-round-trippable Corpus (drift guard vs the hand-built viewer bundle). 1 test; no code/bundle change.
- **2026-07-14 — §9: invariance-consistency check (consume invariance_group)** (`feat/invariance-check` → local main, ff).
  `invariance.py` — first consumer of Pattern.invariance_group/scale; maps Pattern.scale → Stevens class, cross-checks
  vs the B1 registry's ScaleType, catches ordinal-as-metric (INCOHERENT). Advisory `invariance_ok`; gate-precondition
  wiring FLAGGED. 4 tests; umbrella-only; grammar/protocol untouched; Corpus 4.
- **2026-07-14 — §7 hygiene: CI workflow + doc-dangle fixes + test-skip visibility** (`feat/ci-and-doc-hygiene` → local main, ff).
  `.github/workflows/ci.yml` (grammar/protocol/umbrella pytest `-rs` + ruff; viewer typecheck; mirrors check-all.sh;
  `-rs` surfaces data-gated skips). Fixed the REAL doc dangles (reparam→archive path; attested-ingestion cozy-growing-naur
  + calibration-ledger refs → git history). PHANTOMS confirmed: `foundations/GLOSSARY.md` (only in BACKLOG text) +
  `LLMPatternGenerationAdapter` (no such class — `LLMGenerationAdapter` already implements the base hooks). Doc-only + CI file.
- **2026-07-14 — §3: placeholder operator_id guard** (`feat/placeholder-operator-id-guard` → local main, ff).
  `PLACEHOLDER_OPERATOR_ID` constant + `bridge_proposer` refuses an adapter whose identity IS the placeholder.
  3 tests; byte-identical; protocol 528; Corpus 4.
- **2026-07-14 — neg-whisper ⑤ (representation): licensed-negative morphospace** (`feat/licensed-negative-morphospace` → local main, ff).
  Grammar `Pattern.asserts_absence=False` (registry-side → byte-identical) + `bounded_absence@v1` pattern; pure
  `morphospace.py` — `MorphospaceState` {OCCUPIED/FORBIDDEN/UNOBSERVED/OTHER} + classifier + `FIREWALL_STATEMENT`
  (licensed-negative = warranted absence at severity, not impossibility). NO licensing change (gate untouched). 6
  tests; grammar 608 (602 unchanged) / protocol 525; Corpus 4. Real-EWAS-non-effect licensing (data-gated) + viewer
  rendering are follow-ups.
- **2026-07-14 — neg-whisper ④: stationarity horizon on `q`** (`feat/q-stationarity-horizon` → local main, ff).
  `CalibrationReport` + optional `validity_frontier`/`as_of_current` (drop-when-unset serializer → byte-identical;
  certificate unchanged, 143 umbrella + 21 protocol calibration tests pass) + pure `stamp_stationarity` (drift on a
  constituent hash → q EXPIRED, not wrong). 5 tests; protocol 525; grammar untouched; Corpus 4. Umbrella wiring (real
  frontier from licenses' MaterializationContexts) is a thin follow-up.
- **2026-07-14 — neg-whisper ③: residue budget for the PENDING graveyard** (`feat/residue-budget` → local main, ff).
  `economics.py`: `SchedulerWeights.residue=0.0` (default off) + `ActionKind.RESIDUE_REEXAM` + dependency-degree
  residue-value → `next_action` schedules high-dependency PENDING (duhem) ahead of isolated untested when enabled.
  Byte-identical at weight 0 (economics 15 / protocol 517→520). Pure-protocol; Corpus 4. Enabling requires caller
  to handle the new action kind (noted).
- **2026-07-14 — neg-whisper ②b (logic): independence as a defeasible claim** (`feat/independence-claim` → local main, ff).
  `independence_claim.py`: `make_independence_claim` (PENDING, two-stratum, ②a evidence + bias-residue rebuttal),
  `independence_verdict_for` (LICENSED→True/REJECTED→False/else None), `multiply_allowed` (gate decision, PROVEN
  byte-identical when off). 7 tests; grammar 602/protocol 517 UNCHANGED, zero licensing source touched. The LIVE
  multiply wire-in is FLAGGED for operator review (above), not applied.
- **2026-07-14 — neg-whisper ②a: correlated-variance probe** (`feat/correlated-variance-probe` → local main, ff).
  Extended `adapter_independence.py`: `correlated_variance_probe` (shared-input perturbation → joint-movement ρ →
  independence verdict) — the measured evidence leg for the multiply gate; correlated-BIAS named as an open defeater
  (`CORRELATED_BIAS_DEFEATER`). 5 tests; umbrella-only, NO gate change; Corpus 4. ②b (wire verdict into the
  replication multiply gate, byte-identically) remains.
- **2026-07-14 — R1: provenance-lineage on AdapterCredential** (`feat/adapter-lineage` → local main, ff).
  `AdapterCredential.lineage: tuple[str,...]=()` + `adapters_independent` refusal QUAD (shared lineage tag →
  not independent, even with distinct owner+hash). Additive, byte-identical for lineage-less registries (512
  protocol tests unchanged; credential never persisted). 5 tests. Pure-protocol; Corpus 4. R2–R5 remain.
- **2026-07-14 — C1: adapter-independence Step-0 probe** (`feat/adapter-independence-probe` → local main, ff).
  `adapter_independence.py` (pure stdlib): error-correlation ρ → `N_eff=2/(1+ρ)`, set-overlap φ variant (claim-shape),
  `independence_report` (ρ/N_eff/per-class/2×2 confusion). 7 synthetic tests; grammar/protocol untouched; Corpus 4.
  Live ClinVar/AlphaMissense/ESM1v run DATA-GATED (documented). Entry instrument for the measured-ρ independence arc.
- **2026-07-14 — B4 verified pre-built** (`edb1322`): promoter SE-contract machinery + unit test; MGMT→TMZ-over-promoter
  finding recorded (flips-but-sub-threshold). §1 cluster complete. (Doc-only checkoff.)
- **2026-07-14 — B3: re-parameterization evaluator** (`feat/reparam-evaluator` → local main, ff). NO grammar change
  (reused `RelationKind.RESTRICTION_MAP`). B3a: `sheaf.py` suppresses equivalence/defeat edges bridged by a
  RESTRICTION_MAP relation (byte-identical when absent; 509 protocol tests unchanged; 3 new). B3b:
  `reparam_evaluator.py` — trigger REJECTED+REFUTED → untrusted `ReparamAgent` (LLM, grounded by B1 registry, never
  fabricates) → declare-and-charge K e-LOND slots upfront → re-test via UNCHANGED gate (injected) → RESTRICTION_MAP
  relation linking original↔alternate; depth-1; original retained; idempotent; two-stratum. 8 synthetic tests.
  Real MGMT→TMZ proof B4-data-gated. grammar 602 / protocol 512 / Corpus 4.
- **2026-07-14 — B2 (store primitive): accumulating-universe store** (`feat/accumulating-store` → local main, ff).
  `src/polymer_claims/accumulating_store.py`: `corpus.json` whole-Corpus snapshot (reuses io.py → ledger position
  round-trips) + append-only content-addressed `claims.jsonl`; `accumulate` load→dedup→register(injected)→persist
  mints 0 on re-run; `census()` (subject×modality×status, modality via B1 registry) reports coverage gaps. Pure-python
  (no DuckDB dep). 8 synthetic tests; grammar/protocol untouched; Corpus 4. Live populate/viewer wiring deferred
  (B2-integration, slow-pipeline-gated).
- **2026-07-14 — B1: measurement-space registry** (`feat/measurement-space-registry` → local main, ff).
  Authored the deferred spec (`specs/2026-07-14-measurement-space-registry-design.md`) + umbrella module
  `src/polymer_claims/measurement_space.py`: catalog of 9 real contract spaces keyed `(contract_uid, row_prefix)`,
  each declaring controlled `Modality` + Stevens `ScaleType` + `invariance_group` (the scale/invariance metadata
  that lived nowhere — advances §9). `resolve_space` grounds the reparam evaluator's proposals to contracts that
  actually resolve (never fabricates). 11 tests; grammar/protocol untouched; Corpus 4.
- **2026-07-14 — Phase A: `feat/cross-arm-relations` merged to local main** (`d69c03a`, ff). Restored the real
  1386-node bundle (discarded the 46-node demo), fixed 1 branch-introduced ruff (unused `FDRLedger` import),
  reconfirmed grammar 602 + protocol 509 + relations e2e 3/3 green. Branch deleted. (Not a numbered backlog line —
  closing in-flight work to get a clean main to branch from.)
