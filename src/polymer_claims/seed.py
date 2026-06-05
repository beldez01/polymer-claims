"""An importable, visibly-evolving default seed corpus for the live node.

`default_seed_corpus()` returns `(corpus, run_cycle_kwargs)` where the kwargs
thread the `rival_generation` + `revision_proposer` proposers, a `CostModel`,
and a modest per-cycle `budget` into `run_cycle` (via `NodeRunner`). The seed is
engineered so the universe visibly GROWS and LICENSES across ticks:

  - ~6 PENDING-with-plan claims across the 3 patterns license a couple per cycle,
  - a POSITIVE-conclusion planless `"SRC"` CONJECTURED claim lets `rival_generation`
    elaborate new conjectured nodes early (and converge),
  - a `revision_proposer` adds a representation-revision CONJECTURED node ONCE the
    sentinel claim `"C03"` licenses (the octahedron glyph appears mid-timeline).

This module imports ONLY grammar/protocol — never fastapi/uvicorn — so the core
CLI stays importable without the optional `[serve]` extra. It is a TRIMMED port of
`viewer/scripts/make_timeline.py`'s `build_seed_corpus` + `revision_proposer`.
"""
from __future__ import annotations

from polymer_grammar import (
    CategoricalLeaf,
    Claim,
    Comparator,
    ComputeGraph,
    Direction,
    EvaluationPlan,
    FDRLedger,
    GenerationMode,
    MeasurementBasis,
    OperationNode,
    PatternRef,
    PatternTarget,
    PendingReason,
    ProducedLeafSpec,
    Proposition,
    Provenance,
    RepresentationRevision,
    RevisionOperation,
    SatisfactionCriterion,
    Status,
)
from polymer_protocol import Corpus, CostModel, CostVector, Proposal
from polymer_protocol.proposers import rival_generation

P_EFFECT = PatternRef(id="adjusted_effect", version="v1")
P_MEDIATION = PatternRef(id="mediation", version="v1")
P_DOSE = PatternRef(id="dose_response", version="v1")

_REV_ID = "C-rev-saturating"
_SENTINEL = "C03"  # once this licenses, the representation-revision node appears


def make_plan(
    value: float, threshold: float, comparator: Comparator = Comparator.LT
) -> EvaluationPlan:
    node = OperationNode(
        id="n0",
        impl="builtin::const",
        params=(("value", str(value)),),
        produces=ProducedLeafSpec(
            leaf_kind="quantity", measurement_basis=MeasurementBasis.DERIVED
        ),
    )
    return EvaluationPlan(
        graph=ComputeGraph(nodes=(node,), terminal="n0"),
        criterion=SatisfactionCriterion(comparator=comparator, threshold=threshold),
    )


def pending(cid: str, pattern: PatternRef, value: float) -> Claim:
    """A strength-None PENDING claim with a SATISFIED plan (value < 0.05) — licenses on select.

    strength=None exempts the claim from the cardinality-scaled BH bar so it licenses on the
    cycle it is selected; this is the same exemption the conftest fixtures rely on."""
    return Claim(
        id=cid,
        title=f"claim {cid}",
        pattern=pattern,
        leaves=(CategoricalLeaf(ontology_term=f"term-{cid}"),),
        status=Status.PENDING,
        pending_reason=PendingReason.UNTESTED,
        strength=None,
        evaluation_plan=make_plan(value, 0.05),
    )


def revision_proposer(
    corpus: Corpus, frontier: tuple[str, ...]
) -> tuple[Proposal, ...]:
    """Introduce a representation-revision CONJECTURED node ONCE the sentinel has licensed (so the
    octahedron glyph appears mid-timeline) — idempotent + convergent (emits nothing once present)."""
    by_id = corpus.by_id()
    if _REV_ID in by_id:
        return ()
    sentinel = by_id.get(_SENTINEL)
    if sentinel is None or sentinel.status != Status.LICENSED:
        return ()
    rev = Claim(
        id=_REV_ID,
        title="representation revision: saturating dose-response pattern",
        pattern=P_DOSE,
        leaves=(CategoricalLeaf(ontology_term="term-rev"),),
        status=Status.CONJECTURED,
        provenance=Provenance(
            generated_by=GenerationMode.AGENT_GENERATED,
            agent_id="revision-proposer",
            search_cardinality=1,
        ),
        representation_revision=RepresentationRevision(
            operation=RevisionOperation.ADD,
            target=PatternTarget(
                patterns=(PatternRef(id="dose_response_saturating", version="v1"),)
            ),
            rationale="the corpus keeps re-deriving a saturating dose-response shape; add the pattern",
        ),
    )
    return (Proposal(operator_id="revision-proposer", claim=rev),)


def default_seed_corpus() -> tuple[Corpus, dict]:
    """Build the built-in evolving seed corpus + the run_cycle kwargs that animate it."""
    claims: list[Claim] = []

    # ~6 PENDING-with-plan claims across the 3 patterns. Distinct ascending plan values keep
    # canonicalize from collapsing them; strength=None exempts them from the BH bar (they license
    # when selected). The sentinel `"C03"` sits late so its licensing (and the representation-
    # revision it unlocks) lands mid-to-late in the playback.
    specs = [
        ("A01", P_EFFECT, 0.010),
        ("A02", P_EFFECT, 0.011),
        ("B01", P_MEDIATION, 0.012),
        ("B02", P_MEDIATION, 0.013),
        ("C01", P_DOSE, 0.014),
        (_SENTINEL, P_DOSE, 0.015),
    ]
    for cid, pat, val in specs:
        claims.append(pending(cid, pat, val))

    # A POSITIVE-conclusion planless claim — rival_generation elaborates new CONJECTURED nodes
    # off it in the early frames (and converges, so growth is finite).
    concl = Proposition(
        direction=Direction.POSITIVE, estimand="beta", descriptor="dose drives effect"
    )
    claims.append(
        Claim(
            id="SRC",
            title="claim SRC",
            pattern=P_DOSE,
            leaves=(CategoricalLeaf(ontology_term="term-SRC"),),
            status=Status.CONJECTURED,
            conclusion=concl,
        )
    )

    corpus = Corpus(claims=tuple(claims), fdr_ledger=FDRLedger(target_fdr=0.05))

    # Uniform unit cost: SELECT orders equal-value candidates by id and fills the budget greedily,
    # so ~2 still-PENDING claims (ascending id) license each cycle until the pool drains.
    cost_model = CostModel(default=CostVector(wall_latency=1.0))

    run_cycle_kwargs = {
        "proposers": (rival_generation, revision_proposer),
        "cost_model": cost_model,
        "budget": 2.5,
    }
    return corpus, run_cycle_kwargs
