"""Phase 2e — build the two CBF 3-valued fusion-expression contracts (se:{tcga_laml,target_aml}_cbf_expr@1)
from the already-downloaded STAR-TPM matrices + cytogenetics. LOCAL-ONLY (raw inputs gitignored).

Sample_Group ∈ {t821, inv16, other}; panel {RUNX1T1, MN1, ACTB, GAPDH}. Mirrors the 2d-i/2d-iii extracts.
Per-cohort pinned extract written under data/{tcga_laml,target_aml}_cbf_fusion_expr/. No claim, no license.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import re
import statistics
import sys
from pathlib import Path

REPO = Path("/Users/zbb2/Desktop/polymer-claims")
sys.path.insert(0, str(REPO / "src"))
from polymer_claims import contracts as _c  # noqa: E402
from polymer_claims.ingest.tcga_laml_fusion_expr import build_fusion_expr_contract  # noqa: E402
from polymer_claims.ingest.transform import case_id  # noqa: E402

PANEL = {"ENSG00000079102": "RUNX1T1", "ENSG00000169184": "MN1",
         "ENSG00000075624": "ACTB", "ENSG00000111640": "GAPDH"}
GENES = ["RUNX1T1", "MN1", "ACTB", "GAPDH"]


def _median(xs):
    xs = sorted(xs)
    n = len(xs)
    return 0.0 if not n else (xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2)


def _label(karyo: str) -> str:
    if "t(8;21)" in karyo:
        return "t821"
    if re.search(r"inv\(16\)|t\(16;16\)", karyo):
        return "inv16"
    return "other"


def build(cohort: str, matrix: Path, cyto_json: Path, out_dir: Path, uid_stem: str, primary_types):
    out_dir.mkdir(parents=True, exist_ok=True)
    with gzip.open(matrix, "rt") as fh:
        header = fh.readline().rstrip("\n").split("\t")
        barcodes = header[1:]
        case_col: dict[str, int] = {}
        for i, bc in enumerate(barcodes):
            cid = case_id(bc)
            parts = bc.split("-")
            primary = len(parts) >= 4 and parts[3][:2] in primary_types
            if cid not in case_col or primary:
                case_col[cid] = i
        tpm = {g: {} for g in GENES}
        seen = set()
        for line in fh:
            f = line.rstrip("\n").split("\t")
            sym = PANEL.get(f[0].split(".")[0])
            if not sym:
                continue
            seen.add(f[0].split(".")[0])
            for cid, col in case_col.items():
                tpm[sym][cid] = 2.0 ** float(f[col + 1]) - 1.0
    assert not (set(PANEL) - seen), f"{cohort}: panel ids absent {set(PANEL) - seen}"

    cyto = json.loads(cyto_json.read_text())
    karyo = {x["patientId"]: x["value"] for x in cyto}
    universe = sorted(set(case_col) & set(karyo))
    group = {c: _label(karyo[c]) for c in universe}
    n = {g: sum(1 for v in group.values() if v == g) for g in ("t821", "inv16", "other")}
    print(f"[{cohort}] universe={len(universe)}  t821={n['t821']} inv16={n['inv16']} other={n['other']}", flush=True)

    # pin extract
    plines = ["\t".join(["gene", *universe])]
    for g in GENES:
        plines.append("\t".join([g, *(f"{tpm[g].get(c, float('nan')):.6f}" for c in universe)]))
    (out_dir / "panel_tpm.tsv").write_text("\n".join(plines) + "\n")
    (out_dir / "fusion_labels.tsv").write_text(
        "case_id\tsample_group\tkaryotype\n" + "\n".join(f"{c}\t{group[c]}\t{karyo[c]}" for c in universe) + "\n")
    (out_dir / "SOURCE.txt").write_text(
        f"cohort: {cohort}; Sample_Group t821/inv16/other; panel RUNX1T1/MN1/ACTB/GAPDH\n"
        f"expression matrix sha256: {hashlib.sha256(matrix.read_bytes()).hexdigest()}\n"
        "unit: log2(TPM+1) -> raw 2^x-1. MN1 = validated CBFB-MYH11 target (prior lit); MYH11 fails at gene level.\n")

    uid = build_fusion_expr_contract(tpm, group, karyo, genes=GENES, out_dir=Path(_c.__file__).parent,
                                     uid_stem=uid_stem)
    _c.clear_contract_cache()
    ref = _c.load_contract(f"se:{uid}")
    print(f"[{cohort}] built {uid}: dim={_c.load_manifest(ref)['dim']} dimnames={ref.dimnames_hash[:16]}…", flush=True)

    # self-checks
    assert 3 <= n["t821"] and 3 <= n["inv16"], f"{cohort}: too few t821/inv16"
    def med(gene, grp):
        return _median([tpm[gene][c] for c in universe if group[c] == grp])
    runx_t821 = med("RUNX1T1", "t821")
    runx_rest = _median([tpm["RUNX1T1"][c] for c in universe if group[c] != "t821"])
    mn1_inv16 = med("MN1", "inv16")
    mn1_rest = _median([tpm["MN1"][c] for c in universe if group[c] != "inv16"])
    assert runx_t821 >= 5 * max(runx_rest, 1e-6) and runx_t821 >= 13, f"{cohort}: RUNX1T1/t821 weak ({runx_t821:.1f})"
    assert mn1_inv16 >= 5 * max(mn1_rest, 1e-6) and mn1_inv16 >= 13, f"{cohort}: MN1/inv16 weak ({mn1_inv16:.1f})"
    for hk in ("ACTB", "GAPDH"):
        ms = [med(hk, g) for g in ("t821", "inv16", "other")]
        assert max(ms) / max(min(ms), 1e-6) <= 2.0, f"{cohort}: {hk} varies across groups {ms}"
    print(f"[{cohort}] self-checks PASSED: RUNX1T1 t821 {runx_t821:.0f} vs rest {runx_rest:.2f}; "
          f"MN1 inv16 {mn1_inv16:.0f} vs rest {mn1_rest:.2f}", flush=True)
    return ref.dimnames_hash


h_tcga = build("TCGA-LAML", REPO / "data/tcga_laml_fusion_expr/TCGA-LAML.star_tpm.tsv.gz",
               REPO / "data/tcga_laml_fusion_expr/_cytogenetics.json",
               REPO / "data/tcga_laml_cbf_fusion_expr", "tcga_laml_cbf_expr", ("03",))
h_target = build("TARGET-AML", REPO / "data/target_aml_fusion_expr/TARGET-AML.star_tpm.tsv.gz",
                 REPO / "data/target_aml_fusion_expr/_cyto.json",
                 REPO / "data/target_aml_cbf_fusion_expr", "target_aml_cbf_expr", ("03", "09"))
assert h_tcga != h_target, "CBF contracts share dimnames_hash (not distinct cohorts!)"
print("distinct dimnames_hash: OK (REPLICATED-eligible)")
