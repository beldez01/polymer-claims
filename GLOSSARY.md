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
- **air gap** — the evaluator's "writer ≠ verifier" rule: a `Satisfaction` is minted only when ≥2 *distinct adapter identities* agree. Independence is enforced by the **adapter trust registry** (trusted ∧ different owner ∧ different `implementation_hash`); cross-cohort independence is the §2E **REPLICATED** tier. Local registries derive implementation hashes from adapter bytecode, and licensed satisfactions record the credential identities that justified the registry-independent pair. Owner/trust metadata remains operator-authored.
- **adapter** — an injected implementation that resolves data and runs a node's computation. Pure reference adapters ship in-package; real ones live outside.
- **oracle** — a credibility dossier for a measurement apparatus; its validation tier *caps* a claim's empirical strength axes.
- **daemon** — a standing maintenance pass: DRIFT (re-examine LICENSED claims as the world moves), ORACLE-VALIDATION (decay failing oracles), RED-TEAM (attack the corpus's representation). Pure, caller-scheduled.
- **scheduler / next_action** — the recommend-only budget scheduler that value-ranks the next action (RUN_CYCLE vs a daemon pass) under a shared budget.
- **FDR ledger** — the online false-discovery-rate controller (LOND) over the open-ended test stream.

## Sheaf gauge

- **sheaf consistency gauge** — a cellular sheaf over the claims graph — scalar-ℝ stalks on Quantity-leaf claims, equivalence edges = agreement, defeat edges = sign-flipped antagonism (generalizing the signed-Laplacian embedding). Its Laplacian gives the corpus *inconsistency energy* (Robinson consistency radius — a distance-to-consensus that falls as recomputation harmonizes claims), dim H⁰, and localized H¹ frustration obstructions (contradiction cycles no pairwise check sees). An instrument, not a gate. Umbrella/`[embed]`; pure extractor in `protocol/sheaf.py`, numpy spectrum in `polymer_claims/sheaf_spectrum.py`.
- **inconsistency energy / consistency radius** — the scalar headline from the sheaf Laplacian: the Robinson consistency radius, a distance-to-consensus that falls as recomputation harmonizes claims. Surfaced by `export-consistency` and `TopologyExport.consistency`. See *sheaf consistency gauge*.
- **H⁰ / H¹ (sheaf)** — dim H⁰ = number of globally consistent components; H¹ frustration obstructions = contradiction cycles that pairwise checks cannot detect. See *sheaf consistency gauge*.
- **consistency overlay (viewer)** — the live viewer surfaces the gauge behind one opt-in toggle: a falling energy HUD, per-claim **tension halos** on nodes, the H¹ **frustration-cycle overlay**, and an obstruction panel (click-to-focus). Fed by the throttled `GET /consistency` route; off ⇒ the rendered view is unchanged. See *sheaf consistency gauge*.

## Node, viewer & exports

- **node** — the local mutable host (`NodeRunner` + the `serve` FastAPI server). The ONE impure piece; owns the loop/clock/network.
- **topology / timeline** — the export DTOs: `TopologyExport` (nodes/edges/clusters + a deterministic 3D layout) and `TopologyTimeline` (a sequence of warm-started frames + per-frame stats). The protocol↔viewer contract.
- **attestation / standards skin** — a deterministic **in-toto Statement v1 / SLSA Provenance v1** export of a LICENSED claim (+ a GA4GH **DRS** object per dataset), keyed by the content-address the gate already computes (`dimnames_hash`/`profile_hash`/`semantic_run_id`); the air-gap credential pair are the SLSA `builderDependencies` (recompute gate = trusted builder, independence = its security guarantee). The recomputation gate re-expressed as the GA4GH/in-toto/SLSA trust fabric so a third party can verify a run *without trusting our service*. `export-attestation <corpus>` → an `AttestationBundle` (a Polymer envelope over verifier-compatible Statements). Pure umbrella serializer (`attestation.py`, `build_attestation_bundle`); `resolve_contract_index` is the only IO. **Slice 1: local JSON, no signing/Rekor/DSSE** (those are later slices). **Slice 2 (arc 2): `export-attestation --format dsse`** emits per-claim **unsigned DSSE-shaped envelopes** (`signatures: []`) in NDJSON — each envelope wraps the in-toto Statement as a base64 `payload`; signing-ready but **not trust-valid** (decode `payload` to read the bare Statement; real signing is slice 3). North-Star arc 2, §4 seam #3.
- **sample mode** vs **live mode** — the viewer either loads a precomputed `public/sample-timeline.json` (sample) or connects to a running node over SSE (live).
- **layout (spectral / force)** — how the node positions claims. **spectral** (default) = the signed-Laplacian eigenmap (`embedding.py`), orthogonal-Procrustes-aligned to the previous frame so the live universe grows smoothly (`layout_id="external:spectral-v1"`). **force** = the legacy id-hash Fruchterman-Reingold layout. Selected by `serve --layout {spectral,force}`; spectral needs the `[embed]` extra (numpy) and gracefully falls back to force without it.
- **viewer** — the standalone Next/Three.js UI in `viewer/`. Reserve "viewer" for this app unless explicitly discussing polymerbio.org integration.

## External / product

- **polymerbio.org / PolymerGenomicsAPI** — the deployed biophysics database + its redesigned front-end. The future integration target for the claims viewer (and the D2 aesthetic source).
- **superpowers** — the skills/workflow tooling (`docs/superpowers/`) used to build this repo (brainstorm → spec → plan → subagent-driven). Not part of the shipped product.
- **IR** — intermediate representation. Here, the claim grammar (v1.3) or FormalClaim (v1.2).
