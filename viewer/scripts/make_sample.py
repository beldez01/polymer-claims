"""Generate a visually-rich sample TopologyExport for the Claims Universe viewer.

Builds a real corpus through the engine (polymer_grammar + polymer_protocol) and
calls `export_topology(corpus, layout=Layout.FORCE_DIRECTED)`, then writes the JSON
to viewer/public/sample-topology.json.

RUN (from the protocol uv env so polymer_grammar / polymer_protocol resolve):

    cd /Users/zbb2/Desktop/polymer-claims/protocol \
      && uv run python ../viewer/scripts/make_sample.py

The corpus is engineered to exercise EVERY visual case the viewer encodes:
  - >= 24 claims across 3 patterns -> 3 clusters,
  - ALL 5 statuses (licensed / pending / exploratory / conjectured / rejected),
  - several defeat edges (rebut / undercut / undermine) mixing effective + provisional,
  - >= 1 equivalence edge, >= 1 entails edge (conclusion ENTAILS neighborhood),
  - >= 1 representation-revision node (octahedron glyph),
  - several claims carrying a strength 6-vector.
"""
from __future__ import annotations

import json
from pathlib import Path

from polymer_grammar import (
    CategoricalLeaf,
    Claim,
    DefeatEdge,
    DefeatEdgeKind,
    Direction,
    EquivalenceClaim,
    FDRLedger,
    FDRTest,
    LicenseRoute,
    Licensing,
    MaterializationContext,
    NeighborEdge,
    NeighborEdgeKind,
    OntologyTerm,
    PatternRef,
    PendingReason,
    Proposition,
    RepresentationRevision,
    RevisionOperation,
    PatternTarget,
    RivalSetClosure,
    Satisfaction,
    SatisfactionVerdict,
    Status,
    StrengthVector,
)

from polymer_protocol.corpus import Corpus
from polymer_protocol.topology import Layout, export_topology

# Three patterns -> three clusters in the export.
P_EFFECT = PatternRef(id="adjusted_effect", version="v1")
P_MEDIATION = PatternRef(id="mediation", version="v1")
P_DOSE = PatternRef(id="dose_response", version="v1")


def sv(mag, cert, ean, sev, wc, ev) -> StrengthVector:
    return StrengthVector(
        magnitude=mag,
        certainty=cert,
        evidence_against_null=ean,
        severity=sev,
        world_contact=wc,
        explanatory_virtue=ev,
    )


def ontology_subject(cid: str) -> OntologyTerm:
    return OntologyTerm(
        id=f"GO:{abs(hash(cid)) % 9_999_999:07d}",
        display=f"subject for {cid}",
        ontology="GO",
        ontology_release="2025-01-01",
        uri=f"http://purl.obolibrary.org/obo/GO_{abs(hash(cid)) % 9_999_999:07d}",
    )


def claim(
    cid: str,
    pattern: PatternRef,
    status: Status,
    *,
    strength: StrengthVector | None = None,
    conclusion: Proposition | None = None,
    licensing: Licensing | None = None,
    representation_revision: RepresentationRevision | None = None,
    with_subject: bool = True,
) -> Claim:
    pending_reason = PendingReason.CONTESTED if status == Status.PENDING else None
    return Claim(
        id=cid,
        title=f"claim {cid}",
        pattern=pattern,
        leaves=(CategoricalLeaf(ontology_term=f"term-{cid}"),),
        status=status,
        pending_reason=pending_reason,
        strength=strength,
        conclusion=conclusion,
        licensing=licensing,
        representation_revision=representation_revision,
        subject=ontology_subject(cid) if with_subject else None,
    )


def licensed_record() -> Licensing:
    """A valid severe-test licensing with an enumerated rival closure."""
    return Licensing(
        route=LicenseRoute.SEVERE_TEST,
        satisfactions=(
            Satisfaction(
                verdict=SatisfactionVerdict.SATISFIED,
                materialization=MaterializationContext(
                    id="M1", api_version="v1", data_version="d1"
                ),
            ),
        ),
        rival_set_closure=RivalSetClosure.ENUMERATED,
        rivals_considered=("rival_null", "rival_confound"),
    )


def replication_record() -> Licensing:
    """A REPLICATION licensing across two distinct materializations — used by the
    representation-revision node so it clears the meta-tier bar shape."""
    return Licensing(
        route=LicenseRoute.REPLICATION,
        satisfactions=(
            Satisfaction(
                verdict=SatisfactionVerdict.SATISFIED,
                materialization=MaterializationContext(
                    id="M1", api_version="v1", data_version="d1"
                ),
            ),
            Satisfaction(
                verdict=SatisfactionVerdict.SATISFIED,
                materialization=MaterializationContext(
                    id="M2", api_version="v2", data_version="d2"
                ),
            ),
        ),
        rival_set_closure=RivalSetClosure.ENUMERATED,
        rivals_considered=("schema_rival_a", "schema_rival_b"),
    )


def build_corpus() -> Corpus:
    claims: list[Claim] = []
    defeat_edges: list[DefeatEdge] = []
    equivalences: list[EquivalenceClaim] = []

    # ── Cluster A — adjusted_effect (10 claims, all 5 statuses present) ──────
    # Two LICENSED hub claims with a real ENTAILS link between their conclusions.
    concl_target = Proposition(
        direction=Direction.POSITIVE,
        estimand="effect_a_core",
        descriptor="core effect of A",
    )
    concl_source = Proposition(
        direction=Direction.POSITIVE,
        estimand="effect_a_strong",
        descriptor="strong effect of A",
        neighborhood=(
            NeighborEdge(
                kind=NeighborEdgeKind.ENTAILS,
                target=concl_target.content_hash,
                label="strong => core",
            ),
        ),
    )
    claims.append(
        claim(
            "A01",
            P_EFFECT,
            Status.LICENSED,
            strength=sv(0.92, 0.88, 0.95, 0.80, 0.85, 0.78),
            conclusion=concl_source,
            licensing=licensed_record(),
        )
    )
    claims.append(
        claim(
            "A02",
            P_EFFECT,
            Status.LICENSED,
            strength=sv(0.70, 0.82, 0.88, 0.66, 0.74, 0.71),
            conclusion=concl_target,
            licensing=licensed_record(),
        )
    )
    claims.append(claim("A03", P_EFFECT, Status.PENDING, strength=sv(0.55, 0.40, 0.50, 0.45, 0.50, 0.42)))
    claims.append(claim("A04", P_EFFECT, Status.EXPLORATORY, strength=sv(0.40, 0.30, 0.35, 0.30, 0.55, 0.48)))
    claims.append(claim("A05", P_EFFECT, Status.CONJECTURED))
    claims.append(claim("A06", P_EFFECT, Status.CONJECTURED, strength=sv(0.20, 0.15, 0.25, 0.18, 0.30, 0.22)))
    claims.append(claim("A07", P_EFFECT, Status.REJECTED, strength=sv(0.30, 0.20, 0.10, 0.25, 0.20, 0.15)))
    claims.append(claim("A08", P_EFFECT, Status.PENDING, strength=sv(0.48, 0.52, 0.44, 0.40, 0.46, 0.50)))
    claims.append(claim("A09", P_EFFECT, Status.EXPLORATORY))
    claims.append(claim("A10", P_EFFECT, Status.LICENSED, strength=sv(0.66, 0.71, 0.69, 0.60, 0.64, 0.62), licensing=licensed_record()))

    # ── Cluster B — mediation (9 claims) ─────────────────────────────────────
    claims.append(claim("B01", P_MEDIATION, Status.LICENSED, strength=sv(0.80, 0.78, 0.83, 0.70, 0.76, 0.74), licensing=licensed_record()))
    claims.append(claim("B02", P_MEDIATION, Status.PENDING, strength=sv(0.50, 0.45, 0.48, 0.42, 0.44, 0.40)))
    claims.append(claim("B03", P_MEDIATION, Status.EXPLORATORY, strength=sv(0.38, 0.28, 0.33, 0.31, 0.52, 0.46)))
    claims.append(claim("B04", P_MEDIATION, Status.CONJECTURED))
    claims.append(claim("B05", P_MEDIATION, Status.REJECTED, strength=sv(0.25, 0.18, 0.12, 0.20, 0.22, 0.16)))
    claims.append(claim("B06", P_MEDIATION, Status.PENDING, strength=sv(0.44, 0.40, 0.46, 0.38, 0.42, 0.45)))
    claims.append(claim("B07", P_MEDIATION, Status.CONJECTURED, strength=sv(0.22, 0.16, 0.20, 0.18, 0.26, 0.24)))
    claims.append(claim("B08", P_MEDIATION, Status.EXPLORATORY))
    claims.append(claim("B09", P_MEDIATION, Status.LICENSED, strength=sv(0.72, 0.69, 0.74, 0.62, 0.66, 0.64), licensing=licensed_record()))

    # ── Cluster C — dose_response (7 claims, incl. the meta-tier revision) ───
    claims.append(claim("C01", P_DOSE, Status.LICENSED, strength=sv(0.85, 0.80, 0.87, 0.72, 0.78, 0.76), licensing=licensed_record()))
    claims.append(claim("C02", P_DOSE, Status.PENDING, strength=sv(0.52, 0.47, 0.50, 0.43, 0.45, 0.41)))
    claims.append(claim("C03", P_DOSE, Status.EXPLORATORY, strength=sv(0.36, 0.27, 0.32, 0.29, 0.50, 0.44)))
    claims.append(claim("C04", P_DOSE, Status.CONJECTURED))
    claims.append(claim("C05", P_DOSE, Status.REJECTED, strength=sv(0.28, 0.19, 0.11, 0.22, 0.21, 0.17)))
    claims.append(claim("C06", P_DOSE, Status.CONJECTURED, strength=sv(0.21, 0.17, 0.23, 0.19, 0.28, 0.25)))
    # The representation-revision node — a meta-tier claim (octahedron glyph).
    claims.append(
        claim(
            "C07_REV",
            P_DOSE,
            Status.LICENSED,
            strength=sv(0.78, 0.84, 0.80, 0.75, 0.70, 0.88),
            licensing=replication_record(),
            representation_revision=RepresentationRevision(
                operation=RevisionOperation.ADD,
                target=PatternTarget(patterns=(PatternRef(id="dose_response_saturating", version="v1"),)),
                rationale="adds a saturating dose-response pattern the corpus keeps re-deriving",
            ),
        )
    )

    # ── Defeat edges — mix of kinds, effective + provisional ─────────────────
    # effective rebut (source not dominated by target): A07 rebuts A03
    defeat_edges.append(DefeatEdge(source="A07", target="A03", kind=DefeatEdgeKind.REBUT))
    # undercut within cluster A
    defeat_edges.append(DefeatEdge(source="A06", target="A04", kind=DefeatEdgeKind.UNDERCUT))
    # undermine across to a licensed hub (stands — A05 has no strength)
    defeat_edges.append(DefeatEdge(source="A05", target="A10", kind=DefeatEdgeKind.UNDERMINE))
    # provisional defeat (inert until source LICENSED -> source A09 is EXPLORATORY, so ghosted)
    defeat_edges.append(DefeatEdge(source="A09", target="A08", kind=DefeatEdgeKind.REBUT, provisional=True))
    # cluster B defeats
    defeat_edges.append(DefeatEdge(source="B05", target="B02", kind=DefeatEdgeKind.REBUT))
    defeat_edges.append(DefeatEdge(source="B07", target="B03", kind=DefeatEdgeKind.UNDERCUT))
    defeat_edges.append(DefeatEdge(source="B04", target="B06", kind=DefeatEdgeKind.UNDERMINE, provisional=True))
    # cluster C defeats + a provisional one
    defeat_edges.append(DefeatEdge(source="C05", target="C02", kind=DefeatEdgeKind.REBUT))
    defeat_edges.append(DefeatEdge(source="C06", target="C03", kind=DefeatEdgeKind.RECLASSIFY))
    defeat_edges.append(DefeatEdge(source="C04", target="C01", kind=DefeatEdgeKind.UNDERMINE, provisional=True))
    # a cross-cluster defeat so the clusters are visibly linked
    defeat_edges.append(DefeatEdge(source="B05", target="A03", kind=DefeatEdgeKind.REINTERPRET))

    # ── Equivalence edges (>=1) ──────────────────────────────────────────────
    equivalences.append(
        EquivalenceClaim(
            id="EQ01", left="A02", right="B01", severity=0.6, status=Status.LICENSED
        )
    )
    equivalences.append(
        EquivalenceClaim(
            id="EQ02", left="B09", right="C01", severity=0.55, status=Status.LICENSED
        )
    )

    return Corpus(
        claims=tuple(claims),
        defeat_edges=tuple(defeat_edges),
        equivalences=tuple(equivalences),
        fdr_ledger=FDRLedger(
            target_fdr=0.05,
            tests=(
                FDRTest(
                    index=1,
                    claim_id="A01",
                    e_value=1000.0,
                    alpha_allocated=0.030396,
                    discovery=True,
                ),
                FDRTest(
                    index=2,
                    claim_id="A07",
                    e_value=500.0,
                    alpha_allocated=0.015198,
                    discovery=True,
                    retracted=True,
                ),
                FDRTest(
                    index=3,
                    claim_id="A03",
                    e_value=0.7,
                    alpha_allocated=0.006755,
                    discovery=False,
                ),
            ),
        ),
    )


def main() -> None:
    corpus = build_corpus()
    export = export_topology(corpus, layout=Layout.FORCE_DIRECTED)

    out = Path(__file__).resolve().parent.parent / "public" / "sample-topology.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(export.model_dump_json(indent=2))

    statuses = {n.status for n in export.nodes}
    kinds = {e.kind for e in export.edges}
    print(f"wrote {out}")
    print(f"  nodes: {len(export.nodes)}  edges: {len(export.edges)}  clusters: {len(export.clusters)}")
    print(f"  statuses: {sorted(statuses)}")
    print(f"  edge kinds: {sorted(kinds)}")
    print(f"  provisional edges: {sum(1 for e in export.edges if e.provisional)}")
    print(f"  effective edges: {sum(1 for e in export.edges if e.effective)}")
    print(f"  representation revisions: {sum(1 for n in export.nodes if n.is_representation_revision)}")
    print(f"  with strength: {sum(1 for n in export.nodes if n.strength is not None)}")


if __name__ == "__main__":
    main()
