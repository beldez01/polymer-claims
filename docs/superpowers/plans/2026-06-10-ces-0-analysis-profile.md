# CES-0 — AnalysisProfile (content-addressed apparatus) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give a claim a versioned, content-addressed `AnalysisProfile` that pins all bioinformatic context, bind it via the existing `oracle_ref` slot so its `ValidationTier` caps strength, and record the realized profile/dataset hashes in `MaterializationContext`.

**Architecture:** Zero new grammar *types* — only three additive-optional string fields on `MaterializationContext`. The `AnalysisProfile` (a frozen pydantic model), its canonical content-hash, the substrate→tier mapping, the profile→`OracleDossier` builders, and the two concrete profiles all live in the umbrella package `polymer_claims` (domain-specific code stays out of the spine). Binding reuses the protocol's existing `oracle_cap` path with no protocol change.

**Tech Stack:** Python 3.14, pydantic v2 (frozen models), `polymer_grammar` + `polymer_protocol`, pytest, ruff, uv workspaces.

**Spec:** `docs/specs/2026-06-10-ces-0-analysis-profile-design.md`
**Audit:** `docs/specs/2026-06-10-ces-architecture-audit.md`

**Design refinement made in this plan (flag for user):** the spec §2 schema showed `substrate` as a field ON the profile. This plan moves `substrate` to the **dossier-build call** instead, because the *same* analysis profile can run over public OR private data (the substrate is a property of the data the profile is applied to, per spec §4 "tier = substrate × validation"). So `AnalysisProfile` carries no `substrate` field; `profile_oracle_dossier(profile, substrate=…)` takes it. This keeps the manuscript profile from falsely baking in one substrate.

**Test commands (memorize):**
- Umbrella: `cd /Users/zbb2/Desktop/polymer-claims && uv run --project . pytest tests/ -q` ; lint `uv run --project . ruff check src tests`
- Grammar: `cd /Users/zbb2/Desktop/polymer-claims/grammar && uv run pytest -q` ; lint `uv run ruff check src tests`
- Full green gate: `bash /Users/zbb2/Desktop/polymer-claims/scripts/check-all.sh`

---

## File Structure

- **Modify** `grammar/src/polymer_grammar/licensing.py` — add 3 optional fields to `MaterializationContext` (Task 1).
- **Create** `grammar/tests/test_materialization_ces.py` — back-compat + new-field round-trip (Task 1).
- **Create** `src/polymer_claims/analysis_profile.py` — the `AnalysisProfile` model, `content_hash`, `profile_oracle_id`, `substrate_tier`, `profile_oracle_dossier`, `profile_oracle_registry` (Tasks 2 & 2b).
- **Create** `src/polymer_claims/profiles.py` — the two concrete profiles + `load_profile` registry (Task 3).
- **Create** `tests/test_analysis_profile.py` — model, hash determinism/distinctness, oracle helpers (Tasks 2, 2b).
- **Create** `tests/test_profiles_registry.py` — the two real profiles load + have distinct deterministic hashes (Task 3).
- **Modify** `src/polymer_claims/exec_adapters.py` — add an optional `oracle_ref` param to `mean_diff_claim` for the integration test (Task 4).
- **Create** `tests/test_profile_binding_e2e.py` — a profile-bound claim's empirical strength is capped to the substrate tier through `run_cycle` (Task 4).
- **Modify** `src/polymer_claims/__init__.py` — re-export `AnalysisProfile`, `load_profile`, `profile_oracle_registry` (Task 5).

---

## Task 1: Extend `MaterializationContext` (grammar — the only core change)

**Files:**
- Modify: `grammar/src/polymer_grammar/licensing.py:28-32`
- Test: `grammar/tests/test_materialization_ces.py`

- [ ] **Step 1: Write the failing test**

Create `grammar/tests/test_materialization_ces.py`:

```python
"""CES-0: MaterializationContext gains three additive-optional content-address keys."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from polymer_grammar import MaterializationContext


def test_back_compat_three_arg_construction_unchanged():
    # Existing call sites pass only id/api_version/data_version — must still work,
    # and the new fields default to None.
    ctx = MaterializationContext(id="M1", api_version="v1", data_version="d1")
    assert ctx.semantic_run_id is None
    assert ctx.profile_hash is None
    assert ctx.dimnames_hash is None


def test_new_fields_round_trip():
    ctx = MaterializationContext(
        id="M1",
        api_version="v1",
        data_version="d1",
        semantic_run_id="sha256:run",
        profile_hash="sha256:prof",
        dimnames_hash="sha256:dims",
    )
    assert ctx.semantic_run_id == "sha256:run"
    assert ctx.profile_hash == "sha256:prof"
    assert ctx.dimnames_hash == "sha256:dims"
    # frozen + extra-forbid still hold
    with pytest.raises(ValidationError):
        MaterializationContext(id="M1", api_version="v1", data_version="d1", bogus="x")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/zbb2/Desktop/polymer-claims/grammar && uv run pytest tests/test_materialization_ces.py -q`
Expected: FAIL — `test_new_fields_round_trip` raises `ValidationError` (extra fields `semantic_run_id`… forbidden).

- [ ] **Step 3: Add the three optional fields**

In `grammar/src/polymer_grammar/licensing.py`, replace the `MaterializationContext` class body (lines 28-32):

```python
class MaterializationContext(_Model):
    id: str
    api_version: str
    data_version: str
    note: str | None = None
    # CES content-address keys (all optional; back-compat — existing call sites unchanged).
    # Populated when a claim is executed against a content-addressed substrate (CES-3):
    semantic_run_id: str | None = None  # SHA256(tool·params·inputs·profile_hash)
    profile_hash: str | None = None     # the realized AnalysisProfile content-address
    dimnames_hash: str | None = None    # the SE-Contract canonical content-address (drift key)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/zbb2/Desktop/polymer-claims/grammar && uv run pytest tests/test_materialization_ces.py -q`
Expected: PASS (2 passed).

- [ ] **Step 5: Confirm no regression + lint**

Run: `cd /Users/zbb2/Desktop/polymer-claims/grammar && uv run pytest -q && uv run ruff check src tests`
Expected: all green (the additive optional fields break nothing).

- [ ] **Step 6: Commit**

```bash
cd /Users/zbb2/Desktop/polymer-claims
git add grammar/src/polymer_grammar/licensing.py grammar/tests/test_materialization_ces.py
git commit -m "feat(grammar): MaterializationContext content-address keys (CES-0)

Add three additive-optional fields (semantic_run_id, profile_hash,
dimnames_hash) so a realized run records exactly which pinned profile over
which dataset produced its value. Back-compat: existing 3-arg construction
unchanged; frozen/extra-forbid intact.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

## Task 2: The `AnalysisProfile` model + canonical `content_hash`

**Files:**
- Create: `src/polymer_claims/analysis_profile.py`
- Test: `tests/test_analysis_profile.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_analysis_profile.py`:

```python
"""CES-0: the AnalysisProfile model + its canonical content-address."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from polymer_claims.analysis_profile import AnalysisProfile, content_hash


def _profile(**overrides) -> AnalysisProfile:
    base = dict(
        profile_id="p_test",
        version="1",
        array_type="EPICv2",
        genome_assembly="hg38",
        manifest="sesameData::EPICv2.hg38.manifest",
        norm_package="sesame",
        norm_method="openSesame",
        norm_prep="QCDPB",
        detection_threshold=0.80,
        detection_rule="retain_if_rate_ge",
        sample_fail_threshold=None,
        cross_reactive_source="Peters2024_CH_WGBS",
        cross_reactive_file_hash="sha256:abc",
        cross_reactive_n_probes=11878,
        snp_method="sesame:M_SNPcommon_1pt",
        snp_maf=None,
        sex_chrom="removed",
        replicate_collapse="mean_of_variants",
        test_on="M_value",
        clamp_lower=1e-6,
        clamp_upper=0.999999,
        design_formula="~ 0 + Sample_Group + Age + Sex",
        contrast="TET2_mut - WT",
        covariates=("Age", "Sex"),
        dmp_method="limma",
        dmp_adjust_method="BH",
        fdr_threshold=0.05,
        engine_version="sesame@x/limma@y/r-4.5.2",
    )
    base.update(overrides)
    return AnalysisProfile(**base)


def test_profile_is_frozen_and_forbids_extras():
    p = _profile()
    with pytest.raises(ValidationError):
        AnalysisProfile(profile_id="x", version="1", bogus="y")  # missing+extra
    with pytest.raises(ValidationError):
        p.profile_id = "mutated"  # frozen


def test_content_hash_is_deterministic_and_prefixed():
    h1 = content_hash(_profile())
    h2 = content_hash(_profile())
    assert h1 == h2
    assert h1.startswith("sha256:")
    assert len(h1) == len("sha256:") + 64


def test_content_hash_changes_with_any_pinned_field():
    base = content_hash(_profile())
    assert content_hash(_profile(detection_threshold=0.05)) != base
    assert content_hash(_profile(design_formula="~ 0 + Sample_Group")) != base
    assert content_hash(_profile(norm_prep="QCDP")) != base
    assert content_hash(_profile(covariates=("Age",))) != base
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/zbb2/Desktop/polymer-claims && uv run --project . pytest tests/test_analysis_profile.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'polymer_claims.analysis_profile'`.

- [ ] **Step 3: Create the model + hash**

Create `src/polymer_claims/analysis_profile.py`:

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/zbb2/Desktop/polymer-claims && uv run --project . pytest tests/test_analysis_profile.py -q`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
cd /Users/zbb2/Desktop/polymer-claims
git add src/polymer_claims/analysis_profile.py tests/test_analysis_profile.py
git commit -m "feat(umbrella): AnalysisProfile model + canonical content_hash (CES-0)

A frozen, flat, hashable profile pinning all three context layers (incl. the
design formula). content_hash uses the SemanticRunID canonicalization for
Python/R hash parity. No stored hash (circular) and no substrate field
(substrate belongs to the data, set at dossier-build time).

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

## Task 2b: Profile → oracle binding helpers (reuse `oracle_cap`)

**Files:**
- Modify: `src/polymer_claims/analysis_profile.py`
- Test: `tests/test_analysis_profile.py` (extend)

- [ ] **Step 1: Write the failing test (append to `tests/test_analysis_profile.py`)**

```python
from polymer_claims.analysis_profile import (
    profile_oracle_dossier,
    profile_oracle_id,
    profile_oracle_registry,
    substrate_tier,
)
from polymer_grammar import ValidationTier


def test_profile_oracle_id_is_id_at_version():
    assert profile_oracle_id(_profile(profile_id="abc", version="3")) == "abc@3"


def test_substrate_tier_maps_known_and_defaults_unvalidated():
    assert substrate_tier("wet_lab_anchor") == ValidationTier.ANCHORED
    assert substrate_tier("recomputable_public") == ValidationTier.BENCHMARKED
    assert substrate_tier("literature") == ValidationTier.INDIRECT
    assert substrate_tier("nonsense") == ValidationTier.UNVALIDATED


def test_profile_oracle_dossier_carries_tier_and_domain():
    d = profile_oracle_dossier(_profile(profile_id="abc", version="1"),
                               substrate="recomputable_public")
    assert d.oracle_id == "abc@1"
    assert d.validation_tier == ValidationTier.BENCHMARKED
    assert "genomic_region" in d.applicability_domain.subject_kinds


def test_profile_oracle_registry_holds_each_profiles_dossier():
    reg = profile_oracle_registry(
        (_profile(profile_id="a", version="1"), "recomputable_public"),
        (_profile(profile_id="b", version="1"), "wet_lab_anchor"),
    )
    assert reg.resolve("a@1").validation_tier == ValidationTier.BENCHMARKED
    assert reg.resolve("b@1").validation_tier == ValidationTier.ANCHORED
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/zbb2/Desktop/polymer-claims && uv run --project . pytest tests/test_analysis_profile.py -q`
Expected: FAIL — `ImportError: cannot import name 'profile_oracle_id'`.

- [ ] **Step 3: Add the helpers to `src/polymer_claims/analysis_profile.py`**

Append these imports near the top (after the existing `from pydantic import …`):

```python
from polymer_protocol import (
    ApplicabilityDomain,
    OracleDossier,
    OracleRegistry,
    ValidationTier,
)
```

Append at the end of the module:

```python
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
    The tier comes from the SUBSTRATE the profile is applied to (not the profile itself)."""
    return OracleDossier(
        oracle_id=profile_oracle_id(profile),
        validation_tier=substrate_tier(substrate),
        applicability_domain=ApplicabilityDomain(subject_kinds=subject_kinds),
        anchor=profile.engine_version,
    )


def profile_oracle_registry(
    *profile_substrate_pairs: tuple[AnalysisProfile, str],
) -> OracleRegistry:
    """An OracleRegistry from (profile, substrate) pairs, ready to pass to run_cycle(oracles=…)."""
    return OracleRegistry(
        dossiers=tuple(
            profile_oracle_dossier(p, substrate=s) for p, s in profile_substrate_pairs
        )
    )
```

Note: `ApplicabilityDomain`, `OracleDossier`, `OracleRegistry`, `ValidationTier` are all
re-exported by `polymer_protocol` (confirmed in `exec_adapters.py:36-43`).

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/zbb2/Desktop/polymer-claims && uv run --project . pytest tests/test_analysis_profile.py -q`
Expected: PASS (7 passed total).

- [ ] **Step 5: Lint + commit**

```bash
cd /Users/zbb2/Desktop/polymer-claims
uv run --project . ruff check src tests
git add src/polymer_claims/analysis_profile.py tests/test_analysis_profile.py
git commit -m "feat(umbrella): profile->oracle binding helpers (CES-0)

profile_oracle_id / substrate_tier / profile_oracle_dossier /
profile_oracle_registry bind a profile to the existing oracle_cap path: the
profile IS the apparatus, the substrate sets the tier ceiling. No protocol
change — reuses the OracleRegistry seam.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

## Task 3: The two concrete profiles + `load_profile` registry

**Files:**
- Create: `src/polymer_claims/profiles.py`
- Test: `tests/test_profiles_registry.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_profiles_registry.py`:

```python
"""CES-0: both real profiles load, are distinct, and hash deterministically."""
from __future__ import annotations

import pytest

from polymer_claims.analysis_profile import content_hash
from polymer_claims.profiles import load_profile


def test_both_profiles_load():
    m = load_profile("tet2_epicv2_hg38_manuscript", "1")
    c = load_profile("canonical_epicv2_hg38_v1", "1")
    assert m.profile_id == "tet2_epicv2_hg38_manuscript"
    assert c.profile_id == "canonical_epicv2_hg38_v1"


def test_unknown_profile_raises():
    with pytest.raises(KeyError):
        load_profile("nope", "1")


def test_profiles_agree_on_normalization_differ_on_detection():
    m = load_profile("tet2_epicv2_hg38_manuscript", "1")
    c = load_profile("canonical_epicv2_hg38_v1", "1")
    # they AGREE on normalization (sesame/QCDPB)
    assert (m.norm_package, m.norm_method, m.norm_prep) == (c.norm_package, c.norm_method, c.norm_prep)
    # and DIFFER on the detection regime
    assert (m.detection_threshold, m.detection_rule) != (c.detection_threshold, c.detection_rule)


def test_profiles_have_distinct_deterministic_hashes():
    m1 = content_hash(load_profile("tet2_epicv2_hg38_manuscript", "1"))
    m2 = content_hash(load_profile("tet2_epicv2_hg38_manuscript", "1"))
    c1 = content_hash(load_profile("canonical_epicv2_hg38_v1", "1"))
    assert m1 == m2          # deterministic
    assert m1 != c1          # distinct regimes -> distinct content-address


def test_cross_reactive_file_hash_is_the_real_wgbs_digest():
    m = load_profile("tet2_epicv2_hg38_manuscript", "1")
    assert m.cross_reactive_n_probes == 11878
    assert m.cross_reactive_file_hash == (
        "sha256:756527d7022855c75a5e0a41895d10c753121b21032c857d159c4bde47fc3013"
    )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/zbb2/Desktop/polymer-claims && uv run --project . pytest tests/test_profiles_registry.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'polymer_claims.profiles'`.

- [ ] **Step 3: Create the registry**

Create `src/polymer_claims/profiles.py`. The values are the real pinnings from the audit §3 (the
WGBS file hash + probe count were computed from
`~/Desktop/Polymer/R-Engine/data/cross_reactive_epicv2_wgbs.txt`):

```python
"""CES-0: the two concrete, versioned AnalysisProfiles + a local resolver.

Mirrors how `datasets/` ships a CSV: a small in-package registry so the local-first slice is
pure and stub-testable with no live R-Engine. Both profiles are EPICv2/hg38 and AGREE on
normalization (sesame/QCDPB); they DIFFER on the detection regime, SNP method, and (manuscript
only) the pinned design formula — proving "which profile" is a named, not defaulted, choice.
"""
from __future__ import annotations

from .analysis_profile import AnalysisProfile

# SHA256 + line count of ~/Desktop/Polymer/R-Engine/data/cross_reactive_epicv2_wgbs.txt
# (Peters 2024 WGBS-validated cross-reactive set; the live cross-project dependency).
_WGBS_HASH = "sha256:756527d7022855c75a5e0a41895d10c753121b21032c857d159c4bde47fc3013"
_WGBS_N = 11878

# The real TET2-manuscript pipeline pinning (audit §3 — ground truth).
TET2_MANUSCRIPT_V1 = AnalysisProfile(
    profile_id="tet2_epicv2_hg38_manuscript",
    version="1",
    array_type="EPICv2",
    genome_assembly="hg38",
    manifest="sesameData::EPICv2.hg38.manifest",
    norm_package="sesame",
    norm_method="openSesame",
    norm_prep="QCDPB",
    detection_threshold=0.80,
    detection_rule="retain_if_rate_ge",
    sample_fail_threshold=None,
    cross_reactive_source="Peters2024_CH_WGBS",
    cross_reactive_file_hash=_WGBS_HASH,
    cross_reactive_n_probes=_WGBS_N,
    snp_method="sesame:M_SNPcommon_1pt",
    snp_maf=None,
    sex_chrom="removed",
    replicate_collapse="mean_of_variants",
    test_on="M_value",
    clamp_lower=1e-6,
    clamp_upper=0.999999,
    design_formula="~ 0 + Sample_Group + Age + Sex",
    contrast="TET2_mut - WT",
    covariates=("Age", "Sex"),
    batch_correction=None,
    cell_adjustment=None,
    dmp_method="limma",
    dmp_adjust_method="BH",
    fdr_threshold=0.05,
    delta_beta_threshold=0.05,
    dmr_method=None,
    seed=None,
    engine_version="sesame/limma/r-4.5.2/bioc-3.22",
)

# The registry canonical_epicv2_hg38_v1 profile (audit §2 — helpers.R:563-570).
CANONICAL_EPICV2_V1 = AnalysisProfile(
    profile_id="canonical_epicv2_hg38_v1",
    version="1",
    array_type="EPICv2",
    genome_assembly="hg38",
    manifest="sesameData::EPICv2.hg38.manifest",
    norm_package="sesame",
    norm_method="openSesame",
    norm_prep="QCDPB",
    detection_threshold=0.05,
    detection_rule="pOOBAH_p_le",
    sample_fail_threshold=0.05,
    cross_reactive_source="Peters2024_CH_WGBS",
    cross_reactive_file_hash=_WGBS_HASH,
    cross_reactive_n_probes=_WGBS_N,
    snp_method="minfi:dropLociWithSnps[SBE,CpG]",
    snp_maf=0.01,
    sex_chrom="removed",
    replicate_collapse="mean_of_variants",
    test_on="M_value",
    clamp_lower=1e-6,
    clamp_upper=0.999999,
    design_formula="~ 0 + group",
    contrast="level2 - level1",
    covariates=(),
    batch_correction=None,
    cell_adjustment=None,
    dmp_method="limma",
    dmp_adjust_method="BH",
    fdr_threshold=0.05,
    delta_beta_threshold=None,
    dmr_method="DMRcate",
    dmr_lambda=1000,
    dmr_c=2,
    dmr_min_cpgs=3,
    seed=None,
    engine_version="sesame/minfi/limma/DMRcate/r-4.5.2/bioc-3.22",
)

_REGISTRY: dict[tuple[str, str], AnalysisProfile] = {
    (p.profile_id, p.version): p for p in (TET2_MANUSCRIPT_V1, CANONICAL_EPICV2_V1)
}


def load_profile(profile_id: str, version: str) -> AnalysisProfile:
    """Resolve a versioned profile from the local registry. KeyError if unknown."""
    try:
        return _REGISTRY[(profile_id, version)]
    except KeyError:
        raise KeyError(f"no profile {profile_id!r}@{version!r} in the CES-0 registry") from None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/zbb2/Desktop/polymer-claims && uv run --project . pytest tests/test_profiles_registry.py -q`
Expected: PASS (5 passed).

- [ ] **Step 5: Lint + commit**

```bash
cd /Users/zbb2/Desktop/polymer-claims
uv run --project . ruff check src tests
git add src/polymer_claims/profiles.py tests/test_profiles_registry.py
git commit -m "feat(umbrella): two real versioned profiles + load_profile (CES-0)

Ship tet2_epicv2_hg38_manuscript@1 (ground truth) and canonical_epicv2_hg38_v1@1
with distinct content-addresses. They agree on normalization (sesame/QCDPB),
differ on detection regime / SNP method / design formula. WGBS file hash +
count are the real digest of the live cross-reactive dependency.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

## Task 4: End-to-end — a profile-bound claim's strength caps to the substrate tier through `run_cycle`

This proves the binding works through the real protocol, reusing the existing `mean_diff`
execution substrate (real methylation execution is CES-2; CES-0 proves the profile→tier→cap
path, not the methylation math). We add one optional param to `mean_diff_claim` so the test can
point a claim's `oracle_ref` at a profile.

**Files:**
- Modify: `src/polymer_claims/exec_adapters.py:113-169` (add `oracle_ref` param)
- Test: `tests/test_profile_binding_e2e.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_profile_binding_e2e.py`:

```python
"""CES-0 capstone: binding a claim to a profile (via oracle_ref) caps its empirical strength
to the substrate tier, end-to-end through run_cycle."""
from __future__ import annotations

from polymer_claims.analysis_profile import (
    profile_oracle_id,
    profile_oracle_registry,
)
from polymer_claims.exec_adapters import (
    StatsPureAdapter,
    StatsStdlibAdapter,
    _PROVISIONAL_STRENGTH,
    independent_registry,
    mean_diff_claim,
)
from polymer_claims.profiles import load_profile
from polymer_grammar import FDRLedger, Status
from polymer_protocol import Corpus, run_cycle


def _run_with(profile, substrate):
    claim = mean_diff_claim(
        "ces0-bound",
        comparator=__import__("polymer_grammar").Comparator.GT,
        threshold=10.0,
        strength=_PROVISIONAL_STRENGTH,
        oracle_ref=profile_oracle_id(profile),
    )
    corpus = Corpus(claims=(claim,), fdr_ledger=FDRLedger(target_fdr=0.05))
    result = run_cycle(
        corpus,
        adapters=(StatsPureAdapter(), StatsStdlibAdapter()),
        adapter_registry=independent_registry(),
        oracles=profile_oracle_registry((profile, substrate)),
        budget=2.5,
    )
    return result.corpus.by_id()["ces0-bound"]


def test_recomputable_public_caps_empirical_axes_to_benchmarked():
    profile = load_profile("tet2_epicv2_hg38_manuscript", "1")
    claim = _run_with(profile, "recomputable_public")
    assert claim.status == Status.LICENSED
    s = claim.strength
    # BENCHMARKED ceiling = 0.6 on the four goodness empirical axes (capped DOWN from 0.8/0.9/0.7).
    assert s.magnitude == 0.6
    assert s.evidence_against_null == 0.6
    assert s.world_contact == 0.6
    assert s.certainty == 0.6
    # theory axes untouched.
    assert s.severity == _PROVISIONAL_STRENGTH.severity
    assert s.explanatory_virtue == _PROVISIONAL_STRENGTH.explanatory_virtue


def test_wet_lab_anchor_caps_higher_than_public():
    profile = load_profile("tet2_epicv2_hg38_manuscript", "1")
    claim = _run_with(profile, "wet_lab_anchor")
    assert claim.status == Status.LICENSED
    # ANCHORED ceiling = 0.85; magnitude 0.8 <= 0.85 so it is UNCAPPED (stays 0.8),
    # world_contact 0.9 caps DOWN to 0.85.
    assert claim.strength.magnitude == 0.8
    assert claim.strength.world_contact == 0.85
```

Note: confirm `run_cycle`'s parameter names by reading the existing live-data test
(`tests/test_earned_strength_live.py` and `tests/test_exec_adapters.py`) — they call
`run_cycle(corpus, adapters=…, adapter_registry=…, oracles=…, budget=…)`. If a keyword differs,
match the existing call sites exactly (do NOT invent names).

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/zbb2/Desktop/polymer-claims && uv run --project . pytest tests/test_profile_binding_e2e.py -q`
Expected: FAIL — `mean_diff_claim()` got an unexpected keyword argument `oracle_ref`.

- [ ] **Step 3: Add the optional `oracle_ref` param to `mean_diff_claim`**

In `src/polymer_claims/exec_adapters.py`, modify the `mean_diff_claim` signature to add a
keyword (after `strength`):

```python
    strength: StrengthVector | None = None,
    oracle_ref: str = _APPARATUS_ORACLE,
) -> Claim:
```

and use it in the `OperationNode` (replace the existing `oracle_ref=_APPARATUS_ORACLE,` line at
~144):

```python
        oracle_ref=oracle_ref,
```

Existing call sites pass no `oracle_ref`, so they keep the `_APPARATUS_ORACLE` default — byte-unchanged behavior.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/zbb2/Desktop/polymer-claims && uv run --project . pytest tests/test_profile_binding_e2e.py -q`
Expected: PASS (2 passed).

If `test_recomputable_public_*` fails on the LICENSED assertion (not the cap), the strength-bearing
claim may be held by the #3a selective-inference bar at this budget — in that case set the claim's
`threshold` low enough that the computed mean-diff strongly clears it (the existing earned-strength
test does this) OR follow the exact pattern in `tests/test_exec_adapters.py`'s oracle-cap test,
which already licenses a single strength-bearing mean_diff claim. Mirror that test's construction
rather than diverging.

- [ ] **Step 5: Confirm the existing exec-adapters tests still pass (back-compat of the signature change)**

Run: `cd /Users/zbb2/Desktop/polymer-claims && uv run --project . pytest tests/test_exec_adapters.py tests/test_real_data_generation.py -q`
Expected: all green (default `oracle_ref` preserves prior behavior).

- [ ] **Step 6: Lint + commit**

```bash
cd /Users/zbb2/Desktop/polymer-claims
uv run --project . ruff check src tests
git add src/polymer_claims/exec_adapters.py tests/test_profile_binding_e2e.py
git commit -m "feat(umbrella): profile-bound claim tier-caps through run_cycle (CES-0)

Add an optional oracle_ref to mean_diff_claim (default unchanged) so a claim
can point at a profile-as-apparatus. End-to-end: binding the manuscript
profile at recomputable_public substrate caps empirical axes to BENCHMARKED
0.6; wet_lab_anchor caps to 0.85 — proving the profile->tier->cap path
through the real protocol with no protocol change.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

## Task 5: Re-exports + full green gate + docs

**Files:**
- Modify: `src/polymer_claims/__init__.py`
- Modify: `docs/superpowers/CONTINUE.md` (state line)

- [ ] **Step 1: Add umbrella re-exports**

In `src/polymer_claims/__init__.py`, add to the imports and `__all__`:

```python
from polymer_claims.analysis_profile import (
    AnalysisProfile,
    content_hash,
    profile_oracle_id,
    profile_oracle_registry,
    substrate_tier,
)
from polymer_claims.profiles import load_profile
```

and add these names to the `__all__` list (keep it sorted):
`"AnalysisProfile"`, `"content_hash"`, `"load_profile"`, `"profile_oracle_id"`,
`"profile_oracle_registry"`, `"substrate_tier"`.

- [ ] **Step 2: Verify the umbrella imports + suite**

Run: `cd /Users/zbb2/Desktop/polymer-claims && uv run --project . python -c "import polymer_claims; print(polymer_claims.AnalysisProfile, polymer_claims.load_profile)" && uv run --project . pytest tests/ -q && uv run --project . ruff check src tests`
Expected: prints the two symbols; all umbrella tests green; ruff clean.

- [ ] **Step 3: Run the full green gate**

Run: `bash /Users/zbb2/Desktop/polymer-claims/scripts/check-all.sh`
Expected: ends with `ALL GREEN` (umbrella + grammar + protocol + isolation + viewer).

- [ ] **Step 4: Update CONTINUE.md**

In `docs/superpowers/CONTINUE.md`, update the top "▶▶ NEXT ACTION" block to record CES-0 done and
set the next action to **CES-1 (DataHandle → SE-Contract DRS-shaped ref + local methylation
SE-Contract fixture)**. Add a one-paragraph "✅ CES-0 DONE" entry mirroring the existing phase
entries (modules added, the two profiles, the three MaterializationContext fields, tests green,
spec/plan paths).

- [ ] **Step 5: Commit**

```bash
cd /Users/zbb2/Desktop/polymer-claims
git add src/polymer_claims/__init__.py docs/superpowers/CONTINUE.md
git commit -m "chore(ces-0): re-exports + CONTINUE; CES-0 complete

Re-export AnalysisProfile/load_profile/profile_oracle_registry for embedders.
check-all ALL GREEN. Next: CES-1 (DataHandle -> SE-Contract DRS ref).

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

## Self-Review (completed by plan author)

**Spec coverage:** §1 (profile-not-grammar) → Tasks 2/3 keep it umbrella-side. §2 AnalysisProfile + §2a registry → Tasks 2/3. §3 canonical hash + parity → Task 2 `content_hash`. §4 oracle_ref binding + substrate→tier + dossier → Task 2b (+ the substrate-on-binding refinement, flagged in the header). §5 MaterializationContext extension → Task 1. §6 first-claim scalar/methodological-independence → the run_cycle capstone reuses the two independent stats adapters (Task 4); the methylation realizer is explicitly deferred to CES-1/2. §7 deliverables → all Tasks; §8 invariants → grammar touch is 3 optional fields only, no new types, back-compat tested. **Deferred per spec (NOT in this plan):** B1/B2/B3 plumbing, drift wiring, vector leaves, live R-Engine — correct, those are CES-1/2/3.

**Placeholder scan:** none — every code block is complete; the one real digest is embedded; Task 4 Step 4 gives a concrete fallback pointing at an existing passing test rather than "handle it."

**Type consistency:** `content_hash`, `profile_oracle_id`, `substrate_tier`, `profile_oracle_dossier`, `profile_oracle_registry`, `load_profile`, `AnalysisProfile` field names are identical across Tasks 2/2b/3/4/5 and the tests. `mean_diff_claim(oracle_ref=…)` matches its Task-4 definition. `run_cycle(adapters=, adapter_registry=, oracles=, budget=)` is flagged to verify against existing call sites before relying on it.
