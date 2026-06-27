from polymer_claims.capabilities import (
    MEAN_DIFF_CELL, REGION_DELTA_BETA_CELL, N_DMPS_CELL, CAPABILITY_CELLS,
)
from polymer_grammar.operations import Comparator

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
