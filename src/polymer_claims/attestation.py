"""Standards-skin attestation export: in-toto Statement v1 / SLSA Provenance v1 + GA4GH DRS.

Umbrella-side, deterministic, stdlib-only. Pure builder (`build_attestation_bundle`) takes the
resolved contract index + optional adapter registry as injected params; `resolve_contract_index`
is the only IO. Design: docs/superpowers/specs/2026-06-21-standards-skin-attestation-design.md
"""
from __future__ import annotations

from pydantic import Field

from polymer_grammar.base import _Model

_STATEMENT_TYPE = "https://in-toto.io/Statement/v1"
_PREDICATE_TYPE = "https://slsa.dev/provenance/v1"
_BUILD_TYPE = "https://polymerclaims.org/recompute-gate/v1"
_BUNDLE_TYPE = "https://polymerclaims.org/attestation-bundle/v1"


# --- in-toto / SLSA shapes (camelCase aliases) ---------------------------------------------------
class DigestSet(_Model):
    sha256: str


class Annotations(_Model):
    role: str | None = None
    dimnames_hash: str | None = Field(default=None, alias="dimnamesHash")
    semantic_run_ids: tuple[str, ...] | None = Field(default=None, alias="semanticRunIds")
    raw_implementation_hash: str | None = Field(default=None, alias="rawImplementationHash")


class ResourceDescriptor(_Model):
    name: str
    uri: str | None = None
    digest: DigestSet | None = None
    annotations: Annotations | None = None


class Subject(_Model):
    name: str
    digest: DigestSet


class ExternalParameters(_Model):
    claim_id: str = Field(alias="claimId")
    pattern_id: str = Field(alias="patternId")
    license_route: str = Field(alias="licenseRoute")
    rival_set_closure: str = Field(alias="rivalSetClosure")
    target_fdr: float | None = Field(default=None, alias="targetFdr")
    fdr_test_index: int | None = Field(default=None, alias="fdrTestIndex")
    fdr_alpha_allocated: float | None = Field(default=None, alias="fdrAlphaAllocated")
    fdr_e_value: float | None = Field(default=None, alias="fdrEValue")


class InternalParameters(_Model):
    independence_tier: str = Field(alias="independenceTier")
    independence_witnessed: bool = Field(alias="independenceWitnessed")
    severity_provenance: str | None = Field(default=None, alias="severityProvenance")
    shared_cause_overlap: float | None = Field(default=None, alias="sharedCauseOverlap")


class BuildDefinition(_Model):
    build_type: str = Field(alias="buildType")
    external_parameters: ExternalParameters = Field(alias="externalParameters")
    internal_parameters: InternalParameters = Field(alias="internalParameters")
    resolved_dependencies: tuple[ResourceDescriptor, ...] = Field(
        default=(), alias="resolvedDependencies"
    )


class Builder(_Model):
    id: str
    builder_dependencies: tuple[ResourceDescriptor, ...] = Field(
        default=(), alias="builderDependencies"
    )


class RunMetadata(_Model):
    invocation_id: str | None = Field(default=None, alias="invocationId")


class RunDetails(_Model):
    builder: Builder
    metadata: RunMetadata | None = None


class SlsaPredicate(_Model):
    build_definition: BuildDefinition = Field(alias="buildDefinition")
    run_details: RunDetails = Field(alias="runDetails")


class Statement(_Model):
    type_: str = Field(default=_STATEMENT_TYPE, alias="_type")
    subject: tuple[Subject, ...]
    predicate_type: str = Field(default=_PREDICATE_TYPE, alias="predicateType")
    predicate: SlsaPredicate


# --- GA4GH DRS object (snake_case field names match the DRS schema) -------------------------------
class DrsAccessURL(_Model):
    url: str


class DrsAccessMethod(_Model):
    type: str
    access_url: DrsAccessURL


class DrsChecksum(_Model):
    type: str
    checksum: str


class DrsObject(_Model):
    id: str
    name: str | None = None
    self_uri: str
    size: int
    checksums: tuple[DrsChecksum, ...]
    access_methods: tuple[DrsAccessMethod, ...] = ()


# --- bundle (Polymer envelope, camelCase) --------------------------------------------------------
class AttestationBundle(_Model):
    bundle_type: str = Field(default=_BUNDLE_TYPE, alias="bundleType")
    attestations: tuple[Statement, ...] = ()
    drs_objects: tuple[DrsObject, ...] = Field(default=(), alias="drsObjects")
    unresolved_datasets: tuple[str, ...] = Field(default=(), alias="unresolvedDatasets")
