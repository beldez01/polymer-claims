"""sensor::senseability — the RNA-editing sensor geometry-tier capability (bridge C3 + C5).

Two INDEPENDENT legs classify a variant window into its ordinal senseability tier and return the
tier's ordinal integer. Leg A = SensorKit's own `classify_variant` (the reference apparatus); Leg B
= `reimpl_classify_variant`, a genuinely separate reimplementation written against the frozen public
geometry contract (NOT importing SensorKit). The GE criterion licenses iff BOTH legs' tier ordinals
clear the pre-registered tier bar, so a REPRODUCED license means two air-gapped classifiers agree.

SensorKit is imported LAZILY inside `execute` only, so importing this module (and the umbrella) never
requires SensorKit to be installed. Umbrella/impure; NOT re-exported from __init__.
"""
from __future__ import annotations

from polymer_grammar import (
    Claim,
    Comparator,
    ExecValue,
    GenerationMode,
    OperationNode,
    PendingReason,
    Provenance,
    QuantityLeaf,
    SatisfactionCriterion,
    Status,
    StrengthVector,
)
from polymer_grammar.leaf import MeasurementBasis, MeasurementContext
from polymer_grammar.oracle import ApplicabilityDomain, OracleDossier, ValidationTier
from polymer_grammar.subject import Subject
from polymer_protocol import AdapterCredential, AdapterRegistry, OracleRegistry

from .adapter_identity import implementation_hash_for_adapter
from .sensor_senseability_reimpl import TIER_ORDINAL as _TIER_ORDINAL
from .sensor_senseability_reimpl import reimpl_classify_variant

_IMPL = "sensor::senseability"
_ORACLE_ID = "sensor_senseability_apparatus"


class SensorSenseabilitySensorKitAdapter:
    """Leg A — SensorKit's reference `classify_variant`. Returns the tier's ordinal integer."""

    identity = "sensor-senseability-sensorkit"

    def execute(self, node: OperationNode, upstream, ctx) -> ExecValue:
        if node.impl != _IMPL:
            raise ValueError(f"{_IMPL} adapter cannot execute impl {node.impl!r}")
        p = {k: v for k, v in node.params}
        from sensorkit import Variant, classify_variant  # lazy — SensorKit optional at import

        v = Variant(
            gene=p.get("gene", "n/a"),
            name=p.get("name", "n/a"),
            hgvs_c="n/a",
            window_wt=p["window_wt"],
            window_mut=p["window_mut"],
            var_index=int(p["var_index"]),
            tpm=0.0,
        )
        return ExecValue(value=float(_TIER_ORDINAL[classify_variant(v, int(p["max_dist"]))]))


class SensorSenseabilityReimplAdapter:
    """Leg B — the INDEPENDENT reimplementation (`reimpl_classify_variant`); no SensorKit import."""

    identity = "sensor-senseability-reimpl"

    def execute(self, node: OperationNode, upstream, ctx) -> ExecValue:
        if node.impl != _IMPL:
            raise ValueError(f"{_IMPL} adapter cannot execute impl {node.impl!r}")
        p = {k: v for k, v in node.params}
        tier = reimpl_classify_variant(
            p["window_wt"], p["window_mut"], int(p["var_index"]), int(p["max_dist"])
        )
        return ExecValue(value=float(_TIER_ORDINAL[tier]))


def sensor_senseability_oracle_id() -> str:
    return _ORACLE_ID


def sensor_senseability_oracle_registry() -> OracleRegistry:
    return OracleRegistry(dossiers=(OracleDossier(
        oracle_id=_ORACLE_ID, validation_tier=ValidationTier.BENCHMARKED,
        applicability_domain=ApplicabilityDomain(subject_kinds=("variant_vrs", "genomic_region")),
        anchor="sensorkit-senseability-knownanswers-v1"),))


def sensor_senseability_registry() -> AdapterRegistry:
    return AdapterRegistry(credentials=(
        AdapterCredential(
            identity="sensor-senseability-sensorkit", owner="owner-sensorkit-apparatus",
            implementation_hash=implementation_hash_for_adapter(SensorSenseabilitySensorKitAdapter)),
        AdapterCredential(
            identity="sensor-senseability-reimpl", owner="owner-senseability-reimpl",
            implementation_hash=implementation_hash_for_adapter(SensorSenseabilityReimplAdapter)),
    ))


def sensor_senseability_claim(
    claim_id: str, *, ref: str, subject: Subject, window_wt: str, window_mut: str,
    var_index: int, max_dist: int, mode: str = "snv", tier_bar: int = 1,
    gene: str | None = None, name: str | None = None, search_cardinality: int = 1,
    agent_id: str = "sensor-senseability-v1", prior_cohorts: tuple[str, ...] = (),
    preregistration_hash: str | None = None, strength: StrengthVector | None = None,
) -> Claim:
    """PENDING claim: the variant window's ordinal senseability tier clears `tier_bar` (a GE bound
    on a QuantityLeaf carrying the pre-registered ordinal bar). The COMPUTED tier never enters the
    leaf — the leaf carries the bar; the GE criterion on both independent legs is the gate."""
    from polymer_grammar.capability import build_evaluation_plan

    from .capabilities import SENSOR_SENSEABILITY_CELL
    from .sensor_senseability_patterns import SENSOR_SENSEABILITY

    params = {
        "window_wt": window_wt, "window_mut": window_mut,
        "var_index": str(int(var_index)), "max_dist": str(int(max_dist)), "mode": mode,
    }
    if gene is not None:
        params["gene"] = gene
    if name is not None:
        params["name"] = name
    plan = build_evaluation_plan(
        SENSOR_SENSEABILITY_CELL,
        params=params,
        data_ref=ref,
        criterion=SatisfactionCriterion(comparator=Comparator.GE, reference_leaf_index=0),
        oracle_ref=_ORACLE_ID)
    leaf = QuantityLeaf(value=float(tier_bar),
                        measurement_basis=MeasurementBasis.DERIVED,
                        formula="variant_senseability_tier_ordinal >= tier_bar",
                        context=MeasurementContext(assay="SensorKit geometry tier"))
    return Claim(
        id=claim_id,
        title=f"{name or claim_id} senseability tier clears bar {tier_bar} ({mode})",
        pattern=SENSOR_SENSEABILITY, leaves=(leaf,),
        status=Status.PENDING, pending_reason=PendingReason.UNTESTED, strength=strength,
        subject=subject, evaluation_plan=plan,
        provenance=Provenance(generated_by=GenerationMode.AGENT_GENERATED, agent_id=agent_id,
                              search_cardinality=int(search_cardinality),
                              preregistration_hash=preregistration_hash, prior_cohorts=prior_cohorts,
                              rationale=f"reproduced senseability tier: {name or claim_id} ({mode})"))
