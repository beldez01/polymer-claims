from __future__ import annotations

from polymer_grammar import Status

from polymer_claims.attestation import build_attestation_bundle
from tests.attestation._fixtures import corpus_with, licensed_claim, licensing, mc, sat


def _licensed(cid):
    return licensed_claim(cid, licensing(sat(mc(dimnames_hash="sha256:" + "a" * 64, profile_hash="sha256:" + "b" * 64, semantic_run_id="r1"))))


def test_empty_corpus_yields_empty_bundle_with_type():
    bundle = build_attestation_bundle(corpus_with(), contract_index={})
    assert bundle.attestations == ()
    assert bundle.drs_objects == ()
    assert bundle.unresolved_datasets == ()
    assert bundle.bundle_type == "https://polymerclaims.org/attestation-bundle/v1"


def test_one_statement_per_licensed_claim_sorted_by_id():
    corpus = corpus_with(_licensed("c2"), _licensed("c1"))
    bundle = build_attestation_bundle(corpus, contract_index={})
    assert [s.subject[0].name for s in bundle.attestations] == ["c1", "c2"]


def test_non_licensed_claims_excluded():
    from polymer_grammar import CategoricalLeaf, Claim, PatternRef

    conj = Claim(
        id="x",
        title="x",
        pattern=PatternRef(id="p", version="v1"),
        leaves=(CategoricalLeaf(ontology_term="t"),),
        status=Status.CONJECTURED,
    )
    bundle = build_attestation_bundle(corpus_with(conj, _licensed("c1")), contract_index={})
    assert [s.subject[0].name for s in bundle.attestations] == ["c1"]


def test_unresolved_dataset_recorded_at_bundle_level():
    bundle = build_attestation_bundle(corpus_with(_licensed("c1")), contract_index={})
    assert bundle.unresolved_datasets == ("sha256:" + "a" * 64,)


def test_export_is_byte_deterministic():
    corpus = corpus_with(_licensed("c2"), _licensed("c1"))
    a = build_attestation_bundle(corpus, contract_index={}).model_dump_json(by_alias=True, exclude_none=True)
    b = build_attestation_bundle(corpus, contract_index={}).model_dump_json(by_alias=True, exclude_none=True)
    assert a == b


def test_golden_statement_shape_for_resolved_corpus():
    import json

    from polymer_claims.contracts import AccessMethod, Checksum, SEContractRef

    h = "sha256:" + "a" * 64
    ref = SEContractRef(
        contract_uid="ds1",
        dimnames_hash=h,
        assay="meth",
        genome_assembly="GRCh38",
        self_uri="drs://local/ds1",
        size=10,
        checksums=(Checksum(checksum="f" * 64),),
        access_methods=(AccessMethod(type="file", access_url="/tmp/x"),),
    )
    bundle = build_attestation_bundle(corpus_with(_licensed("c1")), contract_index={h: ref})
    data = json.loads(bundle.model_dump_json(by_alias=True, exclude_none=True))
    st = data["attestations"][0]
    assert st["_type"] == "https://in-toto.io/Statement/v1"
    assert st["predicateType"] == "https://slsa.dev/provenance/v1"
    bd = st["predicate"]["buildDefinition"]
    roles = [d["annotations"]["role"] for d in bd["resolvedDependencies"]]
    assert roles == ["apparatus", "dataset"]  # full-key sort: role "apparatus" < "dataset"
    assert data["drsObjects"][0]["self_uri"] == "drs://local/ds1"
    assert data["drsObjects"][0]["access_methods"][0]["access_url"]["url"] == "/tmp/x"
    assert data["unresolvedDatasets"] == []
