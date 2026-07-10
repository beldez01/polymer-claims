# Rejection ≠ forbidden region: the agent loop must reason about parameterization

**Date:** 2026-07-10. Prompted by the MGMT→Temozolomide result in the pharmacogenomic
licensing build (merged `90510f8`).

## The worked example
In the pharmaco pipeline, `MGMT→Temozolomide` came back **REJECTED** (betting e≈0.78,
both legs agree the effect fails the criterion). Under the residue taxonomy we just
ratified, a REJECTED claim is a morphospace **forbidden region** — a high-confidence
negative. **But this particular rejection is not a genuine biological negative — it is an
artifact of the measurement scale.**

- The MGMT→temozolomide relationship is the textbook case where **promoter CpG-island
  methylation** silences MGMT and sensitizes cells to the alkylating agent. The signal
  lives in the promoter.
- Our SE-Contract is built from **gene-level (gene-body-averaged) imputed methylation**
  (`ingest/gdsc_pharmaco.py` → `pharmaco/data/gdsc.load_gdsc_methylation` →
  `methylation_imputed.csv.gz`). Gene-body averaging **washes out** the promoter signal.
  Hack's own `notes/MGMT_GATE.md` documented exactly this (gene-level MGMT rho≈−0.02, null).
- **Promoter methylation for the same lines exists** but was not lifted:
  `Hack/data/master/methylation_promoter_bycosmic.csv.gz` and the raw
  `Hack/data/ccle/CCLE_RRBS_TSS1kb_*` (TSS-1kb promoter RRBS).

So the *correct* parameterization would re-express the claim over **promoter β-space**, and
the current REJECTED verdict is confounded by testing over the wrong assay dimension.
(Honest caveat: whether MGMT→TMZ then *licenses* is an open empirical question — cell-line
TMZ AUC is compressed near 0.98, so even the promoter signal may be weak here. The point is
not "promoter will license it," it is "the rejection is not a trustworthy forbidden-region
negative because it was measured over the wrong space.")

## The capability the agent loop needs (the load-bearing note)
When a claim is **REJECTED**, the autonomous loop must not just file it as a forbidden-region
negative. It must ask: **is this a genuine high-confidence negative, or an artifact of the
parameterization?** — i.e. was the claim tested over the *right* measurement space for the
mechanism it asserts? This is precisely the **parameterization seam** of
`foundations/measurement-foundation.md`: a criterion evaluated over an ill-chosen assay
dimension "measures encoding artifacts," and rigor below that seam manufactures false
confidence — here, a false *negative*.

The loop should be able to:
1. **Detect** that a rejection may be scale-confounded — the mechanism is known to be
   localized (promoter / enhancer / specific CpG) but the claim was parameterized over a
   coarser or different dimension (gene-body average).
2. **Re-parameterize and re-propose** the same subject (marker→drug) over the correct
   measurement space (a promoter-β SE-Contract), as a *new* claim with its own pre-registered
   e-test — untrusted-proposer-style: an untrusted proposer generating the corrected hypothesis.
3. **Re-test** through the same gate. Only a claim rejected over the *right* parameterization
   is a trustworthy forbidden-region negative.

## Why this refines the residue-taxonomy decision
REJECTED-as-forbidden-region (the decision ratified for this branch) is sound **only when the
claim was parameterized correctly**. A rejection has (at least) two causes that the loop must
separate:
- **True forbidden negative** — confidently ruled out over the right measurement space.
- **Parameterization artifact** — rejected because tested over the wrong assay dimension; a
  re-parameterized re-test may flip it.

Collapsing both into "forbidden" is the exact morphospace weakness `measurement-foundation.md`
§7 (#8, "forbidden vs unobserved") warns about — extended here to "forbidden vs
mis-parameterized." The invariance idea (§3) is the detector in spirit: a verdict that would
change under a change of assay-space that *should* be mechanistically relevant (gene-body →
promoter) signals that the parameterization, not the biology, is doing the work.

## Concrete buildable follow-ups
- **Lift promoter methylation** (`methylation_promoter_bycosmic.csv.gz` / CCLE RRBS TSS-1kb) as
  a second SE-Contract dimension; re-test the MGMT→TMZ (and other promoter-localized) claims
  over promoter β-space. This is also the honest next step for the measurement-foundation
  "methylation β-space" worked example (gene-body and promoter are *different* measurement
  spaces, not admissible transformations of one another).
- **An agent-loop skill: "on REJECTED, consider alternate parameterizations of the same
  subject and re-propose"** — the generative reasoning this note is really about. Adjacent to
  the neg-whisper backlog and the parameterization-seam research program.
