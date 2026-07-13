# Phase 2d-iii — cross-cohort REPLICATED license Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Promote the RUNX1-RUNX1T1 expression-floor claim to `IndependenceTier.REPLICATED@LICENSED` by adding an error-independent second cohort (TARGET-AML) whose betting e-value multiplies with TCGA's (e₁·e₂) into the claim's single pre-registered e-LOND slot.

**Architecture:** Reuse the 2d-i data pipeline (a second `se:target_aml_fusion_expr@1` contract) and 2d-ii licensing. The one new module is an expression-floor analog of the methyl-only `replication.py::build_replication_inputs`, adapted for the reference_leaf floor criterion (floor = the claim's `QuantityLeaf.value`, e₂ = `expression_floor_evalue`). `shared_cause_factors` are passed as disjoint, non-empty license-time params.

**Tech Stack:** Python 3.12, numpy (`[spine]`), the existing §2E machinery (`grammar/.../licensing.py`, `shared_cause.py`, `protocol/.../verify.py`). Spec: `docs/superpowers/specs/2026-07-12-spine-2diii-replicated-design.md`.

## Global Constraints

- `grammar/` and `protocol/` untouched, pure + numpy-free (§2E already exists there; we add an umbrella-side builder). `Corpus` stays 4. numpy only umbrella-side (`[spine]`).
- Two-stratum: only the recompute licenses. Commit-before-data: floor/CAP/NULL_GAP + factor sets pre-registered.
- **ONE e-LOND slot per claim** — the product e₁·e₂ is folded into the single `evidence[cid]`; NEVER `register_test` cohort B as a second slot.
- **§E fail-quiet guardrails:** `shared_cause_factors` for both cohorts MUST be **non-empty** (empty ⇒ gate inert ⇒ over-credit) AND disjoint (overlap ≥ 0.5 ⇒ silent REPRODUCED cap). `license_replicated` hard-asserts non-empty; a test covers the cap and the empty-guard.
- Self-contained: both cohorts' big data gitignored, small extracts pinned.
- Test command: `cd /Users/zbb2/Desktop/polymer-claims && uv run --project . pytest tests/spine/ -q`.

## Precedent to mirror (read these)

- `src/polymer_claims/replication.py` — the FULL methyl `build_replication_inputs` (Task 2 mirrors it; note the 3 adaptations below).
- `data/tcga_laml_fusion_expr/build_extract.py` — the 2d-i extract (Task 1 mirrors it for TARGET).
- `src/polymer_claims/expression_floor_populate.py` — `license_batch` (Task 3 adds `license_replicated` beside it).

**The 3 adaptations from methyl `replication.py` (load-bearing):**
1. impl guard `node.impl != "expression::floor"` (not methyl `_IMPL`).
2. The criterion is `reference_leaf` (`crit.threshold is None`) — do NOT do methyl's `if crit.threshold is None: continue`. Instead read the **floor from the claim's leaf**: `floor = claim.leaves[crit.reference_leaf_index].value`. The both-legs-clear check compares each leg's location to `floor` (GE).
3. e₂ = `expression_floor_evalue(node_b)` (the discrimination betting e-value with CAP/NULL_GAP) — NOT `betting_evalue(..., threshold=crit.threshold)`.

---

### Task 1: TARGET-AML fusion-expression contract (controller-executed)

> Real one-shot fetch, mirroring 2d-i. Controller-executed. Reuses `build_fusion_expr_contract` UNCHANGED.

**Files:**
- Create: `data/target_aml_fusion_expr/build_extract.py` (+ pinned `panel_tpm.tsv`, `fusion_labels.tsv`, `SOURCE.txt`, `build.log`); committed contract `src/polymer_claims/contracts/target_aml_fusion_expr.{json,betas.tsv}`.
- Modify: `.gitignore` (the big matrix + raw clinical).

- [ ] **Step 1: Write `data/target_aml_fusion_expr/build_extract.py`** — copy `data/tcga_laml_fusion_expr/build_extract.py` and change ONLY:
  - Matrix URL → `https://gdc-hub.s3.us-east-1.amazonaws.com/download/TARGET-AML.star_tpm.tsv.gz` (verify it is log2(TPM+1) the same way — print RUNX1T1/ACTB medians; convert `raw = 2^x − 1`; if the scale looks raw not log2, ABORT and report).
  - Fusion label → cBioPortal `GET /api/studies/aml_target_2018_pub/clinical-data?clinicalDataType=PATIENT&attributeId=PRIMARY_CYTOGENETIC_CODE&projection=SUMMARY`; `fusion_pos` iff `t(8;21)` in the value.
  - `uid_stem="target_aml_fusion_expr"`; out to `data/target_aml_fusion_expr/`.
  - Case-id normalization: TARGET barcodes are `TARGET-20-PAxxxx-...`; confirm `case_id` (transform.py) yields a stable patient id that JOINS the RNA-seq columns to the cytogenetics patientIds (print an overlap count; if the join is empty, adjust the id normalization and report).
- [ ] **Step 2: Run the extract.** `uv run --project . python data/target_aml_fusion_expr/build_extract.py`. Expect `n_fusion_pos ≫ 6` (TARGET has ~123 t(8;21); the RNA-seq∩karyotype overlap is the real number — print it). Self-checks (hard asserts, mirror 2d-i): fusion+ band (assert `5 <= n_pos <= 200`), RUNX1T1 fusion+ median ≥5× fusion−, ACTB/GAPDH flat.
- [ ] **Step 3: Build + register** `se:target_aml_fusion_expr@1` via `build_fusion_expr_contract(..., out_dir=Path(contracts.__file__).parent)`; `clear_contract_cache()`; `load_contract`. Print `dim` + `dimnames_hash`, and ASSERT `dimnames_hash != load_contract("se:tcga_laml_fusion_expr@1").dimnames_hash` (distinct cohorts — required for REPLICATED).
- [ ] **Step 4: `.gitignore`** the big matrix + raw clinical json; confirm `git status` shows only the small extract + contract.
- [ ] **Step 5: Commit** → `git add data/target_aml_fusion_expr src/polymer_claims/contracts/target_aml_fusion_expr.json src/polymer_claims/contracts/target_aml_fusion_expr.betas.tsv .gitignore && git commit -m "feat(spine): build se:target_aml_fusion_expr@1 (TARGET-AML t(8;21) second cohort, 2d-iii)"`

---

### Task 2: The expression-floor replication builder

**Files:**
- Create: `src/polymer_claims/expression_floor_replication.py`
- Test: `tests/spine/test_expression_floor_replication.py`

**Interfaces:**
- Produces: `build_expr_replication_inputs(corpus, base_ctx, *, bindings: dict[str,str], factors_a: tuple[str,...], factors_b: tuple[str,...]) -> ReplicationInputs` (reuses the grammar-agnostic `ReplicationInputs` from `replication.py`).
- Consumes: `.expression_floor_adapters` (both adapters), `.expression_floor_evidence.expression_floor_evalue`, `.replication` (ReplicationInputs, `_rebind`), `.evidence` (`_terminal_node`, `evidence_map`), `.claim_detail._compare`, `.contracts.load_contract`, grammar `DataHandle`/`Satisfaction`/`SatisfactionVerdict`/`MaterializationContext`/`cohorts_error_independent`.

- [ ] **Step 1: Write the failing test** (`tests/spine/test_expression_floor_replication.py`) — a claim licensed on cohort A, plus a strong cohort B with DISJOINT factors, yields a cohort-B satisfaction + a multiplied e-value:

```python
from pathlib import Path

from polymer_claims import contracts as _c
from polymer_claims.ingest.tcga_laml_fusion_expr import build_fusion_expr_contract


def _contract(tmp_path, stem, pos_hi=True):
    pos = {f"{stem}p{i}": (90.0 if pos_hi else 0.1) + i for i in range(8)}
    neg = {f"{stem}n{i}": 0.0 + 0.01 * i for i in range(30)}
    fusion = {**{k: "fusion_pos" for k in pos}, **{k: "fusion_neg" for k in neg}}
    build_fusion_expr_contract({"RUNX1T1": {**pos, **neg}}, fusion, {k: "" for k in fusion},
                               genes=["RUNX1T1"], out_dir=tmp_path / stem, uid_stem=f"{stem}_fx")
    return f"se:{stem}_fx@1"


def test_disjoint_strong_cohortB_multiplies_and_replicates(tmp_path):
    from polymer_protocol.corpus import Corpus
    from polymer_grammar import FDRLedger, MaterializationContext
    from polymer_claims.expression_floor_adapters import expression_floor_claim
    from polymer_claims.expression_floor_replication import build_expr_replication_inputs
    from polymer_claims.expression_floor_evidence import expression_floor_evalue  # noqa

    ref_a = _contract(tmp_path, "acoh")
    ref_b = _contract(tmp_path, "bcoh")
    _c.clear_contract_cache()
    with _c.using_contract_root(tmp_path / "acoh"):
        pass  # contracts written under per-stem dirs; the builder loads by ref below via a shared root
    # NOTE: put BOTH contracts under one root so load_contract finds them; the implementer must
    # write both stems into a single out_dir (adjust _contract's out_dir) — see implementer note.
    claim = expression_floor_claim("floor-RUNX1T1", ref=ref_a, gene="RUNX1T1", floor=13.0,
                                   tissue="AML", search_cardinality=1)
    corpus = Corpus(fdr_ledger=FDRLedger(target_fdr=0.05), claims=(claim,))
    # seed cohort-A e-value into evidence_map's source (the claim's own e-value) — the builder reads it.
    base = MaterializationContext(id="M", api_version="v1", data_version="d1")
    ri = build_expr_replication_inputs(corpus, base, bindings={"floor-RUNX1T1": ref_b},
                                       factors_a=("acoh-adult",), factors_b=("bcoh-peds",))
    assert "floor-RUNX1T1" in ri.replications                    # cohort B counted
    assert ri.evidence["floor-RUNX1T1"] > 1.0                    # product (independent -> multiplied)


def test_overlapping_factors_do_not_multiply(tmp_path):
    ...  # same as above but factors_a == factors_b (Jaccard 1) -> ri.evidence unchanged (no *e2),
         # replications still present (tier will cap REPRODUCED downstream).
```

> **Implementer notes:** (1) `build_fusion_expr_contract` writes ONE stem per `out_dir`; for the test both contracts must be loadable by `load_contract` under a single active contract root — write both into the SAME `out_dir` with different `uid_stem`, and wrap the `build_expr_replication_inputs` call in `with _c.using_contract_root(that_dir):`. Adjust the helper accordingly; the load-bearing asserts (B counted, evidence multiplied vs not) stay. (2) The builder reads the claim's cohort-A e-value via `evidence_map(corpus)` (from `.evidence`) — confirm how `evidence_map` derives a claim's e-value (it may need the claim's own single-cohort e-value pre-seeded; mirror how the methyl `test_2e_tiered_independence_e2e.py` seeds it). Read that test before finalizing the test setup.

- [ ] **Step 2: Run to verify it fails** → FAIL (module missing).

- [ ] **Step 3: Implement `src/polymer_claims/expression_floor_replication.py`** (mirror `replication.py` with the 3 adaptations):

```python
"""§2E replication for the expression-floor spine — the expression-floor analog of replication.py
(which is methyl-only). Air-gaps a second cohort with the two independent expression-floor legs; only if
BOTH clear the claim's FLOOR (the reference_leaf QuantityLeaf value) does cohort B count, and only if the
cohorts are error-independent (disjoint shared_cause_factors) are the e-values multiplied. Umbrella/impure."""
from __future__ import annotations

from polymer_grammar import (
    DataHandle, MaterializationContext, Satisfaction, SatisfactionVerdict, cohorts_error_independent,
)
from polymer_protocol.corpus import Corpus

from .claim_detail import _compare
from .contracts import load_contract
from .evidence import _terminal_node, evidence_map
from .expression_floor_adapters import ExpressionFloorMeanAdapter, ExpressionFloorHLAdapter
from .expression_floor_evidence import expression_floor_evalue
from .replication import ReplicationInputs, _rebind

_IMPL = "expression::floor"


def build_expr_replication_inputs(
    corpus: Corpus, base_ctx: MaterializationContext, *,
    bindings: dict[str, str], factors_a: tuple[str, ...], factors_b: tuple[str, ...],
) -> ReplicationInputs:
    if not factors_a or not factors_b:
        raise ValueError("shared_cause_factors must be non-empty for both cohorts (else the §E gate "
                         "is inert and over-credits)")
    evidence = dict(evidence_map(corpus))
    replications: dict[str, tuple[Satisfaction, ...]] = {}
    by_id = {c.id: c for c in corpus.claims}

    for cid, ref_b in bindings.items():
        claim = by_id.get(cid)
        if claim is None:
            continue
        node = _terminal_node(claim)
        if node is None or node.impl != _IMPL:
            continue
        handle = next((i for i in node.inputs if isinstance(i, DataHandle)), None)
        if handle is None:
            continue
        try:
            contract_a = load_contract(handle.ref)
            contract_b = load_contract(ref_b)
        except FileNotFoundError:
            continue
        if contract_b.dimnames_hash == contract_a.dimnames_hash:
            continue  # same cohort -> not a replication

        crit = claim.evaluation_plan.criterion
        if crit.reference_leaf_index is None:
            continue
        floor = claim.leaves[crit.reference_leaf_index].value   # the QuantityLeaf floor (13)

        node_b = _rebind(node, ref_b)
        try:
            v_mean = ExpressionFloorMeanAdapter().execute(node_b, (), base_ctx).value
            v_hl = ExpressionFloorHLAdapter().execute(node_b, (), base_ctx).value
        except (FileNotFoundError, KeyError, ValueError):
            continue
        # both legs must independently clear the FLOOR on cohort B (GE)
        if not (_compare(v_mean, crit.comparator, floor, None) and _compare(v_hl, crit.comparator, floor, None)):
            continue
        if cid not in evidence:
            continue

        e2 = expression_floor_evalue(node_b)
        sat_b = Satisfaction(
            verdict=SatisfactionVerdict.SATISFIED,
            materialization=MaterializationContext(
                id=f"{base_ctx.id}-repl-{contract_b.contract_uid}",
                api_version=base_ctx.api_version, data_version=base_ctx.data_version,
                dimnames_hash=contract_b.dimnames_hash, shared_cause_factors=factors_b))
        replications[cid] = (sat_b,)
        sat_a = Satisfaction(
            verdict=SatisfactionVerdict.SATISFIED,
            materialization=MaterializationContext(
                id=f"{base_ctx.id}-primary-{contract_a.contract_uid}",
                api_version=base_ctx.api_version, data_version=base_ctx.data_version,
                dimnames_hash=contract_a.dimnames_hash, shared_cause_factors=factors_a))
        if cohorts_error_independent((sat_a, sat_b)) is not False:
            evidence[cid] = evidence[cid] * e2

    return ReplicationInputs(replications=replications, evidence=evidence)
```

- [ ] **Step 4: Run to verify it passes** → the replication tests PASS. Then `uv run --project . pytest tests/spine/ -q`.
- [ ] **Step 5: Commit** → `git add src/polymer_claims/expression_floor_replication.py tests/spine/test_expression_floor_replication.py && git commit -m "feat(spine): expression-floor §2E replication builder (reference-leaf floor, product e-value)"`

---

### Task 3: `license_replicated` + the four integrity tests

**Files:**
- Modify: `src/polymer_claims/expression_floor_populate.py` (add `license_replicated`)
- Test: `tests/spine/test_expression_floor_replicated_license.py`

**Interfaces:**
- Produces: `license_replicated(corpus, claims, *, ref_a, ref_b, factors_a, factors_b) -> Corpus`.
- Consumes: Task 2's `build_expr_replication_inputs`; the existing `run_cycle` wiring in `license_batch`.

- [ ] **Step 1: Write the failing tests** (`tests/spine/test_expression_floor_replicated_license.py`), covering all four from the spec: (a) planted two-cohort with disjoint factors → `floor-RUNX1T1` LICENSED at `IndependenceTier.REPLICATED`, ledger `n_tests == 1`; (b) overlapping factors (Jaccard ≥ 0.5) → REPRODUCED (or PENDING if single-cohort e alone < bar), NOT REPLICATED; (c) empty `factors_b` → `license_replicated` raises `ValueError`; (d) the two contracts have distinct `dimnames_hash`. (Model the contract fixtures on Task 2 + `tests/pharmaco/test_pharmaco_license.py`; read `tests/test_2e_tiered_independence_e2e.py` for how the REPLICATED tier is asserted off `result`.)

- [ ] **Step 2: Run to verify it fails** → FAIL.

- [ ] **Step 3: Implement `license_replicated`** in `expression_floor_populate.py` — it runs the per-claim cohort-A cycle (reuse the 2d-ii per-claim isolation), builds cohort-B replication inputs, and threads `evidence`/`replications` into `run_cycle`:

```python
def license_replicated(corpus, claims, *, ref_a, ref_b,
                       factors_a, factors_b):
    """REPLICATED license: cohort A (ref_a) + an error-independent cohort B (ref_b). The product e1*e2
    folds into the single e-LOND slot; the extra cohort-B satisfaction promotes the tier. factors_a/b
    MUST be non-empty and disjoint (else §E is inert / caps). Reuses the per-claim isolation of 2d-ii."""
    from .expression_floor_replication import build_expr_replication_inputs
    if not factors_a or not factors_b:
        raise ValueError("both cohorts need non-empty shared_cause_factors")
    ri = build_expr_replication_inputs(corpus, MaterializationContext(id="M", api_version="v1", data_version="d1"),
                                       bindings={c.id: ref_b for c in claims if _terminal_node(c) is not None},
                                       factors_a=factors_a, factors_b=factors_b)
    # then per-claim run_cycle over ref_a, passing evidence=ri.evidence[cid] and replications=ri.replications.get(cid)
    ...  # mirror license_batch's per-claim loop; set materialization shared_cause_factors=factors_a,
         # evidence={cid: ri.evidence[cid]}, replications={cid: ri.replications[cid]} when present.
```

> **Implementer note:** the cohort-A materialization in the per-claim `run_cycle` must carry `shared_cause_factors=factors_a` so its Satisfaction matches the `sat_a` the replication builder used (consistent §E accounting). Mirror `license_batch`'s per-claim loop exactly; the only additions are `evidence=ri.evidence` and `replications={cid: ri.replications[cid]}` (when present). Read `run_cycle`'s signature for the `replications=` kwarg (`protocol/.../cycle.py`).

- [ ] **Step 4: Run to verify it passes** → all four tests PASS. Then `uv run --project . pytest tests/spine/ tests/pharmaco/test_pharmaco_license.py -q` (no regression).
- [ ] **Step 5: Commit** → `git add src/polymer_claims/expression_floor_populate.py tests/spine/test_expression_floor_replicated_license.py && git commit -m "feat(spine): license_replicated (§2E two-cohort REPLICATED) + integrity tests"`

---

### Task 4: Real run TCGA+TARGET + continuity (CONTROLLER-EXECUTED)

- [ ] **Step 1: Run the real REPLICATED license.** A driver (`data/target_aml_fusion_expr/license_replicated_spine.py`, mirror `license_spine.py`) that licenses `floor-RUNX1T1` across `se:tcga_laml_fusion_expr@1` (A) + `se:target_aml_fusion_expr@1` (B) with disjoint factors (A=`("tcga-laml-cohort","adult-aml-population","tcga-karyotype")`, B=`("target-aml-cohort","pediatric-aml-population","target-karyotype")`). Print e₁ (TCGA), e₂ (TARGET), the product e₁·e₂, the `IndependenceTier`, and the status; run `check_controls` (ACTB must NOT license).
- [ ] **Step 2: Record the outcome (do NOT assert).** LICENSED@REPLICATED if e₁·e₂ ≥ 32.9 (the headline — first licensed synbio claim, cross-cohort replicated); honest PENDING otherwise (record e₁·e₂ vs 32.9).
- [ ] **Step 3: Continuity + memory + writeup.** Update `CONTINUE.md` (2d-iii shipped; the headline result + e₁/e₂/product/tier; the error-independent declaration + shared-method note) and memory. Commit.

---

## Self-review (against the spec)

- **Second-cohort TARGET-AML contract (reuse 2d-i)** → Task 1. ✔
- **Expression-floor replication builder (methyl analog, 3 adaptations: impl guard / floor-from-leaf / expression_floor_evalue)** → Task 2. ✔
- **§E product into ONE e-LOND slot; tier via cohort-B satisfaction** → Task 2 (`cohorts_error_independent` gate + `ReplicationInputs`) + Task 3 (thread into run_cycle). ✔
- **Disjoint non-empty factors guardrail (empty→raise, overlap→cap)** → Task 2 raise + Task 3 tests (b)/(c). ✔
- **Distinct dimnames_hash required** → Task 1 Step 3 assert + Task 3 test (d). ✔
- **Real run, honest outcome** → Task 4. ✔
- **Invariants (grammar/protocol untouched, Corpus 4, one slot, two-stratum)** → Global Constraints; §2E machinery reused, only umbrella-side builder added. ✔
- **Type consistency:** `build_expr_replication_inputs` signature (Task 2) == call in `license_replicated` (Task 3); `ReplicationInputs`/`_rebind` reused from `replication.py`; adapter identities + `expression_floor_evalue` from Tasks 2d-ii. ✔
