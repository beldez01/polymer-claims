import pytest
np = pytest.importorskip("numpy")
from polymer_protocol.calibration import GeneratingModelParams  # noqa: E402
from polymer_claims.calibration_harness import synthetic_cohort  # noqa: E402
from polymer_claims.contracts import load_contract, using_contract_root  # noqa: E402


def _model(**kw):
    base = dict(model_id="m1", n_per_group=20, n_probes_per_region=5, effect_size=0.25,
                dispersion=20.0, fraction_true=0.5, tau=0.10, target_fdr=0.05,
                n_generated=10, seed_set=(0,))
    base.update(kw); return GeneratingModelParams(**base)  # noqa: E702


def test_synthetic_cohort_is_loadable_and_deterministic(tmp_path):
    b1 = synthetic_cohort(model=_model(), batch_id="b1", seed=0, root=tmp_path / "r1")
    with using_contract_root(b1.root):
        ref = load_contract(f"se:{b1.contract_uid}")
    assert ref.contract_uid == b1.contract_uid
    # determinism: same seed -> identical betas TSV bytes
    b2 = synthetic_cohort(model=_model(), batch_id="b1", seed=0, root=tmp_path / "r2")
    f1 = (b1.root / f"{b1.contract_uid.split('@')[0]}.betas.tsv").read_bytes()
    f2 = (b2.root / f"{b2.contract_uid.split('@')[0]}.betas.tsv").read_bytes()
    assert f1 == f2


def test_truth_labels_match_fraction(tmp_path):
    b = synthetic_cohort(model=_model(n_generated=10, fraction_true=0.4), batch_id="b", seed=1,
                         root=tmp_path)
    assert len(b.regions) == 10
    assert sum(1 for r in b.regions if r.constructed_truth) == 4
