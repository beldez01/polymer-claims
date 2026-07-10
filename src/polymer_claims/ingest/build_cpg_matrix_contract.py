"""Multi-probe SE-Contract builder for a per-CpG x per-sample beta matrix (M1's CpgMatrix).

Unlike the single-feature-row `build_loyfer_contract.build_contract` (one locus-mean beta row x N
samples), this emits PROBES-AS-ROWS: one `row_data` feature per CpG, a `betas.tsv` with a row per
probe and a column per sample, and `col_data` carrying the grouping variable. This is the exact
schema `contracts.load_contract` + `methyl_adapters._load_betas` + `methyl_ndmp._per_probe_pvalues`
read (mirrors the multi-probe contract written by tests/test_n_dmps_e2e.py::_write_adversarial_contract:
`uid` / `assays[{name,ref}]` / `col_data[{sample_id, <group_col>}]` / `row_data[{feature_id}]` /
`metadata.genome_assembly`), so the n-DMP count claim can run over the full probe set.
"""
from __future__ import annotations

import json
from pathlib import Path

from .loyfer_wgbs import CpgMatrix


def build_cpg_matrix_contract(
    matrix: CpgMatrix, uid: str, out_dir: Path, *, group_col: str = "lineage"
) -> Path:
    """Write a multi-probe SE-Contract (`<stem>.json` + `<stem>.betas.tsv`) from a CpgMatrix.

    `group_col` names the col_data field the n-DMP claim groups on; every CpgMatrix sample-meta
    field (cell_type, cell_type_broad, lineage) is always emitted, so no branch is needed. Returns
    the manifest path. Deterministic (no clock/random); probe/sample order is the matrix's order.
    """
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    stem = uid.split("@")[0]
    betas_ref = f"{stem}.betas.tsv"

    # .betas.tsv: header = feature_id + sample ids; one row per probe = beta[probe][sample].
    # repr(float) keeps full precision so per-probe p-values are not perturbed by rounding.
    lines = ["\t".join(["feature_id"] + list(matrix.samples))]
    for p_idx, probe in enumerate(matrix.probe_ids):
        row = matrix.betas[p_idx]
        lines.append("\t".join([probe] + [repr(float(v)) for v in row]))
    (out / betas_ref).write_text("\n".join(lines) + "\n")

    def _pos(probe: str) -> int:
        # probe id is "chrom:pos" (M1 CpgMatrix convention); fall back to 0 if unparseable.
        try:
            return int(probe.split(":", 1)[1])
        except (IndexError, ValueError):
            return 0

    def _chrom(probe: str) -> str:
        return probe.split(":", 1)[0] if ":" in probe else ""

    doc = {
        "uid": uid,
        "dim": [len(matrix.probe_ids), len(matrix.samples)],
        "assays": [{"name": "beta", "ref": betas_ref}],
        "col_data": [
            {
                "sample_id": m["sample"],
                group_col: m[group_col],
                "cell_type": m["cell_type"],
                "cell_type_broad": m["cell_type_broad"],
                "lineage": m["lineage"],
            }
            for m in matrix.sample_meta
        ],
        "row_data": [
            {"feature_id": probe, "chr": _chrom(probe), "pos": _pos(probe)}
            for probe in matrix.probe_ids
        ],
        "metadata": {"genome_assembly": "hg38"},  # Loyfer 2023 WGBS atlas is hg38-referenced
    }
    path = out / f"{stem}.json"
    path.write_text(json.dumps(doc, indent=2) + "\n")
    return path
