"""CES-3: the per-claim content-address map. For each executable claim that references a
content-addressed dataset (a DataHandle) under an apparatus (oracle_ref), compute an enriched
MaterializationContext carrying its dimnames_hash (SE-Contract address, CES-1), profile_hash
(apparatus address, CES-0), and the composite semantic_run_id. Passed to run_cycle(materializations=)
so the minted Satisfaction records the full content-address. Umbrella/impure (load_contract reads the
bundled SE Contract); no numpy.
"""
from __future__ import annotations

from polymer_grammar import DataHandle, MaterializationContext
from polymer_protocol.corpus import Corpus

from ._hashing import canonical_sha256
from .analysis_profile import AnalysisProfile, content_hash, profile_oracle_id
from .contracts import load_contract
from .profiles import CANONICAL_EPICV2_V1


def _terminal_node(claim):
    plan = claim.evaluation_plan
    if plan is None:
        return None
    g = plan.graph
    return next((n for n in g.nodes if n.id == g.terminal), None)


def materialization_map(
    corpus: Corpus,
    base_ctx: MaterializationContext,
    *,
    profiles: tuple[AnalysisProfile, ...] = (CANONICAL_EPICV2_V1,),
) -> dict[str, MaterializationContext]:
    """Per-claim enriched MaterializationContext keyed by claim id. A claim whose terminal node has
    no DataHandle, or whose DataHandle.ref does not resolve to a bundled contract, gets NO entry
    (the caller falls back to base_ctx). An oracle_ref with no matching profile records the dataset
    address but profile_hash=None."""
    by_oracle = {profile_oracle_id(p): p for p in profiles}
    out: dict[str, MaterializationContext] = {}
    for c in corpus.claims:
        node = _terminal_node(c)
        if node is None:
            continue
        handle = next((i for i in node.inputs if isinstance(i, DataHandle)), None)
        if handle is None:
            continue
        try:
            contract = load_contract(handle.ref)
        except FileNotFoundError:
            continue
        dimnames_hash = contract.dimnames_hash
        profile = by_oracle.get(node.oracle_ref) if node.oracle_ref else None
        profile_hash = content_hash(profile) if profile is not None else None
        semantic_run_id = canonical_sha256({
            "tool": node.impl,
            "param_signature": [list(p) for p in node.params],
            "input_signature": [dimnames_hash],
            "profile_hash": profile_hash,
        })
        out[c.id] = MaterializationContext(
            id=base_ctx.id,
            api_version=base_ctx.api_version,
            data_version=base_ctx.data_version,
            note=base_ctx.note,
            semantic_run_id=semantic_run_id,
            profile_hash=profile_hash,
            dimnames_hash=dimnames_hash,
            shared_cause_factors=contract.shared_cause_factors,
        )
    return out
