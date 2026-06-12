"""DRIFT daemon (#5a) — flag LICENSED claims whose minted materialization no longer matches
the world's current context.

Pure / deterministic / caller-scheduled (the standing #5 invariant): no clock, no randomness,
no environment read — the `current` context is an argument. `drift_pass` is FLAG-ONLY: it
returns the corpus identity-unchanged plus a `DriftRecord`. Re-opening drifted claims is the
separate opt-in `reopen_drifted` action. Daemon state lives in the record, never in the Corpus.
"""
from __future__ import annotations

from polymer_grammar import Claim, MaterializationContext, PendingReason, Status

from .base import _Model
from .corpus import Corpus


class DriftFinding(_Model):
    """One LICENSED claim whose materialization(s) all fail to match the current context."""

    claim_id: str
    re_executable: bool  # claim.evaluation_plan is not None -> SELECT could re-pursue it
    # the (api_version, data_version) pairs it was licensed under (the only audit trail that
    # survives a re-open, since the grammar forbids a `licensing` block on a non-LICENSED claim)
    licensed_versions: tuple[tuple[str, str], ...]


class DriftRecord(_Model):
    current: MaterializationContext  # echoed for audit
    examined: int  # number of LICENSED claims scanned
    drifted: tuple[DriftFinding, ...] = ()


def _is_fresh(claim: Claim, current: MaterializationContext) -> bool:
    """A LICENSED claim is fresh if ANY satisfaction materialization matches `current` on
    api_version AND data_version, AND — when the recorded materialization carries them — on the
    content-address fields profile_hash and dimnames_hash. A materialization without those fields
    (const-plan / pre-CES-3) is judged on versions only (back-compat). Equality match (no semver)."""
    for sat in claim.licensing.satisfactions:
        m = sat.materialization
        if m.api_version != current.api_version or m.data_version != current.data_version:
            continue
        if m.profile_hash is not None and m.profile_hash != current.profile_hash:
            continue
        if m.dimnames_hash is not None and m.dimnames_hash != current.dimnames_hash:
            continue
        return True
    return False


def drift_pass(
    corpus: Corpus, *, current: MaterializationContext
) -> tuple[Corpus, DriftRecord]:
    """Scan LICENSED claims; flag those whose materialization no longer matches `current`.
    FLAG-ONLY: the returned Corpus IS the input object (never mutated)."""
    examined = 0
    findings: list[DriftFinding] = []
    for c in corpus.claims:
        if c.status != Status.LICENSED:
            continue
        examined += 1
        if c.licensing is None:  # LICENSED may carry no licensing block -> can't assess drift
            continue
        if _is_fresh(c, current):
            continue
        versions = tuple(
            sorted({(s.materialization.api_version, s.materialization.data_version)
                    for s in c.licensing.satisfactions})
        )
        findings.append(
            DriftFinding(
                claim_id=c.id,
                re_executable=c.evaluation_plan is not None,
                licensed_versions=versions,
            )
        )
    findings.sort(key=lambda f: f.claim_id)
    return corpus, DriftRecord(current=current, examined=examined, drifted=tuple(findings))


def reopen_drifted(
    corpus: Corpus, record: DriftRecord, *, require_plan: bool = True
) -> Corpus:
    """Re-open the drifted claims named in `record` to PENDING (the opt-in action `drift_pass`
    never performs itself). With `require_plan=True` (default) only re-executable findings are
    re-opened — a planless claim re-opened to PENDING could never self-relicense, so it would
    strand. Pure: returns a new Corpus; findings for absent claim ids — and any target whose
    current status is no longer LICENSED (a stale record) — are silently skipped."""
    targets = {f.claim_id for f in record.drifted if (f.re_executable or not require_plan)}
    if not targets:
        return corpus
    new_claims = tuple(
        c.model_copy(
            update={
                "status": Status.PENDING,
                "licensing": None,
                "pending_reason": PendingReason.MATERIALIZATION_DRIFTED,
            }
        )
        if c.id in targets and c.status == Status.LICENSED
        else c
        for c in corpus.claims
    )
    if new_claims == corpus.claims:
        return corpus
    return corpus.model_copy(update={"claims": new_claims})
