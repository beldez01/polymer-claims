# ⟳ Polymer Claims — RESUME HERE

> Hook-loaded continuity file (a SessionStart hook surfaces it). **Keep the *Current state* + *NEXT*
> sections current at every phase boundary.** Detailed build history lives in git (`git log --oneline`)
> and the canonical spec (`docs/superpowers/polymer-claims-canonical-spec.md`).
> One-page architecture map: `ARCHITECTURE_CURRENT.md`. Reserved terminology: `GLOSSARY.md`.
>
> **Doc consolidation (2026-06-29):** the per-feature `specs/`, `plans/`, and the whole `archive/`
> tree were culled — that shipped-feature design history now lives only in git. Inline
> `docs/superpowers/{specs,plans,archive}/…-design.md` paths below are historical references
> (find them via `git log`/`git show`); only `specs/` + `plans/` for *pending* work remain in-tree.

---

## Current state (2026-07-12, session close) — GAP-3 SHIPPED: interval/range/bound on QuantityLeaf (LATEST)

> On `main` (committed, not yet pushed as of this block; `origin/main` was `699a963` at the synbio-ramp push).
> **First core-grammar expansion since Phase 2a.** SDD ledger `.superpowers/sdd/progress.md` (GAP-3 Tasks 1–5).
> Corpus stays **4**; grammar stays pure + numpy-free. Spec `docs/superpowers/specs/2026-07-12-gap3-interval-bounds-design.md`,
> plan `docs/superpowers/plans/2026-07-12-gap3-interval-bounds.md`.

**GAP-3 — `QuantityLeaf` gained optional `low`/`high` bounds** (additive, byte-identical when boundless).
Either end may be open, so one representation covers point / closed-range / floor / ceiling. A new
`_bound_discipline` validator enforces ordering (`low < high`), containment (`value` within present bounds),
and spread-exclusivity (bounds XOR symmetric `uncertainty`); the wrap-serializer drops `low`/`high` when None
(byte-identity proven — `test_leaf_context.py` baseline intact). Tasks 1–5, all per-task reviewed:
- **T1 core grammar** (`grammar/src/polymer_grammar/leaf.py`): fields + validator + serializer; grammar 585→593.
- **T2**: C3 `car_threshold_claim` re-expressed `low=1e2/high=1e4`; the armed `test_c3_interval_gap` xfail flipped to passing.
- **T3**: manifest pipeline (`ManifestLeaf` + `build_claim`) carries the bounds.
- **T4**: five interval-family entries re-expressed with honest bounds (`value=low`, fabricated `uncertainty` dropped) —
  cd19 floor, adar range, gate range, cascade range, vivovec floor; **GAP-5/6/9/10/12 marked RESOLVED** in the gap-log;
  gap-log now **6 open** (GAP-7/8/11/13/14/15). Two domain refinements DEFERRED with armed tripwires
  (GAP-9 log-scale, GAP-10 discrete-integer). Universe regenerated: **798 nodes, synbio 44, all other arms + 6-licensed unchanged**.
- **T5**: full gate + this continuity.

### NEXT — where to proceed
- **Push `main`** (synbio-ramp + GAP-3) once coordinated with the other instances (shared checkout).
- **Remaining gaps** (data/consumer-gated, not yet demanded): GAP-7 (ANALYTIC measurement basis), GAP-8 (gene/locus
  context sub-key), GAP-11 (per-tumor stratification), GAP-13 (endpoint-type), GAP-14 (composite/vector quantity),
  GAP-15 (structured categorical). Follow the same recipe when a real corpus demands one.
- **Phase 2d licensed spine** (still the headline, data-gated): `synbio/spine.py` two-leg floor over real AML fusion RNA-seq.
- **Aggregator precision follow-up:** `aggregate_gaps` dedup on a controlled `gap_kind` tag + reconcile vs canonical GAP-1..4.

---

## Current state (2026-07-11, session close) — SYNBIO RAMP: arm grown 5→44, manifest ingestion + gap harvest (superseded by the GAP-3 block above)

> **MERGED to local `main` via fast-forward (`main` now `3c8bd86`); branch `feat/synbio-ramp` deleted. NOT
> PUSHED** — user chose local-only (shared checkout; `origin/main == c157d55`, local `main` is +13 ahead;
> coordinate before pushing). Whole-branch review (Opus): READY TO MERGE YES; full suite 804p/1s/1xfail. SDD ledger:
> `.superpowers/sdd/progress.md` (Tasks 1–10). Corpus stays **4**; grammar/protocol **untouched**
> this arc (all additive umbrella-side + registry). The 759-node figure below is superseded:
> the merged universe is now **798 nodes** (pharmaco 696 · reference/polymergenomics 47 · immuno 11 ·
> **synthetic-biology 44**), **6 licensed** (synbio adds none — all CONJECTURED).

**SYNBIO RAMP (WAYLAND breadth) — the synthetic-biology arm went from 5 probe claims to a 44-claim
sub-universe via a manifest-driven ingestion pipeline.** Tasks 1–10 all shipped + reviewed on
`feat/synbio-ramp`:
- **Pipeline (Tasks 4–6):** JSON manifest schema (`synbio/manifest.py`) → deterministic
  `build_manifest_claims` (`synbio/ingest.py`, reported-stratum, LITERATURE_EXTRACTED/CONJECTURED
  only — nothing self-licenses) → `aggregate_gaps` gap-ledger (`synbio/gap_ledger.py`, dedup
  schema_fit → canonical GAP-N). Patterns `reported_quantity`/`mechanistic_law`/`sense_and_kill`
  registered (Tasks 2–3).
- **Content (Task 7, human-review-gated):** 5 reviewed chapter manifests
  (`data/synbio_compendia/manifests/plm-{02,03,06,07,08}`) = **39 buildable claims** (23 quantity /
  16 proposition) across sensing 16 / computing 8 / actuation 7 / delivery 8, all built through the
  real v1.3 grammar. Fidelity independently grep-verified vs source; extractors declined to
  fabricate stated ranges (flagged as gaps instead). Operator approved the yield.
- **Merged universe (Task 8):** arm **renamed `synbio` → `synthetic-biology`** (subject name, not a
  dir name); per-claim **`topic` facet** threaded through `ArmFacet`/`ArmSource`/`merge_universes`
  + `make_merged_universe.py`. Regenerated `viewer/public/merged-universe.json` → 798 nodes,
  other arms byte-stable. **NOTE: regen is SLOW (~13 min — real GDSC pharmaco mechanism scan);
  full `tests/` suite likewise. Use targeted tests for iteration.**
- **Spine seam (Task 9, license DEFERRED):** `synbio/spine.py` — `expression_floor_claim` +
  `two_leg_floor_agreement`, exercised on synthetic values, **no `run_cycle`, no data pinned,
  status CONJECTURED.** DATA GATE for next session in the module docstring: pin real AML fusion
  RNA-seq (TCGA-LAML TPM via UCSC Xena, or BLUEPRINT hematopoietic RSEM) → "RUNX1-RUNX1T1 clears the
  ~13 TPM floor in AML" @REPRODUCED. Warm up on PAX3-FOXO1.
- **Gap harvest (Task 10):** gap-log extended to **GAP-5..GAP-15** (11 new, none resolved —
  core-primitive-adjacent, byte-identity-gated). **Headline finding:** the interval/range/floor/bound
  family (GAP-5/6/9/10/12) is 5 of 11 and all reduce to the deferred **GAP-3 (interval)** — the real
  corpus now demands un-deferring it (highest-value next core expansion). Also: `aggregate_gaps`
  dedup is too literal (keys on constraint prose → 11 raw = 11 canonical, no collapse); reconcile
  against GAP-1..4 + a controlled `gap_kind` tag. Details: `docs/superpowers/notes/2026-07-10-synbio-grammar-gaps.md`.

### NEXT — where to proceed (synbio ramp)
- **Un-defer GAP-3 (interval/range) + GAP-5/GAP-12 (floor/bound):** the corpus is demanding it; a
  single core `QuantityLeaf` expansion (optional `value_range` / `value_relation` / `bound`, all
  additive+optional, byte-identity-proven, drop-when-None serializer per the 2a `MeasurementContext`
  recipe) retires 5 of the 11 new gaps at once. This is the next core-grammar slice.
- **Phase 2d licensed spine (data-gated):** feed `spine.py`'s `two_leg_floor_agreement` real AML
  fusion RNA-seq through the SE-Contract seam + two-leg registry; `run_cycle` mints the first
  synbio LICENSE@REPRODUCED. Confirm data availability first.
- **Aggregator precision follow-up** + **finish-branch:** merge `feat/synbio-ramp` (final
  whole-branch review pending), then reconcile the gap ledger's dedup.

---

## Current state (2026-07-11, session close) — immuno first-class + naming/direction decisions (superseded by the synbio-ramp block above)

> `origin/main == f3bf319`. **Supersedes the 761-node / immuno-2 figures below:** the immuno-arm cleanup
> dropped 2 phantom duplicates, so the merged universe is now **759 nodes** (immuno 11 · pharmaco 696 ·
> reference-corpus 47 · synbio 5), **6 unique licensed**. Corpus = 4; grammar/protocol untouched.

**IMMUNO ARM MADE FIRST-CLASS (`f3bf319`)** — immuno now has its own canonical bundle
`data/demo/immuno_universe.json` (11 nodes, real hyphen ids: 2 licensed count-enrichment MHC/HERV-K +
9 refused region-Δβ), and those 11 were REMOVED from the reference seed where they'd been mis-tagged
`arm=polymergenomics` and duplicating the old underscore-id stubs. `collect_immuno` patched to hold the
non-count (region) nodes (categorical leaf + pending/rejection reasons). Merge unit tests 5/5; no betas.

### Decisions to carry forward — NOT yet executed (for the next instance)
1. **Rename the "polymergenomics" arm by SUBJECT — it's a project/dir name, not a subject.** DECIDED:
   split the 47 reference claims into their 4 real subjects — **immunogenetics** (HLA substitution/
   methylation/expression), **transposable-elements** (ERV/LINE silencing/methylation/oncoexaptation),
   **dna-biophysics** (recombination, nucleosome, curvature), **molecular-evolution** (codon cost, COSMIC
   signatures, Ti/Tv). Update `collect_polymergenomics` to emit 4 subject `ArmSource`s via a per-claim
   subject map + adjust the `make_merged_universe` call; regenerate. **Stop labeling any arm "polymergenomics".**
2. **Self-containment — stop tapping sibling directories.** The universe LOADS from in-repo JSON (fine);
   only *regeneration* reaches out — the immuno drive reads the WGBS atlas in `~/Desktop/PolymerGenomicsAPI/`.
   Going forward: pin the small extracted subsets we actually use into `polymer-claims/data/` so even
   regeneration is self-contained; retrofit the immuno source when convenient.
3. **Rebalance toward SYNTHETIC BIOLOGY (the priority).** Universe is pharmaco-heavy (696/759); synbio is 5.
   The next instance's focus is RAMPING UP the synbio arm (WAYLAND). Pharmaco is over-represented relative
   to intent — don't add more pharmaco claims for now.

---

## Current state (2026-07-11) — UNIFIED UNIVERSE + promoter contract (superseded by the session-close block above; `origin/main` was `a32e6ed`)

> **`main` PUSHED — `origin/main == a32e6ed`.** Clean linear lineage over the WAYLAND + pharmaco arcs
> below (both ancestors, both still valid). Corpus = 4. grammar/protocol untouched this arc (all
> umbrella/viewer/scripts-side; still numpy-free).

**UNIFIED UNIVERSE (`a32e6ed`) — all four arms merged into ONE faceted universe** (the accumulating-store
"one atom, many links" design; spec `docs/superpowers/specs/2026-07-10-accumulating-universe-store-design.md`).
- `src/polymer_claims/merge_universes.py` + `viewer/scripts/make_merged_universe.py` → `viewer/public/merged-universe.json`;
  viewer now DEFAULTS to it (`ClaimUniverse.tsx` loads `/merged-universe.json`, falls back to `/pharmaco-universe.json`).
- **761 nodes** — pharmaco 696 · polymergenomics 58 · synbio 5 · immuno 2 — each carrying additive `arm`+`modality`
  facets (node schema otherwise identical to the pharmaco bundle). Per-arm statuses PRESERVED verbatim (a UNION,
  NOT a re-run of the gate): **8 licensed / 611 pending / 94 rejected / 48 conjectured**.
- Verified: full suite **787 passed** (independent run) / 1 skip / 1 xfail; merge unit test 5/5; Playwright
  browser-render (per-arm legend, licensed across arms, claim card shows `arm` facet; screenshots in `.superpowers/sdd/screenshots/`).
- **Rough edges (follow-ups, not blockers):** immuno's 2 nodes reconstructed from grammar primitives (not a strict
  `Corpus`; `inf` e-value capped 1e300); edges only within the polymergenomics sub-cluster; static snapshot (`n_cycles:0`).

**PROMOTER SE-CONTRACT (`edb1322`) — reparam-evaluator step 0** (second measurement space). `se:gdsc_pharmaco_promoter@1`
via `load_gdsc_promoter_methylation()` + `ingest_gdsc_pharmaco_promoter()`; `metadata.modality="methylation_promoter"`
(first `modality` facet). Empirical: MGMT→TMZ direction FLIPS to mechanistically-correct over promoter (−0.069) but
stays sub-threshold; CDK4/6i is gene-body-SPECIFIC (dies over promoter) → "which space is apt" is mechanism-dependent
(validates the per-claim hybrid generator). See memory [[project_polymer_reparameterization_evaluator]].

### NEXT — where to proceed (unified universe / reparam)
- **Measurement-space registry** — the shared next step for BOTH the reparam evaluator and the accumulating store
  (catalog of SE-Contract dimensions per assay). Spec `docs/superpowers/specs/2026-07-10-reparameterization-evaluator-design.md`.
- **Follow-ups:** clean immuno into a real `Corpus`; re-point `check_controls` MTAP→CDKN2A→Palbociclib; the persistent
  append-only content-addressed claim LOG (the merge today is a static union-into-one-bundle VIEW, not yet the persistent store).
- e-BH RULED OUT (2026-07-11 — licenses ~0 for n=696; do not re-chase). "License more" = more data/modalities, not a different FDR.

---

## Current state (2026-07-10, later) — authoritative snapshot (WAYLAND synbio arc)

> `main` is **PUSHED to `origin/main`** (`origin/main == main` as of the Wayland arc, 2026-07-10;
> tip `db5e05e` or later doc commits). Lineage is clean & linear — the immuno-erv arc (`47ddda5`) and the pharmacogenomic engine
> are **ancestors** of HEAD (both already on `main`, both already pushed to origin at `c0c8a11`); the
> immuno-erv snapshot below is a **still-valid parallel arm**, not superseded (different module). Corpus
> = exactly 4 collections. **grammar/protocol note:** the grammar gained ONE additive field this arc
> (`MeasurementContext` on `QuantityLeaf`) — proven byte-identical (drop-when-None serializer); still
> numpy-free.

**WAYLAND — the synthetic-biology claims sub-universe** (new arc, this session). Goal: formalize the
`Research/topics/{synthetic-biology,programmable-living-medicines}/` compendia into a licensed claims
sub-universe → a **blinded, pre-registered re-derivation of the Durendal genotype-directed therapy**
(RUNX1-RUNX1T1 t(8;21) AML) as proof the engine *derives*, not just verifies. Canonical docs:
- Program plan: `docs/superpowers/plans/2026-07-10-synbio-claims-universe.md` (5-phase arc + Phase-1 tasks + **Progress Log**).
- Phase 0 design: `docs/superpowers/specs/2026-07-10-synbio-claims-universe-design.md` (taxonomy, two-stratum rule, firewall, expansion doctrine).
- Phase 2 design: `docs/superpowers/specs/2026-07-10-synbio-phase2-design.md` (decomposition 2a-2d).
- Gap report (Phase-2 entry gate): `docs/superpowers/notes/2026-07-10-synbio-grammar-gaps.md`.
- SDD ledger (commits per task): `.superpowers/sdd/progress.md` (WAYLAND sections).
- Governing law: memory `feedback_ir_monotonic_expansion` (additive-or-nothing, proven byte-identical; general→core, domain→periphery).

**Shipped (all merged to local `main`):**
- **Phase 0 spec + Phase 1 probe** (`2bb5e11`..`3f44881`). New `src/polymer_claims/synbio/` pkg (umbrella-side). 5 reported claims C1-C5 (`claims.py`) validate through the real v1.3 grammar at **CONJECTURED** via `LITERATURE_EXTRACTED` — the **two-stratum rule**: reported priors never self-license; only recomputed claims (Phase 2d) join the licensed spine. `probe.py` = harness. Umbrella 779p, no regression; Opus review READY-TO-MERGE.
- **Phase 2a — GAP-2 resolved** (`a811185`+`753c02d`), the **first core-grammar expansion** under the doctrine: optional structured `MeasurementContext` (tissue/cell_line/assay/condition, all-optional, all-None rejected) on `QuantityLeaf` + drop-when-None `@model_serializer` (mirrors `capability.py:188`). **Byte-identity + hash-stability PROVEN and Opus-independently-verified.** C2 re-expressed w/ assay context. grammar 588 / protocol 497 / umbrella 780p-1xfail.
- **Grammar gap findings** (probe output): GAP-2 (context) RESOLVED; **GAP-3 (interval/range) DEFERRED** (YAGNI — no spine caller yet; xfail tripwire armed in `tests/synbio/test_claims_intervals.py`); GAP-1 (reported-quantity/mechanistic-law patterns → 2b registry) + GAP-4 (reported defeaters must be `provisional=True` → 2b wiring) open.

### NEXT — where to proceed (WAYLAND)
- **Phase 2b — patterns** (unblocked, fast, recommended next): register `reported_quantity`, `mechanistic_law` (retire the Phase-1 placeholder `PatternRef`s in `synbio/claims.py`), and the domain `sense_and_kill` pattern in the open `pattern.registry`. Additive, no core change.
- **Phase 2c — ingestion**: markdown→claims extractor over the compendia (human-in-the-loop), reported-stratum at scale.
- **Phase 2d — the licensed spine** (Phase-2 exit gate + "traction"): execution adapters over a real expression atlas → "RUNX1-RUNX1T1 clears the ~13 TPM floor in AML" LICENSED@REPRODUCED, reusing the SE-Contract seam + two-leg registry (STRATA/methyl). **DATA-GATED: needs real AML fusion-expression RNA-seq** — confirm availability before committing; warm up on PAX3-FOXO1. Uses 2a's `MeasurementContext(tissue="AML", assay="RNA-seq TPM")`.
- **Phases 3-4**: blinded seed + pre-registration (firewall) → the Durendal re-derivation (headline). See program plan.
- **Push status:** `main` (through the Wayland arc) is PUSHED — `origin/main == main`. The checkout is shared with other instances; coordinate before pushing further unrelated local commits.

---

## Current state (2026-07-10) — pharmacogenomic universe arm (parallel; all on `main`)

> The STRATA→pharmaco methylation-marker→drug licensing engine. Spec `specs/2026-07-08-strata-pharmaco-licensing-design.md`, plan `plans/2026-07-09-strata-pharmaco-licensing.md`; module `src/polymer_claims/pharmaco/` + `pharmaco_adapters.py` + `pharmaco_populate.py` + `PHARMACO_ASSOC_CELL` + `[pharmaco]` extra. Capability summary in `ARCHITECTURE_CURRENT.md`. Full memory: `project_polymer_spc_demo`, `project_polymer_claims_knowledge_protocol`.

- **Real-data proof (through the real gate):** `MTAP→Palbociclib` LICENSED @ REPRODUCED (betting e≈216); `MGMT→Temozolomide` REJECTED (e≈0.78, both legs refute). Residue taxonomy reconciled in the spec: an agreed-refuted null → REJECTED = morphospace forbidden region (retained, not erased); an under-powered hit → PENDING frontier.
- **Scaled universe (`pharmaco-populate --full`, real GDSC):** 696 claims / 199 drugs → **4 LICENSED / 609 PENDING / 83 REJECTED** (top e-value: CDKN2A/CDKN2B×Palbociclib, CDKN2A×Nutlin-3a, BCL2L1×AZD5991 — coherent CDK4/6i-cell-cycle/p53 + apoptosis). Wired as the viewer's default bundle (`viewer/public/pharmaco-universe.json`; bundler `viewer/scripts/make_pharmaco_universe.py`), browser-verified. Launch: `cd viewer && npm run dev`.
- **Two engine findings caught at scale:** (1) e-LOND **batch-ordering pathology** — alphabetical registration starved strong-but-late claims (bar grows ~32.9·t²) → 0 licensed; FIXED (umbrella-only) by registering in strength-rank order. (2) strength-rank is a **proxy** for the licensing betting e-value (correlated, not monotonic). **e-BH RULED OUT (2026-07-11)** as a "license-more" lever — for n=696 its bar for even the strongest claim is n/q=13,920 (top e-value 4,736) → e-BH licenses ~0, WORSE than strength-e-LOND's 4; order-independent but far more conservative for large-n-few-signals. The real structural answer is the **accumulating store** (makes the FDR a true stream — e-LOND's native substrate). "License more, honestly" = more data/modalities, not a different FDR procedure.
- **NEXT (pharmaco arm):** the re-parameterization evaluator (`specs/2026-07-10-reparameterization-evaluator-design.md`; note `notes/2026-07-10-parameterization-rejection-reasoning.md`) — **IN PROGRESS**: step 0, the promoter-methylation SE-Contract (`se:gdsc_pharmaco_promoter@1`, a real second measurement space + first `modality` facet) is being built, with an empirical **MGMT→TMZ-over-promoter** test (does the promoter signal appear where the gene-body average washed it out?). Then: the accumulating faceted universe store (`specs/2026-07-10-accumulating-universe-store-design.md`); re-point `check_controls` to CDKN2A→Palbociclib. (e-BH ruled out — see above.) **SPC demo Monday.**

---

## Current state (2026-07-10, earlier) — immuno-erv arm (parallel, still valid; main hash `47ddda5` now an ancestor of `753c02d` above)

> Session 2026-07-09 → 10. `main` was `47ddda5` at this snapshot (now an ancestor of `753c02d`; the
> "ahead of origin" note is stale — origin/main is now `c0c8a11`). grammar/protocol stay pure + numpy-free;
> **Corpus = exactly 4 collections**. Also on `main` (merged concurrently by another session): the
> **pharmacogenomic engine** (`[pharmaco]` extra).

**Immuno / ERV methylation licensing drive merged** (`feat/immuno-erv-drive` → merge `47ddda5`) — two
genuine **licensed immuno nodes** on the real **Loyfer 2023 WGBS atlas** (GSE186458), via the **e-LOND
count-enrichment** route, contrasting **Lymphoid (n=30) vs Myeloid (n=17)** lineages:
- **MHC n-DMP** (`rip_mhc_ndmp`): chr6:29.9–33.1 Mb, 11,582 complete-case CpG probes; DMP count 4,682
  (pooled-t) / 4,677 (rank-sum), both ≫ pre-registered k=1,738; **count e-value → ∞** ≫ e-LOND slot-1
  bar 32.9 → **LICENSED**.
- **HERV-K LTR n-DMP** (`rip_hervk_ndmp`): 630 real HML-2 `LTR5_Hs` elements, 2,587 probes; DMP
  1,083 / 1,073 ≫ k=389; **e-value 3.25e274** → **LICENSED** (the ERV node).

New umbrella pieces (all umbrella-side; grammar/protocol untouched): `ingest/loyfer_wgbs.py`
(`extract_region`/`extract_regions_multi`/`extract_cpg_matrix`/`extract_cpg_matrix_multi` over Loyfer
beds), `ingest/build_loyfer_contract.py` + `ingest/build_cpg_matrix_contract.py`, `panels/`
(pre-registered locus panels + `assert_rmsk_hg38` + `coverage_precheck`), `ingest/hervk_loci.py`, three
drivers (`rip_immuno` region-Δβ + the two n-DMP drivers), and `viewer/scripts/make_immuno_universe.py`
→ `data/demo/immuno_universe.json` (the 2 blue nodes). `[wgbs]` optional extra (pysam; gzip fallback
works without it). **No real betas committed** (local-only / gitignored).

**Key finding:** region-Δβ licensed NOTHING on real data (betting e-value ~1 — a single scalar bet —
far below the multiplicity bars), even at lineage power; the **e-LOND multiplicity gate was demonstrated
to bite** (identical e-value licenses at an early slot, withheld at a deep slot; panel-order flip flips
the verdict). **Count-enrichment** (evidence accumulated across thousands of probes) is what licenses —
the same route as the TCGA n-DMP proof. Post-merge cleanup: dead `HodgesLehmannMeanDiffAdapter` /
`immuno_independent_registry` removed (superseded by the `methyl_adapters` legs the drivers use).

### NEXT — where to proceed
- **Push `main` to origin** when ready — coordinate with the concurrent pharmacogenomic-engine line (both are in local `main`).
- More count-enrichment immuno claims (L1HS young-LINE-1 family; other MHC sub-regions); a **REPLICATED**
  tier via a 2nd WGBS cohort. The neg2 backlog (below) + pharmacogenomic-engine follow-ups remain open.

---

## Current state (2026-07-08) — historical (superseded by 2026-07-10 above)

> Session 2026-07-07 → 08. `main` = `9643d8b`, **pushed to `origin`** (`origin/main == main`). All suites
> green: **grammar 578 · protocol 497 · umbrella green**; ruff clean. grammar/protocol stay pure +
> numpy-free; **Corpus = exactly 4 collections**. Feature branches merged and deleted; single trunk.

**Merged since the 2026-07-01 snapshot:**

- **Phase 1 + Phase 2 real-data licensing merged** (`c4fe813`, `b8fbb1f`) — the `feat/phase1-license-loop`
  work from the last snapshot is now on `main` (`verify-kernel --real` → LICENSED @ REPRODUCED on real
  TCGA-LAML; the migrated HLA-A promoter claim licensed on real BLUEPRINT WGBS).
- **R5.1 — genuine adapter independence** (2026-07-07, `e789b05` / `c99c35a` / `12a1fa6`, merges `4f9f8d9`
  + `2e79457`) — the two methyl legs are now *genuinely* different algorithms (an n-DMP **rank** leg +
  a **Hodges-Lehmann region-Δβ** leg, `both_satisfy_criterion` agreement), and REPRODUCED results
  **attest per-leg independence evidence**. Plus the in-repo **tautology-audit** findings +
  shape-dependent independence docs (`5952695`, `307165a`).
- **Duhem consistency fold — the sheaf's H¹ frustration now ACTS on claim status** (2026-07-07, this
  session). Three slices, each brainstorm → spec → plan → subagent-driven-TDD → whole-branch review:
  1. **neg2 whisper backlog** (`4e59911`) — a `/neg2` peripheral read of the foundations corpus triaged
     into 5 buildable seams + notes (`docs/superpowers/specs/2026-07-07-neg-whisper-backlog-design.md`).
  2. **Item ① — H¹→blame-set coupling** (`3eaca5f`..`0927867`) — pure `blame_bridge.py`: an obstruction
     (frustrated cycle, **no local witness**) → Duhem blame; single cycle → `PENDING duhem_underdetermined`;
     a claim shared across ≥2 cycles → robust (`ROBUSTLY_BLAMED`, now wired).
  3. **The fold wired into `run_cycle`** (`215b6c8`..`50a7dd4`) — `apply_duhem_consistency` runs after
     `integrate` (before the survival-credit snapshot): **demote** LICENSED claims on a frustrated cycle
     to `PENDING duhem_underdetermined`, **reopen** to `PENDING reinstated` when the contradiction
     structurally resolves. **Ledger-neutral** (warrant-only per Refund-Validity — `FDRTest` stays live,
     no `retract_tests`), **demote-only** (never terminal-rejects). The detector `frustration_obstructions`
     moved into pure protocol; `extract_sheaf` gained an `effective_only` switch (effective drives demote,
     structural drives reopen).
  4. **`frustrated_vertices`** (`a37aa84`..`9643d8b`) — demote/reopen now key on membership in *any*
     frustrated cycle (edge-identity **biconnected blocks**, multigraph-correct), fixing a
     spanning-tree-dependent bug where the reported-obstruction union could miss a genuinely-frustrated
     claim (theta-graph witness). `frustration_obstructions` retained for the audit/viewer only. The
     whole-branch review fuzzed the BCC against a brute-force cycle oracle (8,000 graphs, 0 mismatches).

### NEXT — where to proceed

The neg2 backlog (`docs/superpowers/specs/2026-07-07-neg-whisper-backlog-design.md`) has **4 buildable
items left** (item ① shipped above):
1. **② independence-as-claim** — promote the shared-cause/common-cause overlap from an operator-asserted
   flag to a first-class **defeasible claim** with its own evidence bar (the correlated-variance probe
   from `2026-06-29-adapter-independence-hardening-notes.md`). *The load-bearing risk named in every doc.*
2. **③ residue budget** — a residue-value term in the `protocol/economics.py` scheduler so the PENDING
   graveyard (esp. `duhem_underdetermined`) earns scheduled re-examination, not silent accretion.
3. **④ q-stationarity horizon** — stamp the corpus `q` with a drift-epoch / validity window so the
   actuarial framing carries its stationarity assumption explicitly.
4. **⑤ forbidden-vs-unobserved** — a severity-backed **licensed-negative** claim path so the morphospace
   "forbidden region" is separable from "not yet looked."

**Deferred (non-blocking) follow-ups from the duhem line:** promote the `frustrated_vertices` fuzz-vs-oracle
harness into a seeded property test; a guard to skip the structural `extract_sheaf` pass when no claim is
`PENDING duhem_underdetermined` (premature optimization — do on measured cost); per-claim suspension
provenance for a finer reopen (current policy is conservative: reopen iff on no structural frustrated cycle).

### Environment notes for resuming

- **Other-instance in-flight files uncommitted on `main`** (untracked): `docs/the-spine-one-pager.{typ,pdf}`,
  `epistemic-core-derivation.{typ,pdf}`, `prior-art-and-novelty.{typ,pdf}`, `open-questions-research-plan.typ`,
  `foundations/{residualism,compute-boundary}.md`, `roadmap-cross-domain-ecosystems.md`, `actionability-and-roi.md`,
  and the `2026-06-29-{adapter-independence-hardening-notes,claim-type-menu-design}.md` specs. They need
  their author's commit-or-discard call; left untouched.

---

## Current state (2026-07-01) — historical (superseded by 2026-07-08 above)

> Session 2026-06-30 → 07-01. Paused for compute. Servers stopped; scratch bigWigs removed.

**Merged to `main`** (import + viewer layer):
- **Foreign-claim ingestion route** — `ingest-formal-claims` CLI + `src/polymer_claims/formal_claim_import.py`
  (`--sheaf-active` mode). Imports external formal-claim-IR corpora as **WITNESSED** (conjectured/pending,
  **never licensed** — they haven't passed our gate). Importer script `scripts/import_formal_claim_ir.py`.
- **47-claim PolymerGenomics reference universe** — `data/demo/polymergenomics_universe.json`
  (+ `…_sheaf.json`). It's the viewer's default bundle (`viewer/scripts/make_polymergenomics_timeline.py`).
- **Viewer aesthetics** reconciled to the metrology system: node scale (`viewer/src/lib/ring.ts`
  BASE_RADIUS 0.07) + origin-centered ±X/Y/Z axes (`ReferenceFrame.tsx`).

**On branch `feat/phase1-license-loop` — 2 commits, NOT yet merged:**
- **Phase 1 (`c4fe813`)** — proved the licensing loop. `verify-kernel --real` → **LICENSED @ REPRODUCED**
  on real TCGA-LAML (on-disk Xena matrix, no download). A licensed n-DMP node is injected into the
  universe bundle via `viewer/scripts/make_universe_timeline.py`.
- **Phase 2 (`b8fbb1f`)** — licensed a **migrated** claim on real data.
  `hla_t_naive_promoter_methylation_bimodal` promoted WITNESSED→LICENSED via the **mean_diff air-gap**
  (StatsPure vs StatsStdlib) over real **BLUEPRINT WGBS** (`datasets/hla_a_promoter_meth.csv`,
  Δβ≈0.59 ≈ the claim's stated 0.51). Factory `exec_adapters.hla_promoter_meth_claim()`,
  test `tests/test_hla_promoter_license.py`. Universe bundle now shows **2 blue licensed nodes**.

### NEXT — where to proceed
1. **Merge** `feat/phase1-license-loop` → `main` (Phase 1 + 2). Full suite was green before these
   additive changes; touched-area tests pass. `git checkout main && git merge --ff-only feat/phase1-license-loop`.
2. **Generalize licensing:** more **mean_diff** migrated claims (bind real data→CSV, set threshold,
   reuse the `hla_promoter_meth_claim` pattern). Then the frontier — **correlation** claims
   (`spearman_rho`, a large fraction of the 47, e.g. `hla_a_dg37_vs_tpm`): needs TWO independent
   correlation adapters + a `CORRELATION_CELL` + a generation adapter (none exist — scope first).
3. **Optional conceptual thread:** a first-class `WITNESSED` status (currently: `--sheaf-active`
   pending + the discipline written in `docs/superpowers/foundations/compute-boundary.md`).
4. **Uncommitted design docs** (untracked — decide whether to commit): `foundations/compute-boundary.md`
   (the notary / verification-ladder / Science-Claw / WITNESSED spine of this session), plus
   `EXPLAINER.md`, `foundations/residualism.md`, and the `docs/`+`specs/` files in `git status`.

### Environment notes for resuming
- **pyBigWig** was installed into `.venv` (only to extract HLA betas; the committed licensing path is
  pyBigWig-free — reads the CSV).
- Real **TCGA-LAML Xena matrix**: `/Users/zbb2/Desktop/Site Projects/Hack/data/tcga_laml/TCGA-LAML.methylation450.tsv.gz`
  → `verify-kernel --real --xena <that> --cbioportal data/tcga_laml/cbioportal` (no `--fetch`).
- Regenerate the HLA CSV per `src/polymer_claims/datasets/hla_a_promoter_meth.SOURCE.md`.
- View the universe: `polymer-claims serve --seed-corpus data/demo/polymergenomics_universe.json --layout spectral`
  + `cd viewer && npm run dev`; or just `npm run dev` (default bundle already shows the 48-node universe).

---

## Current state (2026-06-29) — historical (superseded by 2026-07-01 above)

> **This is the single current-state summary.** The dated blocks further down are **historical**
> (kept for build detail); when they disagree with this section, *this* section wins. Full shipped
> history is in the **Done checklist** below + `git log`; the forward plan is
> `docs/superpowers/2026-06-23-remaining-roadmap.md` (Path α — wedge-first).

**Where it stands.** `main` is a single trunk, ruff clean, all suites green:
**umbrella 572 · grammar 427 · protocol 431** (+ the grammar isolation guard) + viewer `tsc`/build.
`grammar/` + `protocol/` stay pure + numpy-free; **Corpus = exactly 4 collections**; numpy lives
behind the umbrella `[embed]` extra. **The `beldez01` account flag is RESOLVED (2026-06-29)** —
GitHub Actions / PyPI publish are unblocked (no CI workflow committed yet; `scripts/check-all.sh`
remains the local gate until one mirroring it is added).

**Shipped (newest first):**
- **V2.0 Slice 1 — evidence-licensed capability (2026-06-29, merge `9b8848c`, LOCAL only — not yet
  pushed; main is now ahead of origin/main).** A second, honest licensing route that is NOT the
  two-adapter recompute air-gap: a 4th capability `eval::benchmark_advantage@v1` whose claim is
  identified by its plan's `execution_contract` (bound by `commitment_hash`), dispatched **in-cycle,
  post-commit** in `execute_ground` to an injected `EvidenceExecutor` (protocol-typed; numpy impl
  umbrella-side) instead of `verify()`. It scores a model-vs-**precommitted-baseline** benchmark
  advantage as a **paired sequential betting e-value** (reuses the GRAPA core), and `verify_stage`
  mints `LicenseRoute.EVIDENCE_LICENSED` (new) **only on e-LOND discovery + the standard eligibility
  gates** (selection, commit, mandatory pre-registration with locked α, grounded-extension,
  commitment-match) with a 5-field ledger-equality check. **The e-LOND discovery IS the decision** (no
  separate criterion); the BH bar is honestly exempt (e-LOND is the multiplicity control). New grammar:
  `EvidencePolicy`/`ExecutorDescriptor`+`ExecutorTrustEntry` (content-addressed, validated registries),
  `VerificationPolicy`/`ExecutionContract`/`EvidenceProvenance`, `verification_standing`, optional
  `CapabilityCell.verification_policy`+`content_hash`, optional `EvaluationPlan.execution_contract`,
  `DataRefKind.BENCHMARK`, `PendingReason.EXECUTION_ERROR`. **Compat byte-clean:** drop-when-None
  `model_serializer`s keep ALL existing attestation/commitment/cell hashes byte-identical
  (git-verified zero golden drift, no re-bless). Content-addressed end-to-end (whole-executor
  credential + hash chain checked before scoring). Built via 19 subagent-driven TDD tasks (each
  task-reviewed, risky ones opus-reviewed; final whole-branch opus review READY-TO-MERGE, no
  Critical/Important). Suites: umbrella 697, grammar 568, protocol 467, isolation. **Honest scope
  caveats:** the demo benchmark/fixture is a mechanics demonstration (powered DGP, not real biology);
  label-blindness is **credential-enforced** (a label-peeking predictor changes the implementation hash
  → fails Layer-3) not structural. Spec v8 + plan v3: `docs/superpowers/{specs,plans}/2026-06-29-v2-evidence-licensed-capability*`.
  **Deferred follow-ons:** Slice 2 (full attestation chain + certificate/SLSA `resolvedDependencies`);
  Slice 3 (defeat/drift/reinstatement/replay-over-time + tamper depth + downgraded-oracle); the ~14
  triaged Minor findings (all DEFER — coverage/cosmetic; recorded in `.superpowers/sdd/progress.md`).
- **Audit-driven cleanup + docs consolidation (2026-06-28→29).** A multi-agent tidiness/correctness
  audit (`CLEANUP_AUDIT.md`) applied as ~110 verified changes: **2 real correctness fixes** — the MDL
  meta-tier gate could be fooled by zero-structural-slot claims (a load-bearing pattern DEPRECATE
  wrongly cleared the bar), and `anchored_resolutions` emitted records in non-deterministic order
  (→ a non-deterministic signed certificate digest) — plus condensation/refactors across all packages
  (the 3 LLM adapters unified onto `_GenerationAdapterBase`; `_ndmp_gate` shared by both kernel proofs;
  `node` ring buffer → `deque(maxlen)`; serve mode-flags now mutually exclusive — argparse error vs
  silent shadowing). **Docs culled −63k lines:** shipped per-feature specs/plans + the entire
  `docs/superpowers/archive/` tree removed (history in git); `specs/`+`plans/` keep only the 2 pending
  features; the two spectral docs merged to `docs/spectral-layout.md`.
- **Capability Cell + Registry (V1, 2026-06-27, merge `b058d3c`).** First-class versioned
  `CapabilityCell` + `CapabilityRegistry`; the three reductions registered as the first cells;
  conformance is advisory (closed-world enforcement deliberately deferred).
- **Local transparency-log layer (H1.A1, 2026-06-25)** — RFC-6962 Merkle inclusion log + C2SP signed
- **Local transparency-log layer (H1.A1, 2026-06-25)** — RFC-6962 Merkle inclusion log + C2SP signed
  checkpoint + a trust-gated, offline-verifiable Polymer bundle (Sigstore-INSPIRED, not
  wire-compatible), behind a `TransparencyLog` seam. CLI `verify-bundle PATH [--pub-key]
  [--log-pub-key]` (rc 0 needs BOTH pinned keys) + `--transparency-log` on
  `certify`/`export-attestation`. **Honest boundary:** tamper-evidence + inclusion proofs + signed
  timestamps, but NOT public non-repudiation and NOT verified append-only-ness. The **networked Rekor
  backend** is DESIGNED but **intentionally tabled** (`--rekor-url` reserved + errors; spec
  `specs/2026-06-26-networked-rekor-backend-design.md`, status DEFERRED — do first-use work first).
- **Real signing (H1.A1, 2026-06-25)** — local ed25519 DSSE (`keygen`/`verify-dsse`, opt-in `--key`,
  `[sign]` extra). Real signing is no longer deferred.
- **Kernel proof (H0.1 / H0.1b, 2026-06-25)** — `verify-kernel` (synthetic, offline, CI-guarded —
  proves pipeline integrity) + `verify-kernel --real` (rebuilds `se:tcga_laml_idh@2` from 3 pinned
  inputs, byte-level `contract_checksum` parity, real n-DMP gate → `LICENSED @ REPRODUCED`; real pins
  captured + verified). **H0.1b fully closed.**
- **BioNeMo evidence-adapter (Phase 1)** — a cached NVIDIA NIM run licenses a claim offline;
  oracle-dossier bound; air-gap independence witnessed.
- **(≤2026-06-22, also current)** calibration ledger + certificate (`q` validated not asserted;
  `certify`/`calibrate`), ATTESTED ingestion (`ingest-attested`), attestation export
  (in-toto/SLSA/DRS, `--format dsse`), sheaf consistency gauge + viewer overlay, §E common-cause,
  pre-registration ledger.

**Standing caveats (carry forward — the honest limits):**
- **n-DMP / REPRODUCED is EARNED** on a real TCGA-LAML HM450 cohort (IDH-mut vs WT; e-value → ∞; IDH
  source = cBioPortal complete genotyping `tcga_laml_idh@2`, IDH-mut n=36; n_dmps=115,405). Real betas
  local-only, gitignored.
- **Region-Δβ is PENDING (FDR-withheld, NOT refuted):** held-out betting e-value 5.672 < the e-LOND
  first-test threshold 32.90 (τ fixed at 0.10 — no tuning). A comparable 2nd real cohort would license
  it at §2E REPLICATED.
- **REPLICATED is still synthetic** — earning it on real data is **data-access-gated** (no open HM450
  AML cohort exposes machine-readable IDH; the binding machinery already works).
- Python/R hash parity deferred (needs an R serializer); adapter owner/trust provenance still
  operator-authored (implementation hashes are byte-derived).

## ▶ NEXT (concrete plan)

The single remaining **critical-path** gate is **H1.A2 — source a real 2nd HM450 cohort** with
machine-readable IDH status (long lead; it's the gate to §2E REPLICATED and a shippable wedge, H2).
Optional parallel, non-blocking code: finish **H1.A1** (Sigstore/cosign/Rekor — currently tabled by
choice), the **Track B credence engines** (proper/surrogate scoring atop the ATTESTED typing), and the
**capability-cell follow-ons**: **V2.0 Slice 1 — the generalization test — SHIPPED (2026-06-29, local
`9b8848c`)**; the evidence-licensed executor route now exists (see Shipped above). Remaining: **V2.0
Slice 2** (attestation/SLSA for the evidence route) + **Slice 3** (defeat/drift/replay hardening); the
**V2.1+ menu fan-out** now that the abstraction generalized past the 3 reductions; and eventually
closed-world enforcement. **The V2.0 Slice 1 merge is LOCAL-only — `git push origin main` when ready
(main is ahead of origin/main).**
Authoritative forward plan: `docs/superpowers/2026-06-23-remaining-roadmap.md` (see *Vision-derived
additions*); product vision: `docs/superpowers/vision.md`.

Rhythm: `superpowers:brainstorming` (2–3 forks → spec → plan) →
`superpowers:subagent-driven-development` → merge `--no-ff` → update this file + memory.

---

## ⤵ Historical state snapshots

> Everything below until the **Done — checklist** is **superseded by *Current state (2026-06-26)*
> above** — retained for the dated build narrative. The `## Done`, `## Invariants`,
> `## Reference pointers`, and `## Open follow-ups` sections at the bottom remain current reference.

## Current state (2026-06-25 — transparency-log layer shipped)

> **UPDATE 2026-06-25 — H1.A1 local transparency layer shipped (`feat/transparency-log`):** a local RFC-6962 Merkle inclusion log + C2SP signed checkpoint + a trust-gated, offline-verifiable Polymer bundle (Sigstore-INSPIRED, not wire-compatible), behind a `TransparencyLog` seam. New CLI: `verify-bundle PATH [--pub-key] [--log-pub-key]` (rc 0 needs BOTH pinned keys) and `--transparency-log` on `certify`/`export-attestation`. **Honest boundary:** the local log delivers tamper-evidence, Merkle inclusion proofs, signed timestamps, and fully offline-verifiable bundles — but NOT public non-repudiation and NOT verified append-only-ness (consistency proofs are deferred). Those properties land when the NETWORKED backend ships. Still open: the networked public-Rekor backend (`--rekor-url` is reserved and errors today) and consistency proofs. The spec (`docs/superpowers/specs/2026-06-25-transparency-log-design.md`) is now marked SHIPPED (local-first) v0.3. Next open slice = networked Rekor backend + consistency proofs.

## Current state (2026-06-25)

> **UPDATE 2026-06-25 — shipped since the 2026-06-22 snapshot below (newest first), all merged to `main` and pushed (`main == origin/main`, HEAD `32670bb`):**
> - **H0.1b — real-data kernel parity gate `verify-kernel --real`** (merged `32670bb`). Rebuilds the real `se:tcga_laml_idh@2` proof from three pinned external inputs (Xena matrix; cBioPortal mutations file @ datahub commit; cBioPortal sample-list API response) via a de-hardcoded builder (`ingest/tcga_xena.py`), asserts **byte-level `contract_checksum` parity** (+ a diagnostic `canonical_checksum`) and gate-result parity vs committed pins, runs the real n-DMP gate, requires `LICENSED @ REPRODUCED`. New: `ingest/_pinned.py` (opt-in-fetch resolver), `real_kernel_proof.py` (runner), `ingest/real_kernel_pins.json` (the **real captured pins**), `scripts/bootstrap_real_kernel_pins.py` (two-mode no-self-fulfilling-parity capture). Proves the *pinned computation* reproduces — **not** data veracity (that's H1.A2). Built via subagent-driven TDD (6 tasks + whole-branch review, ruff clean, 26 feature tests green). Spec/plan: `docs/superpowers/{specs/2026-06-25-h01b-real-kernel-parity-design,plans/2026-06-25-h01b-real-kernel-parity}.md`. **Real pins captured + verified (2026-06-25):** the two-mode bootstrap ran, the new builder reproduced the trusted `@2` addresses exactly (clean diff), the real pins are committed, and `verify-kernel --real` returns **`LICENSED @ REPRODUCED`** end-to-end (n_probes=378,894; n_dmps=115,405; e-value=∞; IDH-mut n=36). **H0.1b fully closed — acceptance criterion #5 satisfied.**
> - **H0.1 — offline synthetic kernel proof `verify-kernel`** (CI-guarded `test_kernel_proof_synthetic.py`). Deterministic HM450-shaped fixture through the *real* n-DMP gate → `LICENSED @ REPRODUCED`; proves pipeline integrity offline (no real bytes). Runbook: `docs/superpowers/2026-06-23-kernel-proof-runbook.md`.
> - **H1.A1 — real DSSE signing (local ed25519)** (`feat/dsse-signing`). DSSE PAE + `keygen`/`verify-dsse` + opt-in `--key` on `certify`/`export-attestation` (`[sign]` extra). **Real signing is no longer "deferred."** Still open: Sigstore/cosign/**Rekor** transparency-log layer.
> - **BioNeMo evidence-adapter (Phase 1)** (`feat/bionemo-evidence-adapter`). Worked example where a cached NIM run licenses a claim offline; oracle-dossier bound; air-gap independence witnessed.
>
> **▶ Next:** the single remaining critical-path gate is **H1.A2 — source a real 2nd HM450 cohort** with machine-readable IDH status (long lead — the gate to §2E REPLICATED and a shippable wedge, H2). Optional parallel code: finish H1.A1 (Sigstore/Rekor) and the credence engines (Track B). (H0.1b is fully closed — real pins captured + `verify-kernel --real` verified LICENSED @ REPRODUCED.) See `docs/superpowers/2026-06-23-remaining-roadmap.md` (reconciled 2026-06-25).
>
> The 2026-06-22 snapshot below is retained for detail on everything shipped up to the calibration roadmap.

## Current state (2026-06-22)

`main` GREEN — **378 umbrella + 396 grammar + 423 protocol + 2 isolation** (1199 tests; HEAD `176544d`, pushed to origin — `main == origin/main`), ruff clean; full protocol + umbrella suites green. grammar/protocol pure + numpy-free; **Corpus = 4 collections**.

**Recently shipped (newest first):** **DEFINITIONAL bootstrap CI** (calibration roadmap **slice 5/5**; `176544d`) — a deterministic percentile bootstrap over the per-batch FDPs (umbrella-side `calibration_stats.py`, seeded — protocol stays pure) replaces the normal-approx for the headline-`q` interval when ≥2 batches; pure `definitional_batch_fdps` extracted + reused; CLI `calibrate --batches` default 12→30. **Calibration follow-up roadmap: slices 1,2,3,5 DONE; slice 4 (ATTESTED ingestion) is next** (the foundation-grounded credence layer — roadmap `.claude/plans/cozy-growing-naur.md`; **design spec WRITTEN, awaiting review+build: `docs/superpowers/specs/2026-06-22-attested-ingestion-design.md`** v0.1 — file ingester + resolvability typing + q_attested; attested-as-defeasible-corpus-claim via `source_claim_id`; resolvability = operator-declared + structural prior; scoring engines deferred). Real signing deferred. **▶ a new instance: harden the slice-4 spec through review passes, then build it (brainstorm→spec→plan→subagent rhythm).** · **q_anchored exposure-weighted hazard** (calibration roadmap **slice 3/5**; `ef69644`) — warrant survival is now exposure-aware: `ResolutionRecord.exposure_start_cycle` (the cycle the epoch was licensed; `EpochAllocator` stamps + persists it), and `_anchored_stat` reports a `hazard_rate` = failures per claim-cycle of exposure (pure, numpy-free), surfaced on the certificate. Additive — old ledgers without the clock are excluded from the hazard but still get the proportion. KM curve deferred. · **ANCHORED drift-survival → UPHELD** (calibration roadmap **slice 2/5**; `09fc821`) — `q_anchored` is now a real survival *rate*, not a failure *count*: a claim that stays LICENSED through a DRIFT re-check (examined, not in `last_drift.drifted`) records an UPHELD warrant-survival event. `observe_anchored` gains `drift_ran`; the per-`(claim,epoch)` fold collapses repeats. Deferred (clean): `superseded` (re-license-after-reopen) + red-team-survival (daemon not live in v1). · **`serve --calibration` — live calibration accrual** (calibration follow-up roadmap **slice 1/5**; `17611a0`) — the live node now records ANCHORED warrant-survival to a ledger; off by default (byte-identical). `loop`/`run-cycle` call `run_cycle` directly (no NodeRunner tick), so accrual is serve-only. Roadmap: `.claude/plans/cozy-growing-naur.md` (slices 2-5: ANCHORED survival signals → q_anchored exposure model → ATTESTED ingestion → bootstrap CI; signing deferred). · **Calibration ledger + certificate** (`q` validated not asserted — warrant-tiered DEFINITIONAL realized-FDR through the real gate / ANCHORED warrant-survival / ATTESTED stub; single-claim attestable `certify` certificate; instrument not a gate; merged `9e54684`) · Attestation DSSE export (arc 2 slice 2 — `export-attestation --format dsse`, NDJSON of unsigned DSSE envelopes) · standards-skin attestation slice 1 (`export-attestation` bundle — in-toto Statement v1 / SLSA Provenance v1 + GA4GH DRS) · Sheaf gauge live viz (one opt-in "consistency overlay" toggle: energy HUD, tension halos, animated H¹ frustration-cycle overlay, obstruction panel; new throttled `GET /consistency` route) · Sheaf consistency gauge · §E common-cause REPLICATED + Phase D slices 1+2 (2026-06-19). Details in *Recently shipped* / the Done checklist below.

**Viewer-build caveat:** `npm run typecheck` passes; the `next build` step of `scripts/check-all.sh` can fail *only* because the sandbox cannot fetch Inter/JetBrains Mono from Google Fonts at build time (a network block, not a code defect — the build passes when network is available). All pytest suites + ruff + isolation + viewer typecheck are green.

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

### ▶ NEXT — historical (2026-06-22 plan, superseded)

> **SUPERSEDED (2026-06-25) — historical.** This section reflects the 2026-06-22 plan. Since then H0.1, H0.1b, and the local-signing half of H1.A1 shipped; "real signing deferred" and the signing-as-next-move notes below are **out of date** (see the **UPDATE 2026-06-25** block at the top of this file). Current priorities: (a) run the H0.1b real-pins bootstrap; (b) H1.A2 real 2nd cohort. Authoritative forward plan: `docs/superpowers/2026-06-23-remaining-roadmap.md` (reconciled 2026-06-25).

**Recently shipped** (most recent first): **Calibration ledger + certificate — closes the
build-path critical-path proof** (2026-06-22, merged `9e54684`) — makes the corpus headline `q`
*validated, not asserted*, and emits it as a shareable certificate. Warrant-tiered ledger (pure
`protocol/calibration.py`): **DEFINITIONAL** = realized FDR (mean per-batch FDP over *mixed*
batches) by running Beta-distributed synthetic data through the **real gate** behind a scoped
contract-root contextvar — the only tier that feeds the headline `q`; **ANCHORED** = warrant
survival from the corpus's own defeat/drift events (event-identity per `license_epoch`, JSONL event
log + `EpochAllocator` + a gated byte-identical-off `NodeRunner` hook); **ATTESTED** = schema stub.
No-laundering is enforced (`feeds_headline_q` computed property; only DEFINITIONAL realized-FDR is
the headline). Certificate = in-toto/SLSA Statement **+** calibration block inside a signed DSSE
payload (`Certificate`/`build_certificate`/`certificate_dsse_envelope`; `certify`/`calibrate` CLIs;
new `[calibrate]` numpy extra). **Instrument, not a gate** — no claim status changes, Corpus stays 4;
existing `export-attestation` byte-identical. Subagent-driven 10-task TDD build, whole-branch
reviewed; check-all.sh ALL GREEN (1184 tests). Verified end-to-end: 114 licensed across 12 synthetic
batches, realized FDR 0.0000 (conservative gate). spec+plan
`docs/superpowers/{specs,plans}/2026-06-22-calibration-ledger-and-certificate*`. · **Attestation DSSE export — North-Star arc 2, slice 2**
(2026-06-21) — `--format dsse` NDJSON of unsigned DSSE envelopes (`DsseEnvelope`, `signatures: []`);
records-based refactor (`AttestationRecord` + `build_attestation_records`; bundle output byte-identical,
captured golden); `build_attestation_statements` projection; public API extended (`AttestationRecord`,
`build_attestation_records`, `build_attestation_statements`, `DsseEnvelope`, `DsseSignature`, `dsse_envelope`);
stdlib-only/deterministic/additive. Deferred: real signing (Sigstore/Rekor/DSSE PAE) = slice 3.
spec+plan `docs/superpowers/{specs,plans}/2026-06-21-attestation-dsse-export*`. · **Standards-skin attestation export — North-Star arc 2, slice 1**
(2026-06-21) — `export-attestation <corpus>` emits one deterministic **in-toto Statement v1 / SLSA Provenance
v1** attestation per LICENSED claim **+ GA4GH DRS** object docs, built from the content-address we already
compute (`dimnames_hash`/`profile_hash`/`semantic_run_id`) with the air-gap credential pair as the SLSA
`builderDependencies` (the recompute gate = the trusted builder; independence = its security guarantee). Pure
umbrella module `src/polymer_claims/attestation.py` (typed frozen DTOs + builder) + IO-only
`resolve_contract_index`; stdlib-only, no signing/network/clock; additive/byte-identical when off. The
recompute gate re-expressed as the GA4GH/in-toto/SLSA trust fabric (north-star §4 seam #3). spec+plan
`docs/superpowers/{specs,plans}/2026-06-21-standards-skin-attestation*`. Deferred (later slices):
signing/DSSE/Sigstore/Rekor, `--format ndjson` direct-verifier export, publishing the recompute-gate
build-type/security-model doc at the `builder.id` URI, WES/TRS/RO-Crate, FAIR Signposting, Refget SeqCol. ·
**Sheaf gauge live viz** (2026-06-21) — one opt-in "consistency overlay" toggle: falling energy HUD + sparkline, per-claim tension halos, animated H¹ frustration-cycle overlay, obstruction panel; new throttled `GET /consistency` route; backend corrections P1 energy-only per-frame headline (`ConsistencyHeadline.spectral_gap` now `float | None`) + P3 nonnegative edge-share `per_claim_tension`. spec+plan `docs/superpowers/{specs,plans}/2026-06-21-sheaf-viewer-viz*`. · **Sheaf consistency gauge** (2026-06-21) — cellular sheaf over the
claims graph; inconsistency energy (consistency radius) + dim H⁰ + localized H¹ frustration obstructions;
`export-consistency` CLI + cheap live headline on the topology frame; instrument not a gate; pure protocol
extractor + numpy spectrum behind `[embed]`. spec+plan `docs/superpowers/{specs,plans}/2026-06-21-sheaf-consistency-gauge*`.
Deferred: stalk enrichments (standardized-effect, ℝ²(value,uncertainty)), unit-conversion registry (ρ≠1),
rich viewer obstruction viz, instrument→gate. · **§E common-cause — earn REPLICATED on low shared-cause overlap:
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
manifest** so sex-chrom QC bites + a real platform `profile_hash`; (c) **north-star arc-2 standards skin** (in-toto/SLSA/DRS attestation — the safe first slice of arc 2) or **Phase B** (autonomous `MethylGenerationAdapter`, `docs/superpowers/2026-06-16-autonomous-hypothesis-loop.md`) — both non-blocked; with the sheaf gauge opening arc-3 and arc-1 epistemic core substantially done, arc-2 is now the more natural next candidate. [IDH-source swap (a fuller IDH cohort) —
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
2026-06-19**; Phase D slices 1+2 and §E common-cause independence all shipped 2026-06-19; current non-blocked candidates are the north-star **arc-2 standards skin** or **Phase B** (autonomous hypothesizer).

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

Other safe slices:

1. **§2E follow-ups** — viewer tier display + live-node `replication_map` wiring are done. Remaining:
   bind a **real** second cohort when available so REPLICATED is earned, not only exercised.
2. **n-DMPs as a REPLICATED second reduction** — run the n-DMP count on a second cohort and multiply the
   two count-enrichment e-values (combines §2E's REPLICATED machinery with the new reduction). ~1 slice.
3. **ROBUSTLY_BLAMED wiring** — wire the Duhem robust-blame REJECTED verdict into the protocol and stamp
   it (tiny; the enum value is reserved). Optional/legibility.

**Deferred / blocked-on-external (supervised):** Python/R hash parity (needs the R side);
arc-2 slice 3 — real signing (Sigstore/cosign/Rekor + the DSSE PAE) on top of the shipped unsigned DSSE export — deferred (no external service/keys yet). Literal per-attack e-value
combination is **largely a mirage** — Phase 2.2 already caught its sound core; don't build a generic
combination.

**Candidate next moves:** With the **certificate shipped (2026-06-22)**, the build-path critical-path proof is *closed* — a real claim, a real independence check, a validated (not asserted) `q`, emitted as a shareable certificate. The natural next is build-path **step 4 — one legible wedge claim**: the **Linchpin Layer C Variant Adjudication Engine** (untouched, highest-leverage demonstrable artifact) or the AML epistemic twin. **Calibration follow-ups (non-blocking):** ATTESTED ingestion (no external source yet); an exposure-weighted hazard model for `q_anchored`; a real-claim `q`-calibration *resolution* loop (DEFINITIONAL is validated on a synthetic generating model — a disclosed assumption). Also open: arc-2 slice 3 (real signing — Sigstore/cosign/Rekor/DSSE PAE, now atop both the unsigned DSSE attestation export *and* the certificate); arc-3 deepening (hyperbolic/Lorentz layout, instrument→gate). Real-2nd-cohort §2E REPLICATED stays data-blocked (needs a real `idh_status.tsv`).

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

**External audit — CLOSED:**
- ✅ Tier A+B (`c662f1c`): bounded frame retention · tick-serialization lock · bounded SSE queues ·
  non-loopback bind guard · machine-clean JSON · `ARCHITECTURE_CURRENT.md` + `GLOSSARY.md` · v1.2 frozen
  banners
- ✅ Adapter trust registry (`67f98e3`) — the independence gate (registry core done); **byte-hash hardening DONE (`d3be2bb`, 2026-06-20)** — `implementation_hash` byte-derived from adapter bytecode, `Satisfaction` records the credential-witness pair. Residual: registry owner/trust metadata remains operator-authored (roadmap 1c).
- ✅ Tier-C (`2b7ccb5`): viewer `CONTRACT_VERSION` + 6-axis strength validator · `run_cycle` output
  revalidation · packaging metadata

**Credibility arc + CES:**
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
- ✅ **Sheaf consistency gauge** (2026-06-21) — cellular sheaf over the claims graph; scalar-ℝ stalks on
  Quantity-leaf claims; equivalence edges = agreement, defeat edges = sign-flipped antagonism (generalizing
  the signed-Laplacian embedding); Laplacian → inconsistency energy (consistency radius) + dim H⁰ + localized
  H¹ frustration obstructions; `export-consistency` CLI + cheap live headline (`TopologyExport.consistency`)
  on the topology frame; instrument not a gate *(at the time — H¹ frustration was later wired to act via the
  **duhem consistency fold**, 2026-07-07; see the current-state snapshot at the top)*; pure protocol extractor (`protocol/sheaf.py`) + numpy spectrum
  (`polymer_claims/sheaf_spectrum.py`) behind `[embed]`. spec+plan
  `docs/superpowers/{specs,plans}/2026-06-21-sheaf-consistency-gauge*`. **Deferred:** stalk enrichments
  (standardized-effect, ℝ²(value,uncertainty)), unit-conversion registry (ρ≠1),
  instrument→gate.
- ✅ **Sheaf gauge live viz** (2026-06-21) — the viewer renders the gauge behind one opt-in "consistency
  overlay" toggle: falling energy HUD + sparkline, per-claim tension halos, animated H¹ frustration-cycle
  overlay, obstruction panel (click-to-focus) + node-tension display. New throttled `GET /consistency` route
  (snapshot-then-release, never blocks ticks). Gauge corrections landed first: **P1** per-frame headline is
  energy-only (`ConsistencyHeadline.spectral_gap` now `float|None`, no per-tick eigendecomposition); **P3**
  `per_claim_tension` is a nonnegative edge-share attribution (valid as opacity). Off ⇒ rendered view
  unchanged; `[embed]`-absent ⇒ degrades silently. Demo: `data/demo/frustrated_cycle_corpus.json` →
  exactly one H¹ obstruction. spec+plan `docs/superpowers/{specs,plans}/2026-06-21-sheaf-viewer-viz*`.
  **Deferred** (spec §10): rich layer in sample mode, λ₂-on-frame (Lanczos), tension in protocol export,
  hyperbolic/Lorentz layout, instrument→gate.
- ✅ **Adapter-independence hardening** (`d3be2bb`, 2026-06-20) — byte-derived `implementation_hash` from adapter bytecode; licensed `Satisfaction` records the credential-witness pair that justified the air gap; §E `shared_cause_factors` activated on bundled SE-Contracts.
- ✅ **Standards-skin attestation export — arc 2, slice 1** (2026-06-21) — `export-attestation <corpus>` → deterministic in-toto Statement v1 / SLSA Provenance v1 + GA4GH DRS per LICENSED claim; keyed by existing content-addresses (`dimnames_hash`/`profile_hash`/`semantic_run_id`); air-gap credential pair = SLSA `builderDependencies`; pure umbrella module `attestation.py`; stdlib-only, no signing/network; additive/byte-identical off; 31 attestation tests. spec+plan `docs/superpowers/{specs,plans}/2026-06-21-standards-skin-attestation*`.
- ✅ **Attestation DSSE export — arc 2, slice 2** (2026-06-21) — `--format dsse` NDJSON of unsigned DSSE envelopes (`DsseEnvelope`, `signatures: []`); records-based refactor (`AttestationRecord` + `build_attestation_records`; bundle byte-identical, captured golden); `build_attestation_statements` projection; six new public names exported (`AttestationRecord`, `build_attestation_records`, `build_attestation_statements`, `DsseEnvelope`, `DsseSignature`, `dsse_envelope`); stdlib-only/deterministic/additive; umbrella test count → 327. Deferred: real signing (Sigstore/Rekor/DSSE PAE) = slice 3. spec+plan `docs/superpowers/{specs,plans}/2026-06-21-attestation-dsse-export*`.
- ✅ **Calibration ledger + certificate** (2026-06-22, merged `9e54684`) — `q` *validated, not asserted*, closing the build-path critical-path proof's last open piece. Warrant-tiered ledger (pure `protocol/calibration.py` — `ResolutionRecord`/`CalibrationLedger`/`calibration_summary`/`anchored_resolutions`): **DEFINITIONAL** realized FDR (mean per-batch FDP over mixed batches) by driving Beta-distributed synthetic data through the **real gate** (betting e-value + air-gap + e-LOND, reached via a scoped contract-root contextvar in `contracts/__init__.py`); **ANCHORED** warrant survival from defeat/drift events (event-identity per `license_epoch`); **ATTESTED** stub. No-laundering: `feeds_headline_q` computed property, only DEFINITIONAL realized-FDR is the headline. Impure umbrella: `calibration_harness.py` (`[calibrate]` numpy extra), `calibration_store.py` (JSONL event log + `EpochAllocator` + ANCHORED tap), gated `NodeRunner` `calibration_path` hook (byte-identical off). Certificate: `attestation.py` `Certificate`/`build_certificate`/`certificate_dsse_envelope` (Statement + calibration block in the signed DSSE payload) + `certify`/`calibrate` CLIs; `export-attestation` byte-identical. Instrument, not a gate; Corpus stays 4. Subagent-driven 10-task TDD build (whole-branch reviewed; one mid-build regression — the contextvar default capturing `_DIR` at import — caught+fixed). check-all.sh ALL GREEN (1184 tests). Deferred: ATTESTED ingestion, `q_anchored` hazard model, real signing. spec+plan `docs/superpowers/{specs,plans}/2026-06-22-calibration-ledger-and-certificate*`.

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

- **Product vision:** `docs/superpowers/vision.md` (external-facing thesis — capability-cell spine, three registries, closed-world agent execution, verification ladder; reconciled to current state 2026-06-27).
- **Forward roadmap:** `docs/superpowers/2026-06-23-remaining-roadmap.md` (authoritative) · `docs/superpowers/2026-06-16-linchpin-thesis-three-layer-arc.md` (the three-arc linchpin vision)
- **Parameterization-seam research program (the neurosymbolic frontier — IR leaves layer):** `docs/open-questions-research-plan.typ` — the open questions at the symbolic-type-system↔neural-judgment seam (strength axes, causal roles, ontology grounding, leaf-types, neurosymbolic caging) stated as a *falsifiable program* (metric + first study per seam). Its Group-B1 conceptual-independence is backlog item ② *independence-as-claim*; companion to `foundations/measurement-foundation.md`. *(Source `.typ` tracked; `.pdf` is a gitignored build artifact — `typst compile` to render.)*
- **Phase-2 north star:** `docs/superpowers/2026-06-12-phase-2-north-star.md`
- **Architecture map:** `ARCHITECTURE_CURRENT.md` · **Glossary:** `GLOSSARY.md`
- **Spectral layout guide:** `docs/spectral-layout.md` (usage + eigenmap/Procrustes math)
- **Memory:** `project_polymer_claims_knowledge_protocol` (full phase history + follow-ups)
- **Deep design source:**
  `~/Desktop/Research/topics/epistemic-claim-foundations/generative-protocol/_FINAL_knowledge_generation_protocol.md`
- **Foundations (framing):** `docs/superpowers/foundations/MAP.md` (one-page shape) · `docs/superpowers/foundations/epistemology.md` (why the gate isn't circular) · `docs/superpowers/foundations/scaled-infrastructure.md` (unicorn-scale sketch).

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
