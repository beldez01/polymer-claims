# Real-Data Kernel Parity Gate (`verify-kernel --real`) — Design Spec

**Status:** Design / approved for planning. v0.2 (audit-revised)
**Date:** 2026-06-25
**Author:** Z. Belden (brainstormed with Claude)
**Roadmap:** H0.1b in `docs/superpowers/2026-06-23-remaining-roadmap.md` — the residual split out of
H0.1. H0.1 (`verify-kernel`, synthetic) proves the gate **pipeline** reproduces offline; H0.1b proves
the real `@2` **headline numbers** reproduce from pinned inputs. On the confirmed Path-α (wedge-first)
critical path: a wedge that cites real TCGA-LAML `@2` numbers depends on this.

> **One line.** Make the real `se:tcga_laml_idh@2` proof a **content-address-parity kernel check**
> (`verify-kernel --real`): supply (or, opt-in, fetch) the three pinned external inputs, rebuild the
> contract through the **de-hardcoded** builder, assert the rebuilt content-addresses match
> **committed reference pins captured from the previously trusted `@2` run**, run the **real** n-DMP
> gate, and require `LICENSED @ REPRODUCED`. It proves *the pinned real-data computation reproduces*
> — **not** that the data is real. No TCGA bytes enter git; only the pins do.

---

## 0. Problem & context

H0.1 closed offline reproducibility for the *synthetic* pipeline. The **real** `@2` proof
(`se:tcga_laml_idh@2`, 2026-06-18 source swap: cBioPortal `laml_tcga_pub` IDH genotyping + a local
Xena `TCGA-LAML.methylation450` matrix) still reproduces only in Z's working tree, because
`data/tcga_laml/build_contract_xena.py` and `run_gate.py` are **gitignored, hardcode absolute paths**
(`REPO`, the external `XENA` matrix path), and depend on local-only inputs. From a fresh checkout the
de Bruijn kernel question — *"given content-addressed code + data + environment, does re-running
produce the licensing output?"* (`foundations/epistemology.md` §8) — is **ill-defined for the real
proof**: one input (the ~633 MB Xena matrix) is an un-pinned external file at a hardcoded path.

H0.1b's job is to **extend content-addressing to the real inputs** so that kernel question becomes
answerable from a clean checkout, with a strict parity assertion as the check.

### The de Bruijn boundary (what this does and does not prove)

Per `foundations/epistemology.md` §8: *"a reproducible build of fabricated data is still perfectly
reproducible; the kernel verifies the result follows from the pinned computation, never that the data
is real."* Therefore:

- **In scope (the reproducibility floor for the real numbers):** the LICENSED verdict + its content
  addresses re-derive deterministically from the pinned inputs.
- **Out of scope (a different layer):** data veracity / independence on a second cohort — that is
  roadmap **H1.A2**. `--real` must state this boundary bluntly in CLI output and the runbook.

The trusted kernel does not grow (the §8 invariant): the build/gate logic is **untrusted
scaffolding** that produces inputs the **existing** gate re-checks; H0.1b adds pinning + a parity
assertion, never trusted decision logic.

## 1. Hard constraints (load-bearing)

- **No TCGA-derived bytes in git.** All three external inputs (Xena matrix; cBioPortal **mutations**
  file; cBioPortal **sample-list** API response) stay out of the repo. Only the **pins** (checksums,
  URLs/endpoint, the mutations commit, expected content-addresses) are committed. (Decision: "keep
  gitignored, document fetch" — all inputs.)
- **Fetch is opt-in.** Default behavior resolves inputs from a **local path or cache only**. Network
  retrieval requires an explicit `--fetch` flag. Rationale: a 633 MB governed artifact must not be
  fetched by surprise; network-by-default is wrong for CI, user surprise, and data-use clarity.
- **No self-fulfilling parity.** The reference pins are **bootstrapped from the previously trusted
  `@2` artifact** (the existing local contract / old scripts), committed, and only then must the new
  tracked builder reproduce them. Builder and pins never originate in the same pass — this proves
  **continuity with the earned proof**, not mere internal determinism.
- **Existing `verify-kernel` (synthetic) unchanged.** Absent `--real`, behavior is byte-identical.
- **CI cannot run the full real proof** (633 MB, network, governance). The real parity run is
  opt-in/manual; CI guards everything that does not need the big matrix.

## 2. Decisions settled in brainstorming (2026-06-25)

1. **Deliverable shape:** a `--real` mode on the existing `verify-kernel` CLI command, acting as a
   strict content-address-parity gate. Mirrors the synthetic command; boundary stated in-tool.
2. **Parity coverage:** pin the **full-content fixity** (covers beta values), not only dimnames /
   labels / counts (§4). This was the decisive correction — `dimnames_hash` proves rows/cols and
   `group_digest` proves labels, but neither proves the betas.
3. **Input acquisition:** local path → cache → (only with `--fetch`) pinned source; SHA-256 verified
   before use. **Three** pinned inputs, not two (audit #1): the Xena matrix, the cBioPortal
   **mutations** file (datahub commit-addressed), and the cBioPortal **sample list** (a cBioPortal
   **API** response, pinned separately by endpoint + sha — not covered by the mutations commit).
4. **Data governance:** neither input committed; pins + a documented fetch recipe instead.
5. **Module split:** a parameterized builder (`ingest/tcga_xena.py`) separate from the proof runner
   (`real_kernel_proof.py`); pins as a package data file loaded via `importlib.resources`.

## 3. Architecture & components

Mirrors `kernel_proof.py`: build a contract into a **temp contract root** (`using_contract_root` —
nothing written to the source tree), run the **real, existing** n-DMP gate, return a result.

- **`src/polymer_claims/ingest/tcga_xena.py`** (new, tracked) —
  `build_real_contract(root: Path, xena_file: Path, cbioportal_dir: Path) -> RealBuildResult`.
  The **de-hardcoded** port of `data/tcga_laml/build_contract_xena.py`: all absolute paths removed
  (writes into `root`; Xena + cBioPortal are arguments). Streams the matrix (no full load), applies
  the active cBioPortal IDH-calling + drop-not-default-WT universe logic, writes
  `tcga_laml_idh.json` + `.betas.tsv` into `root`, returns the manifest, `group_digest`, and counts.
  Preserves the existing hard self-checks (known IDH-mut controls present; `IDH_mut` count in
  `[20,50]`; universe/drop accounting). The legacy `USE_MAF` path is **not** ported (it produced the
  superseded `@1`).
- **`src/polymer_claims/real_kernel_proof.py`** (new, tracked) —
  `run_real_kernel_proof(xena_file, cbioportal_dir, *, pins) -> RealKernelProofResult`. Builds into a
  temp root, computes content-addresses via `load_contract`, **asserts parity vs `pins`**, runs the
  gate (reusing `n_dmps_claim`, `dmp_indicators`, `count_enrichment_evalue`, `NDmpTTestAdapter`,
  `NDmpOlsCoefAdapter`, `ndmp_independent_registry`, `run_cycle` — all already exist), and returns
  status / tier / the observed content-addresses / `n_dmps` / `e_value`. Surfaces the materialization
  content-address from `c.licensing.satisfactions[0].materialization` (as `run_gate.py` reads today).
- **`src/polymer_claims/ingest/real_kernel_pins.json`** (new, tracked — the only new committed data) —
  loaded via `importlib.resources`. Holds the pins (§4).
- **`src/polymer_claims/ingest/_pinned.py`** (new helper module) —
  `resolve_pinned_file(filename, *, local, url, sha256, cache_dir, allow_fetch) -> Path`, **per
  file**. The Xena matrix is one call; the cBioPortal mutations file and the API-sourced sample list
  are one call each (each pinned by its own sha — and the sample list by its API endpoint, §4). The
  resolver semantics (audit #6) are explicit:
  - **`local` accepts a file OR a directory:** if `local` is a file, use it directly; if a directory,
    use `local/filename`. (Resolves the file-vs-dir ambiguity for both flags.)
  - **CLI flags:** `--xena PATH` is the **matrix file** (or a dir containing
    `TCGA-LAML.methylation450.tsv.gz`); `--cbioportal PATH` is the **directory** holding
    `data_mutations.txt` and `sequenced_samples.json`. Builder signature mirrors this:
    `build_real_contract(root, xena_file, cbioportal_dir)`.
  - **Resolution order:** the `local` file/dir if present → `cache_dir/filename` if present → (only
    when `allow_fetch`) download from `url`/`api_endpoint` into `cache_dir`.
  - **Default cache:** `cache_dir` defaults to `$XDG_CACHE_HOME/polymer-claims/tcga_laml/` (fallback
    `~/.cache/polymer-claims/tcga_laml/`); `--cache-dir` overrides.
  - **Download is atomic:** write to `cache_dir/<filename>.part-<n>`, verify SHA-256, then
    `os.replace` to the final name only on a match — so a cached file is always a verified file.
  - **SHA-256 is always verified** on the resolved path (local, cached, or freshly fetched); mismatch
    aborts before any build.
  - **git-LFS / HTML pointer guard:** before hashing, if a "blob" file's leading bytes are a Git-LFS
    pointer (`version https://git-lfs…`) or an HTML error page, abort with *"got a pointer/HTML page,
    not the data blob — fetch the raw file"* rather than a bare checksum-mismatch.
- **`cli.py`** — extend the `verify-kernel` parser: `--real`, `--xena PATH`, `--cbioportal PATH`,
  `--cache-dir PATH`, `--fetch`. No `--real` → existing synthetic path, unchanged.
- **Deprecation (no deletion):** the gitignored `data/tcga_laml/build_contract_xena.py` /
  `run_gate.py` are superseded by the tracked modules; left in place, marked deprecated with a
  pointer to `verify-kernel --real`. Minimal churn; they remain Z's local working scripts.

## 4. The reference pins (`real_kernel_pins.json`)

Captured once from the **previously trusted `@2`** artifact (§1, §6), committed, then matched by the
new builder.

```jsonc
{
  "contract_uid": "tcga_laml_idh@2",
  "inputs": {
    "xena":          { "filename": "TCGA-LAML.methylation450.tsv.gz", "sha256": "<pin>", "bytes": <int>, "url": "<xena url>" },
    // cBioPortal MUTATIONS: a commit-addressed datahub file (commit pins the bytes).
    "cbio_mutations":   { "commit": "86690e1ed9752b1dcd50b5657f5f05eafa4b6b78",
                          "url": "<datahub raw url @ commit>/data_mutations.txt",
                          "filename": "data_mutations.txt", "sha256": "<sha256>" },
    // cBioPortal SAMPLE LIST: an API response, NOT a datahub-commit file (see SOURCE.txt
    // `sequenced_universe`). Pinned as its own input by endpoint + sha256 of the response bytes;
    // it is NOT covered by the mutations commit.
    "cbio_sequenced":   { "api_endpoint": "https://www.cbioportal.org/api/sample-lists/laml_tcga_pub_sequenced/sample-ids",
                          "filename": "sequenced_samples.json", "sha256": "<sha256>" }
  },
  "expected": {
    "contract_uid":      "tcga_laml_idh@2",                            // strict: version identity (see §4.3)
    "contract_checksum": "<sha256(manifest_bytes + betas_bytes)>",     // PRIMARY GATE — byte-level, required (see §4.1)
    "canonical_checksum":"<canonical_sha256(logical contract)>",       // DIAGNOSTIC logical checksum, not a gate (see §4.1)
    "dimnames_hash":     "<canonical_sha256(feature_ids|sample_ids)>", // diagnostic: rows/cols
    "group_digest":      "<sha256 of label vector>",                   // diagnostic: labels
    "idh_mut_n": <int>, "wt_n": <int>, "n_probes": <int>,              // diagnostic: shape
    "n_dmps": <int>,                                                   // strict (exact int)
    "e_value": "inf",                                                  // see §4.2 (inf rule | finite repr)
    "profile_hash": "<pin>", "semantic_run_id": "<pin>",               // gate materialization (see §4.4)
    "status": "licensed", "independence_tier": "reproduced"            // serialized enum VALUES (lowercase)
  }
}
```

**Enum casing (audit #8).** `status` / `independence_tier` pins store the **serialized enum values**
(`Status.LICENSED.value == "licensed"`, `IndependenceTier.REPRODUCED.value == "reproduced"` —
`grammar/.../status.py`, `licensing.py`). Comparison is by enum identity in code
(`c.status is Status.LICENSED`, `tier is IndependenceTier.REPRODUCED`); the lowercase strings in the
pins file are the serialized values, not the uppercase display labels used in CLI banner text.

### 4.1 Byte-level vs. canonical parity (audit #2)

`contract_checksum = sha256(manifest_bytes + betas_bytes)` (`contracts/__init__.py:103-104`) is the
full-content DRS fixity: any changed beta byte flips it, which `dimnames_hash` (rows/cols) and
`group_digest` (labels) cannot detect. But it is **byte-level** — it requires the new builder to
reproduce the *exact bytes* of the trusted `@2` artifact:

- **Manifest JSON:** identical `json.dumps` serialization — same dict **insertion order** (`uid`,
  `dim`, `assays`, `col_data`, `row_data`, `metadata` and every nested key), default separators, **no
  `sort_keys`**, no trailing newline. The de-hardcoded port MUST construct the manifest dict in the
  same key/row/column order as `build_contract_xena.py` and emit the identical `uid` string.
- **Betas TSV:** the builder writes beta values **verbatim as the source strings** (`vals =
  [parts[i] ...]`) — **no re-rounding/reformatting** — so byte-stability holds given the same input
  matrix and the same column-selection order. The port must preserve that (copy strings, never parse
  → reformat floats).

Because byte-parity is brittle to incidental serialization changes, the pins also carry a
**`canonical_checksum`** — a **diagnostic logical checksum, not a gate**. It is `canonical_sha256`
(`polymer_claims._hashing`, already exists) over this **exact** normal form:

```python
canonical_sha256({
    "uid": manifest["uid"],                                  # "tcga_laml_idh@2"
    "dim": [n_probes, n_samples],
    "features": sorted(feature_ids),                         # probe ids, ascending
    "samples": sorted([[sample_id, label] for ...],          # ascending by sample_id
                      key=lambda r: r[0]),                    # label = Sample_Group (WT|IDH_mut)
    "betas": { sample_id: [round(float(b), 6) for b in column] },  # keyed by sample_id, probe order = sorted features
})
```

Fixed schema decisions (so this is not left to implementer taste): **6 decimal places**; betas keyed
by `sample_id` with each value list in **sorted-feature order**; clinical metadata, `group_digest`,
and original row/column *ordering* are **excluded** (the byte-level `contract_checksum` already
covers serialization and ordering — this normal form deliberately abstracts them away). **Missing
betas:** the `@2` build drops any probe with an NA across selected samples, so the matrix is dense and
no sentinel is needed; if a NaN is ever encountered the builder aborts (it cannot occur in a
parity-passing build). The byte-level `contract_checksum` is the **required** gate; `canonical_checksum`
is computed only to label a `contract_checksum` failure as *"logical content reproduced but bytes
differ → builder not byte-faithful"* (a builder bug) vs. *"logical content itself diverged"* (a data
bug). It never licenses on its own.

The localized hashes (`dimnames_hash`, `group_digest`, counts) are retained for "which dimension
diverged" diagnostics, not as the primary check.

### 4.2 `e_value` comparison — the inf rule (audit #4)

The real genome-wide n-DMP enrichment drives `count_enrichment_evalue` to **+∞** (documented for the
`@2` proof; `:.3e` prints `inf`). Relative tolerance is meaningless for infinity, so:

- Pin is the JSON **string `"inf"`** when the proof is infinite; comparison succeeds iff
  `math.isinf(observed) and observed > 0`.
- If a (future) finite e-value is pinned, the pin is the exact canonical `repr(float)` and comparison
  accepts exact match or relative tolerance `1e-12`.

The loader/parser maps `"inf"` ↔ `math.inf` explicitly; a plain `float("inf")` round-trip is fine but
the rule is stated so neither side relies on `repr(inf)` formatting.

### 4.3 Version identity assertion (audit #3)

`load_contract` strips the version and reads `tcga_laml_idh.json` **by stem**
(`contracts/__init__.py:84`), so a wrong-version manifest would still load. The builder we port
(`build_contract_xena.py`) already emits `uid: "tcga_laml_idh@2"` — note this is **not** the legacy
`ingest/transform.py:build_contract`, which hardcodes `@1` and is *not* ported. To make version
identity explicit rather than incidental, the gate asserts **`ref.contract_uid == "tcga_laml_idh@2"`**
as a parity check, and the builder is required to emit `@2`.

### 4.4 Claim-construction pins (audit #5)

`semantic_run_id = canonical_sha256({tool: node.impl, param_signature: node.params,
input_signature: [dimnames_hash], profile_hash})` (`materialization.py:52`). It therefore depends on
**exact claim construction**, not just the data — a builder could pass `contract_checksum` yet fail
the materialization pin opaquely. The spec fixes the canonical claim construction (matching today's
`run_gate.py`), and it is part of the parity contract:

| Field | Fixed value |
|---|---|
| claim id | `tcga-laml-ndmp` |
| `ref` | `se:tcga_laml_idh@2` |
| `group_col` / `level_a` / `level_b` | `Sample_Group` / `WT` / `IDH_mut` |
| `alpha` | `0.05` |
| `k` (null floor) | `ceil(0.05 * n_probes)` |
| `oracle_ref` | `profile_oracle_id(CANONICAL_HM450_V1)` |
| adapters | `(NDmpTTestAdapter(), NDmpOlsCoefAdapter())`, `ndmp_independent_registry()` |
| oracles | `profile_oracle_registry((CANONICAL_HM450_V1, "recomputable_public"))` |

Probe **ordering** enters `semantic_run_id` **directly through `param_signature`**: `n_dmps_claim`
with `probes=None` expands to `_all_probe_ids(ref)` and stores `("probes", ",".join(probes))` as a
node param (`methyl_ndmp.py:225-234`), and `semantic_run_id` hashes `node.params`. So the pin requires
the **exact comma-joined probe-id string** in the order `_all_probe_ids("se:tcga_laml_idh@2")` yields
— not merely the probe *set*. The claim must be built with **`probes=None`** (never an explicit list)
so this expansion is the single source of probe order. `_all_probe_ids` order derives from the
contract's `row_data`, so the contract pin fixes it; the contract pin + `probes=None` + this fixed
claim construction together determine `profile_hash` and `semantic_run_id`. (`k = ceil(0.05 *
n_probes)` is also a param and is fixed by `n_probes`.)

## 5. Data flow

```
verify-kernel --real [--xena PATH] [--cbioportal PATH] [--cache-dir PATH] [--fetch]
  │
  ├─ load pins (importlib.resources)
  ├─ resolve+verify Xena matrix              (local→cache→[--fetch]→url; sha256 == pin, else ABORT)
  ├─ resolve+verify cBioPortal mutations file (local→cache→[--fetch]→datahub url@commit; sha256 == pin)
  ├─ resolve+verify cBioPortal sample-list response (local→cache→[--fetch]→API endpoint; sha256 == pin)
  │
  ├─ build_real_contract(temp_root, xena, cbio)      → manifest, group_digest, counts  (uid == @2)
  ├─ load_contract("se:tcga_laml_idh@2")             → contract_uid, dimnames_hash,
  │                                                     contract_checksum, canonical_checksum
  │
  ├─ PARITY ASSERT (vs pins.expected):
  │     contract_uid == "tcga_laml_idh@2"                      (§4.3 version identity)
  │     contract_checksum   (PRIMARY, byte-level)  ── mismatch → if canonical_checksum matches:
  │                                                     "serialization differs, not byte-faithful";
  │                                                     else: "betas/manifest content diverged" (§4.1)
  │     dimnames_hash, group_digest, idh_mut_n/wt_n/n_probes  (localized diagnostics)
  │
  ├─ run_cycle(... real n-DMP gate, fixed claim construction §4.4 ...)
  │                                                   → status, tier, materialization, n_dmps, e_value
  ├─ PARITY ASSERT: n_dmps (exact), e_value (inf rule §4.2), profile_hash, semantic_run_id
  └─ REQUIRE: status is Status.LICENSED  AND  tier is IndependenceTier.REPRODUCED
        → print "LICENSED @ REPRODUCED" + blunt boundary note ; exit 0
        → any mismatch: name the failing pin (expected vs observed) ; exit 1
```

## 6. Bootstrap: capturing pins v1 (the no-self-fulfilling-parity step)

A discrete, documented, **one-time** operation, run by Z in the working tree that holds the trusted
`@2` artifact — separate from and prior to the new builder:

1. From the **existing trusted `@2` contract** (already built by the old local scripts / present in
   the local contracts dir), record `contract_uid` (`tcga_laml_idh@2`), `contract_checksum`
   (byte-level), `canonical_checksum` (logical normal form, §4.1), `dimnames_hash`, the counts, and
   `group_digest` from manifest metadata.
2. Run the trusted gate once; record `n_dmps`, `e_value` (as `"inf"` or finite canonical repr, §4.2),
   `profile_hash`, `semantic_run_id`, and the serialized `status` / `independence_tier` values.
3. Record the input pins **per the §4 split**: Xena matrix SHA-256 + bytes + URL; cBioPortal
   **mutations** file SHA-256 + datahub commit + commit-addressed URL; cBioPortal **sample list**
   SHA-256 + its API endpoint (a *separate* input, not under the mutations commit).
4. Write these into `real_kernel_pins.json` and **commit**.
5. *Then* run `verify-kernel --real` with the **new** builder; it must reproduce every pin. If the
   new builder cannot match the trusted pins, the builder is wrong (not the pins) — fix the builder.

This guarantees the committed pins descend from the earned proof, and the new builder is validated
*against* that descent rather than minting its own ground truth.

## 7. Error handling

Each failure mode is distinct, actionable, and exits nonzero:

- **Input missing and no `--fetch`** (or fetch fails / offline) → `supply --xena <path> (download from
  <pinned url>, sha256 <pin>); pass --fetch to allow network retrieval`.
- **Checksum mismatch** → name the input, expected vs observed sha; refuse to build on wrong bytes.
  The §3 git-LFS/HTML-pointer guard fires first when the bytes are a pointer/error page.
- **Version-identity mismatch** (`contract_uid != "tcga_laml_idh@2"`, §4.3) → explicit, before content
  parity, so a stale-version build is not misreported as a content divergence.
- **Parity mismatch** → name the field (`contract_checksum` / `canonical_checksum` / `dimnames_hash` /
  `group_digest` / counts / `n_dmps` / `e_value` / `profile_hash` / `semantic_run_id`), expected vs
  observed. The §4.1 byte-vs-canonical branch distinguishes a **builder serialization bug** ("logical
  content reproduced but bytes differ") from a **data divergence** ("content itself diverged"). This
  is the kernel reporting "re-running did **not** reproduce."
- **Gate not LICENSED / tier ≠ REPRODUCED** → print status + FDR ledger summary.
- **numpy missing** → reuse the existing `[calibrate]` extra message from `_cmd_verify_kernel`.
- Builder self-checks (IDH-mut controls present; count band; universe/drop accounting) abort with
  their existing messages rather than writing a wrong contract.

## 8. Testing & the CI boundary

The 633 MB matrix **cannot run in CI** — stated honestly (same boundary the real proof already had).

- **CI-guarded (no big matrix):**
  - `real_kernel_pins.json` loads via `importlib.resources` and matches its schema.
  - `_resolve_pinned_input` checksum logic: tiny fixture file with a known sha — pass case and
    tampered-byte refusal; `--fetch` absent → no network attempted.
  - CLI `--real` arg parsing; clean, actionable error when inputs are absent and `--fetch` not given.
  - **Builder determinism:** `build_real_contract` over a **tiny synthetic Xena-shaped TSV +
    synthetic cBioPortal stub** runs twice → identical `contract_checksum` (proves the builder is
    deterministic and the parity mechanics fire). This fixture is **separate from the real pins** and
    asserts mechanics, not the real numbers.
  - **IDH-grouping unit tests (audit #7 — the biologically load-bearing logic):** direct tests on the
    builder's grouping internals, independent of the big matrix:
    - **hotspot parsing:** `_residue("p.R132H") == "R132"`; `(IDH1, R132)`, `(IDH2, R140)`,
      `(IDH2, R172)` are called IDH-mut; a non-hotspot IDH variant and a non-IDH gene are not.
    - **universe = intersection(beta cases, sequenced cases):** a beta case absent from the sample
      list is **dropped**, never defaulted to WT (the `@1` dilution bug); a genotyped non-hotspot case
      is `WT`.
    - **drop accounting:** `len(universe) + len(dropped_ungenotyped) == len(beta_cases)`; the
      known-IDH-mut control set is present; `IDH_mut` count lands in `[20,50]` on the stub.
    - **separate-input wiring:** mutations file and API sample-list resolve independently (§4) and the
      sample list is *not* expected under the mutations commit.
  - Parity-failure messaging: deliberately perturbed expected-pins yield the correct named-field error
    and nonzero exit — including the §4.1 "byte-differs-but-canonical-matches" branch and the §4.2 inf
    vs finite branch.
- **Manual / opt-in (not CI):** the actual real parity run, documented in the runbook with the Xena
  URL + sha and the cBioPortal commit + shas. (A future external artifact cache could promote this to
  CI; out of scope here.)
- **Runbook update:** `docs/superpowers/2026-06-23-kernel-proof-runbook.md` gains the
  `verify-kernel --real` recipe (with `--fetch` semantics, pins, the blunt boundary line) and retires
  the hardcoded-path instructions.

The `chr/pos`-absent caveat (sex-chrom QC skipped in the `@2` build) carries forward untouched: parity
compares against pins captured from the same build, so it is preserved by construction and re-noted in
the runbook.

## 9. Explicitly NOT in scope (YAGNI / boundary)

- **No signing** (that's H1.A1, already shipped separately).
- **No second cohort / data-veracity / independence claim** (H1.A2). `--real` proves reproduction of
  the pinned computation only.
- **No committing of TCGA-derived data.** Pins only.
- **No `@1` MAF path** port (superseded).
- **No external artifact cache / CI big-matrix run** (possible future; not now).

## 10. Acceptance criteria

1. `verify-kernel` with no `--real` is byte-identical to today.
2. `verify-kernel --real` with the correct local inputs prints `LICENSED @ REPRODUCED`, exits 0, and
   every pin in `real_kernel_pins.json` matches — including `contract_uid == "tcga_laml_idh@2"` (§4.3),
   the byte-level `contract_checksum` (§4.1), the `"inf"` e-value (§4.2), and `profile_hash` /
   `semantic_run_id` under the fixed claim construction (§4.4).
3. Tampering with any input (wrong sha) or any pin produces a named, actionable error and exit 1; a
   serialization-only divergence is reported distinctly from a content divergence (§4.1), and a
   pointer/HTML download is reported distinctly from a checksum mismatch (§3).
4. No network is touched without `--fetch`; the three pinned inputs resolve via the §3 order with
   atomic, checksum-verified caching.
5. `real_kernel_pins.json` v1 is demonstrably captured from the trusted `@2` artifact (§6), and the
   new tracked builder reproduces it (continuity, not self-fulfilling parity).
6. CI suite (§8) passes with no real TCGA bytes present, including the IDH-grouping unit tests.
7. The runbook documents the recipe (`--fetch` semantics, the three inputs) and the blunt boundary
   line.
