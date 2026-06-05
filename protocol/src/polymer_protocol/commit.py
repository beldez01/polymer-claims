"""DESIGN/COMMIT: hash-lock the pre-registered test (anti-HARKing).

For a PENDING claim carrying an evaluation_plan, write a stable lock over the plan's
graph hash + criterion into provenance.preregistration_hash (minting a minimal,
conservative Provenance if absent). Idempotent — never overwrites an existing lock;
post-hoc divergence on the locked plan is VERIFY's job to catch. Spec §6.4.
"""
from __future__ import annotations

from polymer_grammar import Claim, GenerationMode, Provenance, Status

from .base import stable_sha
from .corpus import Corpus, is_locked


def _lock(claim: Claim) -> str:
    plan = claim.evaluation_plan
    return stable_sha(
        [plan.graph.content_hash, plan.criterion.model_dump(mode="json")]
    )


def commit(corpus: Corpus, only: frozenset[str] | None = None) -> Corpus:
    new_claims = []
    changed = False
    for c in corpus.claims:
        if only is not None and c.id not in only:
            new_claims.append(c)
            continue
        if c.status != Status.PENDING or c.evaluation_plan is None or is_locked(c):
            new_claims.append(c)
            continue
        lock = _lock(c)
        if c.provenance is None:
            # IMPORTED: claim entered exogenously, generation mode unknown.
            # search_cardinality=1: conservative honest floor — avoids inflating the
            # implicit-search budget the selection-aware significance gate reads later.
            prov = Provenance(
                generated_by=GenerationMode.IMPORTED,
                search_cardinality=1,
                preregistration_hash=lock,
            )
        else:
            prov = c.provenance.model_copy(update={"preregistration_hash": lock})
        new_claims.append(c.model_copy(update={"provenance": prov}))
        changed = True
    if not changed:
        return corpus
    return corpus.model_copy(update={"claims": tuple(new_claims)})
