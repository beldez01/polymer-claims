# Real-Data Kernel Parity Gate (`verify-kernel --real`) — Design Spec

**Status:** Design / approved for planning. v0.1
**Date:** 2026-06-25
**Author:** Z. Belden (brainstormed with Claude)
**Roadmap:** H0.1b in `docs/superpowers/2026-06-23-remaining-roadmap.md` — the residual split out of
H0.1. H0.1 (`verify-kernel`, synthetic) proves the gate **pipeline** reproduces offline; H0.1b proves
the real `@2` **headline numbers** reproduce from pinned inputs. On the confirmed Path-α (wedge-first)
critical path: a wedge that cites real TCGA-LAML `@2` numbers depends on this.

> **One line.** Make the real `se:tcga_laml_idh@2` proof a **content-address-parity kernel check**
> (`verify-kernel --real`): supply (or, opt-in, fetch) the two pinned external inputs, rebuild the
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

- **No TCGA-derived bytes in git.** Both external inputs (Xena matrix; cBioPortal genotyping bundle)
  stay out of the repo. Only the **pins** (checksums, URLs, the cBioPortal commit, expected
  content-addresses) are committed. (Decision: "keep gitignored, document fetch" — both inputs.)
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
3. **Input acquisition:** local path → cache → (only with `--fetch`) pinned URL; SHA-256 verified
   before use. Same resolution path used for both inputs.
4. **Data governance:** neither input committed; pins + a documented fetch recipe instead.
5. **Module split:** a parameterized builder (`ingest/tcga_xena.py`) separate from the proof runner
   (`real_kernel_proof.py`); pins as a package data file loaded via `importlib.resources`.

## 3. Architecture & components

Mirrors `kernel_proof.py`: build a contract into a **temp contract root** (`using_contract_root` —
nothing written to the source tree), run the **real, existing** n-DMP gate, return a result.

- **`src/polymer_claims/ingest/tcga_xena.py`** (new, tracked) —
  `build_real_contract(root: Path, xena_path: Path, cbioportal_dir: Path) -> RealBuildResult`.
  The **de-hardcoded** port of `data/tcga_laml/build_contract_xena.py`: all absolute paths removed
  (writes into `root`; Xena + cBioPortal are arguments). Streams the matrix (no full load), applies
  the active cBioPortal IDH-calling + drop-not-default-WT universe logic, writes
  `tcga_laml_idh.json` + `.betas.tsv` into `root`, returns the manifest, `group_digest`, and counts.
  Preserves the existing hard self-checks (known IDH-mut controls present; `IDH_mut` count in
  `[20,50]`; universe/drop accounting). The legacy `USE_MAF` path is **not** ported (it produced the
  superseded `@1`).
- **`src/polymer_claims/real_kernel_proof.py`** (new, tracked) —
  `run_real_kernel_proof(xena_path, cbioportal_dir, *, pins) -> RealKernelProofResult`. Builds into a
  temp root, computes content-addresses via `load_contract`, **asserts parity vs `pins`**, runs the
  gate (reusing `n_dmps_claim`, `dmp_indicators`, `count_enrichment_evalue`, `NDmpTTestAdapter`,
  `NDmpOlsCoefAdapter`, `ndmp_independent_registry`, `run_cycle` — all already exist), and returns
  status / tier / the observed content-addresses / `n_dmps` / `e_value`. Surfaces the materialization
  content-address from `c.licensing.satisfactions[0].materialization` (as `run_gate.py` reads today).
- **`src/polymer_claims/ingest/real_kernel_pins.json`** (new, tracked — the only new committed data) —
  loaded via `importlib.resources`. Holds the pins (§4).
- **`src/polymer_claims/ingest/_pinned.py`** (new helper module) —
  `resolve_pinned_file(local_path, url, sha256, *, cache_dir, allow_fetch) -> Path`: local path →
  cache → (if `allow_fetch`) fetch URL into cache; then SHA-256 verify, refusing to proceed on
  mismatch. **Per-file.** The Xena matrix is one call; the cBioPortal bundle is one call per pinned
  file (`data_mutations.txt`, `sequenced_samples.json`), each verified against its own sha, all
  resolved under the supplied `--cbioportal` dir / cache.
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
    "xena":       { "filename": "TCGA-LAML.methylation450.tsv.gz", "sha256": "<pin>", "bytes": <int>, "url": "<xena url>" },
    "cbioportal": { "commit": "86690e1ed9752b1dcd50b5657f5f05eafa4b6b78",
                    "url": "<datahub raw url>",
                    "files": { "data_mutations.txt": "<sha256>", "sequenced_samples.json": "<sha256>" } }
  },
  "expected": {
    "contract_checksum": "<sha256(manifest_bytes + betas_bytes)>",   // PRIMARY GATE — covers beta values
    "dimnames_hash":     "<canonical_sha256(feature_ids|sample_ids)>", // diagnostic: rows/cols
    "group_digest":      "<sha256 of label vector>",                   // diagnostic: labels
    "idh_mut_n": <int>, "wt_n": <int>, "n_probes": <int>,              // diagnostic: shape
    "n_dmps": <int>,                                                   // strict (exact)
    "e_value": "<canonical repr>",                                     // strict: exact repr, rel-tol 1e-12 fallback
    "profile_hash": "<pin>", "semantic_run_id": "<pin>",               // gate materialization
    "status": "LICENSED", "independence_tier": "REPRODUCED"
  }
}
```

**Why `contract_checksum` is the primary gate.** Per `contracts/__init__.py:103-104`,
`SEContractRef.checksums[0].checksum = sha256(manifest_bytes + betas_bytes)` — the full-content DRS
fixity. Any changed beta byte flips it, which `dimnames_hash` (rows/cols only) and `group_digest`
(labels only) cannot detect. The localized hashes are retained for "which dimension diverged" error
messages, not as the primary check.

**`e_value` formatting.** The betting/`count_enrichment_evalue` e-value is deterministic
(seed-averaged, past-only GRAPA). Pin the exact canonical `repr(float)`; on comparison, accept exact
match or relative tolerance `1e-12` to absorb any cross-platform float-formatting drift. (Decision:
"pin n_dmps and the final e-value with a stated tolerance or exact canonical formatting" — both.)

## 5. Data flow

```
verify-kernel --real [--xena PATH] [--cbioportal PATH] [--cache-dir PATH] [--fetch]
  │
  ├─ load pins (importlib.resources)
  ├─ resolve+verify Xena matrix       (local→cache→[--fetch]→url; sha256 == pin, else ABORT)
  ├─ resolve+verify cBioPortal bundle  (local→cache→[--fetch]→url; sha256 == pin, commit pinned)
  │
  ├─ build_real_contract(temp_root, xena, cbio)      → manifest, group_digest, counts
  ├─ load_contract("se:tcga_laml_idh@2")             → dimnames_hash, contract_checksum
  │
  ├─ PARITY ASSERT (vs pins.expected):
  │     contract_checksum   (PRIMARY)  ── mismatch → exit 1, "betas/manifest diverged"
  │     dimnames_hash, group_digest, idh_mut_n/wt_n/n_probes  (localized diagnostics)
  │
  ├─ run_cycle(... real n-DMP gate ...)              → status, tier, materialization, n_dmps, e_value
  ├─ PARITY ASSERT: n_dmps (exact), e_value (repr/rel-tol), profile_hash, semantic_run_id
  └─ REQUIRE: status == LICENSED  AND  tier == REPRODUCED
        → print "LICENSED @ REPRODUCED" + blunt boundary note ; exit 0
        → any mismatch: name the failing pin (expected vs observed) ; exit 1
```

## 6. Bootstrap: capturing pins v1 (the no-self-fulfilling-parity step)

A discrete, documented, **one-time** operation, run by Z in the working tree that holds the trusted
`@2` artifact — separate from and prior to the new builder:

1. From the **existing trusted `@2` contract** (already built by the old local scripts / present in
   the local contracts dir), compute `contract_checksum`, `dimnames_hash`, the counts, and read
   `group_digest` from its manifest metadata.
2. Run the trusted gate once; record `n_dmps`, `e_value`, `profile_hash`, `semantic_run_id`,
   `status`, `independence_tier`.
3. Compute SHA-256 of the Xena matrix and the cBioPortal files; record the cBioPortal commit + URLs.
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
- **Parity mismatch** → name the field (`contract_checksum` / `dimnames_hash` / `group_digest` /
  counts / `n_dmps` / `e_value` / `profile_hash` / `semantic_run_id`), expected vs observed. This is
  the kernel reporting "re-running did **not** reproduce."
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
  - Parity-failure messaging: a deliberately perturbed expected-pin yields the correct named-field
    error and nonzero exit.
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
   every pin in `real_kernel_pins.json` matches.
3. Tampering with any input (wrong sha) or any pin produces a named, actionable error and exit 1.
4. No network is touched without `--fetch`.
5. `real_kernel_pins.json` v1 is demonstrably captured from the trusted `@2` artifact (§6), and the
   new tracked builder reproduces it.
6. CI suite (§8) passes with no real TCGA bytes present.
7. The runbook documents the recipe and the blunt boundary line.
