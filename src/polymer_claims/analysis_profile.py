"""CES-0: the AnalysisProfile — a versioned, content-addressed bundle that pins ALL of a
methylation analysis's bioinformatic context (the three layers the SemanticRunID misses:
SE-Contract preprocessing, Boris tool params, and the hardcoded R internals incl. the design
formula). Umbrella/impure-adjacent ONLY — the grammar spine never imports this; bioinformatic
vocabulary stays out of the core.

The profile carries NO stored hash (that would be circular) and NO `substrate` field (substrate
is a property of the DATA the profile is applied to — see profile_oracle_dossier). `content_hash`
canonicalizes with sorted-keys/no-whitespace JSON — the SAME canonicalization Polymer's
SemanticRunID.param_signature uses — so Python and R compute the same digest (hash parity).
"""
from __future__ import annotations

import hashlib
import json

from pydantic import BaseModel, ConfigDict


class AnalysisProfile(BaseModel):
    """A pinned methylation-analysis regime. Flat + hashable (tuples, no dicts) so its
    content-address is stable. Optional fields default to None/empty for regimes that omit
    a step (e.g. no DMR, no cell adjustment)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    profile_id: str
    version: str
    # array / genome
    array_type: str
    genome_assembly: str
    manifest: str
    # normalization
    norm_package: str
    norm_method: str
    norm_prep: str | None = None
    # probe filtering
    detection_threshold: float
    detection_rule: str
    sample_fail_threshold: float | None = None
    cross_reactive_source: str
    cross_reactive_file_hash: str
    cross_reactive_n_probes: int
    snp_method: str
    snp_maf: float | None = None
    sex_chrom: str
    replicate_collapse: str
    # value space
    test_on: str
    clamp_lower: float
    clamp_upper: float
    # design
    design_formula: str
    contrast: str
    covariates: tuple[str, ...] = ()
    batch_correction: str | None = None
    cell_adjustment: str | None = None
    # differential method
    dmp_method: str
    dmp_adjust_method: str
    fdr_threshold: float
    delta_beta_threshold: float | None = None
    # regional method (optional)
    dmr_method: str | None = None
    dmr_lambda: int | None = None
    dmr_c: int | None = None
    dmr_min_cpgs: int | None = None
    # reproducibility
    seed: int | None = None
    engine_version: str


def content_hash(profile: AnalysisProfile) -> str:
    """Canonical content-address of the whole pinned regime. Sorted-keys/no-whitespace JSON
    (Polymer SemanticRunID parity) -> SHA256, prefixed 'sha256:'."""
    payload = profile.model_dump(mode="json")
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()
