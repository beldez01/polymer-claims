# Standards Skin — slice 1: in-toto/SLSA attestation export (design)

> North-Star arc 2 (the standards skin / adoption moat), first slice.
> Worktree `/Users/zbb2/Desktop/polymer-claims-arc2`, branch `feat/standards-skin-attestation`.
> Strategy: north-star §4 (pan-integrator seams; in-toto/SLSA + Sigstore/Rekor ranked #3) and §6
> (sequencing: arc 2). Kickoff: `ARC2-KICKOFF.md`.

## 1. Goal & scope

Add a new umbrella command `export-attestation <corpus>` that turns every **LICENSED** claim in a
corpus into a deterministic, content-addressed **in-toto Statement v1** carrying a **SLSA Provenance
v1** predicate (current v1.x Build Provenance shape — see §1.1), plus standalone **GA4GH DRS object** docs
for the datasets those claims were licensed on.

The thesis: don't integrate the world's data/compute — integrate *trust over* it. Re-express the
content-address / apparatus / run model we already compute **as the standards that already exist**, so
a third party can verify a licensed run *without trusting our service*. Slice 1 produces a pure,
content-addressed JSON shape any third party could **later** sign; signing/Rekor is a separate slice.

**In scope:** the deterministic serializer + CLI command + new exports. Strictly additive — existing
behavior is byte-identical; nothing existing changes.

**Standards fidelity:** strict at the **Statement** level — each element of the bundle is a real in-toto
Statement v1 envelope whose `predicate` matches the SLSA Provenance v1 / current v1.x Build Provenance
shape (`buildDefinition` / `runDetails`), and each DRS doc is GA4GH `DrsObject`-shaped, such that an
off-the-shelf verifier handed a single **Statement** accepts its shape. The **top-level bundle**
(`{ bundleType, attestations, drsObjects, unresolvedDatasets }`) is a Polymer-specific envelope, NOT a
standard container — a standard verifier expects a bare Statement or a DSSE envelope, not the bundle.
The bundle is a convenience container over verifier-compatible Statements; a future slice can add a
`--format ndjson` / one-Statement-per-file export mode (and, later, DSSE) for direct verifier ingestion.

### 1.1 SLSA version note

The predicate type stays `https://slsa.dev/provenance/v1` — it is stable across the v1.x line. SLSA
**v1.0** is retired; the current approved spec is **v1.2 Build Provenance**, which preserves the same
predicate type and the `buildDefinition` / `runDetails` structure used here. Throughout this doc "SLSA
Provenance v1" means "the current v1.x Build Provenance shape," not v1.0 specifically.

## 2. Hard invariants (inherited)

- **Purity:** `grammar/` and `protocol/` stay pure/deterministic/numpy-free. All of this slice is
  **umbrella-side** (`src/polymer_claims/`). The pure builder takes time-like / IO-derived inputs as
  injected params (see §3) so the serializer itself is deterministic and clock/random/IO-free.
- **Zero new deps.** Stdlib `json`/`hashlib` only (`canonical_sha256` already exists in
  `src/polymer_claims/_hashing.py`). No Sigstore/cosign/Rekor.
- **Additive / byte-identical when off:** new module + new CLI subcommand + new `__init__` exports.
  No existing export, model, or command is touched. `Corpus` stays exactly 4 collections.
- **Frozen models:** all new DTOs subclass `_Model` (frozen, `extra="forbid"`); collection fields are
  **tuples**, never `dict`/`list`.
- **SLSA JSON maps as typed DTOs.** SLSA/in-toto have JSON *objects* with map-like values (`digest`,
  `externalParameters`, `internalParameters`, `annotations`). We preserve the no-`dict` invariant by
  modeling each as a **typed frozen DTO with fixed, optional fields** (we control exactly which keys we
  emit), serialized with `exclude_none` so unset keys vanish. Concretely: `DigestSet{ sha256 }`;
  `ExternalParameters{ claimId, patternId, licenseRoute, rivalSetClosure, targetFdr?, fdrTestIndex?,
  fdrAlphaAllocated?, fdrEValue? }`; `InternalParameters{ independenceTier, severityProvenance?,
  sharedCauseOverlap? }`; a single `Annotations{ role?, dimnamesHash?, semanticRunIds?,
  rawImplementationHash?, independenceWitnessed? }` superset reused across descriptors. No open
  `dict[str, Any]` fields anywhere.
- **No clock.** Timestamps are deliberately omitted (SLSA marks them optional) so output is
  deterministic and the no-clock invariant holds.
- **TDD:** failing test first; per-package gate `uv run pytest -q` + `uv run ruff check src tests`.

## 3. Module layout & purity split

New file `src/polymer_claims/attestation.py`, mirroring the `export_topology` / `export_consistency`
pattern but applying the repo's purity discipline *within* the umbrella module:

- **Pure builder** — `build_attestation_bundle(corpus, *, contract_index: Mapping[str, SEContractRef],
  registry: AdapterRegistry | None = None) -> AttestationBundle`. Deterministic, no IO/clock/random.
  Takes resolved contracts (and the adapter registry, for `implementation_hash` lookup) as injected
  params — exactly as grammar/protocol take time-like inputs as params — so it is golden-testable with
  fixtures and contains no surprises.
- **Umbrella resolver** — `resolve_contract_index(corpus, *, extra: Iterable[SEContractRef] = ()) ->
  dict[str, SEContractRef]`. The only IO. Enumerates the bundled SE-Contract manifests, `load_contract`s
  each, and reverse-maps `dimnames_hash → SEContractRef`. `extra` lets callers/tests inject more
  contracts without IO. Unresolvable datasets (local/gitignored TCGA contracts) are simply absent — the
  builder degrades gracefully (never crashes), the same contract `load_contract` already honors
  (`FileNotFoundError` → degrade, never crash the run).
- **CLI handler** — `_cmd_export_attestation(args)` wires `load_corpus → resolve_contract_index →
  build_attestation_bundle → model_dump_json(by_alias=True, exclude_none=True) → _write_or_print`.

The registry passed to the builder is the standard adapter registry used elsewhere in the umbrella; if
a credential id is not resolvable in it, that builder-dependency carries the id with no digest (we never
fabricate a hash).

## 4. The mapping (in-toto v1 / SLSA Provenance v1)

**Granularity:** one Statement per LICENSED claim, collected into a bundle (mirrors how a real CI emits
one provenance per produced artifact). For a claim's datasets we need "one representative `Satisfaction`
per distinct `dimnames_hash`" so REPLICATED claims contribute one dependency per distinct cohort.

**Cohort-representative helper (umbrella-local).** Grammar's `licensing.py` has this dedup but as a
**private** helper (`_distinct_cohort_reps`) — and this slice must stay umbrella-side without reaching
into grammar internals. So `attestation.py` gets its own small public helper
`distinct_cohort_reps(licensing) -> tuple[Satisfaction, ...]` (one representative per distinct non-None
`dimnames_hash`, deterministic: ascending `dimnames_hash`, first occurrence — identical rule to grammar's).
A **parity test** asserts it agrees with grammar's private helper on shared fixtures, so the duplication
can't silently drift. (Alternative considered and rejected: promote/export the grammar private — avoided
to keep grammar untouched and the slice umbrella-only.)

### 4.1 in-toto Statement v1

```
Statement:
  _type:         "https://in-toto.io/Statement/v1"
  subject:       [{ name: <claim.id>, digest: { sha256: <hex> } }]
  predicateType: "https://slsa.dev/provenance/v1"
  predicate:     <SLSA Provenance v1>   # §4.2
```

- **subject.digest.sha256** = `canonical_sha256(claim.model_dump(mode="json"))` with the `sha256:`
  prefix stripped to bare hex (in-toto digest-map convention; `canonical_sha256` returns
  `"sha256:<hex>"`). The subject **is** the licensed claim artifact — the "licensed output hash."

### 4.2 SLSA Provenance v1 predicate

```
predicate:
  buildDefinition:
    buildType: "https://polymerclaims.org/recompute-gate/v1"
    externalParameters:                               # scalar policy inputs (no claim-artifact parsing)
      claimId, patternId, licenseRoute, rivalSetClosure,
      targetFdr?, fdrTestIndex?, fdrAlphaAllocated?, fdrEValue?   # from the corpus fdr_ledger entry, when present
    internalParameters:                               # CLAIM-level only (single-valued)
      independenceTier,
      severityProvenance?, sharedCauseOverlap?        # ?-fields omitted (exclude_none) when None
    resolvedDependencies:
      # one DATASET dep per distinct dimnames_hash (representative satisfactions, §4 dedup):
      - name: "se-contract:<uid>"
        uri:  <DRS self_uri>                          # drs://local/<uid> when resolved
        digest: { sha256: <DRS fixture checksum hex, or dimnames_hash hex if unresolved> }
        annotations: { role: "dataset", dimnamesHash: <dimnames_hash hex> }
      # one APPARATUS dep per distinct profileHash across those representatives:
      - name: "analysis-profile"
        digest: { sha256: <profileHash hex> }
        annotations: { role: "apparatus", semanticRunIds: (<sorted tuple of run ids>) }  # see note
  runDetails:
    builder:
      id: "https://polymerclaims.org/recompute-gate/v1"   # stable id; INTENDED to resolve to the security-model doc
      builderDependencies:                                 # the air-gap witnesses (security-relevant; see note)
        - name: <credential_id_1>, digest:{ sha256:<implementation_hash> }, annotations:{role:"adapter"}
        - name: <credential_id_2>, digest:{ sha256:<implementation_hash> }, annotations:{role:"adapter"}
    metadata: { invocationId: <representative semanticRunId> }   # lowest-dimnames_hash rep; NO clock
```

- **builder / security model.** SLSA reserves `builder.builderDependencies` for *orchestrator*
  dependencies that affect the provenance's security guarantees — not ordinary workload inputs. That is
  exactly what the adapter pair is here: the **recompute gate is the trusted build platform**, and its
  core security guarantee is **independence** (two air-gapped adapters, distinct owner + distinct
  `implementation_hash`, from `independent_credential_pair(registry, satisfaction.credential_ids)`).
  The adapters are therefore part of the gate's trusted boundary, which is why they belong in
  `builderDependencies` rather than `resolvedDependencies` (workload inputs) or `byproducts`. In slice 1
  the `buildType` / `builder.id` URI (`https://polymerclaims.org/recompute-gate/v1`) is treated as an
  **opaque stable identifier** and is **intended to resolve** to a published build-type + security-model
  doc; actually publishing that document is a tracked follow-up (§9), not a slice-1 deliverable — so the
  spec does not claim the URL is live.
- **externalParameters are scalars, not the claim artifact.** `claimId`, `patternId`, `licenseRoute`,
  `rivalSetClosure` come from the claim/licensing; `targetFdr`, `fdrTestIndex`, `fdrAlphaAllocated`,
  `fdrEValue` are pulled from the corpus `fdr_ledger` entry for this claim **when present** (omitted via
  `exclude_none` otherwise). Surfacing these as scalars lets a downstream policy verifier check the FDR
  budget without re-parsing the whole licensed-claim artifact. (Exact ledger field names are bound in the
  plan; the builder reads the ledger entry already available in the in-memory `Corpus`.)
- **builderDependencies population (registry-optional).** The witness *identities* are recorded directly
  on `satisfaction.credential_ids`, but `implementation_hash` lives only in an `AdapterRegistry` (there
  is **no** module-level default registry in the umbrella). So `build_attestation_bundle` takes
  `registry: AdapterRegistry | None = None` and:
    - emits one `ResourceDescriptor` per identity in `satisfaction.credential_ids` (deterministic;
      `role: "adapter"`), with a `digest` **only** when a registry is supplied and resolves that
      identity to a valid `sha256:` `implementation_hash` (else no digest, per digest-normalization);
    - sets `independenceWitnessed: true` **iff** a registry is supplied **and**
      `independent_credential_pair(registry, satisfaction.credential_ids)` returns a verified pair;
      otherwise `independenceWitnessed: false`. We never fabricate a witness or a hash.
    - **empty `credential_ids`** (legacy) → `builderDependencies: ()` + `independenceWitnessed: false`.
  The **slice-1 CLI** runs on a cold from-disk corpus with `registry=None` → witness identities are
  emitted by name, digests omitted, `independenceWitnessed: false`. Registry-backed digests +
  verified-independence are exercised by tests (injected `AdapterRegistry` fixture) and by programmatic
  in-process callers (the live node, which holds the registry) — wiring that into the CLI is a follow-up.
- **Apparatus `semanticRunIds`** is a **sorted tuple** of every run id among the representatives sharing
  that `profileHash` (deduped → sorted) — so no run id is lost when two cohorts share an analysis profile.
- **Digest normalization.** Any content-address that is a valid `sha256:<hex>` is stripped to bare hex in
  its `digest` map. If a value is **not** a valid `sha256:` digest (e.g. a legacy/test
  `implementation_hash` like `h1`), the exporter **omits** the `digest` field and records the raw value
  in a transparent annotation (`rawImplementationHash: <value>`) — it never emits an invalid digest. A
  small `_digest_or_none(value) -> DigestSet | None` helper centralizes this. Applies to
  `implementation_hash`, and defensively to `profileHash` / `dimnames_hash` (which are
  `canonical_sha256`-produced and so normally valid).
- **Timestamps omitted** (`startedOn`/`finishedOn`) — keeps output deterministic; SLSA marks them
  optional.

### 4.3 GA4GH DRS object (one per distinct resolved dataset)

```
DrsObject:
  id, self_uri, size,
  checksums:      [{ type: "sha-256", checksum: <hex> }],
  access_methods: [{ type: <file|https|s3>, access_url: { url: <...> } }],
  name
```

Built straight from `SEContractRef` (`self_uri`, `size`, `checksums`, `access_methods`). Note the DRS
spec wraps `access_url` as an object `{ url: ... }`, vs the ref's flat string — the serializer adapts.
Datasets that don't resolve to a bundled contract produce **no** DRS object (see §5).

### 4.4 The bundle (the `--out` file)

```
AttestationBundle:
  bundleType:          "https://polymerclaims.org/attestation-bundle/v1"   # version the custom envelope
  attestations:        (Statement, ...)        # sorted by claim.id
  drsObjects:          (DrsObject, ...)         # sorted by id
  unresolvedDatasets:  (<dimnames_hash hex>, ...)   # best-effort transparency for non-bundled contracts
```

`bundleType` versions this Polymer-specific envelope so a future signing/DSSE slice can distinguish
bundle versions without guessing (the per-element Statements carry their own in-toto/SLSA type URIs).
One CLI call → one bundle JSON containing both the attestations and their companion DRS objects.

## 5. Determinism, errors, edge cases

- **Determinism:** sorted `attestations` (by `claim.id`), sorted `drsObjects` (by `id`), tuple
  collections, no clock/random. `resolvedDependencies` sort on a **full stable key** —
  `(annotations.role or "", name, uri or "", digest.sha256 or "", semanticRunIds[0] if semanticRunIds else "")`
  — so multiple `analysis-profile` entries (distinct profile hashes) can't tie. The final element is the
  first id of the already-sorted `semanticRunIds` tuple, or `""` when that tuple is empty/absent.
  `builderDependencies` sort by `(name, digest.sha256 or "")`. A test exports the same corpus twice and
  asserts byte-identical output.
- **No LICENSED claims** → empty bundle (`attestations: ()`, `drsObjects: ()`,
  `unresolvedDatasets: ()`), exit 0.
- **`dimnames_hash` is None** (apparatus-only / `builtin::const` run) → the dataset dependency is
  omitted; the apparatus (`analysis-profile`) dependency still emits when `profileHash` is present.
- **Contract unresolvable** (local/gitignored, not bundled) → no DRS object for that dataset; the
  `resolvedDependencies` digest falls back to the `dimnames_hash` hex and the `uri` to a synthetic
  `drs://local/dimnames/<hash>`; the `dimnames_hash` is appended to `unresolvedDatasets`. Never crashes.
- **No independent credential pair** → `builderDependencies: ()` + `independenceWitnessed: false`.
- **LICENSED claim with `licensing is None`** → should not occur (status invariant); defensively skip
  with a `stderr` note rather than crash.

## 6. Serialization

Typed frozen `_Model` DTOs (`Statement`, `Subject`, `SlsaPredicate`, `BuildDefinition`, `RunDetails`,
`Builder`, `ResourceDescriptor`, `DigestSet`, `DrsObject`, `Checksum`, `AccessMethod`, `AttestationBundle`;
`AttestationBundle` carries the `bundleType` envelope-version field) with pydantic `alias=` for camelCase
and `_type` (python field `type_`, `alias="_type"`). Serialize via
`model_dump_json(by_alias=True, exclude_none=True)`. This matches the repo's DTO convention (like
`TopologyExport`), gives schema validation, and is deterministic (ordered fields + tuples). `_Model`'s
`populate_by_name=True` supports the alias plumbing.

(Considered and rejected for slice 1: a plain-dict + `json.dumps(sort_keys=True)` builder. It maximizes
fidelity to an externally-owned schema and trivializes `_type`/camelCase, but loses typing and breaks
the repo's frozen-DTO convention. The typed route is preferred for consistency + validation.)

## 7. Tests (TDD — failing first)

- Golden in-toto Statement for a fixture LICENSED claim — byte-stable.
- `subject.digest.sha256` equals an independently recomputed `canonical_sha256(claim)` (prefix-stripped).
- REPLICATED claim → two dataset `resolvedDependencies` + `independenceTier == "REPLICATED"`.
- Structural conformance (current in-toto Statement v1 + SLSA v1.x Build Provenance): required in-toto
  fields (`_type`, `subject`, `predicateType`, `predicate`) and required SLSA fields
  (`buildDefinition.buildType`, `runDetails.builder.id`) are present — asserted structurally, no new
  schema dependency.
- DRS object shape (`self_uri`, `checksums[].type == "sha-256"`, `access_methods[].access_url.url`).
- **Cohort-rep correctness** (#7): `distinct_cohort_reps` is verified primarily against **fixture-level
  expected outputs** (hand-authored single- and multi-cohort licensings → expected representative tuples)
  — this is the authoritative test and depends on no grammar internals. A **separate, explicitly-marked
  guard** (`test_cohort_rep_parity_PRIVATE_GUARD`, commented "delete if grammar's `_distinct_cohort_reps`
  moves/renames") cross-checks parity with the grammar private as a short-term drift alarm only.
- **Apparatus run-id completeness** (#4): two representatives sharing a `profileHash` but with different
  `semanticRunId`s → the apparatus dep's `semanticRunIds` is the sorted tuple of both (none lost).
- **Digest normalization** (#6): a credential whose `implementation_hash` is not a valid `sha256:` digest
  (e.g. `h1`) → that builder-dependency has **no** `digest`, carries `rawImplementationHash`, no crash.
- **Full-key determinism** (#5): a claim with two distinct `analysis-profile` deps → stable, non-tying
  `resolvedDependencies` order; two exports byte-identical.
- **Bundle envelope** (#8): `bundleType == "https://polymerclaims.org/attestation-bundle/v1"` present.
- Unresolved-contract fallback: DRS object skipped, dependency digest falls back to `dimnames_hash`,
  `uri` is the synthetic `drs://local/dimnames/<hash>`, id recorded in `unresolvedDatasets`, no crash.
- Determinism: two exports of the same corpus are byte-identical.
- Empty / no-LICENSED corpus → empty bundle (`bundleType` still present), exit 0.
- No-credential-pair claim → empty `builderDependencies` + `independenceWitnessed: false`.
- CLI smoke: `export-attestation <fixture> --out` exits 0 and the file re-parses as the bundle.

Per-package gate: `uv run pytest -q` + `uv run ruff check src tests`.

## 8. Exports & wiring (localized / append-only per coordination rules)

- `src/polymer_claims/__init__.py`: add `build_attestation_bundle`, `resolve_contract_index`,
  `AttestationBundle` (+ the key DTOs) to imports and `__all__` — appended, not reordered.
- `src/polymer_claims/cli.py`: append an `export-attestation` subparser (`corpus` positional,
  `--out` optional) + `_cmd_export_attestation`, mirroring `export-topology`. Append-only.
- Both `cli.py` and `__init__.py` are shared with the arc-3 sibling — keep additions localized and
  expect a small merge.

## 9. Out of scope (YAGNI — later slices)

Signing, DSSE envelope, Sigstore/cosign, Rekor transparency log, a `[sigstore]` extra; WES / TRS /
Workflow-Run RO-Crate; FAIR Signposting; Refget SeqCol. Slice 1 is the pure, content-addressed JSON
shape that any of those can later wrap or sign.

**Tracked follow-ups (not slice-1 deliverables):**
- **Publish the build-type / security-model doc** at `https://polymerclaims.org/recompute-gate/v1`
  (the URI is emitted as an opaque stable id in slice 1; the human-readable doc describing the
  recompute-gate build type + independence security model is published later).
- **Direct-verifier export mode** (`--format ndjson` / one-Statement-per-file, then DSSE) so a standard
  in-toto/SLSA verifier can ingest individual Statements without the Polymer bundle envelope.
