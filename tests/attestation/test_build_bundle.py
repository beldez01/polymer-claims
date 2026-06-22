from __future__ import annotations

from pathlib import Path

from polymer_grammar import Status
from polymer_grammar.licensing import IndependenceTier

from polymer_claims.attestation import _resolved_dependencies, build_attestation_bundle
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


def test_public_api_exports():
    import polymer_claims as pc

    assert hasattr(pc, "build_attestation_bundle")
    assert hasattr(pc, "resolve_contract_index")
    assert hasattr(pc, "AttestationBundle")
    assert "build_attestation_bundle" in pc.__all__
    assert "AttestationBundle" in pc.__all__
    assert "resolve_contract_index" in pc.__all__


def test_non_sha256_profile_hashes_deterministic_order_and_raw_annotation():
    """Two apparatus deps with distinct non-sha256 profile hashes must sort deterministically
    across repeated calls, and each must carry the expected rawProfileHash annotation."""
    lic = licensing(
        sat(mc(dimnames_hash="sha256:" + "a" * 64, profile_hash="p2")),
        sat(mc(dimnames_hash="sha256:" + "b" * 64, profile_hash="p1")),
        independence_tier=IndependenceTier.REPLICATED,
    )
    deps1, _, _ = _resolved_dependencies(lic, {})
    deps2, _, _ = _resolved_dependencies(lic, {})
    # Results must be identical across two calls (determinism)
    assert deps1 == deps2
    # Apparatus deps, sorted by raw_profile_hash (p1 < p2)
    apparatus = [d for d in deps1 if d.annotations.role == "apparatus"]
    assert len(apparatus) == 2
    raw_hashes = [d.annotations.raw_profile_hash for d in apparatus]
    assert raw_hashes == sorted(raw_hashes), "apparatus deps not in deterministic order"
    assert set(raw_hashes) == {"p1", "p2"}
    # Each apparatus dep should have no sha256 digest (non-sha256 input)
    assert all(d.digest is None for d in apparatus)


_GOLDEN = Path(__file__).parent / "_golden_bundle.json"


def _golden_corpus():
    def L(cid):
        return licensed_claim(cid, licensing(sat(mc(
            dimnames_hash="sha256:" + "a" * 64, profile_hash="sha256:" + "b" * 64, semantic_run_id="r1"))))
    return corpus_with(L("c2"), L("c1"))


def test_bundle_matches_captured_golden():
    # uses only build_attestation_bundle (already imported at the top of this file) — passes pre-refactor
    out = build_attestation_bundle(_golden_corpus(), contract_index={}).model_dump_json(by_alias=True, exclude_none=True)
    assert out == _GOLDEN.read_text()      # byte-identical to the pre-refactor capture


def test_records_carry_statement_drs_and_unresolved():
    from polymer_claims.attestation import AttestationRecord, build_attestation_records   # in-body: fails until Task 1 impl
    records = build_attestation_records(_golden_corpus(), contract_index={})
    assert len(records) == 2
    r = records[0]
    assert isinstance(r, AttestationRecord)
    assert r.statement.subject[0].name == "c1"            # sorted by claim id
    assert isinstance(r.drs_objects, tuple) and isinstance(r.unresolved, tuple)


def test_statements_projection_equals_records_statements():
    from polymer_claims.attestation import build_attestation_records, build_attestation_statements  # in-body
    corpus = _golden_corpus()
    assert build_attestation_statements(corpus, contract_index={}) == tuple(
        r.statement for r in build_attestation_records(corpus, contract_index={}))
