# CES-1 — Data Seam Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `DataHandle.ref` resolve (umbrella-side) to a frozen, DRS-shaped, content-addressed `SEContractRef` over a bundled EPICv2-shaped methylation fixture — the data seam, no computation or licensing.

**Architecture:** Pure-umbrella addition mirroring `datasets/load_dataset` and `profiles/load_profile`. New `src/polymer_claims/contracts/` package holds the frozen `SEContractRef` model, a `load_contract` resolver, and a bundled fixture (manifest JSON + sidecar betas TSV). A shared `canonical_sha256` helper (extracted from CES-0's `content_hash`) computes the canonical `dimnames_hash`. Grammar and protocol are untouched; `DataHandle.ref` stays a thin `str`.

**Tech Stack:** Python 3, Pydantic v2 (frozen models), pytest, uv (umbrella project at repo root), ruff. Pure stdlib I/O (`json`, `csv`, `hashlib`, `functools.lru_cache`).

**Spec:** `docs/specs/2026-06-11-ces-1-data-seam-design.md`
**Branch:** continue on `feat/m1-structural-equivalence-status` (work is being stacked; nothing merged yet).
**Run umbrella tests from the repo root:** `uv run --project . pytest tests/ -q`

---

## File Structure

| File | Responsibility | Change |
|---|---|---|
| `src/polymer_claims/_hashing.py` | one canonical content-address primitive for the whole umbrella | Create: `canonical_sha256(obj) -> str` |
| `src/polymer_claims/analysis_profile.py` | CES-0 profile + `content_hash` | Modify: `content_hash` reuses `canonical_sha256` (DRY) |
| `src/polymer_claims/contracts/__init__.py` | the data seam: `SEContractRef` model + `load_contract` resolver + `dimnames_hash` | Create |
| `src/polymer_claims/contracts/groupdiff_epicv2_demo.json` | bundled SE-Contract manifest (50×8, EPICv2-shaped) | Create (generated) |
| `src/polymer_claims/contracts/groupdiff_epicv2_demo.betas.tsv` | bundled beta matrix (synthetic, planted shift) | Create (generated) |
| `src/polymer_claims/contracts/_make_fixture.py` | deterministic one-off generator for the two fixture files | Create |
| `src/polymer_claims/__init__.py` | umbrella public surface | Modify: re-export the new symbols |
| `tests/test_hashing.py` | the shared hash primitive | Create |
| `tests/test_contracts_fixture.py` | fixture-on-disk consistency (raw-file read, no loader) | Create |
| `tests/test_contracts_loader.py` | `load_contract` + `dimnames_hash` + DRS shape | Create |

`grammar/` and `protocol/` are **not touched** (scope fence). `exec_adapters.py` is **not touched** (the `dose_response` path is CES-2's concern).

---

## Task 1: Shared canonical-hash primitive (DRY the content-address)

**Files:**
- Create: `src/polymer_claims/_hashing.py`
- Modify: `src/polymer_claims/analysis_profile.py:84-89`
- Test: `tests/test_hashing.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_hashing.py`:

```python
from __future__ import annotations

from polymer_claims._hashing import canonical_sha256


def test_canonical_sha256_is_deterministic_and_prefixed():
    h1 = canonical_sha256({"b": 2, "a": 1})
    h2 = canonical_sha256({"a": 1, "b": 2})  # key order must not matter
    assert h1 == h2
    assert h1.startswith("sha256:")
    assert len(h1) == len("sha256:") + 64  # hex digest


def test_canonical_sha256_is_content_sensitive():
    assert canonical_sha256({"a": 1}) != canonical_sha256({"a": 2})


def test_canonical_sha256_matches_inline_recipe():
    import hashlib
    import json
    obj = {"feature_ids": ["cg1", "cg2"], "sample_ids": ["S1"]}
    expected = "sha256:" + hashlib.sha256(
        json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    assert canonical_sha256(obj) == expected
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/zbb2/Desktop/polymer-claims && uv run --project . pytest tests/test_hashing.py -q`
Expected: FAIL — `ModuleNotFoundError: polymer_claims._hashing`.

- [ ] **Step 3: Create the helper**

Create `src/polymer_claims/_hashing.py`:

```python
"""The single canonical content-address primitive for the umbrella package.

Sorted-keys / no-whitespace JSON -> SHA256, prefixed 'sha256:'. This mirrors Polymer's
SemanticRunID.param_signature canonicalization (the intended basis for Python/R hash parity),
and is reused by both `analysis_profile.content_hash` (the profile address) and
`contracts.load_contract` (the dimnames_hash). One recipe, one place.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any


def canonical_sha256(obj: Any) -> str:
    canonical = json.dumps(obj, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()
```

- [ ] **Step 4: Refactor `content_hash` to use it (DRY)**

In `src/polymer_claims/analysis_profile.py`, replace the body of `content_hash` (lines 84-89) so it delegates to the shared helper. Remove the now-unused `hashlib`/`json` imports **only if** nothing else in the file uses them (check first; if used elsewhere, leave them):

```python
from polymer_claims._hashing import canonical_sha256


def content_hash(profile: AnalysisProfile) -> str:
    """Canonical content-address of the whole pinned regime. Sorted-keys/no-whitespace JSON
    (Polymer SemanticRunID parity) -> SHA256, prefixed 'sha256:'."""
    return canonical_sha256(profile.model_dump(mode="json"))
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run --project . pytest tests/test_hashing.py tests/test_analysis_profile.py -q`
Expected: PASS — the new hashing tests AND every existing `test_analysis_profile.py` test (proves `content_hash` output is byte-identical after the refactor).

- [ ] **Step 6: Commit**

```bash
git add src/polymer_claims/_hashing.py src/polymer_claims/analysis_profile.py tests/test_hashing.py
git commit -m "feat(umbrella): shared canonical_sha256 helper; content_hash reuses it (CES-1 prep)"
```

---

## Task 2: The `SEContractRef` model (+ `AccessMethod`, `Checksum`)

**Files:**
- Create: `src/polymer_claims/contracts/__init__.py` (model only this task; loader added in Task 4)
- Test: `tests/test_contracts_loader.py` (model round-trip portion)

- [ ] **Step 1: Write the failing test**

Create `tests/test_contracts_loader.py`:

```python
from __future__ import annotations

import pytest

from polymer_claims.contracts import AccessMethod, Checksum, SEContractRef


def _ref(**kw) -> SEContractRef:
    base = dict(
        contract_uid="groupdiff_epicv2_demo@1",
        dimnames_hash="sha256:" + "0" * 64,
        assay="beta",
        selection=(("group_col", "Sample_Group"),),
        genome_assembly="hg38",
        self_uri="drs://local/groupdiff_epicv2_demo@1",
        size=123,
        checksums=(Checksum(checksum="ab" * 32),),
        access_methods=(AccessMethod(type="file", access_url="/x/y.tsv"),),
    )
    base.update(kw)
    return SEContractRef(**base)


def test_se_contract_ref_round_trips():
    ref = _ref()
    again = SEContractRef.model_validate(ref.model_dump(mode="json"))
    assert again == ref
    assert again.refget_digest is None  # noted-but-empty slot


def test_se_contract_ref_is_frozen():
    ref = _ref()
    with pytest.raises(Exception):
        ref.assay = "counts"  # frozen models reject mutation
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --project . pytest tests/test_contracts_loader.py -q`
Expected: FAIL — `ModuleNotFoundError: polymer_claims.contracts`.

- [ ] **Step 3: Create the models**

Create `src/polymer_claims/contracts/__init__.py`:

```python
"""CES-1: the data seam. A DataHandle.ref resolves (here, against a bundled fixture) to a
frozen, DRS-shaped, content-addressed SEContractRef. The grammar holds only the thin ref string;
all richness lives here, mirroring datasets/load_dataset and profiles/load_profile.

The loader (load_contract) is added in CES-1 Task 4.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict


class _Frozen(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class AccessMethod(_Frozen):
    type: Literal["file", "https", "s3"]
    access_url: str


class Checksum(_Frozen):
    type: Literal["sha-256"] = "sha-256"
    checksum: str  # hex digest


class SEContractRef(_Frozen):
    # --- SE-Contract / B1 fields ---
    contract_uid: str
    dimnames_hash: str            # canonical content-address: sha256(feature_ids|sample_ids)
    assay: str
    selection: tuple[tuple[str, str], ...] = ()
    genome_assembly: str
    refget_digest: str | None = None
    # --- GA4GH DRS shape (fixity) ---
    self_uri: str
    size: int
    checksums: tuple[Checksum, ...]
    access_methods: tuple[AccessMethod, ...]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run --project . pytest tests/test_contracts_loader.py -q`
Expected: PASS (both model tests).

- [ ] **Step 5: Commit**

```bash
git add src/polymer_claims/contracts/__init__.py tests/test_contracts_loader.py
git commit -m "feat(umbrella): SEContractRef model — DRS-shaped SE-Contract reference (CES-1)"
```

---

## Task 3: The bundled EPICv2-shaped fixture (generator + outputs)

**Files:**
- Create: `src/polymer_claims/contracts/_make_fixture.py`
- Create (generated): `src/polymer_claims/contracts/groupdiff_epicv2_demo.json`, `…/groupdiff_epicv2_demo.betas.tsv`
- Test: `tests/test_contracts_fixture.py`

- [ ] **Step 1: Write the failing test (raw-file consistency — no loader needed)**

Create `tests/test_contracts_fixture.py`:

```python
from __future__ import annotations

import json
import re
from pathlib import Path

_DIR = Path(__file__).resolve().parents[1] / "src" / "polymer_claims" / "contracts"
_MANIFEST = _DIR / "groupdiff_epicv2_demo.json"
_BETAS = _DIR / "groupdiff_epicv2_demo.betas.tsv"


def _manifest() -> dict:
    return json.loads(_MANIFEST.read_text())


def test_fixture_files_exist():
    assert _MANIFEST.is_file()
    assert _BETAS.is_file()


def test_manifest_dims_match_row_and_col_data():
    m = _manifest()
    n_features, n_samples = m["dim"]
    assert n_features == len(m["row_data"])
    assert n_samples == len(m["col_data"])


def test_betas_matrix_shape_matches_dim():
    m = _manifest()
    n_features, n_samples = m["dim"]
    lines = _BETAS.read_text().splitlines()
    header = lines[0].split("\t")
    assert header[0] == "feature_id"
    assert len(header) == 1 + n_samples
    assert len(lines) - 1 == n_features  # one data row per probe


def test_probe_ids_are_cg_format_and_match_matrix_order():
    m = _manifest()
    cg = re.compile(r"^cg\d{8}$")
    manifest_ids = [r["feature_id"] for r in m["row_data"]]
    assert all(cg.match(fid) for fid in manifest_ids)
    matrix_ids = [ln.split("\t")[0] for ln in _BETAS.read_text().splitlines()[1:]]
    assert manifest_ids == matrix_ids  # same order — the dimnames_hash binds this order


def test_sample_groups_are_binary_and_balanced():
    m = _manifest()
    groups = [c["Sample_Group"] for c in m["col_data"]]
    assert set(groups) == {"case", "control"}
    assert groups.count("case") == groups.count("control")


def test_metadata_is_epicv2_hg38():
    m = _manifest()
    assert m["metadata"]["genome_assembly"] == "hg38"
    assert m["metadata"]["array"] == "EPICv2"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --project . pytest tests/test_contracts_fixture.py -q`
Expected: FAIL — `test_fixture_files_exist` fails (files absent), others error on missing files.

- [ ] **Step 3: Write the deterministic generator**

Create `src/polymer_claims/contracts/_make_fixture.py` (no RNG — fully determined by indices, so the fixture is reproducible and the planted shift is explicit):

```python
"""Deterministic generator for the CES-1 EPICv2-shaped methylation fixture.

Synthetic VALUES, real STRUCTURE: 50 cg-format probes x 8 samples (4 case / 4 control) on
chr4 near the example locus (hg38). No RNG — every value is a fixed function of its indices, so the
fixture is reproducible. Probes 0-4 carry a planted +0.20 beta shift in case samples (used by
CES-2 only; CES-1 asserts nothing about values). Re-run with:  python -m
polymer_claims.contracts._make_fixture
"""
from __future__ import annotations

import json
from pathlib import Path

_DIR = Path(__file__).parent
N_FEATURES = 50
N_SAMPLES = 8
_PLANTED_PROBES = set(range(5))   # first 5 probes carry the case shift
_PLANTED_SHIFT = 0.20


def _samples() -> list[dict]:
    out = []
    for j in range(N_SAMPLES):
        group = "case" if j % 2 == 0 else "control"
        out.append({
            "sample_id": f"S{j + 1:02d}",
            "Sample_Group": group,
            "Age": 40 + (j * 3) % 25,
            "Sex": "M" if j % 3 == 0 else "F",
        })
    return out


def _probes() -> list[dict]:
    return [
        {"feature_id": f"cg{i + 1:08d}", "chr": "chr4", "pos": 105_000_000 + i * 500}
        for i in range(N_FEATURES)
    ]


def _beta(i: int, sample: dict) -> float:
    base = 0.20 + ((i * 7 + 3) % 60) / 100.0   # deterministic in [0.20, 0.79]
    if i in _PLANTED_PROBES and sample["Sample_Group"] == "case":
        base += _PLANTED_SHIFT
    return round(min(base, 0.999999), 6)


def build() -> None:
    samples = _samples()
    probes = _probes()
    manifest = {
        "uid": "groupdiff_epicv2_demo@1",
        "dim": [N_FEATURES, N_SAMPLES],
        "assays": [{"name": "beta", "ref": "groupdiff_epicv2_demo.betas.tsv"}],
        "col_data": samples,
        "row_data": probes,
        "metadata": {"genome_assembly": "hg38", "array": "EPICv2"},
    }
    (_DIR / "groupdiff_epicv2_demo.json").write_text(json.dumps(manifest, indent=2) + "\n")

    header = "\t".join(["feature_id"] + [s["sample_id"] for s in samples])
    rows = [header]
    for i, probe in enumerate(probes):
        cells = [probe["feature_id"]] + [f"{_beta(i, s):.6f}" for s in samples]
        rows.append("\t".join(cells))
    (_DIR / "groupdiff_epicv2_demo.betas.tsv").write_text("\n".join(rows) + "\n")


if __name__ == "__main__":
    build()
```

- [ ] **Step 4: Generate the fixture files**

Run: `cd /Users/zbb2/Desktop/polymer-claims && uv run --project . python -m polymer_claims.contracts._make_fixture`
Then confirm: `ls src/polymer_claims/contracts/` shows `groupdiff_epicv2_demo.json` and `groupdiff_epicv2_demo.betas.tsv`.

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run --project . pytest tests/test_contracts_fixture.py -q`
Expected: PASS (all six consistency tests).

- [ ] **Step 6: Commit (generator + generated outputs together)**

```bash
git add src/polymer_claims/contracts/_make_fixture.py \
        src/polymer_claims/contracts/groupdiff_epicv2_demo.json \
        src/polymer_claims/contracts/groupdiff_epicv2_demo.betas.tsv \
        tests/test_contracts_fixture.py
git commit -m "feat(umbrella): bundled EPICv2-shaped methylation fixture + generator (CES-1)"
```

---

## Task 4: `load_contract` + canonical `dimnames_hash`

**Files:**
- Modify: `src/polymer_claims/contracts/__init__.py`
- Test: `tests/test_contracts_loader.py` (append loader tests)

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_contracts_loader.py`:

```python
import hashlib
import json as _json
from pathlib import Path

from polymer_claims._hashing import canonical_sha256
from polymer_claims.contracts import load_contract

_REF = "se:groupdiff_epicv2_demo@1"


def test_load_contract_returns_contract_fields():
    ref = load_contract(_REF)
    assert ref.contract_uid == "groupdiff_epicv2_demo@1"
    assert ref.assay == "beta"
    assert ref.genome_assembly == "hg38"
    assert ref.selection  # non-empty selector


def test_load_contract_accepts_bare_ref_without_prefix():
    assert load_contract("groupdiff_epicv2_demo@1") == load_contract(_REF)


def test_dimnames_hash_is_deterministic_and_prefixed():
    h = load_contract(_REF).dimnames_hash
    assert h == load_contract(_REF).dimnames_hash
    assert h.startswith("sha256:")


def test_dimnames_hash_matches_canonical_recipe_over_ordered_ids():
    # parity: the hash is canonical_sha256 over the ORDERED feature/sample id lists.
    contracts_dir = Path(load_contract(_REF).access_methods[0].access_url).parent
    manifest = _json.loads((contracts_dir / "groupdiff_epicv2_demo.json").read_text())
    feature_ids = [r["feature_id"] for r in manifest["row_data"]]
    sample_ids = [c["sample_id"] for c in manifest["col_data"]]
    expected = canonical_sha256({"feature_ids": feature_ids, "sample_ids": sample_ids})
    assert load_contract(_REF).dimnames_hash == expected


def test_dimnames_hash_is_order_sensitive():
    # permuting sample order must change the address (the matrix identity depends on order).
    a = canonical_sha256({"feature_ids": ["cg00000001"], "sample_ids": ["S01", "S02"]})
    b = canonical_sha256({"feature_ids": ["cg00000001"], "sample_ids": ["S02", "S01"]})
    assert a != b


def test_drs_shape_present():
    ref = load_contract(_REF)
    assert ref.self_uri.startswith("drs://")
    assert ref.size > 0
    assert ref.checksums and ref.checksums[0].type == "sha-256"
    assert ref.access_methods and ref.access_methods[0].type == "file"


def test_checksum_is_sha256_over_fixture_bytes():
    ref = load_contract(_REF)
    contracts_dir = Path(ref.access_methods[0].access_url).parent
    manifest_bytes = (contracts_dir / "groupdiff_epicv2_demo.json").read_bytes()
    betas_bytes = (contracts_dir / "groupdiff_epicv2_demo.betas.tsv").read_bytes()
    expected = hashlib.sha256(manifest_bytes + betas_bytes).hexdigest()
    assert ref.checksums[0].checksum == expected
    assert ref.size == len(manifest_bytes) + len(betas_bytes)


def test_unknown_ref_raises_filenotfound():
    import pytest as _pytest
    with _pytest.raises(FileNotFoundError, match="nope"):
        load_contract("se:nope@1")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run --project . pytest tests/test_contracts_loader.py -q`
Expected: FAIL — `ImportError: cannot import name 'load_contract'`.

- [ ] **Step 3: Implement the loader**

Append to `src/polymer_claims/contracts/__init__.py` (add imports at the top of the file: `import hashlib`, `import json`, `from functools import lru_cache`, `from pathlib import Path`, and `from polymer_claims._hashing import canonical_sha256`):

```python
_DIR = Path(__file__).parent


def _resolve_uid(ref: str) -> str:
    """Strip an optional 'se:' scheme prefix; the remainder is the contract uid."""
    return ref[len("se:"):] if ref.startswith("se:") else ref


@lru_cache(maxsize=None)
def load_contract(ref: str) -> SEContractRef:
    """Resolve a DataHandle.ref to a DRS-shaped, content-addressed SEContractRef over a bundled
    SE-Contract fixture. Unknown ref -> FileNotFoundError (the caller degrades it to a node error;
    it never crashes the run — same contract as datasets.load_dataset)."""
    uid = _resolve_uid(ref)
    stem = uid.split("@")[0]
    manifest_path = _DIR / f"{stem}.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"no bundled SE-Contract {ref!r} at {manifest_path}")

    manifest_bytes = manifest_path.read_bytes()
    manifest = json.loads(manifest_bytes)
    assay = manifest["assays"][0]
    betas_path = _DIR / assay["ref"]
    betas_bytes = betas_path.read_bytes()

    feature_ids = [r["feature_id"] for r in manifest["row_data"]]
    sample_ids = [c["sample_id"] for c in manifest["col_data"]]
    dimnames_hash = canonical_sha256(
        {"feature_ids": feature_ids, "sample_ids": sample_ids}
    )

    fixture_bytes = manifest_bytes + betas_bytes
    checksum = hashlib.sha256(fixture_bytes).hexdigest()

    return SEContractRef(
        contract_uid=manifest["uid"],
        dimnames_hash=dimnames_hash,
        assay=assay["name"],
        selection=(("group_col", "Sample_Group"),),
        genome_assembly=manifest["metadata"]["genome_assembly"],
        self_uri=f"drs://local/{manifest['uid']}",
        size=len(fixture_bytes),
        checksums=(Checksum(checksum=checksum),),
        access_methods=(AccessMethod(type="file", access_url=str(betas_path)),),
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run --project . pytest tests/test_contracts_loader.py -q`
Expected: PASS (model tests from Task 2 + all loader tests).

- [ ] **Step 5: Commit**

```bash
git add src/polymer_claims/contracts/__init__.py tests/test_contracts_loader.py
git commit -m "feat(umbrella): load_contract resolver + canonical dimnames_hash (CES-1)"
```

---

## Task 5: Re-exports + full verification + docs

**Files:**
- Modify: `src/polymer_claims/__init__.py`
- Modify: `docs/superpowers/CONTINUE.md`, `docs/superpowers/roadmaps/2026-06-11-credibility-arc-roadmap.md`

- [ ] **Step 1: Write the failing test (top-level re-export)**

Append to `tests/test_contracts_loader.py`:

```python
def test_symbols_reexported_from_umbrella():
    import polymer_claims
    assert hasattr(polymer_claims, "SEContractRef")
    assert hasattr(polymer_claims, "load_contract")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --project . pytest tests/test_contracts_loader.py::test_symbols_reexported_from_umbrella -q`
Expected: FAIL — `AttributeError: module 'polymer_claims' has no attribute 'SEContractRef'`.

- [ ] **Step 3: Add the re-exports**

In `src/polymer_claims/__init__.py`, after the existing `from polymer_claims.profiles import load_profile` line, add:

```python
from polymer_claims.contracts import (
    AccessMethod,
    Checksum,
    SEContractRef,
    load_contract,
)
```

And add `"AccessMethod"`, `"Checksum"`, `"SEContractRef"`, `"load_contract"` to the `__all__` list.

- [ ] **Step 4: Run the re-export test + the full umbrella suite + lint**

Run:
```bash
uv run --project . pytest tests/ -q && uv run --project . ruff check src tests
```
Expected: all green (new contracts/hashing tests + every pre-existing umbrella test); ruff clean.

- [ ] **Step 5: Run the full local CI substitute**

Run: `bash scripts/check-all.sh`
Expected: `ALL GREEN`. (Confirms grammar/protocol/viewer untouched and still green — the scope fence held.)

- [ ] **Step 6: Update CONTINUE + roadmap, then commit**

Add a dated `✅ CES-1 DONE` entry to `docs/superpowers/CONTINUE.md` recording: the thin-handle decision held (no grammar change), `SEContractRef` + `load_contract` + the bundled `groupdiff_epicv2_demo` fixture, the shared `canonical_sha256` helper, the `dimnames_hash`, the deferral of computation/licensing + real-vs-public data to CES-2, and the final green test counts. Mark CES-1's portion of the roadmap §1b done (note CES-1 complete, CES-2 next).

```bash
git add src/polymer_claims/__init__.py docs/superpowers/CONTINUE.md \
        docs/superpowers/roadmaps/2026-06-11-credibility-arc-roadmap.md tests/test_contracts_loader.py
git commit -m "feat(umbrella): re-export the CES-1 data-seam symbols; CONTINUE + roadmap (CES-1 done)"
```

---

## Self-Review

**Spec coverage:**
- §1 thin handle / no grammar change → Tasks 2-4 are umbrella-only; File Structure fences grammar/protocol. ✓
- §2 `SEContractRef` (B1 fields + DRS shape + `refget_digest` slot) → Task 2. ✓
- §3 EPICv2-shaped fixture, sidecar layout, planted shift → Task 3. ✓
- §4 `load_contract` + canonical `dimnames_hash` reusing CES-0 discipline → Task 1 (shared helper) + Task 4. ✓
- §5 scope fences (no protocol/run_cycle/exec_adapters change) → no task touches them; Task 5 step 5 verifies via check-all. ✓
- §6 tests (round-trip, fields, deterministic + content-sensitive hash, DRS shape, unknown-ref error, fixture consistency, hash-parity) → Tasks 1-4 enumerate each. ✓
- §7 re-exports → Task 5. ✓

**Placeholder scan:** none — every code/test step shows complete content and exact commands.

**Type consistency:** `SEContractRef`/`AccessMethod`/`Checksum` fields are identical across Task 2 (definition), Task 2 test (`_ref` helper), and Task 4 (loader construction + tests). `canonical_sha256` signature matches across Task 1 and Task 4. `load_contract(ref)` returns `SEContractRef` consistently. Fixture filenames (`groupdiff_epicv2_demo.json`, `groupdiff_epicv2_demo.betas.tsv`) and `uid` (`groupdiff_epicv2_demo@1`) are identical across Tasks 3, 4, and their tests.
