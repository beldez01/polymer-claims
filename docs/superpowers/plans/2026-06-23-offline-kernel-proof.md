# Offline-Reproducible Kernel Proof Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the n-DMP gate pipeline re-runnable offline and deterministically via a fully synthetic, realistic-shaped HM450 contract run through the *real* gate — guarded by a committed test, runnable via a `verify-kernel` CLI, with a hardened retrieval runbook for the real proof.

**Architecture:** A deterministic stdlib generator synthesizes the inputs the *existing* `build_contract` consumes (betas/row_meta/groups/clinical/sample_ids) under a distinct uid `tcga_laml_idh_synth`; a thin runner builds that contract and runs the *existing* `n_dmps_claim` through `run_cycle` with the *existing* two-independent-adapter registry, returning a result the test asserts on and the CLI prints. Nothing real is committed; the gate/adapters/contract format are untouched.

**Tech Stack:** Python 3, stdlib `random` (generator — no numpy), the existing methylation gate (numpy-backed adapters), pydantic models, argparse CLI, pytest. Interpreter for all commands: `/Users/zbb2/Desktop/polymer-claims/.venv/bin/python` (`python` alone is NOT on PATH).

## Global Constraints

- **Nothing real committed.** Fixture is fully synthetic; the synthetic output contract is gitignored (Task 1 adds the ignore rule). The real-data path stays manifest + script only.
- **Reuse the real gate, do not fork it.** Use the existing `build_contract`, `n_dmps_claim`, `ndmp_independent_registry`, `NDmpTTestAdapter`, `NDmpOlsCoefAdapter`, `run_cycle`. No changes to grammar/protocol, the gate, the adapters, the FDR/e-value math, or the contract format.
- **Distinct uid:** synthetic contract uses `uid_stem="tcga_laml_idh_synth"` → ref `se:tcga_laml_idh_synth@1`. Never collides with the gitignored real `se:tcga_laml_idh@1`/`@2`.
- **Determinism:** fixed RNG seed `SYNTH_SEED = 20260623`; `build_contract` writes betas at 4-decimal precision → stable n-DMP count. The proof test pins the exact count after the first green run.
- **Sample group levels exactly `"WT"` / `"IDH_mut"`** (matches the gate's `level_a="WT", level_b="IDH_mut"`). Probes autosomal only (`chr1`–`chr22`) so the genome-wide sex-chrom QC filter keeps them.
- **Offline + fast:** the synthetic proof runs with no network, in seconds (`N_SAMPLES=40`, `N_PROBES=3000`).
- **Additive:** the only change to the real `ingest tcga-laml` path is a friendlier error when GDC is unreachable (success path byte-identical).
- Every commit message ends with the `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>` trailer.

---

## File Structure

| File | Change | Responsibility |
|---|---|---|
| `src/polymer_claims/ingest/synthetic.py` | Create | `build_synthetic_contract` — deterministic synthetic HM450 inputs → existing `build_contract` |
| `src/polymer_claims/kernel_proof.py` | Create | `run_synthetic_kernel_proof` + `KernelProofResult` — build fixture → run real gate → result |
| `src/polymer_claims/cli.py` | Modify | `verify-kernel` subcommand; friendlier offline error in `_cmd_ingest` |
| `.gitignore` | Modify | Ignore the synthetic output contract |
| `docs/superpowers/2026-06-23-kernel-proof-runbook.md` | Create | Real-proof retrieval recipe + offline synthetic path |
| `tests/test_synthetic_contract.py` | Create | Generator determinism + loadable contract |
| `tests/test_kernel_proof_synthetic.py` | Create | LICENSED @ REPRODUCED, pinned n-DMP count |
| `tests/test_cli_verify_kernel.py` | Create | CLI smoke + offline-error message |

---

### Task 1: Synthetic contract generator

**Files:**
- Create: `src/polymer_claims/ingest/synthetic.py`
- Modify: `.gitignore`
- Test: `tests/test_synthetic_contract.py`

**Interfaces:**
- Consumes: the existing `polymer_claims.ingest.transform.build_contract(out_dir, *, uid_stem, betas, row_meta, groups, clinical, sample_ids) -> str` and `polymer_claims.contracts.load_contract` / `clear_contract_cache`.
- Produces: `build_synthetic_contract(out_dir, *, seed: int = 20260623) -> str` — writes `tcga_laml_idh_synth.json` + `.betas.tsv` into `out_dir` and returns the uid `"tcga_laml_idh_synth@1"`. Module constants `SYNTH_SEED=20260623`, `N_SAMPLES=40`, `N_PROBES=3000`, `N_DM=150`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_synthetic_contract.py`:

```python
from pathlib import Path

from polymer_claims import contracts as _contracts
from polymer_claims.ingest.synthetic import build_synthetic_contract, N_PROBES, N_SAMPLES


def test_generator_is_deterministic(tmp_path):
    a = tmp_path / "a"; b = tmp_path / "b"
    build_synthetic_contract(a); build_synthetic_contract(b)
    ta = (a / "tcga_laml_idh_synth.betas.tsv").read_bytes()
    tb = (b / "tcga_laml_idh_synth.betas.tsv").read_bytes()
    assert ta == tb and len(ta) > 0          # same seed -> identical betas TSV bytes


def test_contract_loads_with_expected_shape(tmp_path):
    uid = build_synthetic_contract(tmp_path)
    assert uid == "tcga_laml_idh_synth@1"
    import json
    manifest = json.loads((tmp_path / "tcga_laml_idh_synth.json").read_text())
    assert manifest["dim"] == [N_PROBES, N_SAMPLES]     # all autosomal probes survive QC
    groups = {c["Sample_Group"] for c in manifest["col_data"]}
    assert groups == {"WT", "IDH_mut"}
    assert all(not r["chr"].endswith(("X", "Y")) for r in manifest["row_data"])  # autosomal only
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/zbb2/Desktop/polymer-claims && /Users/zbb2/Desktop/polymer-claims/.venv/bin/python -m pytest tests/test_synthetic_contract.py -v`
Expected: FAIL — `ModuleNotFoundError: polymer_claims.ingest.synthetic`.

- [ ] **Step 3: Implement the generator**

Create `src/polymer_claims/ingest/synthetic.py`:

```python
"""Deterministic, fully-synthetic HM450-shaped inputs for the offline kernel proof.

No real TCGA bytes — a realistic-shaped fixture (IDH-mut vs WT, a planted differential-methylation
signal + null bulk) that licenses the n-DMP claim through the REAL gate. Stdlib-only generation
(no numpy); reuses the existing build_contract verbatim. See
docs/superpowers/specs/2026-06-23-offline-kernel-proof-design.md.
"""
from __future__ import annotations

import random
from pathlib import Path

from polymer_claims.ingest.transform import build_contract

SYNTH_SEED = 20260623
N_SAMPLES = 40          # 20 WT + 20 IDH_mut
N_PROBES = 3000
N_DM = 150              # planted differentially-methylated probes
_UID_STEM = "tcga_laml_idh_synth"
_SIGMA = 0.03           # within-group noise
_DELTA = 0.30           # WT 0.30 vs IDH_mut 0.60 on planted probes


def _clamp(x: float) -> float:
    return 0.0 if x < 0.0 else (1.0 if x > 1.0 else x)


def build_synthetic_contract(out_dir, *, seed: int = SYNTH_SEED) -> str:
    """Synthesize a deterministic HM450-shaped contract and write it via the real build_contract.
    Returns the uid 'tcga_laml_idh_synth@1'."""
    rng = random.Random(seed)
    sample_ids = [f"SYN-{i:04d}" for i in range(N_SAMPLES)]
    half = N_SAMPLES // 2
    groups = {s: ("WT" if i < half else "IDH_mut") for i, s in enumerate(sample_ids)}
    clinical = {s: {"Age": rng.randint(40, 80), "Sex": rng.choice(["male", "female"])}
                for s in sample_ids}

    betas: dict[str, dict[str, float]] = {}
    row_meta: dict[str, dict] = {}
    for p in range(N_PROBES):
        probe = f"cgSYN{p:06d}"
        row_meta[probe] = {"chr": f"chr{(p % 22) + 1}", "pos": (p + 1) * 100}
        planted = p < N_DM
        base_mu = rng.uniform(0.2, 0.8)
        col: dict[str, float] = {}
        for s in sample_ids:
            if planted:
                mu = 0.30 if groups[s] == "WT" else 0.30 + _DELTA
            else:
                mu = base_mu
            col[s] = _clamp(rng.gauss(mu, _SIGMA))
        betas[probe] = col

    return build_contract(
        out_dir, uid_stem=_UID_STEM,
        betas=betas, row_meta=row_meta, groups=groups,
        clinical=clinical, sample_ids=sample_ids,
    )
```

- [ ] **Step 4: Add the gitignore rule**

Append to `.gitignore` (next to the existing `src/polymer_claims/contracts/tcga_laml_idh.*` rules):

```
# synthetic offline kernel-proof contract (regenerated deterministically on demand)
src/polymer_claims/contracts/tcga_laml_idh_synth.*
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd /Users/zbb2/Desktop/polymer-claims && /Users/zbb2/Desktop/polymer-claims/.venv/bin/python -m pytest tests/test_synthetic_contract.py -v`
Expected: PASS (2 passed).

- [ ] **Step 6: Commit**

```bash
git add src/polymer_claims/ingest/synthetic.py tests/test_synthetic_contract.py .gitignore
git commit -m "feat(ingest): deterministic synthetic HM450 contract generator

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: Kernel-proof runner

**Files:**
- Create: `src/polymer_claims/kernel_proof.py`
- Test: `tests/test_kernel_proof_synthetic.py`

**Interfaces:**
- Consumes: `build_synthetic_contract` (Task 1); the existing gate — `n_dmps_claim`, `ndmp_independent_registry`, `NDmpTTestAdapter`, `NDmpOlsCoefAdapter`, `dmp_indicators`, `_all_probe_ids` from `polymer_claims.methyl_ndmp`; `count_enrichment_evalue`; `materialization_map`; `profile_oracle_id`/`profile_oracle_registry`; `CANONICAL_HM450_V1`; `Corpus`, `run_cycle`, `FDRLedger`, `MaterializationContext`, `Status`.
- Produces: `run_synthetic_kernel_proof() -> KernelProofResult`, a frozen dataclass with `status: Status`, `independence_tier` (the licensing enum or `None`), `n_dmps: int`, `e_value: float`, `n_probes: int`, `k: int`, `licensed: bool`.

- [ ] **Step 1: Write the failing test (a-priori-knowable assertions)**

Create `tests/test_kernel_proof_synthetic.py`:

```python
from polymer_grammar import Status
from polymer_claims.kernel_proof import run_synthetic_kernel_proof


def test_synthetic_kernel_proof_licenses_at_reproduced():
    r = run_synthetic_kernel_proof()
    assert r.status is Status.LICENSED and r.licensed is True
    assert r.independence_tier is not None
    assert r.independence_tier.name == "REPRODUCED"     # two independent legs agreed
    assert r.n_dmps >= r.k                               # clears the pre-registered null floor
    assert r.n_probes == 3000 and r.k == 150
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/zbb2/Desktop/polymer-claims && /Users/zbb2/Desktop/polymer-claims/.venv/bin/python -m pytest tests/test_kernel_proof_synthetic.py -v`
Expected: FAIL — `ModuleNotFoundError: polymer_claims.kernel_proof`.

- [ ] **Step 3: Implement the runner**

Create `src/polymer_claims/kernel_proof.py` (mirrors `data/tcga_laml/run_gate.py`, committed + synthetic + offline):

```python
"""Offline kernel proof: build the synthetic HM450 fixture, run the REAL n-DMP gate, return the
outcome. Shared by the verify-kernel CLI and the CI guard test. No network; deterministic.
See docs/superpowers/specs/2026-06-23-offline-kernel-proof-design.md."""
from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

from polymer_grammar import FDRLedger, MaterializationContext, Status
from polymer_protocol import Corpus, run_cycle

from polymer_claims import contracts as _contracts
from polymer_claims.analysis_profile import profile_oracle_id, profile_oracle_registry
from polymer_claims.evidence import count_enrichment_evalue
from polymer_claims.ingest.synthetic import build_synthetic_contract
from polymer_claims.materialization import materialization_map
from polymer_claims.methyl_ndmp import (
    NDmpOlsCoefAdapter,
    NDmpTTestAdapter,
    _all_probe_ids,
    dmp_indicators,
    n_dmps_claim,
    ndmp_independent_registry,
)
from polymer_claims.profiles import CANONICAL_HM450_V1

_REF = "se:tcga_laml_idh_synth@1"
_ALPHA = 0.05
_CLAIM_ID = "synthetic-kernel-ndmp"


@dataclass(frozen=True)
class KernelProofResult:
    status: Status
    independence_tier: object | None   # IndependenceTier | None — kept loose to avoid import coupling
    n_dmps: int
    e_value: float
    n_probes: int
    k: int
    licensed: bool


def run_synthetic_kernel_proof() -> KernelProofResult:
    """Build the synthetic contract into the package contracts dir, run the real gate, return result."""
    build_synthetic_contract(Path(_contracts.__file__).parent)
    _contracts.clear_contract_cache()

    n_probes = len(_all_probe_ids(_REF))
    k = math.ceil(_ALPHA * n_probes)
    claim = n_dmps_claim(
        _CLAIM_ID, ref=_REF,
        group_col="Sample_Group", level_a="WT", level_b="IDH_mut",
        alpha=_ALPHA, k=k, oracle_ref=profile_oracle_id(CANONICAL_HM450_V1),
    )
    node = claim.evaluation_plan.graph.nodes[0]
    ind = dmp_indicators(node)
    n_dmps = int(sum(ind))
    evalue = count_enrichment_evalue(ind, p0=_ALPHA)

    base = MaterializationContext(id="M", api_version="v1", data_version="d1")
    corpus = Corpus(claims=(claim,), fdr_ledger=FDRLedger(target_fdr=0.05))
    result = run_cycle(
        corpus, (NDmpTTestAdapter(), NDmpOlsCoefAdapter()), base,
        adapter_registry=ndmp_independent_registry(),
        oracles=profile_oracle_registry((CANONICAL_HM450_V1, "recomputable_public")),
        materializations=materialization_map(corpus, base, profiles=(CANONICAL_HM450_V1,)),
        evidence={_CLAIM_ID: evalue},
    )
    c = next(x for x in result.corpus.claims if x.id == _CLAIM_ID)
    tier = c.licensing.independence_tier if c.licensing is not None else None
    return KernelProofResult(
        status=c.status, independence_tier=tier, n_dmps=n_dmps, e_value=evalue,
        n_probes=n_probes, k=k, licensed=(c.status is Status.LICENSED),
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/zbb2/Desktop/polymer-claims && /Users/zbb2/Desktop/polymer-claims/.venv/bin/python -m pytest tests/test_kernel_proof_synthetic.py -v`
Expected: PASS. If it does NOT license (tier None / not REPRODUCED, or `n_dmps < k`), the planted signal is too weak — this is a fixture-tuning failure, not a code bug: do not weaken the assertions. Read the actual `r.n_dmps`/`r.k` from a debug print and, if needed, raise `N_DM` (e.g. to 300) in `synthetic.py`, re-run Task 1's tests, and retry. The Δβ=0.30/σ=0.03 defaults give a large margin and should clear on the first run.

- [ ] **Step 5: Pin the exact deterministic n-DMP count**

The count is deterministic (fixed seed + 4-decimal betas). Read the observed value:

Run: `cd /Users/zbb2/Desktop/polymer-claims && /Users/zbb2/Desktop/polymer-claims/.venv/bin/python -c "from polymer_claims.kernel_proof import run_synthetic_kernel_proof as r; x=r(); print('PINNED_N_DMPS', x.n_dmps)"`
Note the printed integer `<PINNED>`. Append a pinning assertion to the test in `tests/test_kernel_proof_synthetic.py`:

```python
def test_synthetic_kernel_proof_n_dmps_is_pinned():
    # Deterministic: fixed seed + 4-decimal betas. Update <PINNED> only with an intentional
    # fixture change. Regenerate via the -c one-liner in the plan if this ever changes.
    r = run_synthetic_kernel_proof()
    assert r.n_dmps == <PINNED>
```

Replace `<PINNED>` with the printed integer.

- [ ] **Step 6: Run the test to verify the pin passes**

Run: `cd /Users/zbb2/Desktop/polymer-claims && /Users/zbb2/Desktop/polymer-claims/.venv/bin/python -m pytest tests/test_kernel_proof_synthetic.py -v`
Expected: PASS (2 passed).

- [ ] **Step 7: Commit**

```bash
git add src/polymer_claims/kernel_proof.py tests/test_kernel_proof_synthetic.py
git commit -m "feat(kernel-proof): synthetic offline gate runner (LICENSED @ REPRODUCED)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: `verify-kernel` CLI subcommand

**Files:**
- Modify: `src/polymer_claims/cli.py` (add `_cmd_verify_kernel` near the other `_cmd_*`; register in `_build_parser`)
- Test: `tests/test_cli_verify_kernel.py`

**Interfaces:**
- Consumes: `run_synthetic_kernel_proof` / `KernelProofResult` (Task 2); the existing `main(argv)` argparse entrypoint.
- Produces: CLI `polymer-claims verify-kernel` — prints the tier / n_dmps / e_value; returns `0` iff `licensed and independence_tier.name == "REPRODUCED"`, else `1`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_cli_verify_kernel.py`:

```python
from polymer_claims.cli import main


def test_verify_kernel_smoke(capsys):
    rc = main(["verify-kernel"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "LICENSED @ REPRODUCED" in out
    assert "n_dmps=" in out
    assert "synthetic" in out.lower()       # honest labeling: not the real biology
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/zbb2/Desktop/polymer-claims && /Users/zbb2/Desktop/polymer-claims/.venv/bin/python -m pytest tests/test_cli_verify_kernel.py -v`
Expected: FAIL — argparse error: invalid choice `verify-kernel`.

- [ ] **Step 3: Add the handler**

In `src/polymer_claims/cli.py`, add near the other `_cmd_*` functions:

```python
def _cmd_verify_kernel(args: argparse.Namespace) -> int:
    from .kernel_proof import run_synthetic_kernel_proof

    r = run_synthetic_kernel_proof()
    tier = r.independence_tier.name if r.independence_tier is not None else "NONE"
    ok = r.licensed and tier == "REPRODUCED"
    print(f"kernel proof (synthetic, offline): {'LICENSED @ ' + tier if r.licensed else 'NOT LICENSED'}")
    print(f"  n_probes={r.n_probes}  null-floor k={r.k}  n_dmps={r.n_dmps}  e_value={r.e_value:.3e}")
    print("  (synthetic fixture — proves pipeline integrity, NOT the real biology; "
          "see docs/superpowers/2026-06-23-kernel-proof-runbook.md for the real proof)")
    return 0 if ok else 1
```

- [ ] **Step 4: Register the subcommand**

In `_build_parser`, after an existing `sub.add_parser(...)` block:

```python
    p_vk = sub.add_parser("verify-kernel",
                          help="run the synthetic n-DMP kernel proof offline (pipeline integrity check)")
    p_vk.set_defaults(func=_cmd_verify_kernel)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd /Users/zbb2/Desktop/polymer-claims && /Users/zbb2/Desktop/polymer-claims/.venv/bin/python -m pytest tests/test_cli_verify_kernel.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/polymer_claims/cli.py tests/test_cli_verify_kernel.py
git commit -m "feat(cli): verify-kernel — offline synthetic kernel proof

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: Friendlier offline error + retrieval runbook

**Files:**
- Modify: `src/polymer_claims/cli.py` (`_cmd_ingest` — catch `URLError` specifically)
- Create: `docs/superpowers/2026-06-23-kernel-proof-runbook.md`
- Test: `tests/test_cli_verify_kernel.py` (extend)

**Interfaces:**
- Consumes: the existing `_cmd_ingest` handler and `polymer_claims.ingest.tcga_laml.ingest_tcga_laml` (which calls `fetch_file`, raising `urllib.error.URLError`/`HTTPError` when GDC is unreachable).
- Produces: on a GDC network failure, `ingest tcga-laml` prints a single actionable line mentioning `verify-kernel` and the runbook, and returns `1` (no raw traceback). Success path unchanged.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_cli_verify_kernel.py`:

```python
import urllib.error
import pytest
from polymer_claims.cli import main


def test_ingest_offline_error_is_friendly(tmp_path, capsys, monkeypatch):
    # Simulate GDC unreachable: make the fetch raise URLError.
    def _boom(*a, **k):
        raise urllib.error.URLError("network is unreachable")
    monkeypatch.setattr("polymer_claims.ingest.tcga_laml.fetch_file", _boom)
    rc = main(["ingest", "tcga-laml", "--data-dir", str(tmp_path)])
    err = capsys.readouterr().err
    assert rc == 1
    assert "verify-kernel" in err          # points to the offline path
    assert "runbook" in err.lower()
    assert "Traceback" not in err          # no raw traceback
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/zbb2/Desktop/polymer-claims && /Users/zbb2/Desktop/polymer-claims/.venv/bin/python -m pytest tests/test_cli_verify_kernel.py::test_ingest_offline_error_is_friendly -v`
Expected: FAIL — current `_cmd_ingest` prints a generic `ingest failed: <URLError>` without the `verify-kernel`/runbook guidance.

- [ ] **Step 3: Add the friendly catch**

In `src/polymer_claims/cli.py`, modify `_cmd_ingest` so the network error is caught *before* the generic handler. Add `import urllib.error` at the top of the file if not present, then update the handler body:

```python
def _cmd_ingest(args: argparse.Namespace) -> int:
    if args.dataset != "tcga-laml":
        print(f"unknown ingest dataset: {args.dataset!r}", file=sys.stderr)
        return 1
    from .ingest.tcga_laml import ingest_tcga_laml
    try:
        print(ingest_tcga_laml(args.data_dir))
    except urllib.error.URLError as exc:
        print(
            "GDC unreachable — could not fetch the real TCGA-LAML data "
            f"({exc.reason if hasattr(exc, 'reason') else exc}).\n"
            "  • For an offline pipeline check, run: polymer-claims verify-kernel\n"
            "  • To reproduce the REAL proof, see docs/superpowers/2026-06-23-kernel-proof-runbook.md",
            file=sys.stderr,
        )
        return 1
    except Exception as exc:  # noqa: BLE001 — surface any other ingest error to the user
        print(f"ingest failed: {exc}", file=sys.stderr)
        return 1
    return 0
```

> Note: keep whatever the existing handler already does on success (printing the summary + `return 0`). The only change is the dedicated `URLError` branch above the generic `except`. `urllib.error.HTTPError` is a subclass of `URLError`, so the 404 the verification hit is covered.

- [ ] **Step 4: Write the runbook**

Create `docs/superpowers/2026-06-23-kernel-proof-runbook.md`:

```markdown
# Kernel Proof — Reproduction Runbook

Two ways to reproduce the n-DMP kernel proof. They prove different things — read which is which.

## Offline (synthetic) — pipeline integrity, no network, seconds

```
polymer-claims verify-kernel
```

Builds a fully synthetic, deterministic HM450-shaped contract (`se:tcga_laml_idh_synth@1`) and runs
it through the **real** n-DMP gate (two independent legs + e-LOND + oracle). Expect
`LICENSED @ REPRODUCED`. This proves the gate **pipeline** reproduces deterministically offline. It
does **NOT** reproduce the real biology — no real TCGA data is involved (nothing real is committed).
Guarded in CI by `tests/test_kernel_proof_synthetic.py`.

## Real proof — the genome-wide TCGA-LAML claim (needs the data)

The pinned recipe is committed (`src/polymer_claims/ingest/tcga_laml_manifest.json`, UUID + MD5 per
file); the data it fetches stays gitignored. Requires GDC reachability (or a pre-populated cache dir).

```
# 1. Fetch + build the real SE-contract (cache-first; re-runs are offline once cached)
polymer-claims ingest tcga-laml --data-dir <local-cache-dir>
#    -> builds se:tcga_laml_idh@1 from real TCGA-LAML HM450 (IDH-mut vs WT)

# 2. Run the genome-wide gate (see data/tcga_laml/run_gate.py — local, gitignored)
#    -> licenses the n-DMP claim at REPRODUCED on real data; emits the honest q + certificate
```

If GDC is unreachable, `ingest tcga-laml` now prints an actionable message pointing back here and to
`verify-kernel`. The real betas are hundreds of MB and TCGA has data-use terms — they are
intentionally never committed.
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `cd /Users/zbb2/Desktop/polymer-claims && /Users/zbb2/Desktop/polymer-claims/.venv/bin/python -m pytest tests/test_cli_verify_kernel.py -v`
Expected: PASS (all in file).

- [ ] **Step 6: Commit**

```bash
git add src/polymer_claims/cli.py docs/superpowers/2026-06-23-kernel-proof-runbook.md tests/test_cli_verify_kernel.py
git commit -m "feat(cli): friendly GDC-offline error + kernel-proof reproduction runbook

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Final Verification

- [ ] **All new tests green:**

Run: `cd /Users/zbb2/Desktop/polymer-claims && /Users/zbb2/Desktop/polymer-claims/.venv/bin/python -m pytest tests/test_synthetic_contract.py tests/test_kernel_proof_synthetic.py tests/test_cli_verify_kernel.py -v`
Expected: all pass.

- [ ] **CLI end-to-end:** `... -m polymer_claims.cli verify-kernel` prints `LICENSED @ REPRODUCED` and returns 0.
- [ ] **Lint:** `ruff check src/polymer_claims/ingest/synthetic.py src/polymer_claims/kernel_proof.py src/polymer_claims/cli.py` → clean.
- [ ] **Nothing real / no stray commits:** `git status` shows no `tcga_laml_idh_synth.*` contract files staged (gitignored); only the intended source/test/doc files were committed.

## Self-Review Notes (planner)

- **Spec coverage:** §3 generator → Task 1; §4 runner → Task 2; §5 CLI → Task 3; §6 runbook + offline error + gitignore → Tasks 1 (ignore) + 4 (error + runbook); §7 testing → tests in each task; §8 invariants → Global Constraints + Final Verification.
- **Determinism / pinned count:** the n-DMP count is unknown a priori; Task 2 writes the knowable assertions first (LICENSED, REPRODUCED, `n_dmps >= k`) then pins the exact value from the observed deterministic run (Step 5) — honest TDD, not a placeholder.
- **Reuse:** the runner and generator add zero gate logic; they orchestrate existing functions whose signatures were read from the real code (`n_dmps_claim`, `ndmp_independent_registry`, `build_contract`, `dmp_indicators`, `_all_probe_ids`, `count_enrichment_evalue`, `materialization_map`, `profile_oracle_*`, `CANONICAL_HM450_V1`).
- **Independence-tier coupling:** `KernelProofResult.independence_tier` holds the raw licensing enum; tests/CLI use `.name == "REPRODUCED"` so no fragile import path is assumed.
```
