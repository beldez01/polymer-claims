"""DEFINITIONAL synthetic calibration harness (impure; needs the [calibrate] extra for numpy).

Generates Beta-distributed synthetic cohorts with KNOWN ground truth, writes them as SE-Contract
files, and (Task 6) runs them through the REAL gate behind `using_contract_root`. NOT re-exported
from polymer_claims.__init__ (keeps base import numpy-free)."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from polymer_protocol.calibration import GeneratingModelParams


@dataclass(frozen=True)
class SyntheticRegion:
    region_id: str
    probes: tuple[str, ...]
    constructed_truth: bool


@dataclass(frozen=True)
class SyntheticBatch:
    batch_id: str
    contract_uid: str
    root: Path
    regions: tuple[SyntheticRegion, ...]
    group_of: dict[str, str]   # sample_id -> "case"|"control"


def _beta_ab(mean: float, dispersion: float) -> tuple[float, float]:
    mean = min(max(mean, 1e-4), 1 - 1e-4)
    return mean * dispersion, (1 - mean) * dispersion


def write_synthetic_contract(root, uid, *, samples, probes, betas, groups) -> None:
    """betas: np.ndarray [n_probes, n_samples] in [0,1]; groups: {sample_id: 'case'|'control'}."""
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    stem = uid.split("@")[0]
    manifest = {
        "uid": uid,
        "dim": [len(probes), len(samples)],
        "assays": [{"name": "beta", "ref": f"{stem}.betas.tsv"}],
        "col_data": [{"sample_id": s, "Sample_Group": groups[s]} for s in samples],
        "row_data": [{"feature_id": p, "chr": "chr1", "pos": 1000 + i} for i, p in enumerate(probes)],
        "metadata": {"genome_assembly": "hg38", "array": "EPICv2", "shared_cause_factors": []},
    }
    (root / f"{stem}.json").write_text(json.dumps(manifest, sort_keys=True))
    header = "feature_id\t" + "\t".join(samples)
    rows = [header]
    for i, p in enumerate(probes):
        rows.append(p + "\t" + "\t".join(f"{betas[i, j]:.6f}" for j in range(len(samples))))
    (root / f"{stem}.betas.tsv").write_text("\n".join(rows) + "\n")


def synthetic_cohort(*, model: GeneratingModelParams, batch_id: str, seed: int,
                     root) -> SyntheticBatch:
    rng = np.random.default_rng(seed)
    n = model.n_per_group
    samples = [f"S{j:03d}" for j in range(2 * n)]
    groups = {s: ("control" if j < n else "case") for j, s in enumerate(samples)}
    regions: list[SyntheticRegion] = []
    all_probes: list[str] = []
    rows: list[np.ndarray] = []
    n_true = round(model.fraction_true * model.n_generated)
    for r in range(model.n_generated):
        truth = r < n_true
        probes = tuple(f"cg_{batch_id}_{r}_{k}" for k in range(model.n_probes_per_region))
        regions.append(SyntheticRegion(f"reg_{batch_id}_{r}", probes, truth))
        base = 0.30
        for k, p in enumerate(probes):
            all_probes.append(p)
            ctrl_a, ctrl_b = _beta_ab(base, model.dispersion)
            case_mean = base + (model.effect_size if truth else 0.0)
            case_a, case_b = _beta_ab(case_mean, model.dispersion)
            row = np.concatenate([
                rng.beta(ctrl_a, ctrl_b, n), rng.beta(case_a, case_b, n)
            ])
            rows.append(row)
    betas = np.vstack(rows)
    # content-derived unique uid (no collision with bundled uids; sound under the (uid,root) cache)
    digest = hashlib.sha256(betas.tobytes() + batch_id.encode()).hexdigest()[:12]
    uid = f"synthetic_{digest}@1"
    write_synthetic_contract(root, uid, samples=samples, probes=all_probes, betas=betas, groups=groups)
    return SyntheticBatch(batch_id, uid, Path(root), tuple(regions), groups)
