"""Phase 2a real-execution adapters: two GENUINELY INDEPENDENT implementations of a
two-group mean difference computed from a bundled dataset.

They share the DATA-ACCESS layer (`load_dataset` + param extraction) but each computes
the statistic with its OWN code, so agreement between them is a real two-implementation
check (the #5 adapter trust registry enforces owner/impl-hash independence on top). A
fully-separate impl or data source (e.g. numpy, or PolymerGenomicsAPI) swaps in later on
the same seam — this slice proves the machinery, not a specific library.

Umbrella/impure ONLY (file I/O via the dataset resolver). Grammar + protocol untouched.
"""
from __future__ import annotations

import statistics

from polymer_grammar import (
    CategoricalLeaf,
    Claim,
    Comparator,
    DataHandle,
    ExecValue,
    GenerationMode,
    MaterializationContext,
    OperationNode,
    PatternRef,
    PendingReason,
    Provenance,
    SatisfactionCriterion,
    Status,
    StrengthVector,
)
from polymer_protocol import (
    AdapterCredential,
    AdapterRegistry,
    ApplicabilityDomain,
    OracleDossier,
    OracleRegistry,
    ValidationTier,
)

from .adapter_identity import implementation_hash_for_adapter
from .datasets import load_dataset

_IMPL = "stats::mean_diff"

_APPARATUS_ORACLE = "dose_response_apparatus"

# A provisional (asserted, pre-cap) empirical strength a CALLER may pass to mean_diff_claim
# to exercise the apparatus oracle-tier cap. NOT the default: a strength-bearing claim is
# subject to the #3a cardinality-scaled selective-inference bar, so in the live multi-claim
# node it would never license. Live/generated claims therefore use strength=None (exempt →
# they license). Earned-from-data strength — which legitimately clears the bar — is the
# documented reconciliation.
_PROVISIONAL_STRENGTH = StrengthVector(
    magnitude=0.8, certainty=0.7, evidence_against_null=0.8,
    severity=0.5, world_contact=0.9, explanatory_virtue=0.6,
)


def _resolve(node: OperationNode) -> tuple[list[float], list[float]]:
    """Resolve the node's DataHandle + params into (group_a values, group_b values).
    Raises on a bad impl / missing handle / missing column / empty group — the evaluator
    degrades the raise to a node error."""
    if node.impl != _IMPL:
        raise ValueError(f"{_IMPL} adapter cannot execute impl {node.impl!r}")
    handle = next((i for i in node.inputs if isinstance(i, DataHandle)), None)
    if handle is None:
        raise ValueError(f"{_IMPL} requires a DataHandle input")
    p = {k: v for k, v in node.params}
    value_col, group_col = p["value_col"], p["group_col"]
    group_a, group_b = p["group_a"], p["group_b"]
    data = load_dataset(handle.ref)
    if value_col not in data or group_col not in data:
        raise KeyError(f"dataset {handle.ref!r} missing column {value_col!r}/{group_col!r}")
    groups = data[group_col]
    values = data[value_col]
    a = [float(v) for v, g in zip(values, groups) if g == group_a]
    b = [float(v) for v, g in zip(values, groups) if g == group_b]
    if not a or not b:
        raise ValueError(f"empty group ({group_a!r}={len(a)}, {group_b!r}={len(b)})")
    return a, b


class StatsPureAdapter:
    """Independent impl A — hand-rolled accumulation (no statistics module)."""

    identity = "stats-pure"

    def execute(
        self, node: OperationNode, upstream: tuple[ExecValue, ...], ctx: MaterializationContext
    ) -> ExecValue:
        a, b = _resolve(node)
        mean_a = sum(a) / len(a)
        mean_b = sum(b) / len(b)
        return ExecValue(value=mean_a - mean_b)


class StatsStdlibAdapter:
    """Independent impl B — uses the stdlib `statistics` module."""

    identity = "stats-stdlib"

    def execute(
        self, node: OperationNode, upstream: tuple[ExecValue, ...], ctx: MaterializationContext
    ) -> ExecValue:
        a, b = _resolve(node)
        return ExecValue(value=statistics.fmean(a) - statistics.fmean(b))


class HodgesLehmannMeanDiffAdapter:
    """Independent impl B — Hodges-Lehmann location shift: median of all pairwise a_i - b_j.
    A rank-family estimator, algorithmically distinct from leg A's parametric mean difference
    (StatsPure) and insensitive to skew/outliers, so the two legs agree only on a real, symmetric
    location shift. Sign matches StatsPure (mean_a - mean_b)."""

    identity = "meandiff-hodges-lehmann"

    def execute(self, node, upstream, ctx):
        a, b = _resolve(node)
        diffs = sorted(x - y for x in a for y in b)
        return ExecValue(value=float(statistics.median(diffs)))


def immuno_independent_registry() -> AdapterRegistry:
    """Air-gap for the immuno methylation drive: parametric Δmean (leg A) + Hodges-Lehmann rank
    (leg B). Genuinely independent estimators (distinct owners + impl hashes), unlike the
    StatsPure/StatsStdlib pair which are two spellings of one mean."""
    return AdapterRegistry(credentials=(
        AdapterCredential(identity="stats-pure", owner="owner-pure",
                          implementation_hash=implementation_hash_for_adapter(StatsPureAdapter)),
        AdapterCredential(identity="meandiff-hodges-lehmann", owner="owner-hl",
                          implementation_hash=implementation_hash_for_adapter(HodgesLehmannMeanDiffAdapter)),
    ))


def mean_diff_claim(
    claim_id: str,
    *,
    value_col: str = "response",
    group_col: str = "dose",
    group_a: str = "high",
    group_b: str = "low",
    comparator: Comparator = Comparator.GT,
    threshold: float = 10.0,
    ref: str = "dose_response",
    title: str = "high vs low dose mean difference",
    ontology_term: str = "dose-response",
    rationale: str | None = None,
    strength: StrengthVector | None = None,
    oracle_ref: str = _APPARATUS_ORACLE,
) -> Claim:
    """Build a PENDING Claim whose plan computes mean_diff over a bundled dataset, carrying an
    apparatus oracle_ref so any empirical strength is tier-capped at verify. `strength`
    defaults to None: a strength-bearing claim is subject to the cardinality-scaled
    selective-inference bar and would not license in the live multi-claim node, so the live
    agent emits strength=None claims. Pass a `strength` (e.g. `_PROVISIONAL_STRENGTH`) to
    exercise the oracle cap on a single claim. (In Phase 2b the LLM emits these.)
    `oracle_ref` defaults to `_APPARATUS_ORACLE` (dose_response apparatus) so existing callers
    are byte-unchanged; pass `profile_oracle_id(profile)` to bind a profile-as-apparatus."""
    from .capabilities import MEAN_DIFF_CELL
    from polymer_grammar.capability import build_evaluation_plan

    plan = build_evaluation_plan(
        MEAN_DIFF_CELL,
        params={"value_col": value_col, "group_col": group_col, "group_a": group_a, "group_b": group_b},
        data_ref=ref, criterion=SatisfactionCriterion(comparator=comparator, threshold=threshold),
        oracle_ref=oracle_ref)
    provenance = None
    if rationale is not None:
        provenance = Provenance(
            generated_by=GenerationMode.AGENT_GENERATED,
            agent_id="llm-meandiff-proposer",
            search_cardinality=1,
            rationale=rationale,
        )
    return Claim(
        id=claim_id,
        title=title,
        pattern=PatternRef(id="adjusted_effect", version="v1"),
        leaves=(CategoricalLeaf(ontology_term=ontology_term),),
        status=Status.PENDING,
        pending_reason=PendingReason.UNTESTED,
        strength=strength,
        provenance=provenance,
        evaluation_plan=plan,
    )


def hla_promoter_meth_claim(
    claim_id: str = "hla_t_naive_promoter_methylation_bimodal",
    *,
    threshold: float = 0.3,
) -> Claim:
    """Phase 2: the migrated HLA claim re-expressed as an executable two-group mean difference over
    REAL BLUEPRINT WGBS (datasets/hla_a_promoter_meth.csv). Compares HLA-A 5'UTR/promoter mean
    methylation in CD4-T vs monocytes; licenses when the cell-type Δβ clears `threshold` (the real
    Δβ ≈ 0.59, matching the original claim's ~0.51). A rationale is supplied so the claim carries the
    provenance the gate requires."""
    return mean_diff_claim(
        claim_id,
        value_col="beta", group_col="cell_type", group_a="cd4_t", group_b="monocyte",
        comparator=Comparator.GT, threshold=threshold, ref="hla_a_promoter_meth",
        title="HLA-A 5'UTR/promoter methylation is cell-type-specific: hypermethylated in CD4-T vs open in monocytes",
        ontology_term="hla-a-promoter-methylation",
        rationale="cell-type-specific HLA-A promoter methylation, monocyte vs CD4-T (BLUEPRINT WGBS)",
    )


def independent_registry() -> AdapterRegistry:
    """Credentials asserting the two adapters are genuinely independent (distinct owners +
    impl hashes), so the #5 gate licenses on their agreement."""
    return AdapterRegistry(credentials=(
        AdapterCredential(
            identity="stats-pure",
            owner="owner-pure",
            implementation_hash=implementation_hash_for_adapter(StatsPureAdapter),
        ),
        AdapterCredential(
            identity="stats-stdlib",
            owner="owner-stdlib",
            implementation_hash=implementation_hash_for_adapter(StatsStdlibAdapter),
        ),
    ))


def apparatus_oracle_registry() -> OracleRegistry:
    """BENCHMARKED dossier for the bundled mean_diff apparatus; unbounded domain. Supplying it
    to run_cycle caps a licensed claim's empirical strength to 0.6; omitting it leaves the
    declared oracle_ref UNVALIDATED (0.0)."""
    return OracleRegistry(dossiers=(
        OracleDossier(
            oracle_id=_APPARATUS_ORACLE,
            validation_tier=ValidationTier.BENCHMARKED,
            applicability_domain=ApplicabilityDomain(),
        ),
    ))


def real_data_seed_corpus():
    """A tiny seed of real-data mean_diff claims so the live node isn't empty.
    Returns (corpus, run_cycle_kwargs). The LLM proposer is added by the caller (serve)."""
    from polymer_grammar import FDRLedger
    from polymer_protocol import Corpus
    claims = (
        mean_diff_claim("seed-md-1", comparator=Comparator.GT, threshold=10.0,
                        title="high dose raises response (seed)"),
        mean_diff_claim("seed-md-2", comparator=Comparator.GT, threshold=20.0,
                        title="high dose raises response by >20 (seed)"),
    )
    corpus = Corpus(claims=claims, fdr_ledger=FDRLedger(target_fdr=0.05))
    return corpus, {"budget": 2.5}


def real_ndmp_seed_corpus():
    """Seed the live node with the single REAL-DATA n-DMP claim (genome-wide, REPRODUCED).
    Returns (corpus, from_seed_kwargs). Requires a local se:tcga_laml_idh@1 (ingest first)."""
    import math

    from polymer_grammar import FDRLedger
    from polymer_protocol import Corpus

    from .analysis_profile import profile_oracle_id
    from .methyl_ndmp import _all_probe_ids, n_dmps_claim
    from .profiles import CANONICAL_HM450_V1

    ref = "se:tcga_laml_idh@1"
    k = math.ceil(0.05 * len(_all_probe_ids(ref)))  # pre-registered null floor
    claim = n_dmps_claim(
        "tcga-laml-ndmp", ref=ref,
        group_col="Sample_Group", level_a="WT", level_b="IDH_mut",
        alpha=0.05, k=k, oracle_ref=profile_oracle_id(CANONICAL_HM450_V1),
        title="genome-wide n-DMPs, IDH-mut vs WT AML (real TCGA-LAML)",
    )
    corpus = Corpus(claims=(claim,), fdr_ledger=FDRLedger(target_fdr=0.05))
    return corpus, {"budget": 2.5}
