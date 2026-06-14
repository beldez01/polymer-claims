"""Deterministic GENERIC case/control EPICv2-shaped methylation fixture (CES-2).

Synthetic VALUES, real STRUCTURE: 24 cg-format probes x 10 samples (5 level1 / 5 level2) on chr1
(hg38). No RNG. The first 5 probes (the SIGNAL REGION) carry a planted +0.20 beta shift in level2;
the rest have no group difference (the negative-control region). Generic — not TET2-specific.
Re-run:  python -m polymer_claims.contracts._make_casectrl_fixture
"""
from __future__ import annotations

import json
from pathlib import Path

_DIR = Path(__file__).parent
N_FEATURES = 24
N_SAMPLES = 100
_SIGNAL_PROBES = set(range(5))
_SHIFT = 0.20


def _samples() -> list[dict]:
    out = []
    for j in range(N_SAMPLES):
        group = "level1" if j % 2 == 0 else "level2"
        out.append({"sample_id": f"S{j + 1:02d}", "Sample_Group": group,
                    "Age": 40 + (j * 3) % 25, "Sex": "M" if j % 3 == 0 else "F"})
    return out


def _probes() -> list[dict]:
    return [{"feature_id": f"cg{i + 1:08d}", "chr": "chr1", "pos": 1_000_000 + i * 200}
            for i in range(N_FEATURES)]


def _beta(i: int, sample: dict) -> float:
    base = 0.30 + ((i * 11 + 5) % 40) / 100.0
    if i in _SIGNAL_PROBES and sample["Sample_Group"] == "level2":
        base += _SHIFT
    return round(min(base, 0.999999), 6)


def build() -> None:
    samples = _samples()
    probes = _probes()
    manifest = {
        "uid": "epicv2_casectrl_demo@1",
        "dim": [N_FEATURES, N_SAMPLES],
        "assays": [{"name": "beta", "ref": "epicv2_casectrl_demo.betas.tsv"}],
        "col_data": samples,
        "row_data": probes,
        "metadata": {"genome_assembly": "hg38", "array": "EPICv2"},
    }
    (_DIR / "epicv2_casectrl_demo.json").write_text(json.dumps(manifest, indent=2) + "\n")

    header = "\t".join(["feature_id"] + [s["sample_id"] for s in samples])
    rows = [header]
    for i, probe in enumerate(probes):
        cells = [probe["feature_id"]] + [f"{_beta(i, s):.6f}" for s in samples]
        rows.append("\t".join(cells))
    (_DIR / "epicv2_casectrl_demo.betas.tsv").write_text("\n".join(rows) + "\n")


if __name__ == "__main__":
    build()
