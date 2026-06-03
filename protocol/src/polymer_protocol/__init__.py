"""polymer_protocol — the protocol runtime (assessment spine) over polymer_grammar."""
from __future__ import annotations

__version__ = "0.1.0"

from .base import _Model, stable_sha

# grammar types that appear in run_cycle's public contract — re-exported for caller convenience
from polymer_grammar import Adapter, MaterializationContext, SelfLicensingError

# grammar oracle types a run_cycle caller builds to populate the registry
from polymer_grammar import ApplicabilityDomain, OracleDossier, ValidationTier

from .belief import Beta, expected_information_gain, prior_belief
from .canonicalize import canonicalize
from .commit import commit
from .corpus import (
    Corpus,
    CycleResult,
    CycleScaffolding,
    ExecRecord,
    SelectionDecision,
    SelectionRecord,
    StageAudit,
    ValueVector,
)
from .cost import CostModel, CostVector, CostWeights, aggregate_cost
from .cycle import run_cycle
from .execute import execute_ground
from .integrate import integrate
from .oracle import OracleRegistry, oracle_cap
from .represent import represent
from .safety import safety_gate
from .select import ValueWeights, select_stage
from .stakes import dependency_cone, stakes
from .verify import verify_stage

__all__ = [
    "_Model",
    "stable_sha",
    "__version__",
    "Corpus",
    "CycleResult",
    "CycleScaffolding",
    "ExecRecord",
    "StageAudit",
    "represent",
    "canonicalize",
    "safety_gate",
    "commit",
    "execute_ground",
    "verify_stage",
    "integrate",
    "run_cycle",
    "Adapter",
    "MaterializationContext",
    "SelfLicensingError",
    "ApplicabilityDomain",
    "OracleDossier",
    "ValidationTier",
    "OracleRegistry",
    "oracle_cap",
    "Beta",
    "prior_belief",
    "expected_information_gain",
    "stakes",
    "dependency_cone",
    "CostVector",
    "CostModel",
    "CostWeights",
    "aggregate_cost",
    "select_stage",
    "ValueVector",
    "ValueWeights",
    "SelectionRecord",
    "SelectionDecision",
]
