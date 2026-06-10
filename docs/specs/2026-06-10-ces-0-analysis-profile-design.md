# CES-0 — `AnalysisProfile` as the content-addressed apparatus

**Status:** Design / phase spec. v0.1
**Date:** 2026-06-10
**Author:** Z. Belden
**Depends on:** the CES interface contract (`2026-06-09-claim-evidence-socket.md`) and the
architecture audit (`2026-06-10-ces-architecture-audit.md`).
**Decided forks (this session):** profile-reference model (A1); fold Layer-C internals into the
profile so its hash pins everything (B); scalar reduction for the first terminal, vector leaves
deferred (C); reuse the existing `oracle_ref` slot to bind the profile (no new grammar slot);
local-first seam (no live R-Engine in tests); methodological independence as the air-gap default;
**encode BOTH the TET2-manuscript profile and the registry `canonical_epicv2_hg38_v1` profile as
distinct versioned profiles**, so a claim must name which one it licensed under.

---

## 0. Goal

Give a claim a single, versioned, **content-addressed** unit of analytical context — the
`AnalysisProfile` — so that "LICENSED" means *"tool T, run under fully-pinned profile P, over
dataset D, beat criterion θ — and every pinned choice is captured in the content-address."*
This is the prerequisite that must sit in front of any B1/B2 plumbing: without it, a license
silently inherits the SemanticRunID's Layer-C gap (design formula, `sesame_prep`, cell
reference, analysis-profile selection are not hashed today — see the audit §2).

CES-0 ships the **representation and the binding**, design-only here, then implemented as its
own plan. It does NOT build the live `BorisExecutionAdapter`; that is a later phase.

---

## 1. The load-bearing principle: the profile is NOT a grammar concept

The 15 bioinformatic choices (normalization, filtering, array/genome, design formula, DMP/DMR
method + thresholds, cell adjustment, seeds) are **domain-specific** and belong on the Polymer
side, which already owns them. The EOS spine stays domain-agnostic. Therefore:

- **Zero new grammar *types*.** The `AnalysisProfile` object lives in the **umbrella package**
  (`polymer_claims`) for the local-first slice, and conceptually on the **Polymer side** (it is
  a completed, hashed `analysis_profile`). The grammar never imports it.
- The grammar gains only **three additive-optional fields on one existing model**
  (`MaterializationContext`), all generic strings — no domain vocabulary enters the core.
- The profile binds to a claim through the **already-present, unbound `oracle_ref` slot** on
  `OperationNode` (`grammar/src/polymer_grammar/operations.py:79`). The profile *is* the
  apparatus whose `ValidationTier` caps the claim's empirical strength.

This keeps the "writes-only-IR / no domain in the core" invariant intact.

---

## 2. The `AnalysisProfile` object (umbrella / Polymer-side)

A frozen, hashable record that pins all three audit layers plus the Layer-C residue. Illustrative
schema (the plan fixes exact field names; values shown are the real TET2-manuscript pinning from
the audit §3, which is the first profile we encode):

```jsonc
{
  "profile_id": "tet2_epicv2_hg38_manuscript",
  "version": "1",
  "array": { "type": "EPICv2", "genome_assembly": "hg38",
             "manifest": "sesameData::EPICv2.hg38.manifest" },
  "normalization": { "package": "sesame", "method": "openSesame", "prep": "QCDPB" },
  "filtering": {
    "detection_threshold": 0.80, "detection_rule": "retain_if_rate_ge",
    "cross_reactive": { "source": "Peters2024_CH_WGBS",
                        "file_hash": "sha256:…",  // hash of cross_reactive_epicv2_wgbs.txt (11,878 probes)
                        "n_probes": 11878 },
    "snp": { "method": "sesame:M_SNPcommon_1pt", "maf": null },
    "sex_chrom": "removed", "replicate_collapse": "mean_of_variants"
  },
  "value_space": { "test_on": "M_value", "clamp": [1e-6, 0.999999] },
  "design": { "formula": "~ 0 + Sample_Group + Age + Sex",
              "contrast": "TET2_mut - WT", "covariates": ["Age", "Sex"],
              "batch_correction": null, "cell_adjustment": null },
  "dmp": { "method": "limma", "adjust_method": "BH",
           "fdr_threshold": 0.05, "delta_beta_threshold": 0.05 },
  "dmr": null,
  "reproducibility": { "seed": null,
                       "engine_version": "sesame@<v>/limma@<v>/r-4.5.2/bioc-3.22" },
  "substrate": "recomputable_public",     // → ValidationTier (see §4)
  "profile_hash": "sha256:…"              // canonical content-address (see §3)
}
```

The profile is **declarative**: it records *what the pinned analysis is*, not how to run it. A
realizer (local fixture adapter now; live R-Engine later) reads it and executes accordingly.

### 2a. Local-first registry

For the local slice, profiles ship as a small in-package registry
(`src/polymer_claims/profiles/`), mirroring how `datasets/` ships `dose_response.csv`. A
`load_profile(profile_id, version) -> AnalysisProfile` resolver (impure, like `load_dataset`)
returns the frozen object. No network; pure + stub-testable.

**Two profiles ship in CES-0**, both EPICv2/hg38, both sesame `openSesame`/`QCDPB` normalization
(they *agree* there), differing on the choices that make "which profile" a real question:

| | `tet2_epicv2_hg38_manuscript@1` (ground truth) | `canonical_epicv2_hg38_v1@1` (registry) |
|---|---|---|
| Detection regime | retain-rate ≥ 0.80 (minfi `rowMeans`) | pOOBAH p ≤ 0.05 + 5% sample-fail |
| Sex-chrom probes | removed | removed (`filter_sex=TRUE`) |
| Design formula | pinned: `~ 0 + Sample_Group + Age + Sex`, `TET2_mut − WT` | not pinned by the profile (per-analysis) |
| SNP | sesame `M_SNPcommon_1pt` | minfi `dropLociWithSnps` SBE+CpG, MAF 0.01 |

The profiles produce *different* hashes, so a claim's `profile_hash` records exactly which
analytical regime licensed it. The manuscript profile is the first licensing target (§6); the
canonical profile is encoded alongside it to exercise the "named, not defaulted" property and to
seed the future registry-vs-manuscript comparison.

---

## 3. The canonical profile hash (closes Fork B)

`profile_hash = "sha256:" + SHA256(canonical_json(profile_without_hash))`, where
`canonical_json` is **sorted-keys, no-whitespace** — *exactly the canonicalization Polymer's
`SemanticRunID.param_signature` already uses* (`workflow_memory.py:62–117`), so Python and the
R side compute the same digest (hash parity, the existing SE-Contract discipline). Because the
profile includes the design formula and the Layer-C internals, **hashing the profile pins
everything the SemanticRunID misses today** — that is the gap-closure.

The extended materialization identity is then:
`semantic_run_id = SHA256(tool · param_signature · input_signature · profile_hash)` — profile
folded in. (Whether to fold into the existing SemanticRunID formula or carry `profile_hash`
alongside it is a Polymer-side implementation detail; EOS records both fields regardless.)

---

## 4. Binding: the profile is the apparatus (reuse `oracle_ref`)

- A claim's terminal `OperationNode` sets `oracle_ref = "{profile_id}@{version}"`.
- An `OracleDossier(oracle_id="{profile_id}@{version}", validation_tier=…,
  applicability_domain=…)` is supplied to `run_cycle(oracles=…)` (the existing
  `OracleRegistry` seam — never persisted, Corpus stays 4).
- **`ValidationTier` is set by substrate × validation status** per CES §5, not by the profile
  alone:

  | Substrate (`profile.substrate`) | Tier ceiling |
  |---|---|
  | Direct wet-lab / clinical anchor (sorted-cell EM-seq, the 48-sample cohort) | ANCHORED 0.85 |
  | Recomputable public data (GEO/TCGA methylation SE Contract) | BENCHMARKED 0.6 |
  | Computed/predicted reference | BENCHMARKED→INDIRECT |
  | Literature-reported | INDIRECT 0.4 |
  | Unvalidated / out-of-domain | UNVALIDATED 0.0 |

- The existing protocol `oracle_cap` (`protocol/src/polymer_protocol/oracle.py:45–81`) then
  caps the claim's empirical strength axes to the tier ceiling **with no new wiring** — a claim
  grounded on weak substrate renders visibly weak. `applicability_domain.subject_kinds` bounds
  the profile to the claim subjects it qualifies for (e.g. `genomic_region`, `cohort`); an
  out-of-domain match degrades to UNVALIDATED, exactly as today.

No new grammar slot; `oracle_ref` stops being vestigial and gains its first real use.

---

## 5. The grammar touch: extend `MaterializationContext` (the only core change)

Additive-optional, generic strings, present-only-when-relevant — mirroring the
`conclusion`/`licensing` additive idiom:

```python
class MaterializationContext(_Model):
    id: str
    api_version: str
    data_version: str
    note: str | None = None
    # CES additions (all optional; back-compat — existing call sites unchanged):
    semantic_run_id: str | None = None    # SHA256(tool·params·inputs·profile_hash) — reproducibility key
    profile_hash: str | None = None       # the realized AnalysisProfile content-address
    dimnames_hash: str | None = None       # SE-Contract canonical content-address (the drift key, CES §6)
```

These are the audit/drift keys EOS genuinely needs; `tool_id`/`engine_version` live inside the
`AnalysisProfile` (umbrella-side) and need no grammar field. Drift wiring (compare recorded
`profile_hash`+`dimnames_hash` against current in `drift_pass`) is **noted for CES-3**, not built
here — CES-0 ships only the representation.

---

## 6. The first claim (scalar reduction — Fork C)

A single hematopoiesis/TET2 methylation claim licenses over one bundled EPICv2 methylation SE
Contract fixture under `tet2_epicv2_hg38_manuscript@1`:

- **Claim:** "TET2-mutant vs WT methylation at region/locus R differs" — terminal reduced to a
  **scalar**: e.g. `Δβ at cgXXXXX ≥ θ`, or `n DMPs at FDR<0.05 ≥ k`. (No vector leaf;
  `QuantityVectorLeaf` deferred to a later phase.)
- **Air-gap = methodological independence (default):** two distinct impls compute the same
  scalar under the *same* pinned profile + dataset — e.g. `boris::dmp_limma_mvalue` (moderated
  t on M-values) vs `boris::probe_meandiff_beta` (direct β mean-difference). Each adapter
  `identity` encodes *(tool, engine)* so two legs on the same tool can never count as two
  identities (CES §4 — "no air-gap theater"). They must agree within tolerance for the L2
  `Satisfaction` to mint.
- **Tier cap:** the public fixture is `recomputable_public` → BENCHMARKED 0.6 ceiling; the
  licensed claim's empirical axes render capped at 0.6.

For CES-0 (design) this is the *target* that the CES-1/CES-2 plans build; CES-0 itself ships the
profile object, the hash, the `oracle_ref` binding, the `MaterializationContext` fields, and the
local profile registry — the scaffolding every later piece consumes.

---

## 7. What CES-0 delivers vs defers

**Delivers (this phase, as its own plan):**
- `AnalysisProfile` frozen object + canonical `profile_hash` (umbrella) + **both** real profiles
  (`tet2_epicv2_hg38_manuscript@1` and `canonical_epicv2_hg38_v1@1`) in the local registry, each
  with its own distinct hash.
- The three additive `MaterializationContext` fields (grammar).
- The `oracle_ref = profile_id@version` binding convention + a substrate→tier helper +
  an `OracleDossier` builder for a profile (umbrella/protocol seam, reusing `oracle_cap`).
- Tests: profile round-trip + hash determinism + hash-parity canonicalization; tier cap fires
  for a profile-bound claim through `run_cycle`; back-compat (no `oracle_ref` ⇒ byte-unchanged).

**Defers:**
- B1 DataHandle→SE-Contract DRS-shaped resolution (CES-1).
- Minimal B2 local realizer + the two independent reductions + the licensing claim (CES-2).
- B3 SemanticRunID threading + drift wiring (`profile_hash`/`dimnames_hash` → `drift_pass`) +
  the substrate-tier end-to-end (CES-3).
- Live R-Engine `BorisExecutionAdapter` via PlumberClient; `QuantityVectorLeaf`; the §7
  public/private promotion governance ruling (user-gated); DRS endpoint vs shape; TileDB-SOMA.

---

## 8. Invariants preserved

- **Grammar domain-agnostic:** zero new grammar types; only three generic additive-optional
  string fields. The `AnalysisProfile` never enters `grammar/`.
- **Pure / deterministic core; Corpus stays 4 collections;** `OracleRegistry` never persisted.
- **Air-gap intact:** independence is enforced by distinct *(tool, engine)* adapter identities;
  the profile pins the *shared* context so "two methods agreed" is a real check, not theater.
- **Content-address completeness:** the profile hash captures the design formula and Layer-C
  internals the SemanticRunID misses — a license now fully pins its analysis.
- **Back-compat:** every new field is optional; a claim with no `oracle_ref` and a bare
  `MaterializationContext` behaves exactly as today.

---

## 9. Open decisions for the user (none block CES-0)

1. **Substrate→tier table (§4):** confirm BENCHMARKED for recomputable-public and ANCHORED for
   the 48-sample sorted cohort, or adjust the ladder.
2. **Which first profile — RESOLVED:** encode **both** as distinct versioned profiles
   (`tet2_epicv2_hg38_manuscript@1` + `canonical_epicv2_hg38_v1@1`). They agree on normalization
   (sesame/QCDPB) and differ on the detection regime (retain-rate 0.80 vs pOOBAH 0.05), SNP
   method, and the manuscript's pinned design formula — so a claim names which regime licensed
   it (§2a). The manuscript profile is the first licensing target.
3. **SemanticRunID fold-in (§3):** extend the existing `SHA256(tool·params·inputs)` formula to
   include `profile_hash`, or carry `profile_hash` as a sibling field. (EOS records both either
   way; this is a Polymer-side choice for CES-3.)
