"""DEFINITIONAL synthetic calibration harness (impure; needs the [calibrate] extra for numpy).

Generates Beta-distributed synthetic cohorts with KNOWN ground truth, writes them as SE-Contract
files, and (Task 6) runs them through the REAL gate behind `using_contract_root`. NOT re-exported
from polymer_claims.__init__ (keeps base import numpy-free)."""
from __future__ import annotations

import hashlib
import json
import tempfile
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from polymer_grammar import Comparator, FDRLedger, MaterializationContext, Status
from polymer_protocol.calibration import (
    CalibrationLedger,
    CalibrationTarget,
    GeneratingModelParams,
    ResolutionKind,
    ResolutionRecord,
    ResolutionVerdict,
)
from polymer_protocol.corpus import Corpus

from .contracts import using_contract_root
from .evidence import evidence_map
from .materialization import materialization_map
from .methyl_adapters import (
    RegionLmCoefAdapter,
    RegionMeanDiffAdapter,
    methyl_independent_registry,
    region_delta_beta_claim,
)
from .node import NodeRunner


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


# ---------------------------------------------------------------------------
# Task 6: end-to-end harness -- runs synthetic batches through the REAL gate
# ---------------------------------------------------------------------------

_ADAPTERS = (RegionMeanDiffAdapter(), RegionLmCoefAdapter())


def run_batch(
    *, model: GeneratingModelParams, batch_id: str, seed: int
) -> tuple[ResolutionRecord, ...]:
    """Generate a synthetic cohort, drive the REAL gate, emit DEFINITIONAL ResolutionRecords.

    One record per LICENSED claim. LICENSED null region -> verdict=FAILED; LICENSED true region ->
    verdict=UPHELD. Only licensed claims appear (calibration measures the reliability of earned
    standing). The contract cache is cleared after each batch to avoid cross-batch cache collisions
    (the lru_cache key includes root, so collisions are impossible in practice, but clearing is safe).
    """
    with tempfile.TemporaryDirectory() as tmp:
        batch = synthetic_cohort(model=model, batch_id=batch_id, seed=seed, root=tmp)
        claims = tuple(
            region_delta_beta_claim(
                reg.region_id,
                ref=f"se:{batch.contract_uid}",
                region_probes=reg.probes,
                group_col="Sample_Group",
                level_a="control",
                level_b="case",
                comparator=Comparator.GT,
                threshold=model.tau,
            )
            for reg in batch.regions
        )
        truth_of = {reg.region_id: reg.constructed_truth for reg in batch.regions}
        corpus = Corpus(claims=claims, fdr_ledger=FDRLedger(target_fdr=model.target_fdr))
        base_ctx = MaterializationContext(
            id="cal", api_version="v1", data_version=batch.contract_uid
        )

        with using_contract_root(batch.root):
            mats = materialization_map(corpus, base_ctx)
            ev = evidence_map(corpus)
            # adapter_registry flows through **run_cycle_kwargs into run_cycle; it is NOT a named
            # kwarg of NodeRunner.__init__. evalue_gate=True but we provide _static_evidence so
            # tick() uses ev directly rather than recomputing it.
            runner = NodeRunner(
                corpus,
                adapters=_ADAPTERS,
                ctx=base_ctx,
                evalue_gate=True,
                materializations=mats,
                evidence=ev,
                adapter_registry=methyl_independent_registry(),
            )
            runner.tick()
            final = runner.corpus

        recs: list[ResolutionRecord] = []
        for c in final.claims:
            if c.status != Status.LICENSED:
                continue
            truth = truth_of[c.id]
            recs.append(ResolutionRecord(
                subject_claim_id=c.id,
                license_epoch=0,
                resolution_kind=ResolutionKind.DEFINITIONAL,
                calibration_target=CalibrationTarget.REALIZED_FDR,
                verdict=ResolutionVerdict.UPHELD if truth else ResolutionVerdict.FAILED,
                stated_q=model.target_fdr,
                observed_at_cycle=0,
                constructed_truth=truth,
                model_id=model.model_id,
                batch_id=batch_id,
            ))
        return tuple(recs)


def run_calibration(
    *, model: GeneratingModelParams, n_batches: int, base_seed: int
) -> CalibrationLedger:
    """Run `n_batches` synthetic batches through the REAL gate and aggregate into a CalibrationLedger.

    Each batch gets a unique batch_id and seed derived from base_seed + i so that batches are
    independent but fully reproducible. The ledger records the generating model for the summary's
    n_generated accounting.
    """
    records: list[ResolutionRecord] = []
    for i in range(n_batches):
        bid = f"{model.model_id}-{i}"
        records.extend(run_batch(model=model, batch_id=bid, seed=base_seed + i))
    return CalibrationLedger(
        records=tuple(records),
        generating_models=(model,),
        default_target_q=model.target_fdr,
    )
