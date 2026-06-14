# §2E Tiered Independence (REPRODUCED / REPLICATED) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended)
> or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax
> for tracking.

**Goal:** Split the single LICENSED standing into two tiers — REPRODUCED (today's single-cohort air-gap)
and REPLICATED (independently reproduced across ≥2 cohorts with distinct datasets) — and let REPLICATED
multiply the two cohorts' e-values into one e-LOND test.

**Architecture:** Additive `independence_tier` field on the grammar `Licensing` (default REPRODUCED, so
every existing license is byte-identical). The second cohort enters umbrella-side via a `replications=`
map threaded into `run_cycle`/`verify_stage` — exactly the pattern CES-3 used for `materializations=` and
Phase 2.1 used for `evidence=`. Umbrella `replication.py` air-gaps a second synthetic cohort and produces
both the extra satisfactions and the product e-value `e₁·e₂`. `verify_stage` appends the satisfactions and
stamps the tier. grammar/protocol stay pure + numpy-free; Corpus = 4; one e-LOND test per claim.

**Tech Stack:** Python 3.12, pydantic v2 (frozen `_Model`), numpy (umbrella only, behind the
non-re-exported `methyl_adapters` seam), `uv` + `pytest` + `ruff`. Spec:
`docs/superpowers/specs/2026-06-14-2e-tiered-independence-design.md`.

## File structure

- `grammar/src/polymer_grammar/licensing.py` — **modify**: add `IndependenceTier` enum, the
  `Licensing.independence_tier` field + a REPLICATED-consistency validator, and the pure
  `independence_tier_of(satisfactions)` helper.
- `grammar/src/polymer_grammar/__init__.py` — **modify**: export `IndependenceTier`, `independence_tier_of`.
- `grammar/tests/test_independence_tier.py` — **create**: grammar-level unit tests.
- `src/polymer_claims/contracts/_make_casectrl_fixture_b.py` — **create**: deterministic generator for the
  2nd synthetic cohort.
- `src/polymer_claims/contracts/epicv2_casectrl_demo_b.json` + `.betas.tsv` — **create** (generated).
- `src/polymer_claims/replication.py` — **create**: `ReplicationInputs` + `build_replication_inputs`.
- `tests/test_replication_inputs.py` — **create**: umbrella unit tests for the second-cohort air-gap +
  product e-value.
- `protocol/src/polymer_protocol/verify.py` — **modify**: `verify_stage(replications=)` + stamp the tier.
- `protocol/src/polymer_protocol/cycle.py` — **modify**: `run_cycle(replications=)` threading.
- `protocol/tests/test_verify_replication.py` — **create**: protocol-level threading/back-compat tests.
- `tests/test_2e_tiered_independence_e2e.py` — **create**: the end-to-end demo (acceptance test).
- `docs/superpowers/CONTINUE.md` — **modify** (final task): mark §2E done, advance NEXT.

---

### Task 1: Grammar — `IndependenceTier` + `Licensing.independence_tier` + `independence_tier_of`

**Files:**
- Modify: `grammar/src/polymer_grammar/licensing.py`
- Modify: `grammar/src/polymer_grammar/__init__.py`
- Test: `grammar/tests/test_independence_tier.py`

- [ ] **Step 1: Write the failing test**

Create `grammar/tests/test_independence_tier.py`:

```python
from __future__ import annotations

import pytest

from polymer_grammar import (
    IndependenceTier,
    LicenseRoute,
    Licensing,
    MaterializationContext,
    RivalSetClosure,
    Satisfaction,
    SatisfactionVerdict,
    independence_tier_of,
)


def _sat(dimnames: str | None, mid: str = "M") -> Satisfaction:
    return Satisfaction(
        verdict=SatisfactionVerdict.SATISFIED,
        materialization=MaterializationContext(
            id=mid, api_version="v1", data_version="d1", dimnames_hash=dimnames
        ),
    )


def test_default_tier_is_reproduced():
    lic = Licensing(
        route=LicenseRoute.SEVERE_TEST,
        satisfactions=(_sat("hA"),),
        rival_set_closure=RivalSetClosure.OPEN_ACKNOWLEDGED,
    )
    assert lic.independence_tier is IndependenceTier.REPRODUCED


def test_tier_of_single_cohort_is_reproduced():
    assert independence_tier_of((_sat("hA"),)) is IndependenceTier.REPRODUCED


def test_tier_of_two_distinct_cohorts_is_replicated():
    assert independence_tier_of((_sat("hA"), _sat("hB", "M2"))) is IndependenceTier.REPLICATED


def test_tier_of_two_same_cohort_is_reproduced():
    assert independence_tier_of((_sat("hA"), _sat("hA", "M2"))) is IndependenceTier.REPRODUCED


def test_tier_of_none_dimnames_is_reproduced():
    # back-compat: pre-CES claims carry dimnames_hash=None -> never REPLICATED
    assert independence_tier_of((_sat(None), _sat(None, "M2"))) is IndependenceTier.REPRODUCED


def test_replicated_field_requires_two_distinct_cohorts():
    with pytest.raises(ValueError, match="distinct dimnames_hash"):
        Licensing(
            route=LicenseRoute.SEVERE_TEST,
            satisfactions=(_sat("hA"), _sat("hA", "M2")),
            rival_set_closure=RivalSetClosure.OPEN_ACKNOWLEDGED,
            independence_tier=IndependenceTier.REPLICATED,
        )


def test_replicated_field_accepts_two_distinct_cohorts():
    lic = Licensing(
        route=LicenseRoute.SEVERE_TEST,
        satisfactions=(_sat("hA"), _sat("hB", "M2")),
        rival_set_closure=RivalSetClosure.OPEN_ACKNOWLEDGED,
        independence_tier=IndependenceTier.REPLICATED,
    )
    assert lic.independence_tier is IndependenceTier.REPLICATED
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd grammar && uv run pytest tests/test_independence_tier.py -q`
Expected: FAIL with `ImportError: cannot import name 'IndependenceTier'`.

- [ ] **Step 3: Add the enum, field, validator, and helper**

In `grammar/src/polymer_grammar/licensing.py`, add the enum after `RivalSetClosure` (after line 54):

```python
class IndependenceTier(str, Enum):
    """The independence standing of a license (orthogonal to LicenseRoute).
    REPRODUCED = the agreeing implementations share the dataset (today's air-gap).
    REPLICATED = independently reproduced across >=2 datasets with distinct dimnames_hash
    (conceptual replication; only this tier permits multiplying the cohorts' e-values)."""

    REPRODUCED = "reproduced"
    REPLICATED = "replicated"


def independence_tier_of(satisfactions: tuple["Satisfaction", ...]) -> IndependenceTier:
    """REPLICATED iff the satisfactions carry >=2 DISTINCT non-None materialization.dimnames_hash
    (distinct cohorts); else REPRODUCED. None dimnames (pre-CES claims) never reach REPLICATED."""
    cohorts = {
        s.materialization.dimnames_hash
        for s in satisfactions
        if s.materialization.dimnames_hash is not None
    }
    return IndependenceTier.REPLICATED if len(cohorts) >= 2 else IndependenceTier.REPRODUCED
```

Add the field to `Licensing` (after the `rivals_considered` line, ~line 61):

```python
    independence_tier: IndependenceTier = IndependenceTier.REPRODUCED
```

Add a validator inside `Licensing` (after `_replication_needs_two_distinct_materializations`):

```python
    @model_validator(mode="after")
    def _replicated_tier_needs_two_distinct_cohorts(self) -> "Licensing":
        if self.independence_tier == IndependenceTier.REPLICATED:
            cohorts = {
                s.materialization.dimnames_hash
                for s in self.satisfactions
                if s.materialization.dimnames_hash is not None
            }
            if len(cohorts) < 2:
                raise ValueError(
                    "independence_tier=replicated requires >=2 satisfactions with "
                    "distinct dimnames_hash (cohorts)"
                )
        return self
```

- [ ] **Step 4: Export the new symbols**

In `grammar/src/polymer_grammar/__init__.py`, find the `from .licensing import (...)` block and add
`IndependenceTier` and `independence_tier_of` to it, and add both names to `__all__` (mirror how
`LicenseRoute` is already listed in both places).

- [ ] **Step 5: Run test to verify it passes**

Run: `cd grammar && uv run pytest tests/test_independence_tier.py -q`
Expected: PASS (7 passed).

- [ ] **Step 6: Confirm no regression + lint**

Run: `cd grammar && uv run pytest -q && uv run ruff check src tests`
Expected: all existing grammar tests still pass (the field is additive with a default), ruff clean.

- [ ] **Step 7: Commit**

```bash
cd /Users/zbb2/Desktop/polymer-claims
git add grammar/src/polymer_grammar/licensing.py grammar/src/polymer_grammar/__init__.py grammar/tests/test_independence_tier.py
git commit -m "feat(grammar): IndependenceTier + Licensing.independence_tier + independence_tier_of (2E)"
```

---

### Task 2: Umbrella — second synthetic cohort fixture (cohort B)

**Files:**
- Create: `src/polymer_claims/contracts/_make_casectrl_fixture_b.py`
- Create (generated): `src/polymer_claims/contracts/epicv2_casectrl_demo_b.json`, `...demo_b.betas.tsv`
- Test: `tests/test_replication_inputs.py` (first test only; the rest land in Task 3)

- [ ] **Step 1: Write the fixture generator**

Create `src/polymer_claims/contracts/_make_casectrl_fixture_b.py` (mirrors `_make_casectrl_fixture.py`,
but DIFFERENT sample ids `T01..T10` → different `dimnames_hash`; SAME probe ids `cg00000001..24` and the
SAME planted +0.20 signal on the first 5 probes, so the same region claim replicates on an independent
cohort):

```python
"""Deterministic SECOND synthetic case/control EPICv2-shaped cohort (§2E replication).

Synthetic VALUES, real STRUCTURE: 24 cg-format probes x 10 samples (T01..T10), an INDEPENDENT cohort
from epicv2_casectrl_demo (different sample ids -> different dimnames_hash). Same signal region (first 5
probes) carries the same planted +0.20 beta shift in level2, so the SAME region claim conceptually
replicates here. No RNG. Synthetic data: the REPLICATED tier is EXERCISED, not earned.
Re-run:  python -m polymer_claims.contracts._make_casectrl_fixture_b
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
        out.append({"sample_id": f"T{j + 1:02d}", "Sample_Group": group,
                    "Age": 45 + (j * 5) % 25, "Sex": "F" if j % 3 == 0 else "M"})
    return out


def _probes() -> list[dict]:
    return [{"feature_id": f"cg{i + 1:08d}", "chr": "chr1", "pos": 1_000_000 + i * 200}
            for i in range(N_FEATURES)]


def _beta(i: int, sample: dict) -> float:
    # a different baseline curve than cohort A (independent cohort), same planted signal shift
    base = 0.28 + ((i * 13 + 7) % 40) / 100.0
    if i in _SIGNAL_PROBES and sample["Sample_Group"] == "level2":
        base += _SHIFT
    return round(min(base, 0.999999), 6)


def build() -> None:
    samples = _samples()
    probes = _probes()
    manifest = {
        "uid": "epicv2_casectrl_demo_b@1",
        "dim": [N_FEATURES, N_SAMPLES],
        "assays": [{"name": "beta", "ref": "epicv2_casectrl_demo_b.betas.tsv"}],
        "col_data": samples,
        "row_data": probes,
        "metadata": {"genome_assembly": "hg38", "array": "EPICv2"},
    }
    (_DIR / "epicv2_casectrl_demo_b.json").write_text(json.dumps(manifest, indent=2) + "\n")

    header = "\t".join(["feature_id"] + [s["sample_id"] for s in samples])
    rows = [header]
    for i, probe in enumerate(probes):
        cells = [probe["feature_id"]] + [f"{_beta(i, s):.6f}" for s in samples]
        rows.append("\t".join(cells))
    (_DIR / "epicv2_casectrl_demo_b.betas.tsv").write_text("\n".join(rows) + "\n")


if __name__ == "__main__":
    build()
```

- [ ] **Step 2: Generate the fixture files**

Run: `cd /Users/zbb2/Desktop/polymer-claims && uv run python -m polymer_claims.contracts._make_casectrl_fixture_b`
Expected: creates `epicv2_casectrl_demo_b.json` and `epicv2_casectrl_demo_b.betas.tsv` in
`src/polymer_claims/contracts/`.

- [ ] **Step 3: Write the failing test (distinct cohort resolves with a distinct dimnames_hash)**

Create `tests/test_replication_inputs.py`:

```python
from __future__ import annotations

from polymer_claims.contracts import load_contract


def test_cohort_b_resolves_with_distinct_dimnames():
    a = load_contract("se:epicv2_casectrl_demo@1")
    b = load_contract("se:epicv2_casectrl_demo_b@1")
    assert b.contract_uid == "epicv2_casectrl_demo_b@1"
    assert b.dimnames_hash != a.dimnames_hash  # different cohort -> different content-address
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/zbb2/Desktop/polymer-claims && uv run --project . pytest tests/test_replication_inputs.py -q`
Expected: PASS (the generated fixture resolves; distinct dimnames_hash).

- [ ] **Step 5: Commit**

```bash
cd /Users/zbb2/Desktop/polymer-claims
git add src/polymer_claims/contracts/_make_casectrl_fixture_b.py src/polymer_claims/contracts/epicv2_casectrl_demo_b.json src/polymer_claims/contracts/epicv2_casectrl_demo_b.betas.tsv tests/test_replication_inputs.py
git commit -m "feat(contracts): 2nd synthetic cohort fixture epicv2_casectrl_demo_b (2E)"
```

---

### Task 3: Umbrella — `replication.py` (second-cohort air-gap + product e-value)

**Files:**
- Create: `src/polymer_claims/replication.py`
- Test: `tests/test_replication_inputs.py` (add tests)

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_replication_inputs.py`:

```python
from polymer_grammar import FDRLedger, MaterializationContext
from polymer_protocol import Corpus

from polymer_claims.evidence import betting_evalue
from polymer_claims.methyl_adapters import _region_group_means, region_delta_beta_claim
from polymer_claims.replication import build_replication_inputs

_BASE = MaterializationContext(id="M", api_version="v1", data_version="d1")
_REF_B = "se:epicv2_casectrl_demo_b@1"


def _corpus(claim):
    return Corpus(claims=(claim,), fdr_ledger=FDRLedger(target_fdr=0.05))


def test_replication_produces_satisfaction_and_product_evalue():
    claim = region_delta_beta_claim("c1")  # cohort A = epicv2_casectrl_demo@1
    corpus = _corpus(claim)
    rep = build_replication_inputs(corpus, _BASE, bindings={"c1": _REF_B})

    # one extra satisfaction, carrying cohort B's dimnames_hash
    assert "c1" in rep.replications
    (sat_b,) = rep.replications["c1"]
    assert sat_b.materialization.dimnames_hash == load_contract(_REF_B).dimnames_hash

    # evidence for c1 is the PRODUCT e1 * e2 (computed independently here)
    node = claim.evaluation_plan.graph.nodes[0]
    comparator = claim.evaluation_plan.criterion.comparator
    a1, b1 = _region_group_means(node)
    e1 = betting_evalue(a1, b1, threshold=0.10, comparator=comparator)
    node_b = node.model_copy(update={"inputs": tuple(
        type(i)(ref=_REF_B) if hasattr(i, "ref") else i for i in node.inputs)})
    a2, b2 = _region_group_means(node_b)
    e2 = betting_evalue(a2, b2, threshold=0.10, comparator=comparator)
    assert rep.evidence["c1"] == e1 * e2


def test_same_cohort_binding_is_not_replication():
    claim = region_delta_beta_claim("c2")  # cohort A = epicv2_casectrl_demo@1
    corpus = _corpus(claim)
    rep = build_replication_inputs(corpus, _BASE, bindings={"c2": "se:epicv2_casectrl_demo@1"})
    assert "c2" not in rep.replications  # same dimnames_hash -> no replication
    # evidence falls back to the single-cohort e-value
    assert "c2" in rep.evidence


def test_no_binding_leaves_evidence_unchanged():
    from polymer_claims.evidence import evidence_map
    claim = region_delta_beta_claim("c3")
    corpus = _corpus(claim)
    rep = build_replication_inputs(corpus, _BASE, bindings={})
    assert rep.replications == {}
    assert rep.evidence == evidence_map(corpus)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/zbb2/Desktop/polymer-claims && uv run --project . pytest tests/test_replication_inputs.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'polymer_claims.replication'`.

- [ ] **Step 3: Implement `replication.py`**

Create `src/polymer_claims/replication.py`:

```python
"""§2E: conceptual replication across an independent cohort.

For a claim bound to a second SE-Contract cohort (different dimnames_hash), AIR-GAP that cohort with the
same two independent methyl legs; only if they AGREE and the agreed value is SATISFIED does the cohort
count as a replication. Returns the extra (cohort-B) Satisfaction to append to the claim's Licensing and
the PRODUCT e-value e1*e2 (valid: independent data -> independent e-values for the shared null). The
grammar/protocol stay ignorant of cohort B — verify receives a finished `replications=` map, mirroring
CES-3 `materializations=` / Phase-2.1 `evidence=`. Umbrella/impure; numpy only via methyl_adapters.
See docs/superpowers/specs/2026-06-14-2e-tiered-independence-design.md.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from polymer_grammar import (
    Comparator,
    DataHandle,
    MaterializationContext,
    Satisfaction,
    SatisfactionVerdict,
)
from polymer_protocol.corpus import Corpus

from .contracts import load_contract
from .evidence import _terminal_node, betting_evalue, evidence_map
from .methyl_adapters import (
    RegionLmCoefAdapter,
    RegionMeanDiffAdapter,
    _IMPL,
    _region_group_means,
)

_AGREE_TOL = 1e-9


@dataclass(frozen=True)
class ReplicationInputs:
    """The umbrella-computed inputs to thread into run_cycle for §2E replication."""

    replications: dict[str, tuple[Satisfaction, ...]] = field(default_factory=dict)
    evidence: dict[str, float] = field(default_factory=dict)


def _satisfied(value: float, comparator: Comparator, threshold: float) -> bool:
    if comparator == Comparator.GT:
        return value > threshold
    if comparator == Comparator.GE:
        return value >= threshold
    if comparator == Comparator.LT:
        return value < threshold
    if comparator == Comparator.LE:
        return value <= threshold
    return False


def _rebind(node, ref_b: str):
    """Same terminal node, pointed at cohort B's DataHandle."""
    new_inputs = tuple(DataHandle(ref=ref_b) if isinstance(i, DataHandle) else i for i in node.inputs)
    return node.model_copy(update={"inputs": new_inputs})


def build_replication_inputs(
    corpus: Corpus,
    base_ctx: MaterializationContext,
    *,
    bindings: dict[str, str],
) -> ReplicationInputs:
    """For each claim id in `bindings` mapped to a cohort-B ref: air-gap cohort B and, if the two legs
    AGREE and the agreed value is SATISFIED and B's dimnames_hash differs from the primary cohort's,
    emit the cohort-B Satisfaction + the product e-value. Claims with no binding keep their single-cohort
    e-value (evidence_map). Impure (reads contracts)."""
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
            dimnames_a = load_contract(handle.ref).dimnames_hash
            dimnames_b = load_contract(ref_b).dimnames_hash
        except FileNotFoundError:
            continue
        if dimnames_b == dimnames_a:
            continue  # same cohort -> not a replication

        node_b = _rebind(node, ref_b)
        try:
            a2, b2 = _region_group_means(node_b)
            v_meandiff = RegionMeanDiffAdapter().execute(node_b, (), base_ctx).value
            v_lmcoef = RegionLmCoefAdapter().execute(node_b, (), base_ctx).value
        except (FileNotFoundError, KeyError, ValueError):
            continue
        if abs(v_meandiff - v_lmcoef) > _AGREE_TOL:
            continue  # cohort B did not air-gap (the two legs disagree)

        crit = claim.evaluation_plan.criterion
        if crit.threshold is None or not _satisfied(v_meandiff, crit.comparator, crit.threshold):
            continue  # cohort B did not show the effect -> no replication

        e2 = betting_evalue(a2, b2, threshold=crit.threshold, comparator=crit.comparator)
        sat_b = Satisfaction(
            verdict=SatisfactionVerdict.SATISFIED,
            materialization=MaterializationContext(
                id=f"{base_ctx.id}-repl-{load_contract(ref_b).contract_uid}",
                api_version=base_ctx.api_version,
                data_version=base_ctx.data_version,
                dimnames_hash=dimnames_b,
            ),
        )
        replications[cid] = (sat_b,)
        evidence[cid] = evidence.get(cid, 1.0) * e2

    return ReplicationInputs(replications=replications, evidence=evidence)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/zbb2/Desktop/polymer-claims && uv run --project . pytest tests/test_replication_inputs.py -q`
Expected: PASS (4 passed).

- [ ] **Step 5: Lint**

Run: `cd /Users/zbb2/Desktop/polymer-claims && uv run --project . ruff check src tests`
Expected: clean.

- [ ] **Step 6: Commit**

```bash
cd /Users/zbb2/Desktop/polymer-claims
git add src/polymer_claims/replication.py tests/test_replication_inputs.py
git commit -m "feat(replication): build_replication_inputs — 2nd-cohort air-gap + product e-value (2E)"
```

---

### Task 4: Protocol — thread `replications=` through verify_stage + run_cycle; stamp the tier

**Files:**
- Modify: `protocol/src/polymer_protocol/verify.py`
- Modify: `protocol/src/polymer_protocol/cycle.py`
- Test: `protocol/tests/test_verify_replication.py`

- [ ] **Step 1: Write the failing test**

Create `protocol/tests/test_verify_replication.py`:

```python
from __future__ import annotations

import inspect

from polymer_protocol import run_cycle
from polymer_protocol.verify import verify_stage


def test_run_cycle_and_verify_stage_accept_replications():
    assert "replications" in inspect.signature(run_cycle).parameters
    assert "replications" in inspect.signature(verify_stage).parameters
```

(The deep end-to-end behavior is asserted in the umbrella acceptance test, Task 5, where the methyl
apparatus is available; protocol has no methyl fixtures, so here we pin only the wiring contract.)

- [ ] **Step 2: Run test to verify it fails**

Run: `cd protocol && uv run pytest tests/test_verify_replication.py -q`
Expected: FAIL (`replications` not in signature).

- [ ] **Step 3: Add the param + tier stamping to `verify_stage`**

In `protocol/src/polymer_protocol/verify.py`:

(a) Add `Satisfaction` and `independence_tier_of` to the existing `from polymer_grammar import (...)` block
(the block that already imports `Licensing`, `LicenseRoute`, `RivalSetClosure`, `Status`, etc.).

(b) Extend the signature (after the `evidence` param, ~line 121):

```python
    evidence: dict[str, float] | None = None,
    replications: dict[str, tuple[Satisfaction, ...]] | None = None,
) -> Corpus:
```

(c) Replace the ordinary-license `Licensing(...)` construction (the block at ~line 179 that sets
`route=LicenseRoute.SEVERE_TEST, satisfactions=(ev.satisfaction,)`) with:

```python
            extra_sats = (replications or {}).get(c.id, ())
            sats = (ev.satisfaction, *extra_sats)
            licensing = Licensing(
                route=LicenseRoute.SEVERE_TEST,
                satisfactions=sats,
                rival_set_closure=RivalSetClosure.OPEN_ACKNOWLEDGED,
                independence_tier=independence_tier_of(sats),
            )
```

Leave the MDL/representation-revision branch (`mdl_licensing`) untouched — it keeps the single
satisfaction and the REPRODUCED default.

- [ ] **Step 4: Add the param + threading to `run_cycle`**

In `protocol/src/polymer_protocol/cycle.py`:

(a) Add `Satisfaction` to the existing `from polymer_grammar import (...)` block (it already imports
`MaterializationContext`).

(b) Add the param after `evidence` (~line 59):

```python
    evidence: dict[str, float] | None = None,
    replications: dict[str, tuple[Satisfaction, ...]] | None = None,
) -> CycleResult:
```

(c) Pass it into the `verify_stage(...)` call (~line 125):

```python
    corpus = verify_stage(
        corpus, scaffolding, records, oracles,
        adapter_registry=adapter_registry, evidence=evidence, replications=replications,
    )
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd protocol && uv run pytest tests/test_verify_replication.py -q`
Expected: PASS.

- [ ] **Step 6: Confirm protocol back-compat + lint**

Run: `cd protocol && uv run pytest -q && uv run ruff check src tests`
Expected: all 356 existing protocol tests still pass (default `replications=None` ⇒ byte-identical;
the minted `Licensing` keeps the REPRODUCED default), ruff clean.

- [ ] **Step 7: Commit**

```bash
cd /Users/zbb2/Desktop/polymer-claims
git add protocol/src/polymer_protocol/verify.py protocol/src/polymer_protocol/cycle.py protocol/tests/test_verify_replication.py
git commit -m "feat(protocol): thread replications= through run_cycle/verify_stage; stamp independence_tier (2E)"
```

---

### Task 5: Umbrella — end-to-end demo (acceptance test)

**Files:**
- Test: `tests/test_2e_tiered_independence_e2e.py`

- [ ] **Step 1: Write the acceptance test**

Create `tests/test_2e_tiered_independence_e2e.py`:

```python
from __future__ import annotations

from polymer_grammar import FDRLedger, IndependenceTier, MaterializationContext, Status
from polymer_protocol import Corpus, run_cycle

from polymer_claims.analysis_profile import profile_oracle_registry
from polymer_claims.evidence import evidence_map
from polymer_claims.materialization import materialization_map
from polymer_claims.methyl_adapters import (
    RegionLmCoefAdapter, RegionMeanDiffAdapter, methyl_independent_registry, region_delta_beta_claim,
)
from polymer_claims.profiles import CANONICAL_EPICV2_V1
from polymer_claims.replication import build_replication_inputs

_ADAPTERS = (RegionMeanDiffAdapter(), RegionLmCoefAdapter())
_BASE = MaterializationContext(id="M", api_version="v1", data_version="d1")
_REF_B = "se:epicv2_casectrl_demo_b@1"


def _corpus(claim):
    return Corpus(claims=(claim,), fdr_ledger=FDRLedger(target_fdr=0.05))


def test_replicated_across_two_cohorts_licenses_at_replicated_tier():
    claim = region_delta_beta_claim("c-repl")  # cohort A = epicv2_casectrl_demo@1, signal region
    corpus = _corpus(claim)
    rep = build_replication_inputs(corpus, _BASE, bindings={"c-repl": _REF_B})

    result = run_cycle(
        corpus, _ADAPTERS, _BASE,
        adapter_registry=methyl_independent_registry(),
        oracles=profile_oracle_registry((CANONICAL_EPICV2_V1, "recomputable_public")),
        materializations=materialization_map(corpus, _BASE),
        evidence=rep.evidence,
        replications=rep.replications,
    )
    c = next(x for x in result.corpus.claims if x.id == "c-repl")
    assert c.status == Status.LICENSED
    assert c.licensing.independence_tier is IndependenceTier.REPLICATED
    # two satisfactions across two distinct cohorts
    cohorts = {s.materialization.dimnames_hash for s in c.licensing.satisfactions}
    assert len(cohorts) == 2
    # ONE e-LOND test/discovery (the product is one test, not two)
    assert result.corpus.fdr_ledger.n_tests == 1
    assert result.corpus.fdr_ledger.n_discoveries == 1


def test_single_cohort_demo_stays_reproduced():
    claim = region_delta_beta_claim("c-solo")  # cohort A only
    corpus = _corpus(claim)
    result = run_cycle(
        corpus, _ADAPTERS, _BASE,
        adapter_registry=methyl_independent_registry(),
        oracles=profile_oracle_registry((CANONICAL_EPICV2_V1, "recomputable_public")),
        materializations=materialization_map(corpus, _BASE),
        evidence=evidence_map(corpus),
    )
    c = next(x for x in result.corpus.claims if x.id == "c-solo")
    assert c.status == Status.LICENSED
    assert c.licensing.independence_tier is IndependenceTier.REPRODUCED
    assert len(c.licensing.satisfactions) == 1


def test_same_cohort_binding_does_not_multiply_or_replicate():
    claim = region_delta_beta_claim("c-same")
    corpus = _corpus(claim)
    rep = build_replication_inputs(corpus, _BASE, bindings={"c-same": "se:epicv2_casectrl_demo@1"})
    result = run_cycle(
        corpus, _ADAPTERS, _BASE,
        adapter_registry=methyl_independent_registry(),
        oracles=profile_oracle_registry((CANONICAL_EPICV2_V1, "recomputable_public")),
        materializations=materialization_map(corpus, _BASE),
        evidence=rep.evidence,
        replications=rep.replications,
    )
    c = next(x for x in result.corpus.claims if x.id == "c-same")
    assert c.licensing.independence_tier is IndependenceTier.REPRODUCED
    assert len(c.licensing.satisfactions) == 1
```

- [ ] **Step 2: Run the acceptance test**

Run: `cd /Users/zbb2/Desktop/polymer-claims && uv run --project . pytest tests/test_2e_tiered_independence_e2e.py -q`
Expected: PASS (3 passed). If `test_replicated_..._licenses` fails because the product e-value does not
clear the e-LOND bar, the cohort fixtures are under-powered — bump the planted signal/sample count in
`_make_casectrl_fixture_b.py` (and regenerate), since both cohorts must individually clear for an honest
replication. Do NOT weaken the bar.

- [ ] **Step 3: Commit**

```bash
cd /Users/zbb2/Desktop/polymer-claims
git add tests/test_2e_tiered_independence_e2e.py
git commit -m "test(2e): end-to-end REPLICATED licensing across two cohorts + REPRODUCED back-compat"
```

---

### Task 6: Full green gate + CONTINUE update

**Files:**
- Modify: `docs/superpowers/CONTINUE.md`

- [ ] **Step 1: Run the full gate**

Run: `cd /Users/zbb2/Desktop/polymer-claims && bash scripts/check-all.sh`
Expected: `ALL GREEN`. New counts: umbrella +~7 (replication + e2e + fixture tests), grammar +7
(independence tier), protocol +1 (wiring). If anything fails, fix before proceeding.

- [ ] **Step 2: Update CONTINUE.md**

In `docs/superpowers/CONTINUE.md`:
- Add to the **Done — checklist** under "Phase 2 — epistemic core" (or a new "§2E" line):
  `✅ §2E tiered independence — REPRODUCED / REPLICATED; product e-value across independent cohorts (one e-LOND test); 2nd synthetic cohort demo.`
- In **▶ NEXT**, mark item 1 (§2E) done and promote items 2–4 (reinstatement, n-DMPs, Procrustes).
- Update the **Current state** test counts to the new totals from Step 1.
- Update the standing caveat about adapters being "reproducibility-independent, not error-independent" to
  note REPLICATED now expresses the cross-cohort tier (the demo's REPLICATED runs on a 2nd **synthetic**
  cohort — still exercised, not earned, until real public data).

- [ ] **Step 3: Commit**

```bash
cd /Users/zbb2/Desktop/polymer-claims
git add docs/superpowers/CONTINUE.md
git commit -m "docs(2e): tiered independence DONE — CONTINUE checklist + NEXT advance"
```

---

## Self-review notes (for the implementer)

- **Spec coverage:** grammar tier (Task 1) · 2nd cohort fixture (Task 2) · `replication_map`/product
  e-value (Task 3) · protocol threading + tier stamp (Task 4) · end-to-end REPLICATED demo + REPRODUCED
  back-compat (Task 5) · green gate + docs (Task 6). Viewer badge + live-node wiring are intentionally
  out of scope (spec "Out of scope").
- **One e-LOND test invariant:** REPLICATED supplies a *different value* (the product `e₁·e₂`) for the
  *same single* test via the existing `evidence=` map — never a second ledger entry. Task 5 asserts
  `n_tests == 1`.
- **Back-compat:** `replications=None` ⇒ byte-identical; `independence_tier` defaults REPRODUCED. Tasks
  1/4 Step 6 assert the existing suites stay green.
- **Purity:** all numpy/IO stays umbrella-side (`replication.py` imports only via the non-re-exported
  `methyl_adapters` seam + `evidence`); grammar/protocol changes are pure. Corpus stays 4.
```
