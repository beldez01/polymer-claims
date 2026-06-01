"""polymer_grammar — Polymer Claims v1.3 grammar (isolated from formalclaim)."""
from __future__ import annotations

__version__ = "0.1.0"

from .base import _Model
from .leaf import (
    CategoricalLeaf,
    ExistenceLeaf,
    Leaf,
    MeasurementBasis,
    PropositionLeaf,
    QuantityLeaf,
)
from .status import PendingReason, Status
from .strength import AXES, StrengthVector, licensed
from .pattern import Pattern, PatternRef, get_pattern, registry
from .claim import Claim
from .proposition import Direction, NeighborEdge, NeighborEdgeKind, Proposition
from .equivalence import EquivalenceClaim, are_equivalent, equivalence_class
from .licensing import (
    LicenseRoute,
    Licensing,
    MaterializationContext,
    RivalSetClosure,
    Satisfaction,
    SatisfactionVerdict,
)
from .roles import CausalRoles, Role
from .units import DIMENSIONLESS, Dimension, compatible

__all__ = [
    "AXES",
    "Claim",
    "Direction",
    "EquivalenceClaim",
    "_Model",
    "CategoricalLeaf",
    "ExistenceLeaf",
    "Leaf",
    "MeasurementBasis",
    "NeighborEdge",
    "NeighborEdgeKind",
    "Pattern",
    "PatternRef",
    "PendingReason",
    "Proposition",
    "PropositionLeaf",
    "QuantityLeaf",
    "Status",
    "StrengthVector",
    "__version__",
    "are_equivalent",
    "equivalence_class",
    "get_pattern",
    "licensed",
    "LicenseRoute",
    "Licensing",
    "MaterializationContext",
    "registry",
    "RivalSetClosure",
    "Satisfaction",
    "SatisfactionVerdict",
    "CausalRoles",
    "Role",
    "DIMENSIONLESS",
    "Dimension",
    "compatible",
]
