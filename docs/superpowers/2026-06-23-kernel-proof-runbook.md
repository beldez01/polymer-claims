# Kernel Proof — Reproduction Runbook

Two ways to reproduce the n-DMP kernel proof. They prove **different things** — read which is which.

## Offline (synthetic) — pipeline integrity, no network, seconds

```
polymer-claims verify-kernel
```

Builds a fully synthetic, deterministic HM450-shaped contract (`se:tcga_laml_idh_synth@1`) and runs
it through the **real** n-DMP gate (two independent legs + e-LOND + oracle). Expect
`LICENSED @ REPRODUCED`. This proves the gate **pipeline** reproduces deterministically offline. It
does **NOT** reproduce the real biology — no real TCGA data is involved (nothing real is committed).
Guarded in CI by `tests/test_kernel_proof_synthetic.py`. (Needs numpy — the gate adapters use it;
`pip install 'polymer-claims[calibrate]'` if a base install lacks it.)

## Real proof — the current genome-wide TCGA-LAML claim (`se:tcga_laml_idh@2`)

The **current** earned proof is `se:tcga_laml_idh@2` (the 2026-06-18 source swap): IDH-mut/WT calls
come from **cBioPortal `laml_tcga_pub` genotyping** (IDH-mut n=36) and betas come from a local Xena
`TCGA-LAML.methylation450` matrix (~633 MB).

**These inputs and the build/gate scripts are LOCAL-ONLY and are NOT in a fresh checkout.** All of
`data/tcga_laml/` — the cBioPortal files, `build_contract_xena.py`, and `run_gate.py` — is
gitignored by design (TCGA data-use terms + size; the scripts also hardcode a local Xena path). The
real `@2` proof therefore reproduces only in a working tree that already holds them. To reconstruct
from scratch: re-fetch the cBioPortal `laml_tcga_pub` mutations (pin the commit + `HGVSp_Short`
protein-change column as the original `cbioportal/SOURCE.txt` records), supply the Xena
methylation450 matrix locally, then:

```
# only in a tree that has the local-only data/tcga_laml/ scripts + a local Xena matrix:
.venv/bin/python data/tcga_laml/build_contract_xena.py   # -> se:tcga_laml_idh@2 into contracts/ (untracked)
.venv/bin/python data/tcga_laml/run_gate.py              # -> LICENSED @ REPRODUCED on real data; honest q
```

For a reproduction that works from a **fresh checkout with no real data**, use the offline synthetic
proof above (`polymer-claims verify-kernel`) — that is the committed, CI-guarded reproducibility this
slice delivers. Turning the *real* `@2` data into a retrievable, fresh-checkout-runnable artifact is
tracked as roadmap **H0.1b** and is out of scope here.

> **Deprecated path — do not confuse it with the current proof.** `polymer-claims ingest tcga-laml`
> fetches the GDC open-access masked-WXS MAFs and builds the **older** `se:tcga_laml_idh@1`. That MAF
> source **undercalled IDH (n=10)** and was superseded by the cBioPortal `@2` genotyping above. The
> committed `tcga_laml_manifest.json` (UUID + MD5) pins that `@1` recipe for reference only; the data
> it fetches stays gitignored and it requires GDC reachability. When GDC is unreachable, `ingest
> tcga-laml` now prints an actionable message pointing here and to `verify-kernel`.
