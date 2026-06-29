from polymer_claims.capabilities import (
    MEAN_DIFF_CELL, REGION_DELTA_BETA_CELL, N_DMPS_CELL, CAPABILITY_CELLS,
    EVAL_BENCHMARK_ADVANTAGE_CELL,
)
from polymer_grammar.operations import Comparator
from polymer_grammar.capability import DataRefKind

ALL6 = {Comparator.LT, Comparator.LE, Comparator.EQ, Comparator.NE, Comparator.GE, Comparator.GT}

def test_three_cells_registered():
    assert CAPABILITY_CELLS.resolve("stats::mean_diff", "v1") is MEAN_DIFF_CELL
    assert CAPABILITY_CELLS.resolve("methyl::region_delta_beta", "v1") is REGION_DELTA_BETA_CELL
    assert CAPABILITY_CELLS.resolve("methyl::n_dmps", "v1") is N_DMPS_CELL

def test_cell_shapes_and_comparators_and_oracle():
    assert MEAN_DIFF_CELL.subject.mode == "forbidden"
    assert REGION_DELTA_BETA_CELL.subject.mode == "required" and REGION_DELTA_BETA_CELL.subject.kind == "genomic_region"
    assert set(MEAN_DIFF_CELL.allowed_comparators) == ALL6           # comparator compatibility
    assert MEAN_DIFF_CELL.oracle.required and REGION_DELTA_BETA_CELL.oracle.required and N_DMPS_CELL.oracle.required
    assert any(p.name == "alpha" and p.codec == "float" for p in N_DMPS_CELL.param_schema)
    assert {p.name for p in N_DMPS_CELL.param_schema} == {"probes", "group_col", "level_a", "level_b", "alpha"}


# ---------------------------------------------------------------------------
# Task 16 — eval::benchmark_advantage@v1
# ---------------------------------------------------------------------------

def test_benchmark_cell_registered():
    cell = CAPABILITY_CELLS.resolve("eval::benchmark_advantage", "v1")
    assert cell is not None
    assert cell is EVAL_BENCHMARK_ADVANTAGE_CELL


def test_benchmark_cell_is_single_mode():
    cell = EVAL_BENCHMARK_ADVANTAGE_CELL
    assert cell.verification_policy is not None
    assert cell.verification_policy.execution == "single"
    assert cell.verification_policy.result_rule == "evalue_discovery"
    assert cell.verification_policy.independence_requirement == "baseline_ground_truth"


def test_benchmark_cell_descriptor():
    cell = EVAL_BENCHMARK_ADVANTAGE_CELL
    assert cell.capability_id == "eval::benchmark_advantage"
    assert cell.capability_version == "v1"
    assert cell.operation_impl == "eval::benchmark_advantage"
    assert cell.subject.mode == "forbidden"
    assert cell.param_schema == ()
    assert cell.data_ref_kind == DataRefKind.BENCHMARK
    assert cell.allowed_comparators == (Comparator.GT,)
    assert cell.criterion_target == "threshold"
    assert cell.claim_leaf_kinds == ("categorical",)
    assert cell.min_executing_adapters == 1
    assert "benchmark-model" in cell.eligible_adapter_identities
    assert cell.oracle.required
    assert cell.oracle.default_oracle_id == "benchmark_eval_apparatus"


def test_benchmark_cell_evidence_policy_ref_is_sha256():
    vp = EVAL_BENCHMARK_ADVANTAGE_CELL.verification_policy
    assert vp is not None
    ref = vp.evidence_policy_ref
    assert ref is not None
    assert ref.startswith("sha256:")
    assert len(ref) == len("sha256:") + 64


def test_four_cells_registered():
    assert len(CAPABILITY_CELLS.cells) == 4
    assert CAPABILITY_CELLS.resolve("eval::benchmark_advantage", "v1") is not None
