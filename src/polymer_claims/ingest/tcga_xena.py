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
