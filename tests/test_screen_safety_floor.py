"""B3 — the systematic healthy-tissue safety floor over real screen genes.

Runs expression::absence (two independent legs, REPRODUCED) against the re-paneled
gtex_healthy@1 contract for real screen oncogenes, and asserts the safety verdicts on the
unambiguous cases. The production ceiling is a team calibration (see module docstring).
"""
from polymer_claims.screen_safety_floor import screen_safety_verdicts


def test_safety_verdicts_at_screen_floor():
    v = screen_safety_verdicts(["SSX2", "ACTB", "GAPDH", "CD79B"])  # default ceiling 13 TPM
    # testis-restricted cancer-testis antigen: below the floor in every somatic tissue -> safe
    assert v["SSX2"] is True
    # housekeeping genes (~thousands TPM everywhere) -> vetoed by the worst-tissue leg
    assert v["ACTB"] is False
    assert v["GAPDH"] is False
    # CD79B: B-cell expression — the Tier-3 SNV whose WT-gene expression IS the safety gate -> vetoed
    assert v["CD79B"] is False


def test_ceiling_is_the_lever():
    # a moderately-broad driver flips with the ceiling — the calibration knob is real, not cosmetic
    assert screen_safety_verdicts(["KRAS"], ceiling=13.0)["KRAS"] is False
    assert screen_safety_verdicts(["KRAS"], ceiling=50.0)["KRAS"] is True
