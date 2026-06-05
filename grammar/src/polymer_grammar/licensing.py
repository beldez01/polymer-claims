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

from pydantic import model_validator

from .base import _Model


class SatisfactionVerdict(str, Enum):
    SATISFIED = "satisfied"
    REFUTED = "refuted"
    UNDETERMINED = "undetermined"


class MaterializationContext(_Model):
    id: str
    api_version: str
    data_version: str
    note: str | None = None


class Satisfaction(_Model):
    verdict: SatisfactionVerdict
    materialization: MaterializationContext


class LicenseRoute(str, Enum):
    SEVERE_TEST = "severe_test"
    REPLICATION = "replication"
    MDL_GATE = "mdl_gate"  # a representation-revision earned its license from corpus compressibility


class RivalSetClosure(str, Enum):
    ENUMERATED = "enumerated"
    ONTOLOGY_BOUNDED = "ontology_bounded"
    OPEN_ACKNOWLEDGED = "open_acknowledged"


class Licensing(_Model):
    route: LicenseRoute
    satisfactions: tuple[Satisfaction, ...]
    rival_set_closure: RivalSetClosure
    rivals_considered: tuple[str, ...] = ()
    note: str | None = None

    @model_validator(mode="after")
    def _all_satisfied(self) -> "Licensing":
        if not self.satisfactions:
            raise ValueError("a Licensing record requires >=1 satisfaction")
        if any(s.verdict != SatisfactionVerdict.SATISFIED for s in self.satisfactions):
            raise ValueError(
                "a Licensing record represents successful licensing; every "
                "satisfaction must be SATISFIED (refuted/undetermined => not licensed)"
            )
        return self

    @model_validator(mode="after")
    def _replication_needs_two_distinct_materializations(self) -> "Licensing":
        if self.route == LicenseRoute.REPLICATION:
            ids = {s.materialization.id for s in self.satisfactions}
            if len(ids) < 2:
                raise ValueError(
                    "route=replication requires >=2 satisfactions across DISTINCT "
                    "materializations (M1 and M2)"
                )
        return self

    @model_validator(mode="after")
    def _enumerated_closure_names_rivals(self) -> "Licensing":
        if (
            self.rival_set_closure == RivalSetClosure.ENUMERATED
            and not self.rivals_considered
        ):
            raise ValueError(
                "rival_set_closure=enumerated requires a non-empty rivals_considered"
            )
        return self
