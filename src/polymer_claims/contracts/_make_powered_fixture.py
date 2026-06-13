"""Deterministic WELL-POWERED case/control EPICv2-shaped methylation fixture.

100 samples (50 level1 / 50 level2), 24 probes, fixed seed.

- STRONG region (cg00000001-05): level2 = baseline + 0.30 + N(0, 0.03).  E-value >> 40.
- WEAK region  (cg00000006-10): level2 = baseline + 0.12 + N(0, 0.02).  Satisfied (d>0.10) but e < bar.
- Control      (cg00000011-24): no effect.

Re-run: python src/polymer_claims/contracts/_make_powered_fixture.py
"""
from __future__ import annotations

import json
import random
from pathlib import Path

_DIR = Path(__file__).parent

N_LEVEL1 = 50
N_LEVEL2 = 50
N_SAMPLES = N_LEVEL1 + N_LEVEL2
N_FEATURES = 24

_BASELINE_MU = 0.45
_BASELINE_SD = 0.03

_STRONG_SHIFT = 0.30
_STRONG_NOISE_SD = 0.03

_WEAK_SHIFT = 0.12
_WEAK_NOISE_SD = 0.02

_CONTROL_NOISE_SD = 0.03

_SEED = 42


def _clip(x: float) -> float:
    return max(0.0, min(1.0, x))


def _gauss_clipped(rng: random.Random, mu: float, sd: float) -> float:
    return _clip(rng.gauss(mu, sd))


def build() -> None:
    rng = random.Random(_SEED)

    # --- samples ---
    col_data: list[dict] = []
    for j in range(N_SAMPLES):
        group = "level1" if j < N_LEVEL1 else "level2"
        sid = f"s{j + 1:03d}"
        col_data.append({"sample_id": sid, "Sample_Group": group})

    # --- probes ---
    row_data: list[dict] = [
        {"feature_id": f"cg{i + 1:08d}", "chr": "chr1", "pos": 1_000_000 + i * 200}
        for i in range(N_FEATURES)
    ]

    # --- betas: shape (N_FEATURES, N_SAMPLES) ---
    # Pre-generate all baselines (level1 values for every probe x sample)
    # then apply shifts for level2 samples per region.
    betas: list[list[float]] = []  # betas[probe_idx][sample_idx]
    for i in range(N_FEATURES):
        row: list[float] = []
        for j, col in enumerate(col_data):
            group = col["Sample_Group"]
            base = _gauss_clipped(rng, _BASELINE_MU, _BASELINE_SD)
            if group == "level2":
                if i < 5:  # STRONG region: probes 0-4 -> cg00000001-05
                    noise = rng.gauss(0.0, _STRONG_NOISE_SD)
                    val = _clip(base + _STRONG_SHIFT + noise)
                elif i < 10:  # WEAK region: probes 5-9 -> cg00000006-10
                    noise = rng.gauss(0.0, _WEAK_NOISE_SD)
                    val = _clip(base + _WEAK_SHIFT + noise)
                else:  # control
                    noise = rng.gauss(0.0, _CONTROL_NOISE_SD)
                    val = _clip(base + noise)
            else:
                val = base
            row.append(val)
        betas.append(row)

    # --- manifest ---
    sample_ids = [c["sample_id"] for c in col_data]
    manifest = {
        "uid": "epicv2_casectrl_powered@1",
        "dim": [N_FEATURES, N_SAMPLES],
        "assays": [{"name": "beta", "ref": "epicv2_casectrl_powered.betas.tsv"}],
        "col_data": col_data,
        "row_data": row_data,
        "metadata": {"genome_assembly": "hg38", "array": "EPICv2"},
    }
    (_DIR / "epicv2_casectrl_powered.json").write_text(json.dumps(manifest, indent=2) + "\n")

    # --- TSV ---
    header = "\t".join(["feature_id"] + sample_ids)
    rows = [header]
    for i, probe in enumerate(row_data):
        cells = [probe["feature_id"]] + [f"{v:.4f}" for v in betas[i]]
        rows.append("\t".join(cells))
    (_DIR / "epicv2_casectrl_powered.betas.tsv").write_text("\n".join(rows) + "\n")

    print("Wrote epicv2_casectrl_powered.json and epicv2_casectrl_powered.betas.tsv")


if __name__ == "__main__":
    build()
