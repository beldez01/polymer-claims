"""evaluate.py — FormalClaim M2 (v0.2).

Walks a FormalClaim's InferenceRule against its pinned statistics and
produces an :class:`EvaluationResult` with a LICENSED / REJECTED / PENDING
verdict, a per-leaf conjunct breakdown, and — in v0.2 materialization
mode — a drift report comparing live-computed statistics to their pinned
values.

Scope
-----
* **Inference-only evaluation** from ``Statistic.value`` pinned in the
  fixture. Full AND / OR / NOT / CMP semantics with three-valued logic
  (true / false / null → PENDING). ``StatRef.transform`` (abs / neg /
  log) on both sides of a cmp, and ``cmp.rhs`` as either a scalar or a
  :class:`StatRef` (stat-vs-stat).
* **Materialization mode (v0.2)** — when an ``api_client`` is supplied,
  :func:`evaluate` delegates to :mod:`polymer_formalclaim.materialize`,
  which gates on premise provenance, dispatches each
  ``EstimatorOp.estimator.impl`` by prefix through a registry, collects
  computed statistics, and emits a :class:`StatDrift` record per
  materialized stat. The registry ships with an in-process identity
  handler and recognized (but not yet implemented) prefixes for
  ``scipy.stats.*``, ``python::sklearn.*``, ``R::*``. Individual adapter
  handlers land incrementally without touching the public API.

Batch corpus evaluation is done by the corpus CI wrapper
(``corpus/evaluator/run_evaluator.py``), not by this module.
"""

from __future__ import annotations

import math
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from polymer_formalclaim.schema import (
    FormalClaim,
    InferenceAnd,
    InferenceCmp,
    InferenceExpression,
    InferenceNot,
    InferenceOr,
    Statistic,
    StatRef,
)

EVALUATOR_VERSION = "0.2.0"

Verdict = Literal["LICENSED", "REJECTED", "PENDING"]

MaterializationStatus = Literal[
    "skipped_pinned_only",
    "skipped_ineligible",
    "partial",
    "complete",
    "error",
]


# ---------------------------------------------------------------------------
# Result payload (pydantic so it serializes identically to FormalClaim)
# ---------------------------------------------------------------------------


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CmpEvaluation(_Model):
    """One leaf-level InferenceCmp evaluation."""

    lhs_stat_id: str
    lhs_transform: str | None
    lhs_value: float | None
    op: str
    rhs_stat_id: str | None
    rhs_transform: str | None
    rhs_value: float | None
    result: bool | None


class StatDrift(_Model):
    """Pinned-vs-materialized comparison for one statistic.

    Populated only in materialization mode; in v0.1 this block is always
    absent.
    """

    stat_id: str
    pinned: float | int | str | None
    computed: float | int | str | None
    abs_diff: float | None
    rel_diff: float | None
    within_tolerance: bool | None


class EvaluationResult(_Model):
    claim_id: str
    schema_version: str
    verdict: Verdict
    conjuncts: list[CmpEvaluation]

    materialized: dict[str, float | int | str] | None = None
    drift: list[StatDrift] | None = None
    materialization_status: MaterializationStatus = "skipped_pinned_only"
    materialization_error: str | None = None

    evaluated_at: str
    api_version: str
    data_version: str
    evaluator_version: str = EVALUATOR_VERSION


# ---------------------------------------------------------------------------
# Inference evaluation
# ---------------------------------------------------------------------------


def _stat_numeric(stat: Statistic | None) -> float | None:
    """Return ``float(value)`` when the stat's value is a real number.

    bool is a subclass of int in Python — explicitly exclude it so a boolean
    stat never slips through as 0.0/1.0.
    """
    if stat is None:
        return None
    v = stat.value
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    return None


def _apply_transform(v: float | None, t: str | None) -> float | None:
    if v is None or t is None:
        return v
    if t == "abs":
        return abs(v)
    if t == "neg":
        return -v
    if t == "log":
        if v <= 0:
            return None
        return math.log(v)
    return None


def _resolve_stat_ref(ref: StatRef, stat_map: dict[str, Statistic]) -> float | None:
    return _apply_transform(_stat_numeric(stat_map.get(ref.stat_id)), ref.transform)


def _eval_cmp(lhs: float | None, op: str, rhs: float | None) -> bool | None:
    if lhs is None or rhs is None:
        return None
    if op == "<":
        return lhs < rhs
    if op == "<=":
        return lhs <= rhs
    if op == "=":
        return lhs == rhs
    if op == "!=":
        return lhs != rhs
    if op == ">":
        return lhs > rhs
    if op == ">=":
        return lhs >= rhs
    return None


def _eval_expr(
    expr: InferenceExpression,
    stat_map: dict[str, Statistic],
    conjuncts: list[CmpEvaluation],
) -> bool | None:
    """Walk the inference expression. Appends one CmpEvaluation per leaf.

    Three-valued logic:
      - AND: any False ⇒ False; else any None ⇒ None; else True
      - OR:  any True  ⇒ True;  else any None ⇒ None; else False
      - NOT: None → None; otherwise flips
    """
    if isinstance(expr, InferenceAnd):
        any_null = False
        for term in expr.terms:
            v = _eval_expr(term, stat_map, conjuncts)
            if v is False:
                return False
            if v is None:
                any_null = True
        return None if any_null else True

    if isinstance(expr, InferenceOr):
        any_null = False
        for term in expr.terms:
            v = _eval_expr(term, stat_map, conjuncts)
            if v is True:
                return True
            if v is None:
                any_null = True
        return None if any_null else False

    if isinstance(expr, InferenceNot):
        v = _eval_expr(expr.term, stat_map, conjuncts)
        return None if v is None else not v

    # Leaf
    assert isinstance(expr, InferenceCmp)
    lhs_val = _resolve_stat_ref(expr.lhs, stat_map)

    rhs_stat_id: str | None
    rhs_transform: str | None
    if isinstance(expr.rhs, StatRef):
        rhs_val = _resolve_stat_ref(expr.rhs, stat_map)
        rhs_stat_id = expr.rhs.stat_id
        rhs_transform = expr.rhs.transform
    else:
        rhs_val = float(expr.rhs)
        rhs_stat_id = None
        rhs_transform = None

    result = _eval_cmp(lhs_val, expr.op, rhs_val)
    conjuncts.append(
        CmpEvaluation(
            lhs_stat_id=expr.lhs.stat_id,
            lhs_transform=expr.lhs.transform,
            lhs_value=lhs_val,
            op=expr.op,
            rhs_stat_id=rhs_stat_id,
            rhs_transform=rhs_transform,
            rhs_value=rhs_val,
            result=result,
        )
    )
    return result


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def evaluate(claim: FormalClaim, *, api_client: object | None = None) -> EvaluationResult:
    """Evaluate a FormalClaim's InferenceRule.

    Parameters
    ----------
    claim:
        The parsed FormalClaim fixture.
    api_client:
        If provided, materialization mode will be attempted. v0.1 is
        inference-only and ignores the client except to record that
        materialization was requested but is not yet implemented.

    Returns
    -------
    EvaluationResult
        Verdict + per-conjunct breakdown. In materialization mode the
        ``materialized`` and ``drift`` fields carry the live-API outputs.
    """
    stat_map = {s.id: s for s in claim.statistics}
    conjuncts: list[CmpEvaluation] = []
    root = _eval_expr(claim.inference.expression, stat_map, conjuncts)

    materialized: dict[str, float | int | str] | None = None
    drift: list[StatDrift] | None = None
    materialization_status: MaterializationStatus = "skipped_pinned_only"
    materialization_error: str | None = None

    if api_client is not None:
        from polymer_formalclaim.materialize import materialize_claim

        try:
            run = materialize_claim(claim, api_client)
        except Exception as exc:  # pragma: no cover — guard
            materialization_status = "error"
            materialization_error = f"{type(exc).__name__}: {exc}"
        else:
            # Status maps 1:1 — materialize uses the same vocabulary.
            materialization_status = run.status  # type: ignore[assignment]
            if run.error:
                materialization_error = run.error
            if run.materialized:
                materialized = dict(run.materialized)
            if run.drift:
                drift = [
                    StatDrift(
                        stat_id=d.stat_id,
                        pinned=d.pinned,
                        computed=d.computed,
                        abs_diff=d.abs_diff,
                        rel_diff=d.rel_diff,
                        within_tolerance=d.within_tolerance,
                    )
                    for d in run.drift
                ]

    if root is True:
        verdict: Verdict = "LICENSED"
    elif root is False:
        verdict = "REJECTED"
    else:
        verdict = "PENDING"

    return EvaluationResult(
        claim_id=claim.id,
        schema_version=claim.schema_version,
        verdict=verdict,
        conjuncts=conjuncts,
        materialized=materialized,
        drift=drift,
        materialization_status=materialization_status,
        materialization_error=materialization_error,
        evaluated_at=datetime.now(UTC).isoformat(timespec="seconds"),
        api_version=claim.api_version,
        data_version=claim.data_version,
    )
