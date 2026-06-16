# CES-2 — Methylation Δβ Licensing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make one claim license on a value COMPUTED from a methylation matrix — a region Δβ over a bundled EPICv2 SE-Contract, computed by two methodologically-independent adapters under the pinned `CANONICAL_EPICV2_V1` profile-as-apparatus, licensed through `run_cycle` with the apparatus tier capping its strength.

**Architecture:** Umbrella-only, mirroring `src/polymer_claims/exec_adapters.py` (Phase 2a). Reuses CES-1 `load_contract`, CES-0 `CANONICAL_EPICV2_V1`/`profile_oracle_registry`, the #5 `AdapterRegistry` air gap, earned-strength, and `run_cycle`. Grammar/protocol untouched; numpy (already a dep) for the least-squares leg.

**Tech Stack:** Python 3.12, numpy, Pydantic v2, pytest, uv, ruff.

**Spec:** `docs/specs/2026-06-12-ces-2-methylation-licensing-design.md`
**Branch:** `feat/ces-2-methylation-licensing` (already created off `main`).
**Umbrella tests from repo root:** `uv run --project . pytest tests/ -q`

---

## File Structure

| File | Responsibility | Change |
|---|---|---|
| `src/polymer_claims/contracts/_make_casectrl_fixture.py` | deterministic generic case/control fixture generator | Create |
| `src/polymer_claims/contracts/epicv2_casectrl_demo.json` / `.betas.tsv` | the bundled generic SE-Contract (generated) | Create (generated) |
| `src/polymer_claims/methyl_adapters.py` | betas reader + 2 independent region-Δβ adapters + claim builder + registry | Create |
| `tests/test_casectrl_fixture.py` | fixture structural validity | Create |
| `tests/test_methyl_adapters.py` | adapter units (agreement, lstsq==meandiff, raises) | Create |
| `tests/test_methyl_licensing.py` | end-to-end licensing through run_cycle | Create |

`grammar/`, `protocol/`, and the existing fixture are untouched. `methyl_adapters.py` imports numpy but is imported only by the CES-2 tests (not the CLI/serve), so the base `import polymer_claims` stays numpy-free — do NOT re-export it from `src/polymer_claims/__init__.py`.

---

## Task 1: Generic case/control fixture

**Files:**
- Create: `src/polymer_claims/contracts/_make_casectrl_fixture.py`
- Create (generated): `epicv2_casectrl_demo.json`, `epicv2_casectrl_demo.betas.tsv`
- Test: `tests/test_casectrl_fixture.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_casectrl_fixture.py`:

```python
from __future__ import annotations

import json
import re
from pathlib import Path

_DIR = Path(__file__).resolve().parents[1] / "src" / "polymer_claims" / "contracts"
_MANIFEST = _DIR / "epicv2_casectrl_demo.json"
_BETAS = _DIR / "epicv2_casectrl_demo.betas.tsv"


def _manifest() -> dict:
    return json.loads(_MANIFEST.read_text())


def test_fixture_files_exist():
    assert _MANIFEST.is_file() and _BETAS.is_file()


def test_dims_and_groups():
    m = _manifest()
    nf, ns = m["dim"]
    assert nf == len(m["row_data"]) == 24
    assert ns == len(m["col_data"]) == 10
    groups = [c["Sample_Group"] for c in m["col_data"]]
    assert set(groups) == {"level1", "level2"}
    assert groups.count("level1") == groups.count("level2") == 5


def test_probe_format_and_matrix_shape():
    m = _manifest()
    cg = re.compile(r"^cg\d{8}$")
    ids = [r["feature_id"] for r in m["row_data"]]
    assert all(cg.match(x) for x in ids)
    lines = _BETAS.read_text().splitlines()
    assert lines[0].split("\t") == ["feature_id"] + [c["sample_id"] for c in m["col_data"]]
    assert [ln.split("\t")[0] for ln in lines[1:]] == ids  # row order matches manifest
    assert len(lines) - 1 == 24


def test_metadata_epicv2_hg38():
    m = _manifest()
    assert m["metadata"]["genome_assembly"] == "hg38"
    assert m["metadata"]["array"] == "EPICv2"


def test_planted_shift_on_signal_region_only():
    # signal region = first 5 probes; level2 exceeds level1 by ~0.20 there, ~0 elsewhere.
    m = _manifest()
    groups = {c["sample_id"]: c["Sample_Group"] for c in m["col_data"]}
    lines = _BETAS.read_text().splitlines()
    header = lines[0].split("\t")[1:]
    rows = {ln.split("\t")[0]: ln.split("\t")[1:] for ln in lines[1:]}
    ids = [r["feature_id"] for r in m["row_data"]]

    def _delta(probe):
        l1 = [float(v) for sid, v in zip(header, rows[probe]) if groups[sid] == "level1"]
        l2 = [float(v) for sid, v in zip(header, rows[probe]) if groups[sid] == "level2"]
        return sum(l2) / len(l2) - sum(l1) / len(l1)

    for probe in ids[:5]:
        assert round(_delta(probe), 6) == 0.20   # signal
    for probe in ids[5:]:
        assert round(_delta(probe), 6) == 0.0    # negative control
```

- [ ] **Step 2: Run — confirm failure**

Run: `uv run --project . pytest tests/test_casectrl_fixture.py -q` → FAIL (files absent).

- [ ] **Step 3: Write the deterministic generator**

Create `src/polymer_claims/contracts/_make_casectrl_fixture.py`:

```python
"""Deterministic GENERIC case/control EPICv2-shaped methylation fixture (CES-2).

Synthetic VALUES, real STRUCTURE: 24 cg-format probes x 10 samples (5 level1 / 5 level2) on chr1
(hg38). No RNG. The first 5 probes (the SIGNAL REGION) carry a planted +0.20 beta shift in level2;
the rest have no group difference (the negative-control region). Generic case/control fixture.
Re-run:  python -m polymer_claims.contracts._make_casectrl_fixture
"""
from __future__ import annotations

import json
from pathlib import Path

_DIR = Path(__file__).parent
N_FEATURES = 24
N_SAMPLES = 10
_SIGNAL_PROBES = set(range(5))
_SHIFT = 0.20


def _samples() -> list[dict]:
    out = []
    for j in range(N_SAMPLES):
        group = "level1" if j % 2 == 0 else "level2"
        out.append({"sample_id": f"S{j + 1:02d}", "Sample_Group": group,
                    "Age": 40 + (j * 3) % 25, "Sex": "M" if j % 3 == 0 else "F"})
    return out


def _probes() -> list[dict]:
    return [{"feature_id": f"cg{i + 1:08d}", "chr": "chr1", "pos": 1_000_000 + i * 200}
            for i in range(N_FEATURES)]


def _beta(i: int, sample: dict) -> float:
    base = 0.30 + ((i * 11 + 5) % 40) / 100.0   # deterministic in [0.30, 0.69]
    if i in _SIGNAL_PROBES and sample["Sample_Group"] == "level2":
        base += _SHIFT
    return round(min(base, 0.999999), 6)


def build() -> None:
    samples = _samples()
    probes = _probes()
    manifest = {
        "uid": "epicv2_casectrl_demo@1",
        "dim": [N_FEATURES, N_SAMPLES],
        "assays": [{"name": "beta", "ref": "epicv2_casectrl_demo.betas.tsv"}],
        "col_data": samples,
        "row_data": probes,
        "metadata": {"genome_assembly": "hg38", "array": "EPICv2"},
    }
    (_DIR / "epicv2_casectrl_demo.json").write_text(json.dumps(manifest, indent=2) + "\n")

    header = "\t".join(["feature_id"] + [s["sample_id"] for s in samples])
    rows = [header]
    for i, probe in enumerate(probes):
        cells = [probe["feature_id"]] + [f"{_beta(i, s):.6f}" for s in samples]
        rows.append("\t".join(cells))
    (_DIR / "epicv2_casectrl_demo.betas.tsv").write_text("\n".join(rows) + "\n")


if __name__ == "__main__":
    build()
```

- [ ] **Step 4: Generate + verify**

Run: `cd /Users/zbb2/Desktop/polymer-claims && uv run --project . python -m polymer_claims.contracts._make_casectrl_fixture`
Then: `uv run --project . pytest tests/test_casectrl_fixture.py -q` → all PASS; `uv run --project . ruff check src tests` → clean.

- [ ] **Step 5: Commit**

```bash
git add src/polymer_claims/contracts/_make_casectrl_fixture.py \
        src/polymer_claims/contracts/epicv2_casectrl_demo.json \
        src/polymer_claims/contracts/epicv2_casectrl_demo.betas.tsv \
        tests/test_casectrl_fixture.py
git commit -m "feat(umbrella): generic case/control EPICv2 methylation fixture + generator (CES-2)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

## Task 2: Methylation adapters (betas reader + two independent legs)

**Files:**
- Create: `src/polymer_claims/methyl_adapters.py` (reader + adapters this task; claim builder + registry in Task 3)
- Test: `tests/test_methyl_adapters.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_methyl_adapters.py`:

```python
from __future__ import annotations

import pytest
from polymer_grammar import DataHandle, MaterializationContext, MeasurementBasis, OperationNode, ProducedLeafSpec

from polymer_claims.methyl_adapters import RegionLmCoefAdapter, RegionMeanDiffAdapter

_CTX = MaterializationContext(id="M1", api_version="v1", data_version="epicv2_casectrl_demo@1")
_SIGNAL = ("cg00000001", "cg00000002", "cg00000003", "cg00000004", "cg00000005")
_CONTROL = ("cg00000006", "cg00000007", "cg00000008", "cg00000009", "cg00000010")


def _node(probes=_SIGNAL, ref="se:epicv2_casectrl_demo@1"):
    return OperationNode(
        id="n0", impl="methyl::region_delta_beta",
        inputs=(DataHandle(ref=ref),),
        params=(
            ("region_probes", ",".join(probes)),
            ("group_col", "Sample_Group"),
            ("level_a", "level1"),
            ("level_b", "level2"),
        ),
        produces=ProducedLeafSpec(leaf_kind="quantity", measurement_basis=MeasurementBasis.DERIVED),
    )


def test_signal_region_delta_is_planted_shift():
    md = RegionMeanDiffAdapter().execute(_node(), (), _CTX).value
    assert abs(md - 0.20) < 1e-9


def test_two_legs_agree_exactly():
    node = _node()
    md = RegionMeanDiffAdapter().execute(node, (), _CTX).value
    lm = RegionLmCoefAdapter().execute(node, (), _CTX).value
    assert abs(md - lm) < 1e-9   # OLS group coef == two-group mean difference


def test_control_region_delta_is_zero():
    md = RegionMeanDiffAdapter().execute(_node(probes=_CONTROL), (), _CTX).value
    assert abs(md) < 1e-9


def test_identities_distinct():
    assert RegionMeanDiffAdapter().identity == "methyl-meandiff-beta"
    assert RegionLmCoefAdapter().identity == "methyl-lm-coef"
    assert RegionMeanDiffAdapter().identity != RegionLmCoefAdapter().identity


def test_missing_region_probe_raises():
    with pytest.raises(Exception):
        RegionMeanDiffAdapter().execute(_node(probes=("cg99999999",)), (), _CTX)


def test_unsupported_impl_raises():
    bad = OperationNode(id="n0", impl="builtin::const", params=(("value", "1"),),
                        produces=ProducedLeafSpec(leaf_kind="quantity", measurement_basis=MeasurementBasis.DERIVED))
    with pytest.raises(Exception):
        RegionLmCoefAdapter().execute(bad, (), _CTX)
```

- [ ] **Step 2: Run — confirm failure**

Run: `uv run --project . pytest tests/test_methyl_adapters.py -q` → FAIL (`ModuleNotFoundError: polymer_claims.methyl_adapters`).

- [ ] **Step 3: Write the reader + adapters**

Create `src/polymer_claims/methyl_adapters.py`:

```python
"""CES-2: region differential-methylation execution over a content-addressed SE Contract.

Two methodologically-independent legs compute the SAME region Δβ = mean(level_b) − mean(level_a) of
the per-sample region-mean betas: a direct group mean-difference and an OLS group coefficient
(numpy lstsq), which equals the mean difference for a two-group design — so they agree (a real
two-implementation air-gap check) yet are genuinely different estimators. Umbrella/impure (file I/O
via load_contract). Grammar + protocol untouched. NOT re-exported from __init__ (keeps base import
numpy-free). See docs/specs/2026-06-12-ces-2-methylation-licensing-design.md.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from polymer_grammar import DataHandle, ExecValue, OperationNode

from .contracts import load_contract

_IMPL = "methyl::region_delta_beta"


def _region_group_means(node: OperationNode) -> tuple[list[float], list[float]]:
    """Resolve the node's DataHandle to per-sample region-mean betas, split by the two levels.
    Returns (level_a means, level_b means). Raises on bad impl / missing handle / missing probe /
    empty group (the evaluator degrades a raise to a node error)."""
    if node.impl != _IMPL:
        raise ValueError(f"{_IMPL} adapter cannot execute impl {node.impl!r}")
    handle = next((i for i in node.inputs if isinstance(i, DataHandle)), None)
    if handle is None:
        raise ValueError(f"{_IMPL} requires a DataHandle input")
    p = {k: v for k, v in node.params}
    region_probes = [s for s in p["region_probes"].split(",") if s]
    group_col, level_a, level_b = p["group_col"], p["level_a"], p["level_b"]

    se = load_contract(handle.ref)
    betas_path = Path(se.access_methods[0].access_url)
    manifest = json.loads(
        (betas_path.parent / f"{se.contract_uid.split('@')[0]}.json").read_text()
    )
    sample_ids = [c["sample_id"] for c in manifest["col_data"]]
    group_of = {c["sample_id"]: c[group_col] for c in manifest["col_data"]}

    lines = betas_path.read_text().splitlines()
    header = lines[0].split("\t")[1:]  # sample ids in column order
    beta: dict[str, dict[str, float]] = {}
    for ln in lines[1:]:
        cells = ln.split("\t")
        beta[cells[0]] = {sid: float(v) for sid, v in zip(header, cells[1:])}
    for cg in region_probes:
        if cg not in beta:
            raise KeyError(f"region probe {cg!r} not in contract {handle.ref!r}")

    per_sample = {
        sid: sum(beta[cg][sid] for cg in region_probes) / len(region_probes)
        for sid in sample_ids
    }
    a = [per_sample[sid] for sid in sample_ids if group_of[sid] == level_a]
    b = [per_sample[sid] for sid in sample_ids if group_of[sid] == level_b]
    if not a or not b:
        raise ValueError(f"empty group (level_a={len(a)}, level_b={len(b)})")
    return a, b


class RegionMeanDiffAdapter:
    """Independent impl A — direct group mean-difference (level_b − level_a)."""

    identity = "methyl-meandiff-beta"

    def execute(self, node, upstream, ctx) -> ExecValue:
        a, b = _region_group_means(node)
        return ExecValue(value=(sum(b) / len(b)) - (sum(a) / len(a)))


class RegionLmCoefAdapter:
    """Independent impl B — OLS coefficient of region-mean-β on a level_b indicator (numpy lstsq).
    Equals the two-group mean difference exactly, computed by a different estimator."""

    identity = "methyl-lm-coef"

    def execute(self, node, upstream, ctx) -> ExecValue:
        a, b = _region_group_means(node)
        y = np.array(a + b, dtype=float)
        ind = np.array([0.0] * len(a) + [1.0] * len(b))
        X = np.column_stack([np.ones_like(ind), ind])
        coef, *_ = np.linalg.lstsq(X, y, rcond=None)
        return ExecValue(value=float(coef[1]))
```

- [ ] **Step 4: Run tests**

Run: `uv run --project . pytest tests/test_methyl_adapters.py -q && uv run --project . ruff check src tests` → PASS, clean.

- [ ] **Step 5: Commit**

```bash
git add src/polymer_claims/methyl_adapters.py tests/test_methyl_adapters.py
git commit -m "feat(umbrella): two independent region-Δβ methylation adapters (mean-diff + OLS coef)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

## Task 3: Claim builder + independence registry

**Files:**
- Modify: `src/polymer_claims/methyl_adapters.py` (append builder + registry)
- Test: `tests/test_methyl_adapters.py` (append builder tests)

- [ ] **Step 1: Write the failing tests** — append to `tests/test_methyl_adapters.py`:

```python
from polymer_grammar import Comparator, Status
from polymer_claims.methyl_adapters import methyl_independent_registry, region_delta_beta_claim


def test_claim_carries_oracle_ref_subject_and_criterion():
    c = region_delta_beta_claim("c0")
    node = c.evaluation_plan.graph.nodes[0]
    assert node.oracle_ref == "canonical_epicv2_hg38_v1@1"
    assert node.impl == "methyl::region_delta_beta"
    assert c.subject is not None and c.subject.kind == "genomic_region"
    assert c.status == Status.PENDING and c.strength is None
    crit = c.evaluation_plan.criterion
    assert crit.comparator == Comparator.GT and crit.threshold == 0.10


def test_claim_can_omit_subject_for_the_precondition_probe():
    c = region_delta_beta_claim("c-nosub", with_subject=False)
    assert c.subject is None


def test_independent_registry_has_two_distinct_owners():
    reg = methyl_independent_registry()
    owners = {cr.owner for cr in reg.credentials}
    ids = {cr.identity for cr in reg.credentials}
    assert ids == {"methyl-meandiff-beta", "methyl-lm-coef"}
    assert len(owners) == 2
```

- [ ] **Step 2: Run — confirm failure**

Run: `uv run --project . pytest tests/test_methyl_adapters.py -q` → FAIL (ImportError for the new names).

- [ ] **Step 3: Append the builder + registry** to `src/polymer_claims/methyl_adapters.py` (add imports at the top: from `polymer_grammar` also import `CategoricalLeaf, Claim, Comparator, ComputeGraph, EvaluationPlan, GenomicRegion, MeasurementBasis, PatternRef, PendingReason, ProducedLeafSpec, SatisfactionCriterion, Status, StrengthVector`; from `polymer_protocol` import `AdapterCredential, AdapterRegistry`; and `from .analysis_profile import profile_oracle_id`, `from .profiles import CANONICAL_EPICV2_V1`):

```python
# Default signal region of the bundled fixture (first 5 probes, chr1:1,000,000-1,000,800).
_DEFAULT_REGION_PROBES = ("cg00000001", "cg00000002", "cg00000003", "cg00000004", "cg00000005")
_DEFAULT_REGION = ("chr1", 1_000_000, 1_000_800)


def region_delta_beta_claim(
    claim_id: str,
    *,
    ref: str = "se:epicv2_casectrl_demo@1",
    region_probes: tuple[str, ...] = _DEFAULT_REGION_PROBES,
    region: tuple[str, int, int] = _DEFAULT_REGION,
    group_col: str = "Sample_Group",
    level_a: str = "level1",
    level_b: str = "level2",
    comparator: Comparator = Comparator.GT,
    threshold: float = 0.10,
    ontology_term: str = "differential_methylation",
    strength: StrengthVector | None = None,
    with_subject: bool = True,
    oracle_ref: str | None = None,
    title: str = "region differential methylation (level2 - level1)",
) -> Claim:
    """Build a PENDING claim whose plan computes a region Δβ over the bundled SE Contract, binding
    CANONICAL_EPICV2_V1 as the apparatus (oracle_ref). `strength=None` → earned at verify. The
    `genomic_region` subject is REQUIRED for the apparatus domain ({genomic_region, cohort}); pass
    `with_subject=False` only to probe the out-of-domain precondition."""
    if oracle_ref is None:
        oracle_ref = profile_oracle_id(CANONICAL_EPICV2_V1)
    node = OperationNode(
        id="n0",
        impl=_IMPL,
        inputs=(DataHandle(ref=ref),),
        params=(
            ("region_probes", ",".join(region_probes)),
            ("group_col", group_col),
            ("level_a", level_a),
            ("level_b", level_b),
        ),
        oracle_ref=oracle_ref,
        produces=ProducedLeafSpec(leaf_kind="quantity", measurement_basis=MeasurementBasis.DERIVED),
    )
    plan = EvaluationPlan(
        graph=ComputeGraph(nodes=(node,), terminal="n0"),
        criterion=SatisfactionCriterion(comparator=comparator, threshold=threshold),
    )
    subject = None
    if with_subject:
        chrom, start, end = region
        subject = GenomicRegion(assembly="hg38", chrom=chrom, start=start, end=end)
    return Claim(
        id=claim_id,
        title=title,
        pattern=PatternRef(id="adjusted_effect", version="v1"),
        leaves=(CategoricalLeaf(ontology_term=ontology_term),),
        status=Status.PENDING,
        pending_reason=PendingReason.UNTESTED,
        strength=strength,
        subject=subject,
        evaluation_plan=plan,
    )


def methyl_independent_registry() -> AdapterRegistry:
    """Credentials asserting the two legs are genuinely independent (distinct owners + impl hashes),
    so the #5 gate licenses on their agreement."""
    return AdapterRegistry(credentials=(
        AdapterCredential(identity="methyl-meandiff-beta", owner="owner-meandiff", implementation_hash="h-meandiff"),
        AdapterCredential(identity="methyl-lm-coef", owner="owner-lm", implementation_hash="h-lm"),
    ))
```

- [ ] **Step 4: Run tests**

Run: `uv run --project . pytest tests/test_methyl_adapters.py -q && uv run --project . ruff check src tests` → PASS, clean.

- [ ] **Step 5: Commit**

```bash
git add src/polymer_claims/methyl_adapters.py tests/test_methyl_adapters.py
git commit -m "feat(umbrella): region_delta_beta_claim (profile apparatus + genomic_region subject) + registry

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

## Task 4: End-to-end licensing through run_cycle

**Files:**
- Create: `tests/test_methyl_licensing.py`

- [ ] **Step 1: Write the end-to-end tests**

Create `tests/test_methyl_licensing.py`:

```python
from __future__ import annotations

from polymer_grammar import Comparator, FDRLedger, MaterializationContext, StrengthVector
from polymer_protocol import AdapterCredential, AdapterRegistry, Corpus, run_cycle

from polymer_claims.analysis_profile import profile_oracle_registry
from polymer_claims.methyl_adapters import (
    RegionLmCoefAdapter, RegionMeanDiffAdapter, methyl_independent_registry, region_delta_beta_claim,
)
from polymer_claims.profiles import CANONICAL_EPICV2_V1

_ADAPTERS = (RegionMeanDiffAdapter(), RegionLmCoefAdapter())
_CTX = MaterializationContext(id="M1", api_version="v1", data_version="epicv2_casectrl_demo@1")
_CONTROL = ("cg00000006", "cg00000007", "cg00000008", "cg00000009", "cg00000010")
_CONTROL_REGION = ("chr1", 1_001_000, 1_001_800)

# A provisional strength to exercise the apparatus tier cap on a single claim (run alone, cardinality
# 1, so the selective-inference bar doesn't hold it) — mirrors the Phase-2a cap test.
_STR = StrengthVector(magnitude=0.8, certainty=0.7, evidence_against_null=0.8,
                      severity=0.5, world_contact=0.9, explanatory_virtue=0.6)


def _corpus(claim):
    return Corpus(claims=(claim,), fdr_ledger=FDRLedger(target_fdr=0.05))


def _claim(result, cid):
    return next(c for c in result.corpus.claims if c.id == cid)


def _oracles():
    return profile_oracle_registry((CANONICAL_EPICV2_V1, "recomputable_public"))


def test_true_region_claim_licenses_on_computed_delta_beta():
    c = region_delta_beta_claim("c-true", threshold=0.10)  # planted Δβ ~0.20 > 0.10
    result = run_cycle(_corpus(c), _ADAPTERS, _CTX,
                       adapter_registry=methyl_independent_registry(), oracles=_oracles())
    assert _claim(result, "c-true").status.value == "licensed"


def test_negative_control_region_does_not_license():
    c = region_delta_beta_claim("c-ctrl", region_probes=_CONTROL, region=_CONTROL_REGION, threshold=0.10)
    result = run_cycle(_corpus(c), _ADAPTERS, _CTX,
                       adapter_registry=methyl_independent_registry(), oracles=_oracles())
    assert _claim(result, "c-ctrl").status.value != "licensed"  # Δβ ~0 fails > 0.10


def test_apparatus_tier_caps_strength_to_0_6():
    c = region_delta_beta_claim("c-cap", threshold=0.10, strength=_STR)  # has genomic_region subject
    result = run_cycle(_corpus(c), _ADAPTERS, _CTX,
                       adapter_registry=methyl_independent_registry(), oracles=_oracles())
    lic = _claim(result, "c-cap")
    assert lic.status.value == "licensed"
    assert lic.strength.magnitude == 0.6
    assert lic.strength.world_contact == 0.6
    assert lic.strength.evidence_against_null == 0.6


def test_air_gap_holds_non_independent_pair_pending():
    c = region_delta_beta_claim("c-dep", threshold=0.10)
    same_owner = AdapterRegistry(credentials=(
        AdapterCredential(identity="methyl-meandiff-beta", owner="same", implementation_hash="h1"),
        AdapterCredential(identity="methyl-lm-coef", owner="same", implementation_hash="h2"),
    ))
    result = run_cycle(_corpus(c), _ADAPTERS, _CTX, adapter_registry=same_owner, oracles=_oracles())
    assert _claim(result, "c-dep").status.value == "pending"


def test_subjectless_claim_resolves_out_of_domain_to_zero_strength():
    # without a genomic_region subject the apparatus domain ({genomic_region, cohort}) is out-of-domain
    # -> UNVALIDATED -> empirical strength capped to 0.0 (documents why the subject is required).
    c = region_delta_beta_claim("c-nosub", threshold=0.10, strength=_STR, with_subject=False)
    result = run_cycle(_corpus(c), _ADAPTERS, _CTX,
                       adapter_registry=methyl_independent_registry(), oracles=_oracles())
    lic = _claim(result, "c-nosub")
    assert lic.strength.magnitude == 0.0
```

- [ ] **Step 2: Run**

Run: `uv run --project . pytest tests/test_methyl_licensing.py -q`
Expected: all PASS. If `test_apparatus_tier_caps_strength_to_0_6` or the subjectless test fail on exact axis values, print `lic.strength` and reconcile against the Phase-2a analog `tests/test_exec_adapters.py::test_benchmarked_oracle_caps_goodness_axes_to_0_6` (same cap mechanic). If `test_true_region_claim_licenses` fails, print the executed value (it should be ~0.20) — a wrong value means the reader selected the wrong probes/groups, not a licensing bug. Do NOT weaken an assertion to force a pass; if a result is genuinely off, report it.

- [ ] **Step 3: Run ruff + commit**

```bash
uv run --project . ruff check src tests
git add tests/test_methyl_licensing.py
git commit -m "test(umbrella): CES-2 end-to-end — claim licenses on computed methylation Δβ + tier cap + air gap

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

## Task 5: Full verification + docs

**Files:** Modify `docs/superpowers/CONTINUE.md`, `docs/superpowers/roadmaps/2026-06-11-credibility-arc-roadmap.md`.

- [ ] **Step 1: Full verification**

Run:
```bash
uv run --project . pytest tests/ -q && uv run --project . ruff check src tests
cd /Users/zbb2/Desktop/polymer-claims && bash scripts/check-all.sh
```
Expected: all umbrella tests green; ruff clean; `check-all.sh` → `ALL GREEN` (confirms grammar/protocol/viewer untouched — CES-2 is umbrella-only). If check-all fails outside the umbrella, STOP and report BLOCKED.

- [ ] **Step 2: Confirm numpy containment**

Run: `uv run --project . python -c "import sys, polymer_claims; assert not any('numpy' in m for m in sys.modules), 'numpy leaked into base import'; print('base import numpy-free OK')"`
Expected: prints OK (methyl_adapters is not imported by the base package).

- [ ] **Step 3: Docs**

Add a dated `✅ CES-2 DONE` entry near the top of `docs/superpowers/CONTINUE.md` (do NOT alter existing entries) recording: the first claim to license on a COMPUTED methylation Δβ; the generic case/control fixture + `load_contract` reuse; the two methodologically-independent legs (mean-diff vs OLS coef) and the real air gap; `region_delta_beta_claim` binding `CANONICAL_EPICV2_V1` as apparatus + the required `genomic_region` subject; the BENCHMARKED 0.6 tier cap; the synthetic-data honesty caveat (tier exercised, not earned — real public data deferred); umbrella-only, no grammar/protocol change; final green counts. Update the NEXT ACTION line to **CES-3** (record `dimnames_hash`/`profile_hash`/`semantic_run_id` on MaterializationContext through run_cycle + drift wiring). Mark CES-2 done in the roadmap §1b.

- [ ] **Step 4: Commit**

```bash
git add docs/superpowers/CONTINUE.md docs/superpowers/roadmaps/2026-06-11-credibility-arc-roadmap.md
git commit -m "docs(ces-2): methylation Δβ licensing done — CONTINUE + roadmap; NEXT = CES-3

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

## Self-Review

**Spec coverage:**
- §2 generic fixture (case/control, planted signal region) → Task 1. ✓
- §3 betas reader + two independent legs (mean-diff + OLS coef, same value/different method) → Task 2. ✓
- §4 `region_delta_beta_claim` (oracle_ref, GenomicRegion subject, criterion, strength=None) → Task 3. ✓
- §5 registries (`methyl_independent_registry` + `profile_oracle_registry`) → Tasks 3, 4. ✓
- §6 tests: licenses-on-computed (4.1), tier-cap-0.6 (4.3), air-gap-bites (4.4), negative-control (4.2), subject-precondition (4.5), adapter units (2) → Tasks 2, 4. ✓
- §7 fences (static, region-Δβ-only, synthetic caveat, no grammar/protocol change) → no task adds serve/n-DMPs; Task 5 step 2 confirms numpy containment; check-all confirms grammar/protocol untouched. ✓

**Placeholder scan:** none — every step has complete code and exact commands. The only "if it fails" guidance (Task 4 step 2) points at the Phase-2a analog for reconciliation, with an explicit no-fudge instruction.

**Type consistency:** `region_delta_beta_claim(...)` signature, the adapter `identity` strings (`methyl-meandiff-beta`/`methyl-lm-coef`), `_IMPL="methyl::region_delta_beta"`, the param keys (`region_probes`/`group_col`/`level_a`/`level_b`), the fixture ref (`se:epicv2_casectrl_demo@1`), and the oracle_ref (`canonical_epicv2_hg38_v1@1`) are identical across Tasks 1-4 and their tests. `run_cycle(corpus, adapters, ctx, adapter_registry=, oracles=)` matches the Phase-2a call signature verified in `tests/test_exec_adapters.py`.
