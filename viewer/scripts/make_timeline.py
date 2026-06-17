"""Generate a visually-evolving sample TopologyTimeline for the Claims Universe viewer.

Builds a real seed corpus through the engine (polymer_grammar + polymer_protocol) and calls
`export_timeline(...)`, then writes the JSON to viewer/public/sample-timeline.json. The timeline
plays back the universe GROWING and LICENSING across run_cycle iterations, warm-started so existing
claims hold their place and only new structure perturbs locally.

RUN (from the protocol uv env so polymer_grammar / polymer_protocol resolve):

    cd /Users/zbb2/Desktop/polymer-claims/protocol \
      && uv run python ../viewer/scripts/make_timeline.py

The seed corpus is engineered so the playback visibly evolves across >= 8 cycles:
  - ~10 PENDING-with-plan claims with distinct per-claim costs + a modest per-cycle budget, so a
    couple LICENSE each cycle (progressive licensing — a node turns amber -> blue over frames),
  - a POSITIVE-conclusion planless claim + the `rival_generation` proposer, so new `gen-rival-*`
    CONJECTURED nodes APPEAR in the early frames (and converge),
  - a `revision_proposer` that introduces a representation-revision CONJECTURED node MID-timeline
    (once a sentinel claim has licensed) — the octahedron glyph appears partway through.
"""
from __future__ import annotations

from pathlib import Path

from polymer_grammar import (
    CategoricalLeaf,
    Claim,
    Comparator,
    ComputeGraph,
    Direction,
    EvaluationPlan,
    FDRLedger,
    MaterializationContext,
    MeasurementBasis,
    OperationNode,
    PatternRef,
    PatternTarget,
    PendingReason,
    ProducedLeafSpec,
    Proposition,
    Provenance,
    GenerationMode,
    RepresentationRevision,
    RevisionOperation,
    SatisfactionCriterion,
    Status,
)

from polymer_protocol import (
    Corpus,
    CostModel,
    CostVector,
    Layout,
    Proposal,
    export_timeline,
)
from polymer_protocol.proposers import rival_generation
from polymer_grammar import IdentityAdapter, ReferenceAdapter

P_EFFECT = PatternRef(id="adjusted_effect", version="v1")
P_MEDIATION = PatternRef(id="mediation", version="v1")
P_DOSE = PatternRef(id="dose_response", version="v1")

_ADAPTERS = (IdentityAdapter(), ReferenceAdapter(identity="reference"))
_CTX = MaterializationContext(id="M1", api_version="v1", data_version="d1")

_REV_ID = "C-rev-saturating"
_SENTINEL = "C03"  # once this licenses, the representation-revision node appears


def make_plan(value: float, threshold: float, comparator: Comparator = Comparator.LT) -> EvaluationPlan:
    node = OperationNode(
        id="n0",
        impl="builtin::const",
        params=(("value", str(value)),),
        produces=ProducedLeafSpec(leaf_kind="quantity", measurement_basis=MeasurementBasis.DERIVED),
    )
    return EvaluationPlan(
        graph=ComputeGraph(nodes=(node,), terminal="n0"),
        criterion=SatisfactionCriterion(comparator=comparator, threshold=threshold),
    )


def pending(cid: str, pattern: PatternRef, value: float) -> Claim:
    """A strength-None PENDING claim with a SATISFIED plan (value < 0.05) — it licenses once selected.

    strength=None exempts the claim from the cardinality-scaled BH bar so it licenses on the cycle
    it is selected (a strength vector would need evidence_against_null >= 1 - q/M to clear a deep
    pool); this is the same exemption the conftest fixtures rely on."""
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


def build_seed_corpus() -> tuple[Corpus, CostModel]:
    claims: list[Claim] = []

    # ~10 PENDING-with-plan claims across 3 patterns. Distinct plan values keep canonicalize from
    # collapsing them; strength=None exempts them from the BH bar (they license when selected);
    # distinct ascending per-claim costs + a modest per-cycle budget license a couple each cycle, so
    # licensing spreads visibly across frames. `_SENTINEL` sits late so its licensing (and the
    # representation-revision it unlocks) lands mid-to-late in the playback.
    specs = [
        ("A01", P_EFFECT, 0.010),
        ("A02", P_EFFECT, 0.011),
        ("A03", P_EFFECT, 0.012),
        ("B01", P_MEDIATION, 0.013),
        ("B02", P_MEDIATION, 0.014),
        ("B03", P_MEDIATION, 0.015),
        ("C01", P_DOSE, 0.016),
        ("C02", P_DOSE, 0.017),
        (_SENTINEL, P_DOSE, 0.018),
        ("C04", P_DOSE, 0.019),
    ]
    for cid, pat, val in specs:
        claims.append(pending(cid, pat, val))

    # A POSITIVE-conclusion planless claim — rival_generation elaborates new CONJECTURED nodes
    # off it in the early frames (and converges, so growth is finite).
    concl = Proposition(direction=Direction.POSITIVE, estimand="beta", descriptor="dose drives effect")
    claims.append(
        Claim(
            id="SRC", title="claim SRC", pattern=P_DOSE,
            leaves=(CategoricalLeaf(ontology_term="term-SRC"),),
            status=Status.CONJECTURED, conclusion=concl,
        )
    )

    corpus = Corpus(claims=tuple(claims), fdr_ledger=FDRLedger(target_fdr=0.05))

    # Per-claim costs ascending with the spec order; a small per-cycle budget then licenses the
    # cheapest still-PENDING claims first -> licensing spreads across cycles.
    # Uniform unit cost: SELECT then orders equal-value candidates by id and fills the budget
    # greedily, so ~2 still-PENDING claims (in ascending id order) license each cycle until the
    # pool drains — progressive licensing the playback can show frame by frame.
    cost_model = CostModel(default=CostVector(wall_latency=1.0))
    return corpus, cost_model


def revision_proposer(corpus: Corpus, frontier: tuple[str, ...]) -> tuple[Proposal, ...]:
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
            generated_by=GenerationMode.AGENT_GENERATED, agent_id="revision-proposer",
            search_cardinality=1,
        ),
        representation_revision=RepresentationRevision(
            operation=RevisionOperation.ADD,
            target=PatternTarget(patterns=(PatternRef(id="dose_response_saturating", version="v1"),)),
            rationale="the corpus keeps re-deriving a saturating dose-response shape; add the pattern",
        ),
    )
    return (Proposal(operator_id="revision-proposer", claim=rev),)


def main() -> None:
    corpus, cost_model = build_seed_corpus()
    timeline = export_timeline(
        corpus, _ADAPTERS, _CTX,
        n_cycles=9,
        layout=Layout.FORCE_DIRECTED,
        proposers=(rival_generation, revision_proposer),
        cost_model=cost_model,
        budget=2.5,  # ~2 still-PENDING claims (by ascending id) license each cycle
        evidence={cid: 1_000_000.0 for cid, _, _ in [
            ("A01", P_EFFECT, 0.010),
            ("A02", P_EFFECT, 0.011),
            ("A03", P_EFFECT, 0.012),
            ("B01", P_MEDIATION, 0.013),
            ("B02", P_MEDIATION, 0.014),
            ("B03", P_MEDIATION, 0.015),
            ("C01", P_DOSE, 0.016),
            ("C02", P_DOSE, 0.017),
            (_SENTINEL, P_DOSE, 0.018),
            ("C04", P_DOSE, 0.019),
        ]},
    )

    out = Path(__file__).resolve().parent.parent / "public" / "sample-timeline.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(timeline.model_dump_json(indent=2))

    print(f"wrote {out}")
    print(f"  frames: {len(timeline.frames)} (n_cycles={timeline.n_cycles})")
    for f in timeline.frames:
        s = f.stats
        rev = sum(1 for n in f.topology.nodes if n.is_representation_revision)
        print(
            f"  frame {s.cycle_index:>2}: nodes={s.n_nodes:>2} licensed={s.n_licensed:>2} "
            f"pending={s.n_pending:>2} conjectured={s.n_conjectured:>2} edges={s.n_edges:>2} "
            f"+added={s.n_added} +licensed={s.n_newly_licensed} revisions={rev}"
        )


if __name__ == "__main__":
    main()
