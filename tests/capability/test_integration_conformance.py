from polymer_claims.capabilities import (
    CAPABILITY_CELLS, REGION_DELTA_BETA_CELL, MEAN_DIFF_CELL, N_DMPS_CELL,
)
from polymer_claims.exec_adapters import mean_diff_claim
from polymer_claims.methyl_adapters import region_delta_beta_claim
from polymer_claims.methyl_ndmp import n_dmps_claim
from polymer_grammar.capability import (
    validate_claim_shape, validate_claim_conformance, ConformanceReason as R,
)

def test_each_builders_claim_conforms_to_its_cell():
    assert validate_claim_shape(mean_diff_claim(claim_id="m"), MEAN_DIFF_CELL).ok
    assert validate_claim_shape(region_delta_beta_claim(claim_id="r"), REGION_DELTA_BETA_CELL).ok
    assert validate_claim_shape(n_dmps_claim(claim_id="n", k=5.0), N_DMPS_CELL).ok

def test_region_without_subject_is_byte_identical_but_nonconformant():
    claim = region_delta_beta_claim(claim_id="r2", with_subject=False)
    res = validate_claim_shape(claim, REGION_DELTA_BETA_CELL)
    assert R.SUBJECT_REQUIRED_MISSING in res.reasons and not res.ok

def test_conformance_wrapper_unknown():
    claim = mean_diff_claim(claim_id="m2")
    assert validate_claim_conformance(claim, CAPABILITY_CELLS, "stats::mean_diff", "v1").ok
    assert validate_claim_conformance(claim, CAPABILITY_CELLS, "ghost", "v1").reasons == (R.CAPABILITY_NOT_REGISTERED,)
