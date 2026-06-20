# ⟳ Polymer Claims — RESUME HERE

> Hook-loaded continuity file (a SessionStart hook surfaces it). **Keep the *Current state* + *NEXT*
> sections current at every phase boundary.** Detailed build history lives in git (`git log --oneline`),
> the canonical spec (`docs/superpowers/polymer-claims-canonical-spec.md`), the per-slice plans
> (`docs/superpowers/archive/plans/`), and the archived per-feature design specs (`docs/superpowers/archive/specs/`).
> One-page architecture map: `ARCHITECTURE_CURRENT.md`. Reserved terminology: `GLOSSARY.md`.

---

## Current state (2026-06-20)

`main` GREEN — **269 umbrella + 396 grammar + 394 protocol + 2 isolation**, ruff
clean, viewer `tsc` clean. grammar/protocol pure + numpy-free; **Corpus = 4 collections**. (**§E
common-cause slice — earn REPLICATED on low shared-cause overlap — shipped 2026-06-19, merged**;
Phase D slice 2 + slice 1 merged 2026-06-19; see NEXT.) **Viewer-build caveat:** `npm run typecheck`
passes; the `next build` step of `scripts/check-all.sh` currently fails *only* because the sandbox cannot
fetch Inter/JetBrains Mono from Google Fonts at build time (a network block, not a code defect — the build
passed when network was available). All pytest suites + ruff + isolation + viewer typecheck are green.

**Repo reconciled to a single trunk (2026-06-19).** The git tangle is gone: ~9 stacked feature branches
were fast-forwarded into `main` (zero divergence, nothing lost), all stale local + remote branches
pruned, and **`main` pushed to `origin` (`origin/main == main`)**. The account flag is RESOLVED, so the
old "local-only, never push" rule no longer applies — `main` is now kept in sync with origin.

**Repo hygiene (2026-06-17):** a full cleanup pass — `docs/` consolidated (one canonical spec +
this file + the forward roadmap + the Phase-2 vision docs under `docs/superpowers/`; everything
historical under `archive/`); the closed external audit archived; obsolete v1.2 migration scripts +
dev-only fixture generators removed; one dead helper (`io.load_claim`) dropped. **v1.2 retired from
the repo** (moved out to a local sibling, preserved pending deletion — the v1.3 system never
depended on it; isolation-guard enforced). Runtime is unchanged — the test counts above still
describe `main`.

What the system *is* — the full architecture (grammar → protocol → node → viewer; the e-value-native
epistemic core; real computation + CES) — lives in the canonical spec
**`docs/superpowers/polymer-claims-canonical-spec.md`**. This file tracks **state + what's next**, not the
design.

**Standing caveats (carry forward):**
- **n-DMP / REPRODUCED is EARNED on real betas (2026-06-17 Phase A; IDH source upgraded 2026-06-18).**
  The genome-wide n-DMP count licenses at REPRODUCED on a **real TCGA-LAML HM450 cohort** (IDH-mut vs WT;
  194×378,894; e-value → ∞; legs agree; full content-address). **IDH calling swapped to cBioPortal
  complete genotyping (`tcga_laml_idh@2`, 2026-06-18):** IDH-mut **n=10 → 36** (cBioPortal
  `laml_tcga_pub@86690e1`; WT now = genotyped-and-not-hotspot, never a missing-data default;
  dropped_ungenotyped=0 so betas are byte-identical to @1, only labels+metadata change — captured by a
  `group_digest`). Non-diluted, the DMP count rose 50,339 → **115,405** (floor 18,945). Betas = local Xena
  GDC-Level-3 matrix. Run caveat: sex-chrom QC skipped (Xena lacks chr/pos). Data local-only, gitignored;
  builders in `data/tcga_laml/` (gitignored).
- **Region-Δβ re-run at proper power (2026-06-18) — held-out e-value 0.867 → 5.672, still PENDING (honest).**
  On `@2` (now ~18 IDH-mut/split vs ~5 at n=10) the held-out top-10k betting e-value (Δβ > pre-registered
  τ=0.10) jumped to **5.672** — it crossed break-even (>1), so the held-out data now genuinely favors the
  effect; the n=10 power diagnosis was correct. It is **still WITHHELD**: the e-LOND first-test discovery
  threshold is **1/α₁ = 32.90** (q=0.05, γ₁=6/π²) and 5.672 < 32.9 → PENDING. **τ stays fixed at 0.10 — no
  tuning.** Clearing 32.9 as a §2E REPLICATED **product** e₁·e₂ needs each cohort ≈ √32.9 = 5.74; the
  single-cohort e=5.67 is right at that bar, so **a 2nd real cohort would license it at REPLICATED**.
  Region-Δβ remains **UNEARNED** (FDR-withheld, not refuted). **Still synthetic:** REPLICATED (needs the
  2nd real cohort). [next: 2nd real cohort → §2E REPLICATED]
- `semantic_run_id` is the **Python** digest; an R-parity golden fixture is deferred (needs an R
  serializer). [menu item 7]
- Adapter independence is now **partly hardened**: local adapter registries derive
  `implementation_hash` from adapter implementation bytecode, and licensed `Satisfaction`s record the
  registry credential identities that justified the independent air gap. Registry owner/trust metadata
  remains operator-authored. [roadmap 1c residual]
- The two methylation adapters are **reproducibility-independent, not error-independent** (same estimand,
  same data) → the single-cohort demo licenses at **REPRODUCED**. **§2E now expresses the stronger tier:**
  a claim reproduced across two cohorts with distinct `dimnames_hash` licenses at **REPLICATED** (the
  cross-cohort independence that error-decorrelates). **§E now gates this (2026-06-19):** when runs declare
  `shared_cause_factors`, REPLICATED additionally requires every pairwise Jaccard < 0.5 — else REPRODUCED,
  with the e-value product withheld (factors operator-asserted; bundled SE-Contracts now carry flat
  factors and `materialization_map` propagates cohort-A factors, so the gate is active on bundled
  contract-backed runs). The REPLICATED demo runs on a **2nd synthetic
  cohort** (`epicv2_casectrl_demo_b`) — still exercised, not earned, until a real 2nd cohort is swapped in.

## ▶ NEXT (concrete plan)

**Recently shipped** (most recent first): **§E common-cause — earn REPLICATED on low shared-cause overlap:
each run declares `MaterializationContext.shared_cause_factors`; the REPLICATED tier (which licenses
multiplying e₁·e₂) now requires distinct `dimnames_hash` AND every pairwise Jaccard < `SHARED_CAUSE_TAU=0.5`
(else REPRODUCED); the umbrella `build_replication_inputs` gates the e-value product on the same
`cohorts_error_independent` predicate (cohort-A proxy built from its contract, so the gate fires in
production). `Licensing.shared_cause_overlap` recorded + viewer-surfaced. Bundled SE-Contracts now carry
flat factors, and `materialization_map` propagates cohort-A factors so verify's label agrees with
replication's e-value multiplication gate. Second concrete edge of north-star §E. Operator-asserted factors;
byte-derived factor provenance remains a hardening follow-up.
Additive/byte-identical when off; subagent-driven (5-task plan, whole-branch opus review). spec+plan
`docs/superpowers/{specs,plans}/2026-06-19-common-cause-replicated*`; shipped and merged 2026-06-19.** ·
**Phase D slice 2 — literature-shared-cause gate +
incubation/ranking: a hypothesis records the cohorts its motivating prior was established on
(`Provenance.prior_cohorts`); overlap with the test cohort → `severity_provenance=CONFIRMATORY`
license + `severity`-axis cap (strict mode withholds). The same data-blind signal feeds SELECT
ranking (injected `cohort_of_ref`) + `register_selected` budget-aware top-k commit. First concrete
edge of north-star §E. Additive/byte-identical when off; merged 2026-06-19.** · **Phase D slice 1 —
pre-registration ledger: a hypothesis commits before it sees data; registration charges+locks the
e-LOND α-slot (strict, no refund) + a verify match-gate rejects post-hoc changes
(`HYPOTHESIS_ALTERED`, terminal) — closes the §5a multiplicity leak; pure-code grammar+protocol,
byte-identical when off (subagent-driven, whole-branch-reviewed; merged 2026-06-19)** · **IDH-source swap — cBioPortal genotyping →
`tcga_laml_idh@2` (IDH-mut n=10→36); region-Δβ re-run at proper power: held-out e 0.867→5.672, still
PENDING below the e-LOND threshold 32.9 (2026-06-18)** · **Region-Δβ via held-out top-10k — gate WITHHELD
at n=10 (2026-06-17), severity demonstrated** · **Phase A real-data swap — n-DMP EARNED on real
TCGA-LAML HM450 betas (2026-06-17)** · Procrustes / live-spectral layout · §2E tiered independence
(REPRODUCED / REPLICATED) · reinstatement → PENDING · n-DMPs-at-FDR. SHAs + one-line summaries in the
*Done* checklist below; design rationale in `docs/superpowers/archive/specs/`.

**▶ PHASE A SHIPPED — the real-data swap is *earned* for n-DMP/REPRODUCED.** The genome-wide n-DMP count
licenses at REPRODUCED on a real TCGA-LAML HM450 cohort (see Standing caveats above for the numbers +
run caveats). Archived plan:
`docs/superpowers/archive/plans/2026-06-17-phase-a-real-data-swap.md` (Tasks 1–7, spec +
implementation). Local-only run builders live in `data/tcga_laml/` (gitignored).

**▶ REGION-Δβ re-run at proper power on `tcga_laml_idh@2` — held-out e 0.867 → 5.672, still PENDING
(FDR-withheld, NOT refuted).** The honest region reduction (no hand-picked region): select the top-10k
DMPs on a discovery half, test Δβ on the held-out half. After the IDH-source swap (n=10→36; ~18
IDH-mut/split): discovery/test = 97/97; held-out betting e-value (Δβ > pre-registered τ=0.10) = **5.672**
— it **crossed break-even (>1)**, confirming the n=10 power diagnosis (the held-out data now genuinely
favors the effect). **Still WITHHELD:** the e-LOND first-test discovery threshold is **1/α₁ = 32.90**
(q=0.05, γ₁=6/π²) and 5.672 < 32.9 → PENDING. **τ stays fixed at 0.10 (no post-hoc tuning).** The reusable
severity machinery is `src/polymer_claims/split_select.py` (`stratified_split` / `split_contract` /
`top_k_hypermethylated`). Plans: design + impl at
`docs/superpowers/specs/2026-06-18-idh-source-swap-design.md` +
`docs/superpowers/plans/2026-06-18-idh-source-swap.md`; the n=10 attempt at
`docs/superpowers/archive/plans/2026-06-17-region-delta-beta-split.md`.
Region-Δβ remains **UNEARNED** (FDR-withheld, not refuted). **Recommended next
moves (re-ordered):** (a) **a 2nd real cohort → §2E REPLICATED** gold tier — the product e₁·e₂ needs each
cohort ≈ √32.9 = 5.74 and the single-cohort e=5.67 sits right at that bar, so a comparable 2nd cohort
**would license region-Δβ at REPLICATED** (now the highest-leverage move); (b) **a real HM450 probe
manifest** so sex-chrom QC bites + a real platform `profile_hash`; (c) **Phase B** — the
`MethylGenerationAdapter` (autonomous hypothesizer) on top of the now-real substrate
(`docs/superpowers/2026-06-16-autonomous-hypothesis-loop.md`). [IDH-source swap (a fuller IDH cohort) —
DONE 2026-06-18.]

**▶ §2E REPLICATED (move a) — STAGED, BLOCKED on data access (key finding 2026-06-18).** Attempted on
branch `feat/replicated-second-cohort` (spec+plan committed: `docs/superpowers/{specs,plans}/2026-06-18-replicated-second-cohort*`).
Cohort B = **GSE86409** (Study Alliance Leukemia adult-AML, HM450, n=79) — its 419k-probe betas are
public + downloaded, BUT a hunt across GEO returned a hard lesson: **no open independent HM450 adult-AML
cohort exposes machine-readable per-sample IDH status.** GSE86409 / GSE159907 keep IDH only in paper
supplements or controlled-access dbGaP (phs001657); the GEO series that DO carry per-sample `idh1:`/`idh2:`
(GSE146173, GSE98350) are RNA/seq, not 450K. **So earning REPLICATED on real data is *data-access*-gated,
not code-gated** — the binding machinery (`build_replication_inputs` / `replication_bindings`) already
works. Ingestion + run scripts are written & compile-clean (`data/sal_aml/build_contract_gse86409.py`
reads a user-supplied `data/sal_aml/idh_status.tsv` keyed by eAML-NGS title or GSM, drops unlabeled
samples — no WT dilution; `data/sal_aml/run_replicated.py` gates the product vs 32.9). **Resume =** drop
`data/sal_aml/idh_status.tsv` (SAL PMID 28366934 supplement / dbGaP phs001657) → run the two scripts. **No
fabrication of genotypes — the run waits on real labels.** Non-data-blocked alternatives if REPLICATED
stays gated (both pure-code, no external data): **Phase D slice 1 (pre-registration ledger) — DONE
2026-06-19**; remaining non-blocked work is **Phase D slice 2** (close the §5a literature-shared-cause
leak + incubation/ranking) or **North Star §E common-cause-DAG independence**.

**▶ PHASE B FIRST SLICE SHIPPED — methylation hypothesizer.** `MethylGenerationAdapter` now mirrors
`MeanDiffGenerationAdapter`: a constrained LLM DSL emits executable `region_delta_beta` / `n_dmps`
methylation claims against SE-Contracts, with validation, deterministic IDs, generated provenance, and
tests. Live wiring is available as `serve --methyl-data`, which runs methylation adapters plus
content-address/e-value gating. This is the autonomous hypothesis loop's first real-methylation agent
surface; the gate still decides license/reject/PENDING.

**▶ §2E LIVE WIRING + ASSET CATALOG SHIPPED.** `NodeRunner` can now compute `replication_map` inputs
live via `replication_bindings`, so a live tick can license a bound methylation claim at
`independence_tier=replicated` instead of requiring a hand-built `run_cycle(...)` call. The viewer
already displays `independence_tier`. Phase B also has a small methylation data-asset catalog
(`methylation_asset_catalog`) that lists bundled SE-Contract fixtures and locally generated TCGA
contracts when present; the methylation generator prompt is now metadata-driven rather than hardcoded.

Other safe slices (the historical decision menu is archived at `docs/superpowers/archive/2026-06-13-overnight-deferred-analysis.md`):

1. **§2E follow-ups** — viewer tier display + live-node `replication_map` wiring are done. Remaining:
   bind a **real** second cohort when available so REPLICATED is earned, not only exercised.
2. **n-DMPs as a REPLICATED second reduction** — run the n-DMP count on a second cohort and multiply the
   two count-enrichment e-values (combines §2E's REPLICATED machinery with the new reduction). ~1 slice.
3. **ROBUSTLY_BLAMED wiring** — wire the Duhem robust-blame REJECTED verdict into the protocol and stamp
   it (tiny; the enum value is reserved). Optional/legibility.

**Deferred / blocked-on-external (supervised):** Python/R hash parity (needs the R side);
standards-skin attestation JSON (in-toto/SLSA/DRS
serialization — the safe first slice of the north-star "standards" arc). Literal per-attack e-value
combination is **largely a mirage** — Phase 2.2 already caught its sound core; don't build a generic
combination.

Rhythm: `superpowers:brainstorming` (2–3 forks → spec → plan) →
`superpowers:subagent-driven-development` → merge `--no-ff` → update this file + memory.

## Done — checklist (git has the detail; SHAs for spelunking)

**Grammar** (`polymer_grammar`) — complete, all 8 phases:
- ✅ L0–L4: sum-typed leaf · status lifecycle · 6-axis Pareto strength · Proposition + defeasible
  Equivalence · L2 licensing bridge · typed causal roles + Dimension algebra · L3 VAF defeat graph +
  Duhem blame · L4 AGM/TMS revision
- ✅ Phase 7 protocol-imposed fields: provenance · governance · online-FDR ledger · subject slot ·
  `representation_revision` meta-tier
- ✅ Phase 8 evaluator: typed compute-graph IR + air-gapped `verify()` (≥2 distinct adapter identities)

**Protocol runtime** (`polymer_protocol`) — complete, 5 sub-projects + 3 daemons + scheduler:
- ✅ #1 Corpus + assessment spine (`c8b7279`) · #2 oracle dossier (`a61d7dd`) · #3a/#3b SELECT pursuit
  engine + QD/heterodox/Goodhart/accumulating-belief (`03ae863`/`4293faf`) · #4a/#4b GENERATE proposer
  bus + provisional links + executable rivals + intelligent-operator seam
  (`5d7899f`/`64b8042`/`8e0bba0`/`7c7a953`)
- ✅ #5 daemons: DRIFT (`ce107b9`) · ORACLE-VALIDATION + F2 fix (`ea517c7`) · REPRESENTATION RED-TEAM
  (`9996e49`) · #5d loop-economics scheduler (`7e1d5c9`)

**Umbrella + product:**
- ✅ `pip install polymer-claims` CLI + live local node (`NodeRunner` + FastAPI SSE, `[serve]` extra) +
  3D viewer (Next 16 / React Three Fiber; sample + live modes), verified in-browser
- ✅ Real LLM generation adapter (`[llm]` extra) driving the live node (`serve --llm`)

**External audit — CLOSED** (`docs/superpowers/archive/polymer-claims-audit.md`):
- ✅ Tier A+B (`c662f1c`): bounded frame retention · tick-serialization lock · bounded SSE queues ·
  non-loopback bind guard · machine-clean JSON · `ARCHITECTURE_CURRENT.md` + `GLOSSARY.md` · v1.2 frozen
  banners
- ✅ Adapter trust registry (`67f98e3`) — the independence gate (registry core done; byte-hash +
  credential-provenance hardening still open, see caveat)
- ✅ Tier-C (`2b7ccb5`): viewer `CONTRACT_VERSION` + 6-axis strength validator · `run_cycle` output
  revalidation · packaging metadata

**Credibility arc + CES** (`docs/superpowers/archive/roadmaps/2026-06-11-credibility-arc-roadmap.md`):
- ✅ M1 structural-equivalence status (`Status.STRUCTURAL` — no more false LICENSED on structural
  collapse) · earned-strength · relational graph embedding v1 (signed-Laplacian eigenmap, silhouette 0.62)
  · live spectral layout (`procrustes-embedding-alignment`) — eigenmap as the live `NodeRunner` default,
  Procrustes-aligned per frame; `serve --layout`; force path byte-identical (design rationale in archive/specs/)
- ✅ CES-0 analysis-profile content-address · CES-1 data seam · CES-2 methylation Δβ licensing ·
  CES-3 content-address completeness · CES-4 live wiring

**Phase 2 — epistemic core** (north star: `docs/superpowers/2026-06-12-phase-2-north-star.md`):
- ✅ 2.1 e-value / FDR / VERIFY unification (`6960100`) — e-LOND (FDR under arbitrary dependence) +
  Waudby-Smith-Ramdas betting e-value + the hard 4-way VERIFY gate
- ✅ 2.2 defeat-as-e-value-update + alpha-wealth refund (`eef6143`) — `FDRTest.retracted` tombstone;
  defeat de-licenses through the ledger
- ✅ Audit remediation (`3241c8d`) — fixed a CRITICAL cross-cycle duplicate-FDR-entry bug (one e-test
  per claim lifetime)
- ✅ 2.3 live e-gate (`a8ab596`) · 2.4 drift-reopen tombstone + live-dedup (`bb619f1`)
- ✅ §2E tiered independence (`feat/2e-tiered-independence`) — REPRODUCED / REPLICATED; product e-value
  across independent cohorts as one e-LOND test; 2nd synthetic cohort demo (design rationale in archive/specs/)
- ✅ Reinstatement → PENDING (`feat/reinstatement-pending`) — `RejectionReason` marker + INTEGRATE
  reinstatement block; a defeat-rejected claim reopens to re-test when its attacker falls (symmetric to
  Phase 2.2); refuted claims stay terminal (design rationale in archive/specs/)
- ✅ n-DMPs-at-FDR (`feat/n-dmps-at-fdr`) — second methylation reduction; per-probe-significant DMP count
  licenses on a one-sample count-enrichment betting e-value; two pooled-t legs agree on the count
  (air-gap); umbrella-only (design rationale in archive/specs/)
- ✅ **§2E REPLICATED on a real 2nd cohort — STAGED, data-blocked** (2026-06-18) — cohort B = GSE86409
  (SAL adult-AML HM450); betas downloaded, ingestion + run scripts staged (`data/sal_aml/`, gitignored).
  Key finding: no open HM450 adult-AML cohort exposes machine-readable IDH → blocked on a real
  `idh_status.tsv` (user-supplied; no genotype fabrication). spec+plan
  `docs/superpowers/{specs,plans}/2026-06-18-replicated-second-cohort*`.
- ✅ **Phase D slice 1 — pre-registration ledger** (2026-06-19) — closes the §5a multiplicity leak:
  grammar `commitment_hash` + `register_test`/`resolve_test` (charge+lock the e-LOND α at REGISTRATION,
  strict no-refund) + `RejectionReason.HYPOTHESIS_ALTERED`; protocol `register_hypotheses` REGISTER stage
  + verify match-gate (post-hoc plan change → terminal REJECT) + `_reinstate` guard. Additive/opt-in,
  byte-identical when off; an agent fishing N hypotheses pays all N slots, FDR ≤ q preserved
  (conservative locked α). Subagent-driven; whole-branch opus review READY-TO-MERGE. spec+plan
  `docs/superpowers/{specs,plans}/2026-06-19-preregistration-ledger*`.
- ✅ **Phase D slice 2 — literature-shared-cause gate + incubation/ranking** (2026-06-19) — closes the
  §5a literature-shared-cause provenance leak: grammar `shared_cause` module (`SeverityProvenance`
  enum, `shared_cause_overlap`, `severity_provenance_of`, `cap_severity_for_confirmatory`) + grammar
  `Provenance.prior_cohorts` + `Licensing.severity_provenance`; VERIFY gate stamps CONFIRMATORY/HELD_OUT
  + applies severity ceiling (0.2) + strict-mode withholds; SELECT data-blind ranking penalty
  (`CONFIRMATORY_RANK_PENALTY=0.5`, injected `cohort_of_ref`) + `register_selected` budget-aware top-k
  commit; viewer passthrough + `severity_provenance` display. First concrete edge of north-star §E
  common-cause DAG. Additive/byte-identical when off; subagent-driven (7-task plan). spec+plan
  `docs/superpowers/{specs,plans}/2026-06-19-shared-cause-incubation*`. **Deferred Phase-D slices:**
  incubation strict-mode wiring, live-agent wiring, fuzzy literature→cohort resolution.
- ✅ **§E common-cause — earn REPLICATED on low shared-cause overlap** (2026-06-19) — makes the §5b
  implementation-independence condition derived+evidenced (Reichenbach screening-off, first concrete form):
  grammar `shared_cause_jaccard` + `SHARED_CAUSE_TAU=0.5`; `MaterializationContext.shared_cause_factors` +
  `Licensing.shared_cause_overlap`; overlap-aware `independence_tier_of` + `cohorts_error_independent` +
  `max_shared_cause_overlap` (REPLICATED requires distinct dimnames AND every pairwise Jaccard < τ, else
  REPRODUCED); umbrella `build_replication_inputs` gates the e₁·e₂ product on the same predicate (cohort-A
  proxy built from its contract — review caught+fixed an inert-in-production bug); verify records the
  overlap + topology/viewer surface it. Additive/byte-identical when off; subagent-driven (5-task plan,
  whole-branch opus review). spec+plan `docs/superpowers/{specs,plans}/2026-06-19-common-cause-replicated*`.
  **Deferred (full §E):** the real per-implementation causal DAG (vs the flat factor set), the formal
  screening-off probability derivation, per-adapter factor sets / grading `adapters_independent`, and
  byte-derived/credential-backed provenance for `shared_cause_factors`.

## Invariants / working agreements (don't relearn)

- `grammar/` must NEVER import `polymer_formalclaim` (enforced by `grammar/tests/test_isolation.py`);
  `protocol/` depends one-way on `grammar/` (isolation-tested).
- `grammar/` + `protocol/` are **pure/deterministic + numpy-free** (no clock/random/IO; time-like inputs
  are passed in). The ONLY impurity is the umbrella node/server. **`Corpus` = exactly 4 collections**
  (claims, defeat_edges, equivalences, fdr_ledger).
- All models subclass `_Model` (frozen, `extra="forbid"`); **collections are tuples** (deep immutability
  + content-addressing). No `dict`/`list` fields on models.
- New cross-cutting fields land **additive/optional** (`X | None = None`) with a present-only-when-Y
  validator. Opt-in features default to byte-identical behavior when off.
- numpy lives behind the umbrella `[embed]` extra; `embedding.py` / `methyl_adapters.py` are NOT
  re-exported, so base import stays numpy-free.
- Tests: per-package `uv run pytest -q` + `uv run ruff check src tests`; full gate `scripts/check-all.sh`.
  TDD: failing test first.
- Merge feature work to `main` `--no-ff`; **`main` is now pushed to `origin`** (the account flag is
  RESOLVED — 2026-06-19, `origin/main == main`). The old "local-only, never push" rule is retired. No
  active CI yet, so `check-all.sh` is still the pre-merge gate. Repo is a **single trunk** — no long-lived
  feature branches; the 2026-06-19 reconcile pruned all stale local + remote branches.

## Reference pointers

- **Forward roadmap:** `docs/superpowers/2026-06-16-autonomous-hypothesis-loop.md` · historical decision menu (archived): `docs/superpowers/archive/2026-06-13-overnight-deferred-analysis.md`
- **Phase-2 north star:** `docs/superpowers/2026-06-12-phase-2-north-star.md`
- **Credibility-arc roadmap:** `docs/superpowers/archive/roadmaps/2026-06-11-credibility-arc-roadmap.md`
- **Architecture map:** `ARCHITECTURE_CURRENT.md` · **Glossary:** `GLOSSARY.md`
- **Spectral layout guides:** `docs/spectral-layout-how-to-use.md` (usage) ·
  `docs/spectral-layout-how-it-works.md` (eigenmap + Procrustes math/theory)
- **Memory:** `project_polymer_claims_knowledge_protocol` (full phase history + follow-ups)
- **Deep design source:**
  `~/Desktop/Research/topics/epistemic-claim-foundations/generative-protocol/_FINAL_knowledge_generation_protocol.md`

## Open follow-ups (tracked, non-blocking)

- **Context-separation / pre-ship scrub (Option 3).** The TET2-vs-WT methylation example (the author's
  separate research) is removed from the live code AND genericized in the historical CES docs (case/control,
  `pinned_design` profile; local R-pipeline paths + the real cross-reactive digest stripped) — 2026-06-15.
  **Still to do before any public release** (external users won't have this content): genericize the remaining
  **Polymer Genomics / Boris / PlumberClient** integration references in the CES design docs; strip the
  `~/Desktop/Research/topics/epistemic-claim-foundations/...` design-source absolute paths cited across the
  protocol specs + this file. (The v1.2 plugin/corpus fixtures that named other research projects left
  with the v1.2 tree, moved out of the repo 2026-06-17.) None affect the running system — pure
  documentation/context hygiene.
- **Adapter-independence residual hardening** (roadmap 1c): owner/trust credential provenance is still
  operator-authored; local implementation hashes are now byte-derived and satisfactions record the
  credential pair.
- **Earned-strength 2d:** `evidence_against_null` from a real test statistic with n (now partly
  subsumed by the e-value gate).
- **I2 / I1:** `grounded_extension` ~O(N³) worklist rewrite + untrusted-corpus ingestion size/depth
  bounds (only bites with large untrusted corpora — federated layer).
- **Vector leaves** (`QuantityVectorLeaf`): a DMP is vector-valued; scalar reduction is an honest
  simplification until a claim needs the full vector.
- **Card/viewer value display** for `stats::mean_diff` plans (computed value + ✓✗ only populated for
  `builtin::const` today).
- **Multi-dataset drift** (CES-4 single-world `current` → per-claim) · per-frame viewer drift annotation
  ("knowledge breathing").
- **User-gated:** PyPI publish · polymerbio.org viewer integration · federated / BYO-compute
  (`POST /inject` hook).
