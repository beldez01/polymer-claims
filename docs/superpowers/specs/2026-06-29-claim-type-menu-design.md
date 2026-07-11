# Claim-Type Menu — the first slate of validatable science

**Date:** 2026-06-29
**Status:** Horizon / conceptual outline. **Not scheduled for implementation.** This document
exists to (a) put a concrete build target on the roadmap, and (b) bring the abstract
"epistemic operating system" pitch down to earth with real, recognizable examples.

---

## Why this document exists

The platform's idea — a machine that generates, tests, and licenses scientific claims — is
beautiful but abstract. The first thing anyone asks when you explain it is: *"like what? give me
an example."* This menu is the answer. Each row is a kind of scientific claim the system can
actually validate end-to-end, paired with the real tools that validate it and a real dataset it
runs on. It turns "epistemic OS" into "here are twelve concrete things it does."

It is also a roadmap: the ranked, gated list of claim types we intend to build evidence adapters
for, in roughly the order that makes sense.

---

## Terminology (load-bearing)

A "claim type we know how to validate" is a **bundle of three** distinct things in this system:

| Concept | What it is | The term |
|---|---|---|
| The **shape** of a claim | "X differs from Y, adjusting for confounders" | a **pattern** (grammar-level type, e.g. `adjusted_effect`) |
| The **pipeline** that computes/validates it | code that hits real data and returns a value | an **evidence adapter** (external/third-party ones; internal ones are "execution adapters") |
| The **trust authority** behind it | the apparatus + its validation tier | an **oracle** (with an oracle *dossier*) |

So an item on this menu is precisely:

> **a `pattern`  +  a *pair* of independent evidence adapters  +  an oracle dossier**

The *pair* is non-negotiable. Because of the air-gap rule (no self-licensing), a claim type is
not validatable until **two independently-owned** evidence adapters exist for it. One pipeline,
however good, can never license a claim by itself.

---

## The air-gap gate and independence tiers

A claim type qualifies for the menu only if it clears the **gate**: two evidence adapters of
independence **Tier 2 or better** exist. Much of our computation is grounded in the
**Bioconductor** ecosystem, so the two legs are often two R packages — which raises a real
question about how independent they actually are. We answer it by *tiering* independence and
letting the strength cap follow:

| Tier | Definition | Example | Strength consequence |
|---|---|---|---|
| **T1 — cross-runtime** | ≥1 leg lives outside the R/Bioconductor runtime (a Python tool or an external API) | AlphaFold (DeepMind) vs ESMFold (Meta); DESeq2 (R) vs PyDESeq2 (Python) | full empirical strength |
| **T2 — cross-team, same-runtime** | two Bioconductor/R packages, different author teams, different methods, one R interpreter | DESeq2 (Huber lab) vs edgeR (Smyth lab) | **capped** — shared-runtime correlated-failure discount |
| **T3 — same-team / same-method** | not independent; excluded | DESeq2 vs DESeq2 with different params | cannot license |

The **oracle dossier records the tier**, and the existing oracle-tier → strength-cap mechanism
applies the consequence automatically. A T2-licensed RNA-seq claim is honestly weaker than a
T1-licensed variant-effect claim, and the system encodes that rather than just noting it.

### Scoring (applied only after the gate passes)

Each qualifying claim type is scored 1–5 on three axes:

- **Impact** — would working scientists care (disease mechanism, clinical/causal weight)?
- **Data readiness** — is there a clean public dataset to ingest *now* (TCGA / GEO / GTEx / PDB)
  vs access-gated (UK Biobank) or synthetic-only?
- **Demo** — how compelling does conjecture → licensed look live in the viewer?

Rows are then bucketed into **Tier 1 (ship-now) / Tier 2 (near-term) / Tier 3 (aspirational)**.

---

## The menu

Independence tier in brackets. Substrate: **B** = Bioconductor-native · **X** = external API ·
**R+Py** = cross-runtime (R + Python).

### Tier 1 — ship-now (real pair + ready public data + high value)

| Claim type | Pattern | Independent pair | Data | I / D / Demo | Substrate |
|---|---|---|---|---|---|
| **RNA-seq differential expression** | `adjusted_effect` | DESeq2 vs edgeR **[T2]** → upgradable to DESeq2 vs PyDESeq2 **[T1]** | TCGA / GTEx / recount3 | 5 / 5 / 3 | B |
| **DNA methylation DMP/DMR** *(anchor — partly built)* | `adjusted_effect` | minfi/limma vs methylKit **[T2]** | GEO GSE86409 *(have it)*, TCGA | 4 / 5 / 3 | B |
| **Variant effect / pathogenicity** | `existence` / categorical score | AlphaMissense (DeepMind) vs ESM1v (Meta) **[T1]** | ClinVar + gnomAD | 5 / 4 / 4 | X |
| **Survival / outcome association** | `adjusted_effect` (hazard) | survival (R) vs lifelines (Py) **[T1]** | TCGA clinical *(have LAML)* | 5 / 5 / 3 | R+Py |

### Tier 2 — near-term (pair exists; heavier pipeline or gated data)

| Claim type | Pattern | Independent pair | Data | I / D / Demo | Substrate |
|---|---|---|---|---|---|
| **Protein structure prediction** *(top demo)* | `quantity` / `existence` ("mutation destabilizes fold", ΔpLDDT) | AlphaFold vs ESMFold **[T1]** | PDB / UniProt | 4 / 4 / **5** | X |
| **Single-cell DE / markers** | `adjusted_effect` | Seurat (R) vs Scanpy (Py) **[T1]** | Tabula Sapiens / HCA | 4 / 4 / 4 | R+Py |
| **Protein–ligand docking / affinity** | `quantity` / `dose_response` | AutoDock Vina vs DiffDock **[T1]** | PDBbind / BindingDB | 4 / 4 / **5** | X |
| **GWAS / genetic association** | `adjusted_effect` | PLINK vs SAIGE / REGENIE **[T1/T2]** | 1000G + GWAS Catalog ready; **UK Biobank gated** | 5 / 3 / 3 | X |

### Tier 3 — aspirational / derivative

| Claim type | Pattern | Independent pair | Data | I / D / Demo |
|---|---|---|---|---|
| **eQTL mapping** | `adjusted_effect` | Matrix-eQTL vs tensorQTL **[T1/T2]** | GTEx | 4 / 4 / 3 |
| **Gene-set / pathway enrichment** *(derivative — consumes an upstream DE claim)* | `existence` / enrichment | fgsea vs clusterProfiler vs GSEA **[T2]** | DE output + MSigDB | 3 / 5 / 3 |
| **Drug dose-response / IC50** | `dose_response` | drc (R) vs Python 4-param logistic **[T1]** | DepMap / GDSC | 4 / 4 / 4 |
| **Copy-number alteration association** | `adjusted_effect` / `existence` | GISTIC vs CNVkit **[T1]** | TCGA | 3 / 4 / 3 |

**Notes:**
- **Methylation is the anchor** — the one row already partly built, so it is the reference
  implementation every other Bioconductor row copies.
- **The external-API rows (variant, structure, docking) are the strongest independence stories**
  (T1, different corporate owners) *and* the best demos — but they are a different substrate from
  the Bioconductor cluster, so they form a parallel track, not a continuation of it.

---

## The reuse lens — why this is cheaper than 12 separate efforts

One pattern dominates. **`adjusted_effect` is the workhorse**: it covers **7 of the 12 rows**.
Those rows differ only in *which two adapters* run and *which dataset* feeds them — the claim
shape and the SE-contract bridge are shared.

| Pattern family | Rows it unlocks | Build implication |
|---|---|---|
| **`adjusted_effect`** | RNA-seq DE · methylation · survival · single-cell · GWAS · eQTL · CNV (7) | Build the substrate **once**; each new row = wire 2 adapters |
| **`existence` / categorical** | variant effect · enrichment (2) | Second substrate, external models |
| **`quantity`** | structure prediction · docking affinity (2) | External APIs, best demos |
| **`dose_response`** | docking · drug IC50 (2) | Smallest family |

### Horizon build-order (natural order, not a commitment)

- **Wave 0 (anchor, partly built):** methylation `adjusted_effect`
- **Wave 1:** reuse that exact substrate → RNA-seq DE + survival (cheap: only adapters change)
- **Wave 2:** external-API family → variant effect + structure (new substrate, strongest
  independence + best demo)
- **Wave 3:** single-cell, GWAS, docking → then the Tier 3 derivatives

---

## Down to earth — worked examples

This is what each row *becomes* for the person who asks for an example.

> **RNA-seq differential expression.**
> *"In TCGA-LAML, FLT3 is over-expressed in FLT3-ITD-mutant patients vs wild-type, adjusting for
> age and sex."*
> DESeq2 and edgeR each compute the log₂ fold-change + significance on the same count matrix. The
> claim licenses **only if both agree** within tolerance. If DESeq2 says up and edgeR says flat,
> it stays PENDING — the system has caught a method-dependent result before you believed it.

> **Variant effect / pathogenicity.**
> *"The BRCA1 missense variant p.R1699Q is pathogenic."*
> AlphaMissense (DeepMind) and ESM1v (Meta) each score the variant independently. The categorical
> "pathogenic" licenses only if both cross threshold and agree — two unrelated models from two
> companies, no shared code. Strongest independence tier (T1).

> **Survival / outcome association.**
> *"In TCGA-LAML, high BAALC expression predicts worse overall survival, adjusting for age."*
> A Cox proportional-hazards fit via R's `survival` and Python's `lifelines` each compute the
> hazard ratio; the claim licenses if they agree. Cross-runtime (R + Python), so it can earn full
> empirical strength.

> **DNA methylation DMP/DMR (the anchor).**
> *"CpG island near GENE is hypermethylated in IDH-mutant AML vs wild-type."*
> minfi/limma and methylKit each compute the region Δβ + significance on the same array data;
> licenses on agreement. T2 (both Bioconductor), so honestly strength-capped — and the system
> says so.

(Tier 2/3 rows get a one-line example in the same spirit when their wave comes up.)

---

## Open questions / caveats (for when this leaves the horizon)

- **T2 strength-cap calibration.** We've decided same-runtime pairs are capped; the *magnitude*
  of the discount is unset. The deeper problem — that organizational independence (T1/T2) is not
  the same as *epistemic* independence (two "independent" tools can share priors and fail together)
  — and a concrete, empirical way to measure it (an error-correlation "decorrelation battery" that
  replaces the hand-set discount with an effective-witness count) are worked out in the companion
  note: [`2026-06-29-adapter-independence-hardening-notes.md`](2026-06-29-adapter-independence-hardening-notes.md).
- **R-side hash parity.** The bytecode-derived `implementation_hash` that enforces "different code
  lineage" is defined for Python adapters. The R/Bioconductor leg needs an equivalent under the
  SE-contract / hash-parity path (see the `debug-int` integration surface).
- **Owner assertion honesty.** `owner` is operator-asserted. For two Bioconductor packages we
  assert lab-level owners (Huber vs Smyth) — defensible, but we should document the policy so it
  can't be gamed into laundering a same-team pair as independent.
- **Derivative claims (enrichment).** Pathway enrichment consumes an upstream DE claim rather than
  raw data; its provenance and strength must inherit from that parent. Worth a small design note
  of its own before it ships.
- **Gated data (UK Biobank).** GWAS impact is high but its best dataset is access-controlled;
  first GWAS rows should lean on 1000 Genomes + GWAS Catalog summary stats.

---

## What this is not

Not a plan, not a schedule, not a commitment to build in any quarter. It is the conceptual menu
we point at — for ourselves, to know what we're aiming at, and for others, to make the abstract
concrete. When a row is ready to leave the horizon, it gets its own spec → plan → implementation
cycle, with methylation as the worked reference.
