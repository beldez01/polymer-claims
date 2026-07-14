# Polymer Claims — Running Backlog

> The living to-do list for hardening, debugging, and building out Polymer. Compiled **2026-07-13**
> from three parallel discovery sweeps (design docs `specs/`+`plans/`+`notes/`; the `CONTINUE.md`
> primer + `2026-06-23-remaining-roadmap.md`; and a code+tests grep of `src/`/`grammar/`/`protocol/`/`tests/`).
> Every item traces to text in the repo. SHIPPED arcs are excluded (see `CONTINUE.md` for what's done).

**How to use this file.** Check items off as they ship (`- [x]`). Keep it deduped — one row per unit of
work. When you finish something, move its one-liner into `CONTINUE.md`'s shipped log and tick it here.
When a new gap is found while running claims (per the "flag engine gaps" discipline), add a row.

**Legend.** `BUILD` = unbuilt feature · `HARDEN` = partial / provenance / trust / robustness gap ·
`DEBUG` = known bug, degenerate path, or armed tripwire · `DEFER` = deliberately tabled, don't build yet.

**Ruled out — do NOT re-chase** (settled): e-BH as a "license-more" lever (licenses ~0 at n=696,
ruled out 2026-07-11); generic per-attack e-value combination ("largely a mirage").

**Status corrections found while compiling** (the primer had drifted):
- Attested-ingestion (calibration **slice 4**) MVP is **built**, not pending — `attested_ingest.py` +
  `ingest-attested` CLI + 3 tests exist. Only the §11 deferrals remain (§3.9 below). `CONTINUE.md`
  still calls slice 4 "next / spec awaiting build" — **update it**.
- The three daemons (DRIFT / ORACLE-VALIDATION / RED-TEAM) are **built**; the only unbuilt "SELECT"
  piece is semantic/EIG dedup in the representation layer (§3.11).

---

## 1. Near-term critical cluster — persistence & parameterization
*Interdependent, mostly approved-but-unbuilt, each unlocks the next. Highest actionable leverage.*

- [x] **Accumulating-universe store (persistent claim log)** · `BUILD` · `specs/2026-07-10-accumulating-universe-store-design.md` §6
  — Append-only content-addressed JSONL + facet layer so re-runs mint 0 new claims and the `fdr_ledger`
  accumulates. Today the merge is a static union / fresh `Corpus` per run, not a persistent store.
  — **STORE PRIMITIVE SHIPPED 2026-07-14 (loop)** on `feat/accumulating-store`.
  `src/polymer_claims/accumulating_store.py`: `AccumulatingStore(root)` = `corpus.json` authoritative
  whole-Corpus snapshot (reuses `io.load_corpus/dump_corpus`, so the live `fdr_ledger` position round-trips
  verbatim) + append-only content-addressed `claims.jsonl` (audit/dedup/census). `accumulate(proposed,
  register_license)` load→dedup(by id, vs log+corpus+within-batch)→register+license(INJECTED, generic)→
  persist-back — **re-run mints 0** (tested), ledger appends as a stream (tested, first wave byte-identical
  after 2nd). `census()` = (subject×modality×status) coverage over the snapshot, modality derived from
  `data_ref` via the B1 registry (no grammar field), reports coverage-gap cells. DuckDB not a dep → pure-python
  census. 8 tests on synthetic corpora; grammar/protocol untouched; Corpus 4.
  — Deferred (noted in module/spec): two-file crash-atomicity (self-correcting via corpus-id dedup),
  subject-CLASS coarsening (v1 is exact-subject), pure-JSONL-as-sole-source (v1 = snapshot+log).
- [ ] **B2-integration: wire the real `populate_universe` + viewer at the store** · `BUILD` · store spec §6.2–6.4
  — Point `pharmaco_populate.populate_universe` (and the methyl/spine populate paths + CLI) at
  `AccumulatingStore` instead of a fresh `Corpus()` each run; regenerate the viewer bundle from the store with
  facet filters. **SLOW-PIPELINE-GATED** (the ~13-min real GDSC scan) — the loop deferred it to keep the store
  primitive fast+fully-tested; do it behind the full-gate discipline. This is what closes the "code is ephemeral
  per run" gap in the LIVE pipeline (the primitive already closes it structurally + is proven on synthetic runs).
- [x] **Measurement-space registry** · `BUILD` · accumulating-store §7 + reparam-evaluator §7
  — Keyed catalog of available SE-Contract dimensions per assay. *Shared prerequisite of the store AND
  the evaluator ("one registry, two consumers").*
  — **SHIPPED 2026-07-14 (loop)** on `feat/measurement-space-registry`. Both specs deferred the schema →
  authored `specs/2026-07-14-measurement-space-registry-design.md`. Umbrella-side
  `src/polymer_claims/measurement_space.py`: a space = `(contract_uid, row_prefix)`; catalog of the 9
  real committed contract spaces (pharmaco gene-body/promoter meth+auc, fusion/cbf expr ×4, idh cg).
  Controlled `Modality` + Stevens `ScaleType` + `invariance_group` per space — the registry is the home
  for the scale/invariance metadata that lived nowhere (advances §9). Query API: `all_spaces`,
  `spaces_for_modality/contract`, `available_spaces` (grounds to contracts that resolve via
  `load_contract`), `resolve_space` (evaluator grounding — never fabricates), `coverage` (census).
  grammar/protocol untouched; Corpus 4; 11 tests. Follow-ups noted in spec §5 (entries→meta-claims,
  reconcile `merge_universes` modality strings).
- [x] **Re-parameterization evaluator** · `BUILD` · `specs/2026-07-10-reparameterization-evaluator-design.md` §9
  — On REJECTED/REFUTED, LLM-propose + registry-ground alternate measurement spaces, declare-and-charge
  FDR, re-test; separates a true negative from a mis-parameterization. Only Step 0 (promoter SE-contract)
  is built. Deps: registry (above) + an additive grammar "reinterpret edge" (§4, still open).
  — **SHIPPED 2026-07-14 (loop)** on `feat/reparam-evaluator`. **NO grammar change needed** — the "reinterpret"
  non-contradiction edge already exists as `RelationKind.RESTRICTION_MAP` (cross-arm work; a relation CLAIM,
  Corpus stays 4). Two slices:
  **B3a (protocol)** — `sheaf.py` drops any equivalence/defeat edge whose endpoints are bridged by a
  RESTRICTION_MAP relation (non-comparable → no contradiction), completing the cross-arm Slice-1 "define/render-only"
  restriction_map into real sheaf/Duhem behavior. Pure, numpy-free, byte-identical when absent (509 tests unchanged);
  3 tests (frustrate → RESTRICTION_MAP suppresses → COHERES doesn't).
  **B3b (umbrella)** — `src/polymer_claims/reparam_evaluator.py`: trigger=REJECTED+REFUTED; `ReparamAgent` untrusted
  LLM (injected `complete` + `.anthropic` tripwire) proposes modalities re-validated to the controlled vocab,
  GROUNDED by the B1 registry to apt-AVAILABLE spaces (never fabricates); declare-and-charge all K e-LOND slots
  upfront (non-adaptive) via `register_test`+`commitment_hash`; re-test via the UNCHANGED gate (injected);
  depth-1; original REFUTED retained verbatim; emits a RESTRICTION_MAP relation linking original↔alternate
  (B3a consumes it). Two-stratum: LLM only narrows which re-test; only the gate licenses. Idempotent. 8 synthetic
  tests over real contract ids. **Real MGMT→TMZ numerical proof is B4-data-gated** (promoter contract live run).
  ⚠ **Name collision (resolved):** `DefeatEdgeKind.REINTERPRET` is an *attack* edge — correctly NOT reused; the
  non-contradiction edge is `RelationKind.RESTRICTION_MAP` (opposite polarity), exactly as this warning required.
- [x] **Promoter-methylation SE-Contract (2nd measurement dimension)** · `BUILD` · reparam §7 pre-req 0
  — Second contract dimension so MGMT→TMZ and promoter-localized claims can be re-tested over promoter
  β-space. Buildable/unit-testable on synthetic contracts now; **data-gated** on `methylation_promoter_bycosmic.csv.gz` / CCLE RRBS for the live run.
  — **ALREADY SHIPPED (`edb1322`, verified by loop 2026-07-14).** `ingest_gdsc_pharmaco_promoter` +
  `load_gdsc_promoter_methylation` build `se:gdsc_pharmaco_promoter@1` (metadata.modality=methylation_promoter);
  unit-tested (`tests/pharmaco/test_gdsc_pharmaco_contract.py::test_build_pharmaco_promoter_contract_loads_via_load_contract`,
  synthetic promoter matrix); in the B1 registry. **Live real-data finding already recorded:** MGMT→TMZ direction
  FLIPS to mechanistically-correct over promoter (r_adj +0.078→−0.069) but stays sub-threshold (e~0.81; compressed
  TMZ AUC + smaller cohort) — the honest "reparam over the right space, still doesn't license" outcome (spec §8).
  Real promoter betas gitignored (local-only subset). Nothing to build. The B3b evaluator can drive this end-to-end
  through the real gate as a slow-pipeline follow-up (finding already known).
- [x] **Cross-arm relations spec hardening** · `HARDEN` · `specs/2026-07-13-cross-arm-relations-design.md`
  — **Resolved 2026-07-13** across two review passes, folded into the spec. §0.1 (first pass): true signed
  projection is a Slice-1 addition (not assumed); relations project into a versioned `TopologyEdge` so the
  viewer sees them; concrete `ClaimSetSubject` IR (Corpus stays 4); dropped "singletons reproduce legacy
  edges"; new non-attack `RelationKind` instead of overloading `REINTERPRET`; corrected purity layering.
  §0.2 (second pass): explicit `model_serializer` for byte-identity (`_Model` has no `exclude_none`);
  sorted-`tuple` relata (not `frozenset`); concrete `RelationLeaf` in the `Leaf` union; signed-edge
  **sum-clamp** aggregation (not `max()`); `restriction_map` is define/render-only in Slice 1 (sheaf
  wiring → Slice 2); explicit `is_relation` protocol-lane guard. Ready for writing-plans pending final sign-off.

## 2. Warrant / independence / trust hardening
*Instrument the correlated bias, external testimony, drift horizons, and licensed negatives the gate
can't yet see. Plan-ready; each gated on a small first probe.*

- [x] **Adapter-independence Step 0 probe** · `DEBUG` · `plans/2026-07-07-adapter-independence-hardening-plan.md` §3
  — 1-day falsifiable experiment: do AlphaMissense vs ESM1v errors correlate on ClinVar? **Non-data-blocked, do-now.**
  Gates whether the D4 air-gap warrant is real or hollow, and sets the priority of R2–R5 below.
  — **PROBE MACHINERY SHIPPED 2026-07-14 (loop)** on `feat/adapter-independence-probe`.
  `src/polymer_claims/adapter_independence.py` (pure stdlib, no numpy): `signed_errors` (score−label),
  `error_correlation` (Pearson ρ), `n_eff_from_rho` (`N_eff = 2/(1+ρ)`), `set_overlap_neff` (φ of two flag-sets —
  the claim-shape variant per §R2: a single N_eff does NOT cap everything), and `independence_report` (ρ, N_eff,
  per-class ρ, 2×2 correctness confusion). 7 synthetic tests (identical errors→ρ1/N_eff1; orthogonal→ρ0/N_eff2;
  anti→N_eff>2; constant→nan; report+confusion; set-overlap). grammar/protocol untouched; Corpus 4. **LIVE run
  DATA-GATED/BLOCKED** (`run_variant_effect_probe` raises with the exact spec): needs ClinVar variant_summary +
  AlphaMissense_hg38 + ESM1v LLR tables, post-training-cutoff variants (leakage guard), threshold calibrated on a
  held-out split. The instrument is the entry point for the measured-ρ independence arc (foundations §2.B / §9).
- [ ] **Adapter-independence R1–R5 arc** · `HARDEN` · hardening plan §4 / `specs/2026-06-29-adapter-independence-hardening-notes.md`
  — Replace the hand-set organizational tier with measured error-correlation → `N_eff = 2/(1+ρ)`.
  R1 provenance lineage on `AdapterCredential` (ship-now); R2 decorrelation battery (after Step 0);
  R3 decorrelation red-team; R4 heterodox third witness; R5.2 shape-dependent strength cap.
  — **R1 SHIPPED 2026-07-14 (loop)** on `feat/adapter-lineage`: `AdapterCredential.lineage: tuple[str,...] = ()`
  (provenance-lineage tags: org / model family / training corpus / shared reference DB) + `adapters_independent`
  strengthened to a refusal QUAD — two adapters sharing ANY lineage tag are NOT independent even with distinct
  owner + implementation_hash (a shared training corpus makes differently-owned models fail together). Additive,
  byte-identical for lineage-less registries (all 512 protocol tests unchanged; not persisted in the Corpus);
  5 new tests. Pure-protocol; Corpus 4. **R2 (decorrelation battery) is the next sub-item** — feed C1's
  `adapter_independence` probe a real known-truth calibration battery (data-gated); R3/R4/R5 after.
- [ ] **neg-whisper ② — shared-cause independence as a defeasible claim** · `HARDEN` · `specs/2026-07-07-neg-whisper-backlog-design.md` §3
  — Promote the multiply-e-values gate from an operator flag to a licensable `independence` claim with a
  correlated-variance probe. "The load-bearing risk named in every doc." (Item ① shipped.)
  — **②a SHIPPED 2026-07-14 (loop)** on `feat/correlated-variance-probe`: the MEASURED evidence leg. Extended
  `adapter_independence.py` with the correlated-VARIANCE perturbation probe — `perturbation_responses` (deviation
  from baseline), `correlated_variance` (Pearson ρ of two legs' joint movement under a SHARED-input perturbation
  battery), `variance_independent` (|ρ|<τ), `correlated_variance_probe`→`CorrelatedVarianceReport`. The
  correlated-BIAS axis is recorded as a NAMED OPEN DEFEATER (`CORRELATED_BIAS_DEFEATER` — un-instrumentable from
  within, needs an external anchor / R4), never silently absorbed (spec §3 scope guard). 5 tests; umbrella-only,
  no gate change; Corpus 4. **②b REMAINS (gate-touching, next):** make independence a licensable CLAIM whose verdict
  (from this probe's e-value) caps the multiply in `replication.py:130` / `expression_floor_replication.py:99`
  (`cohorts_error_independent`, `grammar/.../licensing.py:156`) — ADDITIVE + BYTE-IDENTICAL when no independence
  claim present (default multiply behavior preserved); a defeat on the independence claim withdraws the multiply →
  single-leg standing. Do with byte-identity proof (existing licensing outcomes unchanged).
  — **②b LOGIC SHIPPED 2026-07-14 (loop)** on `feat/independence-claim` (standalone; live gate NOT wired — flagged):
  `src/polymer_claims/independence_claim.py`: `make_independence_claim` (a PENDING PropositionLeaf claim over a leg
  pair — TWO-STRATUM: carries the ②a correlated-variance verdict + e-value as evidence but is NOT self-licensed;
  bias residue as its standing rebuttal), `is_independence_claim`, `independence_verdict_for` (LICENSED→True /
  REJECTED→False / else None), and `multiply_allowed(cohorts_verdict, independence_verdict)` — the gate decision,
  PROVEN byte-identical to today when no independence claim (`multiply_allowed(v, None) == (v is not False)`).
  7 tests; grammar 602 / protocol 517 UNCHANGED (zero licensing source touched). **REMAINS: the live wire-in**
  (thread the corpus/verdict into `replication.py:130` + `expression_floor_replication.py:99` and replace
  `cohorts_error_independent(...) is not False` with `multiply_allowed(...)`) — a licensing-behavior change,
  **FLAGGED for operator review in LOOP-CONTROL**, not applied autonomously.
- [x] **neg-whisper ③ — residue budget for the PENDING graveyard** · `HARDEN` · neg-whisper §4
  — Residue-value term in `SchedulerWeights`/`economics.py` so PENDING (esp. `duhem_underdetermined`)
  earns scheduled re-examination instead of silently accreting. Byte-identical when weight = 0.
  — **SHIPPED 2026-07-14 (loop)** on `feat/residue-budget`: `SchedulerWeights.residue: float = 0.0` (default OFF) +
  `ActionKind.RESIDUE_REEXAM` + `_residue_value` (a PENDING claim's dependency degree = defeat/equivalence edges
  incident to it). When `residue>0`, `next_action` earns a re-examination targeting the highest-dependency PENDING
  claim, so a `duhem_underdetermined` claim in a contested region is scheduled ahead of an isolated `untested` one;
  a zero-dependency residue earns none (a budget, not a mandate — never auto-relicenses). **Byte-identical at
  weight 0** (economics 15 + protocol 517 unchanged → 520 with 3 new tests). Pure-protocol, numpy-free; Corpus 4.
  Note: a caller that ENABLES the residue weight must handle the new `RESIDUE_REEXAM` action kind (scheduler is
  recommend-only; today's callers key on RUN_CYCLE/DRIFT, so default-off is unaffected).
- [x] **neg-whisper ④ — stationarity horizon on `q`** · `HARDEN` · neg-whisper §5
  — Stamp corpus `q` with a drift-epoch / validity window so the actuarial framing carries its
  stationarity assumption explicitly; `q` expires when a watched dependency drifts.
  — **SHIPPED 2026-07-14 (loop)** on `feat/q-stationarity-horizon`: `CalibrationReport` (protocol `calibration.py`)
  gained optional `validity_frontier: tuple[str,...]` (content-addresses whose drift invalidates this q) +
  `as_of_current: bool | None`, with a drop-when-unset `@model_serializer` (the leaf.py recipe) so an unstamped
  report is BYTE-IDENTICAL to pre-④ (the signed certificate embeds CalibrationReport — 143 umbrella
  calibration/attestation tests + 21 protocol calibration tests unchanged). Pure `stamp_stationarity(report,
  frontier, drifted)` sets the frontier (sorted) + `as_of_current = frontier.isdisjoint(drifted)` — a drift on a
  constituent hash marks q EXPIRED (stale, not wrong; mirrors a re-opened license); empty frontier makes no
  stationarity claim. 5 new tests; protocol 520→525; grammar untouched; Corpus 4. Does NOT forecast the future
  (scope guard). Umbrella wiring (extract the real frontier from a corpus's licenses' MaterializationContexts +
  detect drift → call stamp_stationarity at report time) is a thin follow-up — the mechanism is in place.
- [x] **neg-whisper ⑤ — severity-backed licensed negative (forbidden vs unobserved)** · `BUILD` · neg-whisper §6
  — New pattern licensing a severe test for *absence*; maps morphospace occupied/empty/forbidden to real
  corpus states. Touches the licensing-not-meaning firewall. (Largest of the four remaining seams.)
  — **REPRESENTATION SHIPPED 2026-07-14 (loop)** on `feat/licensed-negative-morphospace` — additive, NO licensing
  change (the gate is untouched; a negative claim licenses via the existing bound-below-threshold criterion): grammar
  `Pattern.asserts_absence: bool = False` (default = presence; registry-side, NOT in the Corpus → byte-identical) +
  a concrete `bounded_absence@v1` pattern; new pure `morphospace.py` — `MorphospaceState`
  {OCCUPIED/FORBIDDEN/UNOBSERVED/OTHER} + `morphospace_state`/`morphospace_state_of` classifier (LICENSED presence →
  OCCUPIED; LICENSED severe negative [severity ≥ floor] → FORBIDDEN; PENDING untested → UNOBSERVED — the
  operational separation the measurement doc asks for) + `FIREWALL_STATEMENT` (licensed-negative = warranted absence
  at severity, NOT impossibility — a licensing status, not meaning). 6 tests; grammar 602→608 (existing unchanged =
  byte-identical); protocol 525 unchanged; Corpus 4. **Follow-ups (not this slice):** license a negative on a REAL
  EWAS non-effect through the gate (bounded-absence adapter/e-value — DATA-GATED), and viewer rendering of FORBIDDEN
  vs EMPTY (viewer). The firewall statement + operational trichotomy — the crux of doing ⑤ — are in place.
- [x] **v2 Slice 2 — attestation chain + certificate/SLSA `resolvedDependencies`** · `BUILD` · `specs/2026-06-29-v2-evidence-licensed-capability-design.md` §13
  — Full attestation chain for the evidence-licensed route (Slice 1 shipped `9b8848c`).
  — **CORE SHIPPED 2026-07-14 (loop)** on `feat/v2-slice2`. The gap: an EVIDENCE_LICENSED claim's SLSA
  `resolvedDependencies` was built only from cohort hashes (empty for a benchmark claim), so the attestation chain
  was blind to what produced the e-value; the real artifacts sat on `claim.licensing.evidence_provenance`, IGNORED by
  attestation.py. Added `_evidence_resolved_dependencies(licensing)` — maps every `EvidenceProvenance` ref (benchmark
  / executor-descriptor / evidence-policy / baseline-predictions / configs / capability / execution-contract /
  optional oracle) to a `ResourceDescriptor{name, digest.sha256, role}` using the ALREADY-COMPUTED content addresses
  (never fabricated; `bench:` prefix stripped), appended in `_statement` before the deterministic sort. **BYTE-IDENTICAL**
  for the recompute route (no `evidence_provenance` → empty) — PROVEN: 76 attestation/certificate tests + the pinned
  golden bundle unchanged. 3 new tests. Umbrella-only (attestation.py); grammar/protocol untouched; Corpus 4.
  — **Slice-2 follow-ups (not this core):** a "meaningful benchmark" fixture/demo + an optional `content` field on
  `ResourceDescriptor` (inline small artifacts). The attestation chain / SLSA resolvedDependencies — the heart — is done.
- [ ] **v2 Slice 3 — defeat/drift/reinstatement/replay hardening** · `BUILD` · v2 design §13
  — Defeat/drift/reinstatement/replay-over-time + tamper depth + downgraded-oracle for evidence claims.

## 3. Gate-integrity & core-grammar code debts
*Correctness/robustness of the licensing machinery itself — where a silent failure is most costly.*

- [ ] **Audit the `strength=None` / `_permitted_by_bar` exemption** · `HARDEN` · `protocol/.../verify.py:93`, `src/.../seed.py:73`, `src/.../exec_adapters.py:51`
  — Any executed claim with `strength=None` skips the cardinality-scaled BH selective-inference bar and
  always licenses. By design (live/generated claims ride it), but it's the single widest path past the
  bar — add an explicit guard/test that nothing *untrusted* reaches it with `strength=None`.
  — **LOOP ANALYSIS 2026-07-14 (flagged, not built — gate-touching):** grounded `verify.py:93`
  `{c.id for c in executed if c.strength is None and c.id not in earned}`. The exemption skips ONLY the BH
  MULTIPLICITY bar — a strength=None claim STILL faces the air-gap (two independent trusted adapters must agree)
  + e-value to actually license, so it is NOT a free-license path, just a skip-the-multiplicity-bar path. Two ways
  to harden: (a) a CHARACTERIZATION test pinning the exact scope (strength=None+not-earned → exempt; earned → scored;
  strength!=None → scored) — safe but needs `ExecRecord`/`VerifiedEvaluation` fixtures; (b) an explicit
  untrusted-cannot-ride GUARD keyed on a trust tag — **GATE-TOUCHING (changes which claims are exempt), FLAG for
  operator**. Deferred by the loop as gate-critical; do (a) first with care, treat (b) like the ②b wire-in.
- [ ] **Retire the per-claim `run_cycle` isolation workaround** · `HARDEN` · `CONTINUE.md` "NEXT" (logged since spine 2d-ii); `verify.py::_permitted_by_bar`
  — Exempt reference_leaf/threshold-None claims (scored by e-LOND alone) so they batch-license, removing
  the per-claim isolation the licensed-spine build needed. The one concrete logged cleanup.
- [ ] **Verify the evidence-dispatch bypass of the 2-adapter gate** · `HARDEN` · `protocol/.../execute.py:146`
  — Single-execution capability cells skip 2-adapter agreement, gated instead by a pending FDR test +
  matching `commitment_hash`. Confirm the hash/FDR guards are airtight (it's an alternate licensing route).
- [ ] **Per-unit concordance in two-adapter agreement** · `HARDEN` · `grammar/.../evaluate.py:364`
  — Agreement only checks both legs cross the same threshold, not that the *same units* drove the count
  (two n-DMP legs can agree on count while flagging different probes). Deliberately deferred; strengthen.
- [ ] **Oracle `relative_uncertainty` propagation into leaves** · `DEFER→HARDEN` · `grammar/.../oracle.py:115` (spec §8)
  — Credibility field is representable but never flows into executed-leaf uncertainty (under-propagated).
- [ ] **RELAX transport MDL pricing** · `DEBUG` · `grammar/.../description_length.py:275`
  — RELAX constraint-revision returns inputs unchanged (`mdl_delta == 0`), so it can never be selected on
  compression merit until real constraint-algebra pricing exists.
- [ ] **`incompatible_with` embedding edge (repulsion)** · `DEFER` · `src/.../embedding.py:18` (v1.1)
  — Incompatibility edges are absent from the layout weight map; the embedding ignores that relation.
- [ ] **Multi-signer trust policy** · `DEFER` · `src/.../signing.py:57` (spec §9)
  — `sign_envelope` is single-signer and replaces existing signatures; no threshold/multi-party trust.
- [ ] **Functorial schema migration of live claims** · `DEFER` · `grammar/.../representation.py:9` (spec §7)
  — No Δ/Σ/Π migration; schema evolution can't remap existing corpus claims.
- [ ] **Semantic/EIG dedup in the representation layer (SELECT #3)** · `DEFER` · `protocol/.../canonicalize.py:6` (spec §6.1)
  — Canonicalize does syntactic dedup only; semantic/expected-info-gain dedup is unbuilt. *(Daemons ARE built.)*
- [x] **Reference-adapter placeholder `operator_id` guard** · `HARDEN` · `protocol/.../red_team.py:53`, `generation_adapter.py:85`
  — Reference proposers ship `UNSET`/placeholder ids relying on `bridge_proposer` to overwrite; add a
  guard/test that no path emits a proposal with the placeholder intact. (Low risk; comment says forced.)
  — **SHIPPED 2026-07-14 (loop)** on `feat/placeholder-operator-id-guard`: named the sentinel
  `PLACEHOLDER_OPERATOR_ID = "UNSET"` (used by both reference adapters + red_team) and made `bridge_proposer`
  REFUSE (ValueError) an adapter whose `identity` IS the placeholder — the one way the un-forced sentinel could
  reach a credit-governed path. 3 tests (both adapters emit it; bridge forces it away; bridge refuses a
  placeholder-identity adapter). Byte-identical (value unchanged); protocol 525→528. Pure-protocol; Corpus 4.
- [x] **`LLMPatternGenerationAdapter` prompt/claim builders** · `BUILD` · `src/.../llm_adapter.py:114,117`
  — Base-class hooks raise `NotImplementedError`; a concrete subclass must implement them before the
  LLM-pattern generation surface works.
  — **PHANTOM / ALREADY SATISFIED (verified 2026-07-14, loop):** there is no `LLMPatternGenerationAdapter` class.
  `llm_adapter.py` has `_GenerationAdapterBase` (an ABSTRACT base whose `_build_prompt`/`_build_claim` raise
  `NotImplementedError` BY DESIGN) and the CONCRETE `LLMGenerationAdapter(_GenerationAdapterBase)` (`:120`) which
  implements both hooks + maps a constrained DSL into executable PENDING+plan grammar Claims. The generation
  surface works; the base-class `NotImplementedError` is the correct abstract-base pattern, not a gap.

## 4. Attested calibration hardening (slice-4 §11 deferrals)
*MVP shipped; these are the deferred trust-boundary pieces.*

- [ ] **Validate `license_epoch` against real epoch state** · `HARDEN` · `src/.../attested_ingest.py:41` (spec §11)
  — Epoch is recorded but never checked; can't distinguish a historical license from the current one.
- [ ] **Auto-wire defeat edges between contradictory attestations** · `HARDEN` · `attested_ingest.py:79` (spec §11)
  — Contradictory external attestations coexist with no automatic defeat edge; conflict resolution absent.
- [ ] **Credence-layer scoring engines / markets / live feeds** · `DEFER` · `specs/2026-06-22-attested-ingestion-design.md` §11
  — Proper scoring (resolvable), surrogate/peer-prediction (unresolvable), live ClinVar/registry feeds.

## 5. Synbio HEADLINE capstone (WAYLAND Phases 3–5) + grammar gaps
*Spine + fusion-marker family shipped at REPLICATED. Remaining = the blinded re-derivation and its residue.*

- [ ] **Phase 3 — blinded seed + pre-registration firewall** · `BUILD` · `plans/2026-07-10-synbio-claims-universe.md` §Phase 3
  — Firewall admissibility + conclusion-stripping + independent leakage review + `commitment_hash`/α-slot
  lock. Own spec+plan not yet authored. *Gate to the headline.*
  — **FIREWALL HARNESS SHIPPED 2026-07-14 (loop)** on `feat/synbio-phase3-firewall`: `src/polymer_claims/synbio/firewall.py`
  — the PROCESS-enforced conceptual-leakage guard (Phase 0 §4). `check_admissibility` = conclusion-stripping (an
  answer-leaking claim is inadmissible even if old) + optional date-cutoff, each admitted claim tagged with the
  deciding rule; `assemble_blinded_seed` partitions candidates deterministically. `DEFAULT_FORBIDDEN_ANSWER_TOKENS`
  (RUNX1-RUNX1T1 / opto-car / genotype-directed-cytotoxicity / direct-caspase / topology-rejection) — configurable.
  6 tests; additive, umbrella-side, NOT the licensing gate; Corpus 4. **REMAINS FOR THE OPERATOR (headline scientific
  work — NOT autonomous):** the blinded-seed CURATION (which real synbio claims go in), the Durendal derivation-plan
  pre-registration (`commitment_hash` + α-slot lock), and the exit-gate **independent-reviewer no-leakage confirmation**
  — the harness is the tool; the human review + the framing decision (Phase 4 "decide before the run") are yours.
- [ ] **Phase 4 — the Durendal derivation run (the forge) [HEADLINE]** · `BUILD` · synbio plan §Phase 4
  — Re-derive Durendal (RUNX1-RUNX1T1 + topology-rejection + direct-caspase) as a grounded extension under
  the locked plan, *without having been shown the answer*. Human-proposed fallback framing decided pre-run.
- [ ] **Phase 5 — wedge & demo** · `BUILD` · synbio plan §Phase 5
  — Auditable-derivation artifact + live argument-graph viewer + "next three targets" (PAX3-FOXO1,
  SS18-SSX, NPM1-ALK), each with its own Gate-1.
- [ ] **Broaden markers/fusions (verify-before-license)** · `BUILD` · `CONTINUE.md` 2e "NEXT"
  — Add more CBF/other fusion markers as data supports; verify each vs data first (the MYH11→MN1 lesson).
- [ ] **Synbio 2c ingestion at scale** · `HARDEN` · `specs/2026-07-10-synbio-phase2-design.md` §3
  — Extend the reviewed markdown→claims extractor beyond the 5 reviewed manifests / 39 claims.
- [ ] **Open IR grammar gaps GAP-7/8/11/13/14/15** · `BUILD` · `notes/2026-07-10-synbio-grammar-gaps.md`
  — GAP-7 ANALYTIC basis; GAP-8 gene/locus sub-key; GAP-11 per-tumor stratification; GAP-13 endpoint_type;
  **GAP-14 composite/vector leaf** (`QuantityVectorLeaf` — a DMP is vector-valued); GAP-15 structured
  categorical mapping. Each core-adjacent, byte-identity-gated, needs a real caller to demand it.
  ⚠ **Measurement-foundation caveats (see §9):** GAP-14 for *compositional* data (a molar ratio) needs a
  **joint** log-ratio invariance group, not independent per-component scalars (the naive fix is the
  "ordinal-as-interval" error). GAP-8/GAP-11 are the *entity/sample axis* (MAE-style), not
  measurement-semantics. GAP-13 *is* the parameterization seam. Every GAP should declare its scale-type +
  invariance group as part of definition-of-done.

### TE-methylation engine gaps (honestly logged; DEBUG/HARDEN residue, not blockers)
- [ ] **Rank-sum small-sample calibration** · `DEBUG` · `notes/2026-07-11-transposable-element-methylation-strain.md`
  — Per-probe n-DMP test mildly anti-conservative under permutation (~1.5–2× nominal) on small n.
- [ ] **BH-withheld claims mislabel `pending_reason=UNTESTED`** · `DEBUG` · TE note §CORRECTION
  — Claims withheld by the ~1.29× effective BH fold-floor report `UNTESTED` though they *were* evaluated.
- [ ] **Pre-register the honest enrichment threshold** · `HARDEN` · TE note §CORRECTION
  — Nominal `fold≥1.0` is misleading vs the ~1.29× effective floor from `_permitted_by_bar`/K=8.
- [ ] **Single-pass rmsk bucketing (perf)** · `DEBUG` · TE note §Follow-ups
  — Sweep re-parses the 491 MB `rmsk.txt` once per family (6×); bucket by (repName,repClass) in one pass.

## 6. Wedge / real-data path (data-gated)
*The critical-path to a public, defensible claim. Machinery works; waits on real labels/datasets.*

- [ ] **Real 2nd HM450 AML cohort → §2E REPLICATED on real data (H1.A2)** · `BUILD` · `2026-06-23-remaining-roadmap.md` Track A
  — **Data-access-gated:** no open HM450 adult-AML cohort exposes machine-readable IDH; needs a
  user-supplied `data/sal_aml/idh_status.tsv` (GSE86409 betas already downloaded; no genotype fabrication).
- [ ] **One legible wedge claim as a public signed certificate (H2)** · `BUILD` · remaining-roadmap Track A
  — Variant-adjudication / biomarker-ledger / AML disease-twin wedge, publicly signed + calibrated.
  Gated on H1.A2.
- [ ] **Close the calibration loop on real resolved claims (H1.C2)** · `DEFER` · remaining-roadmap Track C
  — DEFINITIONAL `q` is currently validated on a synthetic data-generating process (disclosed); needs real
  resolvable claims.
- [ ] **`CORRELATION_CELL` + 2 independent correlation adapters + generation adapter** · `BUILD` · remaining-roadmap capability-menu
  — Unlocks `spearman_rho` claims (a large fraction of the 47-claim reference universe). Scope first — none
  of the three parts exists yet.
- [ ] **Migrate more `mean_diff` claims** · `BUILD` · `CONTINUE.md` 2026-07-01 NEXT
  — Cheap generalization: reuse the `hla_promoter_meth_claim` pattern (bind real data → CSV, set threshold).
- [ ] **Capability cells V2.1 / V2.2 / V2.3** · `BUILD` · remaining-roadmap capability-menu
  — Enrichment / fixed-protocol classifier-eval / feature–phenotype association cells.
- [ ] **Promote WITNESSED to a first-class status** · `BUILD` · `CONTINUE.md` 2026-07-01 NEXT
  — From `--sheaf-active`-pending + compute-boundary discipline to a real corpus status.

## 7. Infra / tooling / hygiene

- [x] **Add a CI workflow** · `HARDEN` · `scripts/check-all.sh:11`
  — No working CI (GitHub account was flagged → now resolved, `beldez01`). Mirror `check-all.sh`
  (tests + lint + viewer build) so regressions can't land unnoticed. `.github/` currently absent.
  — **SHIPPED 2026-07-14 (loop)** on `feat/ci-and-doc-hygiene`: `.github/workflows/ci.yml` — a `python` job
  (grammar + protocol + umbrella pytest **with `-rs`** + ruff on all three, via `astral-sh/setup-uv`, py3.12) and a
  `viewer` job (npm ci + typecheck). Mirrors `check-all.sh`. `-rs` **surfaces the data-gated test skips** (folds in
  the "surface 5 skips" item — real data is gitignored so those tests skip in a clean checkout, now visible not
  silent). NOTE: GitHub Actions was historically account-suppressed; the file activates automatically once enabled.
- [ ] **Push local `main`** · `HARDEN` · `CONTINUE.md` "NEXT — Push main"
  — Accumulated local commits; coordinate first (shared checkout with other instances).
- [x] **Surface the 5 data-gated test skips** · `DEBUG` · `tests/test_tcga_laml_ndmp_e2e.py:41` + 4 more
  — TCGA-LAML / Loyfer WGBS / GDSC pharmaco / BioNeMo-live tests silently skip without gitignored data or a
  live key, so the real-biology paths are unexercised in a clean checkout. Make the skip visible in CI output.
  — **DONE 2026-07-14 (loop)** — folded into the new CI workflow: every pytest invocation runs with `-rs`, which
  prints the skip reasons (each skip already carries a clear `reason=`), so the data-gated paths are visibly
  reported in CI output instead of silently passing.
- [ ] **GDSC drug→CHEBI resolver** · `HARDEN` · `src/.../pharmaco_populate.py:62`
  — Unmapped drugs fall back to a synthetic `urn:pharmaco:drug:<slug>` under an "other" ontology instead of a
  real CHEBI id. The noted scaling bottleneck for the pharmaco arm.
- [ ] **`profiles.py` placeholder registry values** · `DEFER` · `src/.../profiles.py:14`
  — Example profile registry carries invented values, not real analysis-engine params.
- [x] **immuno bundle fails strict `Corpus` validation** · `HARDEN` · `src/.../merge_universes.py:181`
  — `immuno_universe.json` (2 reconstructed nodes) is hand-rebuilt around strict grammar validation → drift
  risk between viewer bundle and real corpus schema. Clean into a real Corpus.
  — **DRIFT-GUARD SHIPPED 2026-07-14 (loop)** on `feat/immuno-corpus-guard`. (Count corrected: the bundle is **11**
  nodes — 2 licensed count-enrichment + 2 pending + 7 rejected region-Δβ — not 2.) Rather than churn the viewer
  bundle format, pinned the reconstruction's contract: `test_immuno_corpus_guard.py` asserts `collect_immuno()`'s
  reconstructed claims + fdr tests form a **strict, JSON-round-trippable `Corpus`** (unique ids, referential
  integrity, valid leaves/statuses; the `"inf"` MHC e-value capped to a finite sentinel) — so any drift between the
  hand-built bundle and the grammar schema, or a collector regression, now fails a test. 1 test; umbrella-only;
  no bundle/collector change → no merged-universe regression. (A deeper "make the raw JSON itself a strict Corpus"
  is a viewer-format follow-up; the drift risk the item names is now guarded.)
- [ ] **Regenerate `merged-universe.json` with all arms** · `HARDEN` · TE note §Follow-ups
  — Resolve the `merge_universes.py` synbio→synthetic-biology rename; pharmaco regen needs the `pandas` extra (~13 min).
- [ ] **Pre-release context scrub** · `HARDEN` · `CONTINUE.md` "Open follow-ups"
  — Genericize remaining PolymerGenomics/Boris/PlumberClient refs; strip `~/Desktop/Research/...` absolute
  paths from specs. Before any public release.
- [x] **Fix stale/dangling doc references** · `DEBUG` · (discovery findings)
  — `specs/2026-07-10-reparameterization-evaluator-design.md` cites `2026-07-07-duhem-consistency-fold-design.md`
  at a `specs/` path (now in `archive/specs/`); attested-ingestion header cites the missing
  `.claude/plans/cozy-growing-naur.md` and §12 cites a missing `2026-06-22-calibration-ledger-and-certificate-design.md`;
  several specs cite `GLOSSARY.md` as `foundations/GLOSSARY.md` (it's at repo root). Also update `CONTINUE.md`'s
  stale "slice 4 next" claim (attested MVP is built — see corrections above).
  — **DONE 2026-07-14 (loop)** — fixed the REAL dangles (verified by grep/ls): reparam spec duhem ref →
  `archive/specs/…`; attested-ingestion header `.claude/plans/cozy-growing-naur.md` + the missing
  calibration-ledger-and-certificate spec ref → redirected to git history / the shipped substrate. **Two were
  PHANTOMS:** `foundations/GLOSSARY.md` appears ONLY in this BACKLOG's own description (no spec actually cites it;
  GLOSSARY.md is at repo root), and the CONTINUE "slice 4 next" claim was already corrected. CONTINUE.md scrub +
  §11 deferrals left as-is.

## 8. Deferred by choice / horizon — don't build yet

- [ ] **Networked Rekor backend** · `DEFER` · `specs/2026-06-26-networked-rekor-backend-design.md`
  — Public non-repudiation + verified append-only-ness. Designed, build-ready, **TABLED** until the first
  externally-shared wedge (H2). `--rekor-url` reserved + errors today.
- [ ] **GAP-9 log-scale / GAP-10 discrete-integer interval markers** · `DEFER` · grammar-gaps §GAP-9/10
  — Range facet shipped (low/high); these sub-markers are behind strict xfail tripwires
  (`tests/synbio/test_claims_intervals.py:27,36`) — YAGNI until a consumer computes inside an interval.
- [ ] **Claim-type menu rows (12-row slate)** · `DEFER` · `specs/2026-06-29-claim-type-menu-design.md`
  — RNA-seq DE, variant effect, survival, structure, etc. Horizon; each row = its own spec→plan when scheduled.
- [ ] **Cohort Foundry (data-independence producer)** · `DEFER` · `specs/2026-06-29-cohort-foundry-design.md`
  — Independently-assembled validation cohorts + qualification dossier. Horizon; consumes the `replication.py`
  REPLICATED seam. (Directionally the same as the Durendal blinded-validation concern.)
- [ ] **`q_anchored` Kaplan–Meier hazard curve** · `DEFER` · remaining-roadmap Track C
  — Exposure-weighted hazard already shipped; the KM curve is deferred.
- [ ] **Parameterization-seam research program** · `DEFER` · remaining-roadmap; `docs/open-questions-research-plan.typ`
  — Group-A leaves/parameterization + Group-B statistical seams as falsifiable, foundations-validated hypotheses.
- [ ] **V3/V4 operational states & vision** · `DEFER` · remaining-roadmap Horizon
  — Temporal reproducibility as earned standing (V3.1); `resource-exceeded`/`migrated`/`untrusted` states
  (V3.2); V4 published claim registry; autonomous hypothesizer, red-team marketplace, Earn-Standing API,
  federated/BYO-compute. Mostly gated on H2.

---

## 9. Foundations-concordance gaps (added 2026-07-13)
*From reconciling `foundations/` against the build. The docs are **concordant in direction** — no place
where the build does the wrong thing. The recurring theme: the build installs the **socket** (a gate, a
metadata field, a tier) but in several load-bearing places the philosophy describes a **measured current**
that is still operator-**asserted**. These cross-ref existing rows rather than duplicate them.*

### The "declared-not-enforced" trio — HIGH (gate integrity)
- [ ] **Consume `invariance_group` — run the meaningfulness/invariance check as a licensing precondition** · `HARDEN` · measurement-foundation §3.1
  — `invariance_group`/`scale` ship on `Pattern` (`grammar/.../pattern.py:28`) + `MeasurementBasis` but are
  **never read** by any evaluator — no invariance test runs before a claim reaches LICENSED. The doc's core
  necessary-condition-for-standing is absent from the gate. The socket is built; the check isn't.
  — **CHECK SHIPPED 2026-07-14 (loop)** on `feat/invariance-check` (advisory; gate-wiring FLAGGED, not applied):
  `src/polymer_claims/invariance.py` — the FIRST consumer of `Pattern.invariance_group`/`scale`. Maps the 5
  free-form `Pattern.scale` strings to a Stevens scale-CLASS and cross-checks it against the B1 measurement-space
  registry's `ScaleType` for the space(s) the claim reads → `InvarianceVerdict` {COHERENT / UNCHECKED / INCOHERENT
  / UNDECLARED}. Catches the load-bearing "ordinal-as-metric" error (an ordinal-scale pattern reading a ratio/interval
  space). `invariance_ok(claim)` is the advisory precondition. 4 tests; umbrella-only; grammar/protocol untouched;
  Corpus 4. **REMAINS (gate-touching → FLAGGED for operator):** wire `invariance_ok` as a HARD licensing precondition
  in `verify.py` (reject INCOHERENT/UNDECLARED before LICENSED) — changes licensing outcomes; do like the ②b wire-in.
- [ ] **Independence as MEASURED error-correlation, not asserted-label Jaccard** · `HARDEN` · epistemology §2.B — *same work as §2 adapter-independence R1–R5 + Step 0 + neg-whisper ②*
  — `grammar/.../shared_cause.py:54` overlaps operator-declared factor *labels* vs a fixed τ (comment:
  "operator-asserted factors"), not measured ρ. This row records that **the foundations doc overstates it
  as already "measured"** — the measurement is the unbuilt §2 work.
- [ ] **Enforce/confirm the attested-log floor as a licensing precondition** · `HARDEN` · compute-boundary "move 1" *(trust-machinery — unaffected by the compute-hosting softening)*
  — Doctrine: "no `Satisfaction` licenses without an attested log." **Verified NOT enforced** — `verify.py`
  / `licensing.py` bind no runtime log at license time. Confirm whether any path can license without a bound
  log; if so, add the gate.

### IR-schema expansion discipline (serves the data→schema feedback loop)
- [ ] **Every new IR field declares its scale-type + admissible-transformation (invariance) group** · `HARDEN` · measurement-foundation
  — The additive-monotonic expansion practice is *justified* (even predicted) by the measurement theory —
  but each open GAP widens the schema **without** declaring the new field's invariance group, so growth is
  drifting from the foundation. Make invariance-declaration part of definition-of-done for every IR
  expansion. *This is the theoretical backbone of your "monitor where data resists the schema → expand" loop.*
- [ ] **Adopt an entity/sample axis (MAE-style) instead of hand-rolling it; re-file GAP-8 / GAP-11** · `HARDEN` · measurement-foundation §5.1
  — GAP-8 (gene/locus) + GAP-11 (per-tumor) are the entity axis (MultiAssayExperiment colData/rowRanges),
  not measurement-semantics; the doc says "ride MAE, don't rebuild." Today they leak into free-text `condition`.
- [ ] **Cross-assay relationships as first-class licensable claims** · `BUILD` · measurement-foundation §5.3
  — e.g. methylation→expression as a *claim* with its own bar, not asserted infrastructure.

### Residualism-driven
- [ ] **Audited/configurable audience value-ordering for defeat — or correct the doc** · `HARDEN` · residualism §7 vs `grammar/.../defeat.py:94`
  — The doc commits (twice) to defeat "relative to an audience's ordering over values" as "an explicit,
  audited parameter"; the code hard-codes strength-Pareto dominance. Either make the ordering selectable/
  audited, or amend `residualism.md` to say the strength-Pareto order *is* the fixed audience.
- [ ] **Query / convert surface for the PENDING residue graveyard** · `BUILD` · residualism §7 (R3)
  — neg-whisper ③ funds only *scheduling* re-exam (a weight); the doc's "queryable" graveyard + R3 active
  conversion implies an inspection/re-conversion surface not yet listed.

### Compute / infra (reframed — stance softened 2026-07-13, no rigid never-host caveats)
- [ ] **STRATEGIC — resolve the product-identity fork (your active decision)** · drives where the compute line falls
  — local meaning-extraction tool · open public claims world · hosted concordance API · in-house
  drug-discovery engine. `compute-boundary.md` softened from doctrine → default (2026-07-13) pending this.
  Federation / Cohort Foundry / a managed compute tier are now spectrum **options**, not violations.
- [ ] **Cross-hardware determinism / tolerance criterion** · `HARDEN` · scaled-infrastructure ("the core systems problem")
  — Under FP/GPU nondeterminism, "re-run and compare" needs principled tolerances vs bit-exactness. Adjacent
  to two-adapter/per-unit concordance but named as *the* hard systems problem; no dedicated row until now.
- [ ] **Real auth / multi-tenant surface** · `HARDEN` · scaled-infrastructure ("local-only → federated gap")
  — Needed by any hosted/federated form; today the node's mutating routes are unauthenticated by design
  (`src/.../server.py:171`).

### Foundations-doc overstatement corrections
- [x] `epistemology.md` §2.B — softened 2026-07-13: independence "measured, evidenced" reframed as the
  *aim*; the built gate is asserted-label overlap, measured ρ is the unbuilt step.
- [x] `scaled-infrastructure.md` — softened 2026-07-13: the transparency log's "witnessed / multi-party"
  description now marked as target vs the shipped **local, single-signer, inclusion-only** log.
- [x] `compute-boundary.md` — softened 2026-07-13: "the platform *is* four parts" → "*designed as*," with
  a status note that the Science Claw and Cohort Foundry are horizon (no code yet).
- [ ] `measurement-foundation.md` §3.1 — left as-is (self-labeled brainstorm-stage, adequately hedged);
  the real fix is enforcing the invariance check (tracked above), not editing the doc.
- [ ] Reconcile the proposer/attacker-inference compute placed on opposite sides of the boundary in
  `compute-boundary.md` (Science Claw = user-side) vs `scaled-infrastructure.md` (Pile B = owned) — now
  a live question under the softened stance, not a contradiction to erase.
