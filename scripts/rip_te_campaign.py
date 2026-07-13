"""Real overnight drive of the TE multi-contrast CAMPAIGN over the Loyfer 2023 WGBS atlas.

Runs the pre-registered CONTRAST panel (lineage + cell_type_broad pairs) x {n-DMP beyond-chance,
background-enrichment} gates from ONE atlas extraction. Writes a crash-safe running summary after every
contrast (so an interrupted overnight run keeps its progress), then two combined strict-Corpus bundles
(all n-DMP claims / all enrichment claims, contrast-tagged) for later viewer integration.

Not exercised by tests (real atlas + rmsk on disk; several minutes). Usage:
    uv run python scripts/rip_te_campaign.py
"""
import json
from pathlib import Path

from polymer_claims.io import dump_corpus
from polymer_claims.merge_universes import ArmSource, merge_universes
from polymer_claims.te_campaign import CONTRASTS, run_te_campaign

_ATLAS = Path.home() / "Desktop/PolymerGenomicsAPI/data/wgbs/loyfer_2023"
_RMSK = Path.home() / "Desktop/PolymerGenomicsAPI/data/repeatmasker/rmsk.txt"
_REPO = Path(__file__).resolve().parents[1]
_OUTDIR = _REPO / "data" / "demo" / "campaign"
_SUMMARY = _OUTDIR / "te_campaign_summary.json"


def _fam_rows(verdicts):
    out = []
    for v in verdicts:
        out.append({
            "key": v.key, "verdict": v.verdict, "status": v.status.value,
            "n_probes": v.n_probes, "count_ttest": v.count_ttest, "count_rank": v.count_rank,
            "e_value": v.e_value, "bar": v.bar, "fold_ttest": v.fold_ttest, "fold_rank": v.fold_rank,
        })
    return out


def _serialize(cr):
    return {
        "contrast": {"key": cr.contrast.key, "group_col": cr.contrast.group_col,
                     "level_a": cr.contrast.level_a, "level_b": cr.contrast.level_b,
                     "note": cr.contrast.note},
        "n_a": cr.n_a, "n_b": cr.n_b, "skipped": cr.skipped,
        "bg_rate_ttest": cr.bg_rate_ttest, "bg_rate_rank": cr.bg_rate_rank,
        "ndmp": _fam_rows(cr.ndmp), "enrichment": _fam_rows(cr.enrichment),
    }


def _tally(contrasts):
    t = {"ndmp": {"LICENSED": 0, "PENDING": 0, "REJECTED": 0},
         "enrichment": {"LICENSED": 0, "PENDING": 0, "REJECTED": 0}, "claims": 0, "skipped": 0}
    for cr in contrasts:
        if cr.get("skipped"):
            t["skipped"] += 1
        for gate in ("ndmp", "enrichment"):
            for r in cr.get(gate, []):
                t[gate][r["verdict"]] += 1
                t["claims"] += 1
    return t


def main() -> None:
    contracts_dir = Path.home() / ".cache/polymer-claims/te_campaign_contracts"
    _OUTDIR.mkdir(parents=True, exist_ok=True)
    running = {"contrasts": []}

    print("\n=== TE multi-contrast campaign — Loyfer 2023 WGBS atlas ===", flush=True)
    print(f"{len(CONTRASTS)} pre-registered contrasts x 2 gates x 6 TE families\n", flush=True)

    def on_contrast(cr):
        running["contrasts"].append(_serialize(cr))
        _SUMMARY.write_text(json.dumps(running, indent=2, default=str))  # crash-safe checkpoint
        c = cr.contrast
        if cr.skipped:
            print(f"[{c.key:<26}] SKIPPED — {cr.skipped}", flush=True)
            return
        nd = "/".join(f"{v.verdict[0]}" for v in cr.ndmp)          # e.g. L/P/R per family
        en = "/".join(f"{v.verdict[0]}" for v in cr.enrichment)
        nl = sum(v.verdict == "LICENSED" for v in cr.ndmp)
        el = sum(v.verdict == "LICENSED" for v in cr.enrichment)
        print(f"[{c.key:<26}] n={cr.n_a}v{cr.n_b}  bg t={100*cr.bg_rate_ttest:.0f}%/r="
              f"{100*cr.bg_rate_rank:.0f}%  n-DMP[{nd}] {nl}/6 lic  ENR[{en}] {el}/6 lic", flush=True)

    res = run_te_campaign(
        _RMSK, _ATLAS / "bed_hg38", _ATLAS / "sample_manifest.tsv", contracts_dir,
        on_contrast=on_contrast)

    # Combined strict-Corpus bundles (contrast-tagged arm facets), one per gate.
    nd_sources = [ArmSource.from_corpus(f"te-{cr.contrast.key}-ndmp", "methylation", cr.ndmp_corpus)
                  for cr in res.contrasts if cr.ndmp_corpus is not None]
    en_sources = [ArmSource.from_corpus(f"te-{cr.contrast.key}-enrich", "methylation",
                                        cr.enrichment_corpus)
                  for cr in res.contrasts if cr.enrichment_corpus is not None]
    nd_merged, _ = merge_universes(nd_sources)
    en_merged, _ = merge_universes(en_sources)
    (_OUTDIR / "te_campaign_ndmp_universe.json").write_text(dump_corpus(nd_merged))
    (_OUTDIR / "te_campaign_enrichment_universe.json").write_text(dump_corpus(en_merged))

    tally = _tally(running["contrasts"])
    running["tally"] = tally
    _SUMMARY.write_text(json.dumps(running, indent=2, default=str))

    print("\n=== CAMPAIGN TOTALS ===", flush=True)
    print(f"  contrasts run: {len(res.contrasts) - tally['skipped']}  (skipped {tally['skipped']})",
          flush=True)
    print(f"  total claims: {tally['claims']}", flush=True)
    print(f"  n-DMP (beyond-chance):  {tally['ndmp']}", flush=True)
    print(f"  enrichment (vs bg):     {tally['enrichment']}", flush=True)
    print(f"\n  bundles -> {_OUTDIR}/te_campaign_{{ndmp,enrichment}}_universe.json", flush=True)
    print(f"  summary -> {_SUMMARY}", flush=True)


if __name__ == "__main__":
    main()
