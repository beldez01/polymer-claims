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

## Real proof, fresh-checkout-runnable — `verify-kernel --real` (H0.1b)

The real `se:tcga_laml_idh@2` proof now reproduces from a clean checkout once you supply the three
pinned inputs. It proves **the pinned real-data computation reproduces** — NOT data veracity or
independence (that is roadmap H1.A2).

```
# inputs are pinned by checksum and stay out of git. Supply locally (default) or fetch (opt-in):
polymer-claims verify-kernel --real \
    --xena /path/TCGA-LAML.methylation450.tsv.gz \
    --cbioportal /path/dir_with_data_mutations.txt_and_sequenced_samples.json
# add --fetch to download the pinned inputs into the cache instead of supplying them.
```

Expect `LICENSED @ REPRODUCED`. The gate verifies the rebuilt contract's byte-level `contract_checksum`
and the gate-result addresses (`n_dmps`, `e_value`, `profile_hash`, `semantic_run_id`) against the
committed pins in `src/polymer_claims/ingest/real_kernel_pins.json`. The ~633 MB matrix means this is
**manual/opt-in, not CI** (CI guards the synthetic `verify-kernel` and the parity machinery).

**How the pins were captured / how to re-capture (spec §6 — no self-fulfilling parity):**
`real_kernel_pins.json` now holds the **real pins** (captured + verified 2026-06-25; `verify-kernel
--real` returns `LICENSED @ REPRODUCED`). They were produced — and should be re-produced if the inputs
ever change (new Xena release, new cBioPortal commit) — by running the script in **both** modes and
diffing (the new builder must reproduce the trusted `@2` addresses exactly before pins are committed):

```
# 1. ground truth: addresses of the already-trusted @2 contract (no rebuild)
.venv/bin/python scripts/bootstrap_real_kernel_pins.py --from-existing \
    --contract-root src/polymer_claims/contracts | python -c 'import sys,json; print(json.dumps(json.load(sys.stdin)["expected"],sort_keys=True))' > trusted_expected.json
# 2. NEW-builder rebuild from the real inputs -> full pins
.venv/bin/python scripts/bootstrap_real_kernel_pins.py \
    --xena /path/TCGA-LAML.methylation450.tsv.gz --cbioportal /path/cbio \
    --commit 86690e1ed9752b1dcd50b5657f5f05eafa4b6b78 > rebuilt_pins.json
# 3. the new builder must reproduce the trusted addresses EXACTLY:
python -c 'import sys,json; print(json.dumps(json.load(open("rebuilt_pins.json"))["expected"],sort_keys=True))' > rebuilt_expected.json
diff trusted_expected.json rebuilt_expected.json && echo "PARITY OK — safe to commit pins"
```

Only if the diff is empty, write `rebuilt_pins.json` to
`src/polymer_claims/ingest/real_kernel_pins.json` and commit. A non-empty diff means the new builder
is not faithful to the earned proof — fix the builder, never the pins.

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
# SUPERSEDED by `verify-kernel --real` (see section above). Left for historical reference only.
# only in a tree that has the local-only data/tcga_laml/ scripts + a local Xena matrix:
.venv/bin/python data/tcga_laml/build_contract_xena.py   # -> se:tcga_laml_idh@2 into contracts/ (untracked)
.venv/bin/python data/tcga_laml/run_gate.py              # -> LICENSED @ REPRODUCED on real data; honest q
```

> **Superseded by `verify-kernel --real` (H0.1b).** The hardcoded `build_contract_xena.py` /
> `run_gate.py` path above requires local-only scripts and a gitignored Xena path; it is no longer the
> recommended reproduction path. Use `polymer-claims verify-kernel --real` (section above) instead.

For a reproduction that works from a **fresh checkout with no real data**, use the offline synthetic
proof above (`polymer-claims verify-kernel`) — that is the committed, CI-guarded reproducibility this
slice delivers.

> **Deprecated path — do not confuse it with the current proof.** `polymer-claims ingest tcga-laml`
> fetches the GDC open-access masked-WXS MAFs and builds the **older** `se:tcga_laml_idh@1`. That MAF
> source **undercalled IDH (n=10)** and was superseded by the cBioPortal `@2` genotyping above. The
> committed `tcga_laml_manifest.json` (UUID + MD5) pins that `@1` recipe for reference only; the data
> it fetches stays gitignored and it requires GDC reachability. When GDC is unreachable, `ingest
> tcga-laml` now prints an actionable message pointing here and to `verify-kernel`.
