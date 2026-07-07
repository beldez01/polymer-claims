# Adapter-Independence Hardening — Plan

**Date:** 2026-07-07
**Status:** PLAN (turns the recommendation set into a scheduled arc). Ready for `writing-plans` per slice.
**Basis:** `docs/superpowers/specs/2026-06-29-adapter-independence-hardening-notes.md` (the recommendations),
`docs/the-theory-of-polymer-claims.md` (defeater **D4**), `docs/superpowers/foundations/epistemology.md` §2/§8,
`docs/superpowers/foundations/residualism.md` §7 (the Sellarsian back-door Given).

---

## 1. Why this is the priority

This closes the theory's most exposed defeater, **D4**: *warrant is hollow if conceptual independence
can't even be measured.* The air-gap secures **organizational** independence (different owner,
different code lineage). It does **not** secure **epistemic** independence: two adapters can share
training corpora, reference databases, and modeling priors, and then *fail together* — their agreement
is "not two witnesses; one witness counted twice." Correlated error walks straight across the air-gap.

The goal is not to *eliminate* this (impossible — see §7), but to **instrument** it: replace the
hand-set organizational-tier discount with a **measured effective-witness count**, and honestly flag
the residual it cannot see. That is the residualist stance made into engineering.

## 2. The organizing distinction (bias vs. variance)

Every slice below is sequenced by this split (from the notes):

- **Correlated *variance*** — the legs wobble together on noise. **Detectable without ground truth**,
  by perturbing shared inputs and watching whether the legs move together.
- **Correlated *bias*** — the legs are wrong in the *same direction by the same amount*. **Invisible
  to agreement by construction** — they agree *because* both are wrong. Only an external truth anchor
  (or a methodologically-distant third witness) catches it.

R2 measures variance (and bias where truth exists); R1 and R4 bound the bias R2 cannot see.

---

## 3. Step 0 — The weekend experiment (do this FIRST; it gates everything)

**A one-day, falsifiable probe of whether D4 is a real threat or a paragraph.** Before building any
machinery, measure whether organizational independence is a comfortable illusion.

> This section is written to be lifted straight to a compute instance. As Research I scope + source;
> the scoring runs are compute (another instance). Consistent with the compute boundary — the models
> run wherever; Polymer only *witnesses* the error vectors.

### 3.1 Question

Do two **organizationally-independent** variant-effect predictors — **AlphaMissense** (DeepMind) and
**ESM1v** (Meta) — make their *errors* independently, or do they fail on the **same** variants? I.e.,
is their T1 "full independence" tier epistemically real?

### 3.2 Truth set (ClinVar, high-confidence, missense)

Source: ClinVar `variant_summary.txt.gz` (NCBI FTP). Filter to a binary, high-confidence, missense set:

- **Review status ≥ 2 gold stars** — `ReviewStatus ∈ {"criteria provided, multiple submitters, no
  conflicts", "reviewed by expert panel", "practice guideline"}`. (Excludes single-submitter and
  conflicting.) *[reported — verify current ClinVar column values at run time.]*
- **Label:** `y = 1` for `ClinicalSignificance ∈ {Pathogenic, Likely pathogenic}`; `y = 0` for
  `{Benign, Likely benign}`. Drop VUS / conflicting / other.
- **Consequence:** missense only (both models score missense substitutions). Map via
  `MolecularConsequence` / the protein change (`p.XnnnY`).
- **Assembly:** GRCh38; keep `(chrom, pos, ref, alt)` for joining.
- **Leakage guard (critical):** both models were developed against ClinVar-adjacent data. Prefer
  variants **added/updated after each model's training cutoff** (use the ClinVar `LastEvaluated` /
  submission dates). If a clean post-cutoff split is too small, proceed on the full set but **report the
  leakage caveat prominently** — leakage tends to make both models *more* accurate on ClinVar, which is
  conservative for our purpose (it makes independence look *better* than it is, so a high ρ despite
  leakage is an even stronger alarm).
- Aim for **N ≥ a few thousand** variants with both models scored; report N per class.

### 3.3 Model scores

- **AlphaMissense** *(reported, Cheng et al., Science 2023)*: precomputed pathogenicity ∈ [0,1] for
  ~71M human missense (`AlphaMissense_hg38.tsv.gz`). Class thresholds: likely-benign < 0.34, ambiguous
  0.34–0.564, likely-pathogenic > 0.564. Join by `(chrom,pos,ref,alt)` or UniProt + protein change.
- **ESM1v** *(reported, Meier et al., NeurIPS 2021)*: variant effect = masked-marginal log-likelihood
  ratio (LLR) of alt vs ref at the position; **more negative = more deleterious**. Use the 5-model
  ensemble mean (ESM1v_1..5) from precomputed human-proteome LLR tables, or compute via the ESM repo.
- **Orientation + threshold (avoid circularity):** split the truth set into **calibration** and
  **test** halves. Pick each model's decision threshold on **calibration** only (Youden's J on the ROC,
  or the published AlphaMissense 0.564), then compute all error metrics on **test** only. Never tune a
  threshold on the same variants you score errors on.

### 3.4 Metrics (Kuncheva–Whitaker ensemble diversity)

For each model `m ∈ {A, E}` and test variant `i`, binary call `ŷ_{m,i}` → **error indicator**
`z_{m,i} = 1[ŷ_{m,i} ≠ y_i]`.

1. **Error correlation ρ** = Pearson (φ) correlation between `z_{A,·}` and `z_{E,·}`.
2. **Double-fault rate** `DF = (#{i : z_{A,i}=1 ∧ z_{E,i}=1}) / N` — both wrong on the same variant.
3. **Q-statistic** and **disagreement measure** as secondary diversity indices.
4. **Effective witnesses** `N_eff = 2 / (1 + ρ)` — the concrete headline. ρ≈0 → ~2 witnesses; ρ→1 → ~1.
5. Report per-class breakdown (errors on pathogenic vs benign can correlate differently) and a 2×2
   confusion of (A correct?) × (E correct?).

### 3.5 Decision rule (what the result gates)

- **ρ high (≳0.5) or DF high** → organizational independence is largely illusory for this pair; two
  "independent" corporate models fail together → **D4 is real → R2 (decorrelation battery) + R5 (N_eff
  cap) become priority builds.** Empirically justifies the whole arc.
- **ρ low (≈0–0.2)** → the pair really is close to two witnesses; T1 ≈ honest for this pair. R2 can stay
  a paragraph *for now*; still ship R1 (the cheap prior). **Does not clear D4 globally** — see §7.

Either outcome is decision-useful. Escalation if ambiguous: add a third pair (e.g., a
structural/biophysical predictor as R4's heterodox witness) and re-measure.

### 3.6 Deliverable

A one-page result: N, per-class counts, ρ, DF, Q, `N_eff`, the confusion table, and the leakage-caveat
statement — plus the go/no-go for R2. Hand back to the plan; it sets R2's priority.

---

## 4. The build arc (each slice plugs into an existing seam — none greenfield)

### R1 — Provenance lineage in the credential *(the cheap prior; ship regardless of Step 0)*
Extend `AdapterCredential` — today `(identity, owner, implementation_hash, version, trusted)` — with a
**declared provenance lineage**: training corpora, reference databases, assumption class. Compute a
**prior-overlap coefficient** between two legs; high overlap sets an independence *prior* below T1's
nominal full strength. Static/declaration-based (gameable, incomplete) but free, and it upgrades the
binary tier to a graded coefficient. **Seam:** the oracle dossier that already records the tier.

### R2 — The decorrelation battery *(the empirical instrument; priority set by Step 0)*
Per claim type, assemble a **known-truth calibration battery** (ClinVar hi-conf for variant effect;
spike-in / simulated RNA-seq with known fold-changes; null-permuted data for false-positive behavior).
Run both legs, record each leg's **signed error vector** (not its output), compute **error correlation
ρ** and **double-fault**. **Seam:** the shipped `calibrate`/`certify` warrant-tiered `q`-ledger — one
more column.

### R5 — Effective-N as the cap *(the integration)*
Make the strength vector's evidence axes reflect **`N_eff = 2/(1+ρ)`** (bounded by R1's provenance
prior when ρ is unmeasurable), instead of a hand-set tier discount. The organizational tier degrades to
a **fallback prior used only until the battery has spoken.** **Seam:** the existing oracle strength-cap
mechanism — this changes what *feeds* the cap, not the gate itself.

### R3 — Adversarial shared-failure probing *(active; no waiting on batteries)*
Don't only measure on a fixed battery — *hunt* for inputs where both legs likely share a blind spot:
OOD probes near the edge of common training support, or inputs engineered to violate a *shared*
assumption (e.g., zero-inflated / overdispersed counts that break the negative-binomial prior both
DESeq2 and edgeR lean on). **Co-failure is the fingerprint of a shared prior.** **Seam:** the RED-TEAM
daemon → a "decorrelation red-team."

### R4 — The heterodox third witness *(architectural; for the bias R2 can't see)*
When two legs are suspected of shared priors, audit with a **third** adapter chosen for *maximal
methodological distance* (for variant effect: a structural/biophysical model, not another
evolutionary-sequence model). Its job is to **disagree informatively**; agreement that survives a
methodologically-distant third is the only agreement that argues against correlated *bias*. **Seam:**
the heterodox reserve lane already in SELECT (#3b) — extend it from *selection* into *verification*.

---

## 5. Sequencing & dependencies

```
Step 0  weekend experiment  ──gates priority of──▶  R2/R5
   │
R1  provenance prior         (ship now; independent of Step 0; cheap)
R2  decorrelation battery    (priority ← Step 0)     ┐
R5  N_eff → strength cap      (needs R2's ρ)          ├─ the core instrument
R3  decorrelation red-team   (parallel; reuses RED-TEAM)
R4  heterodox third witness  (architectural; last; for correlated bias)
```

Each slice: `writing-plans` → `subagent-driven-development` (TDD) → whole-branch review → merge
`--no-ff` → update `CONTINUE.md`. Purity invariant holds: the battery/ρ computation is umbrella-side
(numpy); `grammar/`+`protocol/` stay pure — the cap consumes a passed-in `N_eff` the way the e-value is
passed in today.

## 6. Acceptance (arc-level)

- Step 0 result recorded, with the go/no-go for R2.
- A licensed claim's strength axes reflect a **measured** `N_eff` (R2+R5), not a hand-set tier discount,
  for at least one claim type — with the battery, ρ, and `N_eff` recorded in the `q`-ledger and the
  certificate.
- The credential carries provenance lineage + a prior-overlap coefficient (R1).
- `grammar/`+`protocol/` pure + numpy-free; `Corpus` stays 4; `check-all.sh` green.

## 7. The honest limit (state it; do not paper over it)

This arc **instruments** D4; it does not solve it. R2 catches correlated **variance** always, and
correlated **bias only where ground truth exists.** For the vast majority of real claims with no truth
anchor, **correlated bias stays invisible** — two legs wrong the same way agree, and no amount of
recomputation sees it. R1 (declared-provenance prior) and R4 (heterodox witness) *bound* what R2 cannot
measure, but do not close it. The correct posture is the residualist one (`residualism.md` §7): the gate
is a **method-dependence detector, not a correspondence oracle**, and a license's strength is bounded by
the **breadth of independence actually sampled** — certified and logged, never assumed. Publishing this
limit (as D4, with its defeaters) is the integrity move, not a weakness.

## 8. Compute-boundary compliance

Every slice keeps Polymer on the **witness-not-serve** side (`foundations/compute-boundary.md`): the
batteries and probes run the *models*' compute elsewhere (user/third-party); Polymer records the error
vectors, computes ρ/`N_eff`, and adjusts standing. It certifies independence; it never hosts the models.
