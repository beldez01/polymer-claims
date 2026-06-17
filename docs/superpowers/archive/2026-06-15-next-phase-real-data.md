# Next phase — the real-data swap (from *exercised* to *earned*)

**Date:** 2026-06-15 · **Status:** dataset chosen — **TCGA-LAML, IDH1/2-mut vs WT** (GDC, open access); spec next.
**Reconciles:** `ARCHITECTURE_CURRENT.md`, `CONTINUE.md`, the deferred-analysis menu (item 6).

---

## The recommendation, in one line

**Swap the synthetic methylation betas for a real public cohort.** It is the single highest-leverage
move available: it converts the system's central proof — "a claim licenses on a real, independently
recomputed, content-addressed analysis that beats a criterion" — from *exercised* to **earned**, which
is the whole thesis. Every other open item is polish or a parallel arc by comparison.

## Why this, why now

- **It closes the #1 standing caveat.** Every doc carries the same honesty note: the methylation tier
  licenses on a *computed* region-Δβ from two independent legs, but **over synthetic betas**, so the
  recomputable-public tier is *exercised, not earned*. Real data is the one thing that retires it.
- **The swap is designed-in, not a rebuild.** Data enters through the content-addressed SE-Contract
  seam (DRS-shaped, keyed by `dimnames_hash`); the apparatus is a content-addressed `AnalysisProfile`
  (`profile_hash`); the two independent legs and the drift daemon already exist. The load path was
  built so a real cohort is an *identical `load_contract` seam* — point it at real betas and the rest
  runs unchanged.
- **It's the keystone for the next arc.** The standards skin (DRS / RO-Crate / in-toto attestation)
  is far more compelling once there are *real* runs to address and attest. Real data first, standards
  skin second.
- **The rigor core is ready for it.** Phases 2.1–2.4 + §2E + reinstatement + n-DMPs all shipped: the
  e-value/e-LOND gate, defeat-as-update with refund, drift-reopen, REPRODUCED/REPLICATED tiers, and a
  second reduction (n-DMP count) are live. The machine is built; it needs real input.

## What this phase delivers (acceptance)

1. A **real public methylation cohort** licenses a region-Δβ (and the n-DMP count) at **REPRODUCED**,
   on values **computed from real betas** by the two independent legs, beating the stated criterion.
2. The license records its **full content-address** — real dataset `dimnames_hash` + apparatus
   `profile_hash` + `semantic_run_id` — and survives a drift check.
3. The **synthetic-betas caveat is retired** for that tier; `q` (the false-license rate) is reported
   on real data.
4. **Honest failure is an acceptable outcome.** If a region does *not* clear the criterion on real
   data, the gate correctly **withholds** the license — that is the system working, reported plainly,
   not a failure of the phase.

## The dataset (chosen) — TCGA-LAML, IDH1/2-mut vs WT

Acute Myeloid Leukemia (TCGA-LAML), Illumina **HumanMethylation450 (HM450)**, via the NCI **GDC**.
Verified fit (sourced GDC + NEJM 2013 + Figueroa 2010):

- **~194 cases** with HM450 methylation; **fully open access** — Level-3 beta values *and* the somatic
  MAF (for grouping) *and* clinical (age/sex) are all open in GDC, **no dbGaP / controlled access needed**.
- **Genome build:** harmonized **GRCh38** (SeSAMe-processed Level-3 betas) are the current default.
- **Contrast: IDH1/2-mutant vs WT (~38 vs ~155)** — the strongest, most-replicated hypermethylation
  signal in AML (IDH→2-HG inhibits TET2 demethylation; Figueroa 2010, confirmed in TCGA 2013) and
  well-powered. (Backup: DNMT3A-mut ~51 — larger N but co-mutation-confounded. Not the small ~17
  TET2-mut group.)

**Two adjustments from the synthetic demo's EPICv2 assumption:**

- **Add a 450K `AnalysisProfile`.** The apparatus is content-addressed precisely so "which platform" is
  a *named* choice; running HM450 data through the EPICv2 profile would be wrong. A new `HM450` profile
  (450K manifest, GRCh38, distinct `profile_hash`) is the system working as designed — and a proof point
  that the apparatus abstraction spans platforms.
- **Ingest GDC's processed Level-3 betas → the Python legs run directly** (no R normalization for the
  demo). The `AnalysisProfile` honestly becomes *"GDC HM450 Level-3 SeSAMe pipeline"* — a real, citable
  upstream apparatus (arguably more honest than re-deriving).

> **Data is NOT committed.** A 194 × ~485k real beta matrix is hundreds of MB and stays local /
> gitignored; the repo ships the *ingestion + validation*, the 450K profile, and a tiny content-address
> manifest — not the data. (Exact "what's committed vs local" boundary is a spec fork — see below.)

## The wiring path

1. **Ingest** TCGA-LAML HM450 Level-3 betas + the open MAF + clinical from GDC → real `dimnames_hash`.
   Define `Sample_Group` = IDH1/2-mut vs WT from the MAF; carry Age/Sex from clinical. (First reuse what
   transfers from the existing real-data path — `exec_adapters.py: real_data_seed_corpus`,
   `StatsPureAdapter`, `serve --real-data`.)
2. **Add the 450K `AnalysisProfile`** (manifest, GRCh38, GDC SeSAMe provenance) → its `profile_hash`.
3. **Compute** real betas → region-Δβ and the n-DMP count via the two independent legs (over a chosen
   IDH-hypermethylated region — region selection is a spec fork).
4. **Gate**: legs agree (air-gap) ∧ e-value beats the e-LOND threshold ∧ survives the defeat graph →
   an **earned** license, not an asserted one.
5. **Pin & verify**: record the full content-address; run the drift daemon to confirm a content move
   re-opens it.
6. **Retire the caveat** in `ARCHITECTURE_CURRENT.md` / `CONTINUE.md`; report `q` on the real run.

Now ready for the **brainstorm → spec → plan → subagent-driven** build — the dataset has fixed the
unknowns, leaving a handful of design forks (what's committed vs local; region selection; IDAT-vs-betas;
how `Sample_Group` is derived/pinned) to resolve in the spec.

## The natural follow-on (REPLICATED)

One real cohort earns **REPRODUCED** (two methods, one dataset — the air-gap). A **second real cohort**
with a distinct `dimnames_hash` then earns the **REPLICATED** gold tier and licenses the *product*
e-value as one e-LOND test (§2E is already built and waiting for it). So the fully-earned arc is:
real cohort A → REPRODUCED, then real cohort B → REPLICATED. Pick A first; B is the encore.

## What this phase is NOT

- Not a rewrite — the rigor core, the seams, and the drift daemon are done.
- Not the standards skin (that's the next arc, and wants real runs to attest).
- Not federated/multi-tenant (still local-only by design).
- Not blocked on R parity or new math — purely on choosing real input.
