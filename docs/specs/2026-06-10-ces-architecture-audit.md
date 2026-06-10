# CES Architecture Audit — where bioinformatic context lives, and the gap to close

**Status:** Architecture findings (input to the next-phase design). Not a design itself.
**Date:** 2026-06-10
**Scope:** the two repos the Claim Evidence Socket (CES) must bind —
Polymer EOS (`~/Desktop/polymer-claims/`) and Polymer Genomics (`~/Desktop/Polymer/`) —
plus the real in-practice TET2 methylation pipeline (`~/Desktop/TET2/`) as ground truth.
**Why this exists:** before building the CES, we paused to answer one question — *what
tool-specific bioinformatic context (normalization, filtering, design, covariates,
multiple-testing) must a claim capture for a license to be scientifically meaningful, and
where should it live?* Three read-only audits answer it.

---

## 0. The one-paragraph finding

A real differential-methylation result is meaningless without ~15 pinned analytical
choices (normalization, probe filtering, array/genome, design formula + covariates,
DMP/DMR method + thresholds, cell-type adjustment, reproducibility seeds). Polymer
Genomics captures *most* of them — but in **three different layers** with **incomplete
content-addressing**: some live in the SE Contract, some in the Boris tool params (these
get hashed into the SemanticRunID), and a load-bearing residue is **hardcoded in R and
escapes the hash entirely**. Meanwhile the EOS claim side has **no typed home for any of
it** — `OperationNode.params` is a flat `tuple[(str,str)]` bag, `DataHandle.ref` is a bare
string, and `MaterializationContext` records only `api_version`/`data_version`. So the CES
cannot just "wire B1+B2": it must first decide **where the pinned analytical context lives
and how it is content-addressed**, or every license silently inherits the gap.

---

## 1. EOS side — the claim's plan IR is parameter-thin (anchors)

| Type | File:line | Shape | Verdict |
|---|---|---|---|
| `OperationNode.params` | `grammar/src/polymer_grammar/operations.py:78–85` | `tuple[tuple[str, str], ...]` | **Flat, untyped, string-only.** No nesting, no schema, no validation. Adapters parse ad-hoc. |
| `DataHandle` | `operations.py:32–37` | `ref: str` + optional `expected_dimension` | Bare reference string (CES-compliant thin). No schema, no access methods, no version. |
| `ProducedLeafSpec` / `Leaf` | `operations.py:50–75`, `leaf.py:30–77` | scalar `leaf_kind` only | **No vector/array output.** A DMP's 850K betas/p-values must collapse to one scalar (e.g. "n significant probes", "Δβ at cgX"). |
| `MaterializationContext` | `licensing.py:28–32` | `id, api_version, data_version, note` | **No tool config, no preprocessing provenance, no semantic-run id.** Pure audit metadata. |
| `OperationNode.impl` | `operations.py:79` | bare `str` (e.g. `"stats::mean_diff"`) | **Unversioned.** Two adapters can run different code under one impl key. |
| Oracle / `ValidationTier` | grammar `oracle.py:22–121`, protocol `oracle.py:45–81` | tier ceiling caps empirical strength axes | **Parameter-blind.** Caps by validation lineage; knows nothing of *which params* the tool ran with. |

Closest existing analog: the Phase-2a `stats::mean_diff` adapter
(`src/polymer_claims/exec_adapters.py:63–110`) reads four string params
(`value_col/group_col/group_a/group_b`) — that is the ceiling of what the plan IR can
express today.

**EOS gap:** normalization method, design formula, covariate list, filtering thresholds,
array type, batch correction, multiple-testing procedure — **none has a typed home**; all
would degrade to flat strings parsed inside an adapter, with no validation and no
content-address of their own.

---

## 2. Polymer Genomics side — most context captured, in three layers, hashed incompletely

**Layer A — SE Contract** (`Backend/app/models/se_contract.py`, `shared/core/se_contract.json`):
records `assays[]` (beta/M), `col_data[]` (group/batch/condition), `row_data[]`,
`dimnames_hash` (SHA256 of `feature_ids|sample_ids`), `metadata` (genome_assembly,
bioc/r_version, lockfile_summary). **Critically: assays are OPAQUE — the base schema does
NOT record the normalization method, filtering rules, or batch correction already applied.**
An optional `extensions.provenance` (lineage_depth, trace_ids) exists but is rarely used and
does not encode method specifics. `data_type_info.suggested_preprocessing` is advisory, not a
record of what was done.

**Layer B — Boris tool params** (`shared/core/tool_registry.json`, `methylation.analyze_full`
@ ~612–800): RICH explicit param schema — `normalization` enum (funnorm/quantile/noob/ssnoob),
`detection_threshold`, `filter_snps/filter_sex/filter_crossreactive`, `fdr_threshold`,
`dmr_lambda/C/min_cpgs`, `adjust_cell_composition`. Notably carries a `clinical_mode.locked_params`
list — an existing notion of "which params must be pinned for clinical validity." **These params
ARE hashed** into the SemanticRunID.

**Layer C — hardcoded R internals** (`R-Engine/R/analysis/methylation/pipeline.R`,
`helpers.R`): `analysis_profile` (selects sesame-vs-minfi QC), `sesame_prep="QCDPB"`,
`use_any_sample_rule=TRUE`, `fail_fast`, `cell_reference="FlowSorted.Blood.EPIC"`, and the
**limma design formula itself (assumed `~ group`)**. **These are NOT tool params and NOT
hashed.**

**The content-address:** `SemanticRunID = SHA256(tool | param_signature | input_signature)`
(`Backend/app/models/workflow_memory.py:62–117`), where `param_signature =
SHA256(canonical params JSON)` and `input_signature = SHA256(sorted input dimnames_hashes)`.
**It captures Layer B + the dataset identity, but misses Layer C and the SE Contract's
preprocessing history.** So two runs with the same SemanticRunID can diverge if an R default
changes — and the design formula / cell reference are invisible to it.

**The `analysis_profile` concept** (e.g. `canonical_epicv2_hg38_v1` in `helpers.R:563–570`)
is the most important latent asset: it is a *named, versioned bundle of pinned choices*
(normalization=sesame/QCDPB, detection=0.05, filter_sex=TRUE, cross_reactive=Peters2024_WGBS,
…). It is exactly the right unit for a claim to reference — but today the profile selection is
itself a Layer-C internal that the SemanticRunID does not fully capture.

---

## 3. Ground truth — what the real TET2 pipeline actually pins

From `~/Desktop/TET2/analysis/early_rscript_pipeline/`. This is the reference for "what a
real claim must capture," and it diverges from the registry defaults — proving the point that
context must be named, not assumed:

- **Normalization:** sesame `openSesame(prep="QCDPB")` — *not* the registry default `funnorm`.
- **Detection:** 0.80 retain-rule (TET2) — *not* the canonical 0.05.
- **Cross-reactive:** Peters2024 WGBS set, **11,878 probes**, from the live cross-project file
  `~/Desktop/Polymer/R-Engine/data/cross_reactive_epicv2_wgbs.txt` (the global-config-flagged
  dependency).
- **SNP:** sesame `M_SNPcommon_1pt`; **Sex chrom:** filtered (TET2 script) — registry default
  is FALSE.
- **Array/genome:** EPICv2 / hg38; replicate probes collapsed by mean.
- **Design:** `~ 0 + Sample_Group + Age + Sex`, contrast `TET2_mut − WT`; **no batch
  correction, no cell adjustment** in the main model.
- **DMP:** limma on M-values, clamp `[1e-6, 1−1e-6]`, BH, FDR 0.05.
- **High-risk implicit choices** (silently lost by any naive capture): BH adjust-method,
  M-value clamp bounds, contrast *direction* (factor-level order), `topTable` sort order,
  replicate-collapse method, infinite-M handling.

The canonical-profile and the real-manuscript-pipeline **disagree on detection threshold,
sex filtering, and normalization prep** — so "which profile" is a real, claim-level question,
not a default.

---

## 4. Synthesis — the real shape of the next phase

The CES spec's "highest-leverage first step" (B1 + minimal B2, one claim licenses) is sound,
but the audit shows a **prerequisite design decision sits in front of it**: *what is the
content-addressed unit of analytical context that a claim binds to, such that "licensed" means
"this exact analysis, fully pinned, beat the criterion"?*

Three layers of context exist; the SemanticRunID covers ~⅔ of them. The choice is **where the
missing pinning lives and how the claim references it**. That is the genuine fork to settle
before any plumbing — see §5.

Two facts constrain the answer:
1. **The "thin handle" law** (no bulk bytes, small handles only) argues against re-encoding 15
   params inside the EOS grammar.
2. **The oracle/ValidationTier seam already exists** to treat an *apparatus* as the thing whose
   validation lineage caps a claim's strength — and a *versioned analysis profile* is exactly
   an apparatus.

---

## 5. The decision the next phase must make (forks, with a recommendation)

**Fork A — where the pinned bioinformatic context lives (core architecture):**

- **(A1) Profile-reference model — RECOMMENDED.** Promote Polymer's `analysis_profile` to a
  first-class, versioned, **content-addressed `AnalysisProfile`** that pins *all* layers
  (incl. the Layer-C internals and the design formula). A claim's plan references it by
  `profile_id@version` (+ hash); the profile *is* the apparatus → its `ValidationTier` caps
  strength; the SemanticRunID is extended to hash the profile so the content-address is
  complete. EOS stays thin (handle + impl + profile-ref + criterion); the heavy param schema
  stays on the Polymer side where it already lives. Licensing means "tool T under pinned
  profile P over dataset D beat θ."
- **(A2) Rich-params-in-EOS.** Add a typed `AnalysisConfig` object to the EOS plan IR
  (normalization enum, design formula, covariates, filtering struct). Self-contained and
  portable, but duplicates the Boris schema, bloats the grammar, and fights the thin-handle law.
- **(A3) Opaque-SemanticRunID.** Claim references only a SemanticRunID; params are wholly
  Polymer's concern. Minimal EOS change, least legible from the claims side, and **inherits the
  Layer-C hash gap silently** — the worst for auditability.

**Fork B — close the SemanticRunID completeness gap (prerequisite either way):** the Layer-C
internals (analysis_profile, sesame_prep, design_formula, cell_reference) must become part of
the hashed identity. Recommendation: fold them into the `AnalysisProfile` (Fork A1) so the
profile hash pins everything by construction, rather than chasing individual params into the
param bag.

**Fork C — vector outputs:** a DMP is intrinsically vector-valued. Decide per-claim whether the
terminal leaf is a scalar reduction ("n DMPs at FDR<0.05", "Δβ at cgX") — buildable today — or
whether EOS needs a `QuantityVectorLeaf` (a real grammar expansion). Recommendation: **scalar
reduction for the first slice**, defer vector leaves to a later phase.

**Working defaults already chosen (survive the audit):** local-first seam (build in
polymer-claims with a local SE-Contract realizer, no live R-Engine in tests); methodological
independence as the air-gap default (two different tools, same pinned profile + dataset).

---

## 6. Recommended phase decomposition

1. **Phase CES-0 (design) — `AnalysisProfile` as the content-addressed apparatus.** Define the
   versioned profile object (pins all three layers + design formula), its hash, its mapping to
   `OracleDossier`/`ValidationTier`, and the extended `MaterializationContext`
   (semantic_run_id + profile_hash + dimnames_hash). *This is the spec to write next.*
2. **Phase CES-1 (B1) — DataHandle → SE-Contract ref**, DRS-shaped, `dimnames_hash` canonical.
   Local realizer (read a bundled methylation SE Contract), no live API.
3. **Phase CES-2 (minimal B2) — one tool, one profile, one claim licenses.** A local
   `BorisLikeAdapter` computing one scalar reduction (e.g. region Δβ or n-DMPs) under a pinned
   profile, with a methodologically-independent second leg, over one public EPICv2 SE Contract.
4. **Phase CES-3 (B3 + drift + tier) — wire SemanticRunID into materialization, the profile
   hash into the drift key, and the substrate→tier cap.** (Much already exists on one side.)
5. **(later) live R-Engine `BorisExecutionAdapter` via PlumberClient; vector leaves; the §7
   public/private promotion ruling.**

The CES spec's open governance ruling (private-evidence-proposes / public-data-licenses) and
the DRS-shape-vs-endpoint and TileDB-SOMA decisions remain user-gated and do **not** block
Phases CES-0→2.

---

## 7. Anchored file map (for the next implementer)

**EOS:** `grammar/src/polymer_grammar/{operations.py,leaf.py,licensing.py,oracle.py,evaluate.py}`;
`protocol/src/polymer_protocol/oracle.py`; `src/polymer_claims/{exec_adapters.py,datasets/,llm_adapter.py}`.
**Polymer Genomics:** `Backend/app/models/{se_contract.py,workflow_memory.py}`;
`shared/core/{se_contract.json,tool_registry.json}`;
`Backend/app/services/{plumber_client.py,workflow_memory_service.py}`;
`R-Engine/R/analysis/methylation/{pipeline.R,helpers.R,methylation.R,methylation_sesame.R}`;
`BACKEND_STRUCTURE.md`.
**Ground truth:** `~/Desktop/TET2/analysis/early_rscript_pipeline/{00_config.R,01_ingestion_qc.R,02_dmp_analysis.R}`;
`~/Desktop/Polymer/R-Engine/data/cross_reactive_epicv2_wgbs.txt`.
