# Polymer Claims — Glossary

Terse, reserved definitions. When these terms overlap in conversation, this file is the tiebreaker.
See `ARCHITECTURE_CURRENT.md` for how the active pieces fit together.

## Versions & packages

- **FormalClaim** — the **v1.2** claim IR (`polymer_formalclaim`). Reserved for v1.2 only. The v1.2 tree was moved out of the repo (2026-06-17, preserved locally); the v1.3 system never depended on it.
- **grammar** — the **v1.3** claim IR (`polymer_grammar`, in `grammar/`). Reserved for the v1.3 schema/type-system. "What a claim *is*."
- **protocol** — the **runtime/flywheel** over the grammar (`polymer_protocol`, in `protocol/`). "How a corpus *evolves*." Reserved for the runtime, never the schema.
- **polymer-claims** — the umbrella distribution package (`src/polymer_claims/`): CLI + local node/server over grammar + protocol.

## Core IR concepts (grammar)

- **claim** — a single `Claim`: pattern-typed, sum-typed leaves, status, optional strength/licensing/subject/conclusion/roles/provenance/governance/evaluation-plan.
- **corpus** — a `Corpus`: exactly 4 collections (claims, defeat_edges, equivalences, fdr_ledger). The unit the protocol transforms.
- **leaf (L0)** — the empirical anchor; a sum type (Quantity/Categorical/Existence/Proposition) so qualitative/warrant findings are first-class, not fake statistics.
- **proposition (L1)** — molecular claim content; identity is an *asserted, licensed equivalence*, never a hash.
- **strength** — a 6-axis Pareto vector (magnitude, certainty, evidence_against_null, severity, world_contact, explanatory_virtue), uniformly higher-is-better, no hidden scalar.
- **licensing** — the bridge that mints a LICENSED status: an (σ, M) satisfaction via a severe-test or replication route, with a required rival-set-closure. No "LICENSED-simpliciter."
- **independence tier (REPRODUCED / REPLICATED)** — the `Licensing.independence_tier` standing (§2E). **REPRODUCED** = the agreeing implementations share the dataset (the air-gap; today's default). **REPLICATED** = reproduced across ≥2 cohorts with distinct `dimnames_hash` — the only tier that permits *multiplying* the cohorts' e-values (independent data → a valid product e-value), recorded as one e-LOND test.
- **defeat graph / VAF (L3)** — value-based argumentation: a strength-mediated effective-defeat relation whose **grounded extension** is the accepted set.
- **AGM revision (L4)** — belief-base expand/contract/revise + entrenchment, for how the corpus changes under new incompatible claims.
- **representation-revision** — a schema/representation change expressed as a first-class licensable (meta-tier) claim.

## Runtime concepts (protocol)

- **run_cycle** — one pass of the flywheel: represent → generate → canonicalize → safety_gate → select → commit → execute_ground → verify_stage → integrate. Pure; threads a frozen `Corpus` + `SelectionLedger`.
- **flywheel** — the generate → select → execute → verify → integrate loop that grows the corpus.
- **air gap** — the evaluator's "writer ≠ verifier" rule: a `Satisfaction` is minted only when ≥2 *distinct adapter identities* agree. Independence is enforced by the **adapter trust registry** (trusted ∧ different owner ∧ different `implementation_hash`); cross-cohort independence is the §2E **REPLICATED** tier. (Open: `implementation_hash` is operator-asserted — byte-derived hashing is the next hardening slice.)
- **adapter** — an injected implementation that resolves data and runs a node's computation. Pure reference adapters ship in-package; real ones live outside.
- **oracle** — a credibility dossier for a measurement apparatus; its validation tier *caps* a claim's empirical strength axes.
- **daemon** — a standing maintenance pass: DRIFT (re-examine LICENSED claims as the world moves), ORACLE-VALIDATION (decay failing oracles), RED-TEAM (attack the corpus's representation). Pure, caller-scheduled.
- **scheduler / next_action** — the recommend-only budget scheduler that value-ranks the next action (RUN_CYCLE vs a daemon pass) under a shared budget.
- **FDR ledger** — the online false-discovery-rate controller (LOND) over the open-ended test stream.

## Node, viewer & exports

- **node** — the local mutable host (`NodeRunner` + the `serve` FastAPI server). The ONE impure piece; owns the loop/clock/network.
- **topology / timeline** — the export DTOs: `TopologyExport` (nodes/edges/clusters + a deterministic 3D layout) and `TopologyTimeline` (a sequence of warm-started frames + per-frame stats). The protocol↔viewer contract.
- **sample mode** vs **live mode** — the viewer either loads a precomputed `public/sample-timeline.json` (sample) or connects to a running node over SSE (live).
- **layout (spectral / force)** — how the node positions claims. **spectral** (default) = the signed-Laplacian eigenmap (`embedding.py`), orthogonal-Procrustes-aligned to the previous frame so the live universe grows smoothly (`layout_id="external:spectral-v1"`). **force** = the legacy id-hash Fruchterman-Reingold layout. Selected by `serve --layout {spectral,force}`; spectral needs the `[embed]` extra (numpy) and gracefully falls back to force without it.
- **viewer** — the standalone Next/Three.js UI in `viewer/`. Reserve "viewer" for this app unless explicitly discussing polymerbio.org integration.

## External / product

- **polymerbio.org / PolymerGenomicsAPI** — the deployed biophysics database + its redesigned front-end. The future integration target for the claims viewer (and the D2 aesthetic source).
- **superpowers** — the skills/workflow tooling (`docs/superpowers/`) used to build this repo (brainstorm → spec → plan → subagent-driven). Not part of the shipped product.
- **IR** — intermediate representation. Here, the claim grammar (v1.3) or FormalClaim (v1.2).
