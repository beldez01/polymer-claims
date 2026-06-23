from polymer_grammar import Status
from polymer_claims.kernel_proof import run_synthetic_kernel_proof


def test_synthetic_kernel_proof_licenses_at_reproduced():
    r = run_synthetic_kernel_proof()
    assert r.status is Status.LICENSED and r.licensed is True
    assert r.independence_tier is not None
    assert r.independence_tier.name == "REPRODUCED"     # two independent legs agreed
    assert r.n_dmps >= r.k                               # clears the pre-registered null floor
    assert r.n_probes == 3000 and r.k == 150
    assert r.e_value > 1e10


def test_synthetic_kernel_proof_n_dmps_is_pinned():
    # Deterministic: fixed seed + 4-decimal betas. Update <PINNED> only with an intentional
    # fixture change. Regenerate via the -c one-liner in the plan if this ever changes.
    r = run_synthetic_kernel_proof()
    assert r.n_dmps == 295
