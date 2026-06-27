# Polymer Claims — Vision

**Status:** Product vision / external-facing thesis. v1.0
**Date:** 2026-06-27
**Author:** Z. Belden
**Purpose:** The productized statement of what Polymer is and becomes — the capability-cell spine,
the three registries, closed-world agent-first execution, the narrow-menu discipline, and the
verification ladder. The cleanest external articulation of the thesis the other forward docs
operationalize.

> **Read this when** the question is "what is Polymer, in one read, for someone outside the project?"
> For the rigor core see the North Star; for the go-to-market arc see the Linchpin Thesis; for build
> order see the Build Path; for tracked work see the Remaining Roadmap.

### Relationship to the other docs

This sits at the **product-thesis altitude** — consistent with, and a shared external frame over, the
operational forward docs. It does **not** supersede them; it adds productization vocabulary.

- `2026-06-12-phase-2-north-star.md` — the *technical-philosophical charter* (recomputation gate,
  e-value/FDR/defeat unification, rigorous independence). This vision's "verification means evaluating
  a claim within a declared, constrained execution system" **is** the recomputation-gate principle,
  productized.
- `2026-06-16-linchpin-thesis-three-layer-arc.md` — the *commercial arc* (wedge → engine → substrate).
  This vision's "Long-Term Arc" (Infrastructure → Network → Topology → Model) is the same arc, with the
  longer-horizon **Model** stage made explicit.
- `2026-06-21-build-path-and-grounding-recommendations.md` — the *sequencing brief*. This vision's
  "Strategic Discipline" (one legible end-to-end claim) **is** the build-path critical path, restated.
- `2026-06-23-remaining-roadmap.md` — the *tracked work*. The net-new primitives this vision names are
  tracked there under **"Vision-derived additions (2026-06-27)."**

**What this vision adds beyond the others:** the **capability cell** as the first-class, registered,
versioned unit of "what Polymer knows how to claim and evaluate"; the **three-registry** product
surface (capability / adapter / claim); **closed-world, agent-first execution** as the operating
model; and the explicit **verification ladder** and **operational-state** vocabulary. See the
*Reconciliation with current state* footer for what is built vs. net-new.

---

## Thesis

Polymer is the compiler and runtime for AI-generated science. It turns disconnected outputs from models, agents, databases, APIs, and analysis tools into durable scientific state: structured claims with identity, provenance, execution history, verification status, relationships, defeaters, revisions, and trust metadata.

> AI will generate scientific claims at massive scale. Polymer is the protocol that makes them interoperable, executable, and auditable.

Most AI-science products generate content—summaries, hypotheses, predictions, reports, or candidate molecules. Polymer addresses the harder downstream problem: determining what was claimed, what ran, what evidence supports it, what contradicts it, what can be trusted, and what should happen next.

## Product

Polymer provides:

- a machine-readable claim grammar;
- a protocol for generating, selecting, executing, verifying, and integrating claims;
- versioned execution and evidence adapters;
- content-addressed data, analyses, and results;
- licensing, calibration, signing, and attestation;
- a live claims-universe viewer;
- an evolving graph of equivalence, contradiction, defeat, provenance, and revision.

The central boundary must remain explicit:

- what an agent suggested;
- what the claim asserts;
- what computation executed;
- what the system verified;
- what a trust policy accepts.

Verification does not mean proving arbitrary science true. It means evaluating a claim within a declared, constrained execution system and recording exactly what that evaluation establishes.

## Agent-First, Closed-World Execution

Polymer is designed primarily for agents, not manual claim authoring. Agents should not invent arbitrary computations or environments. They should compile proposals into registered, versioned capability cells.

A capability cell defines:

- the scientific task and claim shape;
- accepted inputs and preprocessing assumptions;
- parameters and covariates;
- execution adapters and pinned environments;
- typed outputs;
- agreement and licensing rules;
- resource limits and failure semantics;
- schema and capability versions.

Claims reference shared execution images by capability rather than carrying bespoke environments. Backend agents may build environments, author adapters, execute jobs, migrate claims, and audit independence, but they operate through narrow, testable roles. Humans govern capability admission, trusted adapters, trust roots, and promotion policies.

Operational states must remain legible: malformed, structurally valid, executable, grounded, reproduced, replicated, contradicted, resource-exceeded, stale, migrated, or untrusted.

## Start Narrow and Expand Empirically

Polymer should not begin with a universal scientific IR. It should begin with a small menu of executable bioinformatics claims whose inputs, outputs, and verification rules are crisp—for example:

- two-group numerical comparisons;
- feature–phenotype associations;
- differential methylation probes or regions;
- enrichment analyses;
- fixed-protocol classifier evaluation.

A capability is real only when it has a schema, fixtures, typed outputs, a comparison rule, at least one adapter, preferably an independent second adapter, and verifiable result artifacts.

The core IR should expand only when multiple real capabilities require the same abstraction. Repeated needs—not speculative ontology design—should drive support for richer cohorts, covariates, units, composite endpoints, measurement error, or causal structure. Every schema, adapter, dataset, environment, verifier rule, and artifact format must be versioned with backward-compatible readers or explicit migrations.

## Verification Ladder

Claims can earn progressively stronger standing:

1. **Structural validity** — the claim conforms to the IR.
2. **Executability** — it targets a registered capability and resolvable inputs.
3. **Grounding** — an adapter runs successfully and emits a typed result.
4. **Reproduction** — independent implementations agree on the same data.
5. **Replication** — agreement extends across sufficiently independent cohorts.
6. **Temporal reproducibility** — the claim can be rerun later under pinned or explicitly migrated infrastructure.

Most claims need not reach the highest tier. Failure, disagreement, and later unexecutable states are scientific state, not disposable errors, and must remain visible in the corpus.

## Platform Expansion

Polymer’s menu is the product surface; external tools are execution or evidence substrates. Long-term growth comes from three linked registries:

- **Capability registry:** what Polymer knows how to claim and evaluate.
- **Adapter registry:** which tools, APIs, models, databases, and pipelines can support each capability.
- **Claim registry:** the signed, machine-readable claims and their evolving state.

An integration is not merely an API wrapper. A Polymer adapter accepts a typed claim, invokes a tool under declared parameters, normalizes its output, reports uncertainty and failure modes, attaches provenance, and emits a result eligible for comparison and revision.

Tools that provide context, search, annotation, or hypothesis generation remain valuable, but they do not enter the verification lane until they have a typed claim form and an evaluation path. Adapter maturity and independence should be explicit: experimental, single-adapter, reproduced, replicated, audited, or deprecated.

This supports a disciplined path toward becoming the panintegrator for bio-AI: the place where tools become claims, claims become auditable, and accumulated claims become a living scientific graph.

## Compounding Advantage

The claims universe is more than a visualization. As the corpus grows, its topology can become backend intelligence:

- locate dense, stable, fragile, or contradictory regions;
- identify convergence and shared failure modes across tools;
- track transformations between datasets, models, evidence, and biological entities;
- distinguish representation artifacts from stable objects;
- find disconnected but structurally analogous domains;
- route agents toward claims that most reduce uncertainty.

Each claim, execution, failure, contradiction, and revision improves both the corpus and the map of how scientific knowledge composes and breaks.

## Long-Term Arc

1. **Infrastructure:** harden the grammar, runtime, execution, verification, attestation, and viewer around a narrow menu.
2. **Network:** add high-quality bio-AI capabilities and adapters one at a time.
3. **Topology:** use the growing corpus to identify structure, gaps, incompatibilities, and valuable next experiments.
4. **Model:** train a foundation model on scientific state rather than scientific prose alone.

The eventual training substrate would include structured claims, typed evidence, execution traces, provenance, failed and contradicted claims, revisions, adapter behavior, cross-tool disagreement, topology, temporal updates, and signed verification artifacts.

> Today’s scientific AI is trained largely on what scientists wrote. Polymer can create the substrate for training on what science claims, tests, rejects, and revises.

## Strategic Discipline

The immediate objective is not breadth. It is one legible, externally credible claim demonstrated end to end through real inputs, constrained execution, independent checking, calibration, signing, and a shareable certificate.

The main risks are IR churn, hidden dependence between adapters, provenance complexity, environment decay, ambiguous verification UX, plugin sprawl, corpus-scale performance, and trust-root governance. The response is the same throughout: closed-world execution, explicit versions, content addressing, typed states, narrow extension points, visible uncertainty, and human governance at trust boundaries.

Polymer should make AI-generated claims survivable: inspectable, rerunnable, comparable, challengeable, revisable, and retireable.

> Polymer turns scientific content into scientific state.

---

## Reconciliation with current state (2026-06-27)

Where each pillar stands against the shipped system (full state: `CONTINUE.md`; tracked work:
`2026-06-23-remaining-roadmap.md` → *Vision-derived additions*):

**Built / already on the path:**
- The grammar + protocol + runtime + viewer; content-addressed data, analyses, results.
- Licensing, calibration (`q` validated not asserted), signing (local ed25519 DSSE + local
  transparency log), attestation (in-toto/SLSA/DRS).
- The e-value/FDR/defeat unification; the **adapter trust registry**; the air-gap independence gate.
- REPRODUCED **earned** on a real TCGA-LAML cohort; three executable reductions (`stats::mean_diff`,
  `methyl::region_delta_beta`, `n_dmps`).
- The "Strategic Discipline" wedge **is** the current build-path: H1.A1 signing ✓ → H1.A2 real 2nd
  cohort → H2 shareable wedge claim.

**Net-new this vision names (now tracked as roadmap V1–V4):**
- **Capability cell + Capability Registry** — the spine. The ingredients exist but are *scattered*
  (claim pattern + `impl` string + adapters + SE-Contract + oracle dossier + agreement rule); there is
  no registered, versioned **capability** object yet. Highest-leverage and **not data-blocked**.
- **Three registries as product surface** — adapter registry ✓; **capability registry ✗**; **claim
  registry** only partial (in-repo corpus + signing, not a published surface).
- **Menu expansion** — add **enrichment**, **fixed-protocol classifier eval**, and **feature–phenotype
  association** to the existing two-group / DMP reductions.
- **Verification ladder rung 6 — temporal reproducibility** — partly realized (`verify-kernel --real`
  pinned inputs + the drift daemon); not yet an explicit earned tier/state.
- **Operational states** — add explicit **resource-exceeded**, **migrated**, **untrusted** to the
  lifecycle vocabulary (today: malformed/structural/executable/grounded/reproduced/replicated/
  contradicted/stale).
