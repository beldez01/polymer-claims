# Phase 2d-i — TCGA-LAML fusion-expression SE-contract Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Build and validate `se:tcga_laml_fusion_expr@1` — a feature×sample SE-contract of TCGA-LAML RNA-seq TPM for a fixed 4-gene panel, with each case labeled fusion+/fusion− for RUNX1-RUNX1T1 (t(8;21)) from cytogenetic karyotype.

**Architecture:** A pure contract builder (`ingest/tcga_laml_fusion_expr.py`) mirroring `build_pharmaco_contract`, tested on a tiny committed fixture; and a one-shot fetch+extract script that pulls real STAR TPM + cBioPortal karyotype, pins a small extract into `data/`, builds the real contract, and runs abort-on-fail self-checks. No licensing (2d-ii).

**Tech Stack:** Python 3.12, stdlib (`json`, `gzip`, `urllib`/`curl`), the existing `contracts/` loader. Spec: `docs/superpowers/specs/2026-07-12-spine-2di-fusion-expr-contract-design.md`.

## Global Constraints

- `grammar/` and `protocol/` untouched, pure + numpy-free. `Corpus` stays 4. **No claim built, nothing licensed** (that is 2d-ii).
- Compute-boundary: the builder writes a data contract; it runs no analysis and mints no claim.
- Self-contained regeneration reads only `data/`; the network fetch is a documented one-shot, not part of regeneration. Big source matrices stay external/gitignored; only the small extract is committed.
- Contract format (from `contracts/__init__.py`): manifest `<stem>.json` + matrix `<stem>.betas.tsv`; manifest MUST have `uid`, `assays[0].{name,ref}`, `row_data[].feature_id`, `col_data[].sample_id`, `metadata.genome_assembly` (loader KeyErrors without it). Loader pins `group_col=Sample_Group`, so the fusion label lives under `Sample_Group`.
- Gene panel (fixed): `RUNX1T1`=ENSG00000079102, `RUNX1`=ENSG00000159216, `ACTB`=ENSG00000075624, `GAPDH`=ENSG00000111640.
- Known t(8;21) named controls (from the 2026-07-12 probe): `TCGA-AB-2819`, `TCGA-AB-2858`, `TCGA-AB-2875`, `TCGA-AB-2886`, `TCGA-AB-2937`, `TCGA-AB-2950`.
- Test command: `cd /Users/zbb2/Desktop/polymer-claims && uv run --project . pytest tests/ingest/test_tcga_laml_fusion_expr.py -v`.

---

## File Structure

- `src/polymer_claims/ingest/tcga_laml_fusion_expr.py` — the pure builder (Task 1).
- `tests/ingest/test_tcga_laml_fusion_expr.py` — fixture-based builder tests (Task 1).
- `tests/ingest/fixtures/fusion_expr_mini/{panel_tpm.tsv,fusion_labels.tsv}` — tiny committed fixture (Task 1).
- `data/tcga_laml_fusion_expr/build_extract.py` — one-shot real fetch+extract+build+self-checks (Task 2).
- `data/tcga_laml_fusion_expr/{panel_tpm.tsv,fusion_labels.tsv,SOURCE.txt,build.log}` — pinned extract (Task 2).
- `src/polymer_claims/contracts/tcga_laml_fusion_expr.{json,betas.tsv}` — the built contract (Task 2, committed).

---

### Task 1: The contract builder + fixture tests

**Files:**
- Create: `src/polymer_claims/ingest/tcga_laml_fusion_expr.py`
- Create: `tests/ingest/fixtures/fusion_expr_mini/panel_tpm.tsv`, `.../fusion_labels.tsv`
- Test: `tests/ingest/test_tcga_laml_fusion_expr.py`

**Interfaces:**
- Produces: `build_fusion_expr_contract(tpm: dict[str, dict[str, float]], fusion_status: dict[str, str], karyotype: dict[str, str], *, genes: list[str], out_dir, uid_stem: str = "tcga_laml_fusion_expr") -> str` (returns the uid `"tcga_laml_fusion_expr@1"`; writes `<uid_stem>.json` + `<uid_stem>.betas.tsv` into `out_dir`). `tpm` is `gene_symbol -> {case_id -> TPM}`; `fusion_status` is `case_id -> "fusion_pos"|"fusion_neg"`; `karyotype` is `case_id -> str` (provenance).
- Consumes: the `contracts` loader (`load_contract`, `using_contract_root`, `clear_contract_cache`).

- [ ] **Step 1: Create the tiny fixture.** `tests/ingest/fixtures/fusion_expr_mini/panel_tpm.tsv` (tab-sep, `gene` header col + 5 case columns; RUNX1T1 high in the two fusion_pos cases, near-zero elsewhere; housekeeping flat):

```
gene	TCGA-AB-2819	TCGA-AB-2937	TCGA-AB-2802	TCGA-AB-2803	TCGA-AB-2804
RUNX1T1	140.5	155.2	0.3	0.1	0.4
RUNX1	22.0	19.5	20.1	21.3	18.9
ACTB	900.0	880.0	910.0	905.0	895.0
GAPDH	600.0	590.0	605.0	610.0	595.0
```

`tests/ingest/fixtures/fusion_expr_mini/fusion_labels.tsv`:

```
case_id	fusion_status	karyotype
TCGA-AB-2819	fusion_pos	46,XX,t(8;21)(q22;q22)[17]/46,XX[3]
TCGA-AB-2937	fusion_pos	46,XX,t(8;21)(q22;q22)[20]
TCGA-AB-2802	fusion_neg	46,XY[20]
TCGA-AB-2803	fusion_neg	46,XX[20]
TCGA-AB-2804	fusion_neg	47,XY,+8[20]
```

- [ ] **Step 2: Write the failing test** (`tests/ingest/test_tcga_laml_fusion_expr.py`):

```python
from pathlib import Path

from polymer_claims import contracts as _c
from polymer_claims.ingest.tcga_laml_fusion_expr import build_fusion_expr_contract

_FIX = Path(__file__).parent / "fixtures" / "fusion_expr_mini"
_GENES = ["RUNX1T1", "RUNX1", "ACTB", "GAPDH"]


def _load_fixture():
    rows = [ln.split("\t") for ln in (_FIX / "panel_tpm.tsv").read_text().splitlines()]
    header, data = rows[0], rows[1:]
    cases = header[1:]
    tpm = {r[0]: {c: float(v) for c, v in zip(cases, r[1:])} for r in data}
    lab = [ln.split("\t") for ln in (_FIX / "fusion_labels.tsv").read_text().splitlines()][1:]
    fusion = {r[0]: r[1] for r in lab}
    karyo = {r[0]: r[2] for r in lab}
    return tpm, fusion, karyo


def test_builds_loadable_contract_with_fusion_group(tmp_path):
    tpm, fusion, karyo = _load_fixture()
    uid = build_fusion_expr_contract(tpm, fusion, karyo, genes=_GENES, out_dir=tmp_path)
    assert uid == "tcga_laml_fusion_expr@1"
    _c.clear_contract_cache()
    with _c.using_contract_root(tmp_path):
        ref = _c.load_contract("se:tcga_laml_fusion_expr@1")
        manifest = _c.load_manifest(ref)
    feats = {r["feature_id"] for r in manifest["row_data"]}
    assert feats == {f"expr::{g}" for g in _GENES}
    groups = {c["Sample_Group"] for c in manifest["col_data"]}
    assert groups == {"fusion_pos", "fusion_neg"}
    assert manifest["metadata"]["genome_assembly"] == "hg38"


def test_matrix_values_and_sample_order_are_deterministic(tmp_path):
    tpm, fusion, karyo = _load_fixture()
    build_fusion_expr_contract(tpm, fusion, karyo, genes=_GENES, out_dir=tmp_path)
    tsv = (tmp_path / "tcga_laml_fusion_expr.betas.tsv").read_text()
    lines = tsv.splitlines()
    assert lines[0].split("\t")[0] == "feature_id"
    assert lines[0].split("\t")[1:] == sorted(fusion)          # samples sorted, deterministic
    runx1t1 = next(l for l in lines if l.startswith("expr::RUNX1T1")).split("\t")[1:]
    col = lines[0].split("\t")[1:]
    val = dict(zip(col, runx1t1))
    assert float(val["TCGA-AB-2819"]) > 100 and float(val["TCGA-AB-2802"]) < 1  # signal preserved
```

- [ ] **Step 3: Run to verify it fails** → `uv run --project . pytest tests/ingest/test_tcga_laml_fusion_expr.py -v` → FAIL (module missing).

- [ ] **Step 4: Implement `src/polymer_claims/ingest/tcga_laml_fusion_expr.py`:**

```python
"""Builder for se:tcga_laml_fusion_expr@1 — TCGA-LAML RNA-seq TPM (4-gene panel) with a t(8;21)
fusion group. Mirrors ingest/gdsc_pharmaco.py:build_pharmaco_contract. Writes a data contract only;
no analysis, no claim (that is Phase 2d-ii). numpy-free (stdlib json/math).
"""
from __future__ import annotations

import json
import math
from pathlib import Path


def build_fusion_expr_contract(
    tpm: dict[str, dict[str, float]],
    fusion_status: dict[str, str],
    karyotype: dict[str, str],
    *,
    genes: list[str],
    out_dir,
    uid_stem: str = "tcga_laml_fusion_expr",
) -> str:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    samples = sorted(fusion_status)
    features = [f"expr::{g}" for g in sorted(genes)]

    def _val(g: str, s: str) -> str:
        v = tpm.get(g, {}).get(s)
        if v is None or (isinstance(v, float) and math.isnan(v)):
            return "nan"
        return f"{float(v):.6f}"

    manifest = {
        "uid": f"{uid_stem}@1",
        "dim": [len(features), len(samples)],
        "assays": [{"name": "tpm", "ref": f"{uid_stem}.betas.tsv"}],
        "col_data": [
            {
                "sample_id": s,
                "Sample_Group": fusion_status[s],   # loader reads group_col=Sample_Group
                "tissue": "AML",
                "karyotype": karyotype.get(s, ""),  # provenance
            }
            for s in samples
        ],
        "row_data": [{"feature_id": f, "chr": "", "pos": 0} for f in features],
        "metadata": {"source": "TCGA-LAML", "kind": "expression", "genome_assembly": "hg38"},
    }
    (out_dir / f"{uid_stem}.json").write_text(json.dumps(manifest, indent=2))

    lines = ["\t".join(["feature_id", *samples])]
    for g in sorted(genes):
        lines.append("\t".join([f"expr::{g}", *(_val(g, s) for s in samples)]))
    (out_dir / f"{uid_stem}.betas.tsv").write_text("\n".join(lines) + "\n")
    return f"{uid_stem}@1"
```

- [ ] **Step 5: Run to verify it passes** → `uv run --project . pytest tests/ingest/test_tcga_laml_fusion_expr.py -v` → PASS (2 tests).

- [ ] **Step 6: Commit**

```bash
git add src/polymer_claims/ingest/tcga_laml_fusion_expr.py tests/ingest/test_tcga_laml_fusion_expr.py tests/ingest/fixtures/fusion_expr_mini
git commit -m "feat(ingest): TCGA-LAML fusion-expression SE-contract builder (fixture-tested)"
```

---

### Task 2: One-shot real fetch + extract + build + self-checks (CONTROLLER-EXECUTED)

> **Execution note:** this task hits the network and adapts to real data (large streamed matrix, cBioPortal API, real gene/case joins). Execute it in-session as the controller rather than via a rigid subagent; the code below is the target, but expect to inspect real intermediate values (e.g. confirm the four Ensembl ids are present in the matrix, confirm the karyotype join) and adjust. The self-checks are hard asserts — a failure means STOP and diagnose, do not weaken the check.

**Files:**
- Create: `data/tcga_laml_fusion_expr/build_extract.py` (+ writes `panel_tpm.tsv`, `fusion_labels.tsv`, `SOURCE.txt`, `build.log`)
- Create (committed output): `src/polymer_claims/contracts/tcga_laml_fusion_expr.json`, `.betas.tsv`
- Modify: `.gitignore` (ignore the large external download, keep the small extract)

- [ ] **Step 1: Fetch + extract.** Write `data/tcga_laml_fusion_expr/build_extract.py`:
  - **Expression:** download `https://gdc-hub.s3.us-east-1.amazonaws.com/download/TCGA-LAML.star_tpm.tsv.gz` to a gitignored local path; stream-parse (line by line, no full load). Header cols are full barcodes → `case_id`. Keep only rows whose Ensembl id (strip `.version`) is in `{ENSG00000079102:RUNX1T1, ENSG00000159216:RUNX1, ENSG00000075624:ACTB, ENSG00000111640:GAPDH}`. Build `tpm[symbol][case_id]` (if multiple samples per case, take the primary `-03A`/first). ABORT if any of the 4 Ensembl ids is absent from the matrix.
  - **Fusion label:** GET `https://www.cbioportal.org/api/studies/laml_tcga_pub/clinical-data?clinicalDataType=PATIENT&attributeId=CYTOGENETICS&projection=SUMMARY` (JSON list of `{patientId, value}`). `fusion_status[case] = "fusion_pos" if "t(8;21)" in value else "fusion_neg"`; `karyotype[case] = value`.
  - **Universe:** `sorted(set(tpm cases) & set(karyotyped cases))`. Cases with TPM but no karyotype are DROPPED (logged), never defaulted.
  - Write the pinned extract `panel_tpm.tsv` (gene × case) + `fusion_labels.tsv` (`case_id, fusion_status, karyotype`) + `SOURCE.txt` (urls, sha256 of the downloaded matrix, fetch date, api endpoint) + `build.log` (counts). Print `n_universe`, `n_fusion_pos`, `n_fusion_neg`.

- [ ] **Step 2: Run the extract; eyeball the counts.** `uv run --project . python data/tcga_laml_fusion_expr/build_extract.py`. Expect `n_fusion_pos == 6` (the six named controls), `n_universe` ≈ the RNA-seq∩karyotype cases (~130-150). Confirm the six named controls are all `fusion_pos`.

- [ ] **Step 3: Build the real contract from the pinned extract** (extend the script or a short follow-on): call `build_fusion_expr_contract(...)` with `out_dir = Path(polymer_claims.contracts.__file__).parent`, then `clear_contract_cache()` and `load_contract("se:tcga_laml_fusion_expr@1")`.

- [ ] **Step 4: Self-checks (hard asserts — abort on fail).** In the script, after building:

```python
NAMED_T821 = {"TCGA-AB-2819","TCGA-AB-2858","TCGA-AB-2875","TCGA-AB-2886","TCGA-AB-2937","TCGA-AB-2950"}
n_pos = sum(1 for v in fusion_status.values() if v == "fusion_pos")
assert 3 <= n_pos <= 20, f"fusion_pos count {n_pos} out of band [3,20] — labeling swap?"
present = NAMED_T821 & set(fusion_status)
assert all(fusion_status[c] == "fusion_pos" for c in present), "a named t(8;21) control is not fusion_pos"
def _median(xs): xs = sorted(xs); n = len(xs); return xs[n//2] if n % 2 else (xs[n//2-1]+xs[n//2])/2
pos = [tpm["RUNX1T1"][c] for c in fusion_status if fusion_status[c]=="fusion_pos" and c in tpm["RUNX1T1"]]
neg = [tpm["RUNX1T1"][c] for c in fusion_status if fusion_status[c]=="fusion_neg" and c in tpm["RUNX1T1"]]
assert _median(pos) >= 5 * max(_median(neg), 1e-6), "RUNX1T1 fusion+ not >=5x fusion- — signal/orientation wrong"
for hk in ("ACTB","GAPDH"):
    hp = _median([tpm[hk][c] for c in fusion_status if fusion_status[c]=="fusion_pos" and c in tpm[hk]])
    hn = _median([tpm[hk][c] for c in fusion_status if fusion_status[c]=="fusion_neg" and c in tpm[hk]])
    assert 0.5 <= hp/max(hn,1e-6) <= 2.0, f"housekeeping {hk} discriminates by fusion — batch artifact?"
print("self-checks passed:", n_pos, "fusion_pos; RUNX1T1 pos/neg median ratio =", round(_median(pos)/max(_median(neg),1e-6),1))
```

- [ ] **Step 5: `.gitignore` the big download, keep the extract + contract.** Add the large `*.star_tpm.tsv.gz` local path to `.gitignore`; confirm `git status` shows only `data/tcga_laml_fusion_expr/{build_extract.py,panel_tpm.tsv,fusion_labels.tsv,SOURCE.txt,build.log}` + `contracts/tcga_laml_fusion_expr.{json,betas.tsv}` as additions (no multi-hundred-MB blob).

- [ ] **Step 6: Regression + register check.** `uv run --project . pytest tests/ingest/ -q` (Task-1 fixture tests still green) and a quick `python -c "from polymer_claims import contracts as c; r=c.load_contract('se:tcga_laml_fusion_expr@1'); print(c.load_manifest(r)['dim'])"` prints `[4, n_universe]`.

- [ ] **Step 7: Continuity + commit.** Append a note to `docs/superpowers/CONTINUE.md` (2d-i shipped: `se:tcga_laml_fusion_expr@1` built, 6 t(8;21) fusion+, RUNX1T1 signal ratio recorded; 2d-ii can now wire the licensed spine) and a one-line memory note. Commit:

```bash
git add data/tcga_laml_fusion_expr src/polymer_claims/contracts/tcga_laml_fusion_expr.json src/polymer_claims/contracts/tcga_laml_fusion_expr.betas.tsv .gitignore docs/superpowers/CONTINUE.md
git commit -m "feat(spine): build se:tcga_laml_fusion_expr@1 from real TCGA-LAML TPM + t(8;21) karyotype (2d-i)"
```

---

## Self-review (against the spec)

- **Builder mirrors pharmaco; contract loads; Sample_Group carries fusion label** → Task 1. ✔
- **Expression via STAR TPM (Ensembl-versioned, case_id-normalized); label via CYTOGENETICS karyotype; no-missing-default universe** → Task 2 Step 1. ✔
- **Fixed 4-gene panel; floor NOT set here** → Global Constraints + no threshold in any check. ✔
- **Self-checks: fusion+ band, named controls, signal sanity (RUNX1T1 ≥5×, housekeeping flat)** → Task 2 Step 4. ✔
- **Self-contained: big download gitignored, small extract pinned; fixture tests need no network** → Task 1 (fixture) + Task 2 Step 5. ✔
- **No licensing / claim / grammar / protocol change; Corpus stays 4** → Global Constraints; nothing in either task builds a claim. ✔
- **Type consistency:** `build_fusion_expr_contract` signature identical in Task 1 (definition) and Task 2 Step 3 (call); `fusion_status` values `"fusion_pos"/"fusion_neg"` consistent across builder, checks, and `Sample_Group`. ✔
