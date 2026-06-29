"""L2 — the licensing bridge (spec §1; unified spec §3.4).

How a claim EARNS the LICENSED status: satisfaction of its inference in a specific
materialization (the (σ, M) pair — never a context-free Boolean), reached via a
severe test OR replication across independent materializations, against a declared
closure of rival explanations. A licensing record cannot exist without naming its
rival-set closure — so no verdict is ever rendered LICENSED-simpliciter.

This phase models the licensing *logic*; the grounding node (produced_by /
licensed_by + asserting-agent) and the evaluator that *produces* satisfactions are
later phases.
"""
from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import model_serializer, model_validator

from .base import _Model
from .shared_cause import SHARED_CAUSE_TAU, SeverityProvenance, shared_cause_jaccard


class SatisfactionVerdict(str, Enum):
    SATISFIED = "satisfied"
    REFUTED = "refuted"
    UNDETERMINED = "undetermined"


class MaterializationContext(_Model):
    id: str
    api_version: str
    data_version: str
    note: str | None = None
    # CES content-address keys (all optional; back-compat — existing call sites unchanged).
    # Populated when a claim is executed against a content-addressed substrate (CES-3):
    semantic_run_id: str | None = None  # SHA256(tool·params·inputs·profile_hash)
    profile_hash: str | None = None     # the realized AnalysisProfile content-address
    dimnames_hash: str | None = None    # the SE-Contract canonical content-address (drift key)
    # §E common-cause: namespaced causal-dependency tags this run's result depends on
    # (e.g. "manifest:HM450", "norm:noob", "ref:GRCh38", "lib:numpy-lstsq", "prior:idh-hypermeth").
    # Operator-asserted. Empty => not assessable (inert). The flat first form of the common-cause DAG.
    shared_cause_factors: tuple[str, ...] = ()


class Satisfaction(_Model):
    verdict: SatisfactionVerdict
    materialization: MaterializationContext
    # Adapter credential identities that justified this satisfaction under an active registry.
    # Empty => not recorded / legacy path; tuple keeps the model frozen and content-addressable.
    credential_ids: tuple[str, ...] = ()


class LicenseRoute(str, Enum):
    SEVERE_TEST = "severe_test"
    REPLICATION = "replication"
    MDL_GATE = "mdl_gate"  # a representation-revision earned its license from corpus compressibility
    EVIDENCE_LICENSED = "evidence_licensed"  # e-value evidence against a baseline (V2.0)


class RivalSetClosure(str, Enum):
    ENUMERATED = "enumerated"
    ONTOLOGY_BOUNDED = "ontology_bounded"
    OPEN_ACKNOWLEDGED = "open_acknowledged"


class IndependenceTier(str, Enum):
    """The independence standing of a license (orthogonal to LicenseRoute).

    REPRODUCED = the agreeing implementations share the dataset (today's air-gap).
    REPLICATED = independently reproduced across >=2 datasets with distinct dimnames_hash
    (conceptual replication; only this tier permits multiplying the cohorts' e-values)."""

    REPRODUCED = "reproduced"
    REPLICATED = "replicated"


def _distinct_cohort_reps(
    satisfactions: tuple[Satisfaction, ...]
) -> list[Satisfaction]:
    """One representative Satisfaction per distinct non-None dimnames_hash, deterministic
    (ascending dimnames_hash, first occurrence)."""
    reps: dict[str, Satisfaction] = {}
    for s in satisfactions:
        h = s.materialization.dimnames_hash
        if h is not None and h not in reps:
            reps[h] = s
    return [reps[h] for h in sorted(reps)]


def _cohort_pairwise_jaccards(
    satisfactions: tuple[Satisfaction, ...]
) -> list[float] | None:
    """The pairwise shared-cause Jaccards among distinct-cohort representatives, or None when
    not assessable: <2 distinct cohorts, OR any representative has empty factors (partial
    adoption falls back to today's behavior — byte-identical when off)."""
    reps = _distinct_cohort_reps(satisfactions)
    if len(reps) < 2:
        return None
    factors = [r.materialization.shared_cause_factors for r in reps]
    if any(not f for f in factors):
        return None
    return [
        shared_cause_jaccard(factors[i], factors[j])
        for i in range(len(factors))
        for j in range(i + 1, len(factors))
    ]


def cohorts_error_independent(
    satisfactions: tuple[Satisfaction, ...]
) -> bool | None:
    """§E: are the distinct cohorts' errors independent (low shared-cause overlap)?
    None  -> not assessable (see _cohort_pairwise_jaccards).
    True  -> every pairwise Jaccard < SHARED_CAUSE_TAU.
    False -> some pair's Jaccard >= SHARED_CAUSE_TAU (the runs share too much cause)."""
    jaccards = _cohort_pairwise_jaccards(satisfactions)
    if jaccards is None:
        return None
    return all(j < SHARED_CAUSE_TAU for j in jaccards)


def max_shared_cause_overlap(
    satisfactions: tuple[Satisfaction, ...]
) -> float | None:
    """The max pairwise Jaccard among distinct-cohort representatives, or None when not
    assessable (matches cohorts_error_independent's None cases). Recorded on the license."""
    jaccards = _cohort_pairwise_jaccards(satisfactions)
    if jaccards is None:
        return None
    return max(jaccards)


def independence_tier_of(satisfactions: tuple[Satisfaction, ...]) -> IndependenceTier:
    """REPLICATED iff >=2 DISTINCT non-None dimnames_hash AND the cohorts are error-independent.
    cohorts_error_independent is None (factors absent / partial) => today's behavior (REPLICATED on
    distinct cohorts — byte-identical when off); False (high overlap) => REPRODUCED (the §E gate)."""
    cohorts = {
        s.materialization.dimnames_hash
        for s in satisfactions
        if s.materialization.dimnames_hash is not None
    }
    if len(cohorts) < 2:
        return IndependenceTier.REPRODUCED
    if cohorts_error_independent(satisfactions) is False:
        return IndependenceTier.REPRODUCED
    return IndependenceTier.REPLICATED


class Licensing(_Model):
    route: LicenseRoute
    satisfactions: tuple[Satisfaction, ...]
    rival_set_closure: RivalSetClosure
    rivals_considered: tuple[str, ...] = ()
    independence_tier: IndependenceTier | None = IndependenceTier.REPRODUCED
    severity_provenance: SeverityProvenance | None = None
    shared_cause_overlap: float | None = None
    note: str | None = None
    # V2.0 evidence-licensed fields — non-None iff route=EVIDENCE_LICENSED.
    # Both are omitted from serialized output when None (see _serialize below).
    verification_standing: Literal["single_source_baseline"] | None = None
    evidence_provenance: EvidenceProvenance | None = None

    @model_serializer(mode="wrap")
    def _serialize(self, handler) -> dict:
        """Drop verification_standing and evidence_provenance from the output when
        they are None, so a non-evidence Licensing is byte-identical to pre-Task-8."""
        data = handler(self)
        if data.get("verification_standing") is None:
            data.pop("verification_standing", None)
        if data.get("evidence_provenance") is None:
            data.pop("evidence_provenance", None)
        return data

    @model_validator(mode="after")
    def _all_satisfied(self) -> Licensing:
        if not self.satisfactions:
            raise ValueError("a Licensing record requires >=1 satisfaction")
        if any(s.verdict != SatisfactionVerdict.SATISFIED for s in self.satisfactions):
            raise ValueError(
                "a Licensing record represents successful licensing; every "
                "satisfaction must be SATISFIED (refuted/undetermined => not licensed)"
            )
        return self

    @model_validator(mode="after")
    def _replication_needs_two_distinct_materializations(self) -> Licensing:
        if self.route == LicenseRoute.REPLICATION:
            ids = {s.materialization.id for s in self.satisfactions}
            if len(ids) < 2:
                raise ValueError(
                    "route=replication requires >=2 satisfactions across DISTINCT "
                    "materializations (M1 and M2)"
                )
        return self

    @model_validator(mode="after")
    def _replicated_tier_needs_two_distinct_cohorts(self) -> Licensing:
        if (
            self.independence_tier == IndependenceTier.REPLICATED
            and independence_tier_of(self.satisfactions) != IndependenceTier.REPLICATED
        ):
            raise ValueError(
                "independence_tier=replicated requires >=2 satisfactions with "
                "distinct dimnames_hash (cohorts)"
            )
        return self

    @model_validator(mode="after")
    def _enumerated_closure_names_rivals(self) -> Licensing:
        if (
            self.rival_set_closure == RivalSetClosure.ENUMERATED
            and not self.rivals_considered
        ):
            raise ValueError(
                "rival_set_closure=enumerated requires a non-empty rivals_considered"
            )
        return self

    @model_validator(mode="after")
    def _evidence_route_fields(self) -> Licensing:
        """verification_standing and evidence_provenance are non-None iff route=EVIDENCE_LICENSED."""
        is_evidence = self.route == LicenseRoute.EVIDENCE_LICENSED
        has_standing = self.verification_standing is not None
        has_provenance = self.evidence_provenance is not None
        if is_evidence:
            if not has_standing or not has_provenance:
                raise ValueError(
                    "route=evidence_licensed requires both verification_standing and "
                    "evidence_provenance"
                )
        else:
            if has_standing or has_provenance:
                raise ValueError(
                    "verification_standing and evidence_provenance are only valid "
                    "when route=evidence_licensed"
                )
        return self


# Late import to break the circular dependency with verification_policy.py, which imports
# LicenseRoute and MaterializationContext from this module (defined above Licensing).
# EvidenceProvenance is resolved here after verification_policy is loadable, then
# model_rebuild() completes the Licensing schema.
from .verification_policy import EvidenceProvenance  # noqa: E402
Licensing.model_rebuild()
