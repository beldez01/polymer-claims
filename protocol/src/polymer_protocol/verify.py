"""VERIFY: decide each executed claim's status + assemble Licensing.

LICENSED <=> minted Satisfaction (agreement + SATISFIED) AND grounded-extension membership
AND provenance present (search_cardinality recorded — the selection-aware honesty gate).
REJECTED <=> refuted, or outside the grounded extension. Else PENDING (triage). This is the
Licensing-assembly + status-flip that Phase 8 deliberately left to the protocol. Spec §6.6.
"""
from __future__ import annotations

from polymer_grammar import (
    Claim,
    LicenseRoute,
    Licensing,
    RivalSetClosure,
    SatisfactionVerdict,
    Status,
)

from .corpus import Corpus, CycleScaffolding, ExecRecord


def _with_status(claim: Claim, **update) -> Claim:
    """Apply a status/licensing/pending_reason update AND re-run Claim validators
    (model_copy alone skips validation)."""
    return Claim.model_validate(claim.model_copy(update=update).model_dump())


def verify_stage(
    corpus: Corpus,
    scaffolding: CycleScaffolding,
    exec_records: tuple[ExecRecord, ...],
) -> Corpus:
    in_ext = set(scaffolding.grounded_extension)
    rec_by_id = {r.claim_id: r for r in exec_records}
    new_claims = []
    for c in corpus.claims:
        rec = rec_by_id.get(c.id)
        if rec is None:
            new_claims.append(c)
            continue
        ev = rec.evaluation
        # ev.results is non-empty in the normal pipeline (verify requires >=2 adapters);
        # the truthiness guard is defensive.
        agreed_refuted = (
            ev.agreement
            and ev.results
            and ev.results[0].verdict == SatisfactionVerdict.REFUTED
        )
        # provenance is non-None for anything that passed execute_ground (_is_executable
        # requires the lock); the guard is defensive for direct callers.
        if ev.satisfaction is not None and c.id in in_ext and c.provenance is not None:
            licensing = Licensing(
                route=LicenseRoute.SEVERE_TEST,
                satisfactions=(ev.satisfaction,),
                rival_set_closure=RivalSetClosure.OPEN_ACKNOWLEDGED,
            )
            new_claims.append(
                _with_status(
                    c,
                    status=Status.LICENSED,
                    licensing=licensing,
                    pending_reason=None,
                )
            )
        elif agreed_refuted or c.id not in in_ext:
            new_claims.append(
                _with_status(c, status=Status.REJECTED, licensing=None, pending_reason=None)
            )
        else:
            new_claims.append(c)  # stays PENDING — already carries a valid pending_reason
    return corpus.model_copy(update={"claims": tuple(new_claims)})
