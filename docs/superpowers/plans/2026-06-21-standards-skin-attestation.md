# Standards-Skin Attestation Export Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `export-attestation <corpus>` — a deterministic umbrella exporter that turns every LICENSED claim into an in-toto Statement v1 / SLSA Provenance v1 attestation plus GA4GH DRS object docs, built from the content-address fields the repo already computes.

**Architecture:** A new umbrella module `src/polymer_claims/attestation.py` with (a) typed frozen `_Model` DTOs for the in-toto/SLSA/DRS shapes, (b) small pure helper builders, (c) a pure top-level `build_attestation_bundle(corpus, *, contract_index, registry=None)`, and (d) an IO-only `resolve_contract_index(corpus)` that reverse-maps bundled SE-Contracts by `dimnames_hash`. A CLI subcommand wires `load_corpus → resolve_contract_index → build_attestation_bundle → JSON`. Design spec: `docs/superpowers/specs/2026-06-21-standards-skin-attestation-design.md`.

**Tech Stack:** Python 3, pydantic v2 (`_Model` = frozen, `extra="forbid"`, `populate_by_name=True`), stdlib `json`/`hashlib`/`re`, `argparse`. Tests: pytest. Lint: ruff.

## Global Constraints

- **Umbrella-side only.** All new code lives under `src/polymer_claims/`. Do NOT modify `grammar/` or `protocol/`. Do NOT touch `protocol/.../sheaf.py`, `src/polymer_claims/sheaf_spectrum.py`, or any sheaf/topology rendering (arc-3 owns those).
- **Zero new dependencies.** stdlib only. Reuse `from polymer_claims._hashing import canonical_sha256` (returns `"sha256:<hex>"`).
- **Frozen DTOs.** Every new model subclasses `from polymer_grammar.base import _Model`. Collection fields are **tuples**, never `dict`/`list`. No open `dict[str, Any]` fields — SLSA JSON maps are modeled as typed DTOs with fixed optional fields.
- **Deterministic, no clock/random/IO in the builder.** No timestamps. The pure builder takes `contract_index` and `registry` as injected params.
- **Additive / byte-identical when off.** New module + appended CLI subcommand + appended `__init__` exports. Touch no existing export, model, or command body. `Corpus` stays exactly 4 collections.
- **Serialization:** `bundle.model_dump_json(by_alias=True, exclude_none=True)`.
- **Constant URIs:** statement type `https://in-toto.io/Statement/v1`; predicate type `https://slsa.dev/provenance/v1`; buildType **and** builder.id `https://polymerclaims.org/recompute-gate/v1`; bundleType `https://polymerclaims.org/attestation-bundle/v1`.
- **Per-package gate (run from repo root):** `uv run pytest -q tests/attestation` and `uv run ruff check src tests`.
- **TDD:** failing test first, minimal code to pass, commit per task.

---

## File Structure

- `src/polymer_claims/attestation.py` — DTOs, helpers, `build_attestation_bundle`, `resolve_contract_index` (created Task 1, extended through Task 8).
- `tests/attestation/_fixtures.py` — shared test builders for LICENSED claims/corpora (created Task 2).
- `tests/attestation/test_dtos.py` — DTO serialization (Task 1).
- `tests/attestation/test_helpers.py` — subject/cohort/params/deps/builder helpers (Tasks 2–6).
- `tests/attestation/test_build_bundle.py` — top-level builder, determinism, golden (Task 7).
- `tests/attestation/test_resolve_contracts.py` — IO resolver (Task 8).
- `tests/attestation/test_cli.py` — CLI smoke (Task 9).
- `src/polymer_claims/cli.py` — append subcommand (Task 9).
- `src/polymer_claims/__init__.py` — append exports (Task 10).

---

### Task 1: DTOs + serialization

**Files:**
- Create: `src/polymer_claims/attestation.py`
- Test: `tests/attestation/test_dtos.py`

**Interfaces:**
- Produces: frozen `_Model` DTOs `DigestSet`, `Annotations`, `ResourceDescriptor`, `Subject`, `ExternalParameters`, `InternalParameters`, `BuildDefinition`, `Builder`, `RunMetadata`, `RunDetails`, `SlsaPredicate`, `Statement`, `DrsAccessURL`, `DrsAccessMethod`, `DrsChecksum`, `DrsObject`, `AttestationBundle`. Module constants `_STATEMENT_TYPE`, `_PREDICATE_TYPE`, `_BUILD_TYPE`, `_BUNDLE_TYPE`.

- [ ] **Step 1: Write the failing test**

Create `tests/attestation/test_dtos.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest -q tests/attestation/test_dtos.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'polymer_claims.attestation'`.

- [ ] **Step 3: Write minimal implementation**

Create `src/polymer_claims/attestation.py`:

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest -q tests/attestation/test_dtos.py`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add src/polymer_claims/attestation.py tests/attestation/test_dtos.py
git commit -m "feat(attestation): in-toto/SLSA/DRS frozen DTOs + serialization"
```

---

### Task 2: hashing helpers + subject + shared fixtures

**Files:**
- Modify: `src/polymer_claims/attestation.py`
- Create: `tests/attestation/_fixtures.py`
- Test: `tests/attestation/test_helpers.py`

**Interfaces:**
- Consumes: `DigestSet`, `Subject` (Task 1); `canonical_sha256` from `polymer_claims._hashing`.
- Produces: `_bare_hex(h: str) -> str`; `_digest_or_none(value: str | None) -> DigestSet | None`; `_subject(claim) -> Subject`. Test fixtures `mc(...)`, `sat(...)`, `licensing(...)`, `licensed_claim(...)`, `corpus_with(...)` in `tests/attestation/_fixtures.py`.

- [ ] **Step 1: Write the shared fixtures module**

Create `tests/attestation/_fixtures.py`:

```python
"""Shared builders for LICENSED-claim attestation tests. Self-contained (no conftest dependency)."""
from __future__ import annotations

from polymer_grammar import CategoricalLeaf, Claim, FDRLedger, PatternRef, Status
from polymer_grammar.licensing import (
    LicenseRoute,
    Licensing,
    MaterializationContext,
    RivalSetClosure,
    Satisfaction,
    SatisfactionVerdict,
)
from polymer_protocol import Corpus

_PATTERN = PatternRef(id="adjusted_effect", version="v1")


def mc(
    *,
    dimnames_hash: str | None = None,
    profile_hash: str | None = None,
    semantic_run_id: str | None = None,
    mid: str = "M",
) -> MaterializationContext:
    return MaterializationContext(
        id=mid,
        api_version="v1",
        data_version="d1",
        dimnames_hash=dimnames_hash,
        profile_hash=profile_hash,
        semantic_run_id=semantic_run_id,
    )


def sat(materialization: MaterializationContext, *, credential_ids: tuple[str, ...] = ()) -> Satisfaction:
    return Satisfaction(
        verdict=SatisfactionVerdict.SATISFIED,
        materialization=materialization,
        credential_ids=credential_ids,
    )


def licensing(*satisfactions: Satisfaction, **kwargs) -> Licensing:
    return Licensing(
        route=kwargs.pop("route", LicenseRoute.SEVERE_TEST),
        satisfactions=tuple(satisfactions),
        rival_set_closure=kwargs.pop("rival_set_closure", RivalSetClosure.ENUMERATED),
        **kwargs,
    )


def licensed_claim(cid: str, lic: Licensing) -> Claim:
    return Claim(
        id=cid,
        title=f"claim {cid}",
        pattern=_PATTERN,
        leaves=(CategoricalLeaf(ontology_term=f"term-{cid}"),),
        status=Status.LICENSED,
        licensing=lic,
    )


def corpus_with(*claims: Claim, fdr_ledger: FDRLedger | None = None) -> Corpus:
    return Corpus(
        claims=tuple(claims),
        fdr_ledger=fdr_ledger or FDRLedger(target_fdr=0.05),
    )
```

- [ ] **Step 2: Write the failing test**

Create `tests/attestation/test_helpers.py`:

```python
from __future__ import annotations

from polymer_claims._hashing import canonical_sha256
from polymer_claims.attestation import _bare_hex, _digest_or_none, _subject

from tests.attestation._fixtures import licensed_claim, licensing, mc, sat


def test_bare_hex_strips_algorithm_prefix():
    assert _bare_hex("sha256:abc123") == "abc123"
    assert _bare_hex("abc123") == "abc123"


def test_digest_or_none_accepts_valid_sha256_and_rejects_others():
    valid = "sha256:" + "a" * 64
    assert _digest_or_none(valid).sha256 == "a" * 64
    assert _digest_or_none("h1") is None
    assert _digest_or_none(None) is None
    assert _digest_or_none("sha256:tooshort") is None


def test_subject_digest_matches_canonical_claim_hash():
    claim = licensed_claim("c1", licensing(sat(mc())))
    expected = canonical_sha256(claim.model_dump(mode="json")).split(":", 1)[1]
    subj = _subject(claim)
    assert subj.name == "c1"
    assert subj.digest.sha256 == expected
```

- [ ] **Step 3: Run test to verify it fails**

Run: `uv run pytest -q tests/attestation/test_helpers.py`
Expected: FAIL — `ImportError: cannot import name '_bare_hex'`.

- [ ] **Step 4: Write minimal implementation**

Append to `src/polymer_claims/attestation.py` (add imports `import re` at top with the others, and `from polymer_claims._hashing import canonical_sha256`):

```python
import re

from polymer_claims._hashing import canonical_sha256

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
```

- [ ] **Step 5: Run test to verify it passes**

Run: `uv run pytest -q tests/attestation/test_helpers.py`
Expected: PASS (3 tests).

- [ ] **Step 6: Commit**

```bash
git add src/polymer_claims/attestation.py tests/attestation/_fixtures.py tests/attestation/test_helpers.py
git commit -m "feat(attestation): hashing helpers + subject builder + test fixtures"
```

---

### Task 3: distinct_cohort_reps + private parity guard

**Files:**
- Modify: `src/polymer_claims/attestation.py`
- Test: `tests/attestation/test_helpers.py` (append)

**Interfaces:**
- Consumes: `Licensing`, `Satisfaction` (grammar).
- Produces: `distinct_cohort_reps(licensing: Licensing) -> tuple[Satisfaction, ...]` — one representative per distinct non-None `dimnames_hash`, ascending by `dimnames_hash`, first occurrence wins.

- [ ] **Step 1: Write the failing test (fixture-level expected outputs + a marked parity guard)**

Append to `tests/attestation/test_helpers.py`:

```python
from polymer_claims.attestation import distinct_cohort_reps


def test_distinct_cohort_reps_dedups_and_sorts_by_dimnames_hash():
    s_b = sat(mc(dimnames_hash="sha256:bbb", mid="B"))
    s_a1 = sat(mc(dimnames_hash="sha256:aaa", mid="A1"))
    s_a2 = sat(mc(dimnames_hash="sha256:aaa", mid="A2"))  # duplicate cohort, dropped
    s_none = sat(mc(dimnames_hash=None, mid="N"))  # no cohort, dropped
    lic = licensing(s_b, s_a1, s_a2, s_none)
    reps = distinct_cohort_reps(lic)
    # ascending dimnames_hash, first occurrence: aaa(A1) then bbb(B)
    assert [s.materialization.id for s in reps] == ["A1", "B"]


def test_cohort_rep_parity_PRIVATE_GUARD():
    # Disposable drift alarm: delete if grammar's private `_distinct_cohort_reps` moves/renames.
    from polymer_grammar.licensing import _distinct_cohort_reps

    sats = (
        sat(mc(dimnames_hash="sha256:bbb", mid="B")),
        sat(mc(dimnames_hash="sha256:aaa", mid="A1")),
        sat(mc(dimnames_hash="sha256:aaa", mid="A2")),
        sat(mc(dimnames_hash=None, mid="N")),
    )
    lic = licensing(*sats)
    assert list(distinct_cohort_reps(lic)) == _distinct_cohort_reps(sats)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest -q tests/attestation/test_helpers.py -k cohort`
Expected: FAIL — `ImportError: cannot import name 'distinct_cohort_reps'`.

- [ ] **Step 3: Write minimal implementation**

Append to `src/polymer_claims/attestation.py`:

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest -q tests/attestation/test_helpers.py -k cohort`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add src/polymer_claims/attestation.py tests/attestation/test_helpers.py
git commit -m "feat(attestation): umbrella-local distinct_cohort_reps + parity guard"
```

---

### Task 4: externalParameters + internalParameters

**Files:**
- Modify: `src/polymer_claims/attestation.py`
- Test: `tests/attestation/test_helpers.py` (append)

**Interfaces:**
- Consumes: `Licensing`, `Claim`, `FDRLedger`; DTOs `ExternalParameters`, `InternalParameters`.
- Produces: `_fdr_test_for(ledger, claim_id) -> FDRTest | None`; `_external_parameters(claim, licensing, ledger) -> ExternalParameters`; `_internal_parameters(licensing, *, independence_witnessed: bool) -> InternalParameters`.

- [ ] **Step 1: Write the failing test**

Append to `tests/attestation/test_helpers.py`:

```python
from polymer_grammar import FDRLedger
from polymer_grammar.fdr import FDRTest
from polymer_grammar.licensing import IndependenceTier
from polymer_claims.attestation import _external_parameters, _internal_parameters


def test_external_parameters_pulls_fdr_ledger_fields():
    claim = licensed_claim("c1", licensing(sat(mc())))
    ledger = FDRLedger(
        target_fdr=0.05,
        tests=(FDRTest(index=3, claim_id="c1", e_value=42.0, alpha_allocated=0.0125, discovery=True),),
    )
    ep = _external_parameters(claim, claim.licensing, ledger)
    assert ep.claim_id == "c1"
    assert ep.pattern_id == "adjusted_effect"
    assert ep.license_route == "severe_test"
    assert ep.rival_set_closure == "enumerated"
    assert ep.target_fdr == 0.05
    assert ep.fdr_test_index == 3
    assert ep.fdr_alpha_allocated == 0.0125
    assert ep.fdr_e_value == 42.0


def test_external_parameters_without_matching_ledger_entry_omits_test_fields():
    claim = licensed_claim("c1", licensing(sat(mc())))
    ledger = FDRLedger(target_fdr=0.1)  # no tests
    ep = _external_parameters(claim, claim.licensing, ledger)
    assert ep.target_fdr == 0.1
    assert ep.fdr_test_index is None
    assert ep.fdr_alpha_allocated is None
    assert ep.fdr_e_value is None


def test_internal_parameters_reflects_tier_and_witness():
    lic = licensing(sat(mc()), independence_tier=IndependenceTier.REPLICATED)
    ip = _internal_parameters(lic, independence_witnessed=True)
    assert ip.independence_tier == "replicated"
    assert ip.independence_witnessed is True
    assert ip.severity_provenance is None
    assert ip.shared_cause_overlap is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest -q tests/attestation/test_helpers.py -k parameters`
Expected: FAIL — `ImportError: cannot import name '_external_parameters'`.

- [ ] **Step 3: Write minimal implementation**

Append to `src/polymer_claims/attestation.py`:

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest -q tests/attestation/test_helpers.py -k parameters`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add src/polymer_claims/attestation.py tests/attestation/test_helpers.py
git commit -m "feat(attestation): external/internal SLSA parameter builders (incl. FDR ledger)"
```

---

### Task 5: resolvedDependencies + DRS objects + unresolved fallback

**Files:**
- Modify: `src/polymer_claims/attestation.py`
- Test: `tests/attestation/test_helpers.py` (append)

**Interfaces:**
- Consumes: `distinct_cohort_reps`, `_digest_or_none`, `_bare_hex`; DTOs `ResourceDescriptor`, `Annotations`, `DigestSet`, `DrsObject`, `DrsChecksum`, `DrsAccessMethod`, `DrsAccessURL`; `SEContractRef` from `polymer_claims.contracts`.
- Produces: `_drs_object(ref: SEContractRef) -> DrsObject`; `_resolved_dependencies(licensing, contract_index) -> tuple[tuple[ResourceDescriptor, ...], tuple[DrsObject, ...], tuple[str, ...]]` returning `(deps, drs_objects, unresolved_dimnames_hashes)`.

- [ ] **Step 1: Write the failing test**

Append to `tests/attestation/test_helpers.py`:

```python
from polymer_claims.contracts import AccessMethod, Checksum, SEContractRef
from polymer_claims.attestation import _resolved_dependencies


def _ref(dimnames_hash: str, uid: str) -> SEContractRef:
    return SEContractRef(
        contract_uid=uid,
        dimnames_hash=dimnames_hash,
        assay="meth",
        genome_assembly="GRCh38",
        self_uri=f"drs://local/{uid}",
        size=10,
        checksums=(Checksum(checksum="f" * 64),),
        access_methods=(AccessMethod(type="file", access_url="/tmp/x"),),
    )


def test_resolved_dependencies_resolved_dataset_plus_apparatus():
    lic = licensing(
        sat(mc(dimnames_hash="sha256:" + "a" * 64, profile_hash="sha256:" + "b" * 64, semantic_run_id="r1"))
    )
    idx = {"sha256:" + "a" * 64: _ref("sha256:" + "a" * 64, "ds1")}
    deps, drs, unresolved = _resolved_dependencies(lic, idx)
    roles = {d.annotations.role for d in deps}
    assert roles == {"dataset", "apparatus"}
    dataset = next(d for d in deps if d.annotations.role == "dataset")
    assert dataset.uri == "drs://local/ds1"
    assert dataset.digest.sha256 == "f" * 64  # DRS fixture checksum
    assert dataset.annotations.dimnames_hash == "a" * 64
    apparatus = next(d for d in deps if d.annotations.role == "apparatus")
    assert apparatus.digest.sha256 == "b" * 64
    assert apparatus.annotations.semantic_run_ids == ("r1",)
    assert len(drs) == 1 and drs[0].id == "ds1"
    assert unresolved == ()


def test_resolved_dependencies_unresolved_dataset_falls_back():
    h = "sha256:" + "c" * 64
    lic = licensing(sat(mc(dimnames_hash=h)))
    deps, drs, unresolved = _resolved_dependencies(lic, {})  # empty index
    dataset = next(d for d in deps if d.annotations.role == "dataset")
    assert dataset.uri == "drs://local/dimnames/" + "c" * 64
    assert dataset.digest.sha256 == "c" * 64
    assert drs == ()
    assert unresolved == (h,)


def test_resolved_dependencies_shared_profile_collects_run_ids():
    p = "sha256:" + "b" * 64
    lic = licensing(
        sat(mc(dimnames_hash="sha256:" + "a" * 64, profile_hash=p, semantic_run_id="r2")),
        sat(mc(dimnames_hash="sha256:" + "d" * 64, profile_hash=p, semantic_run_id="r1")),
        independence_tier=IndependenceTier.REPLICATED,
    )
    deps, _drs, _u = _resolved_dependencies(lic, {})
    apparatus = [d for d in deps if d.annotations.role == "apparatus"]
    assert len(apparatus) == 1  # one per distinct profile hash
    assert apparatus[0].annotations.semantic_run_ids == ("r1", "r2")  # sorted, none lost
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest -q tests/attestation/test_helpers.py -k resolved`
Expected: FAIL — `ImportError: cannot import name '_resolved_dependencies'`.

- [ ] **Step 3: Write minimal implementation**

Append to `src/polymer_claims/attestation.py`:

```python
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
        deps.append(
            ResourceDescriptor(
                name="analysis-profile",
                digest=_digest_or_none(ph),
                annotations=Annotations(
                    role="apparatus", semantic_run_ids=rids if rids else None
                ),
            )
        )

    return tuple(deps), tuple(drs[k] for k in sorted(drs)), tuple(unresolved)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest -q tests/attestation/test_helpers.py -k resolved`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add src/polymer_claims/attestation.py tests/attestation/test_helpers.py
git commit -m "feat(attestation): resolvedDependencies + DRS objects + unresolved fallback"
```

---

### Task 6: builder (registry-optional builderDependencies)

**Files:**
- Modify: `src/polymer_claims/attestation.py`
- Test: `tests/attestation/test_helpers.py` (append)

**Interfaces:**
- Consumes: `_digest_or_none`; DTOs `Builder`, `ResourceDescriptor`, `Annotations`; `AdapterRegistry`, `AdapterCredential`, `independent_credential_pair` from `polymer_protocol`.
- Produces: `_builder(licensing, registry) -> tuple[Builder, bool]` — the Builder plus `independence_witnessed`. builderDependencies = union of all `credential_ids` across satisfactions (deduped, sorted), digests resolved only when the registry resolves a valid `sha256:` hash (else `rawImplementationHash` annotation when the credential resolves but its hash is non-sha256).

- [ ] **Step 1: Write the failing test**

Append to `tests/attestation/test_helpers.py`:

```python
from polymer_protocol import AdapterCredential, AdapterRegistry
from polymer_claims.attestation import _builder


def test_builder_no_registry_emits_named_deps_unwitnessed():
    lic = licensing(sat(mc(), credential_ids=("adapter-x", "adapter-y")))
    builder, witnessed = _builder(lic, None)
    assert builder.id == "https://polymerclaims.org/recompute-gate/v1"
    assert [d.name for d in builder.builder_dependencies] == ["adapter-x", "adapter-y"]
    assert all(d.digest is None for d in builder.builder_dependencies)
    assert witnessed is False


def test_builder_empty_credentials_is_empty_and_unwitnessed():
    builder, witnessed = _builder(licensing(sat(mc())), None)
    assert builder.builder_dependencies == ()
    assert witnessed is False


def test_builder_with_registry_resolves_digest_and_witness():
    registry = AdapterRegistry(
        credentials=(
            AdapterCredential(identity="adapter-x", owner="lab-a", implementation_hash="sha256:" + "1" * 64),
            AdapterCredential(identity="adapter-y", owner="lab-b", implementation_hash="sha256:" + "2" * 64),
        )
    )
    lic = licensing(sat(mc(), credential_ids=("adapter-x", "adapter-y")))
    builder, witnessed = _builder(lic, registry)
    by_name = {d.name: d for d in builder.builder_dependencies}
    assert by_name["adapter-x"].digest.sha256 == "1" * 64
    assert witnessed is True  # distinct owner + distinct impl hash -> independent pair


def test_builder_registry_nonsha_hash_omits_digest_keeps_raw():
    registry = AdapterRegistry(
        credentials=(AdapterCredential(identity="adapter-z", owner="lab-c", implementation_hash="h1"),)
    )
    lic = licensing(sat(mc(), credential_ids=("adapter-z",)))
    builder, _w = _builder(lic, registry)
    dep = builder.builder_dependencies[0]
    assert dep.digest is None
    assert dep.annotations.raw_implementation_hash == "h1"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest -q tests/attestation/test_helpers.py -k builder`
Expected: FAIL — `ImportError: cannot import name '_builder'`.

- [ ] **Step 3: Write minimal implementation**

Append to `src/polymer_claims/attestation.py` (add `from polymer_protocol import independent_credential_pair` near the top-of-file imports):

```python
from polymer_protocol import independent_credential_pair


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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest -q tests/attestation/test_helpers.py -k builder`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add src/polymer_claims/attestation.py tests/attestation/test_helpers.py
git commit -m "feat(attestation): registry-optional builder + independence witness"
```

---

### Task 7: build_attestation_bundle (assembly, determinism, golden)

**Files:**
- Modify: `src/polymer_claims/attestation.py`
- Test: `tests/attestation/test_build_bundle.py`

**Interfaces:**
- Consumes: every helper from Tasks 2–6; DTOs `Statement`, `SlsaPredicate`, `BuildDefinition`, `RunDetails`, `RunMetadata`, `AttestationBundle`; `Status` from grammar.
- Produces: `_dep_sort_key(d: ResourceDescriptor) -> tuple`; `_statement(claim, ledger, contract_index, registry) -> tuple[Statement, tuple[DrsObject, ...], tuple[str, ...]]`; `build_attestation_bundle(corpus, *, contract_index, registry=None) -> AttestationBundle`.

- [ ] **Step 1: Write the failing test**

Create `tests/attestation/test_build_bundle.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest -q tests/attestation/test_build_bundle.py`
Expected: FAIL — `ImportError: cannot import name 'build_attestation_bundle'`.

- [ ] **Step 3: Write minimal implementation**

Append to `src/polymer_claims/attestation.py` (add `from polymer_grammar import Status` near the imports):

```python
from polymer_grammar import Status


def _dep_sort_key(d) -> tuple:
    role = d.annotations.role if d.annotations and d.annotations.role else ""
    sha = d.digest.sha256 if d.digest else ""
    rids = d.annotations.semantic_run_ids if d.annotations else None
    first_rid = rids[0] if rids else ""
    return (role, d.name, d.uri or "", sha, first_rid)


def _statement(claim, ledger, contract_index, registry):
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


def build_attestation_bundle(corpus, *, contract_index, registry=None) -> AttestationBundle:
    """Deterministic in-toto/SLSA attestation bundle + DRS object docs for a corpus's LICENSED claims.

    Pure: `contract_index` (dimnames_hash -> SEContractRef) and `registry` (AdapterRegistry | None)
    are injected; no IO/clock/random."""
    statements = []
    drs: dict = {}
    unresolved: set[str] = set()
    licensed = sorted(
        (c for c in corpus.claims if c.status == Status.LICENSED and c.licensing is not None),
        key=lambda c: c.id,
    )
    for claim in licensed:
        statement, drs_objects, claim_unresolved = _statement(
            claim, corpus.fdr_ledger, contract_index, registry
        )
        statements.append(statement)
        for obj in drs_objects:
            drs[obj.id] = obj
        unresolved.update(claim_unresolved)
    return AttestationBundle(
        attestations=tuple(statements),
        drs_objects=tuple(drs[k] for k in sorted(drs)),
        unresolved_datasets=tuple(sorted(unresolved)),
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest -q tests/attestation/test_build_bundle.py`
Expected: PASS (5 tests).

- [ ] **Step 5: Add a golden byte-stability test**

Append to `tests/attestation/test_build_bundle.py`:

```python
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
```

- [ ] **Step 6: Run test to verify it passes**

Run: `uv run pytest -q tests/attestation/test_build_bundle.py`
Expected: PASS (6 tests).

- [ ] **Step 7: Commit**

```bash
git add src/polymer_claims/attestation.py tests/attestation/test_build_bundle.py
git commit -m "feat(attestation): build_attestation_bundle assembly + determinism + golden"
```

---

### Task 8: resolve_contract_index (IO resolver)

**Files:**
- Modify: `src/polymer_claims/attestation.py`
- Test: `tests/attestation/test_resolve_contracts.py`

**Interfaces:**
- Consumes: `load_contract`, and the bundled-manifest directory `_DIR` from `polymer_claims.contracts`.
- Produces: `resolve_contract_index(corpus, *, extra: Iterable[SEContractRef] = ()) -> dict[str, SEContractRef]` — reverse-maps bundled SE-Contracts by `dimnames_hash`; `extra` injected without IO; bundled manifests that fail to load are skipped (never crash).

- [ ] **Step 1: Write the failing test**

Create `tests/attestation/test_resolve_contracts.py`:

```python
from __future__ import annotations

from polymer_claims.attestation import resolve_contract_index
from polymer_claims.contracts import AccessMethod, Checksum, SEContractRef
from tests.attestation._fixtures import corpus_with


def _ref(h: str, uid: str) -> SEContractRef:
    return SEContractRef(
        contract_uid=uid,
        dimnames_hash=h,
        assay="meth",
        genome_assembly="GRCh38",
        self_uri=f"drs://local/{uid}",
        size=10,
        checksums=(Checksum(checksum="f" * 64),),
        access_methods=(AccessMethod(type="file", access_url="/tmp/x"),),
    )


def test_extra_contracts_indexed_by_dimnames_hash():
    h = "sha256:" + "e" * 64
    idx = resolve_contract_index(corpus_with(), extra=(_ref(h, "ds-extra"),))
    assert idx[h].contract_uid == "ds-extra"


def test_resolver_never_crashes_and_returns_dict():
    # Bundled manifests are loaded best-effort; the call must always return a dict.
    idx = resolve_contract_index(corpus_with())
    assert isinstance(idx, dict)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest -q tests/attestation/test_resolve_contracts.py`
Expected: FAIL — `ImportError: cannot import name 'resolve_contract_index'`.

- [ ] **Step 3: Write minimal implementation**

Append to `src/polymer_claims/attestation.py` (add imports `import json as _json` is NOT needed — reuse stdlib `json`; add `from collections.abc import Iterable`, `from polymer_claims.contracts import _DIR as _CONTRACTS_DIR, load_contract`):

```python
import json
from collections.abc import Iterable

from polymer_claims.contracts import _DIR as _CONTRACTS_DIR
from polymer_claims.contracts import load_contract


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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest -q tests/attestation/test_resolve_contracts.py`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add src/polymer_claims/attestation.py tests/attestation/test_resolve_contracts.py
git commit -m "feat(attestation): resolve_contract_index IO resolver (best-effort, no-crash)"
```

---

### Task 9: CLI subcommand `export-attestation`

**Files:**
- Modify: `src/polymer_claims/cli.py` (append a handler near the other `_cmd_export_*` handlers around lines 197–229; append a subparser before `main()` at the end of `_build_parser`, after the last `set_defaults` at line 499)
- Test: `tests/attestation/test_cli.py`

**Interfaces:**
- Consumes: `load_corpus` (already imported in cli.py line 42), `_write_or_print` (cli.py lines 61–65), `build_attestation_bundle`, `resolve_contract_index`.
- Produces: `_cmd_export_attestation(args) -> int`; subcommand `export-attestation <corpus> [--out PATH]`.

- [ ] **Step 1: Write the failing test**

Create `tests/attestation/test_cli.py`:

```python
from __future__ import annotations

import json

from polymer_claims.cli import main
from polymer_claims.io import dump_corpus
from tests.attestation._fixtures import corpus_with, licensed_claim, licensing, mc, sat


def _write_corpus(tmp_path):
    claim = licensed_claim("c1", licensing(sat(mc(dimnames_hash="sha256:" + "a" * 64))))
    path = tmp_path / "corpus.json"
    path.write_text(dump_corpus(corpus_with(claim)))
    return path


def test_export_attestation_writes_bundle(tmp_path):
    corpus_path = _write_corpus(tmp_path)
    out = tmp_path / "att.json"
    rc = main(["export-attestation", str(corpus_path), "--out", str(out)])
    assert rc == 0
    data = json.loads(out.read_text())
    assert data["bundleType"] == "https://polymerclaims.org/attestation-bundle/v1"
    assert data["attestations"][0]["subject"][0]["name"] == "c1"
```

Note: confirm the corpus serializer helper name with `grep -n "def dump_corpus" src/polymer_claims/io.py`; it is imported alongside `load_corpus` in `cli.py:42`. If it is named differently, use that name.

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest -q tests/attestation/test_cli.py`
Expected: FAIL — `SystemExit: 2` / "invalid choice: 'export-attestation'".

- [ ] **Step 3: Add the handler**

In `src/polymer_claims/cli.py`, immediately after `_cmd_export_consistency` (ends ~line 218), add:

```python
def _cmd_export_attestation(args: argparse.Namespace) -> int:
    from .attestation import build_attestation_bundle, resolve_contract_index

    corpus = load_corpus(args.corpus)
    bundle = build_attestation_bundle(corpus, contract_index=resolve_contract_index(corpus))
    _write_or_print(bundle.model_dump_json(by_alias=True, exclude_none=True), args.out)
    return 0
```

- [ ] **Step 4: Register the subparser**

In `_build_parser`, immediately after the last `set_defaults` (the `p_serve.set_defaults(func=_cmd_serve)` at ~line 499), add:

```python
    p_att = sub.add_parser(
        "export-attestation",
        help="emit an in-toto/SLSA attestation bundle (+ DRS objects) for a corpus's LICENSED claims",
    )
    p_att.add_argument("corpus", help="path to a corpus JSON file")
    p_att.add_argument("--out", default=None, help="write the attestation bundle JSON here")
    p_att.set_defaults(func=_cmd_export_attestation)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `uv run pytest -q tests/attestation/test_cli.py`
Expected: PASS (1 test).

- [ ] **Step 6: Commit**

```bash
git add src/polymer_claims/cli.py tests/attestation/test_cli.py
git commit -m "feat(attestation): export-attestation CLI subcommand"
```

---

### Task 10: public exports

**Files:**
- Modify: `src/polymer_claims/__init__.py` (imports block near lines 1–31; `__all__` at lines 32–48)
- Test: `tests/attestation/test_build_bundle.py` (append)

**Interfaces:**
- Produces: top-level `polymer_claims.build_attestation_bundle`, `polymer_claims.resolve_contract_index`, `polymer_claims.AttestationBundle`.

- [ ] **Step 1: Write the failing test**

Append to `tests/attestation/test_build_bundle.py`:

```python
def test_public_api_exports():
    import polymer_claims as pc

    assert hasattr(pc, "build_attestation_bundle")
    assert hasattr(pc, "resolve_contract_index")
    assert hasattr(pc, "AttestationBundle")
    assert "build_attestation_bundle" in pc.__all__
    assert "AttestationBundle" in pc.__all__
    assert "resolve_contract_index" in pc.__all__
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest -q tests/attestation/test_build_bundle.py::test_public_api_exports`
Expected: FAIL — `AssertionError` (attribute missing).

- [ ] **Step 3: Add the exports**

In `src/polymer_claims/__init__.py`, add an import line in the import block (after the existing `from polymer_claims.contracts import (...)` group):

```python
from polymer_claims.attestation import (
    AttestationBundle,
    build_attestation_bundle,
    resolve_contract_index,
)
```

Then add these three names to the `__all__` list (keep it alphabetically sorted to match the existing style), so the list includes:

```python
    "AnalysisProfile",
    "AttestationBundle",
    ...
    "build_attestation_bundle",
    ...
    "resolve_contract_index",
    ...
```

(Insert `"AttestationBundle"` after `"AnalysisProfile"`, `"build_attestation_bundle"` after `"__version__"`/before `"content_hash"`, and `"resolve_contract_index"` before `"run_cycle"` — keeping the existing alphabetical ordering.)

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest -q tests/attestation/test_build_bundle.py::test_public_api_exports`
Expected: PASS.

- [ ] **Step 5: Full gate**

Run: `uv run pytest -q tests/attestation && uv run ruff check src tests`
Expected: all attestation tests PASS, ruff clean. Then sanity-check nothing else broke: `uv run pytest -q` (umbrella suite green).

- [ ] **Step 6: Commit**

```bash
git add src/polymer_claims/__init__.py tests/attestation/test_build_bundle.py
git commit -m "feat(attestation): export public API (build_attestation_bundle, resolve_contract_index, AttestationBundle)"
```

---

## Final Verification

- [ ] `uv run pytest -q tests/attestation` — all green.
- [ ] `uv run ruff check src tests` — clean.
- [ ] `uv run pytest -q` — full umbrella suite green (additive change broke nothing).
- [ ] Manual smoke: build a tiny LICENSED corpus JSON and run `uv run polymer-claims export-attestation <corpus> --out /tmp/att.json` (or `python -m polymer_claims.cli ...` if no console script); confirm the bundle has `bundleType`, one `attestations[]` entry per LICENSED claim with `_type`/`predicateType`/`predicate`, and `drsObjects`/`unresolvedDatasets` as expected.
- [ ] Update `docs/superpowers/CONTINUE.md` *Current state* + *Recently shipped* and the canonical spec pointer (coordinate the shared-doc edit with the arc-3 sibling at merge), then merge `--no-ff` to `main`.

## Self-Review notes (coverage check vs spec)

- Spec §3 purity split → Tasks 7 (pure builder) + 8 (IO resolver). ✔
- §4.1 subject digest → Task 2. ✔
- §4.2 build/run details, builder trust model, registry-optional witnesses, digest normalization, externalParameters incl. FDR, apparatus semanticRunIds tuple → Tasks 4, 5, 6, 7. ✔
- §4.3 DRS object (wrapped access_url) → Task 5 + golden in Task 7. ✔
- §4.4 bundle + bundleType → Tasks 1, 7. ✔
- §5 determinism/full sort key, empty corpus, unresolved fallback, no-credential case → Tasks 5, 6, 7. ✔
- §6 typed frozen DTOs / no open dict → Task 1. ✔
- §7 test list → distributed across tasks. ✔
- §8 exports + CLI wiring (append-only) → Tasks 9, 10. ✔
- §9 out-of-scope (signing/DSSE/ndjson/security-model-doc publish) → not implemented (correct). ✔
