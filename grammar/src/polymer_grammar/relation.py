"""Relation meta-claims — a Claim about a set-to-set relationship (spec 2026-07-13)."""
from __future__ import annotations

from .claim import Claim
from .leaf import RelationKind, RelationLeaf, Tier
from .pattern import Pattern, PatternRef, registry
from .provenance import GenerationMode, Provenance
from .status import Status
from .subject import ClaimSetSubject

registry.register(Pattern(
    id="relation", version="v1",
    estimand="claim_set_relationship", null_model="none", scale="signed_unit",
    invariance_group="claim_relabeling",
    intended_applications=("cross_arm_coherence", "cross_arm_tension", "restriction_map"),
    excluded_applications=("single-claim assertions (use the object claim's own pattern)",),
))

_RELATION_PATTERN = PatternRef(id="relation", version="v1")


def make_relation_claim(
    id, source_ids, target_ids, tier: Tier, relation_kind: RelationKind,
    severity: float, *, rationale: str, status: Status = Status.CONJECTURED,
) -> Claim:
    subject = ClaimSetSubject(
        id=id, display=f"{sorted(source_ids)}~{sorted(target_ids)}",
        source_set=tuple(source_ids), target_set=tuple(target_ids),
    )
    leaf = RelationLeaf(tier=tier, relation_kind=relation_kind, severity=severity)
    return Claim(
        id=id, title=rationale[:120], pattern=_RELATION_PATTERN, leaves=(leaf,),
        status=status, subject=subject,
        provenance=Provenance(
            generated_by=GenerationMode.AGENT_GENERATED,
            agent_id="polymer_grammar.relation",
            search_cardinality=1,
            rationale=rationale,
        ),
    )


def is_relation(claim: Claim) -> bool:
    return bool(claim.leaves) and claim.leaves[0].kind == "relation"
