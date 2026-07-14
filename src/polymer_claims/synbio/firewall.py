"""Pre-registration firewall — the process-enforced conceptual-leakage guard (synbio Phase 3).

The Durendal re-derivation is a genuine held-out prediction only if the blinded seed contains NO
answer-leakage. The IR-enforced layer (`Provenance.prior_cohorts` + shared-cause) already guards
DATA-overlap leakage; this module is the PROCESS-enforced layer (Phase 0 spec §4). The admissibility
rule: a claim enters the blinded seed only if it is *upstream of and independent from* the Durendal
insight, enforced by two mechanisms together — **conclusion-stripping** (a claim that states/implies
the answer is inadmissible even if old) and an optional **literature-date cutoff** (nothing
post-dating the insight). Each admitted claim carries an `admissibility` tag naming the deciding rule.

This is a firewall HARNESS — additive, umbrella-side, NOT the licensing gate. The actual blinded-seed
CURATION, the Durendal derivation-plan pre-registration (`commitment_hash` + α-slot lock), and the
exit-gate "an independent reviewer confirms no answer-leakage" are the OPERATOR's calls — the harness
is the tool they apply, not a substitute for the human review the exit gate requires.
"""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum

# The Durendal ANSWER concepts (Phase 0 §4 OUT list). A seed claim whose conclusion/title/rationale
# states or implies any of these leaks the answer and is INADMISSIBLE even if it pre-dates the cutoff.
# Lowercase; matched case-insensitively as substrings. CONFIGURABLE — the operator finalizes the exact
# set when sealing the seed (the raw fusion/expression DATA is admissible; answer-REASONING is not).
DEFAULT_FORBIDDEN_ANSWER_TOKENS: frozenset[str] = frozenset({
    "runx1-runx1t1", "runx1t1", "t(8;21)",          # the answer fusion / genotype
    "opto-car",                                      # the answer effector conclusion
    "genotype-directed cytotoxicity",               # the Part XI synthesis
    "direct-caspase", "topology-rejection",          # the answer's mechanism moves
})


class Admissibility(str, Enum):
    ADMISSIBLE = "admissible"
    INADMISSIBLE_CONCLUSION_LEAK = "inadmissible:conclusion_leak"
    INADMISSIBLE_POST_CUTOFF = "inadmissible:post_cutoff"


@dataclass(frozen=True)
class AdmissibilityRuling:
    verdict: Admissibility
    rule: str                              # the deciding rule — the `admissibility` tag to record
    leaked_tokens: tuple[str, ...] = ()     # the answer tokens that leaked (conclusion-leak only)

    @property
    def admissible(self) -> bool:
        return self.verdict is Admissibility.ADMISSIBLE


def check_admissibility(
    text: str,
    *,
    source_date: str | None = None,   # ISO date string; compared lexicographically (ISO sorts correctly)
    cutoff_date: str | None = None,
    forbidden_tokens: Iterable[str] = DEFAULT_FORBIDDEN_ANSWER_TOKENS,
) -> AdmissibilityRuling:
    """Rule on a candidate seed claim's admissibility from its conclusion/title/rationale `text`.

    Conclusion-stripping is checked FIRST (an answer-leaking claim is out even if old / pre-cutoff),
    then the optional date-cutoff (nothing post-dating the insight). Returns the verdict + the
    deciding rule (the admissibility tag) + any leaked answer tokens.
    """
    low = text.lower()
    hits = tuple(sorted(t for t in forbidden_tokens if t in low))
    if hits:
        return AdmissibilityRuling(
            Admissibility.INADMISSIBLE_CONCLUSION_LEAK,
            f"conclusion-stripping: leaks {list(hits)}",
            hits,
        )
    if source_date is not None and cutoff_date is not None and source_date > cutoff_date:
        return AdmissibilityRuling(
            Admissibility.INADMISSIBLE_POST_CUTOFF,
            f"date-cutoff: source {source_date} post-dates cutoff {cutoff_date}",
        )
    return AdmissibilityRuling(
        Admissibility.ADMISSIBLE, "upstream-of + independent-from the Durendal insight"
    )


@dataclass(frozen=True)
class BlindedSeed:
    admitted: dict[str, str]                      # claim_id -> admissibility tag (the deciding rule)
    rejected: dict[str, AdmissibilityRuling]      # claim_id -> why it was excluded

    @property
    def n_conclusion_leaks_caught(self) -> int:
        """How many candidates the conclusion-stripping mechanism excluded for leaking the answer.
        The admitted set is leak-free BY CONSTRUCTION (a leak is never admitted); this is the
        machine-checkable half of the exit gate. The OTHER half — the independent reviewer confirming
        no SUBTLE leakage the token list misses — is a human step this harness does NOT replace."""
        return sum(
            1 for r in self.rejected.values()
            if r.verdict is Admissibility.INADMISSIBLE_CONCLUSION_LEAK
        )


def assemble_blinded_seed(
    candidates: Iterable[tuple[str, str, str | None]],
    *,
    cutoff_date: str | None = None,
    forbidden_tokens: Iterable[str] = DEFAULT_FORBIDDEN_ANSWER_TOKENS,
) -> BlindedSeed:
    """Partition candidate seed claims into admitted (each tagged with its deciding rule) + rejected.

    ``candidates`` = iterable of ``(claim_id, text, source_date | None)``. Deterministic. This is the
    machine-checkable firewall pass; sealing the seed still requires the operator's independent
    no-leakage review + the derivation-plan pre-registration (out of scope here, by design).
    """
    admitted: dict[str, str] = {}
    rejected: dict[str, AdmissibilityRuling] = {}
    for cid, text, date in candidates:
        ruling = check_admissibility(
            text, source_date=date, cutoff_date=cutoff_date, forbidden_tokens=forbidden_tokens
        )
        if ruling.admissible:
            admitted[cid] = ruling.rule
        else:
            rejected[cid] = ruling
    return BlindedSeed(admitted=admitted, rejected=rejected)
