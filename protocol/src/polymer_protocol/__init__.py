"""polymer_protocol — the protocol runtime (assessment spine) over polymer_grammar."""
from __future__ import annotations

__version__ = "0.1.0"

from .base import _Model, stable_sha

# grammar types that appear in run_cycle's public contract — re-exported for caller convenience
from polymer_grammar import Adapter, MaterializationContext, SelfLicensingError

# grammar oracle types a run_cycle caller builds to populate the registry
from polymer_grammar import ApplicabilityDomain, OracleDossier, ValidationTier

from .allocate import CREDIT_FLOOR_DEFAULT, allocate_subcaps
from .belief import Beta, accumulated_belief, expected_information_gain, prior_belief
from .canonicalize import canonicalize
from .commit import commit
from .corpus import (
    Corpus,
    CycleResult,
    CycleScaffolding,
    DiscardEntry,
    ExecRecord,
    GenerationRecord,
    Proposal,
    SelectionDecision,
    SelectionRecord,
    StageAudit,
    ValueVector,
)
from .cost import CostModel, CostVector, CostWeights, aggregate_cost
from .cycle import run_cycle
from .execute import execute_ground
from .generate import Proposer, compile_to_IR, generate_stage
from .generation_adapter import (
    GenerationAdapter,
    TemplateGenerationAdapter,
    bridge_proposer,
    compile_untrusted,
)
from .red_team import RepresentationRedTeamAdapter
from .integrate import integrate
from .ledger import (
    ClaimOutcome,
    ExecutedOutcome,
    OperatorCredit,
    SelectionLedger,
    credit_factor,
    operator_of,
    update_ledger,
)
from .drift import DriftFinding, DriftRecord, drift_pass, reopen_drifted
from .oracle import OracleRegistry, oracle_cap
from .economics import (
    ActionKind,
    ScheduledAction,
    SchedulerConfig,
    SchedulerState,
    SchedulerWeights,
    next_action,
)
from .oracle_validation import OracleDecay, OracleValidationRecord, SpotProbe, oracle_validation_pass
from .plan_synthesis import mirror_criterion, transplant_plan
from .proposers import frontier_attack, rival_generation
from .represent import represent
from .safety import safety_gate
from .select import ValueWeights, cell_of, select_stage
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
    "generate_stage",
    "compile_to_IR",
    "Proposer",
    "Proposal",
    "GenerationRecord",
    "DiscardEntry",
    "GenerationAdapter",
    "TemplateGenerationAdapter",
    "bridge_proposer",
    "compile_untrusted",
    "RepresentationRedTeamAdapter",
    "rival_generation",
    "frontier_attack",
    "mirror_criterion",
    "transplant_plan",
    "allocate_subcaps",
    "CREDIT_FLOOR_DEFAULT",
    "SelectionLedger",
    "ClaimOutcome",
    "OperatorCredit",
    "ExecutedOutcome",
    "operator_of",
    "credit_factor",
    "update_ledger",
    "accumulated_belief",
    "cell_of",
    "DriftFinding",
    "DriftRecord",
    "drift_pass",
    "reopen_drifted",
    "OracleDecay",
    "OracleValidationRecord",
    "SpotProbe",
    "oracle_validation_pass",
    "ActionKind",
    "ScheduledAction",
    "SchedulerConfig",
    "SchedulerState",
    "SchedulerWeights",
    "next_action",
]
