# tests/test_real_kernel_proof.py
import math
import pytest
from pathlib import Path
from polymer_claims.real_kernel_proof import run_real_kernel_proof, ParityError, RealKernelProofResult
from polymer_grammar import Status
from tests.test_tcga_xena_builder import _make_fixture, _KW   # reuse the fixture generator

_BAND = (1, 50)

def _capture_pins(tmp_path) -> tuple[dict, Path, Path]:
    """Build once via the runner's own machinery to capture truthful pins for this fixture."""
    import hashlib, json
    from polymer_claims.contracts import load_contract, using_contract_root, clear_contract_cache
    from polymer_claims.ingest.tcga_xena import build_real_contract, compute_canonical_checksum
    xena, cbio = _make_fixture(tmp_path)
    out = tmp_path / "cap"
    r = build_real_contract(out, xena, mutations_file=cbio / "data_mutations.txt",
                            sequenced_file=cbio / "sequenced_samples.json", **_KW)
    with using_contract_root(out):
        clear_contract_cache()
        ref = load_contract("se:tcga_laml_idh@2")
        # run the gate the same way the runner will, to capture n_dmps/e_value/materialization
        from polymer_claims.real_kernel_proof import _run_gate_capture  # test-only helper exposed below
        gate = _run_gate_capture()
    clear_contract_cache()
    pins = {
        "contract_uid": "tcga_laml_idh@2",
        "inputs": {
            "xena": {"filename": "matrix.tsv.gz", "sha256": hashlib.sha256(xena.read_bytes()).hexdigest(), "url": None},
            "cbio_mutations": {"commit": "testcommit", "filename": "data_mutations.txt",
                               "sha256": hashlib.sha256((cbio / "data_mutations.txt").read_bytes()).hexdigest(), "url": None},
            "cbio_sequenced": {"api_endpoint": None, "filename": "sequenced_samples.json",
                               "sha256": hashlib.sha256((cbio / "sequenced_samples.json").read_bytes()).hexdigest()},
        },
        "expected": {
            "contract_uid": "tcga_laml_idh@2",
            "contract_checksum": ref.checksums[0].checksum,
            "canonical_checksum": compute_canonical_checksum(out),
            "dimnames_hash": ref.dimnames_hash,
            "group_digest": r.group_digest,
            "idh_mut_n": r.idh_mut_n, "wt_n": r.wt_n, "n_probes": r.n_probes,
            "n_dmps": gate["n_dmps"],
            "e_value": "inf" if math.isinf(gate["e_value"]) else repr(gate["e_value"]),
            "profile_hash": gate["profile_hash"], "semantic_run_id": gate["semantic_run_id"],
            "status": gate["status"], "independence_tier": gate["independence_tier"],
        },
    }
    return pins, xena, cbio

def test_parity_passes_on_faithful_rebuild(tmp_path):
    pins, xena, cbio = _capture_pins(tmp_path)
    res = run_real_kernel_proof(xena, cbio, pins=pins, cache_dir=tmp_path / "cache",
                                allow_fetch=False, idh_count_band=_BAND,
                                required_idh_mut_controls=frozenset())
    assert isinstance(res, RealKernelProofResult)
    assert res.licensed and res.status is Status.LICENSED

def test_contract_checksum_perturbation_is_named(tmp_path):
    pins, xena, cbio = _capture_pins(tmp_path)
    pins["expected"]["contract_checksum"] = "0" * 64
    pins["expected"]["canonical_checksum"] = "sha256:deadbeef"   # also wrong -> "content diverged"
    with pytest.raises(ParityError, match="content itself diverged"):
        run_real_kernel_proof(xena, cbio, pins=pins, cache_dir=tmp_path / "c2",
                              allow_fetch=False, idh_count_band=_BAND, required_idh_mut_controls=frozenset())

def test_serialization_only_divergence_is_distinguished(tmp_path):
    pins, xena, cbio = _capture_pins(tmp_path)
    pins["expected"]["contract_checksum"] = "0" * 64            # byte-level wrong
    # canonical_checksum left correct -> builder-not-byte-faithful branch
    with pytest.raises(ParityError, match="serialization differs"):
        run_real_kernel_proof(xena, cbio, pins=pins, cache_dir=tmp_path / "c3",
                              allow_fetch=False, idh_count_band=_BAND, required_idh_mut_controls=frozenset())

def test_version_identity_checked_first(tmp_path):
    pins, xena, cbio = _capture_pins(tmp_path)
    pins["expected"]["contract_uid"] = "tcga_laml_idh@1"
    with pytest.raises(ParityError, match="contract_uid"):
        run_real_kernel_proof(xena, cbio, pins=pins, cache_dir=tmp_path / "c4",
                              allow_fetch=False, idh_count_band=_BAND, required_idh_mut_controls=frozenset())

def test_evalue_inf_rule(tmp_path):
    pins, xena, cbio = _capture_pins(tmp_path)
    if pins["expected"]["e_value"] == "inf":
        pins["expected"]["e_value"] = "123.0"                  # finite pin vs observed inf -> mismatch
        with pytest.raises(ParityError, match="e_value"):
            run_real_kernel_proof(xena, cbio, pins=pins, cache_dir=tmp_path / "c5",
                                  allow_fetch=False, idh_count_band=_BAND, required_idh_mut_controls=frozenset())

def test_assert_evalue_inf_branch():
    """Direct unit test for _assert_evalue inf rule (covers branch if synthetic e-value is finite)."""
    from polymer_claims.real_kernel_proof import _assert_evalue
    _assert_evalue("inf", math.inf)                        # must pass silently
    with pytest.raises(ParityError):
        _assert_evalue("inf", 1.0)                         # finite obs vs inf pin -> ParityError
