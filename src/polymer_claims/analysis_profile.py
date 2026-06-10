"""CES-0: the AnalysisProfile — a versioned, content-addressed bundle that pins ALL of a
methylation analysis's bioinformatic context (the three layers the SemanticRunID misses:
SE-Contract preprocessing, Boris tool params, and the hardcoded R internals incl. the design
formula). Umbrella/impure-adjacent ONLY — the grammar spine never imports this; bioinformatic
vocabulary stays out of the core.

The profile carries NO stored hash (that would be circular) and NO `substrate` field (substrate
is a property of the DATA the profile is applied to — see profile_oracle_dossier). `content_hash`
canonicalizes with sorted-keys/no-whitespace JSON, mirroring Polymer's
SemanticRunID.param_signature canonicalization — the INTENDED basis for Python/R hash parity.
Parity is not yet validated end-to-end: R's float JSON rendering (e.g. `1e-06`, trailing zeros,
scientific notation) can differ from Python's, so CES-3 must validate this against the live R
serializer with a golden-hash fixture before any R-side code relies on the digest. Within Python
the hash is deterministic, which is all CES-0 requires.
"""
from __future__ import annotations

import hashlib
import json

from pydantic import BaseModel, ConfigDict

from polymer_protocol import (
    ApplicabilityDomain,
    OracleDossier,
    OracleRegistry,
    ValidationTier,
)


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


# Substrate (the nature of the DATA the profile is applied to) -> validation-tier ceiling
# (spec §4 / CES §5). The profile pins the METHOD; the substrate sets the CEILING.
_SUBSTRATE_TIER = {
    "wet_lab_anchor": ValidationTier.ANCHORED,        # sorted-cell EM-seq / the 48-sample cohort
    "recomputable_public": ValidationTier.BENCHMARKED,  # public GEO/TCGA methylation SE Contract
    "computed_reference": ValidationTier.INDIRECT,
    "literature": ValidationTier.INDIRECT,
    "unvalidated": ValidationTier.UNVALIDATED,
}

_DEFAULT_SUBJECT_KINDS = ("genomic_region", "cohort")


def profile_oracle_id(profile: AnalysisProfile) -> str:
    """The oracle_ref a claim sets to bind this profile-as-apparatus: '<profile_id>@<version>'."""
    return f"{profile.profile_id}@{profile.version}"


def substrate_tier(substrate: str) -> ValidationTier:
    """Map a substrate key to its tier ceiling; an unknown substrate is conservatively
    UNVALIDATED (0.0)."""
    return _SUBSTRATE_TIER.get(substrate, ValidationTier.UNVALIDATED)


def profile_oracle_dossier(
    profile: AnalysisProfile,
    *,
    substrate: str,
    subject_kinds: tuple[str, ...] = _DEFAULT_SUBJECT_KINDS,
) -> OracleDossier:
    """Build the OracleDossier that makes this profile the apparatus capping a claim's strength.
    The tier comes from the SUBSTRATE the profile is applied to (not the profile itself).

    PRECONDITION: the default `subject_kinds=("genomic_region","cohort")` is a BOUNDED domain,
    so a claim with `subject=None` resolves out-of-domain -> UNVALIDATED (cap 0.0). Real CES-2
    methylation claims carry a `genomic_region` subject (default applies); a subjectless proxy
    must pass `subject_kinds=()` to opt into an unbounded domain."""
    return OracleDossier(
        oracle_id=profile_oracle_id(profile),
        validation_tier=substrate_tier(substrate),
        applicability_domain=ApplicabilityDomain(subject_kinds=subject_kinds),
        anchor=profile.engine_version,
    )


def profile_oracle_registry(
    *profile_substrate_pairs: tuple[AnalysisProfile, str],
) -> OracleRegistry:
    """An OracleRegistry from (profile, substrate) pairs, ready to pass to run_cycle(oracles=…).
    Uses `profile_oracle_dossier`'s BOUNDED default domain: claims must carry a matching subject
    (e.g. `genomic_region`) or they resolve UNVALIDATED — see that precondition note."""
    return OracleRegistry(
        dossiers=tuple(
            profile_oracle_dossier(p, substrate=s) for p, s in profile_substrate_pairs
        )
    )
