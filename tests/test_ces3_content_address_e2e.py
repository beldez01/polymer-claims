from __future__ import annotations

from polymer_grammar import FDRLedger, MaterializationContext, Status
from polymer_protocol import Corpus, run_cycle
from polymer_protocol.drift import drift_pass, reopen_drifted

from polymer_claims.analysis_profile import content_hash, profile_oracle_registry
from polymer_claims.capabilities import CAPABILITY_CELLS
from polymer_claims.contracts import load_contract
from polymer_claims.materialization import materialization_map
from polymer_claims.methyl_adapters import (
    RegionHodgesLehmannAdapter, RegionMeanDiffAdapter, methyl_independent_registry, region_delta_beta_claim,
)
from polymer_claims.profiles import CANONICAL_EPICV2_V1

_ADAPTERS = (RegionMeanDiffAdapter(), RegionHodgesLehmannAdapter())
_BASE = MaterializationContext(id="M", api_version="v1", data_version="d1")


def _run(claim):
    corpus = Corpus(claims=(claim,), fdr_ledger=FDRLedger(target_fdr=0.05))
    mats = materialization_map(corpus, _BASE)
    return run_cycle(corpus, _ADAPTERS, _BASE,
                     adapter_registry=methyl_independent_registry(),
                     oracles=profile_oracle_registry((CANONICAL_EPICV2_V1, "recomputable_public")),
                     materializations=mats,
                     capability_registry=CAPABILITY_CELLS)


def test_licensed_claim_records_full_content_address():
    result = _run(region_delta_beta_claim("c-true", threshold=0.10))
    c = next(x for x in result.corpus.claims if x.id == "c-true")
    assert c.status == Status.LICENSED
    m = c.licensing.satisfactions[0].materialization
    assert m.dimnames_hash == load_contract("se:epicv2_casectrl_demo@1").dimnames_hash
    assert m.profile_hash == content_hash(CANONICAL_EPICV2_V1)
    assert m.semantic_run_id is not None and m.semantic_run_id.startswith("sha256:")


def test_drift_reopens_on_dimnames_hash_change():
    result = _run(region_delta_beta_claim("c-true", threshold=0.10))
    licensed = result.corpus
    real_dim = load_contract("se:epicv2_casectrl_demo@1").dimnames_hash
    current = MaterializationContext(id="M", api_version="v1", data_version="d1",
                                     profile_hash=content_hash(CANONICAL_EPICV2_V1),
                                     dimnames_hash="sha256:" + "9" * 64)
    assert current.dimnames_hash != real_dim
    _, record = drift_pass(licensed, current=current)
    assert any(f.claim_id == "c-true" for f in record.drifted)
    reopened = reopen_drifted(licensed, record)
    c = next(x for x in reopened.claims if x.id == "c-true")
    assert c.status == Status.PENDING


def test_no_drift_when_content_address_matches():
    result = _run(region_delta_beta_claim("c-true", threshold=0.10))
    current = MaterializationContext(id="M", api_version="v1", data_version="d1",
                                     profile_hash=content_hash(CANONICAL_EPICV2_V1),
                                     dimnames_hash=load_contract("se:epicv2_casectrl_demo@1").dimnames_hash)
    _, record = drift_pass(result.corpus, current=current)
    assert not record.drifted
