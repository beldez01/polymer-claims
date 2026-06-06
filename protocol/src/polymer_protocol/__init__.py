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
from .adapter_registry import (
    AdapterCredential,
    AdapterRegistry,
    adapters_independent,
    pair_is_registry_independent,
)
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
from .topology import (
    CONTRACT_VERSION,
    Layout,
    TopologyCluster,
    TopologyEdge,
    TopologyExport,
    TopologyNode,
    export_topology,
)
from .timeline import (
    FrameStats,
    TimelineFrame,
    TopologyTimeline,
    export_timeline,
    frame_stats,
    n_licensed,
)
from .verify import verify_stage

# Public API. Grouped by stability/role (audit #12, no-refactor sectioning — the names are
# unchanged; the sections just signal which surfaces are stable contracts vs runtime
# internals downstream code should lean on cautiously). Everything here is importable today.
__all__ = [
    # ── base ──────────────────────────────────────────────────────────────
    "_Model",
    "stable_sha",
    "__version__",
    # ── stable contracts (the Corpus IR bundle + the run_cycle entrypoint) ─
    "Corpus",
    "CycleResult",
    "CycleScaffolding",
    "ExecRecord",
    "StageAudit",
    "run_cycle",
    "Adapter",
    "MaterializationContext",
    "SelfLicensingError",
    # ── runtime stages (composed by run_cycle; callable directly) ──────────
    "represent",
    "canonicalize",
    "safety_gate",
    "commit",
    "execute_ground",
    "verify_stage",
    "integrate",
    "select_stage",
    "generate_stage",
    # ── oracle credibility (registry + cap) ───────────────────────────────
    "ApplicabilityDomain",
    "OracleDossier",
    "ValidationTier",
    "OracleRegistry",
    "oracle_cap",
    # ── adapter trust registry (verifier independence) ────────────────────
    "AdapterCredential",
    "AdapterRegistry",
    "adapters_independent",
    "pair_is_registry_independent",
    # ── selection: belief / stakes / cost / value ─────────────────────────
    "Beta",
    "prior_belief",
    "expected_information_gain",
    "accumulated_belief",
    "stakes",
    "dependency_cone",
    "CostVector",
    "CostModel",
    "CostWeights",
    "aggregate_cost",
    "ValueVector",
    "ValueWeights",
    "SelectionRecord",
    "SelectionDecision",
    "cell_of",
    # ── generation: bus, proposers, adapters, credit ──────────────────────
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
    # ── ledger / credit economy ───────────────────────────────────────────
    "SelectionLedger",
    "ClaimOutcome",
    "OperatorCredit",
    "ExecutedOutcome",
    "operator_of",
    "credit_factor",
    "update_ledger",
    # ── daemons (caller-scheduled standing passes) ────────────────────────
    "DriftFinding",
    "DriftRecord",
    "drift_pass",
    "reopen_drifted",
    "OracleDecay",
    "OracleValidationRecord",
    "SpotProbe",
    "oracle_validation_pass",
    # ── loop economics (the recommend-only scheduler) ─────────────────────
    "ActionKind",
    "ScheduledAction",
    "SchedulerConfig",
    "SchedulerState",
    "SchedulerWeights",
    "next_action",
    # ── topology / timeline export (the viewer data contract) ─────────────
    "CONTRACT_VERSION",
    "export_topology",
    "TopologyExport",
    "TopologyNode",
    "TopologyEdge",
    "TopologyCluster",
    "Layout",
    "export_timeline",
    "TopologyTimeline",
    "TimelineFrame",
    "FrameStats",
    "frame_stats",
    "n_licensed",
]
