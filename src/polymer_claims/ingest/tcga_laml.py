"""Orchestrate: fetch pinned GDC files -> parse -> build the on-disk SE-Contract into the package
contracts/ dir (where load_contract reads it). The contract is gitignored; nothing real is committed."""
from __future__ import annotations

import gzip
from pathlib import Path

from polymer_claims import contracts as _contracts
from polymer_claims.ingest.gdc_fetch import fetch_file, load_pinned_manifest
from polymer_claims.ingest.gdc_parse import parse_beta_file, parse_beta_meta, parse_clinical, parse_maf
from polymer_claims.ingest.transform import _case_id, build_contract, derive_groups


def ingest_tcga_laml(data_dir: str) -> str:
    """Fetch + transform TCGA-LAML HM450 into se:tcga_laml_idh@1. Returns a one-line summary."""
    cache = Path(data_dir)
    man = load_pinned_manifest()

    # 1. betas: one file per case -> {case_id: {probe: beta}} and the union probe set + row meta.
    #    The per-probe Chromosome/Start annotation is platform-fixed (identical across aliquot files),
    #    so row_meta is parsed ONCE from the first file's annotation columns (real chr/pos -> the
    #    genome-wide QC sex-chrom filter bites and row_data carries true coordinates).
    betas: dict[str, dict[str, float]] = {}
    sample_ids: list[str] = []
    row_meta: dict[str, dict] = {}
    for entry in man["betas"]:
        raw = fetch_file(entry["uuid"], entry["md5"], cache / entry["filename"])
        text = raw.decode("utf-8", errors="replace")
        col = parse_beta_file(text)
        if not row_meta:
            row_meta = parse_beta_meta(text)
        cid = entry["case_id"]
        sample_ids.append(cid)
        for probe, beta in col.items():
            betas.setdefault(probe, {})[cid] = beta

    # every probe in betas must have a row_meta entry (build_contract indexes row_meta[p] directly);
    # GDC aliquot files share the platform probe set, so this only fills genuine gaps.
    for probe in betas:
        row_meta.setdefault(probe, {"chr": "", "pos": 0})

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
