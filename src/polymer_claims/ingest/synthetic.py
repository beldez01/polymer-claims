"""Deterministic, fully-synthetic HM450-shaped inputs for the offline kernel proof.

No real TCGA bytes — a realistic-shaped fixture (IDH-mut vs WT, a planted differential-methylation
signal + null bulk) that licenses the n-DMP claim through the REAL gate. Stdlib-only generation
(no numpy); reuses the existing build_contract verbatim.
"""
from __future__ import annotations

import random

from polymer_claims.ingest.transform import build_contract

SYNTH_SEED = 20260623
N_SAMPLES = 40          # 20 WT + 20 IDH_mut
N_PROBES = 3000
N_DM = 150              # planted differentially-methylated probes
_UID_STEM = "tcga_laml_idh_synth"
_SIGMA = 0.03           # within-group noise
_DELTA = 0.30           # WT 0.30 vs IDH_mut 0.60 on planted probes


def _clamp(x: float) -> float:
    return 0.0 if x < 0.0 else (1.0 if x > 1.0 else x)


def build_synthetic_contract(out_dir, *, seed: int = SYNTH_SEED) -> str:
    """Synthesize a deterministic HM450-shaped contract and write it via the real build_contract.
    Returns the uid 'tcga_laml_idh_synth@1'."""
    rng = random.Random(seed)
    sample_ids = [f"SYN-{i:04d}" for i in range(N_SAMPLES)]
    half = N_SAMPLES // 2
    groups = {s: ("WT" if i < half else "IDH_mut") for i, s in enumerate(sample_ids)}
    clinical = {s: {"Age": rng.randint(40, 80), "Sex": rng.choice(["male", "female"])}
                for s in sample_ids}

    betas: dict[str, dict[str, float]] = {}
    row_meta: dict[str, dict] = {}
    for p in range(N_PROBES):
        probe = f"cgSYN{p:06d}"
        row_meta[probe] = {"chr": f"chr{(p % 22) + 1}", "pos": (p + 1) * 100}
        planted = p < N_DM
        # drawn for every probe (even planted, where it's unused) to keep the RNG stream — and the pinned n-DMP count — stable if N_DM changes
        base_mu = rng.uniform(0.2, 0.8)
        col: dict[str, float] = {}
        for s in sample_ids:
            if planted:
                mu = 0.30 if groups[s] == "WT" else 0.30 + _DELTA
            else:
                mu = base_mu
            col[s] = _clamp(rng.gauss(mu, _SIGMA))
        betas[probe] = col

    return build_contract(
        out_dir, uid_stem=_UID_STEM,
        betas=betas, row_meta=row_meta, groups=groups,
        clinical=clinical, sample_ids=sample_ids,
    )
