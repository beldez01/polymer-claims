from __future__ import annotations

import json

from polymer_claims.attestation import (
    AttestationBundle,
    BuildDefinition,
    Builder,
    DigestSet,
    ExternalParameters,
    InternalParameters,
    RunDetails,
    SlsaPredicate,
    Statement,
    Subject,
)


def _minimal_statement() -> Statement:
    return Statement(
        subject=(Subject(name="c1", digest=DigestSet(sha256="ab")),),
        predicate=SlsaPredicate(
            build_definition=BuildDefinition(
                build_type="https://polymerclaims.org/recompute-gate/v1",
                external_parameters=ExternalParameters(
                    claim_id="c1",
                    pattern_id="p",
                    license_route="severe_test",
                    rival_set_closure="enumerated",
                ),
                internal_parameters=InternalParameters(
                    independence_tier="reproduced", independence_witnessed=False
                ),
            ),
            run_details=RunDetails(builder=Builder(id="https://polymerclaims.org/recompute-gate/v1")),
        ),
    )


def test_statement_serializes_with_intoto_aliases():
    data = json.loads(_minimal_statement().model_dump_json(by_alias=True, exclude_none=True))
    assert data["_type"] == "https://in-toto.io/Statement/v1"
    assert data["predicateType"] == "https://slsa.dev/provenance/v1"
    assert data["subject"][0]["digest"] == {"sha256": "ab"}
    bd = data["predicate"]["buildDefinition"]
    assert bd["buildType"] == "https://polymerclaims.org/recompute-gate/v1"
    assert bd["externalParameters"]["claimId"] == "c1"
    assert bd["internalParameters"]["independenceTier"] == "reproduced"
    assert data["predicate"]["runDetails"]["builder"]["id"].endswith("recompute-gate/v1")


def test_exclude_none_drops_optional_fields():
    data = json.loads(_minimal_statement().model_dump_json(by_alias=True, exclude_none=True))
    # severityProvenance / sharedCauseOverlap unset -> absent
    assert "severityProvenance" not in data["predicate"]["buildDefinition"]["internalParameters"]
    # builderDependencies defaults to () -> empty list present (not None)
    assert data["predicate"]["runDetails"]["builder"]["builderDependencies"] == []


def test_bundle_carries_bundletype():
    bundle = AttestationBundle(attestations=(_minimal_statement(),))
    data = json.loads(bundle.model_dump_json(by_alias=True, exclude_none=True))
    assert data["bundleType"] == "https://polymerclaims.org/attestation-bundle/v1"
    assert len(data["attestations"]) == 1
    assert data["drsObjects"] == []
    assert data["unresolvedDatasets"] == []
