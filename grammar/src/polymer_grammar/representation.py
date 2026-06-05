"""representation_revision meta-tier (unified spec §5.5 / §7) — claims ABOUT the IR itself.

Schema/representation changes (new patterns, deprecated ontology terms, merged patterns, relaxed
constraints) are themselves claims, carried as an additive-optional `Claim.representation_revision`
payload so they reuse the full Claim machinery (status, licensing, provenance, defeat, AGM). The grammar
expresses the *more conservative* licensing bar as a pure predicate (`meets_meta_tier_bar`); the PROTOCOL
decides to enforce it (grammar represents, protocol decides). Imports nothing from polymer_protocol.

Deferred (noted in the spec): functorial migration of existing claims (§7 Spivak Δ/Σ/Π); schema_version
frozen-as-interpreted pinning; a reserved meta-pattern. `proposed_definition` is prose/JSON, not executable.
"""
from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Annotated, Literal

from pydantic import Field, model_validator

from .base import _Model
from .licensing import LicenseRoute, Licensing, RivalSetClosure
from .pattern import PatternRef

if TYPE_CHECKING:
    from .claim import Claim


class RevisionOperation(str, Enum):
    ADD = "add"
    DEPRECATE = "deprecate"
    MERGE = "merge"
    RELAX = "relax"


class PatternTarget(_Model):
    kind: Literal["pattern"] = "pattern"
    patterns: tuple[PatternRef, ...]  # exactly 1 for add/deprecate; >=2 for merge


class OntologyTermTarget(_Model):
    kind: Literal["ontology_term"] = "ontology_term"
    term_id: str = Field(min_length=1)


class ConstraintTarget(_Model):
    kind: Literal["constraint"] = "constraint"
    name: str = Field(min_length=1)


RevisionTarget = Annotated[
    PatternTarget | OntologyTermTarget | ConstraintTarget, Field(discriminator="kind")
]


class RepresentationRevision(_Model):
    operation: RevisionOperation
    target: RevisionTarget
    rationale: str = Field(min_length=1)       # a governed scientific act needs a justification
    proposed_definition: str | None = None     # new pattern/term content as prose/JSON (NOT executable)

    @model_validator(mode="after")
    def _operation_target_compatible(self) -> "RepresentationRevision":
        op, tgt = self.operation, self.target
        if op == RevisionOperation.MERGE:
            if not (isinstance(tgt, PatternTarget) and len(tgt.patterns) >= 2):
                raise ValueError("operation=merge requires a PatternTarget with >=2 patterns")
        elif op == RevisionOperation.RELAX:
            if not isinstance(tgt, ConstraintTarget):
                raise ValueError("operation=relax requires a ConstraintTarget")
        else:  # ADD / DEPRECATE
            if isinstance(tgt, ConstraintTarget):
                raise ValueError(f"operation={op.value} does not apply to a constraint target")
            if isinstance(tgt, PatternTarget) and len(tgt.patterns) != 1:
                raise ValueError(f"operation={op.value} on a pattern targets exactly 1 pattern")
        return self


META_TIER_REQUIRED_ROUTE = LicenseRoute.REPLICATION
META_TIER_ALLOWED_CLOSURES = frozenset(
    {RivalSetClosure.ENUMERATED, RivalSetClosure.ONTOLOGY_BOUNDED}
)


def meets_meta_tier_bar(licensing: Licensing) -> bool:
    """The conservative bar a representation-revision's licensing must clear: REPLICATION across independent
    materializations AND a CLOSED rival set (enumerated or ontology-bounded) — never a single severe test
    with an open-acknowledged closure. Pure; the PROTOCOL decides to enforce it (this slice gates nothing)."""
    return (
        licensing.route == META_TIER_REQUIRED_ROUTE
        and licensing.rival_set_closure in META_TIER_ALLOWED_CLOSURES
    )


def is_representation_revision(claim: "Claim") -> bool:
    """True iff `claim` carries a representation_revision payload (i.e. is a meta-tier claim)."""
    return claim.representation_revision is not None
