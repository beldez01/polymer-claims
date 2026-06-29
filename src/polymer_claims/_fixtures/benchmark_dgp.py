"""Powered benchmark DGP (data-generating process) for the V2.0 evidence-licensed capability.

Order-of-operations contract (audit #18):
  1. MODEL_RULE_CONFIG and BASELINE_RULE_CONFIG are fixed at MODULE IMPORT TIME —
     before any RNG stream is created or drawn from.
  2. _generate_examples(n, rng) consumes those configs via module-level names only;
     the RNG stream passed in is the SOLE source of stochasticity (no rule-object
     calls, no implicit global state).

DGP description:
  - Binary feature x0 ∈ {"0", "1"} drawn i.i.d. with P(x0="1") = _P_POS.
  - Base label: "pos" if x0 == "1" else "neg"  (mirrors model rule perfectly).
  - Label noise: flip with probability _EPSILON via independent Bernoulli draws.
  - Expected per-example advantage: E[W] = _P_POS * (1 − 2*_EPSILON) ≈ 0.45,
    which comfortably exceeds TAU = 0.1.
  - Model adapter accuracy ≈ 0.95; baseline (always "neg") accuracy ≈ 0.50.
"""
from __future__ import annotations

import math
from typing import NamedTuple

import numpy as np

from polymer_grammar import SamplingRegime

from polymer_claims._hashing import canonical_sha256
from polymer_claims.benchmark_adapter import BenchmarkArtifact, BenchmarkExample
from polymer_claims.benchmark_evidence import (
    PredictionVector,
    paired_advantage_evalue,
    score_advantage,
)

# ---------------------------------------------------------------------------
# 1. Rule configs — FIXED FIRST, before any RNG draw (audit #18)
# ---------------------------------------------------------------------------

MODEL_RULE_CONFIG: dict = {
    "identity": "dgp-model-v1",
    "signal_feature": "x0",
    "positive_value": "1",
    "positive_class": "pos",
    "negative_class": "neg",
}

BASELINE_RULE_CONFIG: dict = {
    "identity": "dgp-baseline-v1",
    "always_predict": "neg",
}

# ---------------------------------------------------------------------------
# 2. DGP parameters (also fixed before any RNG draw)
# ---------------------------------------------------------------------------

TAU: float = 0.1          # theta0 for the e-value test
_P_POS: float = 0.5       # P(x0="1") — balanced classes
_EPSILON: float = 0.05    # label noise probability
_DGP_SEED: int = 42       # fixed sampling seed

# Pre-declared schedule for n (never search: only escalate in order if LCB < 0.80)
_N_SCHEDULE: tuple[int, ...] = (200, 400, 800)
_DGP_N: int = _N_SCHEDULE[0]  # committed sample size — first predeclared schedule value

# Canonical digest of all DGP parameters (includes rule configs + tau + n + seed)
_DGP_DIGEST: str = canonical_sha256(
    {
        "model_rule_config": MODEL_RULE_CONFIG,
        "baseline_rule_config": BASELINE_RULE_CONFIG,
        "tau": TAU,
        "p_pos": _P_POS,
        "epsilon": _EPSILON,
        "n": _DGP_N,
        "dgp_seed": _DGP_SEED,
        "version": "v1",
    }
)


# ---------------------------------------------------------------------------
# 3. Label-blind adapters (implement BenchmarkAdapter Protocol)
# ---------------------------------------------------------------------------


class DGPModelAdapter:
    """Model adapter: reads signal_feature from features to predict class.

    Label-blind: prediction derived solely from ex.example_id + ex.features.
    Config-driven: behavior fully determined by MODEL_RULE_CONFIG (fixed above).
    """

    def __init__(self) -> None:
        self.identity: str = MODEL_RULE_CONFIG["identity"]
        self.config: dict = dict(MODEL_RULE_CONFIG)  # shallow copy of frozen config

    def predict(self, examples: tuple[BenchmarkExample, ...]) -> PredictionVector:
        cfg = self.config
        pos_val = cfg["positive_value"]
        pos_cls = cfg["positive_class"]
        neg_cls = cfg["negative_class"]
        sig_feat = cfg["signal_feature"]
        preds: list[tuple[str, str]] = []
        for ex in examples:
            features_dict = dict(ex.features)
            signal = features_dict.get(sig_feat, "0")
            cls = pos_cls if signal == pos_val else neg_cls
            preds.append((ex.example_id, cls))
        return PredictionVector(tuple(preds))


class DGPBaselineAdapter:
    """Baseline adapter: always predicts a fixed class (label-blind, id-blind).

    Always predicts BASELINE_RULE_CONFIG["always_predict"] = "neg".
    Weaker than DGPModelAdapter by construction.
    """

    def __init__(self) -> None:
        self.identity: str = BASELINE_RULE_CONFIG["identity"]
        self.config: dict = dict(BASELINE_RULE_CONFIG)  # shallow copy of frozen config

    def predict(self, examples: tuple[BenchmarkExample, ...]) -> PredictionVector:
        cls: str = self.config["always_predict"]
        preds: list[tuple[str, str]] = [(ex.example_id, cls) for ex in examples]
        return PredictionVector(tuple(preds))


# ---------------------------------------------------------------------------
# 4. Example generation — SEPARATE RNG stream (audit #18)
# ---------------------------------------------------------------------------


def _generate_examples(n: int, rng: np.random.Generator) -> tuple[BenchmarkExample, ...]:
    """Generate n labelled examples from the DGP using the supplied RNG stream.

    The RNG stream is the ONLY source of randomness here.  Rule configs are
    consumed via module-level names MODEL_RULE_CONFIG (fixed before this call).
    No model/baseline adapter objects are constructed or called.
    """
    pos_cls: str = MODEL_RULE_CONFIG["positive_class"]
    neg_cls: str = MODEL_RULE_CONFIG["negative_class"]
    pos_val: str = MODEL_RULE_CONFIG["positive_value"]
    sig_feat: str = MODEL_RULE_CONFIG["signal_feature"]

    x0_positive = rng.random(n) < _P_POS   # True → "1"
    flip_label = rng.random(n) < _EPSILON   # True → flip

    examples: list[BenchmarkExample] = []
    for i in range(n):
        x0 = pos_val if x0_positive[i] else "0"
        base_label = pos_cls if x0 == pos_val else neg_cls
        label = (neg_cls if base_label == pos_cls else pos_cls) if flip_label[i] else base_label
        examples.append(
            BenchmarkExample(
                example_id=f"ex_{i:04d}",
                features=((sig_feat, x0),),
                label=label,
            )
        )
    return tuple(examples)


# ---------------------------------------------------------------------------
# 5. Power helpers
# ---------------------------------------------------------------------------


def evalue_threshold(alpha: float) -> float:
    """Return 1/alpha — the e-value threshold for a given alpha level."""
    return 1.0 / alpha


def _wilson_lcb(successes: int, total: int, *, z: float = 1.645) -> float:
    """One-sided 95% lower confidence bound using the Wilson score interval."""
    if total == 0:
        return 0.0
    p_hat = successes / total
    z2 = z * z
    denom = 1.0 + z2 / total
    centre = (p_hat + z2 / (2.0 * total)) / denom
    margin = z * math.sqrt(p_hat * (1.0 - p_hat) / total + z2 / (4.0 * total * total)) / denom
    return centre - margin


class PowerResult(NamedTuple):
    """Outcome of a Monte-Carlo power estimate."""

    point_estimate: float
    lcb_95: float  # one-sided Wilson 95% lower confidence bound


def estimate_power(
    n: int,
    alpha: float,
    *,
    n_sims: int,
    sim_seed: int,
) -> PowerResult:
    """Monte-Carlo power estimate: P̂(e-value ≥ 1/alpha) over n_sims i.i.d. DGP draws.

    Deterministic given (n, alpha, n_sims, sim_seed).  Each simulation uses a
    child RNG spawned from the top-level sim_seed RNG so draws are independent
    and reproducible.

    Returns PowerResult(point_estimate, lcb_95).
    """
    threshold = evalue_threshold(alpha)
    top_rng = np.random.default_rng(sim_seed)
    model_adapter = DGPModelAdapter()
    baseline_adapter = DGPBaselineAdapter()

    n_exceed = 0
    for _ in range(n_sims):
        # Each sim gets an independent child RNG (avoids correlated streams)
        child_seed = int(top_rng.integers(0, 2**63))
        sim_rng = np.random.default_rng(child_seed)
        examples = _generate_examples(n, sim_rng)
        order = [ex.example_id for ex in examples]
        labels = {ex.example_id: ex.label for ex in examples}
        model_pv = model_adapter.predict(examples)
        baseline_pv = baseline_adapter.predict(examples)
        w = score_advantage(model_pv, baseline_pv, labels, order)
        e = paired_advantage_evalue(w, theta0=TAU)
        if e >= threshold:
            n_exceed += 1

    point_est = n_exceed / n_sims
    lcb = _wilson_lcb(n_exceed, n_sims)
    return PowerResult(point_estimate=point_est, lcb_95=lcb)


# ---------------------------------------------------------------------------
# 6. Committed benchmark fixture
# ---------------------------------------------------------------------------


def build_demo_benchmark() -> BenchmarkArtifact:
    """Build the committed benchmark at the predeclared n=200 and dgp_seed=42.

    The RNG stream is created AFTER all configs/parameters are fixed (at
    module-import time).  This function is pure given the module constants.
    """
    rng = np.random.default_rng(_DGP_SEED)
    examples = _generate_examples(_DGP_N, rng)
    return BenchmarkArtifact(
        examples=examples,
        target_population="synthetic-dgp-v1",
        sampling_regime=SamplingRegime.IID_EXAMPLES,
        version="v1",
        sampling_seed=_DGP_SEED,
        dgp_digest=_DGP_DIGEST,
    )


def demo_model_adapter() -> DGPModelAdapter:
    """Return a fresh DGPModelAdapter instance (label-blind)."""
    return DGPModelAdapter()


def demo_baseline_adapter() -> DGPBaselineAdapter:
    """Return a fresh DGPBaselineAdapter instance (label-blind)."""
    return DGPBaselineAdapter()
