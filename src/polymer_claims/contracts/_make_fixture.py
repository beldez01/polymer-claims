"""Deterministic generator for the CES-1 EPICv2-shaped methylation fixture.

Synthetic VALUES, real STRUCTURE: 50 cg-format probes x 8 samples (4 TET2_mut / 4 WT) on
chr4 near the TET2 locus (hg38). No RNG — every value is a fixed function of its indices, so the
fixture is reproducible. Probes 0-4 carry a planted +0.20 beta shift in TET2_mut samples (used by
CES-2 only; CES-1 asserts nothing about values). Re-run with:  python -m
polymer_claims.contracts._make_fixture
"""
from __future__ import annotations

import json
from pathlib import Path

_DIR = Path(__file__).parent
N_FEATURES = 50
N_SAMPLES = 8
_PLANTED_PROBES = set(range(5))   # first 5 probes carry the TET2_mut shift
_PLANTED_SHIFT = 0.20


def _samples() -> list[dict]:
    out = []
    for j in range(N_SAMPLES):
        group = "TET2_mut" if j % 2 == 0 else "WT"
        out.append({
            "sample_id": f"S{j + 1:02d}",
            "Sample_Group": group,
            "Age": 40 + (j * 3) % 25,
            "Sex": "M" if j % 3 == 0 else "F",
        })
    return out


def _probes() -> list[dict]:
    return [
        {"feature_id": f"cg{i + 1:08d}", "chr": "chr4", "pos": 105_000_000 + i * 500}
        for i in range(N_FEATURES)
    ]


def _beta(i: int, sample: dict) -> float:
    base = 0.20 + ((i * 7 + 3) % 60) / 100.0   # deterministic in [0.20, 0.79]
    if i in _PLANTED_PROBES and sample["Sample_Group"] == "TET2_mut":
        base += _PLANTED_SHIFT
    return round(min(base, 0.999999), 6)


def build() -> None:
    samples = _samples()
    probes = _probes()
    manifest = {
        "uid": "tet2_epicv2_demo@1",
        "dim": [N_FEATURES, N_SAMPLES],
        "assays": [{"name": "beta", "ref": "tet2_epicv2_demo.betas.tsv"}],
        "col_data": samples,
        "row_data": probes,
        "metadata": {"genome_assembly": "hg38", "array": "EPICv2"},
    }
    (_DIR / "tet2_epicv2_demo.json").write_text(json.dumps(manifest, indent=2) + "\n")

    header = "\t".join(["feature_id"] + [s["sample_id"] for s in samples])
    rows = [header]
    for i, probe in enumerate(probes):
        cells = [probe["feature_id"]] + [f"{_beta(i, s):.6f}" for s in samples]
        rows.append("\t".join(cells))
    (_DIR / "tet2_epicv2_demo.betas.tsv").write_text("\n".join(rows) + "\n")


if __name__ == "__main__":
    build()
