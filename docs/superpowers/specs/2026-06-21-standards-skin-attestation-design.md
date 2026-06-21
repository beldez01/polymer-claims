# Standards Skin — slice 1: in-toto/SLSA attestation export (design)

> North-Star arc 2 (the standards skin / adoption moat), first slice.
> Worktree `/Users/zbb2/Desktop/polymer-claims-arc2`, branch `feat/standards-skin-attestation`.
> Strategy: north-star §4 (pan-integrator seams; in-toto/SLSA + Sigstore/Rekor ranked #3) and §6
> (sequencing: arc 2). Kickoff: `ARC2-KICKOFF.md`.

## 1. Goal & scope

Add a new umbrella command `export-attestation <corpus>` that turns every **LICENSED** claim in a
corpus into a deterministic, content-addressed **in-toto Statement v1** carrying a **SLSA Provenance
v1** predicate, plus standalone **GA4GH DRS object** docs for the datasets those claims were licensed
on.

The thesis: don't integrate the world's data/compute — integrate *trust over* it. Re-express the
content-address / apparatus / run model we already compute **as the standards that already exist**, so
a third party can verify a licensed run *without trusting our service*. Slice 1 produces a pure,
content-addressed JSON shape any third party could **later** sign; signing/Rekor is a separate slice.

**In scope:** the deterministic serializer + CLI command + new exports. Strictly additive — existing
behavior is byte-identical; nothing existing changes.

**Standards fidelity:** strict — a real in-toto Statement v1 envelope whose `predicate` matches SLSA
Provenance v1 (`buildDefinition` / `runDetails`), and GA4GH `DrsObject`-shaped dataset handles, such
that an off-the-shelf verifier accepts the shape.

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
one provenance per produced artifact). For a claim's datasets, reuse the existing "one representative
`Satisfaction` per distinct `dimnames_hash`" logic in `licensing.py` so REPLICATED claims contribute
one dependency per distinct cohort.

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
    externalParameters:
      claimId, pattern, licenseRoute, rivalSetClosure, criterion: "e-value/FDR (e-LOND)"
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
        annotations: { role: "apparatus", semanticRunId: <semanticRunId> }   # per-run id lives here
  runDetails:
    builder:
      id: "https://polymerclaims.org/recompute-gate/v1"   # the gate IS the build platform
      builderDependencies:                                 # the air-gap witnesses
        - name: <credential_id_1>, digest:{ sha256:<implementation_hash> }, annotations:{role:"adapter"}
        - name: <credential_id_2>, digest:{ sha256:<implementation_hash> }, annotations:{role:"adapter"}
    metadata: { invocationId: <representative semanticRunId> }   # lowest-dimnames_hash rep; NO clock
```

- **builder** = the independent credential pair from `independent_credential_pair(registry,
  satisfaction.credential_ids)`. The recompute gate is the SLSA "builder"; the two air-gapped adapters
  are its pinned `builderDependencies`. This is the faithful reading: the recomputation gate is the
  build platform, the two independent adapters are pinned dependencies that witnessed the air gap.
- If **no** independent pair is recorded (legacy / empty `credential_ids`): `builderDependencies: []`
  and an annotation `independenceWitnessed: false`. We never fabricate witnesses.
- All `sha256:`-prefixed content-addresses (`profileHash`, `dimnames_hash`, `implementation_hash`)
  are stripped to bare hex inside any `digest` map; the prefixed form may appear only in an opaque
  annotation if useful.
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
  attestations:        (Statement, ...)        # sorted by claim.id
  drsObjects:          (DrsObject, ...)         # sorted by id
  unresolvedDatasets:  (<dimnames_hash hex>, ...)   # best-effort transparency for non-bundled contracts
```

One CLI call → one bundle JSON containing both the attestations and their companion DRS objects.

## 5. Determinism, errors, edge cases

- **Determinism:** sorted `attestations` (by `claim.id`), sorted `drsObjects` (by `id`), sorted
  `resolvedDependencies` (by `name`), tuple collections, no clock/random. A test exports the same corpus
  twice and asserts byte-identical output.
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
`Builder`, `ResourceDescriptor`, `DigestSet`, `DrsObject`, `Checksum`, `AccessMethod`, `AttestationBundle`)
with pydantic `alias=` for camelCase and `_type` (python field `type_`, `alias="_type"`). Serialize via
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
- Structural conformance: required in-toto fields (`_type`, `subject`, `predicateType`, `predicate`)
  and required SLSA fields (`buildDefinition.buildType`, `runDetails.builder.id`) are present — asserted
  structurally, no new schema dependency.
- DRS object shape (`self_uri`, `checksums[].type == "sha-256"`, `access_methods[].access_url.url`).
- Unresolved-contract fallback: DRS object skipped, dependency digest falls back to `dimnames_hash`,
  id recorded in `unresolvedDatasets`, no crash.
- Determinism: two exports of the same corpus are byte-identical.
- Empty / no-LICENSED corpus → empty bundle, exit 0.
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
