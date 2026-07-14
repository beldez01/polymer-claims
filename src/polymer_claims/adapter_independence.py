"""Adapter-independence Step 0 probe (C1) — measured error-correlation, not asserted labels.

The air-gap defeater D4 assumes two organizationally-independent adapters make INDEPENDENT errors.
This probe MEASURES whether that holds: given two predictors' scores over a known-truth battery it
computes the error-correlation ρ and the effective number of witnesses ``N_eff = 2/(1+ρ)`` — the
concrete instrument the R1–R5 hardening arc needs, and the first step toward the foundations §2.B /
§9 gap ("independence as MEASURED error-correlation, not operator-declared factor labels").

Claim-shape matters (plan §R2): the right independence metric depends on the claim's shape —
**error-correlation** for continuous score / classification shapes, **set-overlap φ** for flag-set
shapes (e.g. per-probe DMP flagging). Both are provided; a single ``N_eff`` does NOT cap everything.

Pure stdlib, umbrella-side (no numpy); no grammar/protocol/Corpus change. The compute here is
unit-tested on synthetic score pairs. The LIVE run is **DATA-GATED** — see ``run_variant_effect_probe``.

Plan: docs/superpowers/plans/2026-07-07-adapter-independence-hardening-plan.md §3.
"""
from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass


def _pearson(x: Sequence[float], y: Sequence[float]) -> float:
    """Pearson correlation; ``nan`` when undefined (n<2 or a constant vector — a perfect predictor
    has zero error variance, so its error-correlation is undefined, not zero)."""
    n = len(x)
    if n < 2 or len(y) != n:
        return math.nan
    mx, my = sum(x) / n, sum(y) / n
    sxx = sum((xi - mx) ** 2 for xi in x)
    syy = sum((yi - my) ** 2 for yi in y)
    if sxx == 0.0 or syy == 0.0:
        return math.nan
    sxy = sum((xi - mx) * (yi - my) for xi, yi in zip(x, y))
    return sxy / math.sqrt(sxx * syy)


def signed_errors(scores: Sequence[float], labels: Sequence[float]) -> tuple[float, ...]:
    """Per-item signed error ``score - label`` (the residual vector whose cross-model correlation is
    the quantity of interest — NOT the raw outputs)."""
    return tuple(s - y for s, y in zip(scores, labels))


def error_correlation(errors_a: Sequence[float], errors_b: Sequence[float]) -> float:
    """ρ = Pearson correlation between two models' signed error vectors."""
    return _pearson(errors_a, errors_b)


def n_eff_from_rho(rho: float) -> float:
    """Effective independent witnesses ``N_eff = 2/(1+ρ)``. ρ→1 ⇒ 1 witness (they fail together);
    ρ≈0 ⇒ ~2; ρ<0 ⇒ >2 (decorrelated beyond independence). ρ=-1 ⇒ +inf (degenerate)."""
    if math.isnan(rho):
        return math.nan
    denom = 1.0 + rho
    return math.inf if denom == 0.0 else 2.0 / denom


def _phi(flagged_a: set, flagged_b: set, universe: Sequence) -> float:
    """φ = correlation of the two binary flag-indicator vectors over ``universe``."""
    a = [1.0 if u in flagged_a else 0.0 for u in universe]
    b = [1.0 if u in flagged_b else 0.0 for u in universe]
    return _pearson(a, b)


def set_overlap_neff(flagged_a: set, flagged_b: set, universe: Sequence) -> float:
    """``N_eff`` from the φ-coefficient of two flag SETS over a universe — the claim-shape variant for
    flag-set adapters (e.g. two DMP callers). Identical flags ⇒ 1; disjoint ⇒ >2."""
    return n_eff_from_rho(_phi(flagged_a, flagged_b, universe))


@dataclass(frozen=True)
class IndependenceReport:
    n: int
    rho: float
    n_eff: float
    rho_pathogenic: float | None   # per-class error-correlation (label==1); None if undefined
    rho_benign: float | None       # per-class error-correlation (label==0); None if undefined
    # 2x2 correctness confusion (each model right/wrong at its threshold)
    both_correct: int
    a_only_correct: int
    b_only_correct: int
    both_wrong: int


def _class_rho(errors_a, errors_b, labels, target) -> float | None:
    idx = [i for i, y in enumerate(labels) if y == target]
    if len(idx) < 2:
        return None
    rho = _pearson([errors_a[i] for i in idx], [errors_b[i] for i in idx])
    return None if math.isnan(rho) else rho


def independence_report(
    scores_a: Sequence[float],
    scores_b: Sequence[float],
    labels: Sequence[float],
    *,
    threshold_a: float,
    threshold_b: float,
) -> IndependenceReport:
    """The Step-0 headline: ρ, ``N_eff``, per-class error-correlation, and the 2×2 correctness
    confusion, over a known-truth battery (labels ∈ {0,1}; a score ≥ threshold predicts pathogenic).
    """
    ea = signed_errors(scores_a, labels)
    eb = signed_errors(scores_b, labels)
    rho = _pearson(ea, eb)
    both_correct = a_only = b_only = both_wrong = 0
    for sa, sb, y in zip(scores_a, scores_b, labels):
        a_ok = (sa >= threshold_a) == (y == 1.0)
        b_ok = (sb >= threshold_b) == (y == 1.0)
        if a_ok and b_ok:
            both_correct += 1
        elif a_ok:
            a_only += 1
        elif b_ok:
            b_only += 1
        else:
            both_wrong += 1
    return IndependenceReport(
        n=len(labels),
        rho=rho,
        n_eff=n_eff_from_rho(rho),
        rho_pathogenic=_class_rho(ea, eb, labels, 1.0),
        rho_benign=_class_rho(ea, eb, labels, 0.0),
        both_correct=both_correct,
        a_only_correct=a_only,
        b_only_correct=b_only,
        both_wrong=both_wrong,
    )


# --- Correlated-VARIANCE probe (neg-whisper ② evidence leg) -----------------------------------
#
# The shared-cause / multiply-e-values gate (replication.py) today decides independence from
# operator-ASSERTED factor-tag Jaccard vs a fixed τ. This probe supplies the MEASURED evidence the
# spec asks for: perturb a SHARED input and measure how JOINTLY the two legs' outputs move. High
# joint movement ⇒ the legs share a variance source ⇒ their errors are NOT independent, so their
# e-values must not multiply. This is the correlated-VARIANCE axis only.
#
# CORRELATED-BIAS RESIDUE (spec §3 scope guard): correlated BIAS — both legs wrong in the SAME
# direction from a shared prior/reference, invisible to agreement — is UN-INSTRUMENTABLE from within
# (it needs an EXTERNAL anchor: a third heterodox witness, R4). It is recorded as a NAMED OPEN
# DEFEATER, never silently absorbed.
CORRELATED_BIAS_DEFEATER = "correlated_bias:needs_external_anchor"

# |ρ_cv| ≥ τ ⇒ the two legs share a variance source ⇒ NOT independent (mirrors SHARED_CAUSE_TAU).
SHARED_VARIANCE_TAU: float = 0.5


def perturbation_responses(outputs: Sequence[float], baseline: float) -> tuple[float, ...]:
    """Each perturbed output's deviation from the leg's unperturbed baseline (its response to the
    shared-input perturbation battery)."""
    return tuple(o - baseline for o in outputs)


def correlated_variance(responses_a: Sequence[float], responses_b: Sequence[float]) -> float:
    """Joint movement of two legs under a battery of SHARED-input perturbations = Pearson ρ of their
    response vectors. |ρ|→1 ⇒ they move together (shared variance source); ρ≈0 ⇒ independent."""
    return _pearson(responses_a, responses_b)


def variance_independent(rho_cv: float, *, tau: float = SHARED_VARIANCE_TAU) -> bool | None:
    """Independence verdict from the correlated-variance ρ: ``|ρ| < τ`` ⇒ independent. ``None`` when
    ρ is undefined (a leg that never moved under perturbation — no measurable shared variance)."""
    if math.isnan(rho_cv):
        return None
    return abs(rho_cv) < tau


@dataclass(frozen=True)
class CorrelatedVarianceReport:
    rho_cv: float
    independent: bool | None
    n_eff: float
    bias_residue: str = CORRELATED_BIAS_DEFEATER  # the un-instrumentable axis, named not hidden


def correlated_variance_probe(
    outputs_a: Sequence[float],
    baseline_a: float,
    outputs_b: Sequence[float],
    baseline_b: float,
    *,
    tau: float = SHARED_VARIANCE_TAU,
) -> CorrelatedVarianceReport:
    """The shared-input perturbation probe: given both legs' outputs across a shared-input
    perturbation battery (and each leg's unperturbed baseline), measure correlated variance ρ, the
    independence verdict, and ``N_eff``. Records the correlated-bias residue as an open defeater."""
    ra = perturbation_responses(outputs_a, baseline_a)
    rb = perturbation_responses(outputs_b, baseline_b)
    rho = _pearson(ra, rb)
    return CorrelatedVarianceReport(
        rho_cv=rho,
        independent=variance_independent(rho, tau=tau),
        n_eff=n_eff_from_rho(abs(rho)) if not math.isnan(rho) else math.nan,
    )


def run_variant_effect_probe(*_args, **_kwargs):  # pragma: no cover - data-gated
    """The live AlphaMissense-vs-ESM1v-on-ClinVar Step-0 experiment. **DATA-GATED / BLOCKED** — needs
    external data NOT in this repo:

      * ClinVar ``variant_summary.txt.gz`` (NCBI FTP), filtered to a binary high-confidence missense
        truth set, PREFERRING variants added/updated AFTER each model's training cutoff (leakage guard);
      * AlphaMissense ``AlphaMissense_hg38.tsv.gz`` precomputed pathogenicity ∈ [0,1];
      * ESM1v masked-marginal LLR tables (ensemble mean of ESM1v_1..5).

    Wire those loaders to produce ``(scores_a, scores_b, labels)`` and hand them to
    ``independence_report`` (calibrate each model's threshold on a HELD-OUT split, report on TEST
    only, never fabricate scores or labels). The statistical compute above is complete and tested;
    only this real-data loading is blocked.
    """
    raise NotImplementedError(
        "adapter-independence Step-0 live run is data-gated: supply ClinVar + AlphaMissense + ESM1v "
        "(see run_variant_effect_probe docstring) and call independence_report on the loaded arrays."
    )
