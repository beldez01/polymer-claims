# Phase 2d-ii — the licensed expression-floor spine (design)

**Status:** approved (brainstorm 2026-07-12). Second sub-project of the WAYLAND licensed spine; consumes
`se:tcga_laml_fusion_expr@1` from 2d-i.

## Goal

Mint the **first LICENSED synbio claim**: *"In RUNX1-RUNX1T1+ (t(8;21)) AML, RUNX1T1 expression clears a
pre-registered 13 TPM floor; fusion− AML does not."* Drive it through the real `run_cycle` gate at
`IndependenceTier.REPRODUCED`, reusing the pharmaco MTAP→Palbociclib plumbing. Two-stratum rule: only this
recompute licenses (the reported synbio claims stay CONJECTURED).

## The core architecture — floor and discrimination are SEPARATE mechanisms

The pharmaco betting e-value (`evidence.py:betting_evalue`) is shape-locked to a **bounded two-sample
difference** `E[b−a] > θ` — it earns validity only from `[0,1]` boundedness. Our claim conflates two
statistically orthogonal facts, which MUST ride different mechanisms or the gate is unsound:

1. **The 13 TPM floor → the leg CRITERION.** The claim leaf is `QuantityLeaf(value=13.0, low=13.0,
   dimension=D, context=MeasurementContext(tissue="AML", assay="RNA-seq TPM"))` — a GAP-3 *floor* (value ==
   low, high open). The plan's `SatisfactionCriterion(comparator=GE, reference_leaf_index=0)` makes the
   criterion RHS = `leaf.value` = 13 (the grammar path at `evaluate.py:219-229`). Each of two independent legs
   returns the **fusion+ group location** as an `ExecValue`; the criterion checks `fusion+ location ≥ 13`. Both
   legs must satisfy → `agreement_mode="both_satisfy_criterion"`.
   - **Dimension-match is load-bearing (plan detail):** `_resolve_reference` (`evaluate.py:246-252`) runs a
     dimension-compatibility check between the leaf and the computed `ExecValue`. The leaf's `dimension` D and
     the value each leg's `ExecValue` carries MUST be compatible (both the same TPM/abundance `Dimension`, or
     both `None`) or the criterion rejects on a dimension mismatch. The plan pins one consistent choice and a
     test asserts a bare `≥13` comparison actually fires (guards against a silent dimension-mismatch reject).
2. **The fusion+/− discrimination → the betting E-VALUE.** A separate `expression_floor_evalue` computes
   `betting_evalue(a=fusion_neg/CAP, b=fusion_pos/CAP, threshold=NULL_GAP, comparator=GT)` — the between-group
   gap, TPM rescaled into `[0,1]` by a **pre-registered CAP** (boundedness is load-bearing for validity).
   Reuses `evidence.py:betting_evalue` untouched.

**Why the split is non-negotiable (the ACTB guardrail).** A housekeeping gene like ACTB is high in *both*
groups: it clears 13 everywhere (criterion satisfied on both legs) but has ~0 between-group gap (e-value ≪ 33 →
PENDING, never licensed). The **ACTB negative control is the only thing that proves the two mechanisms stayed
separate.** If anyone ever "simplifies" the e-value to test the floor directly (e.g. the one-sample
`count_enrichment_evalue` path), ACTB licenses and the control catches it. The control is mandatory, not
optional.

## The two independent legs (the air-gap)

Named-categorical split on `Sample_Group ∈ {fusion_pos, fusion_neg}` (closer to `REGION_DELTA_BETA_CELL`'s
explicit `level_a`/`level_b` than pharmaco's within-tissue median split). Two estimators of the fusion+
location, registered with **distinct owners** (that is what makes them independent for the air-gap):
- **Leg A — mean:** `mean(fusion_pos TPM)`.
- **Leg B — Hodges-Lehmann:** the pseudo-median (median of within-group values / HL estimator) of
  `fusion_pos TPM`.

Both return the fusion+ location; the criterion checks each ≥ 13. Only Leg A's split feeds the e-value (mirrors
pharmaco: rank leg corroborates, never feeds the e-value).

## Pre-registered parameters (commit-before-data)

Locked via `register_test(ledger, claim.id, commitment_hash(claim))` in `preregister`, BEFORE any TPM is read:
- **FLOOR = 13.0 TPM** — the criterion. Anchored to a domain-standard "robustly expressed gene" threshold
  (~10–13 TPM is a widely-used RNA-seq convention), carried in the spine scaffold since Phase 1. **Not tuned to
  the observed gap.**
- **CAP = 100.0 TPM** — the e-value rescaling constant. Domain-justified: 100 TPM is a standard "highly
  expressed" ceiling; genes above it clip to 1.0. Data-independent.
- **NULL_GAP = 0.1** — the e-value null discrimination margin in `[0,1]` units (≈ 10 TPM at CAP). The null is
  "fusion+ exceeds fusion− by less than NULL_GAP"; rejecting it means a real, sizeable discrimination (not
  noise > 0). Data-independent.

### Integrity — the pre-registered floor and the robustness demonstration

We have already seen the 2d-i data (fusion+ ~94 TPM, fusion− ~0.023 TPM), so the floor must be defended as
*independent of that peek*. Two safeguards, both required:
- The floor is anchored to a **domain threshold** (robust-expression ~10–13 TPM), not to the observed gap.
- A **mandatory robustness sweep** (a test) shows the LICENSE verdict is **invariant for any floor in ~[1, 90]
  TPM** — because the 4161× separation dwarfs the floor. That invariance is the evidence the result is not
  floor-fished; a result that flipped as the floor moved would be. The sweep is reported in the writeup.

## Components (all umbrella-side; reuse pharmaco, swap the split + evidence)

- `src/polymer_claims/expression_floor_adapters.py` — `ExpressionFloorMeanAdapter`, `ExpressionFloorHLAdapter`
  (each `_split(node)` → `(fusion_pos, fusion_neg)` via `group_of[s] == level`), `expression_floor_registry()`
  (two distinct owners); `expression_floor_claim(gene, tissue, floor, ...)` + `build_evaluation_plan(...,
  criterion=SatisfactionCriterion(GE, reference_leaf_index=0))`. numpy allowed (umbrella).
- `src/polymer_claims/expression_floor_evidence.py` — `expression_floor_evalue(node, *, cap, null_gap)` →
  `betting_evalue(fusion_neg/cap, fusion_pos/cap, threshold=null_gap, GT)`.
- **`EXPRESSION_FLOOR_CELL`** — a new `CapabilityCell` added ALONGSIDE `PHARMACO_ASSOC_CELL` (same file), pure
  and additive (numpy-free; existing corpora unaffected — nothing references it, so byte-identical):
  `criterion_target` via `reference_leaf_index`, `claim_leaf_kinds=("quantity",)`,
  `agreement_mode="both_satisfy_criterion"`, params `{gene, group_col, level_a, level_b}`.
- `src/polymer_claims/expression_floor_populate.py` — `preregister` / `license_batch` copied from
  `pharmaco_populate.py` (swap adapters/registry/evidence); `check_controls(corpus, *,
  positive="floor-RUNX1T1", negative="floor-ACTB")`; keep `FDRLedger(target_fdr=0.05)` → first-test bar
  **32.9**. `populate_universe`-style publish guard optional (single claim; may inline).
- **`[spine]` extra** in `pyproject.toml` = `["numpy>=1.26"]` (no pandas/scipy/statsmodels — the GDSC scan is
  replaced by a fixed floor). The new modules are **not** re-exported from `polymer_claims/__init__.py` (base
  import stays numpy-free), matching the pharmaco convention.

## Tests

- **End-to-end license test** (`tests/spine/test_expression_floor_license.py`, cloned from
  `tests/pharmaco/test_pharmaco_license.py`): against a small synthetic contract (planted fusion+ well above
  13, fusion− near 0), `preregister` → `license_batch` → assert `floor-RUNX1T1` status is LICENSED at
  `IndependenceTier.REPRODUCED` **if** the e-value clears 32.9; the test asserts the *mechanism* (a strong
  planted signal licenses; a weak one stays PENDING) so it is deterministic regardless of the real n=6 outcome.
- **ACTB control test:** a housekeeping gene high in both groups → criterion satisfied on both legs BUT e-value
  ≪ 32.9 → NOT licensed. `check_controls` returns `ok=True` (positive licensed, negative not).
- **Air-gap test:** the two legs have distinct owners; a single-leg agreement (only mean, or only HL) does not
  license (both must satisfy).
- **Floor-robustness sweep:** the license verdict on the planted-strong fixture is invariant for floor ∈
  {1, 5, 13, 50, 90}.
- **Real-data run** (slow, marked): against `se:tcga_laml_fusion_expr@1`, report the actual e-value and status
  (LICENSED or honest PENDING) — recorded, not asserted (n=6 power is what it is).

## Invariants

- `grammar/` and `protocol/` stay pure + numpy-free (the new cell is a pure additive object; the e-value reaches
  `run_cycle` as a plain `float`). `Corpus` stays 4. numpy only umbrella-side behind `[spine]`.
- Two-stratum: only this recompute licenses; reported synbio claims stay CONJECTURED. The computed effect never
  enters the claim leaf (the leaf carries the *floor*, 13, not the measured 94).
- Commit-before-data: floor/CAP/NULL_GAP + `commitment_hash` locked at `preregister`, before `license_batch`
  reads TPM.

## n=6 power caveat

6 fusion+ samples with a huge, consistent gap may or may not clear the 32.9 e-LOND first-test bar. **An honest
PENDING is an acceptable outcome** — the machinery, the controls, and the robustness sweep all validate
regardless, and PENDING (not REJECTED) correctly means "unearned at this power," not "refuted."

## Scope / tasks (for writing-plans)

1. `expression_floor_adapters.py` (two legs + split + registry) + unit tests (split correctness, two owners).
2. `expression_floor_evidence.py` (gap betting e-value + CAP/NULL_GAP) + unit tests (strong gap → large e-value;
   zero gap → e-value ≈ 1).
3. `EXPRESSION_FLOOR_CELL` + `expression_floor_claim` + plan wiring (QuantityLeaf floor + reference_leaf_index
   criterion) + a build/round-trip test.
4. `expression_floor_populate.py` (preregister/license_batch/check_controls) + the end-to-end license test,
   ACTB control test, air-gap test, floor-robustness sweep + `[spine]` extra.
5. Real-data run against `se:tcga_laml_fusion_expr@1` (record e-value + status) + continuity/memory + writeup of
   the headline (LICENSED@REPRODUCED or honest PENDING) with the robustness sweep.

## Out of scope

A second independent cohort (would lift REPRODUCED → REPLICATED); other fusions (PAX3-FOXO1); the Durendal
headline re-derivation (later WAYLAND phase).
