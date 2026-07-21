"""C6 — run the sensor::senseability bridge over the REAL reproduced SNV screen (A3).

For each senseable SNV in the regenerated screen, reconstruct the sensor window OFFLINE from
SensorKit's committed CDS cache (via sensorkit.snv_runner.build_snv), submit it through the
two-classifier bridge (Leg A = SensorKit classify_variant, Leg B = the independent reimpl), and
record the warranted verdict. This is the payoff: the engine licensing REAL senseability calls at
IndependenceTier.REPRODUCED, not just the R248Q/R248W controls.

Subject note: the screen artifact carries gene/residue/change, not genomic coordinates or VRS ids,
so each claim's subject is a placeholder GenomicRegion keyed by the lesion label (assembly GRCh37 —
the screen is GRCh37-native). The senseability verdict is real (from the windows in params); binding
real VRS ids / loci is a follow-up (resolve via the API variant endpoint). Umbrella/impure; NOT
re-exported from __init__.
"""
from __future__ import annotations

import json
from pathlib import Path

from polymer_grammar import FDRLedger, GenomicRegion, Status
from polymer_grammar.licensing import IndependenceTier
from polymer_protocol import Corpus

from .sensor_senseability_adapters import sensor_senseability_claim
from .sensor_senseability_populate import license_batch, preregister

_SCREEN_REF = "sensorkit:snv-universe-scored@2026-07-15"


def _sensorkit_data() -> Path:
    import sensorkit
    return Path(sensorkit.__file__).resolve().parents[2] / "data"


def real_senseable_lesions(limit: int | None = None) -> list[dict]:
    """Reconstruct (offline, from the committed CDS cache) the senseable SNVs of the reproduced
    screen, each with its sensor window + tier. Mirrors run_screen_snv's offline scoring path."""
    import sensorkit  # noqa: F401 (resolve the install path / data dir)
    from sensorkit.hotspots import _DEFAULT_PATH, load_cancerhotspots
    from sensorkit.compendium import load_refseq
    from sensorkit.geometry import calibrate_max_dist
    from sensorkit.snv_runner import build_snv, snv_candidates

    data = _sensorkit_data()
    records = json.loads(Path(_DEFAULT_PATH).read_text())
    candidates = snv_candidates(records, load_cancerhotspots())
    max_dist = calibrate_max_dist(load_refseq(str(data / "refseq")))

    out: list[dict] = []
    for les in candidates:
        cache = data / "cds_cache" / f"{les.transcript_id}.json"
        if not cache.exists():
            continue
        cds = json.loads(cache.read_text())["seq"]
        scored_variant = build_snv(les, cds, max_dist)
        if scored_variant is None:
            continue
        scored, variant = scored_variant
        if scored.tier == "unsenseable":
            continue
        out.append({
            "id": f"sense-{les.gene}-{les.change}",
            "name": f"{les.gene} {les.change}",
            "gene": les.gene,
            "window_wt": variant.window_wt,
            "window_mut": variant.window_mut,
            "var_index": variant.var_index,
            "tier": scored.tier,
        })
        if limit is not None and len(out) >= limit:
            break
    return out


def build_screen_claims(lesions: list[dict]) -> list:
    return [
        sensor_senseability_claim(
            L["id"], ref=_SCREEN_REF,
            subject=GenomicRegion(id=L["id"], display=L["name"], assembly="GRCh37",
                                  chrom="chr0", start=1, end=2),  # placeholder locus (see docstring)
            window_wt=L["window_wt"], window_mut=L["window_mut"], var_index=L["var_index"],
            max_dist=5, mode="snv", tier_bar=1, gene=L["gene"], name=L["name"])
        for L in lesions
    ]


def run_bridge_over_screen(limit: int | None = None) -> dict:
    """Run the bridge over the real senseable SNVs and return a warranted ledger:
    {lesion_id: {"status", "reproduced", "tier"}}."""
    lesions = real_senseable_lesions(limit=limit)
    claims = build_screen_claims(lesions)
    corpus = preregister(Corpus(fdr_ledger=FDRLedger(target_fdr=0.05)), claims)
    out = license_batch(corpus, claims).by_id()
    ledger = {}
    by_tier = {L["id"]: L["tier"] for L in lesions}
    for L in lesions:
        c = out[L["id"]]
        rep = (c.licensing is not None
               and c.licensing.independence_tier is IndependenceTier.REPRODUCED)
        ledger[L["id"]] = {"status": c.status.name, "reproduced": rep, "tier": by_tier[L["id"]]}
    return ledger
