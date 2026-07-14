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

## State (update every fire)
- **On `main`** at `3a140fe` (about to merge ③), clean tree, **NOT pushed — policy**.
- **§1 COMPLETE** (B1/B2p/B3/B4) + **§2: C1 ✓ · R1 ✓ · ②a ✓ · ②b-logic ✓ (wire-in FLAGGED) · ③ ✓.**
- **Next: neg-whisper ④** — stamp corpus `q` with a drift-epoch / validity window so the actuarial framing carries
  its stationarity assumption; `q` expires when a watched dependency drifts. Spec `2026-07-07-neg-whisper-backlog-design.md`
  §5. GROUND on where `q` is computed/stored (grep `q_`/`feeds_headline_q`/calibration certificate/`q` in
  `src/polymer_claims/` — the calibration ledger). Additive + byte-identity when the window is unset. Then ⑤
  (severity-backed licensed-negative: forbidden vs unobserved — §6, largest of the four; touches licensing-not-meaning
  firewall — scope carefully, may need a flag) → v2 slices 2/3 → §3 gate-integrity debts. Each: branch → TDD →
  byte-identity proof → merge local.
- **Deferred follow-ups (tracked in BACKLOG, not lost):** B2-integration (wire real populate_universe + viewer at
  the store — slow-pipeline-gated); reconcile `merge_universes` hard-coded modality strings to the B1 controlled vocab.
- Foundations digest: `notes/2026-07-14-foundations-digest-for-loop.md` (read for §2/§9 grounding).

## Test/gate cadence
- Fast gate (per change): `cd grammar && uv run pytest -q` (~0.5s, 602) · `cd protocol && uv run pytest -q` (~2s, 509)
  · targeted umbrella `uv run --project . pytest tests/<file> -q` · `ruff check` touched files.
- Full gate (item close only, SLOW ~13–63 min): `bash scripts/check-all.sh`. Note when skipped.

## Flagged for the user (decisions / blockers I will NOT resolve autonomously)
- **Push to origin** is deferred (many commits ahead) — needs your coordination (shared checkout). Loop keeps
  accumulating on local main.
- **neg-whisper ②b LIVE GATE WIRE-IN (licensing-behavior change — needs your sign-off).** The independence-claim
  machinery is built + tested (`independence_claim.py`), byte-identical when off. ACTIVATING it means editing the
  two multiply sites — `replication.py:130` and `expression_floor_replication.py:99` — to thread the corpus and
  replace `if cohorts_error_independent((sat_a,sat_b)) is not False:` with
  `if multiply_allowed(cohorts_error_independent((sat_a,sat_b)), independence_verdict_for(corpus.claims, leg_a, leg_b)):`,
  plus a populate step that mints + gate-licenses the independence claim from the ②a correlated-variance probe. This
  WITHDRAWS a multiply (drops REPLICATED→single-leg) whenever a REJECTED/defeated independence claim covers the pair
  — a deliberate, correct change to real licensing outcomes. Left unwired so the loop never silently alters the gate.

## Shipped by the loop (newest first)
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
