"""Deterministic manifest -> Claim builder. Same manifests => same claims (byte-stable).

Every claim is reported-stratum: LITERATURE_EXTRACTED / CONJECTURED. Nothing here licenses.
"""
from __future__ import annotations

from pathlib import Path

from polymer_grammar.claim import Claim
from polymer_grammar.leaf import (
    MeasurementBasis,
    MeasurementContext,
    PropositionLeaf,
    QuantityLeaf,
)
from polymer_grammar.provenance import GenerationMode, Provenance
from polymer_grammar.status import Status

from .manifest import ManifestEntry, load_manifest
from .patterns import MECHANISTIC_LAW, REPORTED_QUANTITY
from .sources import SOURCES


def _provenance(source_key: str) -> Provenance:
    src = SOURCES[source_key]
    return Provenance(
        generated_by=GenerationMode.LITERATURE_EXTRACTED,
        method=src.ref,
        version=src.title,
        search_cardinality=1,
    )


def _context(raw: dict | None) -> MeasurementContext | None:
    if not raw or not any(raw.get(k) for k in ("tissue", "cell_line", "assay", "condition")):
        return None
    return MeasurementContext(
        tissue=raw.get("tissue"),
        cell_line=raw.get("cell_line"),
        assay=raw.get("assay"),
        condition=raw.get("condition"),
    )


def build_claim(entry: ManifestEntry) -> Claim:
    leaf_spec = entry.leaf
    if leaf_spec.kind == "quantity":
        leaf: object = QuantityLeaf(
            value=leaf_spec.value,
            unit=leaf_spec.unit,
            uncertainty=leaf_spec.uncertainty,
            measurement_basis=MeasurementBasis[leaf_spec.measurement_basis],
            formula=leaf_spec.formula,
            context=_context(leaf_spec.context),
            low=leaf_spec.low,
            high=leaf_spec.high,
        )
        pattern = REPORTED_QUANTITY
    elif leaf_spec.kind == "proposition":
        leaf = PropositionLeaf(
            data=leaf_spec.data,
            warrant=leaf_spec.warrant,
            rebuttal=leaf_spec.rebuttal,
            warrant_type=leaf_spec.warrant_type or "mechanistic_analogy",
        )
        pattern = MECHANISTIC_LAW
    else:
        raise ValueError(f"{entry.id}: unknown leaf kind {leaf_spec.kind!r}")
    return Claim(
        id=entry.id,
        title=entry.title,
        pattern=pattern,
        leaves=(leaf,),
        status=Status.CONJECTURED,
        provenance=_provenance(entry.source),
    )


def build_manifest_claims(paths: list[Path]) -> tuple[list[Claim], dict[str, str]]:
    claims: list[Claim] = []
    topics: dict[str, str] = {}
    for path in paths:
        for entry in load_manifest(path):
            if entry.skip or entry.tier >= 3:
                continue
            claims.append(build_claim(entry))
            topics[entry.id] = entry.topic
    return claims, topics


def collect_all_synbio_claims() -> tuple[list[Claim], dict[str, str]]:
    """The 5 probe factory claims + every non-skipped manifest claim, with a topic map.
    Probe claims get a static topic; manifest claims carry their own."""
    from .probe import build_all

    _PROBE_TOPICS = {
        "synbio-c1-mismatch-energy": "sensing",
        "synbio-c2-adar-dynamic-range": "sensing",
        "synbio-c3-car-threshold": "sensing",
        "synbio-c4-endosomal-escape": "delivery",
        "synbio-c5-affinity-discrimination-law": "sensing",
    }
    manifest_dir = Path(__file__).resolve().parents[3] / "data/synbio_compendia/manifests"
    paths = sorted(manifest_dir.glob("*.json"))
    m_claims, m_topics = build_manifest_claims(paths)

    claims = list(build_all()) + m_claims
    topics = {**_PROBE_TOPICS, **m_topics}
    return claims, topics
