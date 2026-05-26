"""materialize.py — FormalClaim evaluator v0.2 materialization layer.

Implements the operation-DAG materialization pathway that v0.1 stubbed.
Walks a claim's ``EstimatorOp`` (and related op) list, dispatches each
one's ``EstimatorSpec.impl`` through a prefix registry, and collects the
resulting computed statistics into a drift report against the pinned
values.

Design
------
* **Eligibility gate** runs first. A claim is materialization-eligible
  iff every premise has a supported ``provenance_state`` (``fly_postgres``
  or ``canonical_db``; ``local_rds`` is not materializable by a remote API).
  A claim whose gate fails returns a ``skipped_ineligible`` result; the
  inference verdict from ``evaluate()`` is unaffected.
* **Dispatch registry** maps an ``EstimatorSpec.impl`` prefix to a handler
  function. The built-in registry ships with these prefixes recognized:

    ``python::polymer_genomics.stats.identity``
        In-process passthrough handler (testing). Copies the pinned
        value of the produced statistics to ``materialized`` with zero
        drift. Proves the plumbing end-to-end without needing network or
        R.

    ``scipy.stats.*``, ``python::sklearn.*``, ``R::*``
        Registered as *known* prefixes, but each raises
        ``HandlerNotImplemented`` until the full adapter lands. Claims
        that route here surface as ``partial`` (some handlers worked) or
        ``skipped_ineligible`` with a specific missing-handler reason.

* **Status resolution** folds the individual op outcomes:

    all estimator ops handled               → ``complete``
    some handled, some missing-handler      → ``partial``
    none handled, all missing-handler       → ``skipped_ineligible``
    claim has no estimator ops              → ``complete`` (trivially)
    exception during any handler            → ``error``

* The caller receives a ``MaterializationRun`` with everything needed
  to populate the evaluation-result's ``materialized`` / ``drift`` /
  ``materialization_status`` / ``materialization_error`` fields.

v0.2 ships the framework + the identity handler. Subsequent patches add
real scipy / sklearn / R handlers without changing the surface API.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Callable, Protocol

from polymer_formalclaim.schema import (
    EstimatorOp,
    FormalClaim,
    Operation,
    ProvenanceState,
    Statistic,
)

# ---------------------------------------------------------------------------
# Public exception + protocol types
# ---------------------------------------------------------------------------


class HandlerNotImplemented(Exception):
    """A registered handler prefix recognizes the impl but has no body yet."""


class HandlerFailure(Exception):
    """A handler attempted materialization and failed with a concrete error."""


class MaterializationHandler(Protocol):
    """Signature every dispatch handler implements.

    The handler returns a mapping ``{stat_id: computed_value}`` for the
    statistics produced by this operation. Any other statistic IDs are
    silently ignored by the caller.
    """

    def __call__(
        self,
        op: EstimatorOp,
        claim: FormalClaim,
        produced_stat_ids: list[str],
        api_client: object,
    ) -> dict[str, float | int | str]:
        ...


# ---------------------------------------------------------------------------
# Eligibility
# ---------------------------------------------------------------------------

# Provenance states whose data can be resolved via the live Polymer API.
_MATERIALIZABLE_PROVENANCE: frozenset[ProvenanceState] = frozenset(
    {"fly_postgres", "canonical_db"}  # type: ignore[arg-type]
)


@dataclass(frozen=True)
class EligibilityResult:
    ok: bool
    reasons: tuple[str, ...] = ()


def check_eligibility(claim: FormalClaim) -> EligibilityResult:
    """Decide whether a claim can be materialized end-to-end.

    A claim is ineligible if any premise's data is not reachable through
    the API. The caller may still choose to attempt partial materialization
    — this function is purely a gate-check helper.
    """
    reasons: list[str] = []
    for prem in claim.premises:
        state = prem.source.provenance_state
        if state not in _MATERIALIZABLE_PROVENANCE:
            reasons.append(
                f"premise {prem.id!r} has provenance_state={state!r}; "
                f"materialization supports only {sorted(_MATERIALIZABLE_PROVENANCE)}"
            )
    return EligibilityResult(ok=not reasons, reasons=tuple(reasons))


# ---------------------------------------------------------------------------
# Dispatch registry
# ---------------------------------------------------------------------------


@dataclass
class _HandlerEntry:
    prefix: str
    handler: MaterializationHandler | None
    # ``None`` handler means prefix is recognized but not yet implemented.


_REGISTRY: list[_HandlerEntry] = []


def register_handler(prefix: str, handler: MaterializationHandler | None) -> None:
    """Register a handler under an ``EstimatorSpec.impl`` prefix.

    Handlers are matched longest-prefix-wins on the op's ``impl`` string.
    Pass ``handler=None`` to register a prefix as *recognized but not yet
    implemented* (the dispatcher will emit ``HandlerNotImplemented``).
    """
    # Replace any existing entry with the same prefix.
    for i, entry in enumerate(_REGISTRY):
        if entry.prefix == prefix:
            _REGISTRY[i] = _HandlerEntry(prefix=prefix, handler=handler)
            return
    _REGISTRY.append(_HandlerEntry(prefix=prefix, handler=handler))


def _dispatch(impl: str) -> _HandlerEntry | None:
    """Return the longest-prefix-matching handler entry, or None."""
    best: _HandlerEntry | None = None
    for entry in _REGISTRY:
        if impl.startswith(entry.prefix):
            if best is None or len(entry.prefix) > len(best.prefix):
                best = entry
    return best


# ---------------------------------------------------------------------------
# Built-in handler: in-process identity (v0.2 demonstration)
# ---------------------------------------------------------------------------


def _identity_handler(
    op: EstimatorOp,
    claim: FormalClaim,
    produced_stat_ids: list[str],
    api_client: object,
) -> dict[str, float | int | str]:
    """Pure-function passthrough. Returns each produced stat's pinned value.

    Useful as a smoke-test target. Real handlers replace the pinned-value
    read with a live computation against the API or a subprocess.
    """
    _ = (claim, api_client)  # unused; signature parity only
    stat_map = {s.id: s for s in claim.statistics}
    out: dict[str, float | int | str] = {}
    for sid in produced_stat_ids:
        stat = stat_map.get(sid)
        if stat is None:
            continue
        v = stat.value
        if isinstance(v, bool):
            out[sid] = str(v)
        elif isinstance(v, (int, float, str)):
            out[sid] = v
        # list-valued stats are silently skipped by the identity handler.
    return out


# ---------------------------------------------------------------------------
# Built-in handler: scipy.stats correlation tests
# ---------------------------------------------------------------------------

# Minimum ``api_client`` protocol the scipy handler expects. A caller that
# wants scipy handlers to fire must supply an object exposing:
#
#     fetch_columns(layer: str, columns: Iterable[str]) -> dict[str, list[float]]
#
# Returns a column-major dict for the named layer. Any other shape raises
# ``HandlerNotImplemented`` so the calling harness falls through to other
# material sources without a hard crash.


_SCIPY_STAT_FUNCS = {
    "scipy.stats.spearmanr": "spearmanr",
    "scipy.stats.pearsonr": "pearsonr",
    "scipy.stats.kendalltau": "kendalltau",
    "python::scipy.stats.spearmanr": "spearmanr",
    "python::scipy.stats.pearsonr": "pearsonr",
    "python::scipy.stats.kendalltau": "kendalltau",
}


def _scipy_stats_handler(
    op: EstimatorOp,
    claim: FormalClaim,
    produced_stat_ids: list[str],
    api_client: object,
) -> dict[str, float | int | str]:
    """Compute a scipy.stats correlation test for the op's response vs features.

    Signature contract — the caller's ``api_client`` must expose:

        fetch_columns(layer: str, columns: Iterable[str]) -> dict[str, list[float]]

    Without that method the handler raises ``HandlerNotImplemented`` and the
    dispatcher marks the op as ``unsupported_impl`` — not an evaluator error,
    just a missing integration.
    """
    impl = op.estimator.impl
    func_name = _SCIPY_STAT_FUNCS.get(impl)
    if func_name is None:
        raise HandlerNotImplemented(
            f"scipy handler recognizes spearmanr/pearsonr/kendalltau only; got impl={impl!r}"
        )

    fetch = getattr(api_client, "fetch_columns", None)
    if fetch is None or not callable(fetch):
        raise HandlerNotImplemented(
            "scipy.stats handler requires api_client.fetch_columns(layer, columns). "
            "Supply an object with that duck-typed method to materialize correlation ops."
        )

    response_col = op.estimator.response
    features = op.estimator.features
    if response_col is None or features is None or not features.resolved:
        raise HandlerNotImplemented(
            f"scipy handler for op={op.id!r} needs EstimatorSpec.response and "
            "EstimatorSpec.features.resolved populated (the FeatureSet resolver has not run)."
        )

    # Resolve from whichever premise the estimator reads. For the op-DAG we
    # pick the first input; downstream joins are the caller's concern.
    source_premise_id = op.inputs[0] if op.inputs else None
    premise = next((p for p in claim.premises if p.id == source_premise_id), None)
    if premise is None:
        raise HandlerFailure(
            f"op {op.id} input {source_premise_id!r} does not match any premise"
        )
    layer = premise.source.layer

    # One pair of columns per feature → compute rho/p vs the response.
    try:
        import scipy.stats as stats  # local import keeps materialize.py cheap on cold start.
    except ImportError as exc:  # pragma: no cover
        raise HandlerNotImplemented(
            f"scipy is not importable in this environment: {exc}. "
            "Install scipy to enable this handler."
        )

    fn = getattr(stats, func_name)
    columns_needed = [response_col, *features.resolved]
    data = fetch(layer, columns_needed)

    y = data.get(response_col)
    if y is None:
        raise HandlerFailure(f"fetch_columns did not return response column {response_col!r}")

    # Each produced stat is a scalar; convention: one stat per feature (rho)
    # and one companion stat per feature (p-value) if named accordingly. v0.2
    # ships the simplest convention: one stat id that matches op.id receives
    # the average |rho|; callers can add a richer mapping once FeatureSet
    # carries per-feature stat ids.
    rhos: list[float] = []
    pvals: list[float] = []
    for col in features.resolved:
        x = data.get(col)
        if x is None:
            raise HandlerFailure(f"fetch_columns did not return feature column {col!r}")
        result = fn(x, y)
        # scipy returns a namedtuple-ish object; .statistic / .pvalue in modern scipy
        rho = float(getattr(result, "statistic", result[0]))
        pval = float(getattr(result, "pvalue", result[1]))
        rhos.append(rho)
        pvals.append(pval)

    mean_abs_rho = sum(abs(r) for r in rhos) / len(rhos) if rhos else 0.0
    min_pval = min(pvals) if pvals else 1.0

    # Populate whatever stat ids the op produces. Heuristic: if a produced
    # stat's name hints at a p-value, we give it the min_pval; otherwise
    # mean_abs_rho. Callers who need stricter wiring should use the op-DAG's
    # stat-spec names, not these heuristics.
    out: dict[str, float | int | str] = {}
    stat_map = {s.id: s for s in claim.statistics}
    for sid in produced_stat_ids:
        stat = stat_map.get(sid)
        lowered = (stat.name.lower() if stat else sid.lower())
        if "pval" in lowered or "p_value" in lowered or "p-value" in lowered:
            out[sid] = min_pval
        else:
            out[sid] = mean_abs_rho
    return out


# Bootstrap the registry with concrete handlers + recognized-but-pending
# external prefixes. Longest-prefix match wins.
register_handler("python::polymer_genomics.stats.identity", _identity_handler)
# Concrete scipy.stats handlers — exact-impl keys so they shadow the
# generic ``scipy.stats.`` placeholder.
for _impl in _SCIPY_STAT_FUNCS:
    register_handler(_impl, _scipy_stats_handler)
register_handler("scipy.stats.", None)            # other scipy.stats.* still pending
register_handler("python::scipy.stats.", None)
register_handler("python::sklearn.", None)
register_handler("R::", None)
register_handler("python::polymer_genomics.stats.", None)


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------


@dataclass
class OpOutcome:
    op_id: str
    impl: str
    status: str  # "materialized" | "unsupported_impl" | "handler_error" | "no_handler"
    materialized_stat_ids: tuple[str, ...] = ()
    error: str | None = None


@dataclass
class MaterializationRun:
    status: str  # "complete" | "partial" | "skipped_ineligible" | "error"
    materialized: dict[str, float | int | str] = field(default_factory=dict)
    drift: list["StatDriftRecord"] = field(default_factory=list)
    op_outcomes: list[OpOutcome] = field(default_factory=list)
    error: str | None = None


@dataclass
class StatDriftRecord:
    stat_id: str
    pinned: float | int | str | None
    computed: float | int | str | None
    abs_diff: float | None
    rel_diff: float | None
    within_tolerance: bool | None


def _compute_drift(
    pinned: Statistic | None,
    computed: float | int | str | None,
    *,
    abs_tol: float = 1e-9,
    rel_tol: float = 1e-6,
) -> StatDriftRecord:
    if pinned is None:
        return StatDriftRecord(
            stat_id="<unknown>",
            pinned=None,
            computed=computed,
            abs_diff=None,
            rel_diff=None,
            within_tolerance=None,
        )
    p_raw = pinned.value
    p_scalar = p_raw if isinstance(p_raw, (int, float, str)) and not isinstance(p_raw, bool) else None
    # Only compute numeric drift when both sides are numeric.
    if isinstance(p_scalar, (int, float)) and isinstance(computed, (int, float)):
        ad = abs(float(p_scalar) - float(computed))
        denom = max(abs(float(p_scalar)), abs(float(computed)), 1.0)
        rd = ad / denom
        within = ad <= abs_tol or rd <= rel_tol
        return StatDriftRecord(
            stat_id=pinned.id,
            pinned=p_scalar,
            computed=computed,
            abs_diff=ad,
            rel_diff=rd,
            within_tolerance=within,
        )
    return StatDriftRecord(
        stat_id=pinned.id,
        pinned=p_scalar,
        computed=computed,
        abs_diff=None,
        rel_diff=None,
        within_tolerance=(p_scalar == computed) if (p_scalar is not None and computed is not None) else None,
    )


def materialize_claim(claim: FormalClaim, api_client: object) -> MaterializationRun:
    """Attempt to materialize every estimator op in the claim.

    Eligibility is checked first; if the gate fails, no handlers are run
    and the return value is ``skipped_ineligible``.
    """
    gate = check_eligibility(claim)
    if not gate.ok:
        return MaterializationRun(
            status="skipped_ineligible",
            error="; ".join(gate.reasons),
        )

    estimator_ops = [op for op in claim.operations if isinstance(op, EstimatorOp)]
    if not estimator_ops:
        # Claims without any estimator ops (pure retrieval / proof claims) are
        # trivially "complete" with nothing to materialize.
        return MaterializationRun(status="complete")

    stat_by_producer: dict[str, list[str]] = {}
    for s in claim.statistics:
        stat_by_producer.setdefault(s.produced_by, []).append(s.id)

    stat_map = {s.id: s for s in claim.statistics}
    run = MaterializationRun(status="complete")

    for op in estimator_ops:
        impl = op.estimator.impl
        produced = stat_by_producer.get(op.id, [])
        entry = _dispatch(impl)
        if entry is None:
            run.op_outcomes.append(
                OpOutcome(
                    op_id=op.id,
                    impl=impl,
                    status="no_handler",
                    error=f"no registered handler for impl prefix of {impl!r}",
                )
            )
            continue
        if entry.handler is None:
            run.op_outcomes.append(
                OpOutcome(
                    op_id=op.id,
                    impl=impl,
                    status="unsupported_impl",
                    error=f"handler for prefix {entry.prefix!r} not yet implemented",
                )
            )
            continue
        try:
            computed = entry.handler(op, claim, produced, api_client)
        except HandlerNotImplemented as exc:
            run.op_outcomes.append(
                OpOutcome(
                    op_id=op.id,
                    impl=impl,
                    status="unsupported_impl",
                    error=str(exc) or f"handler for prefix {entry.prefix!r} raised NotImplemented",
                )
            )
            continue
        except Exception as exc:  # pragma: no cover — guard
            run.op_outcomes.append(
                OpOutcome(
                    op_id=op.id,
                    impl=impl,
                    status="handler_error",
                    error=f"{type(exc).__name__}: {exc}",
                )
            )
            run.status = "error"
            run.error = f"{op.id}: {exc}"
            continue

        run.op_outcomes.append(
            OpOutcome(
                op_id=op.id,
                impl=impl,
                status="materialized",
                materialized_stat_ids=tuple(computed.keys()),
            )
        )
        for sid, val in computed.items():
            run.materialized[sid] = val
            run.drift.append(_compute_drift(stat_map.get(sid), val))

    # Resolve overall status if not already set to error.
    if run.status == "error":
        return run
    statuses = {o.status for o in run.op_outcomes}
    if statuses == {"materialized"}:
        run.status = "complete"
    elif "materialized" in statuses and statuses - {"materialized"}:
        run.status = "partial"
    else:
        # Nothing materialized. Aggregate the missing-handler reasons into
        # a single error string so the caller can surface it.
        run.status = "skipped_ineligible"
        reasons = [
            f"{o.op_id}({o.impl}): {o.error}"
            for o in run.op_outcomes
            if o.status in {"no_handler", "unsupported_impl"}
        ]
        run.error = "; ".join(reasons) or "no estimator ops were materialized"
    return run


__all__ = [
    "HandlerNotImplemented",
    "HandlerFailure",
    "MaterializationHandler",
    "MaterializationRun",
    "OpOutcome",
    "StatDriftRecord",
    "EligibilityResult",
    "check_eligibility",
    "register_handler",
    "materialize_claim",
]
