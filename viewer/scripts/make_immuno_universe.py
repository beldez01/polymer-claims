"""Build the viewer-loadable universe bundle for the two genuinely LICENSED immuno n-DMP nodes:
MHC n-DMP (`rip_mhc_ndmp.run_mhc_ndmp`) and HERV-K LTR n-DMP (`rip_hervk_ndmp.run_hervk_ndmp`), both
licensed via the e-LOND count-enrichment route. Mirrors the static bundle schema of
`data/demo/polymergenomics_universe.json` (top-level `claims`/`defeat_edges`/`equivalences`/
`fdr_ledger`) so the viewer renders them as blue LICENSED nodes.

`build_bundle` is pure/deterministic given `nodes` — no run_cycle here. The real drives
(`run_mhc_ndmp`, `run_hervk_ndmp`) are reused verbatim by `__main__`, not reimplemented.

JSON has no `inf` literal (the MHC count e-value is `inf`), so e-values are always serialized as
strings ("inf" / "-inf" / "nan", or a finite decimal string) — never a raw float that could be
non-finite.

RUN (umbrella env, real drives, ~7 min total):
    cd /Users/zbb2/Desktop/polymer-claims-immuno \
      && PYTHONPATH=src /Users/zbb2/Desktop/polymer-claims/.venv/bin/python \
           viewer/scripts/make_immuno_universe.py
"""
from __future__ import annotations

import json
import math
from pathlib import Path

_SCHEMA_VERSION = "v1.3"

_OUT = Path(__file__).resolve().parents[2] / "data" / "demo" / "immuno_universe.json"


def _evalue_str(value) -> str | None:
    """Serialize an e-value for JSON: non-finite floats (inf/-inf/nan) become their string name
    (JSON cannot encode them); a caller-provided string passes through unchanged; any other
    finite numeric value is stringified via repr (a decimal string)."""
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, float) and not math.isfinite(value):
        if math.isnan(value):
            return "nan"
        return "inf" if value > 0 else "-inf"
    return repr(value)


def _claim_entry(node: dict) -> dict:
    """One claim entry mirroring polymergenomics_universe.json's claim shape (schema_version, id,
    title, pattern, leaves, status, ...) plus the flat count-enrichment metadata the viewer needs:
    region, n_probes, dmp_count, e_value (string-safe), tier, and semantic_run_id (content-address)."""
    semantic_run_id = node.get("semantic_run_id")
    return {
        "schema_version": _SCHEMA_VERSION,
        "id": node["id"],
        "title": node["title"],
        "pattern": {"id": "count_enrichment", "version": "v1"},
        "leaves": [{
            "kind": "quantity",
            "value": node.get("dmp_count"),
            "unit": None,
            "uncertainty": None,
            "measurement_basis": "derived",
            "formula": "count_enrichment_dmp_count",
            "dimension": None,
        }],
        "status": node["status"],
        "pending_reason": None,
        "rejection_reason": None,
        "strength": None,
        "conclusion": None,
        "licensing": {"semantic_run_id": semantic_run_id} if semantic_run_id else None,
        "roles": None,
        "subject": None,
        "provenance": None,
        "governance": None,
        "evaluation_plan": None,
        "representation_revision": None,
        "tier": node.get("tier"),
        "region": node.get("region"),
        "n_probes": node.get("n_probes"),
        "dmp_count": node.get("dmp_count"),
        "e_value": _evalue_str(node.get("e_value")),
        "semantic_run_id": semantic_run_id,
    }


def build_bundle(nodes: list[dict], out_path: Path) -> Path:
    """nodes: list of {id,title,status,tier,region,n_probes,dmp_count,e_value,semantic_run_id?}.
    Writes a viewer-schema universe JSON (claims + empty defeat_edges/equivalences + a minimal
    fdr_ledger). Returns out_path. Pure/deterministic given nodes."""
    doc = {
        "claims": [_claim_entry(n) for n in nodes],
        "defeat_edges": [],
        "equivalences": [],
        "fdr_ledger": {"target_fdr": 0.05, "procedure": "elond", "tests": []},
    }
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, indent=2) + "\n")
    return out_path


def _semantic_run_id(corpus, claim_id: str) -> str | None:
    c = next((x for x in corpus.claims if x.id == claim_id), None)
    if c is None or c.licensing is None or not c.licensing.satisfactions:
        return None
    return c.licensing.satisfactions[0].materialization.semantic_run_id


def _mhc_node():
    from polymer_claims.rip_mhc_ndmp import run_mhc_ndmp

    atlas = Path.home() / "Desktop/PolymerGenomicsAPI/data/wgbs/loyfer_2023"
    chrom, start, end = "chr6", 29_900_000, 33_100_000
    contracts_dir = Path.home() / ".cache/polymer-claims/mhc_ndmp_contracts"
    res = run_mhc_ndmp(
        atlas / "bed_hg38", atlas / "sample_manifest.tsv", contracts_dir,
        chrom=chrom, start=start, end=end,
        group_col="lineage", level_a="Lymphoid", level_b="Myeloid",
        alpha=0.05, min_cov=4,
    )
    if res.verdict != "LICENSED":
        raise SystemExit(f"MHC n-DMP claim did not license: verdict={res.verdict!r}")
    title = next(x for x in res.corpus.claims if x.id == "mhc-ndmp").title
    return {
        "id": "mhc_ndmp", "title": title, "status": res.verdict, "tier": "REPRODUCED",
        "region": f"{chrom}:{start}-{end}", "n_probes": res.n_probes, "dmp_count": res.count_ttest,
        "e_value": res.e_value, "semantic_run_id": _semantic_run_id(res.corpus, "mhc-ndmp"),
    }, res


def _hervk_node():
    from polymer_claims.rip_hervk_ndmp import run_hervk_ndmp

    atlas = Path.home() / "Desktop/PolymerGenomicsAPI/data/wgbs/loyfer_2023"
    rmsk = Path.home() / "Desktop/PolymerGenomicsAPI/data/repeatmasker/rmsk.txt"
    contracts_dir = Path.home() / ".cache/polymer-claims/hervk_ndmp_contracts"
    res = run_hervk_ndmp(
        rmsk, atlas / "bed_hg38", atlas / "sample_manifest.tsv", contracts_dir,
        group_col="lineage", level_a="Lymphoid", level_b="Myeloid",
        alpha=0.05, min_cov=4,
    )
    if res.verdict != "LICENSED":
        raise SystemExit(f"HERV-K n-DMP claim did not license: verdict={res.verdict!r}")
    title = next(x for x in res.corpus.claims if x.id == "hervk-ndmp").title
    return {
        "id": "hervk_ndmp", "title": title, "status": res.verdict, "tier": "REPRODUCED",
        "region": f"HERVK_LTR5_Hs({res.n_windows} elements)", "n_probes": res.n_probes,
        "dmp_count": res.count_ttest, "e_value": res.e_value,
        "semantic_run_id": _semantic_run_id(res.corpus, "hervk-ndmp"),
    }, res


def main() -> None:
    mhc_node, mhc_res = _mhc_node()
    print(f"MHC n-DMP: {mhc_res.verdict} n_probes={mhc_res.n_probes} "
          f"count_ttest={mhc_res.count_ttest} count_rank={mhc_res.count_rank} e_value={mhc_res.e_value}")

    hervk_node, hervk_res = _hervk_node()
    print(f"HERV-K n-DMP: {hervk_res.verdict} n_windows={hervk_res.n_windows} "
          f"n_probes={hervk_res.n_probes} count_ttest={hervk_res.count_ttest} "
          f"count_rank={hervk_res.count_rank} e_value={hervk_res.e_value}")

    out = build_bundle([mhc_node, hervk_node], _OUT)
    n_licensed = sum(1 for n in (mhc_node, hervk_node) if n["status"] == "LICENSED")
    print(f"wrote {out} (2 nodes, {n_licensed} licensed)")


if __name__ == "__main__":
    main()
