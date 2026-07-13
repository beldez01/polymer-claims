"""One-shot builder for se:tcga_laml_fusion_expr@1 (Phase 2d-i). LOCAL-ONLY / gitignored raw input.

Reads:
  - TCGA-LAML.star_tpm.tsv.gz  (GDC/Xena, gitignored) — gene x sample, values are LOG2(TPM+1),
    versioned Ensembl row ids. Converted to raw TPM (2**x - 1) here.
  - _cytogenetics.json          (cBioPortal laml_tcga_pub CYTOGENETICS clinical attribute) — karyotype
    per patient; a case is fusion_pos iff its karyotype contains "t(8;21)".

Writes the pinned self-contained extract (panel_tpm.tsv, fusion_labels.tsv, SOURCE.txt, build.log) and
builds/registers the real contract into src/polymer_claims/contracts/. NO analysis, NO claim (that is 2d-ii).
"""
from __future__ import annotations

import gzip
import hashlib
import json
import sys
from pathlib import Path

REPO = Path("/Users/zbb2/Desktop/polymer-claims")
HERE = REPO / "data" / "tcga_laml_fusion_expr"
sys.path.insert(0, str(REPO / "src"))
from polymer_claims import contracts as _c  # noqa: E402
from polymer_claims.ingest.tcga_laml_fusion_expr import build_fusion_expr_contract  # noqa: E402
from polymer_claims.ingest.transform import case_id  # noqa: E402

MATRIX = HERE / "TCGA-LAML.star_tpm.tsv.gz"
CYTO = HERE / "_cytogenetics.json"
PANEL = {  # unversioned Ensembl id -> symbol
    "ENSG00000079102": "RUNX1T1",
    "ENSG00000159216": "RUNX1",
    "ENSG00000075624": "ACTB",
    "ENSG00000111640": "GAPDH",
}
GENES = ["RUNX1T1", "RUNX1", "ACTB", "GAPDH"]
NAMED_T821 = {"TCGA-AB-2819", "TCGA-AB-2858", "TCGA-AB-2875",
              "TCGA-AB-2886", "TCGA-AB-2937", "TCGA-AB-2950"}
log: list[str] = []


def _p(msg: str) -> None:
    print(msg, flush=True)
    log.append(msg)


def _median(xs: list[float]) -> float:
    xs = sorted(xs)
    n = len(xs)
    if not n:
        return 0.0
    return xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2


# 1. expression: stream the log2 matrix, keep panel genes, prefer the -03A primary sample per case.
with gzip.open(MATRIX, "rt") as fh:
    header = fh.readline().rstrip("\n").split("\t")
    barcodes = header[1:]
    # case_id -> chosen column index (prefer a barcode whose sample-type field starts '03')
    case_col: dict[str, int] = {}
    for i, bc in enumerate(barcodes):
        cid = case_id(bc)
        parts = bc.split("-")
        is_primary = len(parts) >= 4 and parts[3].startswith("03")
        if cid not in case_col or is_primary:
            case_col[cid] = i
    tpm: dict[str, dict[str, float]] = {g: {} for g in GENES}
    seen_ens: set[str] = set()
    for line in fh:
        f = line.rstrip("\n").split("\t")
        ens = f[0].split(".")[0]
        sym = PANEL.get(ens)
        if not sym:
            continue
        seen_ens.add(ens)
        for cid, col in case_col.items():
            raw = 2.0 ** float(f[col + 1]) - 1.0  # log2(tpm+1) -> raw TPM  (col+1: f[0] is the id)
            tpm[sym][cid] = raw

missing = set(PANEL) - seen_ens
assert not missing, f"panel Ensembl ids absent from matrix: {missing}"
expr_cases = set(case_col)
_p(f"expression: {len(barcodes)} samples -> {len(expr_cases)} cases (log2->raw TPM converted)")

# 2. fusion labels from karyotype.
cyto = json.loads(CYTO.read_text())
karyotype = {x["patientId"]: x["value"] for x in cyto}
fusion_pos_cases = {c for c, v in karyotype.items() if "t(8;21)" in v}
_p(f"cytogenetics: {len(karyotype)} patients, {len(fusion_pos_cases)} t(8;21)")

# 3. universe = expression cases that have a karyotype (no missing default).
universe = sorted(expr_cases & set(karyotype))
dropped = sorted(expr_cases - set(karyotype))
fusion_status = {c: ("fusion_pos" if c in fusion_pos_cases else "fusion_neg") for c in universe}
karyo_map = {c: karyotype[c] for c in universe}
n_pos = sum(1 for v in fusion_status.values() if v == "fusion_pos")
_p(f"universe={len(universe)}  fusion_pos={n_pos}  fusion_neg={len(universe) - n_pos}  "
   f"dropped_no_karyotype={len(dropped)}")

# 4. pin the small extract.
panel_lines = ["\t".join(["gene", *universe])]
for g in GENES:
    panel_lines.append("\t".join([g, *(f"{tpm[g].get(c, float('nan')):.6f}" for c in universe)]))
(HERE / "panel_tpm.tsv").write_text("\n".join(panel_lines) + "\n")
lab_lines = ["\t".join(["case_id", "fusion_status", "karyotype"])]
for c in universe:
    lab_lines.append("\t".join([c, fusion_status[c], karyo_map[c]]))
(HERE / "fusion_labels.tsv").write_text("\n".join(lab_lines) + "\n")

matrix_sha = hashlib.sha256(MATRIX.read_bytes()).hexdigest()
(HERE / "SOURCE.txt").write_text(
    "expression: https://gdc-hub.s3.us-east-1.amazonaws.com/download/TCGA-LAML.star_tpm.tsv.gz\n"
    f"  unit: log2(TPM+1) (converted to raw TPM = 2^x - 1 in build_extract.py)\n"
    f"  sha256: {matrix_sha}\n"
    "fusion_label: cBioPortal REST /api/studies/laml_tcga_pub/clinical-data "
    "?clinicalDataType=PATIENT&attributeId=CYTOGENETICS (karyotype; fusion_pos iff 't(8;21)' in value)\n"
    "panel: RUNX1T1 ENSG00000079102, RUNX1 ENSG00000159216, ACTB ENSG00000075624, GAPDH ENSG00000111640\n"
    "fetched: 2026-07-12\n"
)

# 5. build + register the real contract from the extract.
uid = build_fusion_expr_contract(tpm, fusion_status, karyo_map, genes=GENES,
                                 out_dir=Path(_c.__file__).parent)
_c.clear_contract_cache()
ref = _c.load_contract(f"se:{uid}")
manifest = _c.load_manifest(ref)
_p(f"built {uid}: dim={manifest['dim']}  dimnames_hash={ref.dimnames_hash[:16]}…")

# 6. self-checks (hard asserts — abort rather than register a wrong contract).
assert 3 <= n_pos <= 20, f"fusion_pos count {n_pos} out of band [3,20] — labeling swap?"
present = NAMED_T821 & set(fusion_status)
bad = [c for c in present if fusion_status[c] != "fusion_pos"]
assert not bad, f"named t(8;21) controls not fusion_pos: {bad}"
pos = [tpm["RUNX1T1"][c] for c in universe if fusion_status[c] == "fusion_pos"]
neg = [tpm["RUNX1T1"][c] for c in universe if fusion_status[c] == "fusion_neg"]
ratio = _median(pos) / max(_median(neg), 1e-6)
assert ratio >= 5, f"RUNX1T1 fusion+/- median ratio {ratio:.1f} < 5 — signal/orientation wrong"
for hk in ("ACTB", "GAPDH"):
    hp = _median([tpm[hk][c] for c in universe if fusion_status[c] == "fusion_pos"])
    hn = _median([tpm[hk][c] for c in universe if fusion_status[c] == "fusion_neg"])
    hr = hp / max(hn, 1e-6)
    assert 0.5 <= hr <= 2.0, f"housekeeping {hk} discriminates by fusion (ratio {hr:.2f}) — batch artifact?"
_p(f"self-checks PASSED: n_pos={n_pos}, RUNX1T1 pos/neg median ratio={ratio:.0f}x "
   f"(pos median {_median(pos):.1f} TPM, neg median {_median(neg):.3f} TPM)")

(HERE / "build.log").write_text("\n".join(log) + "\n")
