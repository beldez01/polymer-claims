"""Independence as a first-class defeasible CLAIM (neg-whisper ②b — the de Bruijn move on the gate).

Today the multiply-e-values decision (``replication.py`` / ``expression_floor_replication.py``) is a
silent gate parameter: ``cohorts_error_independent`` over operator-asserted shared-cause factor tags.
This module makes that premise a CLAIM in the corpus — evidence-bearing (the ②a correlated-variance
probe), attackable (a defeat withdraws it), and non-self-licensing (two-stratum: minted PENDING; only
the gate can license it). Its verdict then caps the multiply via ``multiply_allowed``.

**Scope / safety:** this module is standalone — it does NOT modify the live licensing multiply. The
one-line wire-in of ``multiply_allowed`` into the two replication multiply sites is a licensing-behavior
change (it withdraws a multiply when a REJECTED/defeated independence claim exists) and is **flagged for
operator review** (see LOOP-CONTROL / BACKLOG neg-whisper ②) rather than applied silently. When no
independence claim is present, ``multiply_allowed(cohorts_verdict, None)`` is byte-identical to today's
``cohorts_error_independent(...) is not False``.

Correlated-BIAS stays an un-instrumentable open defeater (``CORRELATED_BIAS_DEFEATER``, from ②a) — the
independence claim records it as its standing rebuttal, never absorbs it.

Umbrella-side; grammar/protocol unchanged; Corpus stays 4.
"""
from __future__ import annotations

from collections.abc import Sequence

from polymer_grammar import (
    Claim,
    ClaimSetSubject,
    GenerationMode,
    PatternRef,
    PendingReason,
    PropositionLeaf,
    Provenance,
    Status,
)

from polymer_claims.adapter_independence import CORRELATED_BIAS_DEFEATER

INDEPENDENCE_PATTERN = PatternRef(id="error_independence", version="v1")


def make_independence_claim(
    leg_a: str,
    leg_b: str,
    *,
    rho_cv: float,
    e_value: float,
    independent: bool,
    cid: str | None = None,
) -> Claim:
    """A PENDING, attackable claim asserting legs ``leg_a`` / ``leg_b`` are error-independent, carrying
    the ②a correlated-variance probe as its evidence. NOT self-licensed (two-stratum): the measured
    ``independent`` verdict + ``e_value`` are recorded as evidence in the warrant, but standing is
    earned only through the gate. The correlated-bias residue is the standing rebuttal."""
    a, b = sorted((leg_a, leg_b))
    if a == b:
        raise ValueError("an independence claim needs two distinct legs")
    verdict = "independent" if independent else "NOT independent"
    return Claim(
        id=cid or f"independence::{a}::{b}",
        title=f"error-independence of {a} & {b}",
        pattern=INDEPENDENCE_PATTERN,
        leaves=(
            PropositionLeaf(
                data=f"legs {a} and {b} are error-independent for this test",
                warrant=(
                    f"correlated-variance perturbation probe: rho_cv={rho_cv:.4f}, "
                    f"e={e_value:.4g} -> {verdict}"
                ),
                rebuttal=CORRELATED_BIAS_DEFEATER,
                warrant_type="mechanistic_analogy",
            ),
        ),
        status=Status.PENDING,
        pending_reason=PendingReason.UNTESTED,
        subject=ClaimSetSubject(
            id=f"independence-subject::{a}::{b}",
            display=f"{a}~{b}",
            source_set=(a,),
            target_set=(b,),
        ),
        provenance=Provenance(
            generated_by=GenerationMode.AGENT_GENERATED,
            agent_id="polymer_claims.independence",
            search_cardinality=1,
            rationale=f"shared-input correlated-variance probe over legs {a},{b}",
        ),
    )


def is_independence_claim(claim: Claim) -> bool:
    return claim.pattern.id == INDEPENDENCE_PATTERN.id


def _legs_of(claim: Claim) -> frozenset[str]:
    s = claim.subject
    if isinstance(s, ClaimSetSubject):
        return frozenset((*s.source_set, *s.target_set))
    return frozenset()


def independence_verdict_for(claims: Sequence[Claim], leg_a: str, leg_b: str) -> bool | None:
    """The corpus's standing on whether these two legs are error-independent:
    ``True`` (a LICENSED independence claim), ``False`` (a REJECTED / defeated one — withdraw the
    multiply), or ``None`` (no independence claim, or only a PENDING/CONJECTURED one → today's
    behavior). A REJECTED claim wins over a LICENSED one (conservative: any refutation withdraws)."""
    want = frozenset((leg_a, leg_b))
    licensed = False
    for c in claims:
        if not is_independence_claim(c) or _legs_of(c) != want:
            continue
        if c.status == Status.REJECTED:
            return False
        if c.status == Status.LICENSED:
            licensed = True
    return True if licensed else None


def multiply_allowed(cohorts_verdict: bool | None, independence_verdict: bool | None) -> bool:
    """The multiply-e-values decision: allow UNLESS either the shared-cause-factor gate
    (``cohorts_error_independent``) or the independence CLAIM verdict says NOT independent (False).

    Byte-identity: ``multiply_allowed(v, None) == (v is not False)`` for every ``v`` — so with no
    independence claim the gate is exactly today's ``cohorts_error_independent(...) is not False``.
    """
    return cohorts_verdict is not False and independence_verdict is not False
