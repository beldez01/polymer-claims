"""Discovery/test sample-splitting + top-k probe selection — the severity (anti-cherry-picking)
machinery for region-Δβ. Umbrella/impure (split_contract + top_k read/write contracts). Selection
happens ONLY on the discovery half; the held-out test half is never read during selection. Deterministic
(sort + even/odd interleave; ties by probe id) so sub-contracts are content-addressable."""
from __future__ import annotations

import json
from pathlib import Path

from polymer_claims.contracts import load_contract


def stratified_split(sample_groups: dict[str, str]) -> tuple[list[str], list[str]]:
    """Deterministic stratified 50/50 split. Within each group (processed in sorted order), sorted
    sample ids are assigned even-index -> discovery, odd-index -> test. Returns (discovery, test),
    each sorted. Disjoint; union = all ids."""
    by_group: dict[str, list[str]] = {}
    for sid, grp in sample_groups.items():
        by_group.setdefault(grp, []).append(sid)
    disc: list[str] = []
    test: list[str] = []
    for grp in sorted(by_group):
        for i, sid in enumerate(sorted(by_group[grp])):
            (disc if i % 2 == 0 else test).append(sid)
    return sorted(disc), sorted(test)


def split_contract(
    contracts_dir,
    *,
    in_stem: str = "tcga_laml_idh",
    disc_stem: str = "tcga_laml_idh_disc",
    test_stem: str = "tcga_laml_idh_test",
    group_col: str = "Sample_Group",
) -> tuple[list[str], list[str]]:
    """Split {in_stem} into two disjoint-sample sub-contracts (same probes), streamed. Returns
    (discovery_ids, test_ids)."""
    cdir = Path(contracts_dir)
    manifest = json.loads((cdir / f"{in_stem}.json").read_text())
    col_data = manifest["col_data"]
    groups = {c["sample_id"]: c[group_col] for c in col_data}
    disc_ids, test_ids = stratified_split(groups)

    sample_order = [c["sample_id"] for c in col_data]
    col_of = {sid: i + 1 for i, sid in enumerate(sample_order)}  # +1: col 0 is feature_id
    cd_by_id = {c["sample_id"]: c for c in col_data}

    for stem, ids in ((disc_stem, disc_ids), (test_stem, test_ids)):
        sel = [col_of[s] for s in ids]
        with open(cdir / f"{in_stem}.betas.tsv") as fin, open(cdir / f"{stem}.betas.tsv", "w") as fout:
            fout.write("\t".join(["feature_id", *ids]) + "\n")
            next(fin)  # skip the header
            for line in fin:
                cells = line.rstrip("\n").split("\t")
                fout.write("\t".join([cells[0], *(cells[i] for i in sel)]) + "\n")
        sub = {
            **manifest,
            "uid": f"{stem}@1",
            "dim": [len(manifest["row_data"]), len(ids)],
            "assays": [{"name": "beta", "ref": f"{stem}.betas.tsv"}],
            "col_data": [cd_by_id[s] for s in ids],
        }
        (cdir / f"{stem}.json").write_text(json.dumps(sub))
    return disc_ids, test_ids


def top_k_hypermethylated(
    ref: str,
    k: int,
    *,
    group_col: str = "Sample_Group",
    level_a: str = "WT",
    level_b: str = "IDH_mut",
) -> tuple[str, ...]:
    """Top-k probes by Δβ = mean(level_b) − mean(level_a), read ONLY from the named contract
    (the discovery half). Descending; ties broken by probe id. Deterministic."""
    se = load_contract(ref)
    betas_path = Path(se.access_methods[0].access_url)
    manifest = json.loads((betas_path.parent / f"{se.contract_uid.split('@')[0]}.json").read_text())
    group_of = {c["sample_id"]: c[group_col] for c in manifest["col_data"]}
    lines = betas_path.read_text().splitlines()
    header = lines[0].split("\t")[1:]
    a_idx = [i for i, sid in enumerate(header) if group_of[sid] == level_a]
    b_idx = [i for i, sid in enumerate(header) if group_of[sid] == level_b]
    if not a_idx or not b_idx:
        raise ValueError(f"empty group (level_a={len(a_idx)}, level_b={len(b_idx)})")
    scored: list[tuple[float, str]] = []
    for ln in lines[1:]:
        cells = ln.split("\t")
        vals = cells[1:]
        ma = sum(float(vals[i]) for i in a_idx) / len(a_idx)
        mb = sum(float(vals[i]) for i in b_idx) / len(b_idx)
        scored.append((mb - ma, cells[0]))
    scored.sort(key=lambda t: (-t[0], t[1]))  # Δβ desc, probe-id tiebreak -> deterministic
    return tuple(p for _, p in scored[:k])
