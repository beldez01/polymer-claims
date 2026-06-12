from __future__ import annotations

from polymer_grammar import FDRLedger, MaterializationContext
from polymer_protocol import Corpus

from polymer_claims.analysis_profile import content_hash
from polymer_claims.contracts import load_contract
from polymer_claims.materialization import materialization_map
from polymer_claims.methyl_adapters import region_delta_beta_claim
from polymer_claims.profiles import CANONICAL_EPICV2_V1

_BASE = MaterializationContext(id="M", api_version="v1", data_version="d1")


def _corpus(claim):
    return Corpus(claims=(claim,), fdr_ledger=FDRLedger(target_fdr=0.05))


def test_map_records_dimnames_and_profile_hash():
    c = region_delta_beta_claim("c0")
    mats = materialization_map(_corpus(c), _BASE)
    m = mats["c0"]
    assert m.dimnames_hash == load_contract("se:epicv2_casectrl_demo@1").dimnames_hash
    assert m.profile_hash == content_hash(CANONICAL_EPICV2_V1)
    assert m.api_version == "v1" and m.data_version == "d1"


def test_semantic_run_id_is_deterministic_composite():
    c = region_delta_beta_claim("c0")
    m = materialization_map(_corpus(c), _BASE)["c0"]
    assert m.semantic_run_id is not None and m.semantic_run_id.startswith("sha256:")
    m2 = materialization_map(_corpus(c), _BASE)["c0"]
    assert m.semantic_run_id == m2.semantic_run_id


def test_unresolvable_ref_is_skipped():
    c = region_delta_beta_claim("c-bad", ref="se:does_not_exist@1")
    mats = materialization_map(_corpus(c), _BASE)
    assert "c-bad" not in mats


def test_unmatched_oracle_records_data_but_no_profile_hash():
    c = region_delta_beta_claim("c-noprof", oracle_ref="unknown_apparatus@9")
    m = materialization_map(_corpus(c), _BASE)["c-noprof"]
    assert m.dimnames_hash is not None
    assert m.profile_hash is None
