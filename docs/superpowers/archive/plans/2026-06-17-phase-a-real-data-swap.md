# Phase A — Real-Data Swap (n-DMP on real TCGA-LAML betas) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** License the genome-wide n-DMP count on real TCGA-LAML HM450 betas (IDH1/2-mut vs WT) through the existing gate at the REPRODUCED tier, converting the system's central proof from *exercised* (synthetic) to *earned*.

**Architecture:** Every compute seam (`n_dmps_claim`, the two legs, `load_contract`→`dimnames_hash`, `materialization_map`, `evidence_map`, `count_enrichment_evalue`) is **reused unchanged**. New code lives only in three places: (1) a new `CANONICAL_HM450_V1` `AnalysisProfile` (apparatus); (2) a `polymer-claims ingest tcga-laml` CLI command that fetches GDC open-access files by pinned UUID and transforms them into an on-disk SE-Contract the existing loader reads; (3) wiring + tests. The generated contract is written into `src/polymer_claims/contracts/` (where `load_contract` looks) and **gitignored**; raw GDC downloads cache in `./data/` (also gitignored). Nothing real is ever committed.

**Tech Stack:** Python 3 (stdlib + numpy behind the `[embed]` extra), pydantic models, argparse CLI, pytest + ruff, `uv` for envs. GDC REST API (`https://api.gdc.cancer.gov/data/<uuid>`), open-access (no auth).

## Global Constraints

- `grammar/` + `protocol/` stay **pure/deterministic + numpy-free**; all new impurity (GDC fetch, transform) is **umbrella-side only** (`src/polymer_claims/`). The grammar spine never imports the new code.
- `Corpus` stays exactly 4 collections; all models frozen `_Model`/`BaseModel` (`extra="forbid"`); collections are tuples; no `dict`/`list` model fields.
- New cross-cutting fields land **additive/optional** (`X | None = None`); opt-in features default to byte-identical behavior when off.
- numpy stays behind the `[embed]` extra; ingest **lazy-imports** numpy (base import stays numpy-free).
- The two n-DMP legs stay genuinely independent — the pure-Python pooled-t leg is **never** vectorized with numpy (that would collapse the air-gap).
- Tier is **REPRODUCED**; e-values are **not** multiplied (the §2E rule). No REPLICATED, no region-Δβ, no region/probe selection, no agent — all deferred.
- Tests: per-package `uv run pytest -q` + `uv run ruff check src tests`; full gate `scripts/check-all.sh`. TDD: failing test first. Commit frequently. Merge to `main` `--no-ff`, local-only.
- Data handling: fully local, nothing committed. Contract + raw downloads gitignored; real-data tests `skipif`-absent.
- Honesty over polish: the n-DMP pooled-t is **unadjusted** (no age/sex covariate, no cell-composition adjustment) — age/sex are carried in `col_data` for future use but not adjusted for. The profile must say so honestly (`covariates=()`, `cell_adjustment=None`).

---

### Task 1: The HM450 AnalysisProfile (`CANONICAL_HM450_V1`)

**Files:**
- Modify: `src/polymer_claims/profiles.py` (add the profile + register it in `_REGISTRY`)
- Test: `tests/test_hm450_profile.py` (create)

**Interfaces:**
- Consumes: `AnalysisProfile` (`analysis_profile.py:30`), `content_hash` (`analysis_profile.py:83`), `profile_oracle_id` (`analysis_profile.py:102`), `load_profile` (`profiles.py:100`).
- Produces: `CANONICAL_HM450_V1: AnalysisProfile` with `profile_id="canonical_hm450_grch38_v1"`, `version="1"`; resolvable via `load_profile("canonical_hm450_grch38_v1", "1")`; `profile_oracle_id(...) == "canonical_hm450_grch38_v1@1"`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_hm450_profile.py
from __future__ import annotations

from polymer_claims.analysis_profile import content_hash, profile_oracle_id
from polymer_claims.profiles import CANONICAL_EPICV2_V1, CANONICAL_HM450_V1, load_profile


def test_hm450_profile_registered_and_resolvable():
    assert load_profile("canonical_hm450_grch38_v1", "1") is CANONICAL_HM450_V1
    assert profile_oracle_id(CANONICAL_HM450_V1) == "canonical_hm450_grch38_v1@1"


def test_hm450_profile_is_hm450_hg38():
    assert CANONICAL_HM450_V1.array_type == "HM450"
    assert CANONICAL_HM450_V1.genome_assembly == "hg38"


def test_hm450_profile_hash_stable_and_distinct_from_epicv2():
    # deterministic within Python
    assert content_hash(CANONICAL_HM450_V1) == content_hash(CANONICAL_HM450_V1)
    # spans platforms -> a DIFFERENT content-address than the EPICv2 apparatus
    assert content_hash(CANONICAL_HM450_V1) != content_hash(CANONICAL_EPICV2_V1)


def test_hm450_profile_is_honest_about_unadjusted_method():
    # Phase A n-DMP is an unadjusted two-group pooled-t; the apparatus must say so.
    assert CANONICAL_HM450_V1.covariates == ()
    assert CANONICAL_HM450_V1.cell_adjustment is None
    assert CANONICAL_HM450_V1.dmp_method == "two_group_pooled_t"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/zbb2/Desktop/polymer-claims && uv run pytest tests/test_hm450_profile.py -q`
Expected: FAIL with `ImportError: cannot import name 'CANONICAL_HM450_V1'`.

- [ ] **Step 3: Add the profile and register it**

In `src/polymer_claims/profiles.py`, after the `CANONICAL_EPICV2_V1` definition (line ~93) and **before** the `_REGISTRY` assignment (line ~95), insert:

```python
# The GDC HM450 Level-3 (SeSAMe-processed) apparatus, GRCh38. Distinct platform + distinct
# content-address from the EPICv2 profile -> the apparatus abstraction spans platforms. The
# differential method is the in-repo unadjusted two-group pooled-t (NOT limma): Phase A's n-DMP
# count licenses on per-probe p<alpha with corpus-level FDR governed by the e-LOND ledger, not a
# per-probe BH adjustment. Age/Sex are carried in the contract but NOT adjusted for (honest
# simplification — see plan Global Constraints).
CANONICAL_HM450_V1 = AnalysisProfile(
    profile_id="canonical_hm450_grch38_v1",
    version="1",
    array_type="HM450",
    genome_assembly="hg38",
    manifest="sesameData::HM450.hg38.manifest",
    norm_package="sesame",
    norm_method="openSesame",
    norm_prep="QCDPB",
    detection_threshold=0.05,
    detection_rule="pOOBAH_p_le",
    sample_fail_threshold=0.05,
    cross_reactive_source="cross_reactive_probes_hm450_v1",
    cross_reactive_file_hash="sha256:1111111111111111111111111111111111111111111111111111111111111111",
    cross_reactive_n_probes=29233,
    snp_method="minfi:dropLociWithSnps[SBE,CpG]",
    snp_maf=0.01,
    sex_chrom="removed",
    replicate_collapse="none",
    test_on="M_value",
    clamp_lower=1e-6,
    clamp_upper=0.999999,
    design_formula="~ 0 + group",
    contrast="IDH_mut - WT",
    covariates=(),
    batch_correction=None,
    cell_adjustment=None,
    dmp_method="two_group_pooled_t",
    dmp_adjust_method="none",
    fdr_threshold=0.05,
    delta_beta_threshold=None,
    dmr_method=None,
    seed=None,
    engine_version="gdc-sesame-level3/python-pooled-t/polymer-claims",
)
```

Then change the `_REGISTRY` line (was: `for p in (PINNED_DESIGN_V1, CANONICAL_EPICV2_V1)`) to include the new profile:

```python
_REGISTRY: dict[tuple[str, str], AnalysisProfile] = {
    (p.profile_id, p.version): p
    for p in (PINNED_DESIGN_V1, CANONICAL_EPICV2_V1, CANONICAL_HM450_V1)
}
```

> **Implementation note:** the `cross_reactive_*` values + the SeSAMe method strings are placeholders honest to the GDC SeSAMe Level-3 pipeline; verify the exact `norm_prep`/`detection_rule` strings against current GDC DNA-methylation pipeline docs and swap the cross-reactive list hash for the real list when available. The *values* affect only the content-address, not the computation.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_hm450_profile.py -q`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add src/polymer_claims/profiles.py tests/test_hm450_profile.py
git commit -m "feat: CANONICAL_HM450_V1 apparatus profile (GDC SeSAMe Level-3, hg38)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: Ingest helpers — MAF→group derivation + QC probe filter

**Files:**
- Create: `src/polymer_claims/ingest/__init__.py` (empty package marker)
- Create: `src/polymer_claims/ingest/transform.py`
- Test: `tests/test_ingest_transform.py` (create)

**Interfaces:**
- Produces:
  - `derive_groups(maf_rows: list[dict], all_case_ids: list[str]) -> dict[str, str]` — maps each case id to `"IDH_mut"` (any IDH1 R132* / IDH2 R140* / IDH2 R172* somatic variant) or `"WT"`.
  - `qc_filter(betas: dict[str, dict[str, float]], row_meta: dict[str, dict]) -> list[str]` — returns the sorted list of probe ids that pass genome-wide QC: drop any probe with a missing/NaN beta in any sample, and drop sex-chromosome probes (`chr` in `{"chrX","chrY"}`). (Cross-reactive removal is recorded by the profile; the demo QC applies the NA + sex-chrom rules that the on-disk betas can express.)

- [ ] **Step 1: Write the failing test**

```python
# tests/test_ingest_transform.py
from __future__ import annotations

import math

from polymer_claims.ingest.transform import derive_groups, qc_filter


def test_derive_groups_flags_idh_hotspots():
    maf = [
        {"Hugo_Symbol": "IDH1", "HGVSp_Short": "p.R132H", "Tumor_Sample_Barcode": "TCGA-AB-2802-03A"},
        {"Hugo_Symbol": "IDH2", "HGVSp_Short": "p.R140Q", "Tumor_Sample_Barcode": "TCGA-AB-2803-03A"},
        {"Hugo_Symbol": "IDH2", "HGVSp_Short": "p.R172K", "Tumor_Sample_Barcode": "TCGA-AB-2804-03A"},
        {"Hugo_Symbol": "FLT3", "HGVSp_Short": "p.D835Y", "Tumor_Sample_Barcode": "TCGA-AB-2805-03A"},
        {"Hugo_Symbol": "IDH1", "HGVSp_Short": "p.G123S", "Tumor_Sample_Barcode": "TCGA-AB-2806-03A"},  # non-hotspot
    ]
    cases = ["TCGA-AB-2802", "TCGA-AB-2803", "TCGA-AB-2804", "TCGA-AB-2805", "TCGA-AB-2806", "TCGA-AB-2807"]
    groups = derive_groups(maf, cases)
    assert groups["TCGA-AB-2802"] == "IDH_mut"
    assert groups["TCGA-AB-2803"] == "IDH_mut"
    assert groups["TCGA-AB-2804"] == "IDH_mut"
    assert groups["TCGA-AB-2805"] == "WT"   # FLT3 only
    assert groups["TCGA-AB-2806"] == "WT"   # IDH1 non-hotspot
    assert groups["TCGA-AB-2807"] == "WT"   # no mutation row at all


def test_qc_filter_drops_na_and_sex_chrom_probes():
    betas = {
        "cg01": {"s1": 0.4, "s2": 0.5},          # keep
        "cg02": {"s1": float("nan"), "s2": 0.5}, # drop (NaN)
        "cg03": {"s1": 0.4, "s2": 0.6},          # drop (chrX via row_meta)
        "cg04": {"s1": 0.2, "s2": 0.3},          # keep
    }
    row_meta = {
        "cg01": {"chr": "chr1", "pos": 100},
        "cg02": {"chr": "chr1", "pos": 200},
        "cg03": {"chr": "chrX", "pos": 300},
        "cg04": {"chr": "chr2", "pos": 400},
    }
    kept = qc_filter(betas, row_meta)
    assert kept == ["cg01", "cg04"]
    # determinism
    assert all(not math.isnan(betas[p]["s1"]) for p in kept)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_ingest_transform.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'polymer_claims.ingest'`.

- [ ] **Step 3: Create the package + helpers**

Create `src/polymer_claims/ingest/__init__.py`:

```python
"""Phase A: real-data ingestion (GDC TCGA-LAML HM450 -> on-disk SE-Contract).
Umbrella/impure ONLY (network + filesystem). Not imported by grammar/protocol."""
```

Create `src/polymer_claims/ingest/transform.py`:

```python
"""Pure transform helpers: GDC-parsed structures -> SE-Contract pieces.
No network, no numpy import at module load (numpy is lazy-imported only where a large matrix
is assembled in build_contract). Unit-tested on small synthetic fixtures."""
from __future__ import annotations

import math

# IDH hotspot residues that license the IDH_mut grouping (the AML hypermethylation driver).
_IDH_HOTSPOTS = {
    ("IDH1", "R132"),
    ("IDH2", "R140"),
    ("IDH2", "R172"),
}
_SEX_CHROMS = {"chrX", "chrY"}


def _case_id(barcode: str) -> str:
    """TCGA barcode -> 12-char case (patient) id, e.g. 'TCGA-AB-2802-03A' -> 'TCGA-AB-2802'."""
    return "-".join(barcode.split("-")[:3])


def _is_idh_hotspot(hugo: str, hgvsp_short: str) -> bool:
    """True iff (gene, residue-number) is a licensing IDH hotspot. 'p.R132H' -> ('IDH1','R132')."""
    aa = hgvsp_short[2:] if hgvsp_short.startswith("p.") else hgvsp_short
    # strip the leading ref AA + trailing alt AA -> 'R132H' -> residue token 'R132'
    if len(aa) < 2 or not aa[0].isalpha():
        return False
    i = 1
    while i < len(aa) and aa[i].isdigit():
        i += 1
    residue = aa[:i]  # e.g. 'R132'
    return (hugo, residue) in _IDH_HOTSPOTS


def derive_groups(maf_rows: list[dict], all_case_ids: list[str]) -> dict[str, str]:
    """Each case -> 'IDH_mut' (any IDH hotspot somatic variant) else 'WT'. Cases absent from the
    MAF are 'WT'. Keyed by 12-char case id."""
    mutated: set[str] = set()
    for r in maf_rows:
        if _is_idh_hotspot(r["Hugo_Symbol"], r["HGVSp_Short"]):
            mutated.add(_case_id(r["Tumor_Sample_Barcode"]))
    return {cid: ("IDH_mut" if cid in mutated else "WT") for cid in all_case_ids}


def qc_filter(betas: dict[str, dict[str, float]], row_meta: dict[str, dict]) -> list[str]:
    """Genome-wide QC: drop probes with any NaN beta across samples, and sex-chromosome probes.
    Returns the kept probe ids, sorted (deterministic)."""
    kept = []
    for probe, by_sample in betas.items():
        if row_meta.get(probe, {}).get("chr") in _SEX_CHROMS:
            continue
        if any(math.isnan(v) for v in by_sample.values()):
            continue
        kept.append(probe)
    return sorted(kept)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_ingest_transform.py -q`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add src/polymer_claims/ingest/__init__.py src/polymer_claims/ingest/transform.py tests/test_ingest_transform.py
git commit -m "feat: ingest helpers — IDH-hotspot grouping + genome-wide QC filter

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: Build the on-disk SE-Contract (and verify it round-trips through `load_contract`)

**Files:**
- Modify: `src/polymer_claims/ingest/transform.py` (add `build_contract`)
- Test: `tests/test_ingest_build_contract.py` (create)

**Interfaces:**
- Consumes: `derive_groups`, `qc_filter` (Task 2); `canonical_sha256` (`polymer_claims._hashing`); `load_contract`, `clear_contract_cache` (`polymer_claims.contracts`).
- Produces:
  - `build_contract(out_dir, *, uid_stem="tcga_laml_idh", betas, row_meta, groups, clinical, sample_ids) -> str` — writes `{uid_stem}.json` + `{uid_stem}.betas.tsv` into `out_dir`, returns the contract uid `f"{uid_stem}@1"`. The manifest matches the shape `load_contract` reads (keys: `uid`, `dim`, `assays`, `col_data`, `row_data`, `metadata`); `col_data` carries `sample_id`, `Sample_Group`, `Age`, `Sex`; `row_data` carries `feature_id`, `chr`, `pos` for QC-passing probes; `metadata` = `{"genome_assembly": "hg38", "array": "HM450"}`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_ingest_build_contract.py
from __future__ import annotations

import polymer_claims.contracts as contracts_mod
from polymer_claims._hashing import canonical_sha256
from polymer_claims.contracts import clear_contract_cache, load_contract
from polymer_claims.ingest.transform import build_contract


def _tiny_inputs():
    sample_ids = ["TCGA-AB-2802", "TCGA-AB-2803", "TCGA-AB-2804", "TCGA-AB-2805"]
    betas = {
        "cg01": {"TCGA-AB-2802": 0.8, "TCGA-AB-2803": 0.82, "TCGA-AB-2804": 0.2, "TCGA-AB-2805": 0.22},
        "cg02": {"TCGA-AB-2802": 0.5, "TCGA-AB-2803": 0.51, "TCGA-AB-2804": 0.49, "TCGA-AB-2805": 0.5},
        "cgX1": {"TCGA-AB-2802": 0.4, "TCGA-AB-2803": 0.4, "TCGA-AB-2804": 0.4, "TCGA-AB-2805": 0.4},  # chrX -> dropped
    }
    row_meta = {
        "cg01": {"chr": "chr1", "pos": 1000},
        "cg02": {"chr": "chr2", "pos": 2000},
        "cgX1": {"chr": "chrX", "pos": 3000},
    }
    groups = {"TCGA-AB-2802": "IDH_mut", "TCGA-AB-2803": "IDH_mut", "TCGA-AB-2804": "WT", "TCGA-AB-2805": "WT"}
    clinical = {
        "TCGA-AB-2802": {"Age": 55, "Sex": "male"},
        "TCGA-AB-2803": {"Age": 60, "Sex": "female"},
        "TCGA-AB-2804": {"Age": 45, "Sex": "male"},
        "TCGA-AB-2805": {"Age": 70, "Sex": "female"},
    }
    return sample_ids, betas, row_meta, groups, clinical


def test_build_contract_round_trips_through_load_contract(tmp_path, monkeypatch):
    sample_ids, betas, row_meta, groups, clinical = _tiny_inputs()
    uid = build_contract(
        tmp_path, betas=betas, row_meta=row_meta, groups=groups,
        clinical=clinical, sample_ids=sample_ids,
    )
    assert uid == "tcga_laml_idh@1"

    # Point the loader at tmp_path and resolve the freshly-written contract.
    monkeypatch.setattr(contracts_mod, "_DIR", tmp_path)
    clear_contract_cache()
    ref = load_contract("se:tcga_laml_idh@1")

    assert ref.genome_assembly == "hg38"
    # the chrX probe was dropped by QC; only cg01,cg02 remain (sorted)
    expected_dimnames = canonical_sha256(
        {"feature_ids": ["cg01", "cg02"], "sample_ids": sample_ids}
    )
    assert ref.dimnames_hash == expected_dimnames
    clear_contract_cache()  # leave the cache clean for other tests
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_ingest_build_contract.py -q`
Expected: FAIL with `ImportError: cannot import name 'build_contract'`.

- [ ] **Step 3: Implement `build_contract`**

Append to `src/polymer_claims/ingest/transform.py`:

```python
import json
from pathlib import Path


def build_contract(
    out_dir,
    *,
    uid_stem: str = "tcga_laml_idh",
    betas: dict[str, dict[str, float]],
    row_meta: dict[str, dict],
    groups: dict[str, str],
    clinical: dict[str, dict],
    sample_ids: list[str],
) -> str:
    """Assemble + write the SE-Contract (manifest JSON + betas TSV) the existing load_contract reads.
    Probes are the genome-wide QC-passing set (sorted); samples keep caller order. Returns the uid."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    probes = qc_filter(betas, row_meta)  # genome-wide, sorted, deterministic

    manifest = {
        "uid": f"{uid_stem}@1",
        "dim": [len(probes), len(sample_ids)],
        "assays": [{"name": "beta", "ref": f"{uid_stem}.betas.tsv"}],
        "col_data": [
            {
                "sample_id": s,
                "Sample_Group": groups[s],
                "Age": clinical.get(s, {}).get("Age"),
                "Sex": clinical.get(s, {}).get("Sex"),
            }
            for s in sample_ids
        ],
        "row_data": [
            {"feature_id": p, "chr": row_meta[p]["chr"], "pos": row_meta[p]["pos"]}
            for p in probes
        ],
        "metadata": {"genome_assembly": "hg38", "array": "HM450"},
    }
    (out_dir / f"{uid_stem}.json").write_text(json.dumps(manifest, indent=2))

    # betas TSV: header = 'feature_id' + sample ids; one row per probe.
    lines = ["\t".join(["feature_id", *sample_ids])]
    for p in probes:
        row = betas[p]
        lines.append("\t".join([p, *(f"{row[s]:.4f}" for s in sample_ids)]))
    (out_dir / f"{uid_stem}.betas.tsv").write_text("\n".join(lines) + "\n")

    return f"{uid_stem}@1"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_ingest_build_contract.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/polymer_claims/ingest/transform.py tests/test_ingest_build_contract.py
git commit -m "feat: build on-disk SE-Contract from parsed GDC inputs (round-trips load_contract)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: GDC file parsers (betas / MAF / clinical)

**Files:**
- Create: `src/polymer_claims/ingest/gdc_parse.py`
- Test: `tests/test_ingest_gdc_parse.py` (create)

**Interfaces:**
- Produces:
  - `parse_beta_file(text: str) -> dict[str, float]` — one GDC per-aliquot methylation beta file → `{probe_id: beta}` (cols 0,1; skips a header row if col 1 isn't a float; `"NA"`/empty → `float('nan')`).
  - `parse_maf(text: str) -> list[dict]` — a GDC MAF (skips `#` comment lines, reads the header) → list of `{"Hugo_Symbol","HGVSp_Short","Tumor_Sample_Barcode"}` dicts.
  - `parse_clinical(text: str) -> dict[str, dict]` — a GDC `clinical.tsv` → `{case_id: {"Age": int|None, "Sex": str}}` keyed by 12-char case id (from `case_submitter_id`), reading `age_at_index` + `gender`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_ingest_gdc_parse.py
from __future__ import annotations

import math

from polymer_claims.ingest.gdc_parse import parse_beta_file, parse_clinical, parse_maf


def test_parse_beta_file_reads_probe_beta_and_na():
    text = "Composite Element REF\tBeta_value\ncg01\t0.83\ncg02\tNA\ncg03\t0.20\n"
    out = parse_beta_file(text)
    assert out["cg01"] == 0.83
    assert math.isnan(out["cg02"])
    assert out["cg03"] == 0.20


def test_parse_maf_skips_comments_and_reads_named_columns():
    text = (
        "#version 2.4\n"
        "Hugo_Symbol\tHGVSp_Short\tTumor_Sample_Barcode\n"
        "IDH1\tp.R132H\tTCGA-AB-2802-03A-01D\n"
        "FLT3\tp.D835Y\tTCGA-AB-2805-03A-01D\n"
    )
    rows = parse_maf(text)
    assert len(rows) == 2
    assert rows[0] == {
        "Hugo_Symbol": "IDH1", "HGVSp_Short": "p.R132H",
        "Tumor_Sample_Barcode": "TCGA-AB-2802-03A-01D",
    }


def test_parse_clinical_reads_age_and_sex_by_case():
    text = (
        "case_submitter_id\tage_at_index\tgender\n"
        "TCGA-AB-2802\t55\tmale\n"
        "TCGA-AB-2803\t'--\tfemale\n"
    )
    out = parse_clinical(text)
    assert out["TCGA-AB-2802"] == {"Age": 55, "Sex": "male"}
    assert out["TCGA-AB-2803"] == {"Age": None, "Sex": "female"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_ingest_gdc_parse.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'polymer_claims.ingest.gdc_parse'`.

- [ ] **Step 3: Implement the parsers**

Create `src/polymer_claims/ingest/gdc_parse.py`:

```python
"""Parsers for the three GDC open-access file types. Tolerant by column NAME (GDC harmonized
headers are stable, but locate columns by name, not position, where a header exists). Pure; no I/O."""
from __future__ import annotations


def _to_float(tok: str) -> float:
    tok = tok.strip()
    if tok in ("", "NA", "NaN", ".", "'--"):
        return float("nan")
    return float(tok)


def parse_beta_file(text: str) -> dict[str, float]:
    """GDC per-aliquot methylation beta file -> {probe_id: beta}. Cols 0,1. A first row whose
    2nd column isn't a float is treated as a header and skipped."""
    out: dict[str, float] = {}
    for i, line in enumerate(text.splitlines()):
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        if i == 0:
            try:
                float(parts[1])
            except ValueError:
                continue  # header row
        out[parts[0].strip()] = _to_float(parts[1])
    return out


def parse_maf(text: str) -> list[dict]:
    """GDC MAF -> list of {Hugo_Symbol, HGVSp_Short, Tumor_Sample_Barcode}. Skips '#' comments."""
    rows: list[dict] = []
    header: list[str] | None = None
    want = ("Hugo_Symbol", "HGVSp_Short", "Tumor_Sample_Barcode")
    for line in text.splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        parts = line.split("\t")
        if header is None:
            header = parts
            continue
        rec = dict(zip(header, parts))
        rows.append({k: rec.get(k, "") for k in want})
    return rows


def parse_clinical(text: str) -> dict[str, dict]:
    """GDC clinical.tsv -> {case_id: {'Age': int|None, 'Sex': str}}. Reads case_submitter_id,
    age_at_index, gender by name."""
    out: dict[str, dict] = {}
    header: list[str] | None = None
    for line in text.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        if header is None:
            header = parts
            continue
        rec = dict(zip(header, parts))
        case = rec.get("case_submitter_id", "").strip()
        if not case:
            continue
        age_tok = rec.get("age_at_index", "").strip()
        age = int(age_tok) if age_tok.isdigit() else None
        out[case] = {"Age": age, "Sex": rec.get("gender", "").strip()}
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_ingest_gdc_parse.py -q`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add src/polymer_claims/ingest/gdc_parse.py tests/test_ingest_gdc_parse.py
git commit -m "feat: GDC file parsers (betas / MAF / clinical)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 5: GDC fetch (pinned UUIDs + MD5 verify) + the `ingest tcga-laml` CLI command

**Files:**
- Create: `src/polymer_claims/ingest/gdc_fetch.py`
- Create: `src/polymer_claims/ingest/tcga_laml_manifest.json` (the committed, pinned UUID recipe — populated by a one-time GDC query during this task)
- Create: `src/polymer_claims/ingest/tcga_laml.py` (orchestrator: fetch → parse → build_contract into the package `contracts/` dir)
- Modify: `src/polymer_claims/cli.py` (add `_cmd_ingest` + the `ingest` subparser)
- Modify: `.gitignore` (ignore the raw cache + the generated real contract)
- Test: `tests/test_ingest_gdc_fetch.py` (create — URL + MD5 logic, no network)
- Test: `tests/test_cli_ingest.py` (create — the subcommand parses + dispatches)

**Interfaces:**
- Consumes: `parse_beta_file`/`parse_maf`/`parse_clinical` (Task 4); `derive_groups`/`build_contract` (Tasks 2-3); the contracts dir `polymer_claims.contracts._DIR`.
- Produces:
  - `gdc_data_url(uuid: str) -> str` → `f"https://api.gdc.cancer.gov/data/{uuid}"`.
  - `verify_md5(data: bytes, expected_hex: str) -> None` — raises `ValueError` on mismatch.
  - `_cmd_ingest(args) -> int` dispatched by `polymer-claims ingest tcga-laml`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_ingest_gdc_fetch.py
from __future__ import annotations

import hashlib

import pytest

from polymer_claims.ingest.gdc_fetch import gdc_data_url, verify_md5


def test_gdc_data_url():
    assert gdc_data_url("abc-123") == "https://api.gdc.cancer.gov/data/abc-123"


def test_verify_md5_passes_and_fails():
    data = b"hello"
    verify_md5(data, hashlib.md5(data).hexdigest())  # no raise
    with pytest.raises(ValueError):
        verify_md5(data, "deadbeef")
```

```python
# tests/test_cli_ingest.py
from __future__ import annotations

from polymer_claims.cli import _build_parser


def test_ingest_tcga_laml_subcommand_parses():
    parser = _build_parser()
    args = parser.parse_args(["ingest", "tcga-laml", "--data-dir", "/tmp/x"])
    assert args.command == "ingest"
    assert args.dataset == "tcga-laml"
    assert args.data_dir == "/tmp/x"
    assert callable(args.func)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_ingest_gdc_fetch.py tests/test_cli_ingest.py -q`
Expected: FAIL (`No module named 'polymer_claims.ingest.gdc_fetch'`; and the parser has no `ingest` subcommand).

- [ ] **Step 3: Implement fetch + orchestrator + manifest + gitignore**

Create `src/polymer_claims/ingest/gdc_fetch.py`:

```python
"""GDC open-access fetch by pinned UUID + MD5 fixity. Network I/O via urllib (stdlib).
The pinned UUIDs live in tcga_laml_manifest.json (committed); the data they fetch is gitignored."""
from __future__ import annotations

import hashlib
import json
import urllib.request
from pathlib import Path

_GDC_DATA = "https://api.gdc.cancer.gov/data/"


def gdc_data_url(uuid: str) -> str:
    return f"{_GDC_DATA}{uuid}"


def verify_md5(data: bytes, expected_hex: str) -> None:
    got = hashlib.md5(data).hexdigest()
    if got != expected_hex:
        raise ValueError(f"MD5 mismatch: got {got}, expected {expected_hex}")


def load_pinned_manifest() -> dict:
    """The committed pinned-UUID recipe shipped alongside this module."""
    return json.loads((Path(__file__).parent / "tcga_laml_manifest.json").read_text())


def fetch_file(uuid: str, md5: str, dest: Path) -> bytes:
    """Download one GDC file by UUID, verify MD5, cache to dest (skip re-download if cached+valid)."""
    if dest.is_file():
        cached = dest.read_bytes()
        if hashlib.md5(cached).hexdigest() == md5:
            return cached
    with urllib.request.urlopen(gdc_data_url(uuid)) as resp:  # noqa: S310 — fixed GDC https host
        data = resp.read()
    verify_md5(data, md5)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    return data
```

Create `src/polymer_claims/ingest/tcga_laml_manifest.json` with this **shape** (entries are placeholders — populated in Step 3b):

```json
{
  "project": "TCGA-LAML",
  "platform": "Illumina Human Methylation 450",
  "data_release": "TODO: pin the GDC data release tag at population time",
  "betas": [
    {"uuid": "PLACEHOLDER-UUID", "md5": "PLACEHOLDER-MD5", "case_id": "TCGA-AB-2802", "filename": "PLACEHOLDER.txt"}
  ],
  "maf": {"uuid": "PLACEHOLDER-UUID", "md5": "PLACEHOLDER-MD5", "filename": "TCGA-LAML.maf.gz"},
  "clinical": {"uuid": "PLACEHOLDER-UUID", "md5": "PLACEHOLDER-MD5", "filename": "clinical.tsv"}
}
```

Create `src/polymer_claims/ingest/tcga_laml.py`:

```python
"""Orchestrate: fetch pinned GDC files -> parse -> build the on-disk SE-Contract into the package
contracts/ dir (where load_contract reads it). The contract is gitignored; nothing real is committed."""
from __future__ import annotations

import gzip
from pathlib import Path

from polymer_claims import contracts as _contracts
from polymer_claims.ingest.gdc_fetch import fetch_file, load_pinned_manifest
from polymer_claims.ingest.gdc_parse import parse_beta_file, parse_clinical, parse_maf
from polymer_claims.ingest.transform import _case_id, build_contract, derive_groups


def ingest_tcga_laml(data_dir: str) -> str:
    """Fetch + transform TCGA-LAML HM450 into se:tcga_laml_idh@1. Returns a one-line summary."""
    cache = Path(data_dir)
    man = load_pinned_manifest()

    # 1. betas: one file per case -> {case_id: {probe: beta}} and the union probe set + row meta.
    betas: dict[str, dict[str, float]] = {}
    sample_ids: list[str] = []
    for entry in man["betas"]:
        raw = fetch_file(entry["uuid"], entry["md5"], cache / entry["filename"])
        col = parse_beta_file(raw.decode("utf-8", errors="replace"))
        cid = entry["case_id"]
        sample_ids.append(cid)
        for probe, beta in col.items():
            betas.setdefault(probe, {})[cid] = beta

    # row_meta: probe -> chr/pos. The pinned manifest's per-probe annotation is platform-fixed;
    # for the demo we read it from the HM450 manifest sidecar if present, else default chr/pos 0.
    row_meta = {probe: {"chr": "chr1", "pos": 0} for probe in betas}  # see implementation note

    # 2. MAF -> IDH grouping.
    maf_raw = fetch_file(man["maf"]["uuid"], man["maf"]["md5"], cache / man["maf"]["filename"])
    maf_text = gzip.decompress(maf_raw).decode("utf-8") if man["maf"]["filename"].endswith(".gz") else maf_raw.decode("utf-8")
    groups = derive_groups(parse_maf(maf_text), [_case_id(s) for s in sample_ids])

    # 3. clinical -> Age/Sex.
    clin_raw = fetch_file(man["clinical"]["uuid"], man["clinical"]["md5"], cache / man["clinical"]["filename"])
    clinical = parse_clinical(clin_raw.decode("utf-8"))

    # 4. build the contract into the package contracts dir (gitignored).
    uid = build_contract(
        Path(_contracts.__file__).parent,
        betas=betas, row_meta=row_meta, groups=groups,
        clinical=clinical, sample_ids=sample_ids,
    )
    _contracts.clear_contract_cache()
    ref = _contracts.load_contract(f"se:{uid}")
    n_idh = sum(1 for g in groups.values() if g == "IDH_mut")
    return (
        f"ingested {uid}: {ref.dimnames_hash[:16]}… "
        f"({len(sample_ids)} samples, {ref.size} bytes; {n_idh} IDH_mut / {len(sample_ids) - n_idh} WT)"
    )
```

> **Implementation note (row_meta):** GDC's harmonized methylation beta files include `Chromosome`/`Start` annotation columns per probe; extend `parse_beta_file` to also return chr/pos (or read the HM450 manifest) and replace the `row_meta` stub so `qc_filter`'s sex-chromosome rule and the `row_data` annotation are real. The stub keeps the orchestrator runnable for the synthetic fixture path; the real chr/pos is required before the earned run.

Add `_cmd_ingest` to `src/polymer_claims/cli.py` (after `_cmd_validate`, ~line 90):

```python
def _cmd_ingest(args: argparse.Namespace) -> int:
    if args.dataset != "tcga-laml":
        print(f"unknown ingest dataset: {args.dataset!r}", file=sys.stderr)
        return 1
    from .ingest.tcga_laml import ingest_tcga_laml
    try:
        print(ingest_tcga_laml(args.data_dir))
    except Exception as exc:  # noqa: BLE001 — surface fetch/parse failures to the user
        print(f"ingest failed: {exc}", file=sys.stderr)
        return 1
    return 0
```

Register the subparser in `_build_parser` (after the `p_validate` block, ~line 304):

```python
    p_ingest = sub.add_parser("ingest", help="fetch + transform a real dataset into a local SE-Contract")
    p_ingest.add_argument("dataset", choices=("tcga-laml",), help="which dataset to ingest")
    p_ingest.add_argument("--data-dir", default="./data/tcga_laml", help="local cache dir for raw GDC files (gitignored)")
    p_ingest.set_defaults(func=_cmd_ingest)
```

Append to `.gitignore`:

```
# Phase A real-data: raw GDC cache + the generated real SE-Contract (never committed)
/data/
src/polymer_claims/contracts/tcga_laml_idh.json
src/polymer_claims/contracts/tcga_laml_idh.betas.tsv
```

- [ ] **Step 3b: Populate the pinned UUID manifest (one-time GDC query)**

Run a GDC query to resolve the open-access HM450 Level-3 beta files for TCGA-LAML, the open masked somatic MAF, and the clinical supplement, then write their UUIDs + MD5s + case ids into `tcga_laml_manifest.json`. Reference query (the GDC `files` endpoint filters on `cases.project.project_id=TCGA-LAML`, `data_type="Methylation Beta Value"`, `platform="Illumina Human Methylation 450"`, `access="open"`):

```bash
curl -s 'https://api.gdc.cancer.gov/files' -H 'Content-Type: application/json' -d '{
  "filters": {"op":"and","content":[
    {"op":"in","content":{"field":"cases.project.project_id","value":["TCGA-LAML"]}},
    {"op":"in","content":{"field":"data_type","value":["Methylation Beta Value"]}},
    {"op":"in","content":{"field":"platform","value":["Illumina Human Methylation 450"]}},
    {"op":"in","content":{"field":"access","value":["open"]}}
  ]},
  "fields":"file_id,file_name,md5sum,cases.submitter_id",
  "format":"TSV","size":"500"
}' > /tmp/laml_betas.tsv
```

Transcribe the resulting `file_id`/`md5sum`/`cases.submitter_id` rows into the `betas` array, and run the analogous queries for `data_format=MAF`/`data_type="Masked Somatic Mutation"` and the clinical supplement. Pin the GDC data-release tag in `data_release`. (This is a manual data step — its output is the committed recipe; no real data is committed.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_ingest_gdc_fetch.py tests/test_cli_ingest.py -q`
Expected: PASS (3 tests). (The fetch/orchestrator network path is exercised only by the manual real run + the skip-if-absent e2e in Task 6.)

- [ ] **Step 5: Commit**

```bash
git add src/polymer_claims/ingest/gdc_fetch.py src/polymer_claims/ingest/tcga_laml_manifest.json src/polymer_claims/ingest/tcga_laml.py src/polymer_claims/cli.py .gitignore tests/test_ingest_gdc_fetch.py tests/test_cli_ingest.py
git commit -m "feat: polymer-claims ingest tcga-laml (GDC fetch -> local SE-Contract)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 6: The earned-license acceptance test (skip-if-absent e2e on real betas)

**Files:**
- Create: `tests/test_tcga_laml_ndmp_e2e.py`

**Interfaces:**
- Consumes: `n_dmps_claim`, `NDmpTTestAdapter`, `NDmpOlsCoefAdapter`, `ndmp_independent_registry`, `_all_probe_ids` (`methyl_ndmp.py`); `profile_oracle_registry`, `profile_oracle_id` (`analysis_profile.py`); `CANONICAL_HM450_V1` (`profiles.py`); `materialization_map`, `evidence_map`; `load_contract` (`contracts`); `run_cycle`, `Corpus`, `FDRLedger` (the exact `_run` shape from `tests/test_n_dmps_e2e.py:18-26`).
- The contract `se:tcga_laml_idh@1` exists only after a local `ingest` run → the whole module is `skipif`-guarded on its absence.

- [ ] **Step 1: Write the test (it is the deliverable — no separate impl)**

```python
# tests/test_tcga_laml_ndmp_e2e.py
"""EARNED-MILESTONE e2e: license the genome-wide n-DMP count on REAL TCGA-LAML HM450 betas.
Skipped unless a local `polymer-claims ingest tcga-laml` has produced se:tcga_laml_idh@1
(nothing real is committed). Mirrors tests/test_n_dmps_e2e.py with the HM450 profile + real ref."""
from __future__ import annotations

import math

import pytest
from polymer_grammar import FDRLedger, IndependenceTier, MaterializationContext, Status
from polymer_protocol import Corpus, run_cycle

from polymer_claims.analysis_profile import profile_oracle_id, profile_oracle_registry
from polymer_claims.evidence import evidence_map
from polymer_claims.materialization import materialization_map
from polymer_claims.methyl_ndmp import (
    NDmpOlsCoefAdapter,
    NDmpTTestAdapter,
    _all_probe_ids,
    n_dmps_claim,
    ndmp_independent_registry,
)
from polymer_claims.profiles import CANONICAL_HM450_V1

_REF = "se:tcga_laml_idh@1"
_ADAPTERS = (NDmpTTestAdapter(), NDmpOlsCoefAdapter())
_BASE = MaterializationContext(id="M", api_version="v1", data_version="d1")
_ALPHA = 0.05


def _contract_present() -> bool:
    try:
        from polymer_claims.contracts import load_contract
        load_contract(_REF)
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _contract_present(), reason="run `polymer-claims ingest tcga-laml` first (no real data committed)")


def _run(claim):
    corpus = Corpus(claims=(claim,), fdr_ledger=FDRLedger(target_fdr=0.05))
    result = run_cycle(
        corpus, _ADAPTERS, _BASE,
        adapter_registry=ndmp_independent_registry(),
        oracles=profile_oracle_registry((CANONICAL_HM450_V1, "recomputable_public")),
        materializations=materialization_map(corpus, _BASE, profiles=(CANONICAL_HM450_V1,)),
        evidence=evidence_map(corpus),
    )
    return result, next(x for x in result.corpus.claims if x.id == claim.id)


def _k_null_floor() -> int:
    # pre-registered floor = the expected-under-null false-positive count (NOT read off the data).
    return math.ceil(_ALPHA * len(_all_probe_ids(_REF)))


def test_real_ndmp_licenses_reproduced_with_full_content_address():
    claim = n_dmps_claim(
        "tcga-laml-ndmp", ref=_REF,
        group_col="Sample_Group", level_a="WT", level_b="IDH_mut",
        alpha=_ALPHA, k=_k_null_floor(),
        oracle_ref=profile_oracle_id(CANONICAL_HM450_V1),
    )
    result, c = _run(claim)
    assert c.status == Status.LICENSED
    assert c.licensing.independence_tier is IndependenceTier.REPRODUCED
    # one e-test per claim lifetime; one discovery
    assert result.corpus.fdr_ledger.n_tests == 1
    assert result.corpus.fdr_ledger.n_discoveries == 1
    # the license records the FULL content-address: real dimnames_hash + HM450 profile_hash + run id
    sat = c.licensing.satisfactions[0]
    mctx = sat.materialization_context
    assert mctx.dimnames_hash and mctx.profile_hash and mctx.semantic_run_id
    # q is the honest headline — assert it is reported (a finite false-license rate)
    assert 0.0 <= result.corpus.fdr_ledger.q <= 1.0


def test_real_ndmp_legs_agree_on_the_integer_count():
    node = n_dmps_claim("tmp", ref=_REF, alpha=_ALPHA, k=1).evaluation_plan.graph.nodes[0]
    a = NDmpTTestAdapter().execute(node, (), _BASE).value
    b = NDmpOlsCoefAdapter().execute(node, (), _BASE).value
    assert a == b  # air-gap holds on real data


def test_real_ndmp_withholds_when_criterion_not_met():
    # Honest withholding: an unreachable pre-stated criterion (k = every probe is a DMP) -> REJECTED.
    claim = n_dmps_claim(
        "tcga-laml-ndmp-strict", ref=_REF,
        group_col="Sample_Group", level_a="WT", level_b="IDH_mut",
        alpha=_ALPHA, k=len(_all_probe_ids(_REF)),
        oracle_ref=profile_oracle_id(CANONICAL_HM450_V1),
    )
    _result, c = _run(claim)
    assert c.status != Status.LICENSED  # the gate correctly withholds; system working, not a failure
```

> **Interface check before running:** confirm the licensed-claim accessors against the grammar —
> `claim.licensing.independence_tier`, `claim.licensing.satisfactions[0].materialization_context`
> (fields `dimnames_hash`/`profile_hash`/`semantic_run_id`), and `fdr_ledger.q`. If a name differs,
> grep the grammar (`Licensing`, `Satisfaction`, `MaterializationContext`, `FDRLedger`) and adjust the
> assertions to the real attribute — the *behavior* asserted is fixed, only the accessor may move.

- [ ] **Step 2: Run it (skips without local data — that is success in CI)**

Run: `uv run pytest tests/test_tcga_laml_ndmp_e2e.py -q`
Expected (no local contract): `s` (skipped) — proves the guard works without committing data.

- [ ] **Step 3: Earn it locally (the actual milestone — run once, manually)**

```bash
uv run polymer-claims ingest tcga-laml --data-dir ./data/tcga_laml   # multi-minute fetch+transform
uv run pytest tests/test_tcga_laml_ndmp_e2e.py -q                    # now RUNS (not skipped)
```
Expected: PASS — the n-DMP count licenses at REPRODUCED on real betas, records the full
content-address, legs agree, and the strict-criterion run withholds. If the real run does **not**
license, that is the gate honestly withholding (acceptable outcome) — report `q` and the count, do not
force it.

- [ ] **Step 4: Commit (the test; never the data)**

```bash
git add tests/test_tcga_laml_ndmp_e2e.py
git commit -m "test: earned-milestone e2e — n-DMP licenses on real TCGA-LAML betas (skip-if-absent)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 7: Live-node fast-follow — `serve --tcga-laml`

**Files:**
- Modify: `src/polymer_claims/exec_adapters.py` (add `real_ndmp_seed_corpus`) — OR a new `src/polymer_claims/seed_methyl.py` if preferred; this plan uses `exec_adapters.py` to sit beside `real_data_seed_corpus`.
- Modify: `src/polymer_claims/cli.py` (`serve --tcga-laml` branch in `_cmd_serve` + the flag)
- Test: `tests/test_serve_tcga_laml.py` (create — seed builder + flag parse; the live loop is not unit-tested)

**Interfaces:**
- Consumes: `n_dmps_claim`, `NDmpTTestAdapter`, `NDmpOlsCoefAdapter`, `ndmp_independent_registry`, `_all_probe_ids` (`methyl_ndmp.py`); `profile_oracle_registry`, `profile_oracle_id`, `CANONICAL_HM450_V1`; `NodeRunner.from_seed` (`node.py`); the same `materialization_map(..., profiles=(CANONICAL_HM450_V1,))` + `evidence_map`.
- Produces: `real_ndmp_seed_corpus() -> tuple[Corpus, dict]` (corpus with the single real n-DMP claim; kwargs for `from_seed`).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_serve_tcga_laml.py
from __future__ import annotations

from polymer_claims.cli import _build_parser


def test_serve_has_tcga_laml_flag():
    parser = _build_parser()
    args = parser.parse_args(["serve", "--tcga-laml"])
    assert args.tcga_laml is True


def test_real_ndmp_seed_corpus_builds_one_real_claim():
    import polymer_claims.contracts as contracts_mod
    try:
        contracts_mod.load_contract("se:tcga_laml_idh@1")
    except Exception:
        import pytest
        pytest.skip("run `polymer-claims ingest tcga-laml` first")
    from polymer_claims.exec_adapters import real_ndmp_seed_corpus
    corpus, kwargs = real_ndmp_seed_corpus()
    assert len(corpus.claims) == 1
    assert corpus.claims[0].evaluation_plan.graph.nodes[0].impl == "methyl::n_dmps"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_serve_tcga_laml.py -q`
Expected: FAIL (`serve` has no `--tcga-laml`; `real_ndmp_seed_corpus` undefined).

- [ ] **Step 3: Implement the seed builder + serve wiring**

Append to `src/polymer_claims/exec_adapters.py`:

```python
def real_ndmp_seed_corpus():
    """Seed the live node with the single REAL-DATA n-DMP claim (genome-wide, REPRODUCED).
    Returns (corpus, from_seed_kwargs). Requires a local se:tcga_laml_idh@1 (ingest first)."""
    import math

    from polymer_grammar import FDRLedger
    from polymer_protocol import Corpus

    from .analysis_profile import profile_oracle_id
    from .methyl_ndmp import _all_probe_ids, n_dmps_claim
    from .profiles import CANONICAL_HM450_V1

    ref = "se:tcga_laml_idh@1"
    k = math.ceil(0.05 * len(_all_probe_ids(ref)))  # pre-registered null floor
    claim = n_dmps_claim(
        "tcga-laml-ndmp", ref=ref,
        group_col="Sample_Group", level_a="WT", level_b="IDH_mut",
        alpha=0.05, k=k, oracle_ref=profile_oracle_id(CANONICAL_HM450_V1),
        title="genome-wide n-DMPs, IDH-mut vs WT AML (real TCGA-LAML)",
    )
    corpus = Corpus(claims=(claim,), fdr_ledger=FDRLedger(target_fdr=0.05))
    return corpus, {"budget": 2.5}
```

In `src/polymer_claims/cli.py` `_cmd_serve`, add a branch **before** the `if getattr(args, "real_data", False):` block (~line 219):

```python
    if getattr(args, "tcga_laml", False):
        from .methyl_ndmp import NDmpOlsCoefAdapter, NDmpTTestAdapter, ndmp_independent_registry
        from .analysis_profile import profile_oracle_registry
        from .evidence import evidence_map
        from .materialization import materialization_map
        from .profiles import CANONICAL_HM450_V1
        from .exec_adapters import real_ndmp_seed_corpus
        corpus, seed_kwargs = real_ndmp_seed_corpus()
        runner = NodeRunner.from_seed(
            corpus,
            adapters=(NDmpTTestAdapter(), NDmpOlsCoefAdapter()),
            ctx=_CTX,
            scheduler_budget=args.budget,
            max_frames=args.max_frames,
            adapter_registry=ndmp_independent_registry(),
            oracles=profile_oracle_registry((CANONICAL_HM450_V1, "recomputable_public")),
            materializations=materialization_map(corpus, _CTX, profiles=(CANONICAL_HM450_V1,)),
            evidence=evidence_map(corpus),
            layout=args.layout,
            **seed_kwargs,
        )
        app = create_app(runner, interval=args.interval, origins=args.origins or None)
        uvicorn.run(app, host=args.host, port=args.port)
        return 0
```

Register the flag in the `p_serve` block (~line 363, beside `--real-data`):

```python
    p_serve.add_argument("--tcga-laml", action="store_true", help="seed the live node with the REAL TCGA-LAML genome-wide n-DMP claim (ingest first; one-shot compute, then displays)")
```

> **Interface check:** confirm `NodeRunner.from_seed` accepts `materializations=`/`evidence=` (the
> `--real-data` branch passes `adapter_registry`/`oracles`/`proposers` but not these). If `from_seed`
> does not thread `materializations`/`evidence` into its per-tick `run_cycle`, add them to its
> signature the same way `adapter_registry`/`oracles` are threaded (a small, additive `node.py`
> change), since the n-DMP gate needs both to reach LICENSED. Verify against `node.py` before wiring.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_serve_tcga_laml.py -q`
Expected: PASS (flag parses; seed-builder test runs or skips depending on local data).

- [ ] **Step 5: Commit**

```bash
git add src/polymer_claims/exec_adapters.py src/polymer_claims/cli.py tests/test_serve_tcga_laml.py
git commit -m "feat: serve --tcga-laml — seed the live node with the real n-DMP claim

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 8: Retire the caveat + doc the command (only after the local earned run passes)

**Files:**
- Modify: `ARCHITECTURE_CURRENT.md`, `docs/superpowers/CONTINUE.md`, `docs/superpowers/polymer-claims-canonical-spec.md` (§9 + §6), `README.md`
- Move: this spec `docs/superpowers/specs/2026-06-17-phase-a-real-data-swap-design.md` → `docs/superpowers/archive/specs/`

**Interfaces:** documentation only.

- [ ] **Step 1: Gate on evidence**

Do this task **only after** Task 6 Step 3 has been run locally and `tests/test_tcga_laml_ndmp_e2e.py` PASSES on real betas. If the real run honestly withheld, do **not** retire the caveat — instead record the observed count + `q` and stop. Evidence before assertion.

- [ ] **Step 2: Retire the caveat precisely (n-DMP / REPRODUCED tier only)**

In canonical-spec §9, `CONTINUE.md` "Standing caveats", and `ARCHITECTURE_CURRENT.md`, change the "methylation betas are synthetic" caveat to state that the **n-DMP count now licenses at REPRODUCED on real TCGA-LAML HM450 betas (earned)**, while **region-Δβ stays synthetic-caveated** until its own real run and **REPLICATED stays synthetic** until a 2nd real cohort (Phase C). Do not over-claim. Example replacement line for `CONTINUE.md`:

```markdown
- Methylation betas: the **n-DMP count is EARNED** — it licenses at REPRODUCED on real TCGA-LAML
  HM450 betas (IDH-mut vs WT) via `polymer-claims ingest tcga-laml` (local-only, gitignored). The
  **region-Δβ reduction stays synthetic** (its own real run is a follow-up); **REPLICATED stays
  synthetic** until a 2nd real cohort (Phase C). The n-DMP pooled-t is unadjusted (no age/sex
  covariate) — honest simplification carried by the apparatus.
```

- [ ] **Step 3: Document the command**

Add `ingest` to the CLI command list in canonical-spec §6 and `README.md` (beside `validate`/`serve`):
`ingest tcga-laml` — fetch + transform a real GDC cohort into a local (gitignored) SE-Contract.

- [ ] **Step 4: Archive the spec + update NEXT**

```bash
git mv docs/superpowers/specs/2026-06-17-phase-a-real-data-swap-design.md docs/superpowers/archive/specs/
```
Update `CONTINUE.md` "▶ NEXT": mark Phase A shipped (n-DMP real-data swap earned); the natural encore is a 2nd real cohort → §2E **REPLICATED**, then Phase B (the `MethylGenerationAdapter`).

- [ ] **Step 5: Full gate + commit**

```bash
uv run ruff check src tests && ./scripts/check-all.sh
git add -A
git commit -m "docs: retire synthetic caveat for n-DMP/REPRODUCED (earned on real TCGA-LAML)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Final integration

- [ ] Run the full gate: `cd /Users/zbb2/Desktop/polymer-claims && uv run ruff check src tests && ./scripts/check-all.sh` — expect all green (new unit tests pass; the real-data e2e skips without local data).
- [ ] Merge to `main` `--no-ff` (local-only, not pushed): `git checkout main && git merge --no-ff feat/phase-a-real-data-swap`.
- [ ] Update memory (`project_polymer_claims_knowledge_protocol`) with the Phase-A-shipped state.

---

## Self-review notes (coverage against the spec)

- Spec §2 (ingest CLI, fetch-by-UUID, gitignored transform) → Tasks 2–5. Spec §3 (HM450 profile, distinct hash) → Task 1. Spec §4 (claim + `alpha=0.05`, `k=ceil(α·n)` pre-registered, honest subject) → Tasks 6/7 (claim construction) + note on subject below. Spec §5A (gate seed) → Task 6; §5B (live node) → Task 7. Spec §6 (unit tests always-run + skip-if-absent e2e + honest-withhold + report q) → Tasks 1/3/4/5 (always-run) + Task 6 (e2e, withhold, q). Spec §7 (doc retirement, precise) → Task 8. Spec §8 known costs → Global Constraints + carried in the profile/test comments.
- **Subject slot (spec §4.3):** Phase A keeps the builder's default `GenomicRegion` subject (it is in the oracle's bounded `{"genomic_region","cohort"}` domain, so the apparatus tier applies and licensing is not capped to 0). An honest genome-wide/cohort subject type for n-DMP claims is a small grammar/builder follow-up — tracked, **not** in Phase A scope (avoids touching the grammar). Documented here so it is not silently dropped.
- **Honest-withhold:** Task 6 uses an unreachable pre-stated `k` on the real contract; a label-permutation negative control (a stronger null) is a noted follow-up (would need a permuted on-disk contract).
