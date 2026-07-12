"""Merge all per-arm claims universes into ONE unified, faceted universe.

"One atom, many links" (`docs/superpowers/specs/2026-07-10-accumulating-universe-store-
design.md`): the atom is the content-addressed claim; which arm produced it and what
modality it reads are FACETS carried alongside the claim, never a separate universe.
`merge_universes` performs a UNION of already-decided claims — it does NOT re-run the
licensing gate. Each arm already decided its own claim statuses (pharmaco via
`run_cycle`, synbio as CONJECTURED literature claims, immuno/polymergenomics as
previously-licensed/rendered bundles); this module only content-address-dedups and tags
provenance, preserving every claim's status/e-value exactly as its arm produced it.

Umbrella-side only: grammar/protocol are untouched, and the merged `Corpus` stays
exactly the same 4 collections (claims, defeat_edges, equivalences, fdr_ledger) any
other `Corpus` has — the merge changes nothing about the shape, only the union.
"""
from __future__ import annotations

import hashlib
import logging
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

from polymer_grammar import Claim, DefeatEdge, EquivalenceClaim, FDRLedger
from polymer_grammar.fdr import FDRTest
from polymer_protocol import Corpus

log = logging.getLogger(__name__)

__all__ = [
    "ArmFacet",
    "ArmSource",
    "collect_immuno",
    "collect_pharmaco",
    "collect_polymergenomics",
    "collect_synbio",
    "merge_universes",
]

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_IMMUNO_PATH = _REPO_ROOT / "data" / "demo" / "immuno_universe.json"
_DEFAULT_POLYMERGENOMICS_PATH = _REPO_ROOT / "data" / "demo" / "polymergenomics_universe.json"


@dataclass(frozen=True)
class ArmFacet:
    """The provenance facet tagged onto a surviving claim: which arm produced it, and
    which measurement space (modality) it reads. Never a storage partition — a claim's
    arm/modality is metadata alongside the one merged Corpus, not a separate universe."""

    arm: str
    modality: str | None
    topic: str | None = None


@dataclass(frozen=True)
class ArmSource:
    """One arm's already-decided claims universe, ready to union in. `claims` carries
    whatever status (LICENSED/PENDING/REJECTED/CONJECTURED) the arm's own gate already
    conferred — merge_universes never re-derives it."""

    arm: str
    modality: str | None
    claims: tuple[Claim, ...]
    defeat_edges: tuple[DefeatEdge, ...] = ()
    equivalences: tuple[EquivalenceClaim, ...] = ()
    fdr_tests: tuple[FDRTest, ...] = ()
    topics: dict[str, str] = field(default_factory=dict)

    @staticmethod
    def from_corpus(arm: str, modality: str | None, corpus: Corpus) -> "ArmSource":
        """Lift a whole already-decided `Corpus` (claims + defeat_edges + equivalences +
        fdr_ledger.tests) into one arm's contribution to the merge."""
        return ArmSource(
            arm=arm,
            modality=modality,
            claims=corpus.claims,
            defeat_edges=corpus.defeat_edges,
            equivalences=corpus.equivalences,
            fdr_tests=corpus.fdr_ledger.tests,
        )


def _content_address(claim: Claim) -> str:
    """A whole-claim content address for dedup, independent of `commitment_hash` (which
    requires an `evaluation_plan` — not every arm's claims have one, e.g. synbio's
    CONJECTURED literature claims). SHA-256 over the claim's own canonical JSON dump —
    the frozen-Pydantic round-trip is exact, so two byte-identical claims (the same atom
    re-observed) always hash equal."""
    payload = claim.model_dump_json().encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def merge_universes(
    sources: Iterable[ArmSource], *, target_fdr: float = 0.05
) -> tuple[Corpus, dict[str, ArmFacet]]:
    """UNION arms into one Corpus, preserving every claim's status/e-value exactly as its
    arm produced it — never re-runs the licensing gate.

    Claim id is the dedup key (the content-addressed atom's name). A duplicate id whose
    content address matches the already-kept claim is the SAME atom re-observed by a
    second arm — silently deduped. A duplicate id whose content DIFFERS is a genuine
    conflict: the first arm's claim wins (source order = precedence) and the conflict is
    logged, never silently dropped without a trace.

    Returns the merged `Corpus` (still exactly 4 collections) plus a claim_id -> ArmFacet
    side map recording which arm/modality produced each surviving claim — the facet lives
    beside the Corpus, never inside it, so grammar/protocol stay untouched.
    """
    claims_by_id: dict[str, Claim] = {}
    hash_by_id: dict[str, str] = {}
    facets: dict[str, ArmFacet] = {}
    defeat_edges: list[DefeatEdge] = []
    equivalences: list[EquivalenceClaim] = []
    fdr_tests: list[FDRTest] = []

    for src in sources:
        for c in src.claims:
            h = _content_address(c)
            if c.id in claims_by_id:
                if hash_by_id[c.id] != h:
                    log.warning(
                        "merge_universes: claim id %r collides across arms (%s vs %s) with "
                        "DIFFERENT content — keeping %s, dropping %s",
                        c.id, facets[c.id].arm, src.arm, facets[c.id].arm, src.arm,
                    )
                continue  # dedup: same atom (or a losing conflict) already registered
            claims_by_id[c.id] = c
            hash_by_id[c.id] = h
            facets[c.id] = ArmFacet(arm=src.arm, modality=src.modality, topic=src.topics.get(c.id))
        defeat_edges.extend(src.defeat_edges)
        equivalences.extend(src.equivalences)
        fdr_tests.extend(src.fdr_tests)

    merged = Corpus(
        claims=tuple(claims_by_id.values()),
        defeat_edges=tuple(defeat_edges),
        equivalences=tuple(equivalences),
        fdr_ledger=FDRLedger(target_fdr=target_fdr, tests=tuple(fdr_tests)),
    )
    return merged, facets


# ── per-arm collectors ───────────────────────────────────────────────────────────────
# Each returns one ArmSource, ready to hand to merge_universes(). Real-data arms (pharmaco,
# immuno, polymergenomics) read gitignored/committed-demo data from disk; nothing here
# re-runs a licensing gate — pharmaco's run_full_universe() runs its OWN gate internally
# (as it always has), the merge only unions the result afterward.


def collect_pharmaco(**kwargs) -> ArmSource:
    """Facet: arm="pharmaco", modality="methylation_genebody" (se:gdsc_pharmaco@1, the
    gene-body contract `run_full_universe` licenses against by default)."""
    from .pharmaco_populate import run_full_universe

    corpus = run_full_universe(**kwargs)
    return ArmSource.from_corpus("pharmaco", "methylation_genebody", corpus)


def collect_synbio() -> ArmSource:
    """Facet: arm="synthetic-biology", modality="literature" (reported CONJECTURED claims),
    per-claim topic facet (sensing/computing/writing/delivery/actuation/...)."""
    from .synbio.ingest import collect_all_synbio_claims

    claims, topics = collect_all_synbio_claims()
    return ArmSource(arm="synthetic-biology", modality="literature",
                     claims=tuple(claims), topics=topics)


def collect_immuno(path: str | Path = _DEFAULT_IMMUNO_PATH) -> ArmSource:
    """Facet: arm="immuno", modality="methylation" (MHC + HERV-K n-DMP claims, licensed
    via the e-LOND count-enrichment route over WGBS methylation).

    `data/demo/immuno_universe.json` is a hand-built VIEWER bundle (extra display fields
    like `tier`/`dmp_count`, upper-case status strings, a partial `licensing` stub with no
    `route`/`satisfactions`) — it does NOT validate as a strict grammar `Corpus`
    (`load_corpus` raises). Rather than force the raw JSON through
    `Corpus.model_validate_json`, this collector reconstructs a minimal, valid `Claim` per
    node directly from grammar primitives (id/title/pattern/leaves/status), matching the
    `count_enrichment@v1` pattern the bundle already carries. Each claim's raw e-value (a
    STRING in the source JSON — JSON has no Infinity literal, so the MHC claim's e-value
    is literally `"inf"`) is registered as an `FDRTest` so the merged export still carries
    an e-value on these nodes; a non-finite value is capped to a large finite sentinel
    (1e300) so the final merged bundle stays valid, parseable JSON end-to-end.
    """
    import json
    from math import isfinite

    from polymer_grammar import CategoricalLeaf, MeasurementBasis, PatternRef, QuantityLeaf, Status
    from polymer_grammar.fdr import FDRTest

    raw = json.loads(Path(path).read_text())
    claims: list[Claim] = []
    fdr_tests: list[FDRTest] = []
    for i, node in enumerate(raw["claims"], start=1):
        status = Status(str(node["status"]).lower())
        # Count-enrichment nodes carry a dmp_count -> a derived QuantityLeaf; the region-Δβ nodes
        # (pending/rejected, no count) get a categorical leaf so the arm can hold both claim shapes.
        dmp = node.get("dmp_count")
        if dmp is not None:
            leaf: object = QuantityLeaf(
                value=float(dmp), unit=None, uncertainty=None,
                measurement_basis=MeasurementBasis.DERIVED, formula="count_enrichment_dmp_count",
            )
        else:
            leaf = CategoricalLeaf(ontology_term="differential_methylation")
        claims.append(
            Claim(
                id=node["id"],
                title=node["title"],
                pattern=PatternRef(id=node["pattern"]["id"], version=node["pattern"]["version"]),
                leaves=(leaf,),
                status=status,
                pending_reason=node.get("pending_reason"),
                rejection_reason=node.get("rejection_reason"),
            )
        )
        e: float | None = None
        try:
            e = float(node["e_value"]) if node.get("e_value") is not None else None
        except (TypeError, ValueError):
            e = None
        if e is not None and not isfinite(e):
            e = 1e300 if e > 0 else -1e300
        if e is not None:
            fdr_tests.append(
                FDRTest(
                    index=i, claim_id=node["id"], e_value=e,
                    alpha_allocated=0.05, discovery=(status == Status.LICENSED),
                )
            )
    return ArmSource(
        arm="immuno", modality="methylation", claims=tuple(claims), fdr_tests=tuple(fdr_tests)
    )


def collect_polymergenomics(path: str | Path = _DEFAULT_POLYMERGENOMICS_PATH) -> ArmSource:
    """Facet: arm="polymergenomics", modality=None (the PolymerGenomics reference-seed
    universe — 58 claims/54 equivalences in the committed bundle — spans multiple
    measurement spaces migrated from the pre-grammar corpus; no single modality applies
    to the whole arm — an honest IR gap, not a fabricated tag)."""
    from .io import load_corpus

    corpus = load_corpus(path)
    return ArmSource.from_corpus("polymergenomics", None, corpus)
