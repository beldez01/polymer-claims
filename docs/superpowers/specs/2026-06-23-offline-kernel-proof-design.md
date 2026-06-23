# Offline-Reproducible Kernel Proof — Design Spec

**Status:** Design / approved for planning. v0.1
**Date:** 2026-06-23
**Author:** Z. Belden (brainstormed with Claude)
**Roadmap:** H0.1 in `docs/superpowers/2026-06-23-remaining-roadmap.md` — the foundation of the
confirmed Path-α (wedge-first) critical path. Closes the one reproducibility gap the 2026-06-23
spot-verification found.

> **One line.** Guarantee the n-DMP gate **pipeline** re-runs offline, deterministically, with
> **zero real TCGA bytes in git** — via a fully synthetic, realistic-shaped contract fixture run
> through the *real* gate — and document the *real* genome-wide `@2` proof as a local-only/runbook
> path. Fresh-checkout reproduction of the real numbers is explicitly **deferred to roadmap H0.1b**,
> not delivered here.

---

## 0. Problem & context

The build-path "kernel proof" (one real claim, real public data, real independence check, honest
`q`, shareable certificate) was achieved on TCGA-LAML HM450 (n-DMP, IDH-mut vs WT). But the
2026-06-23 spot-verification found it is **not reproducible offline**: `data/tcga_laml/` holds only
metadata/scripts/logs, the real betas + built SE-Contract are **deliberately gitignored** ("nothing
real is committed"), and `ingest tcga-laml` fetches from the live GDC API (`api.gdc.cancer.gov`,
404 in a network-isolated env). The cache-first `fetch_file` already supports offline runs *when the
data is present* — but it isn't bundled, by design.

**Decisions settled in brainstorming (2026-06-23):**
1. **Reproducibility target:** a committed **small synthetic fixture** that makes the pipeline re-run
   offline (CI-grade) **+** a hardened retrieval recipe for the real numbers. (Not real-data
   bundling; not docs-only.)
2. **Fixture nature:** **fully synthetic, realistic-shaped** — no real TCGA bytes in git, consistent
   with the existing "nothing real is committed" principle and TCGA data-use terms. Proves *pipeline
   integrity*, not the real biology (that is the retrieval recipe's job).
3. **Scope:** committed gate **test** (CI/offline guard) **+** a **CLI** affordance to run the proof
   offline **+** a **retrieval runbook** with a friendlier offline error.

## 1. Hard constraints (load-bearing)

- **Nothing real committed.** The fixture is fully synthetic. The real-data path stays manifest +
  script only (the committed `tcga_laml_manifest.json` is the pinned recipe; the data it fetches
  remains gitignored).
- **Reuse the real gate, do not fork it.** The fixture runs through the *existing*
  `build_contract`, `n_dmps_claim`, `ndmp_independent_registry` (the two independent adapters:
  `NDmpTTestAdapter` + `NDmpOlsCoefAdapter`), and `run_cycle`. The only new thing is *synthesizing
  the inputs*. If the synthetic proof passes, the real pipeline is exercised end-to-end.
- **Determinism.** Fixed RNG seed; `build_contract` already rounds betas to 4 decimals on write, so
  the downstream n-DMP count is stable across runs/platforms. The test pins the exact count.
- **Distinct uid.** The synthetic contract uses `uid_stem="tcga_laml_idh_synth"` → ref
  `se:tcga_laml_idh_synth@1`, never colliding with the gitignored real `se:tcga_laml_idh@1/@2`.
- **Additive.** No change to grammar/protocol, the gate, the adapters, the contract format, or the
  real `ingest tcga-laml` data path (other than a friendlier error on fetch failure).
- **Offline + fast.** The synthetic proof must run with no network and in seconds (small N).

## 2. Components & flow

```
verify-kernel CLI ─┐
                   ├─▶ run_synthetic_kernel_proof()  ──▶ build_synthetic_contract()  (ingest/synthetic.py, new)
test (CI guard) ───┘        (kernel_proof.py, new)            │  deterministic, stdlib random + fixed seed
                                                              │  → calls EXISTING build_contract(uid_stem="tcga_laml_idh_synth")
                                                              ▼
                                                    se:tcga_laml_idh_synth@1  (built into a temp dir, scoped by using_contract_root)
                                                              │
                                                              ▼  EXISTING gate, unchanged
                              n_dmps_claim → run_cycle(ndmp_independent_registry: t-test + OLS legs)
                                                              ▼
                                          {status, independence_tier, n_dmps, e_value}
                                          expect: LICENSED @ REPRODUCED, n_dmps = pinned constant
```

| Piece | Location | Notes |
|---|---|---|
| `build_synthetic_contract(out_dir, *, seed=...) -> str` (returns uid) | `src/polymer_claims/ingest/synthetic.py` (new) | Synthesizes betas/row_meta/groups/clinical/sample_ids, calls existing `build_contract` |
| `run_synthetic_kernel_proof() -> KernelProofResult` | `src/polymer_claims/kernel_proof.py` (new) | Builds fixture → runs real gate → returns result dataclass. Shared by CLI + test (DRY) |
| `verify-kernel` subcommand | `src/polymer_claims/cli.py` | Prints tier / n_dmps / e-value; rc 0 iff LICENSED @ REPRODUCED |
| Friendlier offline error | `src/polymer_claims/cli.py` (`_cmd_ingest`) | Catch `urllib.error.URLError` → message pointing to `verify-kernel` + runbook |
| Gate test | `tests/test_kernel_proof_synthetic.py` (new) | Asserts LICENSED, REPRODUCED, pinned n_dmps |
| Retrieval runbook | `docs/superpowers/2026-06-23-kernel-proof-runbook.md` (new) | Current real `@2` path = local-only Xena matrix + cBioPortal genotyping via `build_contract_xena.py`/`run_gate.py` (untracked); deprecated `@1` = `ingest tcga-laml`; + the synthetic offline `verify-kernel` path |

## 3. The synthetic generator (`build_synthetic_contract`)

Deterministic, stdlib-only (`random.Random(seed)`); **no numpy in the generator** (the gate's
adapters may use numpy — that is unchanged and fine). Produces the five inputs `build_contract`
consumes:

- **Samples:** `N_SAMPLES = 40` — `sample_ids` like `SYN-0001…SYN-0040`; `groups` = 20 `WT` + 20
  `IDH_mut` (`Sample_Group` levels exactly `"WT"` / `"IDH_mut"`, matching the gate's
  `level_a="WT", level_b="IDH_mut"`). `clinical` = plausible Age (int) + Sex (`"male"`/`"female"`).
- **Probes:** `N_PROBES = 3000` synthetic ids `cgSYN000001…`; `row_meta[p] = {"chr": <autosome>,
  "pos": <int>}` — **autosomal only** (chr1–22) so the genome-wide sex-chrom QC filter keeps them.
- **Signal:** `N_DM = 150` probes get a planted differential: `WT ~ N(0.30, 0.03)`,
  `IDH_mut ~ N(0.60, 0.03)` (Δβ ≈ 0.30, clearly separable). The other 2850 are null:
  both groups `~ N(μ_p, 0.03)` for a per-probe baseline `μ_p ∈ [0.2, 0.8]`. All β clamped to
  `[0, 1]`. Low noise + clear Δ ⇒ both the t-test and OLS legs flag ≈ the planted set, comfortably
  above the pre-registered null floor `k = ceil(0.05 · n_probes)`.
- Calls `build_contract(out_dir, uid_stem="tcga_laml_idh_synth", betas=…, row_meta=…, groups=…,
  clinical=…, sample_ids=…)` and returns its uid.

The exact planted n-DMP that the gate *licenses* (≈150, but the QC filter + two-leg agreement set
the final count) is **pinned by the test after the first green run**, not asserted a priori.

## 4. The proof runner (`run_synthetic_kernel_proof`)

Mirrors `data/tcga_laml/run_gate.py` but committed, offline, and synthetic. Returns a small
`KernelProofResult` dataclass: `status: Status`, `independence_tier`, `n_dmps: int`, `e_value:
float`, `n_probes: int`, `k: int`. Builds the synthetic contract into a `TemporaryDirectory` scoped
by the existing `using_contract_root(tmpdir)` contextmanager (so `load_contract` and the adapters
that resolve betas through it all read from the temp dir) — **nothing is written to the source
tree**. Clears the contract cache, constructs the `n_dmps_claim` with the real oracle/profile
(`CANONICAL_HM450_V1`), and runs one `run_cycle` with `ndmp_independent_registry`. Pure
orchestration over existing pieces; no new gate logic.

## 5. CLI — `verify-kernel`

`polymer-claims verify-kernel` → calls the runner, prints e.g.:

```
kernel proof (synthetic, offline): LICENSED @ REPRODUCED
  n_probes=3000  null-floor k=150  n_dmps=<pinned>  e_value=<…>
  (synthetic fixture — proves pipeline integrity, NOT the real biology; see the runbook for the real proof)
```

Returns `0` iff `status == LICENSED` and `independence_tier == REPRODUCED`, else `1` (so it doubles
as a smoke check). No flags needed. Lazy-imports the runner (keeps base CLI import light).

## 6. Retrieval runbook + offline error + gitignore

- **Runbook** (`docs/superpowers/2026-06-23-kernel-proof-runbook.md`): (a) **Real proof — the
  CURRENT `se:tcga_laml_idh@2`** (2026-06-18 source swap): IDH-mut/WT from cBioPortal
  `laml_tcga_pub` genotyping (n=36) + a local Xena `TCGA-LAML.methylation450` matrix (~633 MB). Be
  honest that **all of `data/tcga_laml/` is local-only / gitignored / untracked** — the cBioPortal
  inputs, `build_contract_xena.py`, and `run_gate.py` are NOT in a fresh checkout; the real `@2`
  proof reproduces only in a working tree that has them (use `.venv/bin/python` for those script
  commands). Mark `polymer-claims ingest tcga-laml` as the **deprecated `@1`** GDC/MAF path
  (undercalled IDH at n=10; `tcga_laml_manifest.json` pins it for reference only). Genuinely
  reproducing the real `@2` from a fresh checkout is roadmap **H0.1b**, out of scope here.
  (b) **Offline proof** — `polymer-claims verify-kernel` runs the synthetic pipeline proof with no
  network. State plainly which is which.
- **Friendlier offline error:** in `_cmd_ingest`, catch `urllib.error.URLError` (covers the 404
  `HTTPError` subclass) and surface a single actionable line pointing to `verify-kernel` + the
  runbook, rather than a raw traceback. Success path unchanged.
- **No source-tree writes / no gitignore needed:** the synthetic contract is only ever built into a
  temp dir (runner: `TemporaryDirectory` + `using_contract_root`; tests: `tmp_path`), so nothing
  lands in `src/polymer_claims/contracts/` and no ignore rule is required. The generator is
  committed; its output is regenerated deterministically on demand.

## 7. Testing (TDD)

- **Generator (`tests/test_synthetic_contract.py` or folded in):** `build_synthetic_contract` is
  deterministic (same seed → identical betas TSV bytes); produces a loadable `se:tcga_laml_idh_synth@1`
  with `dim == [3000, 40]`, `Sample_Group` ∈ {WT, IDH_mut}, autosomal `chr` only.
- **Kernel proof (`tests/test_kernel_proof_synthetic.py`):** `run_synthetic_kernel_proof()` returns
  `status == LICENSED`, `independence_tier == REPRODUCED`, `n_dmps == <PINNED>` (exact, set after
  first green run), `n_dmps >= k` (clears the null floor). Runs offline, in seconds. Requires numpy
  (already a dev dependency; the gate adapters use it).
- **CLI (`tests/test_cli.py` or a new file):** `verify-kernel` smoke — rc 0, output contains
  `LICENSED @ REPRODUCED` and `n_dmps=`.
- **Offline-error:** simulate a fetch failure (monkeypatch `fetch_file`/`urlopen` to raise
  `URLError`) → the real ingest path returns the friendly message + nonzero, not a traceback.

## 8. Invariants

Additive; the real gate/adapters/contract format are untouched. No real TCGA bytes enter git (synth
fixture + gitignored output). Determinism: fixed seed + 4-decimal β rounding → pinned n-DMP count.
The synthetic ref (`…_synth@1`) never collides with the real ref. grammar/protocol unchanged. The
`verify-kernel` proof is honestly labeled "pipeline integrity, not the real biology."

## 9. Deferred / explicitly out of scope

- Bundling or LFS-storing the real betas (rejected: governance + size).
- Verifying the live GDC manifest UUIDs are still alive (can't from a network-isolated env; the
  runbook notes the dependency).
- Any change to the gate, adapters, FDR/e-value math, or the real `ingest` transform.
- CI wiring to run `verify-kernel`/the gate test automatically (the test exists; turning on CI is a
  separate infra step).

## 10. References

- `docs/superpowers/2026-06-23-remaining-roadmap.md` (H0.1; Path-α decision)
- `src/polymer_claims/ingest/{tcga_laml.py,gdc_fetch.py,transform.py}` (real fetch/build path)
- `src/polymer_claims/ingest/tcga_laml_manifest.json` (committed pinned recipe)
- `data/tcga_laml/run_gate.py` (the local, gitignored real-gate script this proof mirrors)
- `src/polymer_claims/methyl_ndmp.py` (`n_dmps_claim`, `ndmp_independent_registry`, the two adapters)
- `src/polymer_claims/profiles.py` (`CANONICAL_HM450_V1`)
