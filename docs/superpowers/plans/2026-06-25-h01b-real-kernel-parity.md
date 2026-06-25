# H0.1b Real-Data Kernel Parity Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `verify-kernel --real`, a content-address-parity gate that rebuilds the real
`se:tcga_laml_idh@2` proof from three pinned external inputs, asserts the rebuilt content-addresses
match committed pins, runs the real n-DMP gate, and requires `LICENSED @ REPRODUCED`.

**Architecture:** Mirror the existing synthetic `kernel_proof.py`: build a contract into a temp
contract root (`using_contract_root` — nothing touches the source tree), run the real gate, return a
result. New tracked code is untrusted scaffolding that produces inputs the *existing* gate re-checks;
the only added logic is input pinning + parity assertions. No TCGA bytes enter git — only the pins.

**Tech Stack:** Python 3.12, stdlib (`gzip`, `hashlib`, `json`, `urllib`, `importlib.resources`,
`argparse`, `tempfile`), pytest. Reuses `polymer_grammar`, `polymer_protocol`, and existing
`polymer_claims` modules (`contracts`, `evidence`, `materialization`, `methyl_ndmp`, `profiles`,
`analysis_profile`, `_hashing`, `ingest.transform`). numpy is required by the n-DMP adapters (the
`[calibrate]` extra).

## Global Constraints

- **No TCGA-derived bytes in git.** Only pins (checksums, URLs/endpoint, mutations commit, expected
  content-addresses) are committed. All three inputs stay gitignored/external.
- **Fetch is opt-in.** Inputs resolve from local path → cache only; network requires `--fetch`.
- **Three pinned inputs:** Xena matrix; cBioPortal **mutations** file (datahub commit-addressed);
  cBioPortal **sample-list** API response (pinned separately by endpoint + sha).
- **No self-fulfilling parity.** Real pins (`real_kernel_pins.json`) are bootstrapped from the
  previously trusted `@2` artifact (Task 6), committed, then the new builder must reproduce them.
- **Existing `verify-kernel` (synthetic) must stay byte-identical** when `--real` is absent.
- **Byte-level `contract_checksum` is the primary gate.** `canonical_checksum` is a *diagnostic*,
  computed on demand only to distinguish a serialization bug from a content divergence — never a gate.
- **`e_value` pin** is the string `"inf"`, compared with `math.isinf(x) and x > 0`; a finite pin uses
  exact `repr` + relative tolerance `1e-12`.
- **Claim construction is fixed** (Task 4): id `tcga-laml-ndmp`, ref `se:tcga_laml_idh@2`,
  `group_col="Sample_Group"`, `level_a="WT"`, `level_b="IDH_mut"`, `alpha=0.05`,
  `k=ceil(0.05*n_probes)`, `probes=None` (→ `_all_probe_ids`), `oracle_ref=profile_oracle_id(CANONICAL_HM450_V1)`.
- **Enum pins are serialized values** (lowercase `"licensed"` / `"reproduced"`); code compares against
  `Status`/`IndependenceTier` identity or `.value`.
- **Spec:** `docs/superpowers/specs/2026-06-25-h01b-real-kernel-parity-design.md` (v0.2).

---

### Task 1: Pinned-input resolver

**Files:**
- Create: `src/polymer_claims/ingest/_pinned.py`
- Test: `tests/test_pinned_resolver.py`

**Interfaces:**
- Produces: `PinnedInputError(RuntimeError)`; `resolve_pinned_file(filename: str, *, local: Path|None, url: str|None, sha256: str, cache_dir: Path, allow_fetch: bool) -> Path`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_pinned_resolver.py
import hashlib
import pytest
from pathlib import Path
from polymer_claims.ingest._pinned import resolve_pinned_file, PinnedInputError

def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def test_local_dir_resolves_and_verifies(tmp_path):
    src = tmp_path / "src"; src.mkdir()
    (src / "x.bin").write_bytes(b"hello")
    out = resolve_pinned_file("x.bin", local=src, url=None, sha256=_sha(b"hello"),
                              cache_dir=tmp_path / "cache", allow_fetch=False)
    assert out.read_bytes() == b"hello"

def test_local_file_path_used_directly(tmp_path):
    f = tmp_path / "matrix.tsv.gz"; f.write_bytes(b"data")
    out = resolve_pinned_file("matrix.tsv.gz", local=f, url=None, sha256=_sha(b"data"),
                              cache_dir=tmp_path / "cache", allow_fetch=False)
    assert out == f

def test_cache_hit(tmp_path):
    cache = tmp_path / "cache"; cache.mkdir()
    (cache / "y.bin").write_bytes(b"world")
    out = resolve_pinned_file("y.bin", local=None, url=None, sha256=_sha(b"world"),
                              cache_dir=cache, allow_fetch=False)
    assert out == cache / "y.bin"

def test_sha_mismatch_raises(tmp_path):
    src = tmp_path / "s"; src.mkdir(); (src / "z.bin").write_bytes(b"abc")
    with pytest.raises(PinnedInputError, match="sha256 mismatch"):
        resolve_pinned_file("z.bin", local=src, url=None, sha256=_sha(b"different"),
                            cache_dir=tmp_path / "c", allow_fetch=False)

def test_absent_without_fetch_is_actionable(tmp_path):
    with pytest.raises(PinnedInputError, match="--fetch"):
        resolve_pinned_file("missing.bin", local=None, url="https://example/missing.bin",
                            sha256=_sha(b""), cache_dir=tmp_path / "c", allow_fetch=False)

def test_lfs_pointer_detected(tmp_path):
    src = tmp_path / "s"; src.mkdir()
    (src / "p.bin").write_bytes(b"version https://git-lfs.github.com/spec/v1\n")
    with pytest.raises(PinnedInputError, match="pointer"):
        resolve_pinned_file("p.bin", local=src, url=None, sha256="deadbeef",
                            cache_dir=tmp_path / "c", allow_fetch=False)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_pinned_resolver.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'polymer_claims.ingest._pinned'`

- [ ] **Step 3: Write the implementation**

```python
# src/polymer_claims/ingest/_pinned.py
"""Resolve a pinned external input (local file/dir -> cache -> opt-in fetch) and verify its SHA-256.
Used by the real-data kernel parity gate for the Xena matrix and the cBioPortal inputs. Fetch is
opt-in (network only when allow_fetch=True). See
docs/superpowers/specs/2026-06-25-h01b-real-kernel-parity-design.md §3."""
from __future__ import annotations

import hashlib
import os
import shutil
import tempfile
import urllib.request
from pathlib import Path

_LFS_POINTER = b"version https://git-lfs"
_HTML_SNIFF = (b"<!doctype html", b"<html")


class PinnedInputError(RuntimeError):
    """A pinned input could not be resolved or failed verification."""


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _looks_like_pointer(path: Path) -> bool:
    with open(path, "rb") as fh:
        head = fh.read(64).lstrip().lower()
    return head.startswith(_LFS_POINTER) or any(head.startswith(s) for s in _HTML_SNIFF)


def _verify(path: Path, sha256: str, filename: str, *, cleanup_on_fail: bool = False) -> Path:
    if _looks_like_pointer(path):
        if cleanup_on_fail:
            path.unlink(missing_ok=True)
        raise PinnedInputError(
            f"{filename}: got a git-LFS pointer or HTML page, not the data blob — fetch the raw file.")
    got = _sha256(path)
    if got != sha256:
        if cleanup_on_fail:
            path.unlink(missing_ok=True)
        raise PinnedInputError(f"{filename}: sha256 mismatch (expected {sha256}, got {got}).")
    return path


def resolve_pinned_file(
    filename: str, *, local: Path | None, url: str | None, sha256: str,
    cache_dir: Path, allow_fetch: bool,
) -> Path:
    """Return a path to `filename` whose SHA-256 == `sha256`.

    Resolution order: `local` (a file, or a dir containing `filename`) -> `cache_dir/filename`
    -> (only if allow_fetch and url) download `url` into cache atomically. Verifies SHA-256 on the
    resolved path; raises PinnedInputError on mismatch, pointer/HTML bytes, or an unresolvable input.
    """
    if local is not None:
        candidate = local if local.is_file() else local / filename
        if candidate.is_file():
            return _verify(candidate, sha256, filename)

    cached = cache_dir / filename
    if cached.is_file():
        return _verify(cached, sha256, filename)

    if not (allow_fetch and url):
        raise PinnedInputError(
            f"{filename}: not found locally or in cache ({cache_dir}). Supply it via "
            f"--xena/--cbioportal, or pass --fetch to download from {url!r}.")

    cache_dir.mkdir(parents=True, exist_ok=True)
    # unique temp name so concurrent runs don't trample each other (spec §3: atomic .part-<n>)
    fd, tmp_name = tempfile.mkstemp(prefix=f"{filename}.part-", dir=cache_dir)
    os.close(fd)
    tmp = Path(tmp_name)
    with urllib.request.urlopen(url) as resp, open(tmp, "wb") as out:  # noqa: S310 (pinned + sha-verified)
        shutil.copyfileobj(resp, out)
    _verify(tmp, sha256, filename, cleanup_on_fail=True)
    os.replace(tmp, cached)  # atomic: only a verified file lands at the final name
    return cached
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_pinned_resolver.py -v`
Expected: PASS (6 passed)

- [ ] **Step 5: Commit**

```bash
git add src/polymer_claims/ingest/_pinned.py tests/test_pinned_resolver.py
git commit -m "feat(ingest): pinned-input resolver (local/cache/opt-in fetch + sha256 verify)"
```

---

### Task 2: Real `@2` contract builder

**Files:**
- Create: `src/polymer_claims/ingest/tcga_xena.py`
- Test: `tests/test_tcga_xena_builder.py`

**Interfaces:**
- Consumes: `polymer_claims.ingest.transform.case_id`, `_is_idh_hotspot`; `polymer_claims._hashing.canonical_sha256`; `polymer_claims.contracts.{load_contract, using_contract_root, clear_contract_cache}`.
- Produces: `RealBuildResult` (frozen dataclass: `uid, idh_mut_n, wt_n, n_probes, group_digest, idh_call_source, dropped_ungenotyped_n`); `build_real_contract(root, xena_file, *, mutations_file, sequenced_file, idh_call_source, idh_count_band=(20,50), required_idh_mut_controls=_REAL_IDH_MUT_CONTROLS) -> RealBuildResult`; `compute_canonical_checksum(root: Path) -> str`; `STEM = "tcga_laml_idh"`; `_REAL_IDH_MUT_CONTROLS: frozenset[str]`.
- **Design note (audit #1):** the builder takes **explicit `mutations_file` / `sequenced_file` paths**, not a directory. This lets the runner resolve each cBioPortal input independently (one may be local, one freshly fetched into cache) and pass the two concrete paths — no risk of reading from a directory missing one file.

This is a byte-faithful, de-hardcoded port of `data/tcga_laml/build_contract_xena.py` (absolute paths
removed; `idh_call_source` and the count-band/controls passed in instead of read from `SOURCE.txt`).

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_tcga_xena_builder.py
import gzip, json
import pytest
from pathlib import Path
from polymer_claims.ingest.tcga_xena import (
    build_real_contract, compute_canonical_checksum, RealBuildResult, STEM,
)
from polymer_claims.contracts import load_contract, using_contract_root, clear_contract_cache

# --- fixture: a tiny Xena-shaped matrix + cBioPortal stubs with a planted DM signal -------------
def _make_fixture(root: Path, *, n_probes=60, n_dm=20):
    cases = [f"TCGA-AB-{2800+i}" for i in range(8)]          # 8 patients
    idh_mut = {cases[0], cases[1], cases[2]}                 # 3 IDH-mut
    aliquots = [f"{c}-03A" for c in cases]                   # one aliquot per case
    xena = root / "matrix.tsv.gz"
    with gzip.open(xena, "wt") as fh:
        fh.write("\t".join(["probe", *aliquots]) + "\n")
        for p in range(n_probes):
            row = [f"cg{p:06d}"]
            for c in cases:
                if p < n_dm:                                 # planted: IDH_mut hyper-methylated
                    v = 0.80 if c in idh_mut else 0.30
                else:
                    v = 0.50
                row.append(f"{v:.4f}")
            fh.write("\t".join(row) + "\n")
    cbio = root / "cbio"; cbio.mkdir()
    (cbio / "data_mutations.txt").write_text(
        "Hugo_Symbol\tTumor_Sample_Barcode\tHGVSp_Short\n"
        + "".join(f"IDH1\t{c}-03A\tp.R132H\n" for c in idh_mut))
    (cbio / "sequenced_samples.json").write_text(json.dumps([f"{c}-03A" for c in cases]))
    return xena, cbio

_KW = dict(idh_call_source="cbioportal:laml_tcga_pub@testcommit",
           idh_count_band=(1, 50), required_idh_mut_controls=frozenset())

def _build(out, xena, cbio, **overrides):
    """Call build_real_contract with explicit cBioPortal file paths + the synthetic-test defaults."""
    return build_real_contract(
        out, xena,
        mutations_file=cbio / "data_mutations.txt",
        sequenced_file=cbio / "sequenced_samples.json",
        **{**_KW, **overrides})

def test_builds_at2_contract_that_loads(tmp_path):
    xena, cbio = _make_fixture(tmp_path)
    out = tmp_path / "contracts"
    r = _build(out, xena, cbio)
    assert isinstance(r, RealBuildResult)
    assert r.uid == "tcga_laml_idh@2"
    assert r.idh_mut_n == 3 and r.wt_n == 5 and r.n_probes == 60
    with using_contract_root(out):
        clear_contract_cache()
        ref = load_contract("se:tcga_laml_idh@2")
        assert ref.contract_uid == "tcga_laml_idh@2"
    clear_contract_cache()

def test_ungenotyped_case_dropped_not_defaulted_wt(tmp_path):
    xena, cbio = _make_fixture(tmp_path)
    # drop one case from the sequenced list -> it must be dropped from the universe, not called WT
    seq = json.loads((cbio / "sequenced_samples.json").read_text())
    (cbio / "sequenced_samples.json").write_text(json.dumps(seq[:-1]))
    r = _build(tmp_path / "c", xena, cbio)
    assert r.idh_mut_n + r.wt_n == 7          # 8 beta cases - 1 ungenotyped
    assert r.dropped_ungenotyped_n == 1

def test_non_hotspot_variant_is_wt(tmp_path):
    xena, cbio = _make_fixture(tmp_path)
    (cbio / "data_mutations.txt").write_text(
        "Hugo_Symbol\tTumor_Sample_Barcode\tHGVSp_Short\n"
        "TP53\tTCGA-AB-2800-03A\tp.R175H\n")     # not an IDH hotspot
    # idh_mut_n will be 0, so the band must allow 0 (override the _KW (1,50) default)
    r = _build(tmp_path / "c", xena, cbio, idh_count_band=(0, 50))
    assert r.idh_mut_n == 0

def test_count_band_violation_aborts(tmp_path):
    xena, cbio = _make_fixture(tmp_path)
    with pytest.raises(ValueError, match="outside band"):
        _build(tmp_path / "c", xena, cbio, idh_count_band=(20, 50))

def test_missing_control_aborts(tmp_path):
    xena, cbio = _make_fixture(tmp_path)
    with pytest.raises(ValueError, match="controls not called"):
        _build(tmp_path / "c", xena, cbio, required_idh_mut_controls=frozenset({"TCGA-ZZ-9999"}))

def test_builder_is_deterministic(tmp_path):
    xena, cbio = _make_fixture(tmp_path)
    r1 = _build(tmp_path / "a", xena, cbio)
    r2 = _build(tmp_path / "b", xena, cbio)
    b1 = (tmp_path / "a" / f"{STEM}.json").read_bytes() + (tmp_path / "a" / f"{STEM}.betas.tsv").read_bytes()
    b2 = (tmp_path / "b" / f"{STEM}.json").read_bytes() + (tmp_path / "b" / f"{STEM}.betas.tsv").read_bytes()
    assert b1 == b2                                # byte-identical
    assert compute_canonical_checksum(tmp_path / "a") == compute_canonical_checksum(tmp_path / "b")
    assert r1.group_digest == r2.group_digest
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_tcga_xena_builder.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'polymer_claims.ingest.tcga_xena'`

- [ ] **Step 3: Write the implementation**

```python
# src/polymer_claims/ingest/tcga_xena.py
"""De-hardcoded builder for the real se:tcga_laml_idh@2 SE-Contract: streams a local Xena
methylation450 matrix + cBioPortal laml_tcga_pub genotyping into the contract format load_contract
reads. Byte-faithful port of data/tcga_laml/build_contract_xena.py (absolute paths removed;
idh_call_source + the count-band/controls passed in, not read from SOURCE.txt). The IDH count-band
self-check is parameterized so a tiny synthetic builder test need not manufacture 20+ IDH-mut cases.
See docs/superpowers/specs/2026-06-25-h01b-real-kernel-parity-design.md §3, §4.1."""
from __future__ import annotations

import gzip
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from polymer_claims._hashing import canonical_sha256
from polymer_claims.ingest.transform import _is_idh_hotspot, case_id

STEM = "tcga_laml_idh"
_NA = {"", "NA", "NaN", ".", "na", "null"}
# known IDH-mut hotspots present in the real betas — abort if the swap miscalls them
_REAL_IDH_MUT_CONTROLS = frozenset({"TCGA-AB-2802", "TCGA-AB-2805", "TCGA-AB-2821"})


@dataclass(frozen=True)
class RealBuildResult:
    uid: str
    idh_mut_n: int
    wt_n: int
    n_probes: int
    group_digest: str
    idh_call_source: str
    dropped_ungenotyped_n: int


def _cbio_idh_mut_cases(path: Path) -> set[str]:
    """Parse cBioPortal data_mutations.txt -> set of 12-char case ids carrying an IDH hotspot."""
    rows = [ln for ln in path.read_text().splitlines() if ln.strip() and not ln.startswith("#")]
    header = rows[0].split("\t")
    gi, bi, pi = (header.index(c) for c in ("Hugo_Symbol", "Tumor_Sample_Barcode", "HGVSp_Short"))
    mut: set[str] = set()
    for ln in rows[1:]:
        c = ln.split("\t")
        if len(c) <= max(gi, bi, pi):
            continue
        if _is_idh_hotspot(c[gi], c[pi]):
            mut.add(case_id(c[bi]))
    return mut


def build_real_contract(
    root: Path, xena_file: Path, *,
    mutations_file: Path, sequenced_file: Path,
    idh_call_source: str,
    idh_count_band: tuple[int, int] = (20, 50),
    required_idh_mut_controls: frozenset[str] = _REAL_IDH_MUT_CONTROLS,
) -> RealBuildResult:
    root = Path(root); root.mkdir(parents=True, exist_ok=True)

    # 1. matrix header -> one aliquot column per case (first occurrence).
    with gzip.open(xena_file, "rt") as fh:
        header = fh.readline().rstrip("\n").split("\t")
    case_to_col: dict[str, int] = {}
    for idx, a in enumerate(header[1:], start=1):  # col 0 is the probe id
        case_to_col.setdefault(case_id(a), idx)
    beta_cases = list(case_to_col)

    # 2. IDH calls + intersection universe (drop-not-default WT).
    idh_mut_cases = _cbio_idh_mut_cases(Path(mutations_file))
    genotyped = {case_id(s) for s in json.loads(Path(sequenced_file).read_text())}
    universe = [c for c in beta_cases if c in genotyped]
    dropped = [c for c in beta_cases if c not in genotyped]
    groups = {c: ("IDH_mut" if c in idh_mut_cases else "WT") for c in universe}
    n_idh = sum(1 for g in groups.values() if g == "IDH_mut")
    n_wt = len(universe) - n_idh

    # 3. self-checks (abort rather than write a wrong contract).
    missing = {c for c in required_idh_mut_controls if groups.get(c) != "IDH_mut"}
    if missing:
        raise ValueError(f"known IDH-mut controls not called IDH_mut: {sorted(missing)}")
    lo, hi = idh_count_band
    if not (lo <= n_idh <= hi):
        raise ValueError(f"IDH_mut count {n_idh} outside band [{lo},{hi}] — swap likely failed")
    if n_idh + n_wt != len(universe) or len(universe) + len(dropped) != len(beta_cases):
        raise ValueError("universe/drop accounting mismatch")

    # 4. provenance: group content-address.
    group_digest = hashlib.sha256("\n".join(groups[c] for c in universe).encode()).hexdigest()

    # 5. stream matrix -> betas TSV (drop probes with any NA across selected samples); verbatim vals.
    sel = [case_to_col[c] for c in universe]
    row_feature_ids: list[str] = []
    with gzip.open(xena_file, "rt") as fh, open(root / f"{STEM}.betas.tsv", "w") as out:
        fh.readline()  # skip header (already parsed)
        out.write("\t".join(["feature_id", *universe]) + "\n")
        for line in fh:
            parts = line.rstrip("\n").split("\t")
            if len(parts) <= max(sel):
                continue
            vals = [parts[i] for i in sel]
            if any(v.strip() in _NA for v in vals):
                continue
            out.write("\t".join([parts[0], *vals]) + "\n")
            row_feature_ids.append(parts[0])

    # 6. manifest in the EXACT shape/order load_contract reads (byte-faithful with the @2 artifact).
    manifest = {
        "uid": f"{STEM}@2",
        "dim": [len(row_feature_ids), len(universe)],
        "assays": [{"name": "beta", "ref": f"{STEM}.betas.tsv"}],
        "col_data": [{"sample_id": c, "Sample_Group": groups[c], "Age": None, "Sex": None} for c in universe],
        "row_data": [{"feature_id": p, "chr": "", "pos": 0} for p in row_feature_ids],
        "metadata": {
            "genome_assembly": "hg38",
            "array": "HM450",
            "idh_call_source": idh_call_source,
            "group_digest": group_digest,
            "idh_mut_n": n_idh,
            "wt_n": n_wt,
            "dropped_ungenotyped_n": len(dropped),
        },
    }
    (root / f"{STEM}.json").write_text(json.dumps(manifest))

    return RealBuildResult(
        uid=f"{STEM}@2", idh_mut_n=n_idh, wt_n=n_wt, n_probes=len(row_feature_ids),
        group_digest=group_digest, idh_call_source=idh_call_source,
        dropped_ungenotyped_n=len(dropped))


def compute_canonical_checksum(root: Path) -> str:
    """DIAGNOSTIC logical checksum (§4.1) — order/serialization-independent normal form. Computed on
    demand (only to diagnose a byte-level contract_checksum failure), never a gate. 6-decimal betas,
    keyed by sample_id in sorted-feature order; metadata/ordering excluded."""
    root = Path(root)
    manifest = json.loads((root / f"{STEM}.json").read_text())
    lines = (root / manifest["assays"][0]["ref"]).read_text().splitlines()
    samples_in_col_order = lines[0].split("\t")[1:]
    by_sample: dict[str, dict[str, float]] = {s: {} for s in samples_in_col_order}
    for ln in lines[1:]:
        cells = ln.split("\t")
        feat = cells[0]
        for s, v in zip(samples_in_col_order, cells[1:]):
            by_sample[s][feat] = round(float(v), 6)
    feature_ids = sorted(r["feature_id"] for r in manifest["row_data"])
    samples = sorted(([c["sample_id"], c["Sample_Group"]] for c in manifest["col_data"]),
                     key=lambda r: r[0])
    betas = {s: [by_sample[s][f] for f in feature_ids] for s in by_sample}
    return canonical_sha256({
        "uid": manifest["uid"], "dim": manifest["dim"],
        "features": feature_ids, "samples": samples, "betas": betas,
    })
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_tcga_xena_builder.py -v`
Expected: PASS (6 passed)

- [ ] **Step 5: Commit**

```bash
git add src/polymer_claims/ingest/tcga_xena.py tests/test_tcga_xena_builder.py
git commit -m "feat(ingest): de-hardcoded real @2 contract builder + diagnostic canonical checksum"
```

---

### Task 3: Pins manifest + loader

**Files:**
- Create: `src/polymer_claims/ingest/real_kernel_pins.json`
- Create: `src/polymer_claims/real_kernel_proof.py` (stub: `load_pins` only this task; runner added in Task 4)
- Test: `tests/test_real_kernel_pins.py`
- Modify (only if the wheel check fails): `pyproject.toml` — Hatchling ships package data files by default, so normally no change is needed (see Step 3).

**Interfaces:**
- Produces: `polymer_claims.real_kernel_proof.load_pins() -> dict`.

The JSON ships with **bootstrap-sentinel** values (`"TODO_BOOTSTRAP"`, zeros) — these are filled from
the trusted `@2` tree in Task 6, **not** plan placeholders. CI never depends on these values (it uses
synthetic test pins built in Task 4); this task only proves the file loads and has the right schema.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_real_kernel_pins.py
from polymer_claims.real_kernel_proof import load_pins

def test_pins_load_and_have_schema():
    pins = load_pins()
    assert pins["contract_uid"] == "tcga_laml_idh@2"
    inp = pins["inputs"]
    assert set(inp_key for inp_key in inp) == {"xena", "cbio_mutations", "cbio_sequenced"}
    assert inp["xena"]["filename"] == "TCGA-LAML.methylation450.tsv.gz"
    assert "sha256" in inp["xena"] and "url" in inp["xena"]
    assert inp["cbio_mutations"]["commit"]                       # datahub commit pinned
    assert inp["cbio_sequenced"]["api_endpoint"].startswith("https://")
    exp = pins["expected"]
    for key in ("contract_uid", "contract_checksum", "canonical_checksum", "dimnames_hash",
                "group_digest", "idh_mut_n", "wt_n", "n_probes", "n_dmps", "e_value",
                "profile_hash", "semantic_run_id", "status", "independence_tier"):
        assert key in exp, key
    assert exp["status"] == "licensed" and exp["independence_tier"] == "reproduced"   # lowercase values
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_real_kernel_pins.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'polymer_claims.real_kernel_proof'`

- [ ] **Step 3: Create the pins file, the loader stub, and ensure packaging**

```json
// src/polymer_claims/ingest/real_kernel_pins.json
{
  "_bootstrap": "Sentinel pins. Capture real values from the trusted @2 tree via scripts/bootstrap_real_kernel_pins.py (spec §6) and commit before the real gate can pass. CI does NOT use these values.",
  "contract_uid": "tcga_laml_idh@2",
  "inputs": {
    "xena": {
      "filename": "TCGA-LAML.methylation450.tsv.gz",
      "sha256": "TODO_BOOTSTRAP",
      "bytes": 0,
      "url": "https://gdc-hub.s3.us-east-1.amazonaws.com/download/TCGA-LAML.methylation450.tsv.gz"
    },
    "cbio_mutations": {
      "commit": "86690e1ed9752b1dcd50b5657f5f05eafa4b6b78",
      "url": "https://raw.githubusercontent.com/cBioPortal/datahub/86690e1ed9752b1dcd50b5657f5f05eafa4b6b78/public/laml_tcga_pub/data_mutations.txt",
      "filename": "data_mutations.txt",
      "sha256": "TODO_BOOTSTRAP"
    },
    "cbio_sequenced": {
      "api_endpoint": "https://www.cbioportal.org/api/sample-lists/laml_tcga_pub_sequenced/sample-ids",
      "filename": "sequenced_samples.json",
      "sha256": "TODO_BOOTSTRAP"
    }
  },
  "expected": {
    "contract_uid": "tcga_laml_idh@2",
    "contract_checksum": "TODO_BOOTSTRAP",
    "canonical_checksum": "TODO_BOOTSTRAP",
    "dimnames_hash": "TODO_BOOTSTRAP",
    "group_digest": "TODO_BOOTSTRAP",
    "idh_mut_n": 0,
    "wt_n": 0,
    "n_probes": 0,
    "n_dmps": 0,
    "e_value": "inf",
    "profile_hash": "TODO_BOOTSTRAP",
    "semantic_run_id": "TODO_BOOTSTRAP",
    "status": "licensed",
    "independence_tier": "reproduced"
  }
}
```

```python
# src/polymer_claims/real_kernel_proof.py
"""Real-data kernel parity gate. This module's run_real_kernel_proof (Task 4) resolves the three
pinned inputs, rebuilds se:tcga_laml_idh@2 into a temp contract root, asserts content-address parity
vs the committed pins, runs the REAL n-DMP gate, and requires LICENSED @ REPRODUCED. It proves the
pinned real-data computation reproduces — NOT data veracity (spec §0)."""
from __future__ import annotations

import json
from importlib.resources import files


def load_pins() -> dict:
    """Load the committed reference pins (real_kernel_pins.json), via importlib.resources so an
    installed package resolves it cleanly."""
    return json.loads(
        files("polymer_claims.ingest").joinpath("real_kernel_pins.json").read_text())
```

Confirm packaging includes the JSON. This repo uses **Hatchling** (`pyproject.toml` →
`build-backend = "hatchling.build"`, `[tool.hatch.build.targets.wheel] packages = ["src/polymer_claims"]`).
Hatchling includes **all** files under a selected package directory by default (not just `*.py`) — the
repo already relies on this for `src/polymer_claims/contracts/*.json`, so `ingest/real_kernel_pins.json`
ships automatically with **no pyproject change**. Verify rather than assume:

```bash
.venv/bin/python -m build --wheel 2>/dev/null && \
  unzip -l dist/polymer_claims-*.whl | grep real_kernel_pins.json
```
Expected: the JSON appears in the wheel listing. (If `build` is unavailable, `uv build --wheel` works too.)
If it is somehow absent, add `[tool.hatch.build.targets.wheel.force-include]` with
`"src/polymer_claims/ingest/real_kernel_pins.json" = "polymer_claims/ingest/real_kernel_pins.json"`.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_real_kernel_pins.py -v`
Expected: PASS (1 passed)

- [ ] **Step 5: Commit**

```bash
git add src/polymer_claims/ingest/real_kernel_pins.json src/polymer_claims/real_kernel_proof.py tests/test_real_kernel_pins.py
git add pyproject.toml 2>/dev/null || true   # only if the wheel check required a force-include
git commit -m "feat(repro): real_kernel_pins.json (bootstrap sentinels) + load_pins via importlib.resources"
```

---

### Task 4: Parity runner (`run_real_kernel_proof`)

**Files:**
- Modify: `src/polymer_claims/real_kernel_proof.py`
- Test: `tests/test_real_kernel_proof.py`

**Interfaces:**
- Consumes: `resolve_pinned_file`, `build_real_contract`, `compute_canonical_checksum`, `load_contract`/`using_contract_root`/`clear_contract_cache`, the n-DMP gate machinery, `Status`, `IndependenceTier`.
- Produces: `ParityError(RuntimeError)`; `RealKernelProofResult` (frozen: `status, independence_tier, n_dmps, e_value, n_probes, k, licensed`); `run_real_kernel_proof(xena_file, cbioportal_dir, *, pins, cache_dir, allow_fetch=False, idh_count_band=(20,50), required_idh_mut_controls=None) -> RealKernelProofResult`.

- [ ] **Step 1: Write the failing tests**

These tests exercise the full machinery on the tiny synthetic fixture (no real data): build a
contract, capture the observed content-addresses + gate results into a `pins` dict, assert the runner
passes, then perturb individual pins to assert each failure branch.

```python
# tests/test_real_kernel_proof.py
import math
import pytest
from pathlib import Path
from polymer_claims.real_kernel_proof import run_real_kernel_proof, ParityError, RealKernelProofResult
from polymer_grammar import Status
from tests.test_tcga_xena_builder import _make_fixture, _KW   # reuse the fixture generator

_BAND = (1, 50)

def _capture_pins(tmp_path) -> tuple[dict, Path, Path]:
    """Build once via the runner's own machinery to capture truthful pins for this fixture."""
    import hashlib, json
    from polymer_claims.contracts import load_contract, using_contract_root, clear_contract_cache
    from polymer_claims.ingest.tcga_xena import build_real_contract, compute_canonical_checksum
    xena, cbio = _make_fixture(tmp_path)
    out = tmp_path / "cap"
    r = build_real_contract(out, xena, mutations_file=cbio / "data_mutations.txt",
                            sequenced_file=cbio / "sequenced_samples.json", **_KW)
    with using_contract_root(out):
        clear_contract_cache()
        ref = load_contract("se:tcga_laml_idh@2")
        # run the gate the same way the runner will, to capture n_dmps/e_value/materialization
        from polymer_claims.real_kernel_proof import _run_gate_capture  # test-only helper exposed below
        gate = _run_gate_capture()
    clear_contract_cache()
    pins = {
        "contract_uid": "tcga_laml_idh@2",
        "inputs": {
            "xena": {"filename": "matrix.tsv.gz", "sha256": hashlib.sha256(xena.read_bytes()).hexdigest(), "url": None},
            "cbio_mutations": {"commit": "testcommit", "filename": "data_mutations.txt",
                               "sha256": hashlib.sha256((cbio / "data_mutations.txt").read_bytes()).hexdigest(), "url": None},
            "cbio_sequenced": {"api_endpoint": None, "filename": "sequenced_samples.json",
                               "sha256": hashlib.sha256((cbio / "sequenced_samples.json").read_bytes()).hexdigest()},
        },
        "expected": {
            "contract_uid": "tcga_laml_idh@2",
            "contract_checksum": ref.checksums[0].checksum,
            "canonical_checksum": compute_canonical_checksum(out),
            "dimnames_hash": ref.dimnames_hash,
            "group_digest": r.group_digest,
            "idh_mut_n": r.idh_mut_n, "wt_n": r.wt_n, "n_probes": r.n_probes,
            "n_dmps": gate["n_dmps"],
            "e_value": "inf" if math.isinf(gate["e_value"]) else repr(gate["e_value"]),
            "profile_hash": gate["profile_hash"], "semantic_run_id": gate["semantic_run_id"],
            "status": gate["status"], "independence_tier": gate["independence_tier"],
        },
    }
    return pins, xena, cbio

def test_parity_passes_on_faithful_rebuild(tmp_path):
    pins, xena, cbio = _capture_pins(tmp_path)
    res = run_real_kernel_proof(xena, cbio, pins=pins, cache_dir=tmp_path / "cache",
                                allow_fetch=False, idh_count_band=_BAND,
                                required_idh_mut_controls=frozenset())
    assert isinstance(res, RealKernelProofResult)
    assert res.licensed and res.status is Status.LICENSED

def test_contract_checksum_perturbation_is_named(tmp_path):
    pins, xena, cbio = _capture_pins(tmp_path)
    pins["expected"]["contract_checksum"] = "0" * 64
    pins["expected"]["canonical_checksum"] = "sha256:deadbeef"   # also wrong -> "content diverged"
    with pytest.raises(ParityError, match="content itself diverged"):
        run_real_kernel_proof(xena, cbio, pins=pins, cache_dir=tmp_path / "c2",
                              allow_fetch=False, idh_count_band=_BAND, required_idh_mut_controls=frozenset())

def test_serialization_only_divergence_is_distinguished(tmp_path):
    pins, xena, cbio = _capture_pins(tmp_path)
    pins["expected"]["contract_checksum"] = "0" * 64            # byte-level wrong
    # canonical_checksum left correct -> builder-not-byte-faithful branch
    with pytest.raises(ParityError, match="serialization differs"):
        run_real_kernel_proof(xena, cbio, pins=pins, cache_dir=tmp_path / "c3",
                              allow_fetch=False, idh_count_band=_BAND, required_idh_mut_controls=frozenset())

def test_version_identity_checked_first(tmp_path):
    pins, xena, cbio = _capture_pins(tmp_path)
    pins["expected"]["contract_uid"] = "tcga_laml_idh@1"
    with pytest.raises(ParityError, match="contract_uid"):
        run_real_kernel_proof(xena, cbio, pins=pins, cache_dir=tmp_path / "c4",
                              allow_fetch=False, idh_count_band=_BAND, required_idh_mut_controls=frozenset())

def test_evalue_inf_rule(tmp_path):
    pins, xena, cbio = _capture_pins(tmp_path)
    if pins["expected"]["e_value"] == "inf":
        pins["expected"]["e_value"] = "123.0"                  # finite pin vs observed inf -> mismatch
        with pytest.raises(ParityError, match="e_value"):
            run_real_kernel_proof(xena, cbio, pins=pins, cache_dir=tmp_path / "c5",
                                  allow_fetch=False, idh_count_band=_BAND, required_idh_mut_controls=frozenset())
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_real_kernel_proof.py -v`
Expected: FAIL with `ImportError: cannot import name 'run_real_kernel_proof'` (and `_run_gate_capture`)

- [ ] **Step 3: Add the runner + the test-only gate-capture helper**

Append to `src/polymer_claims/real_kernel_proof.py`:

```python
import math
import tempfile
from dataclasses import dataclass
from pathlib import Path

from polymer_grammar import FDRLedger, MaterializationContext, Status
from polymer_grammar.licensing import IndependenceTier
from polymer_protocol import Corpus, run_cycle

from polymer_claims.analysis_profile import profile_oracle_id, profile_oracle_registry
from polymer_claims.contracts import clear_contract_cache, load_contract, using_contract_root
from polymer_claims.evidence import count_enrichment_evalue
from polymer_claims.ingest._pinned import resolve_pinned_file
from polymer_claims.ingest.tcga_xena import build_real_contract, compute_canonical_checksum
from polymer_claims.materialization import materialization_map
from polymer_claims.methyl_ndmp import (
    NDmpOlsCoefAdapter, NDmpTTestAdapter, _all_probe_ids, dmp_indicators,
    n_dmps_claim, ndmp_independent_registry,
)
from polymer_claims.profiles import CANONICAL_HM450_V1

_REF = "se:tcga_laml_idh@2"
_ALPHA = 0.05
_CLAIM_ID = "tcga-laml-ndmp"


class ParityError(RuntimeError):
    """A rebuilt content-address did not match its pin (the kernel did not reproduce)."""


@dataclass(frozen=True)
class RealKernelProofResult:
    status: Status
    independence_tier: object | None
    n_dmps: int
    e_value: float
    n_probes: int
    k: int
    licensed: bool


def _assert(name: str, expected, observed) -> None:
    if expected != observed:
        raise ParityError(f"parity mismatch [{name}]: expected {expected!r}, got {observed!r}")


def _assert_evalue(expected, observed: float) -> None:
    if expected == "inf":
        if not (math.isinf(observed) and observed > 0):
            raise ParityError(f"parity mismatch [e_value]: expected +inf, got {observed!r}")
        return
    exp = float(expected)
    if observed != exp and abs(observed - exp) > abs(exp) * 1e-12:
        raise ParityError(f"parity mismatch [e_value]: expected {expected}, got {observed!r}")


def _build_claim_and_run_gate() -> dict:
    """Fixed claim construction (spec §4.4) + the real gate, scoped to the active contract root.
    Returns the observed gate quantities. Probes default to ALL (_all_probe_ids) via probes=None."""
    n_probes = len(_all_probe_ids(_REF))
    k = math.ceil(_ALPHA * n_probes)
    claim = n_dmps_claim(
        _CLAIM_ID, ref=_REF, group_col="Sample_Group", level_a="WT", level_b="IDH_mut",
        alpha=_ALPHA, k=k, oracle_ref=profile_oracle_id(CANONICAL_HM450_V1))
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
        evidence={_CLAIM_ID: evalue})
    c = next(x for x in result.corpus.claims if x.id == _CLAIM_ID)
    tier = c.licensing.independence_tier if c.licensing is not None else None
    profile_hash = semantic_run_id = None
    if c.licensing is not None and c.licensing.satisfactions:
        m = c.licensing.satisfactions[0].materialization
        profile_hash, semantic_run_id = m.profile_hash, m.semantic_run_id
    return {
        "n_probes": n_probes, "k": k, "n_dmps": n_dmps, "e_value": evalue,
        "status_enum": c.status, "tier_enum": tier,
        "status": c.status.value, "independence_tier": tier.value if tier is not None else None,
        "profile_hash": profile_hash, "semantic_run_id": semantic_run_id,
    }


def _run_gate_capture() -> dict:
    """Test-only convenience: run the gate under the already-active contract root and return the
    captured quantities (used by tests to build truthful pins for a synthetic fixture)."""
    return _build_claim_and_run_gate()


def run_real_kernel_proof(
    xena_file: Path | None, cbioportal_dir: Path | None, *,
    pins: dict, cache_dir: Path, allow_fetch: bool = False,
    idh_count_band: tuple[int, int] = (20, 50),
    required_idh_mut_controls: frozenset[str] | None = None,
) -> RealKernelProofResult:
    inp = pins["inputs"]
    cache_dir = Path(cache_dir)
    # resolve each input independently and keep the concrete returned paths (audit #1): a local dir
    # missing one file + --fetch retrieving the other must not silently read the wrong directory.
    xena = resolve_pinned_file(
        inp["xena"]["filename"], local=xena_file, url=inp["xena"].get("url"),
        sha256=inp["xena"]["sha256"], cache_dir=cache_dir, allow_fetch=allow_fetch)
    mutations_file = resolve_pinned_file(
        inp["cbio_mutations"]["filename"], local=cbioportal_dir, url=inp["cbio_mutations"].get("url"),
        sha256=inp["cbio_mutations"]["sha256"], cache_dir=cache_dir, allow_fetch=allow_fetch)
    sequenced_file = resolve_pinned_file(
        inp["cbio_sequenced"]["filename"], local=cbioportal_dir,
        url=inp["cbio_sequenced"].get("api_endpoint"), sha256=inp["cbio_sequenced"]["sha256"],
        cache_dir=cache_dir, allow_fetch=allow_fetch)
    idh_call_source = f"cbioportal:laml_tcga_pub@{inp['cbio_mutations']['commit']}"
    exp = pins["expected"]

    build_kw = {"mutations_file": mutations_file, "sequenced_file": sequenced_file,
                "idh_call_source": idh_call_source, "idh_count_band": idh_count_band}
    if required_idh_mut_controls is not None:
        build_kw["required_idh_mut_controls"] = required_idh_mut_controls

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        rbr = build_real_contract(root, xena, **build_kw)
        with using_contract_root(root):
            clear_contract_cache()
            ref = load_contract(_REF)
            # --- version identity first (§4.3) ---
            _assert("contract_uid", exp["contract_uid"], ref.contract_uid)
            # --- byte-level primary gate, with canonical diagnostic branch (§4.1) ---
            if ref.checksums[0].checksum != exp["contract_checksum"]:
                if compute_canonical_checksum(root) == exp["canonical_checksum"]:
                    raise ParityError(
                        "parity mismatch [contract_checksum]: bytes differ but canonical_checksum "
                        "matches — logical content reproduced, serialization differs (builder not "
                        "byte-faithful)")
                raise ParityError(
                    "parity mismatch [contract_checksum]: bytes differ and canonical_checksum "
                    "differs — contract content itself diverged")
            # --- localized diagnostics ---
            _assert("dimnames_hash", exp["dimnames_hash"], ref.dimnames_hash)
            _assert("group_digest", exp["group_digest"], rbr.group_digest)
            _assert("idh_mut_n", exp["idh_mut_n"], rbr.idh_mut_n)
            _assert("wt_n", exp["wt_n"], rbr.wt_n)
            _assert("n_probes", exp["n_probes"], rbr.n_probes)
            # --- gate + gate-result parity ---
            gate = _build_claim_and_run_gate()
            _assert("n_dmps", exp["n_dmps"], gate["n_dmps"])
            _assert_evalue(exp["e_value"], gate["e_value"])
            _assert("profile_hash", exp["profile_hash"], gate["profile_hash"])
            _assert("semantic_run_id", exp["semantic_run_id"], gate["semantic_run_id"])
            _assert("status", exp["status"], gate["status"])
            _assert("independence_tier", exp["independence_tier"], gate["independence_tier"])
        clear_contract_cache()

    return RealKernelProofResult(
        status=gate["status_enum"], independence_tier=gate["tier_enum"], n_dmps=gate["n_dmps"],
        e_value=gate["e_value"], n_probes=gate["n_probes"], k=gate["k"],
        licensed=(gate["status_enum"] is Status.LICENSED))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_real_kernel_proof.py -v`
Expected: PASS (5 passed). If `test_evalue_inf_rule` skips its body, that means the synthetic fixture
yields a finite e-value — that is acceptable (the inf branch is unit-tested via `_assert_evalue`
directly; add `from polymer_claims.real_kernel_proof import _assert_evalue` and a 2-line test asserting
`_assert_evalue("inf", math.inf)` passes and `_assert_evalue("inf", 1.0)` raises).

- [ ] **Step 5: Commit**

```bash
git add src/polymer_claims/real_kernel_proof.py tests/test_real_kernel_proof.py
git commit -m "feat(repro): run_real_kernel_proof parity gate (byte/canonical/version/gate-result asserts)"
```

---

### Task 5: CLI wiring (`verify-kernel --real`)

**Files:**
- Modify: `src/polymer_claims/cli.py` (`_cmd_verify_kernel` ~308-329; parser block ~821-823)
- Test: `tests/test_cli_verify_kernel_real.py`

**Interfaces:**
- Consumes: `run_real_kernel_proof`, `load_pins`, `ParityError`, `PinnedInputError`.
- Produces: `verify-kernel --real [--xena PATH] [--cbioportal PATH] [--cache-dir PATH] [--fetch]`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_cli_verify_kernel_real.py
from polymer_claims.cli import _build_parser, main

def test_real_flags_parse():
    p = _build_parser()
    ns = p.parse_args(["verify-kernel", "--real", "--xena", "/tmp/m.gz",
                       "--cbioportal", "/tmp/cbio", "--cache-dir", "/tmp/cache", "--fetch"])
    assert ns.real and ns.xena == "/tmp/m.gz" and ns.cbioportal == "/tmp/cbio"
    assert ns.cache_dir == "/tmp/cache" and ns.fetch is True

def test_real_without_inputs_errors_actionably(tmp_path, capsys):
    rc = main(["verify-kernel", "--real", "--cache-dir", str(tmp_path / "empty")])
    assert rc == 1
    err = capsys.readouterr().err
    assert "--fetch" in err or "not found" in err            # actionable PinnedInputError surfaced

def test_synthetic_path_unchanged(capsys):
    rc = main(["verify-kernel"])                              # no --real
    out = capsys.readouterr().out
    assert "synthetic" in out.lower()
    assert rc in (0, 1)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_cli_verify_kernel_real.py -v`
Expected: FAIL — `--real` is an unrecognized argument (parser not yet extended).

- [ ] **Step 3: Extend the parser and command handler**

In `_build_parser`, replace the `p_vk` block (currently lines ~821-823):

```python
    p_vk = sub.add_parser("verify-kernel",
                          help="run the n-DMP kernel proof (synthetic offline by default; --real for the @2 parity gate)")
    p_vk.add_argument("--real", action="store_true",
                      help="run the REAL se:tcga_laml_idh@2 parity gate (needs the pinned Xena matrix + cBioPortal inputs)")
    p_vk.add_argument("--xena", default=None,
                      help="TCGA-LAML.methylation450.tsv.gz (file path, or a dir containing it)")
    p_vk.add_argument("--cbioportal", default=None,
                      help="dir holding data_mutations.txt + sequenced_samples.json")
    p_vk.add_argument("--cache-dir", default=None, help="cache dir for resolved pinned inputs")
    p_vk.add_argument("--fetch", action="store_true",
                      help="opt-in: allow network download of pinned inputs (off by default)")
    p_vk.set_defaults(func=_cmd_verify_kernel)
```

Replace `_cmd_verify_kernel` (lines ~308-329) with:

```python
def _cmd_verify_kernel(args: argparse.Namespace) -> int:
    if getattr(args, "real", False):
        return _verify_kernel_real(args)
    try:
        from .kernel_proof import run_synthetic_kernel_proof
    except ModuleNotFoundError as exc:
        if exc.name == "numpy":
            print("verify-kernel needs numpy (the n-DMP gate adapters): install it with "
                  "`pip install 'polymer-claims[calibrate]'`", file=sys.stderr)
        else:
            print(f"verify-kernel import failed: {exc}", file=sys.stderr)
        return 1
    r = run_synthetic_kernel_proof()
    tier = r.independence_tier.name if r.independence_tier is not None else "NONE"
    ok = r.licensed and tier == "REPRODUCED"
    print(f"kernel proof (synthetic, offline): {'LICENSED @ ' + tier if r.licensed else 'NOT LICENSED'}")
    print(f"  n_probes={r.n_probes}  null-floor k={r.k}  n_dmps={r.n_dmps}  e_value={r.e_value:.3e}")
    print("  (synthetic fixture — proves pipeline integrity, NOT the real biology; "
          "see docs/superpowers/2026-06-23-kernel-proof-runbook.md for the real proof)")
    return 0 if ok else 1


def _verify_kernel_real(args: argparse.Namespace) -> int:
    import os
    from pathlib import Path
    try:
        from .ingest._pinned import PinnedInputError
        from .real_kernel_proof import ParityError, load_pins, run_real_kernel_proof
    except ModuleNotFoundError as exc:
        if exc.name == "numpy":
            print("verify-kernel --real needs numpy (the n-DMP gate adapters): install it with "
                  "`pip install 'polymer-claims[calibrate]'`", file=sys.stderr)
        else:
            print(f"verify-kernel --real import failed: {exc}", file=sys.stderr)
        return 1
    pins = load_pins()
    cache_dir = Path(args.cache_dir) if args.cache_dir else (
        Path(os.environ.get("XDG_CACHE_HOME", str(Path.home() / ".cache")))
        / "polymer-claims" / "tcga_laml")
    try:
        r = run_real_kernel_proof(
            Path(args.xena) if args.xena else None,
            Path(args.cbioportal) if args.cbioportal else None,
            pins=pins, cache_dir=cache_dir, allow_fetch=args.fetch)
    except (PinnedInputError, ParityError, ValueError) as exc:
        # PinnedInputError: input resolution/checksum; ParityError: a pin mismatch;
        # ValueError: a builder self-check (controls / count-band / accounting) — all are clean failures.
        print(f"verify-kernel --real FAILED: {exc}", file=sys.stderr)
        return 1
    tier = r.independence_tier.name if r.independence_tier is not None else "NONE"
    ok = r.licensed and tier == "REPRODUCED"
    print(f"kernel proof (REAL @2): {'LICENSED @ ' + tier if r.licensed else 'NOT LICENSED'}")
    print(f"  n_probes={r.n_probes}  null-floor k={r.k}  n_dmps={r.n_dmps}  e_value={r.e_value:.3e}")
    print("  proves the pinned real-data computation reproduces — NOT data veracity / independence "
          "(that is roadmap H1.A2). See docs/superpowers/2026-06-23-kernel-proof-runbook.md")
    return 0 if ok else 1
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_cli_verify_kernel_real.py tests/test_cli_verify_kernel.py -v`
Expected: PASS (the new tests pass; the existing `test_cli_verify_kernel.py` still passes — synthetic path unchanged).

- [ ] **Step 5: Commit**

```bash
git add src/polymer_claims/cli.py tests/test_cli_verify_kernel_real.py
git commit -m "feat(cli): verify-kernel --real parity gate (opt-in fetch, actionable errors)"
```

---

### Task 6: Bootstrap script + runbook update

**Files:**
- Create: `scripts/bootstrap_real_kernel_pins.py`
- Modify: `docs/superpowers/2026-06-23-kernel-proof-runbook.md`

**Interfaces:**
- Consumes: `build_real_contract`/`compute_canonical_checksum`, `load_contract`, the gate-capture helper `_build_claim_and_run_gate`, `resolve_pinned_file` patterns.

This produces the **real** pins from the previously trusted inputs (spec §6) — run once by Z in a tree
that holds the real Xena matrix + cBioPortal inputs. It is **not** CI-tested (no real data in CI); it
is complete, runnable code. It deliberately rebuilds via the **new** `build_real_contract` from the
trusted inputs and emits the resulting addresses; Z then confirms these match the previously trusted
`@2` artifact before committing (the no-self-fulfilling-parity check is the human comparison, not the
script minting its own ground truth).

- [ ] **Step 1: Write the bootstrap script**

```python
# scripts/bootstrap_real_kernel_pins.py
"""Capture/compare real_kernel_pins.json content-addresses (spec §6). LOCAL-ONLY: run in a tree that
holds the real Xena matrix + cBioPortal inputs and the trusted local @2 contract.

Two modes, used together to AVOID self-fulfilling parity:
  --from-existing : read the addresses of the ALREADY-TRUSTED @2 contract (no rebuild) -> the ground
                    truth to compare against. Prints the `expected` block only.
  (rebuild)       : rebuild @2 with the NEW builder from the supplied inputs -> the full pins.

Procedure: run BOTH, diff their `expected` blocks; only if identical, write the rebuild output to
src/polymer_claims/ingest/real_kernel_pins.json and commit. Usage:
  .venv/bin/python scripts/bootstrap_real_kernel_pins.py --from-existing \
      --contract-root src/polymer_claims/contracts > trusted_expected.json
  .venv/bin/python scripts/bootstrap_real_kernel_pins.py \
      --xena /path/TCGA-LAML.methylation450.tsv.gz --cbioportal /path/cbio \
      --commit 86690e1ed9752b1dcd50b5657f5f05eafa4b6b78 > rebuilt_pins.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import tempfile
from pathlib import Path

from polymer_claims.contracts import clear_contract_cache, load_contract, using_contract_root
from polymer_claims.ingest.tcga_xena import STEM, build_real_contract, compute_canonical_checksum
from polymer_claims.real_kernel_proof import _build_claim_and_run_gate


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _expected_block(contract_root: Path) -> dict:
    """Compute the `expected` content-addresses from a contract root holding the @2 artifact."""
    manifest = json.loads((contract_root / f"{STEM}.json").read_text())
    meta = manifest["metadata"]
    with using_contract_root(contract_root):
        clear_contract_cache()
        ref = load_contract("se:tcga_laml_idh@2")
        canonical = compute_canonical_checksum(contract_root)
        gate = _build_claim_and_run_gate()
    clear_contract_cache()
    return {
        "contract_uid": ref.contract_uid,
        "contract_checksum": ref.checksums[0].checksum,
        "canonical_checksum": canonical,
        "dimnames_hash": ref.dimnames_hash,
        "group_digest": meta["group_digest"],
        "idh_mut_n": meta["idh_mut_n"], "wt_n": meta["wt_n"], "n_probes": manifest["dim"][0],
        "n_dmps": gate["n_dmps"],
        "e_value": "inf" if math.isinf(gate["e_value"]) else repr(gate["e_value"]),
        "profile_hash": gate["profile_hash"], "semantic_run_id": gate["semantic_run_id"],
        "status": gate["status"], "independence_tier": gate["independence_tier"],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--from-existing", action="store_true",
                    help="read the already-trusted @2 contract (no rebuild); print the expected block")
    ap.add_argument("--contract-root", type=Path, default=Path("src/polymer_claims/contracts"))
    ap.add_argument("--xena", type=Path)
    ap.add_argument("--cbioportal", type=Path)
    ap.add_argument("--commit")
    ap.add_argument("--xena-url", default="https://gdc-hub.s3.us-east-1.amazonaws.com/download/TCGA-LAML.methylation450.tsv.gz")
    ap.add_argument("--api-endpoint", default="https://www.cbioportal.org/api/sample-lists/laml_tcga_pub_sequenced/sample-ids")
    args = ap.parse_args()

    if args.from_existing:
        print(json.dumps({"expected": _expected_block(args.contract_root)}, indent=2))
        return 0

    if not (args.xena and args.cbioportal and args.commit):
        ap.error("rebuild mode needs --xena, --cbioportal, and --commit")
    idh_call_source = f"cbioportal:laml_tcga_pub@{args.commit}"
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        build_real_contract(
            root, args.xena,
            mutations_file=args.cbioportal / "data_mutations.txt",
            sequenced_file=args.cbioportal / "sequenced_samples.json",
            idh_call_source=idh_call_source)
        expected = _expected_block(root)

    pins = {
        "contract_uid": "tcga_laml_idh@2",
        "inputs": {
            "xena": {"filename": "TCGA-LAML.methylation450.tsv.gz", "sha256": _sha(args.xena),
                     "bytes": args.xena.stat().st_size, "url": args.xena_url},
            "cbio_mutations": {"commit": args.commit,
                               "url": f"https://raw.githubusercontent.com/cBioPortal/datahub/{args.commit}/public/laml_tcga_pub/data_mutations.txt",
                               "filename": "data_mutations.txt",
                               "sha256": _sha(args.cbioportal / "data_mutations.txt")},
            "cbio_sequenced": {"api_endpoint": args.api_endpoint, "filename": "sequenced_samples.json",
                               "sha256": _sha(args.cbioportal / "sequenced_samples.json")},
        },
        "expected": expected,
    }
    print(json.dumps(pins, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Update the runbook**

In `docs/superpowers/2026-06-23-kernel-proof-runbook.md`, replace the "Real proof" section's
hardcoded-path instructions with the new recipe. Add this block under the offline-synthetic section:

```markdown
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

**Bootstrapping the pins (one-time, spec §6 — no self-fulfilling parity):** `real_kernel_pins.json`
ships with sentinel values. Capture the real pins by running the script in **both** modes and diffing:

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
```

(Leave the deprecated `ingest tcga-laml` note in place; mark the old hardcoded `build_contract_xena.py`
/ `run_gate.py` paragraph as superseded by `verify-kernel --real`.)

- [ ] **Step 3: Smoke-test the script (real import + arg parsing, no real data needed)**

Run: `.venv/bin/python scripts/bootstrap_real_kernel_pins.py --help`
Expected: argparse usage text listing `--from-existing`, `--contract-root`, `--xena`, `--cbioportal`,
`--commit` — exit 0. (This actually imports the module — catching import errors `ast.parse` would
miss — and exercises the parser.)

Then confirm the rebuild-mode guard fires without inputs:
Run: `.venv/bin/python scripts/bootstrap_real_kernel_pins.py; echo "exit=$?"`
Expected: an error mentioning `--xena, --cbioportal, and --commit` and a non-zero exit.

- [ ] **Step 4: Run the full suite**

Run: `.venv/bin/python -m pytest tests/test_pinned_resolver.py tests/test_tcga_xena_builder.py tests/test_real_kernel_pins.py tests/test_real_kernel_proof.py tests/test_cli_verify_kernel_real.py tests/test_cli_verify_kernel.py tests/test_kernel_proof_synthetic.py -v`
Expected: PASS (all)

- [ ] **Step 5: Commit**

```bash
git add scripts/bootstrap_real_kernel_pins.py docs/superpowers/2026-06-23-kernel-proof-runbook.md
git commit -m "feat(repro): bootstrap script for real pins + verify-kernel --real runbook"
```

---

## Self-Review

**Spec coverage:**
- §2.1 deliverable (verify-kernel --real) → Task 5. §2.2 full-content parity → Task 4 (`contract_checksum` primary). §2.3 input acquisition → Task 1. §2.4 governance (no committed data) → pins-only (Task 3). §2.5 module split + importlib.resources → Tasks 2/3/4.
- §3 components: `_pinned.py` (T1), `tcga_xena.py` (T2), `real_kernel_pins.json` (T3), `real_kernel_proof.py` (T4), CLI (T5). Deprecation of old scripts → runbook note (T6).
- §4.1 byte+canonical → T2 (`compute_canonical_checksum`) + T4 (branch). §4.2 inf rule → T4 (`_assert_evalue`). §4.3 version identity → T4 (first assert). §4.4 fixed claim construction → T4 (`_build_claim_and_run_gate`, `probes=None`).
- §5 data flow → T4 runner order. §6 bootstrap → T6 script + runbook. §7 error handling → T1 (resolver msgs) + T4 (named parity errors) + T5 (surfaced). §8 tests → T1/T2/T4/T5 (IDH grouping in T2, resolver in T1, parity branches in T4, CLI in T5). §10 acceptance → covered across tasks; criterion #5 (pins from trusted artifact) is the T6 bootstrap + human confirmation.

**Placeholder scan:** The only `TODO_BOOTSTRAP`/zero values are inside `real_kernel_pins.json`, which
is a deliberate spec-defined bootstrap artifact (§6) filled in Task 6, not a plan gap — every plan step
shows complete code/commands.

**Type consistency:** `resolve_pinned_file` signature identical across T1/T4/T6. `build_real_contract`
takes explicit `mutations_file` / `sequenced_file` (keyword-only) plus `idh_call_source`,
`idh_count_band`, `required_idh_mut_controls` — consistent across T2 (impl + `_build` helper), T4
(runner passes the resolved paths), and T6 (bootstrap + `_expected_block`).
`RealBuildResult` fields used in T4/T6 match T2. `_build_claim_and_run_gate` return keys
(`n_dmps, e_value, status, independence_tier, profile_hash, semantic_run_id, status_enum, tier_enum,
n_probes, k`) consistent T4/T6. Pins schema identical T3/T4/T6. Enum pins lowercase `.value`
throughout.
