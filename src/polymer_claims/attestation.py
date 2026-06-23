"""Standards-skin attestation export: in-toto Statement v1 / SLSA Provenance v1 + GA4GH DRS.

Umbrella-side, deterministic, stdlib-only. Pure builder (`build_attestation_bundle`) takes the
resolved contract index + optional adapter registry as injected params; `resolve_contract_index`
is the only IO. Design: docs/superpowers/specs/2026-06-21-standards-skin-attestation-design.md
"""
from __future__ import annotations

import base64
import hashlib
import json
import re
from collections.abc import Iterable

from pydantic import Field

from polymer_grammar import Status
from polymer_grammar.base import _Model
from polymer_grammar.fdr import FDRTest
from polymer_grammar.licensing import Satisfaction
from polymer_claims._hashing import canonical_sha256
from polymer_claims.contracts import _DIR as _CONTRACTS_DIR
from polymer_claims.contracts import load_contract
from polymer_protocol import independent_credential_pair
from polymer_protocol.calibration import (
    CalibrationLedger,
    CalibrationReport,
    GeneratingModelParams,
    calibration_summary,
)

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
    raw_implementation_hash: str | None = Field(default=None, alias="rawImplementationHash")
    raw_profile_hash: str | None = Field(default=None, alias="rawProfileHash")
    semantic_run_ids: tuple[str, ...] | None = Field(default=None, alias="semanticRunIds")


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


_INTOTO_MEDIA_TYPE = "application/vnd.in-toto+json"


class DsseSignature(_Model):
    sig: str
    keyid: str | None = None          # DSSE: keyid is OPTIONAL


class DsseEnvelope(_Model):
    payload_type: str = Field(default=_INTOTO_MEDIA_TYPE, alias="payloadType")
    payload: str                      # standard base64 of the Statement JSON
    signatures: tuple[DsseSignature, ...] = ()   # empty = unsigned, signing-ready (NOT trust-valid)


def dsse_envelope(statement: Statement) -> DsseEnvelope:
    """Wrap one in-toto Statement in an unsigned DSSE-shaped envelope. Pure; stdlib base64+json.
    payload = standard base64 of the standalone Statement serialization (round-trips to the Statement)."""
    raw = statement.model_dump_json(by_alias=True, exclude_none=True).encode("utf-8")
    return DsseEnvelope(payload=base64.b64encode(raw).decode("ascii"))


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


def distinct_cohort_reps(licensing) -> tuple[Satisfaction, ...]:
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


def _fdr_test_for(ledger, claim_id: str) -> FDRTest | None:
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


def _drs_object(ref) -> DrsObject:
    return DrsObject(
        id=ref.contract_uid,
        name=ref.contract_uid,
        self_uri=ref.self_uri,
        size=ref.size,
        checksums=tuple(DrsChecksum(type=c.type, checksum=c.checksum) for c in ref.checksums),
        access_methods=tuple(
            DrsAccessMethod(type=a.type, access_url=DrsAccessURL(url=a.access_url))
            for a in ref.access_methods
        ),
    )


def _resolved_dependencies(licensing, contract_index):
    """Return (deps, drs_objects, unresolved_dimnames_hashes) for one claim's licensing.

    One dataset dep per distinct dimnames_hash (cohort representatives), one apparatus dep per
    distinct profile_hash (carrying the sorted tuple of that profile's semantic_run_ids)."""
    reps = distinct_cohort_reps(licensing)
    deps: list = []
    drs: dict = {}
    unresolved: list[str] = []

    # dataset deps
    for s in reps:
        h = s.materialization.dimnames_hash
        ref = contract_index.get(h)
        if ref is not None:
            deps.append(
                ResourceDescriptor(
                    name=f"se-contract:{ref.contract_uid}",
                    uri=ref.self_uri,
                    digest=DigestSet(sha256=_bare_hex(ref.checksums[0].checksum)),
                    annotations=Annotations(role="dataset", dimnames_hash=_bare_hex(h)),
                )
            )
            drs[ref.contract_uid] = _drs_object(ref)
        else:
            deps.append(
                ResourceDescriptor(
                    name=f"se-contract:dimnames:{_bare_hex(h)}",
                    uri=f"drs://local/dimnames/{_bare_hex(h)}",
                    digest=_digest_or_none(h),
                    annotations=Annotations(role="dataset", dimnames_hash=_bare_hex(h)),
                )
            )
            unresolved.append(h)

    # apparatus deps: one per distinct profile_hash, with the sorted tuple of its run ids
    run_ids_by_profile: dict[str, set[str]] = {}
    for s in reps:
        ph = s.materialization.profile_hash
        if ph is None:
            continue
        bucket = run_ids_by_profile.setdefault(ph, set())
        if s.materialization.semantic_run_id is not None:
            bucket.add(s.materialization.semantic_run_id)
    for ph in sorted(run_ids_by_profile):
        rids = tuple(sorted(run_ids_by_profile[ph]))
        digest = _digest_or_none(ph)
        raw_ph = ph if digest is None else None
        deps.append(
            ResourceDescriptor(
                name="analysis-profile",
                digest=digest,
                annotations=Annotations(
                    role="apparatus",
                    raw_profile_hash=raw_ph,
                    semantic_run_ids=rids if rids else None,
                ),
            )
        )

    return tuple(deps), tuple(drs[k] for k in sorted(drs)), tuple(unresolved)


def _adapter_descriptor(identity: str, registry) -> ResourceDescriptor:
    digest = None
    raw = None
    if registry is not None:
        cred = registry.resolve(identity)
        if cred is not None:
            digest = _digest_or_none(cred.implementation_hash)
            if digest is None:
                raw = cred.implementation_hash
    return ResourceDescriptor(
        name=identity,
        digest=digest,
        annotations=Annotations(role="adapter", raw_implementation_hash=raw),
    )


def _builder(licensing, registry):
    """Return (Builder, independence_witnessed). builderDependencies = the union of recorded
    credential_ids across satisfactions (deduped, sorted); digests resolved only via a supplied
    registry. independence_witnessed iff a registry verifies an independent pair on any satisfaction."""
    identities = sorted({cid for s in licensing.satisfactions for cid in s.credential_ids})
    deps = tuple(_adapter_descriptor(i, registry) for i in identities)
    witnessed = registry is not None and any(
        independent_credential_pair(registry, s.credential_ids) is not None
        for s in licensing.satisfactions
    )
    return Builder(id=_BUILD_TYPE, builder_dependencies=deps), witnessed


def _dep_sort_key(d) -> tuple:
    role = d.annotations.role if d.annotations and d.annotations.role else ""
    sha = d.digest.sha256 if d.digest else ""
    rids = d.annotations.semantic_run_ids if d.annotations else None
    first_rid = rids[0] if rids else ""
    raw_ph = d.annotations.raw_profile_hash if d.annotations else None
    return (role, d.name, d.uri or "", sha, first_rid, raw_ph or "")


def _statement(claim, ledger, contract_index, registry) -> tuple[Statement, tuple[DrsObject, ...], tuple[str, ...]]:
    lic = claim.licensing
    deps, drs_objects, unresolved = _resolved_dependencies(lic, contract_index)
    deps = tuple(sorted(deps, key=_dep_sort_key))
    builder, witnessed = _builder(lic, registry)
    reps = distinct_cohort_reps(lic)
    invocation_id = reps[0].materialization.semantic_run_id if reps else None
    metadata = RunMetadata(invocation_id=invocation_id) if invocation_id is not None else None
    statement = Statement(
        subject=(_subject(claim),),
        predicate=SlsaPredicate(
            build_definition=BuildDefinition(
                build_type=_BUILD_TYPE,
                external_parameters=_external_parameters(claim, lic, ledger),
                internal_parameters=_internal_parameters(lic, independence_witnessed=witnessed),
                resolved_dependencies=deps,
            ),
            run_details=RunDetails(builder=builder, metadata=metadata),
        ),
    )
    return statement, drs_objects, unresolved


class AttestationRecord(_Model):
    statement: Statement
    drs_objects: tuple[DrsObject, ...] = ()
    unresolved: tuple[str, ...] = ()


def build_attestation_records(corpus, *, contract_index, registry=None) -> tuple[AttestationRecord, ...]:
    """One record (statement + its DRS objects + unresolved dimnames hashes) per LICENSED claim,
    sorted by claim id. Pure; contract_index + registry injected."""
    licensed = sorted(
        (c for c in corpus.claims if c.status == Status.LICENSED and c.licensing is not None),
        key=lambda c: c.id,
    )
    records: list[AttestationRecord] = []
    for claim in licensed:
        statement, drs_objects, unresolved = _statement(claim, corpus.fdr_ledger, contract_index, registry)
        records.append(AttestationRecord(statement=statement, drs_objects=drs_objects, unresolved=unresolved))
    return tuple(records)


def build_attestation_statements(corpus, *, contract_index, registry=None) -> tuple[Statement, ...]:
    """Projection: just the in-toto Statements (the DSSE export's input)."""
    return tuple(r.statement for r in build_attestation_records(
        corpus, contract_index=contract_index, registry=registry))


def build_attestation_bundle(corpus, *, contract_index, registry=None) -> AttestationBundle:
    """Deterministic in-toto/SLSA attestation bundle + DRS object docs for a corpus's LICENSED claims.
    Pure: contract_index + registry injected; no IO/clock/random."""
    records = build_attestation_records(corpus, contract_index=contract_index, registry=registry)
    drs: dict = {}
    unresolved: set[str] = set()
    for rec in records:
        for obj in rec.drs_objects:
            drs[obj.id] = obj
        unresolved.update(rec.unresolved)
    return AttestationBundle(
        attestations=tuple(r.statement for r in records),
        drs_objects=tuple(drs[k] for k in sorted(drs)),
        unresolved_datasets=tuple(sorted(unresolved)),
    )


def resolve_contract_index(corpus, *, extra: Iterable = ()) -> dict:
    """Reverse-map available SE-Contracts by dimnames_hash. The only IO in this module.

    Enumerates bundled SE-Contract manifests, loads each best-effort (failures skipped, never
    crash — mirrors load_contract's degradation contract), plus any `extra` refs injected without
    IO. Datasets that don't resolve here degrade gracefully in build_attestation_bundle."""
    index: dict = {}
    for manifest_path in sorted(_CONTRACTS_DIR.glob("*.json")):
        try:
            manifest = json.loads(manifest_path.read_bytes())
            uid = manifest.get("uid")
            if not uid or "assays" not in manifest:
                continue
            ref = load_contract(uid)
        except Exception:
            continue
        index[ref.dimnames_hash] = ref
    for ref in extra:
        index[ref.dimnames_hash] = ref
    return index


# ---------------------------------------------------------------------------
# Certificate DTO + builder + DSSE envelope (Task 8)
# New public symbols only — existing DSSE/Statement/bundle code is untouched.
# ---------------------------------------------------------------------------
_CERTIFICATE_MEDIA_TYPE = "application/vnd.polymer.certificate+json"
_INTERPRETATION = (
    "Definitional calibration validates the gate under known constructed truth (realized FDR). "
    "Anchored/attested calibration measures warrant stability under future pressure, not truth."
)


class Certificate(_Model):
    """Attestation bundle for a single LICENSED claim: in-toto Statement + optional calibration evidence."""

    statement: Statement
    calibration: CalibrationReport | None = None
    generating_models: tuple[GeneratingModelParams, ...] = ()
    ledger_digest: str | None = None
    interpretation: str = _INTERPRETATION


def build_certificate(
    corpus,
    claim_id: str,
    *,
    ledger: CalibrationLedger | None = None,
    target_q: float,
    contract_index=None,
) -> Certificate:
    """Build a Certificate for `claim_id` in `corpus`.

    Finds the in-toto Statement whose subject.name == claim_id. If a CalibrationLedger is
    supplied, attaches calibration_summary(ledger, target_q=target_q), the ledger's
    generating_models, and a sha256 hex digest of the ledger's canonical JSON representation.
    Raises ValueError if no LICENSED statement is found for claim_id."""
    index = contract_index if contract_index is not None else resolve_contract_index(corpus)
    statements = build_attestation_statements(corpus, contract_index=index)
    stmt = next(
        (s for s in statements if any(sub.name == claim_id for sub in s.subject)),
        None,
    )
    if stmt is None:
        raise ValueError(f"no LICENSED claim {claim_id!r} to certify")
    report: CalibrationReport | None = None
    digest: str | None = None
    models: tuple[GeneratingModelParams, ...] = ()
    if ledger is not None:
        report = calibration_summary(ledger, target_q=target_q)
        models = ledger.generating_models
        raw = ledger.model_dump_json(by_alias=True, exclude_none=True).encode("utf-8")
        digest = hashlib.sha256(raw).hexdigest()
    return Certificate(
        statement=stmt,
        calibration=report,
        generating_models=models,
        ledger_digest=digest,
    )


def certificate_dsse_envelope(cert: Certificate) -> DsseEnvelope:
    """Wrap a full Certificate (Statement + calibration block + ledger digest) in a DSSE-shaped
    envelope with payload_type='application/vnd.polymer.certificate+json'.

    The calibration evidence is INSIDE the signed bytes. Mirrors dsse_envelope but uses a
    distinct payloadType — existing dsse_envelope is not modified."""
    raw = cert.model_dump_json(by_alias=True, exclude_none=True).encode("utf-8")
    return DsseEnvelope(
        payload_type=_CERTIFICATE_MEDIA_TYPE,
        payload=base64.b64encode(raw).decode("ascii"),
    )


def render_certificate_text(cert: Certificate) -> str:
    """Human-legible text rendering of a Certificate with the no-laundering invariant.

    The headline q line shows ONLY the definitional realized FDR (mean per-batch FDP).
    q_anchored / q_attested appear ONLY under the separate "Warrant stability
    (field calibration ...)" heading — never as the headline. If cert.calibration is
    None (ledger=None at build time), a standing-only render is emitted with no
    calibration block."""
    lines = [f"Polymer Certificate — claim {cert.statement.subject[0].name}"]
    rep = cert.calibration
    if rep is None:
        lines.append("(standing-only — no calibration ledger supplied)")
        lines.append("")
        lines.append(cert.interpretation)
        return "\n".join(lines)
    d = rep.definitional
    lines.append(f"Corpus target q: {rep.target_q}")
    lines.append("Calibration evidence:")
    # HEADLINE: definitional realized FDR ONLY (the only tier that feeds_headline_q:
    # kind=DEFINITIONAL, target=REALIZED_FDR — recomputed from kind/target, never a stored bool)
    if d.realized_rate is None:
        lines.append("  DEFINITIONAL: no batches yet")
    else:
        ci = f"[{d.ci_low:.3f}, {d.ci_high:.3f}]" if d.ci_low is not None else "n/a"
        lines.append(
            f"  DEFINITIONAL: {d.n_batches} mixed batches, {d.n_total} licensed;"
            f" {d.n_failed} false licenses"
        )
        lines.append(
            f"                -> realized FDR (mean per-batch FDP) {d.realized_rate:.3f},"
            f" 95% CI {ci}"
            f" (pooled false fraction {d.pooled_rate:.3f})"
        )
    # FIELD CALIBRATION: anchored/attested tiers — never the headline q
    lines.append(
        "Warrant stability (field calibration — survival under pressure, NOT truth):"
    )
    a = rep.anchored
    if a.n_total:
        lines.append(
            f"  ANCHORED: {a.n_total} epochs resolved under pressure; {a.n_failed} failed"
            f" -> warrant-failure rate {a.realized_rate:.3f}; {a.n_superseded} superseded;"
            f" {a.n_unresolved} unresolved (span: {rep.observation_span_cycles} cycles)"
        )
        if a.hazard_rate is not None:
            lines.append(
                f"            exposure-weighted hazard {a.hazard_rate:.4g} failures/claim-cycle"
                f" over {a.total_exposure_cycles} exposure-cycles"
            )
    else:
        lines.append("  ANCHORED: no resolved epochs yet")
    lines.append(f"  ATTESTED: {rep.attested.n_total} attested events")
    lines.append("")
    lines.append(f"Interpretation: {cert.interpretation}")
    return "\n".join(lines)
