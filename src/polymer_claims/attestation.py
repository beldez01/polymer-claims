"""Standards-skin attestation export: in-toto Statement v1 / SLSA Provenance v1 + GA4GH DRS.

Umbrella-side, deterministic, stdlib-only. Pure builder (`build_attestation_bundle`) takes the
resolved contract index + optional adapter registry as injected params; `resolve_contract_index`
is the only IO. Design: docs/superpowers/specs/2026-06-21-standards-skin-attestation-design.md
"""
from __future__ import annotations

import re

from pydantic import Field

from polymer_grammar.base import _Model
from polymer_claims._hashing import canonical_sha256

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


_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


def _bare_hex(h: str) -> str:
    """Strip a leading `<alg>:` prefix from a content-address, leaving bare hex."""
    return h.split(":", 1)[1] if ":" in h else h


def _digest_or_none(value: str | None) -> DigestSet | None:
    """A DigestSet for a valid `sha256:<64hex>` value, else None (never emit an invalid digest)."""
    if value is not None and _SHA256_RE.match(value):
        return DigestSet(sha256=_bare_hex(value))
    return None


def _subject(claim) -> Subject:
    """in-toto subject for a licensed claim: name = claim.id, digest = canonical claim hash."""
    return Subject(name=claim.id, digest=DigestSet(sha256=_bare_hex(canonical_sha256(claim.model_dump(mode="json")))))


def distinct_cohort_reps(licensing) -> tuple:
    """One representative Satisfaction per distinct non-None dimnames_hash, deterministic
    (ascending dimnames_hash, first occurrence). Umbrella-local mirror of grammar's private
    `_distinct_cohort_reps` (parity-guarded in tests) to keep this slice umbrella-only."""
    seen: set[str] = set()
    reps = []
    for s in licensing.satisfactions:
        h = s.materialization.dimnames_hash
        if h is None or h in seen:
            continue
        seen.add(h)
        reps.append(s)
    reps.sort(key=lambda s: s.materialization.dimnames_hash)
    return tuple(reps)


def _fdr_test_for(ledger, claim_id: str):
    """First non-retracted FDR test for this claim id, or None."""
    for t in ledger.tests:
        if t.claim_id == claim_id and not t.retracted:
            return t
    return None


def _external_parameters(claim, licensing, ledger) -> ExternalParameters:
    test = _fdr_test_for(ledger, claim.id)
    return ExternalParameters(
        claim_id=claim.id,
        pattern_id=claim.pattern.id,
        license_route=licensing.route.value,
        rival_set_closure=licensing.rival_set_closure.value,
        target_fdr=ledger.target_fdr,
        fdr_test_index=test.index if test is not None else None,
        fdr_alpha_allocated=test.alpha_allocated if test is not None else None,
        fdr_e_value=test.e_value if test is not None else None,
    )


def _internal_parameters(licensing, *, independence_witnessed: bool) -> InternalParameters:
    sp = licensing.severity_provenance
    return InternalParameters(
        independence_tier=licensing.independence_tier.value,
        independence_witnessed=independence_witnessed,
        severity_provenance=sp.value if sp is not None else None,
        shared_cause_overlap=licensing.shared_cause_overlap,
    )
