# Cohort Foundry — the data-independence half of verification

**Date:** 2026-06-29
**Status:** Horizon / conceptual outline. **Not scheduled for implementation.** Companion to
[`2026-06-29-claim-type-menu-design.md`](./2026-06-29-claim-type-menu-design.md): the menu defines
the *claim types* and their *adapter pairs*; this doc defines how the system assembles the
*validation cohorts* that those claims need, and the provenance trail that assembly produces.

**Concrete ancestor:** [`2026-06-18-replicated-second-cohort-design.md`](../archive/specs/2026-06-18-replicated-second-cohort-design.md)
and its [implementation plan](../archive/plans/2026-06-18-replicated-second-cohort.md) are the hand-wired
precursor. They illustrate one instance; this document is about the reusable platform capability,
not that cohort's implementation details.

---

## Why this document exists

The two-implementation gate is the platform's **REPRODUCED strength tier** — one rung above the
attestation-log floor (the actual foundation of belief; see `foundations/compute-boundary.md`), not
the whole of trust — and it is precise about what it tests: two independently-owned adapters compute a claim's value on the **same data
leaves**, and the claim licenses only if they agree. The independence lives in the *computation*,
not the data — the data is held fixed on purpose.

That gate tests **reproducibility, not validity.** It proves the number was not a coding artifact
or a self-confirming implementation. It cannot, by construction, catch:

- a finding that is real in *this* cohort but is a batch effect, an ascertainment artifact, or a
  population-specific quirk;
- a prior that is locally coherent but globally wrong — both adapters faithfully compute the same
  biased estimate;
- anything about generalization — two faithful implementations of an overfit model agree
  perfectly.

The strongest ordinary instrument for testing those is an **external validation cohort**, because
it varies the one thing the gate deliberately holds fixed: the data. It is not a truth oracle:
negative controls, sensitivity analysis, benchmark truth, prospective experiments, and
methodologically different measurements can expose failures that a second observational cohort
cannot. The machinery to *consume* a second cohort already exists (see "How it plugs in" below).
What is missing is the machinery to *produce* one. The **Cohort Foundry** is that producer.

---

## The load-bearing insight: two independence axes

The menu's independence tiers (T1/T2/T3) are entirely about **adapter independence** — different
code, different team, different runtime, *same data*. The menu flags its own blind spot in its
open questions: organizational independence is not the same as epistemic independence; two
"independent" tools can share priors and fail together.

The Foundry adds the **orthogonal second axis: data independence.** Does the finding survive in a
cohort assembled independently of the one that produced it? The two axes do not substitute. The
honest verification state is a 2×2, not a single ladder:

| | One dataset | Independent validation dataset |
|---|---|---|
| **One adapter lineage** | single-pipeline result | externally repeated, method-fragile |
| **Independent adapter witnesses** | **REPRODUCED**: implementation-robust on one dataset | **REPLICATED**: implementation-robust across datasets |

A menu row is not truly "validatable end-to-end" until it has **both** a pair of independent
adapters **and** a Foundry-assembled validation cohort. The existing `REPLICATED` tier already
*wants* both (it requires distinct `dimnames_hash` and certified-independent error before it
multiplies e-values); it simply has no way to obtain the second cohort on its own today.

Here “data-independent” is shorthand for a dossier, not a boolean inferred from a different hash.
It has at least five separable dimensions: non-overlapping subjects; independent collection sites
and operators; independent assay/processing pipelines; outcome-blind cohort discovery and
assembly; and sufficiently distinct recruitment/selection mechanisms. A cohort can be independent
on some dimensions and coupled on others.

---

## The three layers

### Layer 1 — Repository & resource knowledge (the agent-harness context)

The Foundry only works if the agent is genuinely expert at where things live and how each source
behaves. This is curated reference context — a knowledge pack the harness loads — not
inference-on-the-fly. It is **two catalogs**:

**1a. Data-source catalog** — feeds cohort assembly (the data-independence axis). Per source: its
access pattern (API vs bulk vs gated), its metadata conventions and quirks, and how to map its
sample annotations onto the claim's subject ontology and roles. The canonical quirk to encode is
the one already blocking us: *GEO carries no machine-readable per-sample IDH status*, so any
methylation claim that conditions on IDH must recover that covariate from free text or
supplementary tables. Initial members: GEO, GDC/TCGA, cBioPortal, ArrayExpress/BioStudies,
recount3, GTEx, DepMap/GDSC. (See "Deferred: data-resource census.")

**1b. Compute/model-API catalog (oracle dossiers)** — feeds the *adapter* pairs, and carries the
*strongest* independence stories. This is the "beyond Bioconductor + TCGA" track: the emerging
ecosystem of external computational-biology APIs from distinct organizations — BioNeMo (NVIDIA),
AlphaFold/AlphaMissense (DeepMind), ESM (Meta), and the steady stream of new providers. Each entry
is an oracle dossier: owner, validation tier, access, and the patterns it can serve. Because these
are cross-org T1 by construction, they are where adapter-independence is most defensible, and the
catalog is what lets the system make the most of new tools as they ship rather than staying pinned
to the R/Bioconductor cluster.

The two catalogs map to the two axes: the data-source catalog strengthens *data* independence; the
oracle catalog strengthens *adapter* independence.

### Layer 2 — Assembly & harmonization

Given an input claim, produce a contract-compliant validation cohort (an SE/MAE object plus a
`DataHandle`) that the existing replication machinery can bind to. Four steps:

1. **Discovery** — query the data-source catalog for candidate datasets matching the claim's
   subject (disease → MONDO, tissue → UBERON, assay → platform), using ontology expansion rather
   than string matching. Discovery emits a candidate ledger, including every dataset considered
   and every machine-checkable exclusion reason; it does not inspect claim outcomes.
2. **Harmonization** — the load-bearing, dangerous step. Recover the per-sample covariates the
   claim's `roles` demand (the IDH-status problem, generalized): extract them from messy metadata,
   map them to ontology terms, align platforms (e.g. HM450 ↔ EPIC probe overlap), and decide
   sample eligibility. This is where the ontology context earns its keep.
3. **Qualification** — test the candidate against a predeclared transport contract: estimand,
   population, exposure and comparator definitions, outcome/feature semantics, allowable
   measurement transformations, minimum information, subject-overlap checks, and known
   shared-cause factors. “Same ontology term” is necessary but not sufficient.
4. **Assembly** — emit the contract object + `DataHandle`, the assembly dossier, and either
   `eligible`, `provisional`, or `ineligible`; only then hand an eligible cohort to
   `replication.py`.

Harmonization is what is actually blocking the one cohort we have (GSE86409). It is also where the
self-confirmation hazard lives — see below.

### Layer 3 — Provenance & audit

Assembling a cohort *is* a chain of consequential, fallible decisions: which dataset, which
samples, which ontology mappings, which harmonization calls, which Bioconductor package at which
version. A complete, replayable record of that chain is not a side feature — it is the Foundry's
**primary standalone output**, and it is exactly the ROI doc's **Tier 3 "Defensibility"** rung:
*prove your survivors on demand, full provenance, instantly.* An auditor (regulator, acquirer,
reviewer) must be able to confirm the pipeline ran the way it was intended to — that the cohort was
assembled by the stated rules and nothing was curated to taste. The audit record is a product even
when the science underneath it is mundane.

---

## The self-confirmation hazard (and the assembler air-gap)

The more the agent does to assemble a cohort, the more it can re-introduce exactly the
self-confirmation the air-gap was built to prevent. If the same intelligence that proposed "IDH-mut
is hypermethylated" also decides which free-text samples count as "IDH-mut," it can unconsciously
curate a cohort that confirms the claim. The same risk occurs if the Foundry tries several cohorts
and reports only the one that replicates. A *hallucinated* covariate label is worse than no
validation — it would *mint* false confidence, the system's cardinal sin.

Structural defenses, reusing patterns the system already trusts:

1. **Air-gap the assembler from the proposer.** Cohort assembly must be owned by an actor distinct
   from the one that generated the claim. More importantly, the assembler receives a blinded
   transport contract, not the expected direction, effect estimate, cohort-A result, or interim
   cohort-B result. Separation is recorded as provenance; information exposure is recorded too.
   Different actors with the same outcome knowledge are not an air-gap.
2. **Apply the two-implementation gate to harmonization itself.** Each per-sample covariate label
   (this sample is IDH-mutant) is fallible evidence with its own provenance. Two independent
   extractors can be required to agree, but agreement is not truth: both can parse the same
   ambiguous field incorrectly. Their lineage and source evidence must be recorded, and a
   claim-independent gold source (genotype table, authoritative supplement, or audited manual
   adjudication) is preferred when available.
3. **Precommit the search and freeze the candidate ledger.** Eligibility rules, source priority,
   stopping rule, and the treatment of multiple qualifying cohorts are fixed before outcome
   evaluation. Every attempted cohort and failure is retained. Testing cohorts until one passes is
   selection on the answer and invalidates the advertised evidence unless the sequential/multiple
   testing procedure explicitly accounts for it.
4. **Abstain rather than silently drop.** Extractors emit `label + confidence + evidence span` or
   `unresolved`. Dropping disagreements can induce informative missingness and change the cohort
   composition. Exclusion is allowed only under predeclared, outcome-blind rules; otherwise the
   cohort is provisional or ineligible.

A Foundry cohort therefore carries its own independence quality, and should not be promoted to full
`REPLICATED` strength until its harmonization clears these gates. An un-gated, machine-assembled
cohort can still contribute — as provisional external evidence with a capped contribution — but it
must read differently from a hand-curated, dual-extracted one.

---

## How it plugs into the existing machinery (no overhaul)

The Foundry adds a producer in front of machinery that already exists; it does not rewrite the
verification core.

- **`IndependenceTier.REPLICATED`** (`grammar/.../licensing.py`) is the slot the Foundry fills. It
  already requires ≥2 datasets with distinct `dimnames_hash`. That proves different contract
  identities, not different subjects, collection processes, or errors; Foundry qualification must
  supply those stronger facts.
- **`replication.py`** already re-binds a claim to a second cohort's `DataHandle`, re-runs both
  legs, and multiplies e-values (`e1·e2`) only when `cohorts_error_independent`. The Foundry
  produces the `DataHandle`; replication consumes it unchanged. However, today's implementation
  treats missing shared-cause factors as assessability unknown and still permits multiplication.
  A Foundry-issued full-strength cohort must be fail-closed: unknown independence cannot mean
  independent.
- **`shared_cause` / `SeverityProvenance`** already encode prior-soundness as operator-asserted
  factors plus a Jaccard threshold. The Foundry feeds this honestly, but these are hooks rather
  than a proof. Free-form factor sets and Jaccard overlap cannot establish statistical
  independence; they need a controlled factor vocabulary, lineage policy, and conservative
  unknown state.
- **`OntologyTerm`** (MONDO/EFO/UBERON/CL/GO/… with propagation modes) already exists as
  subject identity. The Foundry adds the *reasoning* layer (expansion, traversal, sample-to-term
  mapping) on top of the identity layer that is already typed.

The work is primarily in the producer and its two catalogs, not in the consumer. Full-strength
automatic promotion may still require a narrow consumer hardening change so that a signed
qualification result—not merely distinct hashes and absent factors—is required before e-value
multiplication.

---

## The Foundry output: an assembly and qualification dossier

The `DataHandle` is the computational output. The load-bearing epistemic output is a
content-addressed dossier containing:

- the claim-blinded transport contract and its hash;
- source accession, retrieval time, license/access constraints, raw-artifact hashes, and immutable
  snapshots or resolvable version identifiers;
- the complete candidate and attempt ledger, including exclusions and failed assemblies;
- subject identity/linkage evidence sufficient to detect overlap without exposing identifiers;
- sample-level source evidence, extracted labels, confidence, disagreements, adjudications, and
  exclusions;
- ontology versions, mappings, expansion paths, and every lossy transformation;
- assay, preprocessing, normalization, feature-intersection, missingness, and QC decisions;
- shared-cause and independence dimensions, with `known-independent`, `known-shared`, or `unknown`
  per dimension and supporting evidence;
- code/container/package/model versions, prompts or extraction rules where applicable, random
  seeds, execution logs, and hashes of every emitted artifact;
- a deterministic replay recipe and a qualification verdict with machine-readable reasons.

Provenance proves what was done; it does not prove that the choices were scientifically valid.
Replayability, policy conformance, and scientific adequacy are three separate audit claims.
Tamper-evidence is likewise separate from completeness: the deferred
[`2026-06-26-networked-rekor-backend-design.md`](./2026-06-26-networked-rekor-backend-design.md)
could later make a dossier non-repudiable, but cannot make omitted decisions appear.

---

## Statistical and epistemic contract

A Foundry run must preserve the inferential object, not merely produce a compatible matrix:

1. **Freeze the claim and estimand.** Direction, threshold, feature/region, adjustment set,
   subgroup, contrast, and analysis profile are fixed before cohort-B outcomes are visible.
2. **Declare transportability.** State which population and measurement differences are tolerated
   and why the same scientific quantity is still being estimated. If the construct changes
   (IDH1-only versus IDH1/2, elderly AML versus all adult AML), label it a related conceptual
   replication rather than silently treating it as exact.
3. **Preserve valid evidence accounting.** Cohort search, repeated extraction attempts, multiple
   candidate cohorts, and post-hoc harmonization choices are part of the selection process.
   Combining e-values is justified only under the required conditional independence or under a
   dependence-robust rule. “Different consortium” and distinct `dimnames_hash` are not enough.
4. **Report failures and heterogeneity.** A non-replication, an ineligible cohort, and an
   inconclusive/underpowered test are distinct outcomes. Effect direction and magnitude,
   uncertainty, heterogeneity, missingness, and qualification failures must survive alongside the
   license state.
5. **Never use observed power as eligibility.** Minimum sample/information criteria may be
   predeclared from design assumptions. Rejecting a cohort because its realized `e2` is too small
   is outcome-based selection.

These rules apply uniformly to every Foundry-produced cohort. The hand-wired GSE86409 work is a
useful test fixture for the interfaces, but it must not determine the architecture or become an
implicit special case.

---

## Platform boundary and contracts

The Foundry should be a policy-governed compiler from a **validation request** to a **qualified
cohort package**. Keeping that boundary narrow is what makes the concept feasible.

### Input: `ValidationRequest`

The request is claim-independent enough to blind assembly while still specifying what must be
transported:

- subject/population ontology terms and allowed expansion policy;
- assay and measurement semantics;
- exposure, comparator, outcome, covariate, and sample-role definitions;
- frozen estimand and analysis-profile reference;
- admissible population/platform differences;
- minimum design information fixed without looking at validation outcomes;
- source/access constraints and required independence dimensions.

It deliberately omits the expected direction, cohort-A effect size, licensing threshold progress,
and any validation outcome.

### Output: `QualifiedCohortPackage`

The package is atomic and content-addressed:

- contract object plus `DataHandle`;
- `AssemblyDossier`;
- `QualificationReport`;
- candidate/attempt ledger;
- replay recipe;
- policy and catalog versions under which the verdict was produced.

The verdict is one of:

- **eligible** — all mandatory qualification dimensions are positively established;
- **provisional** — usable for exploration or capped evidence, with named unknowns;
- **ineligible** — violates a mandatory rule;
- **unresolvable** — required evidence is absent or inaccessible.

Only `eligible` packages can request automatic full-strength replication. `Provisional` is not a
soft synonym for eligible.

### Stable internal seams

Source-specific complexity stays behind four interfaces:

1. **Source connector** — discovers and snapshots datasets; never interprets scientific meaning.
2. **Metadata extractor** — emits candidate typed values with evidence spans and abstentions.
3. **Harmonizer** — applies versioned, declarative mappings and transformations.
4. **Qualifier** — evaluates a package against a versioned policy without seeing claim outcomes.

This separation allows connectors and extractors to improve without changing licensing semantics,
and allows policy to tighten without rewriting ingestion.

---

## Qualification model

Qualification should be a vector with evidence, not a single confidence score:

| Dimension | Question | Full-strength requirement |
|---|---|---|
| Subject identity | Are cohort-A and cohort-B people/specimens distinct? | positively established non-overlap |
| Dataset lineage | Is B derived from, merged with, or a republication of A? | no shared subject/data ancestry |
| Collection | Could site, operator, recruitment, or calendar effects be shared? | known factors recorded; mandatory limits pass |
| Measurement | Does B measure the same construct with an admissible process? | transport rule passes |
| Label validity | Are roles/covariates supported by source evidence? | required fields meet source and uncertainty policy |
| Outcome blindness | Was assembly insulated from the answer? | exposure log shows no forbidden information |
| Search integrity | Is every candidate and attempt accounted for? | frozen ledger and stopping rule |
| Statistical combination | Is the proposed combination rule valid for known dependence? | explicit combiner authorization |
| Replayability | Can the exact package be reconstructed or independently verified? | artifacts pinned and recipe complete |
| Permitted use | May the data be processed, retained, and reported this way? | access/use policy passes |

Unknown is a real state. A weighted average must not let strong replayability compensate for
unknown subject overlap or invalid statistical combination. Policies define mandatory dimensions,
caps, and admissible exceptions per claim family.

---

## Catalog governance

The catalogs are executable governance assets, not prompt context alone. Every entry needs:

- a stable identifier, schema version, owner, reviewer, and effective date;
- supporting evidence and machine-checkable assertions;
- freshness/expiry policy and last successful conformance run;
- known failure modes, coverage boundaries, and permitted claim families;
- change history, deprecation path, and impact analysis for packages built under older versions.

Catalog updates must not silently rewrite old dossiers. A historical package remains interpretable
against the exact catalog and policy versions that produced it; requalification under a newer
policy creates a new verdict.

The agent may propose catalog entries and mappings. Promotion into the trusted catalog requires
review or benchmark evidence appropriate to the risk. The platform must never convert model
fluency about a repository into trusted source knowledge without that promotion step.

---

## Operating model and failure semantics

The Foundry is a workflow engine with durable state, not a single autonomous agent call:

```
request frozen
  → candidates discovered and ledgered
  → source artifacts pinned
  → metadata extracted with evidence
  → harmonization applied
  → qualification evaluated
  → package sealed
  → outcomes unblinded and replication invoked
```

Each transition is idempotent, resumable, and emits an event. Failures remain first-class:
`source_unavailable`, `access_denied`, `metadata_insufficient`, `construct_mismatch`,
`subject_overlap_unknown`, `policy_failed`, and `replay_failed` must not collapse into “no cohort.”
This is essential both for audit and for improving the source catalog.

Human review is an explicit lane, not an embarrassment or an invisible fallback. The system routes
only the ambiguous evidence required for a decision, records the adjudicator and rationale, and
keeps the reviewer blinded to outcomes. High-risk mappings can require review by policy; routine,
benchmark-certified mappings can remain automatic.

---

## Feasible build sequence

The general architecture should be built through constrained vertical slices rather than a
universal biomedical-data agent.

### Slice 0 — dossier-only shadow mode

Wrap one existing hand-built cohort assembly. Produce the request, candidate ledger, extraction
evidence, qualification vector, and replay record without changing licensing. This validates the
schemas and reveals which provenance facts are actually recoverable.

### Slice 1 — one source, one assay, one claim family

Support a single connector and tightly bounded harmonization path. Require human approval for
ambiguous labels. Emit `eligible/provisional/ineligible`, but keep full-strength promotion behind
an explicit operator gate.

### Slice 2 — policy-enforced automatic promotion

Add subject-lineage checks, fail-closed shared-cause qualification, frozen search ledgers, and a
consumer check for a valid `QualificationReport`. Only here should a Foundry package
automatically unlock `REPLICATED`.

### Slice 3 — multi-source expansion

Add connectors and mappings one at a time through conformance suites. Introduce a dependence-aware
cohort graph and a declared policy for combining multiple validation cohorts.

### Slice 4 — scaled governance

Add catalog review workflows, freshness monitoring, benchmark suites, controlled-access execution,
and optional external transparency/tamper-evidence.

The feasibility criterion for each slice is not datasets ingested. It is the fraction of requests
that end in a correctly classified, replayable verdict—including honest `ineligible` and
`unresolvable` outcomes—without outcome leakage.

---

## Conformance and acceptance

Before the Foundry can affect licensing, it needs adversarial conformance fixtures:

- duplicate subjects under changed identifiers and derived/repackaged datasets;
- missing, contradictory, and negated covariate text;
- ontology near-matches that change the population or construct;
- platform mappings with silent unit, genome-build, or feature-identity drift;
- informative missingness and extractor-disagreement exclusions;
- multiple candidate cohorts where only a later candidate confirms;
- catalog or source drift between assembly and replay;
- forbidden outcome information presented to the assembler;
- inaccessible controlled data and licenses that prohibit the intended use.

Acceptance is fail-closed behavior, complete attempt accounting, deterministic replay where source
terms permit it, and invariant licensing decisions under irrelevant metadata perturbations. A
successful happy-path ingestion alone is not evidence that the Foundry is safe.

---

## Deferred: data-resource census

Before committing the Foundry's data-source catalog (Layer 1a), do a comprehensive scour of the
available resources — cBioPortal, and the broader landscape beyond the GEO/TCGA core — to know
concretely where the Foundry will source from, each source's access pattern, metadata quality, and
covariate-recoverability. **Deliberately deferred; not part of this doc.** It becomes its own
worklist when the Foundry leaves the horizon.

---

## Open questions / caveats

- **Promotion policy for assembled cohorts.** What exactly gates an un-gated machine-assembled
  cohort from contributing at full `REPLICATED` strength? A capped provisional contribution vs the
  dual-extractor gate above needs a concrete rule.
- **Exact vs conceptual replication.** Define machine-readable compatibility levels for population,
  exposure/comparator, measurement, adjustment, and estimand changes; do not collapse all of them
  into “external.”
- **Cohort search multiplicity.** Specify a stopping rule and an evidence-combination policy for
  zero, one, or many qualifying candidates, including dependence among cohorts that reuse subjects
  or source repositories.
- **Identity and leakage.** `dimnames_hash` cannot detect renamed duplicate subjects, overlapping
  aliquots, derived datasets, or train/test leakage. Privacy-preserving linkage and dataset-lineage
  checks are required.
- **Harmonization confidence as a first-class quantity.** Covariate extraction is uncertain; that
  uncertainty should propagate into strength, not vanish once a label is assigned.
- **Platform harmonization limits.** HM450 ↔ EPIC probe overlap, RNA-seq pipeline differences
  across recount3 vs GDC — where harmonization stops being defensible needs a stated boundary.
- **Ontology expansion limits.** Ontologies improve recall but can change the target population or
  construct. Expansion paths need reviewable distance/relationship policies, not unrestricted
  traversal.
- **Missingness and exclusion bias.** Qualification must test whether unresolved labels, absent
  features, and QC exclusions differ by relevant covariates; dual-extractor disagreement is not a
  neutral reason to discard a sample.
- **Licensing, consent, and controlled access.** A reproducible cohort may still be unlawful or
  impossible to redistribute. Dossiers need access-policy and permitted-use provenance without
  leaking protected metadata.
- **Oracle-catalog freshness.** The emerging-API ecosystem moves fast; the dossier catalog needs a
  maintenance/validation cadence so a newly-added external model is not trusted before its tier is
  established.

---

## What this is not

Not a plan, not a schedule, not a commitment. It is the conceptual frame for the data-independence
half of verification, the companion to the menu's adapter-independence half. When a specific menu
row's Foundry instantiation is ready to leave the horizon, it gets its own spec → plan →
implementation cycle, with methylation (GSE86409, generalized past its IDH-status blocker) as the
worked reference.
