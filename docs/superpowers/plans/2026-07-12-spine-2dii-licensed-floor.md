# Phase 2d-ii — licensed expression-floor spine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Mint the first LICENSED synbio claim — "RUNX1-RUNX1T1+ AML clears the 13 TPM RUNX1T1 floor; fusion− does not" — through the real `run_cycle` gate at `IndependenceTier.REPRODUCED`, reusing the pharmaco plumbing.

**Architecture:** Two mechanisms kept separate: the **13 TPM floor** is the leg criterion (`QuantityLeaf(value=13, low=13)` + `reference_leaf_index`), the **fusion+/− discrimination** is a betting e-value (`fusion_neg/CAP` vs `fusion_pos/CAP`). Two independent legs (mean, Hodges-Lehmann) estimate the fusion+ location; both must clear 13 (`both_satisfy_criterion`). The ACTB control proves the split held.

**Tech Stack:** Python 3.12, numpy (umbrella, `[spine]` extra), the existing grammar/protocol kernel + pharmaco precedent. Spec: `docs/superpowers/specs/2026-07-12-spine-2dii-licensed-floor-design.md`.

## Global Constraints

- `grammar/` and `protocol/` stay pure + numpy-free. `Corpus` stays 4. numpy only umbrella-side behind the new `[spine]` extra; the new modules are NOT re-exported from `polymer_claims/__init__.py`.
- Two-stratum: only this recompute licenses; the reported synbio claims stay CONJECTURED. The computed effect (94 TPM) never enters the claim leaf — the leaf carries the **floor (13)**.
- Commit-before-data: FLOOR=13.0, CAP=100.0, NULL_GAP=0.1 are pre-registered constants locked via `commitment_hash`/`register_test` in `preregister`, before `license_batch` reads TPM.
- The e-value's `[0,1]` boundedness is load-bearing for validity — CAP rescales TPM (`evidence.betting_evalue` clips internally).
- Dimension: leaf `dimension=None` and each leg's `ExecValue(value=...)` has `dimension=None` → `_apply_criterion` skips the dimension check and compares floats (`evaluate.py:245-252`).
- Test command: `cd /Users/zbb2/Desktop/polymer-claims && uv run --project . pytest tests/spine/ -q`.

## Precedent to mirror (read these)

- `src/polymer_claims/pharmaco_adapters.py` — split + two adapters + registry + claim factory (Task 1).
- `src/polymer_claims/pharmaco_evidence.py` — the e-value wrapper (Task 2).
- `src/polymer_claims/capabilities.py:37-53,74-89` — `REGION_DELTA_BETA_CELL` (has `level_a`/`level_b`) + `PHARMACO_ASSOC_CELL` + `CAPABILITY_CELLS` (Task 3).
- `src/polymer_claims/pharmaco_populate.py:104-215` — `preregister`/`_evidence_for`/`license_batch`/`check_controls` (Task 4).
- `tests/pharmaco/test_pharmaco_license.py` — the e2e license test to clone (Task 4).

---

### Task 1: Two legs + split + registry + claim factory

**Files:**
- Create: `src/polymer_claims/expression_floor_adapters.py`
- Test: `tests/spine/test_expression_floor_adapters.py`

**Interfaces:**
- Produces: `_expr_split(node) -> (pos: list[float], neg: list[float])` (fusion+ TPM, fusion− TPM); `ExpressionFloorMeanAdapter` (`identity="expr-floor-mean"`, returns `ExecValue(mean(pos))`); `ExpressionFloorHLAdapter` (`identity="expr-floor-hl"`, returns `ExecValue(hodges_lehmann(pos))`); `expression_floor_registry() -> AdapterRegistry`; `expression_floor_oracle_id()`/`expression_floor_oracle_registry()`; `expression_floor_claim(claim_id, *, ref, gene, floor, tissue, level_a="fusion_pos", level_b="fusion_neg", search_cardinality, ...) -> Claim`.
- Consumes: `.methyl_adapters._load_betas`, `.adapter_identity.implementation_hash_for_adapter`, grammar `ExecValue`/`Claim`/`SatisfactionCriterion`/`Comparator`/`GeneOrProtein`/`QuantityLeaf`/`MeasurementContext`/`Status`/`PatternRef`, `.expression_floor_patterns.EXPRESSION_FLOOR` (Task 3 — for the claim's pattern; until Task 3 lands, Task 1's claim factory imports it lazily inside the function).

- [ ] **Step 1: Write the failing test** (`tests/spine/test_expression_floor_adapters.py`) — build a tiny SE-contract with `expr::RUNX1T1`, `Sample_Group ∈ {fusion_pos, fusion_neg}`, exercise both legs + the split. Use the 2d-i builder to make the fixture contract:

```python
from pathlib import Path

import pytest

from polymer_claims import contracts as _c
from polymer_claims.ingest.tcga_laml_fusion_expr import build_fusion_expr_contract


def _mini_contract(tmp_path):
    tpm = {"RUNX1T1": {"p1": 90.0, "p2": 100.0, "n1": 0.0, "n2": 0.1, "n3": 0.2}}
    fusion = {"p1": "fusion_pos", "p2": "fusion_pos", "n1": "fusion_neg", "n2": "fusion_neg", "n3": "fusion_neg"}
    karyo = {k: "" for k in fusion}
    build_fusion_expr_contract(tpm, fusion, karyo, genes=["RUNX1T1"], out_dir=tmp_path)
    _c.clear_contract_cache()
    return "se:tcga_laml_fusion_expr@1"


def test_split_returns_pos_and_neg(tmp_path):
    from polymer_claims.expression_floor_adapters import _expr_split
    from polymer_grammar import OperationNode
    ref = _mini_contract(tmp_path)
    with _c.using_contract_root(tmp_path):
        node = OperationNode(node_id="n", impl="expression::floor",
                             inputs=({"ref": ref},) if False else ({"kind": "data", "ref": ref},),
                             params={"gene": "RUNX1T1", "group_col": "Sample_Group",
                                     "level_a": "fusion_pos", "level_b": "fusion_neg"})
        pos, neg = _expr_split(node)
    assert sorted(pos) == [90.0, 100.0]
    assert sorted(neg) == [0.0, 0.1, 0.2]


def test_mean_leg_returns_fusion_pos_mean(tmp_path):
    from polymer_claims.expression_floor_adapters import ExpressionFloorMeanAdapter, _expr_split  # noqa
    from polymer_grammar import OperationNode
    ref = _mini_contract(tmp_path)
    with _c.using_contract_root(tmp_path):
        node = OperationNode(node_id="n", impl="expression::floor",
                             inputs=({"kind": "data", "ref": ref},),
                             params={"gene": "RUNX1T1", "group_col": "Sample_Group",
                                     "level_a": "fusion_pos", "level_b": "fusion_neg"})
        v = ExpressionFloorMeanAdapter().execute(node, (), None)
    assert v.value == pytest.approx(95.0)   # mean(90,100)


def test_two_legs_have_distinct_owners():
    from polymer_claims.expression_floor_adapters import expression_floor_registry
    reg = expression_floor_registry()
    owners = {c.owner for c in reg.credentials}
    assert len(owners) == 2 and len(reg.credentials) == 2
```

> **Implementer note — the exact `OperationNode.inputs`/`impl` shape:** before writing the impl, open `src/polymer_claims/pharmaco_adapters.py` and `methyl_adapters.py::_load_betas` and MIRROR precisely how `_pharmaco_split` builds/reads the node (the `impl` string, the `inputs` DataHandle shape, and `p = _load_betas(node)` returning `(beta, sample_ids, group_of, p)`). Fix the test's `OperationNode(...)` construction to match the real `_load_betas` contract (the placeholder above may need the real `impl`/`inputs` keys). The load-bearing asserts (split values, mean=95, two owners) do not change.

- [ ] **Step 2: Run to verify it fails** → `uv run --project . pytest tests/spine/test_expression_floor_adapters.py -v` → FAIL (module missing).

- [ ] **Step 3: Implement `src/polymer_claims/expression_floor_adapters.py`** mirroring `pharmaco_adapters.py`. Key differences from pharmaco: (a) split is a **named-categorical** split on `Sample_Group == level_a / level_b` (NOT a within-tissue median split); (b) each leg returns the **fusion+ location** (not a difference); (c) the claim leaf is a `QuantityLeaf` floor with a `reference_leaf_index` criterion.

```python
"""Two INDEPENDENT legs estimate the fusion+ group's expression location over the fusion-expression
SE-contract; the criterion checks each clears the pre-registered floor. Leg A = mean, Leg B =
Hodges-Lehmann pseudo-median (rank-family). Named-categorical split on Sample_Group. Umbrella/impure;
NOT re-exported from __init__ (base import stays numpy-free)."""
from __future__ import annotations

import numpy as np
from polymer_grammar import (
    Comparator, ExecValue, GeneOrProtein, GeneOrProteinIdentifiers, GenerationMode,
    MeasurementBasis, MeasurementContext, OperationNode, PendingReason, Provenance,
    QuantityLeaf, SatisfactionCriterion, Status, StrengthVector, Claim,
)
from polymer_grammar.oracle import ApplicabilityDomain, OracleDossier, ValidationTier
from polymer_protocol import AdapterCredential, AdapterRegistry, OracleRegistry

from .adapter_identity import implementation_hash_for_adapter
from .methyl_adapters import _load_betas

_IMPL = "expression::floor"
_ORACLE_ID = "expression_floor_apparatus"


def _expr_split(node: OperationNode) -> tuple[list[float], list[float]]:
    """(fusion_pos TPMs, fusion_neg TPMs) — named-categorical split on Sample_Group. Drops NaN.
    Raises on empty group."""
    if node.impl != _IMPL:
        raise ValueError(f"{_IMPL} adapter cannot execute impl {node.impl!r}")
    beta, sample_ids, group_of, p = _load_betas(node)   # group_of = col_data[group_col]
    row = f"expr::{p['gene']}"
    if row not in beta:
        raise KeyError(f"missing {row!r} in contract")
    vals = beta[row]
    a_lvl, b_lvl = p["level_a"], p["level_b"]
    pos: list[float] = []
    neg: list[float] = []
    for s in sample_ids:
        v = vals.get(s)
        if v is None or np.isnan(v):
            continue
        g = group_of[s]
        if g == a_lvl:
            pos.append(float(v))
        elif g == b_lvl:
            neg.append(float(v))
    if not pos or not neg:
        raise ValueError("empty fusion split group")
    return pos, neg


def _hodges_lehmann(xs: list[float]) -> float:
    """One-sample HL pseudo-median: median of Walsh averages (x_i + x_j)/2, i<=j."""
    a = np.asarray(xs, dtype=float)
    walsh = ((a[:, None] + a[None, :]) / 2.0)[np.triu_indices(len(a))]
    return float(np.median(walsh))


class ExpressionFloorMeanAdapter:
    """Leg A — mean of fusion_pos TPM. Independent estimator of the group location."""
    identity = "expr-floor-mean"

    def execute(self, node, upstream, ctx) -> ExecValue:
        pos, _ = _expr_split(node)
        return ExecValue(value=float(np.mean(pos)))


class ExpressionFloorHLAdapter:
    """Leg B — Hodges-Lehmann pseudo-median of fusion_pos TPM. Rank-family; independent of leg A."""
    identity = "expr-floor-hl"

    def execute(self, node, upstream, ctx) -> ExecValue:
        pos, _ = _expr_split(node)
        return ExecValue(value=_hodges_lehmann(pos))


def expression_floor_oracle_id() -> str:
    return _ORACLE_ID


def expression_floor_oracle_registry() -> OracleRegistry:
    return OracleRegistry(dossiers=(OracleDossier(
        oracle_id=_ORACLE_ID, validation_tier=ValidationTier.BENCHMARKED,
        applicability_domain=ApplicabilityDomain(subject_kinds=("gene_or_protein",)),
        anchor="tcga-laml-fusion-expr-v1"),))


def expression_floor_registry() -> AdapterRegistry:
    return AdapterRegistry(credentials=(
        AdapterCredential(identity="expr-floor-mean", owner="owner-expr-mean",
                          implementation_hash=implementation_hash_for_adapter(ExpressionFloorMeanAdapter)),
        AdapterCredential(identity="expr-floor-hl", owner="owner-expr-hl",
                          implementation_hash=implementation_hash_for_adapter(ExpressionFloorHLAdapter)),
    ))


def expression_floor_claim(
    claim_id: str, *, ref: str, gene: str, floor: float, tissue: str,
    level_a: str = "fusion_pos", level_b: str = "fusion_neg",
    search_cardinality: int, agent_id: str = "expression-floor-v1",
    prior_cohorts: tuple[str, ...] = (), preregistration_hash: str | None = None,
    strength: StrengthVector | None = None,
) -> Claim:
    """PENDING claim: `gene` expression in the fusion_pos group clears `floor` TPM (a GAP-3 floor
    on a QuantityLeaf) and fusion_neg does not (carried by the discrimination e-value, not this
    leaf). The COMPUTED level never enters the leaf — the leaf carries the pre-registered floor."""
    from polymer_grammar.capability import build_evaluation_plan

    from .expression_floor_patterns import EXPRESSION_FLOOR  # Task 3
    from .capabilities import EXPRESSION_FLOOR_CELL           # Task 3

    plan = build_evaluation_plan(
        EXPRESSION_FLOOR_CELL,
        params={"gene": gene, "group_col": "Sample_Group", "level_a": level_a, "level_b": level_b},
        data_ref=ref,
        criterion=SatisfactionCriterion(comparator=Comparator.GE, reference_leaf_index=0),
        oracle_ref=_ORACLE_ID)
    leaf = QuantityLeaf(value=float(floor), low=float(floor),
                        measurement_basis=MeasurementBasis.DERIVED,
                        formula="fusion_pos_group_expression >= floor_tpm",
                        context=MeasurementContext(tissue=tissue, assay="RNA-seq TPM"))
    subject = GeneOrProtein(id=f"HGNC:{gene}", display=gene, entity_type="gene",
                            identifiers=GeneOrProteinIdentifiers(hgnc=gene, symbol=gene))
    return Claim(
        id=claim_id, title=f"{gene} clears the {floor:g} TPM expression floor in {tissue} ({level_a})",
        pattern=EXPRESSION_FLOOR, leaves=(leaf,),
        status=Status.PENDING, pending_reason=PendingReason.UNTESTED, strength=strength,
        subject=subject, evaluation_plan=plan,
        provenance=Provenance(generated_by=GenerationMode.AGENT_GENERATED, agent_id=agent_id,
                              search_cardinality=int(search_cardinality),
                              preregistration_hash=preregistration_hash, prior_cohorts=prior_cohorts,
                              rationale=f"fusion-driven re-expression floor: {gene} in {tissue}"))
```

> **Implementer notes:** (1) `MeasurementBasis.DERIVED` with a `formula` is required by the grammar for a DERIVED leaf — keep the formula. (2) Confirm the exact grammar import names (`GeneOrProtein`, `GeneOrProteinIdentifiers`, `QuantityLeaf`, `MeasurementContext`) against `pharmaco_adapters.py`'s import block and `synbio/spine.py` (which already imports `QuantityLeaf`/`MeasurementContext`). (3) `SubjectRequirement` kind `"gene_or_protein"` in Task 3's cell must match this subject; if the grammar's `SubjectRequirement` uses a different kind string for a gene, use that and update both sides.

- [ ] **Step 4: Run to verify it passes** → adapters + split + owners tests PASS. (The `expression_floor_claim` is NOT exercised yet — Task 3 lands its pattern/cell; a claim-build test is in Task 3.)

- [ ] **Step 5: Commit** → `git add src/polymer_claims/expression_floor_adapters.py tests/spine/ && git commit -m "feat(spine): two-leg fusion-expression location adapters + registry + claim factory"`

---

### Task 2: The discrimination betting e-value

**Files:**
- Create: `src/polymer_claims/expression_floor_evidence.py`
- Test: `tests/spine/test_expression_floor_evidence.py`

**Interfaces:**
- Produces: `FLOOR=13.0`, `CAP=100.0`, `NULL_GAP=0.1` (module constants); `expression_floor_evalue(node, *, cap=CAP, null_gap=NULL_GAP) -> float`.
- Consumes: `.evidence.betting_evalue`, `.expression_floor_adapters._expr_split`.

- [ ] **Step 1: Write the failing test** (`tests/spine/test_expression_floor_evidence.py`):

```python
import pytest


def test_strong_gap_gives_large_evalue():
    from polymer_claims.expression_floor_evidence import _gap_evalue
    # pos ~ CAP-scaled ~0.9, neg ~0 -> a big, consistent gap -> e-value >> 1
    e = _gap_evalue(pos=[90.0, 95.0, 100.0, 92.0, 88.0, 97.0], neg=[0.0, 0.1, 0.05] * 20)
    assert e > 5.0


def test_zero_gap_gives_evalue_near_one():
    from polymer_claims.expression_floor_evidence import _gap_evalue
    # both groups identical (housekeeping-like) -> no discrimination -> e-value ~ 1
    same = [3000.0, 3100.0, 2900.0] * 10
    e = _gap_evalue(pos=same, neg=same)
    assert e < 2.0
```

- [ ] **Step 2: Run to verify it fails** → FAIL (module missing).

- [ ] **Step 3: Implement `src/polymer_claims/expression_floor_evidence.py`** (mirror `pharmaco_evidence.py`; the e-value tests the between-group gap, TPM rescaled by CAP into [0,1]):

```python
"""The discrimination e-value for the expression-floor spine: a betting e-value
(evidence.betting_evalue) on the between-group gap, fusion+ vs fusion-, TPM rescaled into [0,1] by a
pre-registered CAP (boundedness is load-bearing for validity). This carries the DISCRIMINATION; the
13 TPM FLOOR is carried separately by the leg criterion (do NOT merge them — see the ACTB control)."""
from __future__ import annotations

from polymer_grammar import Comparator, OperationNode

from .evidence import betting_evalue
from .expression_floor_adapters import _expr_split

FLOOR = 13.0     # criterion floor (used by the claim leaf, not here) — pre-registered
CAP = 100.0      # rescaling constant: TPM/CAP into [0,1] (betting_evalue clips) — pre-registered
NULL_GAP = 0.1   # e-value null discrimination margin in [0,1] units — pre-registered


def _gap_evalue(pos: list[float], neg: list[float], *, cap: float = CAP, null_gap: float = NULL_GAP) -> float:
    """betting_evalue tests E[b-a] > null_gap with a,b in [0,1]. a = fusion_neg/cap, b = fusion_pos/cap,
    so a positive shift = fusion+ expresses higher. Bounded by the /cap + internal clip."""
    a = [v / cap for v in neg]
    b = [v / cap for v in pos]
    return betting_evalue(a, b, threshold=null_gap, comparator=Comparator.GT)


def expression_floor_evalue(node: OperationNode, *, cap: float = CAP, null_gap: float = NULL_GAP) -> float:
    pos, neg = _expr_split(node)
    return _gap_evalue(pos, neg, cap=cap, null_gap=null_gap)
```

- [ ] **Step 4: Run to verify it passes** → 2 tests PASS. Then `uv run --project . pytest tests/spine/ -q` (Task-1 tests still green).

- [ ] **Step 5: Commit** → `git add src/polymer_claims/expression_floor_evidence.py tests/spine/test_expression_floor_evidence.py && git commit -m "feat(spine): discrimination betting e-value (gap, CAP-rescaled)"`

---

### Task 3: The pattern + the EXPRESSION_FLOOR_CELL + claim build

**Files:**
- Create: `src/polymer_claims/expression_floor_patterns.py` (register `expression_floor@v1`)
- Modify: `src/polymer_claims/capabilities.py` (add `EXPRESSION_FLOOR_CELL` to the module + `CAPABILITY_CELLS`)
- Test: `tests/spine/test_expression_floor_cell.py`

**Interfaces:**
- Produces: `EXPRESSION_FLOOR` (a `PatternRef` / registered pattern); `EXPRESSION_FLOOR_CELL` (a `CapabilityCell`); both consumed by Task 1's `expression_floor_claim`.

- [ ] **Step 1: Write the failing test** (`tests/spine/test_expression_floor_cell.py`) — the claim builds, and the criterion fires as a bare `≥ floor`:

```python
def test_expression_floor_claim_builds_with_floor_leaf():
    from polymer_claims.expression_floor_adapters import expression_floor_claim
    from polymer_grammar import QuantityLeaf, Status
    c = expression_floor_claim("floor-RUNX1T1", ref="se:tcga_laml_fusion_expr@1",
                               gene="RUNX1T1", floor=13.0, tissue="AML", search_cardinality=1)
    leaf = c.leaves[0]
    assert isinstance(leaf, QuantityLeaf) and leaf.value == 13.0 and leaf.low == 13.0
    assert c.status is Status.PENDING
    assert c.evaluation_plan.criterion.reference_leaf_index == 0

def test_cell_registered_and_reference_leaf_criterion():
    from polymer_claims.capabilities import EXPRESSION_FLOOR_CELL, CAPABILITY_CELLS
    assert EXPRESSION_FLOOR_CELL.criterion_target == "reference_leaf"
    assert EXPRESSION_FLOOR_CELL.claim_leaf_kinds == ("quantity",)
    assert EXPRESSION_FLOOR_CELL.agreement_mode == "both_satisfy_criterion"
    assert CAPABILITY_CELLS.resolve("expression::floor", "v1") is not None

def test_criterion_fires_as_plain_ge(tmp_path):
    # A QuantityLeaf(value=13, dimension=None) + ExecValue(value=x, dimension=None) compares as x>=13.
    from polymer_grammar.evaluate import _apply_criterion, ExecValue, SatisfactionVerdict
    from polymer_grammar import SatisfactionCriterion, Comparator, QuantityLeaf, MeasurementBasis
    leaf = QuantityLeaf(value=13.0, low=13.0, measurement_basis=MeasurementBasis.DERIVED,
                        formula="x>=f")
    crit = SatisfactionCriterion(comparator=Comparator.GE, reference_leaf_index=0)
    assert _apply_criterion(crit, ExecValue(value=94.0), (leaf,)) is SatisfactionVerdict.SATISFIED
    assert _apply_criterion(crit, ExecValue(value=0.02), (leaf,)) is SatisfactionVerdict.REFUTED
```

- [ ] **Step 2: Run to verify it fails** → FAIL (pattern/cell missing).

- [ ] **Step 3: Register the pattern.** Create `src/polymer_claims/expression_floor_patterns.py`, mirroring how `src/polymer_claims/synbio/patterns.py` registers a pattern into the open `pattern.registry` (READ that file first for the exact `Pattern(...)` fields — `estimand`, `null_model`, `scale`, `invariance_group`, `excluded_applications`). Define `EXPRESSION_FLOOR = PatternRef(id="expression_floor", version="v1")` and register a `Pattern` whose estimand is "group expression location clears a floor" with ≥1 `excluded_applications` (e.g. "a between-group difference — that is the e-value, not this pattern").

- [ ] **Step 4: Add the cell** to `src/polymer_claims/capabilities.py` (after `PHARMACO_ASSOC_CELL`, and add to `CAPABILITY_CELLS`). Mirror `REGION_DELTA_BETA_CELL` (it has `level_a`/`level_b`), with the reference-leaf criterion + quantity leaf:

```python
from .expression_floor_patterns import EXPRESSION_FLOOR  # at top with the other imports

EXPRESSION_FLOOR_CELL = CapabilityCell(
    capability_id="expression::floor", capability_version="v1", operation_impl="expression::floor",
    title="group expression clears a floor", pattern=EXPRESSION_FLOOR,
    subject=SubjectRequirement(mode="required", kind="gene_or_protein"),
    param_schema=(_STR(name="gene", codec="string"), _STR(name="group_col", codec="string"),
                  _STR(name="level_a", codec="string"), _STR(name="level_b", codec="string")),
    produced=_Q, allowed_comparators=_ALL_CMP,
    eligible_adapter_identities=("expr-floor-mean", "expr-floor-hl"),
    oracle=OracleRequirement(default_oracle_id="expression_floor_apparatus", required=True),
    data_ref_kind=DataRefKind.SE_CONTRACT, claim_leaf_kinds=("quantity",),
    criterion_target="reference_leaf", agreement_mode="both_satisfy_criterion",
)
```
Then extend `CAPABILITY_CELLS = CapabilityRegistry(cells=(..., PHARMACO_ASSOC_CELL, EXPRESSION_FLOOR_CELL))`.

> **Implementer notes:** (a) verify `SubjectRequirement`'s valid `kind` values (grammar) — use the gene one (likely `"gene_or_protein"`); if different, update the cell AND Task 1's `expression_floor_claim` subject to match. (b) `pattern=EXPRESSION_FLOOR` must equal the claim's pattern (Task 1). (c) This is a PURE additive cell (no numpy) — `capabilities.py` stays grammar-import-only; existing cells' `content_hash`/serialization are unaffected (nothing references the new cell).

- [ ] **Step 5: Run to verify it passes** → 3 tests PASS. Then confirm no regression: `uv run --project . pytest tests/spine/ -q` and `cd grammar && uv run pytest -q` (cell registry is umbrella-side, grammar untouched — should be unaffected; if `capabilities.py` is under grammar, confirm it stays numpy-free).

- [ ] **Step 6: Commit** → `git add src/polymer_claims/expression_floor_patterns.py src/polymer_claims/capabilities.py tests/spine/test_expression_floor_cell.py && git commit -m "feat(spine): expression_floor pattern + EXPRESSION_FLOOR_CELL (reference-leaf floor criterion)"`

---

### Task 4: Populate/license + controls + the e2e + robustness tests + [spine] extra

**Files:**
- Create: `src/polymer_claims/expression_floor_populate.py`
- Modify: `pyproject.toml` (add `[spine]` extra)
- Test: `tests/spine/test_expression_floor_license.py`

**Interfaces:**
- Produces: `preregister`, `license_batch`, `check_controls`, `propose_spine_claims(ref, floor=FLOOR) -> list[Claim]` (builds the RUNX1T1 + ACTB claims).
- Consumes: Tasks 1-3; mirrors `pharmaco_populate.py:104-215`.

- [ ] **Step 1: Write the failing e2e test** (`tests/spine/test_expression_floor_license.py`), cloned from `tests/pharmaco/test_pharmaco_license.py`. Build a synthetic contract (RUNX1T1 planted strong: fusion+ ≫ 13, fusion− ≈ 0; ACTB high in BOTH), preregister, license_batch, and assert the MECHANISM (deterministic regardless of real n=6):

```python
from pathlib import Path

from polymer_claims import contracts as _c
from polymer_claims.ingest.tcga_laml_fusion_expr import build_fusion_expr_contract
from polymer_grammar import FDRLedger, Corpus, Status, IndependenceTier


def _contract(tmp_path):
    pos = {f"p{i}": 80.0 + i for i in range(8)}
    neg = {f"n{i}": 0.0 + 0.01 * i for i in range(40)}
    fusion = {**{k: "fusion_pos" for k in pos}, **{k: "fusion_neg" for k in neg}}
    tpm = {
        "RUNX1T1": {**pos, **neg},
        "ACTB":    {k: 3000.0 for k in fusion},   # high in BOTH -> clears 13 everywhere, no gap
    }
    build_fusion_expr_contract(tpm, fusion, {k: "" for k in fusion},
                               genes=["RUNX1T1", "ACTB"], out_dir=tmp_path)
    _c.clear_contract_cache()
    return "se:tcga_laml_fusion_expr@1"


def test_signal_licenses_reproduced_housekeeping_pending(tmp_path):
    from polymer_claims.expression_floor_populate import preregister, license_batch, check_controls, propose_spine_claims
    ref = _contract(tmp_path)
    with _c.using_contract_root(tmp_path):
        claims = propose_spine_claims(ref)                    # [floor-RUNX1T1, floor-ACTB]
        corpus = preregister(Corpus(fdr_ledger=FDRLedger(target_fdr=0.05)), claims)
        out = license_batch(corpus, claims, ref=ref)
    by = out.by_id()
    assert by["floor-RUNX1T1"].status is Status.LICENSED
    assert by["floor-ACTB"].status is not Status.LICENSED    # clears floor but no discrimination
    rep = check_controls(out, positive="floor-RUNX1T1", negative="floor-ACTB")
    assert rep["ok"] is True


def test_floor_robustness_sweep(tmp_path):
    from polymer_claims.expression_floor_populate import preregister, license_batch, propose_spine_claims
    ref = _contract(tmp_path)
    for floor in (1.0, 5.0, 13.0, 50.0, 90.0):
        with _c.using_contract_root(tmp_path):
            claims = propose_spine_claims(ref, floor=floor)
            corpus = preregister(Corpus(fdr_ledger=FDRLedger(target_fdr=0.05)), claims)
            out = license_batch(corpus, claims, ref=ref)
        assert out.by_id()["floor-RUNX1T1"].status is Status.LICENSED, f"floor={floor} flipped the verdict"
```

- [ ] **Step 2: Run to verify it fails** → FAIL (module missing).

- [ ] **Step 3: Implement `src/polymer_claims/expression_floor_populate.py`** — copy `preregister` and `check_controls` VERBATIM from `pharmaco_populate.py` (they are generic over claims); adapt `_evidence_for`/`license_batch`/add `propose_spine_claims`:

```python
"""Pre-register + license the expression-floor spine through run_cycle. Mirrors pharmaco_populate.py:
copy preregister/check_controls verbatim; swap the adapters/registry/oracle/evidence. Umbrella/impure
([spine] extra); NOT re-exported from __init__."""
from __future__ import annotations

from polymer_grammar import Claim, Comparator, Corpus, FDRLedger
from polymer_grammar.commitment import commitment_hash
from polymer_grammar.fdr import register_test
from polymer_protocol import MaterializationContext, run_cycle
from polymer_protocol.cycle import ...   # match pharmaco_populate's imports for _terminal_node etc.

from .capabilities import CAPABILITY_CELLS
from .contracts import load_contract
from .expression_floor_adapters import (
    ExpressionFloorMeanAdapter, ExpressionFloorHLAdapter, expression_floor_claim,
    expression_floor_oracle_registry, expression_floor_registry,
)
from .expression_floor_evidence import FLOOR, expression_floor_evalue

# preregister(...)  <- copy verbatim from pharmaco_populate.py:104
# check_controls(...) <- copy verbatim from pharmaco_populate.py:184 (already parameterized positive/negative)
# _terminal_node(...) <- copy the helper pharmaco_populate uses (grep it)

def propose_spine_claims(ref: str, *, floor: float = FLOOR) -> list[Claim]:
    return [
        expression_floor_claim("floor-RUNX1T1", ref=ref, gene="RUNX1T1", floor=floor, tissue="AML",
                               search_cardinality=1),
        expression_floor_claim("floor-ACTB", ref=ref, gene="ACTB", floor=floor, tissue="AML",
                               search_cardinality=1),
    ]

def _evidence_for(claims: list[Claim]) -> dict[str, float]:
    out: dict[str, float] = {}
    for c in claims:
        node = _terminal_node(c)
        if node is None:
            continue
        try:
            out[c.id] = expression_floor_evalue(node)
        except (FileNotFoundError, KeyError, ValueError):
            continue
    return out

def license_batch(corpus: Corpus, claims: list[Claim], *, ref: str,
                  shared_cause_factors: tuple[str, ...] = ("tcga-laml",)) -> Corpus:
    # identical structure to pharmaco_populate.license_batch, swapping:
    #   adapters -> (ExpressionFloorMeanAdapter(), ExpressionFloorHLAdapter())
    #   adapter_registry=expression_floor_registry()
    #   oracles=expression_floor_oracle_registry()
    #   evidence=_evidence_for(claims)
    ...
```

> **Implementer note:** open `pharmaco_populate.py` and copy `preregister`, `check_controls`, `_terminal_node`, and the `license_batch` body EXACTLY, changing only the four swaps listed. Do not re-derive them. Keep `shared_cause_factors=("tcga-laml",)` and `FDRLedger(target_fdr=0.05)` (first-test bar 32.9).

- [ ] **Step 4: Add the `[spine]` extra** to `pyproject.toml` (mirror the `[pharmaco]` block but numpy-only):

```toml
spine = ["numpy>=1.26"]
```

- [ ] **Step 5: Run to verify it passes** → `uv run --project . pytest tests/spine/test_expression_floor_license.py -v` → both tests PASS (RUNX1T1 LICENSED, ACTB not; robustness sweep all LICENSED). Then full `uv run --project . pytest tests/spine/ -q`.

- [ ] **Step 6: Commit** → `git add src/polymer_claims/expression_floor_populate.py pyproject.toml tests/spine/test_expression_floor_license.py && git commit -m "feat(spine): preregister/license/controls + e2e license + floor-robustness + [spine] extra"`

---

### Task 5: Real-data run + continuity (CONTROLLER-EXECUTED)

> Run against the REAL `se:tcga_laml_fusion_expr@1` (already committed in `contracts/`). Record the actual e-value + status; an honest PENDING is acceptable. Controller-executed (reads the real contract, reports the outcome).

**Files:**
- Create: `data/tcga_laml_fusion_expr/license_spine.py` (a short driver) + `docs/superpowers/CONTINUE.md` + memory update.

- [ ] **Step 1: Run the real license.** A driver that, against the committed contract root (default), does `propose_spine_claims("se:tcga_laml_fusion_expr@1")` → `preregister` → `license_batch` → prints each claim's status + the e-value + `check_controls`. Print `RUNX1T1: <status> e=<evalue>` and `ACTB: <status> e=<evalue>` and the e-LOND bar 32.9.

- [ ] **Step 2: Record the outcome (do NOT assert).** Whatever the real result — LICENSED@REPRODUCED (if e≥32.9) or honest PENDING — capture it. If LICENSED: the first licensed synbio claim. If PENDING: note it as unearned-at-n=6, not refuted.

- [ ] **Step 3: Continuity + memory.** Update `CONTINUE.md` (2d-ii shipped; the headline result + e-value + status; the two-mechanism design; ACTB control passed; robustness sweep) and a memory note (first licensed synbio claim OR honest-PENDING; the spine machinery is real). Commit.

---

## Self-review (against the spec)

- **Two-mechanism split (floor=criterion via reference_leaf, discrimination=e-value)** → Task 1 (leg location + QuantityLeaf floor) + Task 2 (gap e-value) + Task 3 (reference_leaf cell). ✔
- **ACTB control mandatory** → Task 4 (`propose_spine_claims` includes ACTB; e2e asserts ACTB not licensed; `check_controls`). ✔
- **Pre-registered FLOOR/CAP/NULL_GAP + commit-before-data** → Task 2 constants + Task 4 `preregister` (verbatim, locks `commitment_hash` before license). ✔
- **Robustness sweep** → Task 4 `test_floor_robustness_sweep` (floor ∈ {1,5,13,50,90} all LICENSED). ✔
- **Two independent legs (distinct owners), both_satisfy_criterion** → Task 1 registry + Task 3 cell `agreement_mode`. ✔
- **Dimension-match handled** → leaf `dimension=None` + `ExecValue` `dimension=None`; Task 3 `test_criterion_fires_as_plain_ge`. ✔
- **[spine] numpy-only extra, not re-exported; grammar/protocol numpy-free; Corpus 4; two-stratum** → Global Constraints + Task 4 extra; cell is pure additive. ✔
- **REPRODUCED tier (single cohort)** → Task 4 `shared_cause_factors=("tcga-laml",)` single cohort. ✔
- **Real-data run, honest PENDING ok** → Task 5. ✔
- **Type consistency:** `expression_floor_claim` signature (Task 1) == call sites (Task 4 `propose_spine_claims`); `_expr_split` (Task 1) consumed by Task 2 evidence; `EXPRESSION_FLOOR`/`EXPRESSION_FLOOR_CELL` (Task 3) consumed by Task 1's factory (lazy import); adapter identities `expr-floor-mean`/`expr-floor-hl` consistent across Task 1 registry + Task 3 cell `eligible_adapter_identities`. ✔
