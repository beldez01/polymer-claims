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
from .oracle import OracleRegistry, oracle_cap

BH_Q = 0.10
_BH_EPS = 1e-9


def _permitted_by_bar(corpus: Corpus, exec_records: tuple[ExecRecord, ...]) -> set[str]:
    """Ids of executed claims permitted to license under the cardinality-scaled BH bar.
    M<=1 -> all permitted (identity). strength=None -> exempt (always permitted)."""
    by_id = corpus.by_id()
    executed = [by_id[r.claim_id] for r in exec_records if r.claim_id in by_id]
    if not executed:
        return set()
    m = max(
        (c.provenance.search_cardinality for c in executed if c.provenance is not None),
        default=1,
    )
    if m <= 1:
        return {c.id for c in executed}
    permitted = {c.id for c in executed if c.strength is None}  # exempt
    scored = [
        (1.0 - c.strength.evidence_against_null, c.id)
        for c in executed
        if c.strength is not None
    ]
    scored.sort()  # ascending pseudo-p, ties by id
    k_max = 0
    for k, (p, _) in enumerate(scored, start=1):
        # inclusive boundary: tolerate float error so p exactly on the BH line passes
        if p <= (k / m) * BH_Q + _BH_EPS:
            k_max = k
    permitted.update(cid for _, cid in scored[:k_max])
    return permitted


def _with_status(claim: Claim, **update) -> Claim:
    """Apply a status/licensing/pending_reason update AND re-run Claim validators
    (model_copy alone skips validation)."""
    return Claim.model_validate(claim.model_copy(update=update).model_dump())


def verify_stage(
    corpus: Corpus,
    scaffolding: CycleScaffolding,
    exec_records: tuple[ExecRecord, ...],
    oracles: OracleRegistry | None = None,
) -> Corpus:
    registry = oracles if oracles is not None else OracleRegistry()
    in_ext = set(scaffolding.grounded_extension)
    rec_by_id = {r.claim_id: r for r in exec_records}
    permitted = _permitted_by_bar(corpus, exec_records)
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
        if (ev.satisfaction is not None and c.id in in_ext
                and c.provenance is not None and c.id in permitted):
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
                    strength=oracle_cap(c, registry),  # None oracles arg -> empty registry -> unresolved refs are UNVALIDATED
                )
            )
        elif agreed_refuted or c.id not in in_ext:
            new_claims.append(
                _with_status(c, status=Status.REJECTED, licensing=None, pending_reason=None)
            )
        else:
            new_claims.append(c)  # stays PENDING — already carries a valid pending_reason
    return corpus.model_copy(update={"claims": tuple(new_claims)})
