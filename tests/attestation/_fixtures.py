"""Shared builders for LICENSED-claim attestation tests. Self-contained (no conftest dependency)."""
from __future__ import annotations

from polymer_grammar import CategoricalLeaf, Claim, FDRLedger, PatternRef, Status
from polymer_grammar.licensing import (
    LicenseRoute,
    Licensing,
    MaterializationContext,
    RivalSetClosure,
    Satisfaction,
    SatisfactionVerdict,
)
from polymer_protocol import Corpus

_PATTERN = PatternRef(id="adjusted_effect", version="v1")


def mc(
    *,
    dimnames_hash: str | None = None,
    profile_hash: str | None = None,
    semantic_run_id: str | None = None,
    mid: str = "M",
) -> MaterializationContext:
    return MaterializationContext(
        id=mid,
        api_version="v1",
        data_version="d1",
        dimnames_hash=dimnames_hash,
        profile_hash=profile_hash,
        semantic_run_id=semantic_run_id,
    )


def sat(materialization: MaterializationContext, *, credential_ids: tuple[str, ...] = ()) -> Satisfaction:
    return Satisfaction(
        verdict=SatisfactionVerdict.SATISFIED,
        materialization=materialization,
        credential_ids=credential_ids,
    )


def licensing(*satisfactions: Satisfaction, **kwargs) -> Licensing:
    return Licensing(
        route=kwargs.pop("route", LicenseRoute.SEVERE_TEST),
        satisfactions=tuple(satisfactions),
        rival_set_closure=kwargs.pop("rival_set_closure", RivalSetClosure.ENUMERATED),
        rivals_considered=kwargs.pop("rivals_considered", ("self",)),
        **kwargs,
    )


def licensed_claim(cid: str, lic: Licensing) -> Claim:
    return Claim(
        id=cid,
        title=f"claim {cid}",
        pattern=_PATTERN,
        leaves=(CategoricalLeaf(ontology_term=f"term-{cid}"),),
        status=Status.LICENSED,
        licensing=lic,
    )


def corpus_with(*claims: Claim, fdr_ledger: FDRLedger | None = None) -> Corpus:
    return Corpus(
        claims=tuple(claims),
        fdr_ledger=fdr_ledger or FDRLedger(target_fdr=0.05),
    )


def corpus_path(tmp_path):
    """Write a one-LICENSED-claim corpus to <tmp_path>/corpus.json and return the path."""
    corpus = corpus_with(licensed_claim("c1", licensing(sat(mc()))))
    p = tmp_path / "corpus.json"
    p.write_text(corpus.model_dump_json())
    return p
