# n-DMPs-at-FDR Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended)
> or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax
> for tracking.

**Goal:** Add a second methylation reduction — the count of differentially-methylated probes (DMPs)
passing a per-probe significance threshold — that licenses on its own count-enrichment e-value.

**Architecture:** Umbrella-only (grammar/protocol untouched, like CES-2). A new one-sample betting
e-value (`count_enrichment_evalue`) in `evidence.py`; a new `methyl::n_dmps` apparatus in a new
`methyl_ndmp.py` (two independent per-probe-t legs that agree on the integer count → air-gap), reusing a
`_load_betas` helper extracted from `methyl_adapters.py`; wired through the existing
`evidence=`/earned-strength/air-gap/e-LOND verify path.

**Tech Stack:** Python 3.12, numpy (umbrella only, behind the non-re-exported methyl seam), `math`
(pure-Python Student-t p-value via the incomplete beta), `uv` + `pytest` + `ruff`. Spec:
`docs/superpowers/specs/2026-06-14-n-dmps-at-fdr-design.md`.

## File structure

- `src/polymer_claims/evidence.py` — **modify**: `count_enrichment_evalue` (+ `_capital_onesample`); the
  `methyl::n_dmps` branch in `evidence_map`.
- `src/polymer_claims/methyl_adapters.py` — **modify**: extract `_load_betas` (refactor `_region_group_means`
  to use it; region path stays byte-identical).
- `src/polymer_claims/methyl_ndmp.py` — **create**: Student-t numerics (incomplete beta), per-probe
  p-values (two independent impls), `_n_dmps`, `dmp_indicators`, the two leg adapters, `n_dmps_claim`,
  `ndmp_independent_registry`.
- `tests/test_count_enrichment_evalue.py`, `tests/test_methyl_ndmp.py`, `tests/test_n_dmps_e2e.py` —
  **create**.
- `docs/superpowers/CONTINUE.md` — **modify** (final task).

---

### Task 1: `count_enrichment_evalue` — the one-sample betting e-value

**Files:**
- Modify: `src/polymer_claims/evidence.py`
- Test: `tests/test_count_enrichment_evalue.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_count_enrichment_evalue.py`:

```python
from __future__ import annotations

from polymer_claims.evidence import count_enrichment_evalue


def test_empty_is_one():
    assert count_enrichment_evalue([], p0=0.05) == 1.0


def test_no_enrichment_is_one():
    # every probe null (X=0 < p0): GRAPA bets nothing, e == 1.0 exactly
    assert count_enrichment_evalue([0] * 20, p0=0.05) == 1.0


def test_mild_enrichment_above_one():
    e = count_enrichment_evalue([1] * 5 + [0] * 19, p0=0.05)  # 5/24 >> 0.05
    assert e > 1.5


def test_strong_enrichment_clears_bar():
    e = count_enrichment_evalue([1] * 12 + [0] * 12, p0=0.05)  # 12/24, huge enrichment
    assert e > 100.0


def test_monotone_in_count():
    lo = count_enrichment_evalue([1] * 3 + [0] * 21, p0=0.05)
    hi = count_enrichment_evalue([1] * 8 + [0] * 16, p0=0.05)
    assert hi > lo


def test_deterministic():
    seq = [1, 0, 1, 0, 0] * 4
    assert count_enrichment_evalue(seq, p0=0.05) == count_enrichment_evalue(seq, p0=0.05)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/zbb2/Desktop/polymer-claims && uv run --project . pytest tests/test_count_enrichment_evalue.py -q`
Expected: FAIL with `ImportError: cannot import name 'count_enrichment_evalue'`.

- [ ] **Step 3: Implement the e-value**

In `src/polymer_claims/evidence.py`, add (the module already imports `numpy as np` and defines `_C` and
`_SEEDS`):

```python
def _capital_onesample(x: np.ndarray, p0: float, seed: int) -> float:
    """One betting capital process e = prod_i (1 + lam_i * W_i) for H0: E[X] <= p0 over X in {0,1}.
    W_i = X_i - p0 (so E[W] <= 0 under H0); lam_i is the predictable (PAST-ONLY) GRAPA plug-in, floored
    at 0 (one-sided) and capped so every factor stays positive (the most negative W is -p0)."""
    rng = np.random.default_rng(seed)
    n = len(x)
    W = (x - p0)[rng.permutation(n)]
    lam_max = _C / p0  # positivity: 1 + lam*(-p0) > 0 needs lam < 1/p0; _C<1 keeps factors >= 1-_C
    e, s, s2, cnt = 1.0, 0.0, 0.0, 0
    for i in range(n):
        if cnt > 0:
            mu = s / cnt
            var = max(s2 / cnt - mu * mu, 0.0)
        else:
            mu, var = 0.0, 0.25
        denom = var + mu * mu
        lam = mu / denom if denom > 0.0 else 0.0
        lam = min(max(lam, 0.0), lam_max)
        e *= 1.0 + lam * float(W[i])
        s += float(W[i])
        s2 += float(W[i]) ** 2
        cnt += 1
    return e


def count_enrichment_evalue(indicators, *, p0: float) -> float:
    """Valid e-value for H0: the per-probe DMP-rate <= p0, over Bernoulli DMP-indicators X in {0,1}.
    A one-sample WSR betting / Ville e-value (same family as betting_evalue, on bounded data): tests
    whether the observed DMP count is ENRICHED beyond the chance rate p0 (= the per-probe alpha).
    Seed-averaged -> deterministic. Empty -> 1.0."""
    x = np.asarray(indicators, dtype=float)
    if x.size == 0:
        return 1.0
    es = [_capital_onesample(x, p0, s) for s in _SEEDS]
    return float(sum(es) / len(es))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/zbb2/Desktop/polymer-claims && uv run --project . pytest tests/test_count_enrichment_evalue.py -q`
Expected: PASS (6 passed).

- [ ] **Step 5: Lint**

Run: `cd /Users/zbb2/Desktop/polymer-claims && uv run --project . ruff check src tests`
Expected: clean.

- [ ] **Step 6: Commit**

```bash
cd /Users/zbb2/Desktop/polymer-claims
git add src/polymer_claims/evidence.py tests/test_count_enrichment_evalue.py
git commit -m "feat(evidence): count_enrichment_evalue — one-sample betting e-value for DMP enrichment (n-DMPs)"
```

---

### Task 2: Extract `_load_betas` from `methyl_adapters.py`

**Files:**
- Modify: `src/polymer_claims/methyl_adapters.py`
- Test: (existing `tests/test_methyl_adapters.py` + `tests/test_evidence_map.py` must stay green — no new test needed; the refactor is behavior-preserving.)

- [ ] **Step 1: Refactor — extract the I/O, keep `_region_group_means` output identical**

In `src/polymer_claims/methyl_adapters.py`, add a `_load_betas` helper and rewrite `_region_group_means`
to call it. Replace the current `_region_group_means` (lines ~43-82) with:

```python
def _load_betas(node: OperationNode):
    """Resolve the node's DataHandle to the per-probe-per-sample beta matrix + sample grouping + params.
    Returns (beta: dict[probe -> dict[sample_id -> float]], sample_ids: list[str],
    group_of: dict[sample_id -> group], params: dict[str, str]). Shared by region-Δβ and n-DMPs.
    Raises ValueError on a missing DataHandle (the evaluator degrades a raise to a node error)."""
    handle = next((i for i in node.inputs if isinstance(i, DataHandle)), None)
    if handle is None:
        raise ValueError(f"{node.impl} requires a DataHandle input")
    p = {k: v for k, v in node.params}
    se = load_contract(handle.ref)
    betas_path = Path(se.access_methods[0].access_url)
    manifest = json.loads(
        (betas_path.parent / f"{se.contract_uid.split('@')[0]}.json").read_text()
    )
    group_col = p["group_col"]
    sample_ids = [c["sample_id"] for c in manifest["col_data"]]
    group_of = {c["sample_id"]: c[group_col] for c in manifest["col_data"]}
    lines = betas_path.read_text().splitlines()
    header = lines[0].split("\t")[1:]
    beta: dict[str, dict[str, float]] = {}
    for ln in lines[1:]:
        cells = ln.split("\t")
        beta[cells[0]] = {sid: float(v) for sid, v in zip(header, cells[1:])}
    return beta, sample_ids, group_of, p


def _region_group_means(node: OperationNode) -> tuple[list[float], list[float]]:
    """Resolve the node's DataHandle to per-sample region-mean betas, split by the two levels.
    Returns (level_a means, level_b means). Raises on bad impl / missing probe / empty group."""
    if node.impl != _IMPL:
        raise ValueError(f"{_IMPL} adapter cannot execute impl {node.impl!r}")
    beta, sample_ids, group_of, p = _load_betas(node)
    region_probes = [s for s in p["region_probes"].split(",") if s]
    level_a, level_b = p["level_a"], p["level_b"]
    for cg in region_probes:
        if cg not in beta:
            raise KeyError(f"region probe {cg!r} not in contract")
    per_sample = {
        sid: sum(beta[cg][sid] for cg in region_probes) / len(region_probes)
        for sid in sample_ids
    }
    a = [per_sample[sid] for sid in sample_ids if group_of[sid] == level_a]
    b = [per_sample[sid] for sid in sample_ids if group_of[sid] == level_b]
    if not a or not b:
        raise ValueError(f"empty group (level_a={len(a)}, level_b={len(b)})")
    return a, b
```

- [ ] **Step 2: Run the methyl + evidence suites to confirm byte-identical behavior**

Run: `cd /Users/zbb2/Desktop/polymer-claims && uv run --project . pytest tests/test_methyl_adapters.py tests/test_evidence_map.py tests/test_methyl_licensing.py -q`
Expected: PASS (all existing region-Δβ tests unaffected — `_region_group_means` returns the same values).

- [ ] **Step 3: Lint + commit**

Run: `cd /Users/zbb2/Desktop/polymer-claims && uv run --project . ruff check src tests`
```bash
cd /Users/zbb2/Desktop/polymer-claims
git add src/polymer_claims/methyl_adapters.py
git commit -m "refactor(methyl): extract _load_betas (shared I/O for region-Δβ + n-DMPs)"
```

---

### Task 3: `methyl_ndmp.py` — Student-t numerics + per-probe p-values + count

**Files:**
- Create: `src/polymer_claims/methyl_ndmp.py`
- Test: `tests/test_methyl_ndmp.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_methyl_ndmp.py`:

```python
from __future__ import annotations

from polymer_claims.methyl_ndmp import (
    _n_dmps,
    _t_two_sided_p,
    dmp_indicators,
)


def test_t_pvalue_zero_t_is_one():
    assert abs(_t_two_sided_p(0.0, 98) - 1.0) < 1e-9


def test_t_pvalue_large_t_is_tiny():
    assert _t_two_sided_p(30.0, 98) < 1e-6


def test_t_pvalue_known_value():
    # t=2.0, df=98 two-sided p ~ 0.048 (close to the normal 0.0455)
    p = _t_two_sided_p(2.0, 98)
    assert 0.04 < p < 0.055


def test_n_dmps_counts_below_alpha():
    pvals = {"a": 0.001, "b": 0.04, "c": 0.20, "d": 0.049}
    assert _n_dmps(pvals, 0.05) == 3  # a, b, d


def test_dmp_indicators_on_powered_fixture():
    # n-DMP node over all 24 powered probes; signal probes (1-10) should be DMPs, controls mostly not.
    probes = tuple(f"cg{i:08d}" for i in range(1, 25))
    node = _ndmp_node(probes)
    ind = dmp_indicators(node)
    assert len(ind) == 24
    assert sum(ind) >= 8  # ~10 true DMPs (5 strong + 5 weak), few/no control false positives
    assert set(ind) <= {0, 1}


def _ndmp_node(probes):
    # build an OperationNode with impl methyl::n_dmps via the (Task-4) builder's node shape;
    # until n_dmps_claim exists, construct the node inline mirroring region_delta_beta_claim.
    from polymer_grammar import DataHandle, MeasurementBasis, OperationNode, ProducedLeafSpec
    return OperationNode(
        id="n0", impl="methyl::n_dmps",
        inputs=(DataHandle(ref="se:epicv2_casectrl_powered@1"),),
        params=(("probes", ",".join(probes)), ("group_col", "Sample_Group"),
                ("level_a", "level1"), ("level_b", "level2"), ("alpha", "0.05")),
        produces=ProducedLeafSpec(leaf_kind="quantity", measurement_basis=MeasurementBasis.DERIVED),
    )
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/zbb2/Desktop/polymer-claims && uv run --project . pytest tests/test_methyl_ndmp.py -q`
Expected: FAIL (`ModuleNotFoundError: No module named 'polymer_claims.methyl_ndmp'`).

- [ ] **Step 3: Create `methyl_ndmp.py` with the numerics + per-probe p-values (manual pooled-t) + count + indicators**

Create `src/polymer_claims/methyl_ndmp.py`:

```python
"""n-DMPs-at-FDR: the count of differentially-methylated probes (a probe is a DMP iff its per-probe
two-group pooled t-test p-value < alpha), as a second scalar reduction alongside region-Δβ. Two
independent legs compute the per-probe t two ways (manual pooled-t vs OLS-coef t) and AGREE on the
integer count -> air-gap. Umbrella/impure (reads the contract via _load_betas). NOT re-exported from
__init__ (base import stays numpy-free). The count's e-value (count_enrichment_evalue) lives in
evidence.py. See docs/superpowers/specs/2026-06-14-n-dmps-at-fdr-design.md.
"""
from __future__ import annotations

import math

import numpy as np
from polymer_grammar import (
    CategoricalLeaf,
    Claim,
    Comparator,
    ComputeGraph,
    DataHandle,
    EvaluationPlan,
    ExecValue,
    GenomicRegion,
    MeasurementBasis,
    OperationNode,
    PatternRef,
    PendingReason,
    ProducedLeafSpec,
    SatisfactionCriterion,
    Status,
    StrengthVector,
)
from polymer_protocol import AdapterCredential, AdapterRegistry

from .analysis_profile import profile_oracle_id
from .contracts import load_contract
from .methyl_adapters import _load_betas
from .profiles import CANONICAL_EPICV2_V1

_NDMP_IMPL = "methyl::n_dmps"


# --- Student-t two-sided p-value via the regularized incomplete beta (pure-Python, no scipy) ---

def _betacf(a: float, b: float, x: float) -> float:
    MAXIT, EPS, FPMIN = 300, 3e-16, 1e-300
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < FPMIN:
        d = FPMIN
    d = 1.0 / d
    h = d
    for m in range(1, MAXIT + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < FPMIN:
            d = FPMIN
        c = 1.0 + aa / c
        if abs(c) < FPMIN:
            c = FPMIN
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < FPMIN:
            d = FPMIN
        c = 1.0 + aa / c
        if abs(c) < FPMIN:
            c = FPMIN
        d = 1.0 / d
        de = d * c
        h *= de
        if abs(de - 1.0) < EPS:
            break
    return h


def _betai(a: float, b: float, x: float) -> float:
    """Regularized incomplete beta I_x(a, b)."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    lbeta = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
    bt = math.exp(lbeta + a * math.log(x) + b * math.log(1.0 - x))
    if x < (a + 1.0) / (a + b + 2.0):
        return bt * _betacf(a, b, x) / a
    return 1.0 - bt * _betacf(b, a, 1.0 - x) / b


def _t_two_sided_p(t: float, df: int) -> float:
    """Two-sided Student-t p-value = I_{df/(df+t^2)}(df/2, 1/2). t=0 -> 1.0; |t|->inf -> 0.0."""
    if df <= 0:
        raise ValueError("df must be positive")
    x = df / (df + t * t)
    return _betai(df / 2.0, 0.5, x)


# --- per-probe two-group test (two independent implementations) ---

def _split(beta_row: dict[str, float], sample_ids, group_of, level_a, level_b):
    a = np.array([beta_row[s] for s in sample_ids if group_of[s] == level_a], dtype=float)
    b = np.array([beta_row[s] for s in sample_ids if group_of[s] == level_b], dtype=float)
    if len(a) < 2 or len(b) < 2:
        raise ValueError("need >=2 samples per group for a t-test")
    return a, b


def _pooled_t(a: np.ndarray, b: np.ndarray) -> tuple[float, int]:
    """Manual pooled (equal-variance) two-sample t-statistic + df. Leg A."""
    na, nb = len(a), len(b)
    df = na + nb - 2
    sp2 = ((a.var(ddof=1) * (na - 1)) + (b.var(ddof=1) * (nb - 1))) / df
    se = math.sqrt(sp2 * (1.0 / na + 1.0 / nb))
    if se == 0.0:
        return (0.0 if a.mean() == b.mean() else math.inf), df
    return (float(b.mean() - a.mean()) / se, df)


def _ols_t(a: np.ndarray, b: np.ndarray) -> tuple[float, int]:
    """OLS group-coefficient t-statistic + df (numpy lstsq). Leg B — equals _pooled_t for two groups."""
    na, nb = len(a), len(b)
    df = na + nb - 2
    y = np.concatenate([a, b])
    ind = np.concatenate([np.zeros(na), np.ones(nb)])
    X = np.column_stack([np.ones_like(ind), ind])
    coef, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ coef
    mse = float(resid @ resid) / df
    xtx_inv = np.linalg.inv(X.T @ X)
    se = math.sqrt(mse * float(xtx_inv[1, 1]))
    if se == 0.0:
        return (0.0 if coef[1] == 0.0 else math.inf), df
    return (float(coef[1]) / se, df)


def _per_probe_pvalues(node: OperationNode, *, leg) -> dict[str, float]:
    """Per-probe two-sided p-values over the node's `probes` param, using the `leg` t-statistic fn."""
    beta, sample_ids, group_of, p = _load_betas(node)
    probes = [s for s in p["probes"].split(",") if s]
    level_a, level_b = p["level_a"], p["level_b"]
    out: dict[str, float] = {}
    for cg in probes:
        if cg not in beta:
            raise KeyError(f"probe {cg!r} not in contract")
        a, b = _split(beta[cg], sample_ids, group_of, level_a, level_b)
        t, df = leg(a, b)
        out[cg] = 0.0 if math.isinf(t) else _t_two_sided_p(t, df)
    return out


def _n_dmps(pvalues: dict[str, float], alpha: float) -> int:
    return sum(1 for v in pvalues.values() if v < alpha)


def dmp_indicators(node: OperationNode) -> list[int]:
    """Per-probe DMP indicators (1 iff p < alpha) using the pooled-t leg — the e-value's view."""
    alpha = float(dict(node.params)["alpha"])
    pvals = _per_probe_pvalues(node, leg=_pooled_t)
    return [1 if v < alpha else 0 for v in pvals.values()]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/zbb2/Desktop/polymer-claims && uv run --project . pytest tests/test_methyl_ndmp.py -q`
Expected: PASS (the 5 tests; `dmp_indicators` over the powered fixture yields ≥8 DMPs).

- [ ] **Step 5: Lint + commit**

Run: `cd /Users/zbb2/Desktop/polymer-claims && uv run --project . ruff check src tests`
```bash
cd /Users/zbb2/Desktop/polymer-claims
git add src/polymer_claims/methyl_ndmp.py tests/test_methyl_ndmp.py
git commit -m "feat(methyl): n-DMP per-probe pooled-t p-values + count + dmp_indicators (Student-t via betai)"
```

---

### Task 4: `methyl_ndmp.py` — two leg adapters + `n_dmps_claim` + registry

**Files:**
- Modify: `src/polymer_claims/methyl_ndmp.py`
- Test: `tests/test_methyl_ndmp.py` (append)

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_methyl_ndmp.py`:

```python
def test_two_legs_agree_on_count():
    from polymer_claims.methyl_ndmp import NDmpOlsCoefAdapter, NDmpTTestAdapter
    probes = tuple(f"cg{i:08d}" for i in range(1, 25))
    node = _ndmp_node(probes)
    va = NDmpTTestAdapter().execute(node, (), None).value
    vb = NDmpOlsCoefAdapter().execute(node, (), None).value
    assert va == vb            # the air-gap: same integer count two ways
    assert va >= 8.0


def test_n_dmps_claim_builds_over_all_probes():
    from polymer_claims.methyl_ndmp import _NDMP_IMPL, n_dmps_claim
    c = n_dmps_claim("c-ndmp", ref="se:epicv2_casectrl_powered@1", k=3)
    node = c.evaluation_plan.graph.nodes[0]
    assert node.impl == _NDMP_IMPL
    assert c.evaluation_plan.criterion.threshold == 3.0
    # probes materialized to the full 24-probe list (no "all" sentinel)
    probes = dict(node.params)["probes"].split(",")
    assert len(probes) == 24
    assert c.subject is not None  # GenomicRegion spanning the probes


def test_ndmp_registry_has_two_independent_legs():
    from polymer_claims.methyl_ndmp import ndmp_independent_registry
    reg = ndmp_independent_registry()
    ids = {cr.identity for cr in reg.credentials}
    assert ids == {"methyl-ndmp-ttest", "methyl-ndmp-ols"}
    owners = {cr.owner for cr in reg.credentials}
    assert len(owners) == 2  # distinct owners -> registry-independent
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/zbb2/Desktop/polymer-claims && uv run --project . pytest tests/test_methyl_ndmp.py -q -k "legs_agree or claim_builds or registry"`
Expected: FAIL (adapters/builder/registry not defined).

- [ ] **Step 3: Add the legs, builder, and registry**

Append to `src/polymer_claims/methyl_ndmp.py`:

```python
class NDmpTTestAdapter:
    """Independent leg A — DMP count via the manual pooled two-sample t-test."""

    identity = "methyl-ndmp-ttest"

    def execute(self, node, upstream, ctx) -> ExecValue:
        alpha = float(dict(node.params)["alpha"])
        return ExecValue(value=float(_n_dmps(_per_probe_pvalues(node, leg=_pooled_t), alpha)))


class NDmpOlsCoefAdapter:
    """Independent leg B — DMP count via the per-probe OLS group-coefficient t (numpy lstsq).
    Equals leg A's count for a two-group design (the OLS-coef t == the pooled t)."""

    identity = "methyl-ndmp-ols"

    def execute(self, node, upstream, ctx) -> ExecValue:
        alpha = float(dict(node.params)["alpha"])
        return ExecValue(value=float(_n_dmps(_per_probe_pvalues(node, leg=_ols_t), alpha)))


def _all_probe_ids(ref: str) -> tuple[str, ...]:
    """Read the contract manifest's row_data feature-ids (the full probe set)."""
    import json
    from pathlib import Path

    se = load_contract(ref)
    betas_path = Path(se.access_methods[0].access_url)
    manifest = json.loads((betas_path.parent / f"{se.contract_uid.split('@')[0]}.json").read_text())
    return tuple(r["feature_id"] for r in manifest["row_data"])


def n_dmps_claim(
    claim_id: str,
    *,
    ref: str = "se:epicv2_casectrl_powered@1",
    probes: tuple[str, ...] | None = None,
    group_col: str = "Sample_Group",
    level_a: str = "level1",
    level_b: str = "level2",
    alpha: float = 0.05,
    k: float,
    comparator: Comparator = Comparator.GE,
    oracle_ref: str | None = None,
    strength: StrengthVector | None = None,
    title: str = "n differentially-methylated probes (p < alpha)",
) -> Claim:
    """Build a PENDING claim whose plan counts DMPs (per-probe p < alpha) over the contract's probes
    (default = ALL probes) and licenses iff the count clears `k`. Mirrors region_delta_beta_claim;
    binds CANONICAL_EPICV2_V1 as the apparatus. `strength=None` -> earned at verify."""
    if probes is None:
        probes = _all_probe_ids(ref)
    if oracle_ref is None:
        oracle_ref = profile_oracle_id(CANONICAL_EPICV2_V1)
    node = OperationNode(
        id="n0",
        impl=_NDMP_IMPL,
        inputs=(DataHandle(ref=ref),),
        params=(
            ("probes", ",".join(probes)),
            ("group_col", group_col),
            ("level_a", level_a),
            ("level_b", level_b),
            ("alpha", str(alpha)),
        ),
        oracle_ref=oracle_ref,
        produces=ProducedLeafSpec(leaf_kind="quantity", measurement_basis=MeasurementBasis.DERIVED),
    )
    plan = EvaluationPlan(
        graph=ComputeGraph(nodes=(node,), terminal="n0"),
        criterion=SatisfactionCriterion(comparator=comparator, threshold=float(k)),
    )
    subject = GenomicRegion(
        id="chr1:1000000-1004800", display="chr1:1,000,000-1,004,800",
        assembly="hg38", chrom="chr1", start=1_000_000, end=1_004_800,
    )
    return Claim(
        id=claim_id,
        title=title,
        pattern=PatternRef(id="adjusted_effect", version="v1"),
        leaves=(CategoricalLeaf(ontology_term="differential_methylation"),),
        status=Status.PENDING,
        pending_reason=PendingReason.UNTESTED,
        strength=strength,
        subject=subject,
        evaluation_plan=plan,
    )


def ndmp_independent_registry() -> AdapterRegistry:
    """Credentials asserting the two n-DMP legs are genuinely independent (distinct owners + hashes)."""
    return AdapterRegistry(credentials=(
        AdapterCredential(identity="methyl-ndmp-ttest", owner="owner-ttest", implementation_hash="h-ndmp-ttest"),
        AdapterCredential(identity="methyl-ndmp-ols", owner="owner-ols", implementation_hash="h-ndmp-ols"),
    ))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/zbb2/Desktop/polymer-claims && uv run --project . pytest tests/test_methyl_ndmp.py -q`
Expected: PASS (8 tests — the two legs agree on the count; the claim builds with 24 probes materialized).

- [ ] **Step 5: Lint + commit**

Run: `cd /Users/zbb2/Desktop/polymer-claims && uv run --project . ruff check src tests`
```bash
cd /Users/zbb2/Desktop/polymer-claims
git add src/polymer_claims/methyl_ndmp.py tests/test_methyl_ndmp.py
git commit -m "feat(methyl): n-DMP two-leg adapters + n_dmps_claim builder + registry (air-gap)"
```

---

### Task 5: Wire `methyl::n_dmps` into `evidence_map`

**Files:**
- Modify: `src/polymer_claims/evidence.py`
- Test: `tests/test_methyl_ndmp.py` (append) OR `tests/test_evidence_map.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_methyl_ndmp.py`:

```python
def test_evidence_map_scores_n_dmps_claim():
    from polymer_grammar import FDRLedger
    from polymer_protocol import Corpus

    from polymer_claims.evidence import evidence_map
    from polymer_claims.methyl_ndmp import n_dmps_claim

    claim = n_dmps_claim("c-ndmp", ref="se:epicv2_casectrl_powered@1", k=3)
    corpus = Corpus(claims=(claim,), fdr_ledger=FDRLedger(target_fdr=0.05))
    m = evidence_map(corpus)
    assert "c-ndmp" in m
    assert m["c-ndmp"] > 32.0  # strong enrichment (~10/24 DMPs vs p0=0.05) clears a typical e-LOND bar
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/zbb2/Desktop/polymer-claims && uv run --project . pytest tests/test_methyl_ndmp.py -q -k "evidence_map_scores"`
Expected: FAIL (`evidence_map` has no `methyl::n_dmps` branch — `c-ndmp` not in the map).

- [ ] **Step 3: Add the `methyl::n_dmps` branch to `evidence_map`**

In `src/polymer_claims/evidence.py`:
(a) Add imports near the top (after the existing `from .methyl_adapters import _IMPL, _region_group_means`):
```python
from .methyl_ndmp import _NDMP_IMPL, dmp_indicators
```
(b) Restructure `evidence_map` so it dispatches on `node.impl` (the current body only handles `_IMPL`).
Replace the loop body so the `node.impl != _IMPL` early-`continue` becomes a two-way dispatch:
```python
def evidence_map(corpus: Corpus) -> dict[str, float]:
    """Per-claim native e-value keyed by claim id. region-Δβ (impl _IMPL) -> betting_evalue on the
    group-mean diff; n-DMPs (impl _NDMP_IMPL) -> count_enrichment_evalue on the DMP indicators. Any other
    claim gets NO entry (caller falls back to the 3-way gate). Impure: reads the bundled contract."""
    out: dict[str, float] = {}
    for c in corpus.claims:
        node = _terminal_node(c)
        if node is None:
            continue
        if not any(isinstance(i, DataHandle) for i in node.inputs):
            continue
        crit = c.evaluation_plan.criterion
        if crit.threshold is None or crit.comparator not in (
            Comparator.GT, Comparator.GE, Comparator.LT, Comparator.LE
        ):
            continue
        if node.impl == _IMPL:
            try:
                a, b = _region_group_means(node)
            except (FileNotFoundError, KeyError, ValueError):
                continue
            out[c.id] = betting_evalue(a, b, threshold=crit.threshold, comparator=crit.comparator)
        elif node.impl == _NDMP_IMPL:
            try:
                indicators = dmp_indicators(node)
                p0 = float(dict(node.params)["alpha"])
            except (FileNotFoundError, KeyError, ValueError):
                continue
            out[c.id] = count_enrichment_evalue(indicators, p0=p0)
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/zbb2/Desktop/polymer-claims && uv run --project . pytest tests/test_methyl_ndmp.py tests/test_evidence_map.py -q`
Expected: PASS (the n-DMP claim is scored; existing region-Δβ `evidence_map` tests stay green — the
`_IMPL` branch is unchanged).

- [ ] **Step 5: Lint + commit**

Run: `cd /Users/zbb2/Desktop/polymer-claims && uv run --project . ruff check src tests`
```bash
cd /Users/zbb2/Desktop/polymer-claims
git add src/polymer_claims/evidence.py tests/test_methyl_ndmp.py
git commit -m "feat(evidence): evidence_map scores methyl::n_dmps via count_enrichment_evalue"
```

---

### Task 6: End-to-end demo + green gate + CONTINUE

**Files:**
- Create: `tests/test_n_dmps_e2e.py`
- Modify: `docs/superpowers/CONTINUE.md`

- [ ] **Step 1: Write the acceptance test**

Create `tests/test_n_dmps_e2e.py`:

```python
from __future__ import annotations

from polymer_grammar import FDRLedger, IndependenceTier, MaterializationContext, Status
from polymer_protocol import Corpus, run_cycle

from polymer_claims.analysis_profile import profile_oracle_registry
from polymer_claims.evidence import evidence_map
from polymer_claims.materialization import materialization_map
from polymer_claims.methyl_ndmp import NDmpOlsCoefAdapter, NDmpTTestAdapter, n_dmps_claim, ndmp_independent_registry
from polymer_claims.profiles import CANONICAL_EPICV2_V1

_ADAPTERS = (NDmpTTestAdapter(), NDmpOlsCoefAdapter())
_BASE = MaterializationContext(id="M", api_version="v1", data_version="d1")
_NULL_PROBES = tuple(f"cg{i:08d}" for i in range(11, 25))  # control region only (no signal)


def _run(claim):
    corpus = Corpus(claims=(claim,), fdr_ledger=FDRLedger(target_fdr=0.05))
    return run_cycle(
        corpus, _ADAPTERS, _BASE,
        adapter_registry=ndmp_independent_registry(),
        oracles=profile_oracle_registry((CANONICAL_EPICV2_V1, "recomputable_public")),
        materializations=materialization_map(corpus, _BASE),
        evidence=evidence_map(corpus),
    )


def test_n_dmps_over_signal_licenses_reproduced():
    claim = n_dmps_claim("c-ndmp", ref="se:epicv2_casectrl_powered@1", k=3)  # all 24 probes
    result = _run(claim)
    c = next(x for x in result.corpus.claims if x.id == "c-ndmp")
    assert c.status == Status.LICENSED
    assert c.licensing.independence_tier is IndependenceTier.REPRODUCED
    assert result.corpus.fdr_ledger.n_discoveries == 1


def test_n_dmps_over_null_region_does_not_license():
    # THE MONEY-SHOT: only control probes -> count ~ alpha*M (chance) < k=3 -> not licensed.
    claim = n_dmps_claim("c-null", ref="se:epicv2_casectrl_powered@1", probes=_NULL_PROBES, k=3)
    result = _run(claim)
    c = next(x for x in result.corpus.claims if x.id == "c-null")
    assert c.status != Status.LICENSED


def test_same_owner_pair_held_pending():
    from polymer_protocol import AdapterCredential, AdapterRegistry
    same_owner = AdapterRegistry(credentials=(
        AdapterCredential(identity="methyl-ndmp-ttest", owner="o", implementation_hash="h1"),
        AdapterCredential(identity="methyl-ndmp-ols", owner="o", implementation_hash="h2"),
    ))
    claim = n_dmps_claim("c-ndmp", ref="se:epicv2_casectrl_powered@1", k=3)
    corpus = Corpus(claims=(claim,), fdr_ledger=FDRLedger(target_fdr=0.05))
    result = run_cycle(
        corpus, _ADAPTERS, _BASE, adapter_registry=same_owner,
        oracles=profile_oracle_registry((CANONICAL_EPICV2_V1, "recomputable_public")),
        materializations=materialization_map(corpus, _BASE), evidence=evidence_map(corpus),
    )
    c = next(x for x in result.corpus.claims if x.id == "c-ndmp")
    assert c.status != Status.LICENSED  # air-gap: same owner -> not registry-independent
```

- [ ] **Step 2: Run the acceptance test**

Run: `cd /Users/zbb2/Desktop/polymer-claims && uv run --project . pytest tests/test_n_dmps_e2e.py -q`
Expected: 3 passed. If `test_n_dmps_over_signal_licenses_reproduced` fails because the claim is not
LICENSED, diagnose honestly: check the count (`_n_dmps` over the powered fixture should be ~10) and the
evidence value (`evidence_map(corpus)["c-ndmp"]` should clear the e-LOND bar). Do NOT weaken the bar or
the criterion; if genuinely under-powered, raise the e-value/count by widening the probe set, not by
lowering `k` below the true signal count.

- [ ] **Step 3: Run the full gate**

Run: `cd /Users/zbb2/Desktop/polymer-claims && bash scripts/check-all.sh`
Expected: `ALL GREEN`. New umbrella tests: count-enrichment (6) + methyl_ndmp (9) + e2e (3) ≈ +18;
grammar/protocol/viewer unchanged.

- [ ] **Step 4: Update CONTINUE.md**

In `docs/superpowers/CONTINUE.md`:
- Add to the **Done — checklist** (under "Phase 2 — epistemic core"):
  `✅ n-DMPs-at-FDR — second methylation reduction; count of per-probe-significant DMPs licenses on a one-sample count-enrichment e-value; two pooled-t legs agree on the count (air-gap); umbrella-only.`
- In **▶ NEXT**, mark item 1 (n-DMPs) done; promote Procrustes + the §2E follow-ups.
- Update the **Current state** test counts to the new totals from Step 3.

- [ ] **Step 5: Commit**

```bash
cd /Users/zbb2/Desktop/polymer-claims
git add tests/test_n_dmps_e2e.py docs/superpowers/CONTINUE.md
git commit -m "test(n-dmps): end-to-end REPRODUCED license + null-region money-shot + air-gap; CONTINUE"
```

---

## Self-review notes (for the implementer)

- **Spec coverage:** count-enrichment e-value (Task 1) · `_load_betas` extraction (Task 2) · per-probe
  pooled-t + count + indicators (Task 3) · two legs + builder + registry (Task 4) · evidence_map wiring
  (Task 5) · e2e demo + money-shot + air-gap + gate + docs (Task 6).
- **Air-gap honesty:** the two legs compute the per-probe t TWO ways (manual pooled-t vs OLS-coef t) and
  agree on the integer count — `test_two_legs_agree_on_count` pins it. On real noisy data a borderline
  probe (p≈α) could flip; the powered fixture has clean separation (no flips), noted as a real-data caveat.
- **One e-value, no double-count:** the n-DMP e-value is ONE entry in `evidence_map` → ONE e-LOND test,
  exactly like region-Δβ. grammar/protocol untouched; Corpus=4; base import numpy-free (methyl_ndmp not
  re-exported); `evidence=None` byte-identical.
- **Region-Δβ unaffected:** Task 2's `_load_betas` extraction is behavior-preserving (Step 2 runs the
  existing region tests); Task 5's `evidence_map` dispatch leaves the `_IMPL` branch identical.
