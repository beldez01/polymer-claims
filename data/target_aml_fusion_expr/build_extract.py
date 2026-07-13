"""One-shot builder for se:target_aml_fusion_expr@1 (Phase 2d-iii, the REPLICATED second cohort).
LOCAL-ONLY / gitignored raw input. Mirrors data/tcga_laml_fusion_expr/build_extract.py.

Reads:
  - TARGET-AML.star_tpm.tsv.gz (GDC/Xena, gitignored) — gene x sample, LOG2(TPM+1), versioned Ensembl.
  - _cyto.json (cBioPortal aml_target_2018_pub PRIMARY_CYTOGENETIC_CODE) — fusion_pos iff 't(8;21)'.
Writes the pinned extract + builds/registers the contract. NO analysis, NO claim.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import sys
from pathlib import Path

REPO = Path("/Users/zbb2/Desktop/polymer-claims")
HERE = REPO / "data" / "target_aml_fusion_expr"
sys.path.insert(0, str(REPO / "src"))
from polymer_claims import contracts as _c  # noqa: E402
from polymer_claims.ingest.tcga_laml_fusion_expr import build_fusion_expr_contract  # noqa: E402
from polymer_claims.ingest.transform import case_id  # noqa: E402

MATRIX = HERE / "TARGET-AML.star_tpm.tsv.gz"
CYTO = HERE / "_cyto.json"
PANEL = {"ENSG00000079102": "RUNX1T1", "ENSG00000159216": "RUNX1",
         "ENSG00000075624": "ACTB", "ENSG00000111640": "GAPDH"}
GENES = ["RUNX1T1", "RUNX1", "ACTB", "GAPDH"]
log: list[str] = []


def _p(m: str) -> None:
    print(m, flush=True)
    log.append(m)


def _median(xs: list[float]) -> float:
    xs = sorted(xs)
    n = len(xs)
    return 0.0 if not n else (xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2)


# 1. expression: stream log2 matrix, prefer a primary-diagnostic sample (type 03/09) per case.
with gzip.open(MATRIX, "rt") as fh:
    header = fh.readline().rstrip("\n").split("\t")
    barcodes = header[1:]
    case_col: dict[str, int] = {}
    for i, bc in enumerate(barcodes):
        cid = case_id(bc)
        parts = bc.split("-")
        primary = len(parts) >= 4 and parts[3][:2] in ("03", "09")  # diagnostic AML types
        if cid not in case_col or primary:
            case_col[cid] = i
    tpm: dict[str, dict[str, float]] = {g: {} for g in GENES}
    seen: set[str] = set()
    for line in fh:
        f = line.rstrip("\n").split("\t")
        sym = PANEL.get(f[0].split(".")[0])
        if not sym:
            continue
        seen.add(f[0].split(".")[0])
        for cid, col in case_col.items():
            tpm[sym][cid] = 2.0 ** float(f[col + 1]) - 1.0  # log2(tpm+1) -> raw TPM

assert not (set(PANEL) - seen), f"panel ids absent: {set(PANEL) - seen}"
expr_cases = set(case_col)
_p(f"expression: {len(barcodes)} samples -> {len(expr_cases)} cases (log2->raw)")

# 2. fusion labels from PRIMARY_CYTOGENETIC_CODE.
cyto = json.loads(CYTO.read_text())
karyo = {x["patientId"]: x["value"] for x in cyto}
pos_cases = {c for c, v in karyo.items() if "t(8;21)" in v}
_p(f"cytogenetics: {len(karyo)} patients, {len(pos_cases)} t(8;21)")

# 3. universe = expression ∩ karyotyped (no missing default).
universe = sorted(expr_cases & set(karyo))
fusion = {c: ("fusion_pos" if c in pos_cases else "fusion_neg") for c in universe}
n_pos = sum(1 for v in fusion.values() if v == "fusion_pos")
_p(f"universe={len(universe)}  fusion_pos={n_pos}  fusion_neg={len(universe) - n_pos}")

# 4. pin the extract.
plines = ["\t".join(["gene", *universe])]
for g in GENES:
    plines.append("\t".join([g, *(f"{tpm[g].get(c, float('nan')):.6f}" for c in universe)]))
(HERE / "panel_tpm.tsv").write_text("\n".join(plines) + "\n")
llines = ["\t".join(["case_id", "fusion_status", "karyotype"])]
for c in universe:
    llines.append("\t".join([c, fusion[c], karyo[c]]))
(HERE / "fusion_labels.tsv").write_text("\n".join(llines) + "\n")
(HERE / "SOURCE.txt").write_text(
    "expression: https://gdc-hub.s3.us-east-1.amazonaws.com/download/TARGET-AML.star_tpm.tsv.gz\n"
    f"  unit: log2(TPM+1) -> raw = 2^x-1;  sha256: {hashlib.sha256(MATRIX.read_bytes()).hexdigest()}\n"
    "fusion_label: cBioPortal aml_target_2018_pub PRIMARY_CYTOGENETIC_CODE (fusion_pos iff 't(8;21)')\n"
    "cohort: TARGET-AML (pediatric) — the error-independent 2nd cohort for the RUNX1-RUNX1T1 spine (2d-iii)\n"
    "shared method w/ TCGA (documented, NOT a shared error cause): GDC STAR-Counts TPM, hg38, Ensembl.\n"
    "fetched: 2026-07-12\n")

# 5. build + register.
uid = build_fusion_expr_contract(tpm, fusion, karyo, genes=GENES, out_dir=Path(_c.__file__).parent,
                                 uid_stem="target_aml_fusion_expr")
_c.clear_contract_cache()
ref = _c.load_contract(f"se:{uid}")
_p(f"built {uid}: dim={_c.load_manifest(ref)['dim']}  dimnames_hash={ref.dimnames_hash[:16]}…")
tcga = _c.load_contract("se:tcga_laml_fusion_expr@1")
assert ref.dimnames_hash != tcga.dimnames_hash, "TARGET dimnames_hash == TCGA (not distinct cohorts!)"
_p("distinct dimnames_hash vs TCGA: OK (REPLICATED-eligible)")

# 6. self-checks.
assert 5 <= n_pos <= 200, f"fusion_pos {n_pos} out of band"
pos = [tpm["RUNX1T1"][c] for c in universe if fusion[c] == "fusion_pos"]
neg = [tpm["RUNX1T1"][c] for c in universe if fusion[c] == "fusion_neg"]
ratio = _median(pos) / max(_median(neg), 1e-6)
assert ratio >= 5, f"RUNX1T1 ratio {ratio:.1f} < 5"
for hk in ("ACTB", "GAPDH"):
    hp = _median([tpm[hk][c] for c in universe if fusion[c] == "fusion_pos"])
    hn = _median([tpm[hk][c] for c in universe if fusion[c] == "fusion_neg"])
    assert 0.5 <= hp / max(hn, 1e-6) <= 2.0, f"housekeeping {hk} discriminates ({hp/max(hn,1e-6):.2f})"
_p(f"self-checks PASSED: n_pos={n_pos}, RUNX1T1 pos/neg median {_median(pos):.1f}/{_median(neg):.3f} TPM ({ratio:.0f}x)")
(HERE / "build.log").write_text("\n".join(log) + "\n")
