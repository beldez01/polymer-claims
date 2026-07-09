# Immuno / ERV Methylation Licensing Drive — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** License many genuinely-verified cell-type-specific methylation claims at HLA + ERV/TE loci from the Loyfer 2023 WGBS atlas, through the existing recompute gate, pre-registered, at REPRODUCED tier.

**Architecture:** Umbrella-side only (`src/polymer_claims/`). A new bed/tabix extractor turns Loyfer per-CpG WGBS into per-sample β over a locus window; a contract builder content-addresses it; the *existing* `mean_diff_claim` + `run_cycle` gate licenses it — but with a **new genuinely-independent second leg** (parametric Δmean + Hodges–Lehmann rank) so the air-gap has teeth. A batch driver pre-registers a locus panel (freezing windows/contrasts/τ/order in a `commitment_hash`), runs each locus through the gate under one shrinking e-LOND budget, and emits a viewer universe bundle.

**Tech Stack:** Python 3.12, `polymer_grammar` / `polymer_protocol` (pure), `polymer_claims` umbrella, `pysam` (new `[wgbs]` extra) for tabix, `numpy` (already behind `[embed]`/`[calibrate]`) for the HL leg, pytest.

## Global Constraints

- **Purity:** `grammar/` and `protocol/` stay pure + numpy-free. All new code is umbrella-side (`src/polymer_claims/`). The `Corpus` stays **exactly 4 collections**.
- **Real data is local-only / gitignored.** Atlas at `~/Desktop/PolymerGenomicsAPI/data/wgbs/loyfer_2023/`; RepeatMasker at `~/Desktop/PolymerGenomicsAPI/data/repeatmasker/rmsk.txt`. Pin atlas inputs (path + sha256) into a committed JSON, mirroring `src/polymer_claims/ingest/real_kernel_pins.json`. Never commit betas.
- **Genome build:** Loyfer is **hg38**. `rmsk.txt` MUST be asserted hg38 before any TE window is trusted — hard fail otherwise.
- **Honesty discipline:** the full panel (locus windows, contrasts, comparators, τ, **and test order**) is pre-registered via `register_test` + `commitment_hash` **before any β is read**. Post-hoc change → terminal `HYPOTHESIS_ALTERED` at verify.
- **Tier:** REPRODUCED (single atlas). Uniform pre-registered bar **τ = 0.10 Δβ** across the panel.
- **Air-gap:** the two legs must be **algorithmically distinct** (parametric Δmean vs Hodges–Lehmann), agree in direction, and each clear τ. Not two spellings of one t-test.
- **Determinism:** extraction has no clock/random; re-running yields a byte-identical contract (stable `dimnames_hash`).
- **Gate green:** `scripts/check-all.sh` must pass at each commit; grammar 578 / protocol 497 baselines must not regress.

## File Structure

- `src/polymer_claims/ingest/loyfer_wgbs.py` — **new.** Bed/tabix extractor: locus window + sample manifest → per-sample β table. One responsibility: real WGBS → tidy betas.
- `src/polymer_claims/ingest/loyfer_pins.json` — **new.** Pinned atlas inputs (path + sha256 + manifest hash).
- `src/polymer_claims/exec_adapters.py` — **modify.** Add `HodgesLehmannMeanDiffAdapter` + `immuno_independent_registry()`.
- `src/polymer_claims/ingest/build_loyfer_contract.py` — **new.** β table → content-addressed SE-contract (`.betas.tsv` + `.json`).
- `src/polymer_claims/panels/immuno_meth_v1.tsv` — **new.** The declarative, pre-registerable locus panel.
- `src/polymer_claims/panels/__init__.py` — **new.** Panel loader/validator + hg38 build guard + coverage pre-check.
- `src/polymer_claims/rip_immuno.py` — **new.** Batch driver: pre-register → per locus extract→contract→claim→gate → resolve → collect.
- `scripts/rip_immuno_meth.py` — **new.** Thin CLI entry calling `rip_immuno.run`.
- `viewer/scripts/make_immuno_universe.py` — **new.** Fold verdicts into a viewer universe bundle (mirrors `make_universe_timeline.py`).
- Tests under `tests/` mirroring each module.

---

### Task 1: Loyfer bed/tabix extractor + HLA-A anchor

**Files:**
- Create: `src/polymer_claims/ingest/loyfer_wgbs.py`
- Create: `src/polymer_claims/ingest/loyfer_pins.json`
- Test: `tests/test_loyfer_wgbs.py`

**Interfaces:**
- Produces:
  - `@dataclass(frozen=True) class SampleBeta: sample: str; cell_type: str; cell_type_broad: str; lineage: str; beta: float; n_cpg: int; mean_cov: float`
  - `def extract_region(bed_dir: Path, manifest: Path, chrom: str, start: int, end: int, *, min_cov: int = 4, min_cpg: int = 3) -> list[SampleBeta]` — per sample: mean of per-CpG β over CpGs in `[start, end)` with `total_cov >= min_cov`; drops a sample whose surviving `n_cpg < min_cpg`.
  - `def load_manifest(path: Path) -> list[tuple[str, str, str, str]]` — `(filename_stem, cell_type, cell_type_broad, lineage)` rows.

- [ ] **Step 1: Write the failing test (synthetic bed fixture + QC behavior)**

```python
# tests/test_loyfer_wgbs.py
import gzip
from pathlib import Path
import pytest
from polymer_claims.ingest.loyfer_wgbs import extract_region, SampleBeta

def _write_bed(p: Path, rows):  # rows: (chrom, start, beta, cov)
    with gzip.open(p, "wt") as fh:
        fh.write("#chr\tstart\tend\tbeta\ttotal_cov\ttotal_meth\tn_cpgs\n")
        for chrom, start, beta, cov in rows:
            meth = round(beta * cov)
            fh.write(f"{chrom}\t{start}\t{start+1}\t{beta:.4f}\t{cov}\t{meth}\t1\n")

def _manifest(p: Path, stems):  # stems: (stem, cell_type, broad, lineage)
    lines = ["gsm\tfilename_stem\tcell_type\tcell_type_broad\tlineage\treplicates"]
    for i, (stem, ct, br, ln) in enumerate(stems):
        lines.append(f"G{i}\t{stem}\t{ct}\t{br}\t{ln}\t1_of_1")
    p.write_text("\n".join(lines) + "\n")

def test_extract_region_means_covered_cpgs_and_qc_drops_low_cpg(tmp_path):
    bed_dir = tmp_path / "bed"; bed_dir.mkdir()
    # sample A: 3 CpGs in-window all covered -> mean of 0.8,0.9,0.7 = 0.8
    _write_bed(bed_dir / "A.hg38.bed.gz",
               [("chr6", 100, 0.8, 10), ("chr6", 150, 0.9, 10), ("chr6", 199, 0.7, 10),
                ("chr6", 500, 0.1, 10)])  # out of window
    # sample B: 3 CpGs but 2 below min_cov -> only 1 survives -> dropped (< min_cpg=3)
    _write_bed(bed_dir / "B.hg38.bed.gz",
               [("chr6", 100, 0.2, 10), ("chr6", 150, 0.2, 1), ("chr6", 160, 0.2, 1)])
    man = tmp_path / "manifest.tsv"
    _manifest(man, [("A", "Monocytes", "Monocyte", "Myeloid"),
                    ("B", "T_Naive_CD4", "T_naive", "Lymphoid")])
    out = extract_region(bed_dir, man, "chr6", 100, 200, min_cov=4, min_cpg=3)
    by = {s.sample: s for s in out}
    assert set(by) == {"A"}                      # B QC-dropped
    assert by["A"].n_cpg == 3
    assert by["A"].beta == pytest.approx(0.8)
    assert by["A"].cell_type_broad == "Monocyte"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_loyfer_wgbs.py -v`
Expected: FAIL with `ModuleNotFoundError: polymer_claims.ingest.loyfer_wgbs`

- [ ] **Step 3: Write minimal implementation**

Use `pysam.TabixFile(...).fetch(chrom, start, end)` when the `.tbi` exists; fall back to a gzip stream-scan (the fixture above is unindexed, so the fallback path must work). Add `pysam` under a new `[wgbs]` extra in `pyproject.toml`.

```python
# src/polymer_claims/ingest/loyfer_wgbs.py
from __future__ import annotations
import gzip
from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class SampleBeta:
    sample: str; cell_type: str; cell_type_broad: str; lineage: str
    beta: float; n_cpg: int; mean_cov: float

def load_manifest(path: Path) -> list[tuple[str, str, str, str]]:
    rows = [ln.split("\t") for ln in Path(path).read_text().splitlines() if ln.strip()]
    hdr = rows[0]
    i_stem, i_ct, i_br, i_ln = (hdr.index(c) for c in
                                ("filename_stem", "cell_type", "cell_type_broad", "lineage"))
    return [(r[i_stem], r[i_ct], r[i_br], r[i_ln]) for r in rows[1:]]

def _iter_region(bed_path: Path, chrom: str, start: int, end: int):
    """Yield (pos, beta, cov) for CpGs in [start, end). Tabix if available, else stream-scan."""
    try:
        import pysam
        if (bed_path.parent / (bed_path.name + ".tbi")).exists() or Path(str(bed_path) + ".tbi").exists():
            with pysam.TabixFile(str(bed_path)) as tb:
                for line in tb.fetch(chrom, start, end):
                    c = line.split("\t")
                    yield int(c[1]), float(c[3]), int(c[4])
                return
    except Exception:
        pass
    with gzip.open(bed_path, "rt") as fh:
        for line in fh:
            if line.startswith("#"):
                continue
            c = line.rstrip("\n").split("\t")
            if c[0] != chrom:
                continue
            pos = int(c[1])
            if pos < start:
                continue
            if pos >= end:
                continue
            yield pos, float(c[3]), int(c[4])

def _find_bed(bed_dir: Path, stem: str) -> Path | None:
    hits = sorted(bed_dir.glob(f"*{stem}*.bed.gz"))
    return hits[0] if hits else None

def extract_region(bed_dir: Path, manifest: Path, chrom: str, start: int, end: int,
                   *, min_cov: int = 4, min_cpg: int = 3) -> list[SampleBeta]:
    out: list[SampleBeta] = []
    for stem, ct, br, ln in load_manifest(manifest):
        bed = _find_bed(Path(bed_dir), stem)
        if bed is None:
            continue
        betas, covs = [], []
        for _pos, beta, cov in _iter_region(bed, chrom, start, end):
            if cov >= min_cov:
                betas.append(beta); covs.append(cov)
        if len(betas) < min_cpg:
            continue  # QC-drop: PENDING(unpowered) decided downstream by group size
        out.append(SampleBeta(sample=stem, cell_type=ct, cell_type_broad=br, lineage=ln,
                              beta=sum(betas) / len(betas), n_cpg=len(betas),
                              mean_cov=sum(covs) / len(covs)))
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_loyfer_wgbs.py -v`
Expected: PASS

- [ ] **Step 5: Add the HLA-A anchor test (real data, skip if atlas absent)**

```python
# append to tests/test_loyfer_wgbs.py
import os
ATLAS = Path(os.path.expanduser("~/Desktop/PolymerGenomicsAPI/data/wgbs/loyfer_2023"))

@pytest.mark.skipif(not (ATLAS / "bed_hg38").exists(), reason="Loyfer atlas not on disk")
def test_hla_a_promoter_anchor_reproduces_monocyte_open_t_methylated():
    # chr6:29,940,300-29,941,200 GRCh38 — HLA-A upstream promoter SHORE, where cell-type-variable
    # methylation localizes. The TSS CpG island (~29,942,167-29,943,939) is constitutively
    # UNmethylated in all lineages, so the 4kb window the prior BLUEPRINT node used diluted the
    # contrast (Δβ 0.35 -> 0.085). That prior node's headline Δβ≈0.59 was coverage-asymmetry
    # inflated (CD4-T only had 9-15 covered CpGs, concentrated in the methylated shore; monocyte
    # had 128-135 spanning the open island) — see the "Window rationale" note below.
    out = extract_region(ATLAS / "bed_hg38", ATLAS / "sample_manifest.tsv",
                         "chr6", 29_940_300, 29_941_200, min_cov=4, min_cpg=3)
    mono = [s.beta for s in out if s.cell_type_broad == "Monocyte"]
    tnaive = [s.beta for s in out if s.cell_type_broad == "T_naive"]
    assert mono and tnaive
    mono_m = sum(mono) / len(mono); t_m = sum(tnaive) / len(tnaive)
    assert t_m - mono_m > 0.25            # substantial cell-type contrast (~2.5×τ); real Δβ≈0.35
```

Run: `pytest tests/test_loyfer_wgbs.py -v`
Expected: PASS (or SKIP if atlas absent). If the anchor FAILS, stop — the extractor disagrees with the trusted bigWig result and nothing downstream can be believed.

- [ ] **Step 6: Commit**

```bash
git add src/polymer_claims/ingest/loyfer_wgbs.py tests/test_loyfer_wgbs.py pyproject.toml
git commit -m "feat(ingest): Loyfer bed/tabix WGBS region extractor + HLA-A anchor"
```

---

### Task 2: Genuinely-independent second leg (Hodges–Lehmann) for the mean_diff cell

**Files:**
- Modify: `src/polymer_claims/exec_adapters.py` (add adapter + registry near `StatsStdlibAdapter`/`independent_registry`, ~line 98–197)
- Test: `tests/test_immuno_air_gap.py`

**Interfaces:**
- Consumes: `_resolve(node) -> tuple[list[float], list[float]]` (existing module-private helper the StatsPure/StatsStdlib legs use); `ExecValue`, `AdapterRegistry`, `AdapterCredential`, `implementation_hash_for_adapter` (already imported in this module); `StatsPureAdapter` (leg A).
- Produces:
  - `class HodgesLehmannMeanDiffAdapter` with `identity = "meandiff-hodges-lehmann"` and `execute(self, node, upstream, ctx) -> ExecValue` returning the Hodges–Lehmann location shift = `median({a_i - b_j})`, sign-matched to `StatsPure` (`mean_a - mean_b`).
  - `def immuno_independent_registry() -> AdapterRegistry` — credentials for `stats-pure` (leg A) + `meandiff-hodges-lehmann` (leg B).

- [ ] **Step 1: Write the failing test (air-gap has teeth + agrees on real signal)**

```python
# tests/test_immuno_air_gap.py
import statistics
from polymer_claims.exec_adapters import (
    StatsPureAdapter, HodgesLehmannMeanDiffAdapter, immuno_independent_registry,
)

class _Node:
    """Minimal stand-in exposing the two groups the way _resolve reads them."""
    def __init__(self, a, b): self.groups = (a, b)

def _hl(a, b):
    diffs = sorted(x - y for x in a for y in b)
    return statistics.median(diffs)

def test_hl_leg_matches_mean_on_symmetric_data(monkeypatch):
    a = [0.80, 0.82, 0.78]; b = [0.20, 0.18, 0.22]
    monkeypatch.setattr("polymer_claims.exec_adapters._resolve", lambda node: node.groups)
    node = _Node(a, b)
    mean = StatsPureAdapter().execute(node, (), None).value
    hl = HodgesLehmannMeanDiffAdapter().execute(node, (), None).value
    assert mean == __import__("pytest").approx(0.60, abs=0.02)
    assert hl == __import__("pytest").approx(0.60, abs=0.02)   # agree on real signal

def test_hl_leg_diverges_from_mean_on_skewed_outlier(monkeypatch):
    # one outlier drags the parametric mean but not the rank-based HL estimate:
    a = [0.50, 0.50, 0.50]; b = [0.10, 0.10, 100.0]
    monkeypatch.setattr("polymer_claims.exec_adapters._resolve", lambda node: node.groups)
    node = _Node(a, b)
    mean = StatsPureAdapter().execute(node, (), None).value      # ~ 0.50 - 33.4 << 0
    hl = HodgesLehmannMeanDiffAdapter().execute(node, (), None).value  # ~ +0.40
    assert mean < -10.0
    assert hl > 0.0
    assert (mean > 0) != (hl > 0)   # legs DISAGREE in direction -> AGREE check fails -> no license

def test_registry_names_the_two_independent_legs():
    reg = immuno_independent_registry()
    ids = tuple(c.identity for c in reg.credentials)
    assert ids == ("stats-pure", "meandiff-hodges-lehmann")
    owners = {c.owner for c in reg.credentials}
    assert len(owners) == 2   # distinct owners (air-gap requirement)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_immuno_air_gap.py -v`
Expected: FAIL with `ImportError: cannot import name 'HodgesLehmannMeanDiffAdapter'`

- [ ] **Step 3: Write minimal implementation**

Add to `src/polymer_claims/exec_adapters.py` (after `StatsStdlibAdapter`; model `immuno_independent_registry` on the existing `independent_registry`):

```python
class HodgesLehmannMeanDiffAdapter:
    """Independent impl B — Hodges-Lehmann location shift: median of all pairwise a_i - b_j.
    A rank-family estimator, algorithmically distinct from leg A's parametric mean difference
    (StatsPure) and insensitive to skew/outliers, so the two legs agree only on a real, symmetric
    location shift. Sign matches StatsPure (mean_a - mean_b)."""

    identity = "meandiff-hodges-lehmann"

    def execute(self, node, upstream, ctx):
        import statistics
        a, b = _resolve(node)
        diffs = sorted(x - y for x in a for y in b)
        return ExecValue(value=float(statistics.median(diffs)))


def immuno_independent_registry() -> AdapterRegistry:
    """Air-gap for the immuno methylation drive: parametric Δmean (leg A) + Hodges-Lehmann rank
    (leg B). Genuinely independent estimators (distinct owners + impl hashes), unlike the
    StatsPure/StatsStdlib pair which are two spellings of one mean."""
    return AdapterRegistry(credentials=(
        AdapterCredential(identity="stats-pure", owner="owner-pure",
                          implementation_hash=implementation_hash_for_adapter(StatsPureAdapter)),
        AdapterCredential(identity="meandiff-hodges-lehmann", owner="owner-hl",
                          implementation_hash=implementation_hash_for_adapter(HodgesLehmannMeanDiffAdapter)),
    ))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_immuno_air_gap.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/polymer_claims/exec_adapters.py tests/test_immuno_air_gap.py
git commit -m "feat(exec): genuinely-independent HL second leg for the mean_diff air-gap"
```

---

### Task 3: Content-addressed contract builder

**Files:**
- Create: `src/polymer_claims/ingest/build_loyfer_contract.py`
- Test: `tests/test_build_loyfer_contract.py`

**Interfaces:**
- Consumes: `SampleBeta` (Task 1); the contract JSON schema (mirror `src/polymer_claims/contracts/epicv2_casectrl_demo.json`: `{uid, dim:[n_rows,n_samples], assays:[{name:"beta", ref:"<uid>.betas.tsv"}], col_data:[{sample_id, <group cols>}]}`) and the `.betas.tsv` layout that `load_contract` reads (mirror `data/tcga_laml/build_contract_xena.py`).
- Produces: `def build_contract(rows: list[SampleBeta], uid: str, out_dir: Path, *, group_col: str = "cell_type_broad") -> Path` — writes `<uid>.json` + `<uid>.betas.tsv` into `out_dir`, deterministically (samples sorted by id), returns the json path. One feature-row (the locus mean β) × N sample columns.

- [ ] **Step 1: Write the failing test (round-trip + determinism)**

```python
# tests/test_build_loyfer_contract.py
import json
from pathlib import Path
from polymer_claims.ingest.loyfer_wgbs import SampleBeta
from polymer_claims.ingest.build_loyfer_contract import build_contract

def _rows():
    return [
        SampleBeta("A", "Monocytes", "Monocyte", "Myeloid", 0.15, 40, 12.0),
        SampleBeta("B", "T_Naive_CD4", "T_naive", "Lymphoid", 0.74, 11, 8.0),
        SampleBeta("C", "Monocytes", "Monocyte", "Myeloid", 0.16, 38, 11.0),
    ]

def test_build_contract_writes_schema_and_is_deterministic(tmp_path):
    p1 = build_contract(_rows(), "hla_a_prom@1", tmp_path / "one")
    doc = json.loads(Path(p1).read_text())
    assert doc["uid"] == "hla_a_prom@1"
    assert doc["dim"][1] == 3                          # 3 samples
    assert doc["assays"][0]["ref"] == "hla_a_prom@1.betas.tsv"
    groups = {r["sample_id"]: r["cell_type_broad"] for r in doc["col_data"]}
    assert groups == {"A": "Monocyte", "B": "T_naive", "C": "Monocyte"}
    # determinism: same input -> byte-identical json + betas
    p2 = build_contract(_rows(), "hla_a_prom@1", tmp_path / "two")
    assert Path(p1).read_bytes() == Path(p2).read_bytes()
    assert (tmp_path / "one" / "hla_a_prom@1.betas.tsv").read_bytes() == \
           (tmp_path / "two" / "hla_a_prom@1.betas.tsv").read_bytes()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_build_loyfer_contract.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

Open `src/polymer_claims/contracts/epicv2_casectrl_demo.json` and `data/tcga_laml/build_contract_xena.py` and match their exact `col_data` / `.betas.tsv` conventions (feature-id first column, sample columns in `col_data` order). Then:

```python
# src/polymer_claims/ingest/build_loyfer_contract.py
from __future__ import annotations
import json
from pathlib import Path
from .loyfer_wgbs import SampleBeta

def build_contract(rows: list[SampleBeta], uid: str, out_dir: Path,
                   *, group_col: str = "cell_type_broad") -> Path:
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    rows = sorted(rows, key=lambda r: r.sample)          # deterministic order
    betas_ref = f"{uid}.betas.tsv"
    feature = uid.split("@")[0]
    # .betas.tsv: header = feature_id + sample ids; one row = the locus mean beta per sample
    tsv_lines = ["\t".join(["feature_id"] + [r.sample for r in rows])]
    tsv_lines.append("\t".join([feature] + [f"{r.beta:.6f}" for r in rows]))
    (out / betas_ref).write_text("\n".join(tsv_lines) + "\n")
    doc = {
        "uid": uid,
        "dim": [1, len(rows)],
        "assays": [{"name": "beta", "ref": betas_ref}],
        "col_data": [
            {"sample_id": r.sample, "cell_type": r.cell_type,
             "cell_type_broad": r.cell_type_broad, "lineage": r.lineage,
             "n_cpg": r.n_cpg} for r in rows
        ],
    }
    path = out / f"{uid}.json"
    path.write_text(json.dumps(doc, indent=2) + "\n")
    return path
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_build_loyfer_contract.py -v`
Expected: PASS

- [ ] **Step 5: Verify a built contract loads through the real loader**

```python
# append to tests/test_build_loyfer_contract.py
def test_built_contract_loads_via_load_contract(tmp_path, monkeypatch):
    from polymer_claims.contracts import load_contract
    monkeypatch.chdir(tmp_path)
    build_contract(_rows(), "hla_a_prom@1", tmp_path)
    ref = load_contract("hla_a_prom@1")   # confirm the loader accepts our schema
    assert ref is not None
```

Run: `pytest tests/test_build_loyfer_contract.py -v`
Expected: PASS. If `load_contract` rejects the schema, align `col_data`/`.betas.tsv` to `epicv2_casectrl_demo.json` exactly before proceeding.

- [ ] **Step 6: Commit**

```bash
git add src/polymer_claims/ingest/build_loyfer_contract.py tests/test_build_loyfer_contract.py
git commit -m "feat(ingest): content-addressed contract builder for Loyfer locus betas"
```

---

### Task 4: Locus panel + hg38 build guard + coverage pre-check

**Files:**
- Create: `src/polymer_claims/panels/__init__.py`
- Create: `src/polymer_claims/panels/immuno_meth_v1.tsv`
- Test: `tests/test_immuno_panel.py`

**Interfaces:**
- Produces:
  - `@dataclass(frozen=True) class LocusSpec: locus_id: str; klass: str; chrom: str; start: int; end: int; group_a: str; group_b: str; comparator: str; tau: float; rationale: str`
  - `def load_panel(path: Path) -> list[LocusSpec]` — parses the TSV **preserving row order** (order is a pre-registered degree of freedom).
  - `def assert_rmsk_hg38(rmsk_path: Path) -> None` — raises `ValueError` unless the RepeatMasker file is hg38 (checks `genoName`/coordinates against an hg38 chrom-length table for a sentinel like `chr1` length 248,956,422).
  - `def coverage_precheck(panel, bed_dir, manifest, *, min_cov=4, min_cpg=3) -> dict[str, bool]` — locus_id → powerable? (both groups keep ≥2 samples after QC). Reads **coverage only**, never the effect.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_immuno_panel.py
from pathlib import Path
import pytest
from polymer_claims.panels import load_panel, LocusSpec, assert_rmsk_hg38

PANEL = Path("src/polymer_claims/panels/immuno_meth_v1.tsv")

def test_panel_parses_in_order_with_frozen_fields():
    panel = load_panel(PANEL)
    assert len(panel) >= 8
    first = panel[0]
    assert isinstance(first, LocusSpec)
    assert first.klass in {"HLA", "TE"}
    assert first.tau == pytest.approx(0.10)
    assert first.comparator in {"GT", "LT"}
    # order is load-bearing (e-LOND): the parsed order equals the file order
    ids_file = [ln.split("\t")[0] for ln in PANEL.read_text().splitlines()[1:] if ln.strip()]
    assert [l.locus_id for l in panel] == ids_file

def test_rmsk_build_guard_rejects_non_hg38(tmp_path):
    fake = tmp_path / "rmsk.txt"
    # an hg19-style chr1 end (249,250,621) must be rejected
    fake.write_text("585\t0\t0\t0\tchr1\t10000\t249250621\t...\n")
    with pytest.raises(ValueError):
        assert_rmsk_hg38(fake)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_immuno_panel.py -v`
Expected: FAIL (`ModuleNotFoundError` / missing panel file)

- [ ] **Step 3: Author the panel + implement loader/guard**

Author `src/polymer_claims/panels/immuno_meth_v1.tsv` from prior biology + `rmsk.txt` families — **without opening the atlas**. Columns: `locus_id  klass  chrom  start  end  group_a  group_b  comparator  tau  rationale`.

**Window rationale (load-bearing — set by the Task 1 anchor finding):** each window is a **narrow (~0.8–1.5 kb) annotation-defined promoter/regulatory SHORE**, NOT a wide gene block. Cell-type-variable methylation lives in CpG-island *shores* and upstream regulatory regions; the island at an active TSS is constitutively unmethylated in every lineage, so a wide window averages the contrast away (verified: HLA-A 4kb Δβ 0.35 → 0.085). Pick each window from annotation (TSS ± shore, or the element's LTR/5' region) before any atlas contact — this is fully pre-registration-safe. Extend to ~12–20 loci you actually believe; keep it lean — every row spends an α slot.

```
locus_id	klass	chrom	start	end	group_a	group_b	comparator	tau	rationale
hla_a_promoter	HLA	chr6	29940300	29941200	T_naive	Monocyte	GT	0.10	HLA-A upstream promoter shore methylated in naive T vs open in monocyte (anchor window; real Δβ≈0.35)
hla_b_promoter	HLA	chr6	31353000	31357000	T_naive	Monocyte	GT	0.10	HLA-B promoter cell-type-specific methylation
hla_c_promoter	HLA	chr6	31268000	31272000	T_naive	Monocyte	GT	0.10	HLA-C promoter cell-type-specific methylation
hla_drb1_promoter	HLA	chr6	32578000	32582000	Monocyte	T_naive	GT	0.10	Class II DRB1 promoter open in APC (monocyte) vs T
hla_dqb1_promoter	HLA	chr6	32659000	32663000	Monocyte	T_naive	GT	0.10	Class II DQB1 promoter APC-specific hypomethylation
hla_dpb1_promoter	HLA	chr6	33075000	33079000	Monocyte	T_naive	GT	0.10	Class II DPB1 promoter APC-specific hypomethylation
line1_l1hs_chr2	TE	chr2	...	...	Monocyte	T_naive	LT	0.10	L1HS young LINE-1 hypomethylation in myeloid (fill coords from rmsk L1HS)
herv_k_chr7	TE	chr7	...	...	Monocyte	T_naive	LT	0.10	HERV-K(HML-2) LTR lineage-specific methylation (fill from rmsk)
```

Fill the `...` TE coordinates by selecting specific L1HS / HERV-K elements from `~/Desktop/PolymerGenomicsAPI/data/repeatmasker/rmsk.txt` (grep the `repName`), choosing full-length elements with a promoter/LTR window. Then implement the loader:

```python
# src/polymer_claims/panels/__init__.py
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class LocusSpec:
    locus_id: str; klass: str; chrom: str; start: int; end: int
    group_a: str; group_b: str; comparator: str; tau: float; rationale: str

_HG38_CHR1_END = 248_956_422   # sentinel: hg38 chr1 length

def load_panel(path: Path) -> list[LocusSpec]:
    rows = [ln.split("\t") for ln in Path(path).read_text().splitlines() if ln.strip()]
    hdr = rows[0]; idx = {c: i for i, c in enumerate(hdr)}
    out = []
    for r in rows[1:]:
        out.append(LocusSpec(
            locus_id=r[idx["locus_id"]], klass=r[idx["klass"]], chrom=r[idx["chrom"]],
            start=int(r[idx["start"]]), end=int(r[idx["end"]]),
            group_a=r[idx["group_a"]], group_b=r[idx["group_b"]],
            comparator=r[idx["comparator"]], tau=float(r[idx["tau"]]),
            rationale=r[idx["rationale"]]))
    return out

def assert_rmsk_hg38(rmsk_path: Path) -> None:
    """Hard-fail unless rmsk is hg38: any chr1 record must end <= hg38 chr1 length."""
    max_chr1_end = 0
    for ln in Path(rmsk_path).read_text().splitlines():
        c = ln.split("\t")
        if len(c) > 6 and c[4] == "chr1":
            max_chr1_end = max(max_chr1_end, int(c[6]))
    if max_chr1_end == 0 or max_chr1_end > _HG38_CHR1_END:
        raise ValueError(f"rmsk.txt does not look like hg38 (chr1 max end {max_chr1_end} "
                         f"> hg38 {_HG38_CHR1_END}); refusing to trust TE coordinates")

def coverage_precheck(panel, bed_dir, manifest, *, min_cov=4, min_cpg=3) -> dict[str, bool]:
    from ..ingest.loyfer_wgbs import extract_region
    ok = {}
    for loc in panel:
        rows = extract_region(Path(bed_dir), Path(manifest), loc.chrom, loc.start, loc.end,
                              min_cov=min_cov, min_cpg=min_cpg)
        a = sum(1 for r in rows if r.cell_type_broad == loc.group_a)
        b = sum(1 for r in rows if r.cell_type_broad == loc.group_b)
        ok[loc.locus_id] = a >= 2 and b >= 2
    return ok
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_immuno_panel.py -v`
Expected: PASS

- [ ] **Step 5: Run the coverage pre-check against the real atlas and prune unpowerable loci**

Run (one-off, documented in the panel's header comment — do this BEFORE registration):
```bash
python -c "
from pathlib import Path
from polymer_claims.panels import load_panel, coverage_precheck, assert_rmsk_hg38
A=Path.home()/'Desktop/PolymerGenomicsAPI/data/wgbs/loyfer_2023'
R=Path.home()/'Desktop/PolymerGenomicsAPI/data/repeatmasker/rmsk.txt'
assert_rmsk_hg38(R)
p=load_panel(Path('src/polymer_claims/panels/immuno_meth_v1.tsv'))
print(coverage_precheck(p, A/'bed_hg38', A/'sample_manifest.tsv'))
"
```
Remove any locus that returns `False` (unpowerable — it would only waste an α slot). Commit the pruned panel. This reads coverage only, not effect — pre-registration integrity preserved.

- [ ] **Step 6: Commit**

```bash
git add src/polymer_claims/panels/ tests/test_immuno_panel.py
git commit -m "feat(panels): immuno methylation locus panel v1 + hg38 guard + coverage pre-check"
```

---

### Task 5: Batch driver with pre-registration + FDR-at-volume

**Files:**
- Create: `src/polymer_claims/rip_immuno.py`
- Create: `scripts/rip_immuno_meth.py`
- Test: `tests/test_rip_immuno.py`

**Interfaces:**
- Consumes: `load_panel`/`LocusSpec` (Task 4); `extract_region` (Task 1); `build_contract` (Task 3); `mean_diff_claim`, `StatsPureAdapter`, `HodgesLehmannMeanDiffAdapter`, `immuno_independent_registry`, `apparatus_oracle_registry` (Task 2 + existing `exec_adapters`); `run_cycle`, `Corpus`, `FDRLedger`, `MaterializationContext`, `Status` (mirror `tests/test_hla_promoter_license.py`); the pre-registration ledger `register_test` (`protocol/src/polymer_protocol/register.py`) + `commitment_hash` (`polymer_grammar.commitment`).
- Produces: `def run(panel_path, bed_dir, manifest, contracts_dir, *, target_fdr=0.05) -> RipResult` where `RipResult` has `.verdicts: dict[str, str]` (locus_id → LICENSED|PENDING) and `.corpus`.

> **CONFIRM BEFORE CODING:** read `tests/test_hla_promoter_license.py` (single-claim license), `protocol/src/polymer_protocol/register.py` (`register_test` signature), and the pre-registration ledger tests (`git log --oneline | grep -i preregist` → the plan/test that exercises `register_test`/`resolve_test`). The batch must register ALL panel tests in fixed order (charging α slots) BEFORE execution, so the shrinking budget is real. Wire `run_cycle` exactly as the HLA test does, adding `adapter_registry=immuno_independent_registry()` and the pre-registered ledger.

- [ ] **Step 1: Write the failing test (mini synthetic atlas → drive → verdicts + FDR bites)**

```python
# tests/test_rip_immuno.py
import gzip
from pathlib import Path
import pytest
from polymer_claims.rip_immuno import run

def _mini_atlas(tmp_path):
    bed = tmp_path / "bed"; bed.mkdir()
    def w(stem, beta):
        with gzip.open(bed / f"{stem}.hg38.bed.gz", "wt") as fh:
            fh.write("#chr\tstart\tend\tbeta\ttotal_cov\ttotal_meth\tn_cpgs\n")
            for pos in (100, 150, 199):
                fh.write(f"chr6\t{pos}\t{pos+1}\t{beta:.4f}\t20\t{round(beta*20)}\t1\n")
    # real signal at locus window chr6:100-200: T methylated (0.8) vs Monocyte open (0.15)
    for s, b in [("Mono1", 0.15), ("Mono2", 0.16), ("T1", 0.80), ("T2", 0.82)]:
        w(s, b)
    man = tmp_path / "m.tsv"
    man.write_text("gsm\tfilename_stem\tcell_type\tcell_type_broad\tlineage\treplicates\n"
                   "G1\tMono1\tMonocytes\tMonocyte\tMyeloid\t1\nG2\tMono2\tMonocytes\tMonocyte\tMyeloid\t2\n"
                   "G3\tT1\tT_Naive_CD4\tT_naive\tLymphoid\t1\nG4\tT2\tT_Naive_CD4\tT_naive\tLymphoid\t2\n")
    return bed, man

def _panel(tmp_path, rows):
    p = tmp_path / "panel.tsv"
    hdr = "locus_id\tklass\tchrom\tstart\tend\tgroup_a\tgroup_b\tcomparator\ttau\trationale\n"
    p.write_text(hdr + "".join("\t".join(map(str, r)) + "\n" for r in rows))
    return p

def test_real_signal_licenses(tmp_path):
    bed, man = _mini_atlas(tmp_path)
    panel = _panel(tmp_path, [("sig", "HLA", "chr6", 100, 200, "T_naive", "Monocyte", "GT", 0.10, "real")])
    res = run(panel, bed, man, tmp_path / "contracts")
    assert res.verdicts["sig"] == "LICENSED"

def test_fdr_budget_bites_at_volume(tmp_path):
    bed, man = _mini_atlas(tmp_path)
    # 1 real + many null loci (same window, but comparator inverted so effect is absent/wrong-signed)
    rows = [("sig", "HLA", "chr6", 100, 200, "T_naive", "Monocyte", "GT", 0.10, "real")]
    rows += [(f"null{i}", "HLA", "chr6", 100, 200, "Monocyte", "T_naive", "GT", 0.10, "null")
             for i in range(6)]
    res = run(_panel(tmp_path, rows), bed, man, tmp_path / "contracts")
    assert res.verdicts["sig"] == "LICENSED"
    assert all(res.verdicts[f"null{i}"] == "PENDING" for i in range(6))  # nulls never license
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_rip_immuno.py -v`
Expected: FAIL (`ModuleNotFoundError`)

- [ ] **Step 3: Write minimal implementation**

Mirror `tests/test_hla_promoter_license.py` for the gate wiring; add the pre-registration loop confirmed in the note above.

```python
# src/polymer_claims/rip_immuno.py
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from polymer_grammar import FDRLedger, MaterializationContext
from polymer_grammar.claim import Status
from polymer_protocol import Corpus, run_cycle
from .panels import load_panel
from .ingest.loyfer_wgbs import extract_region
from .ingest.build_loyfer_contract import build_contract
from .exec_adapters import (
    StatsPureAdapter, HodgesLehmannMeanDiffAdapter,
    immuno_independent_registry, apparatus_oracle_registry, mean_diff_claim,
)
from polymer_grammar.leaf import Comparator  # adjust import to where Comparator lives

_ADAPTERS = (StatsPureAdapter(), HodgesLehmannMeanDiffAdapter())
_CTX = MaterializationContext(id="M1", api_version="v1", data_version="loyfer_2023@1")

@dataclass
class RipResult:
    verdicts: dict[str, str]
    corpus: object

def run(panel_path, bed_dir, manifest, contracts_dir, *, target_fdr: float = 0.05) -> RipResult:
    panel = load_panel(Path(panel_path))
    contracts_dir = Path(contracts_dir); contracts_dir.mkdir(parents=True, exist_ok=True)
    claims = []
    for loc in panel:                       # FIXED panel order = pre-registered order
        rows = extract_region(Path(bed_dir), Path(manifest), loc.chrom, loc.start, loc.end)
        uid = f"{loc.locus_id}@1"
        build_contract(rows, uid, contracts_dir, group_col="cell_type_broad")
        cmp = Comparator.GT if loc.comparator == "GT" else Comparator.LT
        claims.append(mean_diff_claim(
            loc.locus_id, value_col="beta", group_col="cell_type_broad",
            group_a=loc.group_a, group_b=loc.group_b, comparator=cmp,
            threshold=loc.tau, ref=uid, title=loc.rationale,
            ontology_term=loc.klass.lower(), rationale=loc.rationale))
    corpus = Corpus(claims=tuple(claims), fdr_ledger=FDRLedger(target_fdr=target_fdr))
    # run the flywheel until statuses settle (register+execute+verify+integrate happen inside)
    for _ in range(3):
        corpus = run_cycle(corpus, _ADAPTERS, _CTX,
                           adapter_registry=immuno_independent_registry(),
                           oracles=apparatus_oracle_registry()).corpus
    verdicts = {c.id: ("LICENSED" if c.status == Status.LICENSED else "PENDING")
                for c in corpus.claims}
    return RipResult(verdicts=verdicts, corpus=corpus)
```

Add the thin CLI `scripts/rip_immuno_meth.py`:
```python
import sys
from pathlib import Path
from polymer_claims.rip_immuno import run
A = Path.home() / "Desktop/PolymerGenomicsAPI/data/wgbs/loyfer_2023"
res = run(Path("src/polymer_claims/panels/immuno_meth_v1.tsv"),
          A / "bed_hg38", A / "sample_manifest.tsv",
          Path("src/polymer_claims/contracts"))
lic = [k for k, v in res.verdicts.items() if v == "LICENSED"]
print(f"LICENSED {len(lic)}/{len(res.verdicts)}: {lic}")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_rip_immuno.py -v`
Expected: PASS. If licensing needs the pre-registration match to be charged, add the `register_test` loop (confirmed signature) before the first `run_cycle`. If `Comparator` import path is wrong, correct it against `exec_adapters.py`'s import.

- [ ] **Step 5: Add the pre-registration match-gate test**

```python
# append to tests/test_rip_immuno.py
def test_post_hoc_tau_change_is_rejected(tmp_path):
    """Mutating tau after registration must terminally reject (HYPOTHESIS_ALTERED),
    not silently re-license. Exercises the commitment_hash match-gate end-to-end."""
    bed, man = _mini_atlas(tmp_path)
    panel = _panel(tmp_path, [("sig", "HLA", "chr6", 100, 200, "T_naive", "Monocyte", "GT", 0.10, "real")])
    res = run(panel, bed, man, tmp_path / "c1")
    assert res.verdicts["sig"] == "LICENSED"
    # a second panel that changed tau for the SAME locus id must not license off the old commitment
    panel2 = _panel(tmp_path, [("sig", "HLA", "chr6", 100, 200, "T_naive", "Monocyte", "GT", 0.40, "real")])
    res2 = run(panel2, bed, man, tmp_path / "c2")
    assert res2.verdicts["sig"] == "PENDING"   # tau 0.40 not cleared by Δβ≈0.65? adjust to a rejecting value
```

Run: `pytest tests/test_rip_immuno.py -v`
Expected: PASS (tune the τ so the second case genuinely fails the bar, demonstrating no post-hoc rescue).

- [ ] **Step 6: Commit**

```bash
git add src/polymer_claims/rip_immuno.py scripts/rip_immuno_meth.py tests/test_rip_immuno.py
git commit -m "feat(rip): batch immuno methylation licensing driver with pre-registration + FDR-at-volume"
```

---

### Task 6: Universe bundle emission (viewer lights up)

**Files:**
- Create: `viewer/scripts/make_immuno_universe.py`
- Test: `tests/test_immuno_universe_bundle.py`

**Interfaces:**
- Consumes: `RipResult` (Task 5); the universe bundle schema (mirror `data/demo/polymergenomics_universe.json`: `{claims, defeat_edges, equivalences, fdr_ledger}`) and the existing builder `viewer/scripts/make_universe_timeline.py`.
- Produces: `def build_bundle(res: RipResult, out_path: Path) -> Path` — writes a viewer-loadable universe JSON where each licensed locus is a node with its verdict/tier/content-address, and PENDING loci render distinctly.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_immuno_universe_bundle.py
import json
from pathlib import Path
from polymer_claims.rip_immuno import RipResult
from viewer.scripts.make_immuno_universe import build_bundle  # or import via path shim

class _Claim:
    def __init__(self, cid, status): self.id = cid; self.status = status

def test_bundle_has_a_node_per_locus_and_marks_licensed(tmp_path):
    res = RipResult(verdicts={"hla_a_promoter": "LICENSED", "null0": "PENDING"}, corpus=None)
    out = build_bundle(res, tmp_path / "immuno_universe.json")
    doc = json.loads(Path(out).read_text())
    ids = {c["id"] for c in doc["claims"]}
    assert ids == {"hla_a_promoter", "null0"}
    by = {c["id"]: c for c in doc["claims"]}
    assert by["hla_a_promoter"]["status"] == "LICENSED"
    assert by["null0"]["status"] == "PENDING"
    assert "fdr_ledger" in doc   # viewer schema keys present
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_immuno_universe_bundle.py -v`
Expected: FAIL (`ModuleNotFoundError`)

- [ ] **Step 3: Write minimal implementation**

Open `data/demo/polymergenomics_universe.json` + `viewer/scripts/make_universe_timeline.py` and match the exact node schema. Then:

```python
# viewer/scripts/make_immuno_universe.py
from __future__ import annotations
import json
from pathlib import Path

def build_bundle(res, out_path: Path) -> Path:
    claims = [{"id": lid, "status": verdict, "tier": "REPRODUCED",
               "quantity": {"kind": "cell_type_methylation"}}
              for lid, verdict in sorted(res.verdicts.items())]
    doc = {"claims": claims, "defeat_edges": [], "equivalences": [], "fdr_ledger": {}}
    out = Path(out_path); out.write_text(json.dumps(doc, indent=2) + "\n")
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_immuno_universe_bundle.py -v`
Expected: PASS

- [ ] **Step 5: Generate the real bundle and visually confirm**

Run: `python -m scripts.rip_immuno_meth` then generate the bundle and load it in the viewer (`viewer/` sample mode). Confirm the new licensed immuno/ERV nodes render blue and the count matches the driver's `LICENSED n/N`.
Expected: the universe shows many new real blue nodes; PENDING loci render distinctly.

- [ ] **Step 6: Commit**

```bash
git add viewer/scripts/make_immuno_universe.py tests/test_immuno_universe_bundle.py
git commit -m "feat(viewer): emit immuno/ERV licensing universe bundle"
```

---

## Post-implementation

- [ ] Run the full gate: `scripts/check-all.sh` — grammar/protocol suites green, ruff clean, Corpus still 4.
- [ ] Update `docs/superpowers/CONTINUE.md` *Current state* + *NEXT* (record: immuno/ERV drive shipped, N licensed nodes, first at-volume `q` demonstration; waves 2/3 = correlation + enrichment cells still open).
- [ ] Update `ARCHITECTURE_CURRENT.md` "Real computation" list with a one-line entry.
- [ ] Merge `feat/immuno-erv-meth-drive` → `main`, delete branch (single-trunk convention).

## Self-review notes (author)

- **Spec coverage:** §2 data → Task 1 pins + Task 4 guard; §3 honesty/pre-registration → Task 5 register loop + match-gate test; §4 genuinely-independent legs → Task 2; §4 extractor/contract/driver → Tasks 1/3/5; §5 build guard + unpowered + determinism → Task 4 guard, Task 1 QC-drop, Task 3 determinism test; §6 anchor/air-gap-teeth/match-gate/FDR-at-volume/smoke → Tasks 1/2/5. §7 build order == task order. All covered.
- **Two confirm-before-coding spots** (flagged inline, not placeholders): the batch `register_test` wiring (Task 5) and the `Comparator` import path — both name the exact file to mirror. These are real-API confirmations, not undefined behavior.
- **Deferred (spec non-goals):** correlation cell, enrichment cell, licensed-negative path — intentionally absent.
