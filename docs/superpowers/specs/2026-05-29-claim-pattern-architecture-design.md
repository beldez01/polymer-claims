# Claim-Pattern Architecture — Design Spec

Date: 2026-05-29
Status: Draft for review
Scope: Conceptual redesign of the FormalClaim "domain" axis, plus a worked
cross-program proof. No code yet — this spec feeds `writing-plans`.

---

## 1. Problem

The FormalClaim IR (v1.2) treats `domain` as the structural discriminator: it
controls which subject kinds are legal (`_DOMAIN_LEGAL_SUBJECTS`) and is meant to
anchor the per-domain "profiles" described in
`docs/FormalClaim_Domain_Ontology_Note.md`. The thesis there is sound — *keep the
IR minimal, push biological complexity into versioned, ontology-backed domain
profiles* — but the implementation rests on an axis that does not carry the
structure we assigned to it.

### 1.1 What the corpus actually shows

Surveying all 47 corpus claims by `(domain, subject.kind, context-keys)`:

| Scientific program | domain | subject.kind | context |
|---|---|---|---|
| hla | genomic | cohort | {assembly} |
| dual_channel | genomic | cohort | {assembly} |
| te_surveillance | genomic | cohort | {assembly} |
| recombination_hotspots | genomic | cohort | {assembly} |

**Four different scientific programs collapse to one identical schema shape.** The
only deviations are escape hatches: claims that punted to `domain:"other"`
(subject `literal`, context `free_form`) or `domain:"multi_modal"` (subject
`composite`). The `domain` enum is near-constant `genomic`; it is not recording
modality, it is recording "did the cohort+assembly mold fit."

This proves three things:

1. **Scientific program is not a schema discriminator.** hla, dual_channel,
   te_surveillance, and recombination_hotspots are structurally
   indistinguishable. "Program" is a *namespace / provenance tag* — which thesis a
   claim serves — and nothing more.
2. **The `domain` enum does almost no work.** It is a lossy proxy that is mostly
   constant, with `other`/`multi_modal` acting as relief valves.
3. **The real semantic content escaped into `statistic.name` strings.** The
   biology lives in human-readable identifiers like
   `partial_spearman_r_curvature_vs_co_given_gc`,
   `auroc_curvature_1kb_h3k9me3`, `cohens_d_gc_old_vs_young`. This is the exact
   *prose-into-arbitrary-JSON* failure the ontology note warns against — merely
   relocated from `context` into statistic names. Every claim is "a cohort, with
   some named numbers," and the numbers' meaning is unparsed text.

### 1.2 The missing axis

The thing that actually determines a claim's shape is neither its biology nor its
modality. It is the **relationship being asserted** — the *claim pattern*. A
"partial Spearman of property X vs outcome Y controlling for Z" claim has the
identical skeleton whether it is HLA expression or recombination hotspots. The
corpus confirms this: classifying all 47 claims by statistic vocabulary yields a
small, finite set of patterns:

| Pattern | Corpus n |
|---|---|
| `partial_correlation_with_control` | 11 |
| `count_or_threshold` | 10 |
| `enrichment_vs_null` | 6 |
| `group_contrast_effect_size` | 5 |
| `model_delta_over_baseline` | 5 |
| `simple_correlation` | 5 |
| `ranking_by_property` | 3 |
| (meta / composite escape hatch) | 2 |

Seven patterns cover 45 of 47 claims. The unit of structural reuse was never
`methylation.v0.1`; it is the **claim pattern**.

---

## 2. The reframe

`domain` is conflating three orthogonal axes. We separate them, and designate one
— the previously-missing one — as the discriminator.

| Axis | Examples | Role |
|---|---|---|
| **Claim pattern** *(was missing)* | partial_correlation_with_control, enrichment_vs_null | **Discriminator.** Determines required subject roles, statistic family, inference skeleton, conclusion semantics. Modality- and program-agnostic. |
| **Subject biology** | CpG probe, HLA allele, genomic region, GTEx TPM | **Slot fillers.** Each subject carries its own ontology / identifier binding. |
| **Program / lineage** | hla, dual_channel, te_surveillance | **Flat tag** (`provenance.program`). Searchable lineage. Zero structural force. |

---

## 3. Architecture — three layers

```
┌─ CLAIM PATTERN  (discriminator — finite catalog, ~8) ─────────────────┐
│  Modality- & program-agnostic relationship template.                   │
│  Defines: typed subject ROLES · required statistic FAMILY ·           │
│           inference-rule SKELETON · conclusion semantics.             │
└────────────────────────────────────────────────────────────────────────┘
            ▲ slots constrained by
┌─ DOMAIN PROFILE  (slot-filler legality — per biology/assay) ──────────┐
│  For each pattern role: which identifier systems / ontologies / units  │
│  are legal, plus required context dimensions and default thresholds.   │
└────────────────────────────────────────────────────────────────────────┘
            ▲ tagged (non-structural) by
┌─ PROGRAM TAG  (flat namespace — provenance.program) ──────────────────┐
│  hla · dual_channel · te_surveillance · recombination_hotspots …      │
└────────────────────────────────────────────────────────────────────────┘
```

Patterns do **not** replace the existing IR. The IR already carries
`premises / operations / statistics / inference / conclusion`. A pattern is a
**named, validatable contract over those fields** plus a role-typing of
`subject`. This is additive, not a rewrite.

### 3.1 The ClaimPattern object

A pattern is a small declarative document (one per catalog entry, versioned):

```yaml
id: partial_correlation_with_control
version: v1
title: Partial correlation of a predictor with an outcome, controlling for ≥1 confounder
roles:                              # typed subject slots
  - name: predictor   cardinality: "1"
  - name: outcome     cardinality: "1"
  - name: confounder  cardinality: "1+"
statistic_family:                   # required statistics, by abstract role
  - role: effect         measure: partial_correlation   required: true
  - role: significance   measure: p_value               required: true
inference_skeleton:                 # parametric over claim/profile thresholds
  all:
    - { lhs: "effect", transform: abs, op: ">=", rhs: "$TAU" }
    - { lhs: "significance",            op: "<=", rhs: "$ALPHA" }
conclusion_semantics:
  direction: sign(effect)           # the qualitative claim
  comparable_key:                   # what makes two instances comparable
    - predictor.ontology_class
    - outcome.ontology_class
    - confounder.ontology_class
```

### 3.2 What a claim looks like under the model

A claim *declares* its pattern and *binds* its roles and statistics to it. The
existing `operations` / `statistics` machinery is unchanged; the pattern adds a
typed overlay:

```yaml
pattern:  { id: partial_correlation_with_control, version: v1 }
profile:  { id: genomic_biophysics, version: v0.1 }
provenance: { program: te_surveillance }
roles:
  predictor:  { subject: <LTR fraction subject>,   ontology_class: SO:LTR_retrotransposon }
  outcome:    { subject: <GTEx median TPM subject>, ontology_class: EFO:expression_level }
  confounder: [ { subject: <GC content subject>,   ontology_class: SO:GC_content } ]
bindings:
  effect:        { stat_id: s_partial_rho }     # -0.18
  significance:  { stat_id: s_partial_p }        # 1e-50
thresholds:
  TAU: 0.1
  ALPHA: 0.001
```

---

## 4. Versioning model

Patterns make the previously-muddy version story clean. Each version axis has
exactly one job:

| Field | Freezes |
|---|---|
| `schema_version` | The IR grammar (v1.1, v1.2, → v1.3). |
| `pattern.version` | The relationship template: roles, statistic family, inference skeleton. |
| `profile.version` | The ontology / identifier-system snapshot and legal slot-fillers + required context dimensions. |
| `data_version` / `api_version` | The underlying data and serving API (unchanged). |

When a profile revises its required context dimensions or ontology snapshot, old
claims are **frozen-as-interpreted** against the `profile.version` they declared —
never silently reinterpreted. A pattern revision (e.g. `v1 → v2` adds a required
role) likewise leaves `v1` claims valid under `v1`. This resolves the
"profile_version semantics" tension: pattern_version and profile_version freeze
*different things*, and neither retroactively invalidates older claims.

---

## 5. Where semantic discipline lives

The ontology note's deepest claim is that agents should *fill typed slots, not
translate prose to JSON*. Patterns move most of this from "unenforceable" to
"enforceable," and cleanly isolate the residue:

- **Structural conformance — enforceable by a validator.** Declaring
  `partial_correlation_with_control` *requires* a `confounder` role and a
  `partial_correlation` effect statistic. A claim that declares the pattern but
  omits the confounder, or supplies a plain (non-partial) correlation, is
  rejected mechanically. This is a schema property once the pattern contract
  exists.
- **Slot-filler legality — enforceable by the profile.** The profile rejects an
  ontology class that is illegal for a given role (e.g. a disease term in the
  `confounder` slot of a biophysics profile).
- **Semantic correctness — authoring-loop only.** Whether the agent mapped the
  *right* confounder (GC vs. replication timing) is not a schema property and
  never will be. This is the irreducible residue, handled in the claim-authoring
  skill/prompt and human review — and it is now small and well-isolated, not
  smeared across free-text everywhere.

---

## 6. Mapping onto the existing IR (changes)

Additive, targeted to `schema.py` and the corpus schema:

1. **New IR fields** (optional in v1.2, required when `schema_version == "v1.3"`):
   - `pattern: { id, version }`
   - `roles: { <role_name>: RoleBinding | [RoleBinding] }` where `RoleBinding`
     wraps a `SubjectRef` + `ontology_class`.
   - `thresholds: dict[str, float]` — supplies `$TAU`, `$ALPHA`, etc. to the
     pattern's inference skeleton.
2. **`provenance.program`** — promote the corpus folder name to an explicit,
   searchable tag (it is already implicit in the file path).
3. **`profile: { id, version }`** — replaces the structural use of `domain`.
   `domain` is retained as a deprecated coarse modality hint for back-compat, no
   longer a discriminator.
4. **Pattern catalog** — a new `corpus/patterns/<id>.<version>.yml` tree (the ~8
   patterns above), each a declarative contract.
5. **Validator** — extend the corpus evaluator to check claim ⊨ pattern
   (structural conformance) and claim ⊨ profile (slot legality). The existing
   three-valued `evaluate()` of the inference rule is unchanged; the pattern
   skeleton simply *generates* the inference expression from `thresholds`,
   replacing hand-written per-claim inference where a pattern applies.

`_DOMAIN_LEGAL_SUBJECTS` is superseded by per-pattern roles × per-profile legal
ontology classes.

---

## 7. Worked proof — two cross-program claims become comparable

Two real corpus claims, today structurally invisible to each other, re-expressed
under one pattern.

### 7.1 As they are today

| | `recomb_a2_..._curvature` (Exp 17) | `ltr_fraction_..._gc_independent` (Exp 15) |
|---|---|---|
| program | recombination_hotspots | te_surveillance |
| domain | genomic | genomic |
| subject.kind | cohort | cohort |
| where the meaning lives | `statistic.name = "partial_spearman_r_curvature_vs_co_given_gc"` | `statistic.name = "partial_spearman_ltr_fraction_vs_median_tpm_given_gc"` |

A machine cannot tell these are the same kind of claim. Comparison is impossible
without parsing English statistic names.

### 7.2 Re-expressed under `partial_correlation_with_control`

**Claim A — recombination (CO arm):**
```yaml
pattern:  { id: partial_correlation_with_control, version: v1 }
profile:  { id: genomic_biophysics, version: v0.1 }
provenance: { program: recombination_hotspots, exp_number: 17 }
roles:
  predictor:  { subject: curvature@1Mb,        ontology_class: polymer:biophysics/curvature }
  outcome:    { subject: crossover_rate@1Mb,    ontology_class: SO:crossover }
  confounder: [ { subject: gc_content@1Mb,      ontology_class: SO:GC_content } ]
bindings:
  effect:       { stat_id: s_partial_r_curv_co }   # -0.238
  significance: { stat_id: s_steiger_z_p }          # 0.003  (see note)
thresholds: { TAU: 0.1, ALPHA: 0.01 }
# NOTE: this claim does not record the CO partial correlation's *own* p-value;
# its native significance statistic is the Steiger test of the CO-vs-NCO
# difference. Binding it here is a deliberate approximation that exposes the real
# structure: this claim is natively a `difference_of_correlations` composite
# (two partial_correlation_with_control arms + a difference test), not a pure
# single-arm instance. See §7.3 "Composition is visible" and §9 open question 4.
```

**Claim B — TE surveillance:**
```yaml
pattern:  { id: partial_correlation_with_control, version: v1 }
profile:  { id: genomic_biophysics, version: v0.1 }
provenance: { program: te_surveillance, exp_number: 15 }
roles:
  predictor:  { subject: ltr_fraction@1kb,      ontology_class: SO:LTR_retrotransposon }
  outcome:    { subject: gtex_median_tpm@1kb,    ontology_class: EFO:expression_level }
  confounder: [ { subject: gc_content@1kb,       ontology_class: SO:GC_content } ]
bindings:
  effect:       { stat_id: s_partial_rho }   # -0.18
  significance: { stat_id: s_partial_p }      # 1e-50
thresholds: { TAU: 0.1, ALPHA: 0.001 }
```

### 7.3 What the proof buys

- **Same `comparable_key` template** → both are `(predictor, outcome | confounder=GC_content)` partial
  correlations. A query "all GC-controlled negative partial correlations,
  |effect| > 0.1" now returns **both**, across programs, with no string parsing.
- **Directly rankable effect sizes:** curvature→crossover coupling (|ρ|=0.238) is
  stronger than LTR→expression coupling (|ρ|=0.18); both are GC-independent
  negative associations. This sentence is now *computable*, not editorial.
- **Inference is generated, not hand-written:** both inference blocks reduce to
  the pattern skeleton `|effect| ≥ TAU ∧ significance ≤ ALPHA`. The bespoke
  per-claim inference JSON shrinks to two thresholds.
- **Composition is visible:** the *full* recomb claim adds a second arm (NCO) and
  a Steiger difference test — i.e. a `difference_of_correlations` pattern composed
  on top of two `partial_correlation_with_control` instances. The model names
  this composition explicitly instead of hiding it in prose. (Difference-of-
  correlations is a candidate 8th catalog pattern.)

---

## 8. Non-goals (YAGNI)

- **Not** solving all of biology. First profile target stays `genomic_biophysics`
  (covers the existing corpus) + the note's `methylation.v0.1` as the second.
- **Not** auto-migrating all 47 claims in this work. The proof re-expresses two;
  bulk migration is a later, separate plan.
- **Not** building the cross-domain ontology join engine here. Subjects carry
  `ontology_class` strings; a real ontology-resolution service is downstream.
- **Not** removing the existing `evaluate()` semantics. Patterns *generate*
  inference expressions that feed the same evaluator.

---

## 9. Open questions (to resolve during planning, not blocking)

1. **Cross-modal roles.** Claim B's predictor is genomic, its outcome is
   transcriptomic. Does a single `profile` legitimately span modalities, or
   should legality be declared per-role (each role names its own ontology class
   and the profile just lists allowed classes per role)? Leaning per-role; the
   profile is then a thin legality table, not a modality bucket.
2. **Threshold provenance.** Do `TAU`/`ALPHA` live on the claim (as shown), on the
   profile (as defaults), or both with claim-overrides? Leaning profile-default +
   claim-override.
3. **Pattern catalog governance.** Patterns are higher-stakes than claims (a bad
   pattern corrupts every claim using it). Tier-3 review only? Separate
   `corpus/patterns/` PR track.
4. **8th pattern.** Promote `difference_of_correlations` (sign-flip claims) to the
   catalog now, or treat it as composition of two `partial_correlation_with_control`
   instances? Affects how many recomb claims need it.

---

## 10. First milestones (detailed plan deferred to writing-plans)

1. Author the ClaimPattern document format + the `partial_correlation_with_control`
   pattern as the reference example.
2. Add `pattern` / `roles` / `thresholds` / `profile` fields to the IR (v1.3,
   additive) + `provenance.program`.
3. Re-express the two proof claims as conformant v1.3 fixtures; show they pass a
   `claim ⊨ pattern` structural check and produce the same `evaluate()` outcome as
   their v1.2 originals.
4. Write the `claim ⊨ pattern` + `claim ⊨ profile` validators into the corpus
   evaluator.
5. Draft `genomic_biophysics.v0.1` profile (the legality table the proof claims
   need).
