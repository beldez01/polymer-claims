"""Tests for the powered benchmark DGP fixture (Task 17).

Test plan:
  1. Monte-Carlo power: point estimate >= 0.85, LCB >= 0.80 (deterministic, fixed sim_seed).
  2. Committed fixture: realized e-value >= evalue_threshold(alpha_1) where alpha_1 is
     COMPUTED from a fresh FDR ledger's first allocation (never hardcoded).
  3. Structural ordering: model/baseline configs are module-level constants (fixed before
     any RNG draw); _generate_examples uses them by reference (not defined inside it).
  4. Separate RNG streams: the example-generating RNG is a distinct generator from any
     adapter logic (adapters are deterministic, so there is no adapter RNG).
"""
from __future__ import annotations

import inspect
import json
import math
from pathlib import Path

from polymer_grammar.fdr import FDRLedger, _next_alpha

from polymer_claims._fixtures.benchmark_dgp import (
    BASELINE_RULE_CONFIG,
    DGPBaselineAdapter,
    DGPModelAdapter,
    MODEL_RULE_CONFIG,
    TAU,
    _DGP_N,
    _DGP_SEED,
    _generate_examples,
    demo_baseline_adapter,
    demo_model_adapter,
    estimate_power,
    evalue_threshold,
)
from polymer_claims.benchmark_adapter import BenchmarkArtifact
from polymer_claims.benchmark_evidence import paired_advantage_evalue, score_advantage

# ---------------------------------------------------------------------------
# Fixtures / shared helpers
# ---------------------------------------------------------------------------

_FIXTURE_PATH = Path(__file__).parents[2] / "data" / "demo" / "benchmark_advantage_fixture.json"

_N_SIMS = 2000
_SIM_SEED = 137

# Alpha_1 from a FRESH ledger — computed, never hardcoded
_LEDGER_FRESH = FDRLedger(target_fdr=0.05)
_T1, _ALPHA_1 = _next_alpha(_LEDGER_FRESH)


# ---------------------------------------------------------------------------
# 1. Monte-Carlo power
# ---------------------------------------------------------------------------


def test_power_point_estimate_gte_085():
    """Power point estimate P̂(e >= 1/alpha_1) must be >= 0.85."""
    result = estimate_power(_DGP_N, _ALPHA_1, n_sims=_N_SIMS, sim_seed=_SIM_SEED)
    assert result.point_estimate >= 0.85, (
        f"Power point estimate {result.point_estimate:.4f} < 0.85 "
        f"(n={_DGP_N}, alpha_1={_ALPHA_1:.6f}, n_sims={_N_SIMS})"
    )


def test_power_lcb_gte_080():
    """Wilson 95% LCB on power must be >= 0.80."""
    result = estimate_power(_DGP_N, _ALPHA_1, n_sims=_N_SIMS, sim_seed=_SIM_SEED)
    assert result.lcb_95 >= 0.80, (
        f"Power LCB {result.lcb_95:.4f} < 0.80 "
        f"(point estimate={result.point_estimate:.4f}, n={_DGP_N}, n_sims={_N_SIMS})"
    )


# ---------------------------------------------------------------------------
# 2. Committed fixture e-value
# ---------------------------------------------------------------------------


def test_fixture_file_exists():
    assert _FIXTURE_PATH.exists(), f"Fixture not found at {_FIXTURE_PATH}"


def test_fixture_evalue_clears_ledger_threshold():
    """The committed fixture's realized e-value must clear evalue_threshold(alpha_1)
    where alpha_1 is derived from a fresh FDRLedger (never hardcoded)."""
    assert _FIXTURE_PATH.exists(), f"Fixture not found at {_FIXTURE_PATH}"
    payload = json.loads(_FIXTURE_PATH.read_text())
    artifact = BenchmarkArtifact.model_validate(payload)

    model = demo_model_adapter()
    baseline = demo_baseline_adapter()
    order = [ex.example_id for ex in artifact.examples]
    labels = {ex.example_id: ex.label for ex in artifact.examples}

    model_pv = model.predict(artifact.examples)
    baseline_pv = baseline.predict(artifact.examples)
    w = score_advantage(model_pv, baseline_pv, labels, order)
    e = paired_advantage_evalue(w, theta0=TAU)

    threshold = evalue_threshold(_ALPHA_1)
    assert e >= threshold, (
        f"Realized e-value {e:.4f} < threshold {threshold:.4f} "
        f"(alpha_1={_ALPHA_1:.6f} from fresh FDR ledger)"
    )


def test_fixture_dgp_digest_present_and_sha256_shaped():
    """dgp_digest field must be present and sha256:<64 hex> shaped."""
    assert _FIXTURE_PATH.exists(), f"Fixture not found at {_FIXTURE_PATH}"
    payload = json.loads(_FIXTURE_PATH.read_text())
    artifact = BenchmarkArtifact.model_validate(payload)
    import re
    assert re.match(r"^sha256:[0-9a-f]{64}$", artifact.dgp_digest), (
        f"dgp_digest malformed: {artifact.dgp_digest!r}"
    )


def test_fixture_example_count_matches_committed_n():
    assert _FIXTURE_PATH.exists(), f"Fixture not found at {_FIXTURE_PATH}"
    payload = json.loads(_FIXTURE_PATH.read_text())
    artifact = BenchmarkArtifact.model_validate(payload)
    assert len(artifact.examples) == _DGP_N, (
        f"Expected {_DGP_N} examples, got {len(artifact.examples)}"
    )


# ---------------------------------------------------------------------------
# 3. Structural ordering — configs fixed before RNG (audit #18)
# ---------------------------------------------------------------------------


def test_model_rule_config_is_module_level_constant():
    """MODEL_RULE_CONFIG must be a module-level dict (fixed before any RNG)."""
    import polymer_claims._fixtures.benchmark_dgp as dgp_mod
    assert hasattr(dgp_mod, "MODEL_RULE_CONFIG")
    assert isinstance(dgp_mod.MODEL_RULE_CONFIG, dict)
    assert dgp_mod.MODEL_RULE_CONFIG is MODEL_RULE_CONFIG


def test_baseline_rule_config_is_module_level_constant():
    """BASELINE_RULE_CONFIG must be a module-level dict (fixed before any RNG)."""
    import polymer_claims._fixtures.benchmark_dgp as dgp_mod
    assert hasattr(dgp_mod, "BASELINE_RULE_CONFIG")
    assert isinstance(dgp_mod.BASELINE_RULE_CONFIG, dict)
    assert dgp_mod.BASELINE_RULE_CONFIG is BASELINE_RULE_CONFIG


def test_generate_examples_references_configs_not_creates_them():
    """_generate_examples must reference MODEL_RULE_CONFIG via module scope,
    not define new config dicts inside the function body."""
    src = inspect.getsource(_generate_examples)
    # The function reads from MODEL_RULE_CONFIG (module-level)
    assert "MODEL_RULE_CONFIG" in src, (
        "_generate_examples does not reference MODULE-LEVEL MODEL_RULE_CONFIG"
    )
    # The function takes 'rng' as a separate parameter
    assert "rng" in src, "_generate_examples must accept an rng parameter"


def test_generate_examples_accepts_rng_parameter():
    """The RNG is passed as an explicit parameter (separate independent stream)."""
    sig = inspect.signature(_generate_examples)
    params = list(sig.parameters.keys())
    assert "rng" in params, f"_generate_examples parameters: {params}"
    assert "n" in params, f"_generate_examples parameters: {params}"


# ---------------------------------------------------------------------------
# 4. Independent RNG streams
# ---------------------------------------------------------------------------


def test_adapter_configs_fixed_at_construction_not_from_rng():
    """DGPModelAdapter and DGPBaselineAdapter use module-level configs — no RNG."""
    model = DGPModelAdapter()
    baseline = DGPBaselineAdapter()
    # configs are copies of the module-level constants (same values)
    assert model.config == MODEL_RULE_CONFIG
    assert baseline.config == BASELINE_RULE_CONFIG


def test_example_generating_rng_is_separate_from_adapters():
    """The label/feature RNG is its own seeded generator distinct from adapter logic.
    Adapters are deterministic (no internal RNG); the DGP RNG is _DGP_SEED-seeded."""
    import numpy as np

    rng_a = np.random.default_rng(_DGP_SEED)
    rng_b = np.random.default_rng(_DGP_SEED)

    examples_a = _generate_examples(10, rng_a)
    examples_b = _generate_examples(10, rng_b)

    # Same seed → same examples (deterministic)
    assert examples_a == examples_b, "DGP is not deterministic for same seed"

    # Different seeds → (very likely) different examples
    rng_c = np.random.default_rng(_DGP_SEED + 1)
    examples_c = _generate_examples(10, rng_c)
    assert examples_a != examples_c, "DGP not sensitive to seed"


def test_adapters_are_label_blind():
    """Predictions must not change when labels change (label-blind check)."""
    import numpy as np
    rng = np.random.default_rng(0)
    examples = _generate_examples(20, rng)
    model = DGPModelAdapter()
    baseline = DGPBaselineAdapter()

    pv_model_orig = model.predict(examples)
    pv_baseline_orig = baseline.predict(examples)

    # Swap every label
    import dataclasses
    swapped = tuple(
        dataclasses.replace(ex, label="pos" if ex.label == "neg" else "neg")
        for ex in examples
    )
    pv_model_swap = model.predict(swapped)
    pv_baseline_swap = baseline.predict(swapped)

    assert pv_model_orig.predictions == pv_model_swap.predictions, (
        "DGPModelAdapter is NOT label-blind"
    )
    assert pv_baseline_orig.predictions == pv_baseline_swap.predictions, (
        "DGPBaselineAdapter is NOT label-blind"
    )


# ---------------------------------------------------------------------------
# 5. Evalue threshold helper
# ---------------------------------------------------------------------------


def test_evalue_threshold_returns_reciprocal():
    assert math.isclose(evalue_threshold(0.05), 20.0)
    assert math.isclose(evalue_threshold(_ALPHA_1), 1.0 / _ALPHA_1)


# ---------------------------------------------------------------------------
# 6. Alpha_1 is ledger-derived, not hardcoded
# ---------------------------------------------------------------------------


def test_alpha_1_from_ledger_matches_elond_formula():
    """alpha_1 = target_fdr * (6/pi^2) / 1^2 * (0 discoveries + 1)."""
    expected = 0.05 * (6.0 / math.pi**2) / 1.0 * 1.0
    assert math.isclose(_ALPHA_1, expected, rel_tol=1e-9), (
        f"alpha_1={_ALPHA_1} != expected={expected}"
    )
    assert _T1 == 1, f"First test index should be 1, got {_T1}"
