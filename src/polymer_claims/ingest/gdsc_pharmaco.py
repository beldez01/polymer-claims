"""Build se:gdsc_pharmaco@1 — GDSC methylation + drug-response in one content-addressed
SE-Contract. Reuses the feature x sample contract shape: feature ids are prefixed
'meth::<GENE>' (methylation beta) and 'auc::<DRUG>' (drug-response AUC) over the same
cell-line samples; per-line tissue rides col_data (Sample_Group). Gitignored; built on demand.
"""
from __future__ import annotations

import json
import math
from pathlib import Path


def build_pharmaco_contract(
    betas: dict[str, dict[str, str | float]],
    aucs: dict[str, dict[str, str | float]],
    tissue: dict[str, str],
    *,
    genes: list[str],
    drugs: list[str],
    out_dir,
    uid_stem: str = "gdsc_pharmaco",
) -> str:
    """Write the manifest JSON + values TSV load_contract reads. Samples = union of lines with
    a tissue; features = meth::<gene> then auc::<drug> (sorted within each block). Missing
    values -> 'nan' (adapters drop them)."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    samples = sorted(tissue)
    feat_rows = [f"meth::{g}" for g in sorted(genes)] + [f"auc::{d}" for d in sorted(drugs)]

    def _val(prefix_map, key, sid):
        v = prefix_map.get(key, {}).get(sid)
        if v is None or (isinstance(v, float) and math.isnan(v)):
            return "nan"
        return f"{float(v):.6f}"

    manifest = {
        "uid": f"{uid_stem}@1",
        "dim": [len(feat_rows), len(samples)],
        "assays": [{"name": "value", "ref": f"{uid_stem}.betas.tsv"}],
        "col_data": [{"sample_id": s, "Sample_Group": tissue[s], "tissue": tissue[s]} for s in samples],
        "row_data": [{"feature_id": f, "chr": "", "pos": 0} for f in feat_rows],
        "metadata": {"source": "GDSC2", "kind": "pharmaco", "genome_assembly": "hg38"},
    }
    (out_dir / f"{uid_stem}.json").write_text(json.dumps(manifest, indent=2))

    lines = ["\t".join(["feature_id", *samples])]
    for g in sorted(genes):
        lines.append("\t".join([f"meth::{g}", *(_val(betas, g, s) for s in samples)]))
    for d in sorted(drugs):
        lines.append("\t".join([f"auc::{d}", *(_val(aucs, d, s) for s in samples)]))
    (out_dir / f"{uid_stem}.betas.tsv").write_text("\n".join(lines) + "\n")
    return f"{uid_stem}@1"


def ingest_gdsc_pharmaco(data_dir: str | None = None) -> str:
    """Load the lifted GDSC data, restrict to the mechanism-gene union + all drugs, and build the
    contract into the package contracts/ dir (gitignored). Returns a one-line summary.

    ``gene_union`` is exactly the union of scan-candidate genes across all drugs — i.e. every
    gene the STRATA mechanism scan (``rank_mechanism_opportunities`` / ``all_mechanism_markers``)
    could possibly propose a marker for — NOT merely the curated ``PATHWAY_GENES`` +
    ``TARGET_ALIAS`` values (which can miss a drug's own parsed target gene). This guarantees
    every ``meth::<gene>`` row the scan proposes actually exists in the contract."""
    from polymer_claims import contracts as _contracts
    from polymer_claims.strata.mechanism import PATHWAY_GENES, load_inputs, parse_targets

    meth, drug, ann, meta = load_inputs()          # meth: lines x genes; drug: long COSMIC_ID/drug_name/auc
    valid = set(meth.columns)                      # ann: index COSMIC_ID -> tissue; meta: per-drug target/pathway
    gene_union: set[str] = set()
    for _, mr in meta.iterrows():
        tgt, pw = mr["PUTATIVE_TARGET"], mr["PATHWAY_NAME"]
        gene_union |= set(parse_targets(tgt, valid))
        gene_union |= {g for g in PATHWAY_GENES.get(pw, []) if g in valid}
    gene_union = sorted(gene_union)
    drugs = sorted(drug["drug_name"].unique().tolist())
    lines = [str(x) for x in meth.index]
    tissue = {s: str(ann["tissue"].get(s, "unknown")) for s in lines if s in ann.index}
    betas = {g: {s: float(meth.loc[s, g]) for s in tissue if s in meth.index} for g in gene_union}
    aucs: dict[str, dict[str, float]] = {}
    for d, sub in drug.groupby("drug_name"):
        aucs[str(d)] = {str(r.COSMIC_ID): float(r.auc) for r in sub.itertuples() if str(r.COSMIC_ID) in tissue}
    uid = build_pharmaco_contract(betas, aucs, tissue, genes=gene_union, drugs=drugs,
                                  out_dir=Path(_contracts.__file__).parent)
    _contracts.clear_contract_cache()
    ref = _contracts.load_contract(f"se:{uid}")
    return f"ingested {uid}: {ref.dimnames_hash[:16]}… ({len(tissue)} lines, {len(gene_union)} genes, {len(drugs)} drugs)"
