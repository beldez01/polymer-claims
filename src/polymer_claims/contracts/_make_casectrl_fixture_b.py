"""Deterministic SECOND synthetic case/control EPICv2-shaped cohort (§2E replication).

Synthetic VALUES, real STRUCTURE: 24 cg-format probes x 10 samples (T01..T10), an INDEPENDENT cohort
from epicv2_casectrl_demo (different sample ids -> different dimnames_hash). Same signal region (first 5
probes) carries the same planted +0.20 beta shift in level2, so the SAME region claim conceptually
replicates here. No RNG. Synthetic data: the REPLICATED tier is EXERCISED, not earned.
Re-run:  python -m polymer_claims.contracts._make_casectrl_fixture_b
"""
from __future__ import annotations

import json
from pathlib import Path

_DIR = Path(__file__).parent
N_FEATURES = 24
N_SAMPLES = 10
_SIGNAL_PROBES = set(range(5))
_SHIFT = 0.20


def _samples() -> list[dict]:
    out = []
    for j in range(N_SAMPLES):
        group = "level1" if j % 2 == 0 else "level2"
        out.append({"sample_id": f"T{j + 1:02d}", "Sample_Group": group,
                    "Age": 45 + (j * 5) % 25, "Sex": "F" if j % 3 == 0 else "M"})
    return out


def _probes() -> list[dict]:
    return [{"feature_id": f"cg{i + 1:08d}", "chr": "chr1", "pos": 1_000_000 + i * 200}
            for i in range(N_FEATURES)]


def _beta(i: int, sample: dict) -> float:
    # a different baseline curve than cohort A (independent cohort), same planted signal shift
    base = 0.28 + ((i * 13 + 7) % 40) / 100.0
    if i in _SIGNAL_PROBES and sample["Sample_Group"] == "level2":
        base += _SHIFT
    return round(min(base, 0.999999), 6)


def build() -> None:
    samples = _samples()
    probes = _probes()
    manifest = {
        "uid": "epicv2_casectrl_demo_b@1",
        "dim": [N_FEATURES, N_SAMPLES],
        "assays": [{"name": "beta", "ref": "epicv2_casectrl_demo_b.betas.tsv"}],
        "col_data": samples,
        "row_data": probes,
        "metadata": {"genome_assembly": "hg38", "array": "EPICv2"},
    }
    (_DIR / "epicv2_casectrl_demo_b.json").write_text(json.dumps(manifest, indent=2) + "\n")

    header = "\t".join(["feature_id"] + [s["sample_id"] for s in samples])
    rows = [header]
    for i, probe in enumerate(probes):
        cells = [probe["feature_id"]] + [f"{_beta(i, s):.6f}" for s in samples]
        rows.append("\t".join(cells))
    (_DIR / "epicv2_casectrl_demo_b.betas.tsv").write_text("\n".join(rows) + "\n")


if __name__ == "__main__":
    build()
