# Polymer Claims — Canonical Specification

> Current state of record for `main` as of 2026-06-22. This document states what the
> system is, not the phase history. Use `docs/superpowers/CONTINUE.md` for the live
> build log and next work; use the dated specs/plans for design rationale.

## 1. System Shape

Polymer Claims is a compiler and runtime for empirical claims. The grammar defines what
a claim is; the protocol defines how a corpus evolves; the umbrella package hosts a local
mutable node; the viewer renders the evolving topology.

```
grammar  ->  protocol  ->  node (src/polymer_claims)  ->  viewer
claim IR     pure corpus    local mutable host             Next/R3F UI
             runtime        + FastAPI SSE
```

| Layer | Package | Path | State |
|---|---|---|---|
| Claim grammar | `polymer_grammar` | `grammar/` | Complete v1.3 IR |
| Protocol runtime | `polymer_protocol` | `protocol/` | Complete flywheel + daemons |
| Umbrella node/CLI | `polymer-claims` | `src/polymer_claims/` | Active local runtime |
| Viewer | Next/React Three Fiber | `viewer/` | Active sample + live viewer |

## 2. Hard Invariants

- `Corpus` has exactly four collections: `claims`, `defeat_edges`, `equivalences`,
  `fdr_ledger`.
- Grammar and protocol are pure, deterministic, numpy-free, and filesystem/network-free.
  Time-like inputs are passed in. The umbrella node/server is the only impure layer.
- `grammar/` never imports legacy `polymer_formalclaim`; `protocol/` depends one-way on
  `grammar/`. Isolation tests enforce this.
- Models subclass frozen `_Model` with `extra="forbid"`; collection fields are tuples.
- Cross-cutting fields are additive and inert by default (`None` or `()`), preserving
  byte-identical behavior when a feature is off.
- Numpy is behind optional umbrella extras (`[embed]`); base import stays light. The sheaf structure extractor (`protocol/sheaf.py`) is pure and numpy-free; only the spectrum computation (`polymer_claims/sheaf_spectrum.py`) requires `[embed]`.

## 3. Claim Grammar

The grammar is a five-layer IR plus protocol-imposed fields and a verifier-facing compute
graph.

- **L0 leaf:** empirical anchors as a sum type: quantity, categorical, existence, or
  proposition.
- **L1 proposition:** molecular claim content; identity is an asserted and licensed
  equivalence, not a hash.
- **L2 licensing + roles/units:** `LICENSED` status is minted only through a satisfaction
  route with rival-set closure. Typed roles and unit dimensions live here.
- **L3 defeat graph:** value-based argumentation with a strength-mediated effective
  defeat relation and grounded extension.
- **L4 revision:** AGM/TMS-style expand, contract, and revise operations.

Strength is a six-axis Pareto vector:
`magnitude`, `certainty`, `evidence_against_null`, `severity`, `world_contact`,
`explanatory_virtue`. Higher is better on every axis; there is no hidden scalar collapse.

Protocol-imposed fields include provenance, governance, subject, online-FDR state,
representation-revision metadata, pre-registration commitment hashes, severity provenance,
and independence tier metadata.

## 4. Protocol Runtime

`run_cycle` is the pure flywheel:

```
represent -> generate -> canonicalize -> safety_gate -> select -> commit
          -> execute_ground -> verify_stage -> integrate
```

The standing daemons are pure caller-scheduled passes:

- **DRIFT:** re-examines licensed claims when content/world state changes.
- **ORACLE-VALIDATION:** decays or caps claims through apparatus/oracle credibility.
- **REPRESENTATION RED-TEAM:** attacks the corpus representation.

`next_action` recommends budget-aware scheduling across cycle and daemon actions. Topology
exports are protocol DTOs consumed by the viewer.

## 5. Epistemic Core

Licensing, corpus FDR, and defeat are one e-value-native mechanism:

```
LICENSED iff adapter-agreement and SATISFIED and grounded and live e-LOND discovery
```

- The FDR ledger is online e-LOND over an open-ended claim stream, with one e-test per
  claim lifetime.
- Evidence atoms are Waudby-Smith-Ramdas betting e-values.
- Defeat de-licenses through the ledger by tombstoning/retracting the discovery and
  refunding alpha wealth.
- Reinstatement reopens defeat-rejected claims to `PENDING` when their attacker falls.
  Refuted claims remain terminal.
- Pre-registration charges and locks the e-LOND slot before data is seen. Verify rejects
  post-hoc plan changes with `HYPOTHESIS_ALTERED`.

## 5a. Sheaf consistency gauge

The corpus's defeat and equivalence edges form a **cellular sheaf over the claims graph**: a scalar-ℝ stalk on each Quantity-leaf claim, equivalence edges encoding agreement (sign `+1`), and defeat edges encoding antagonism (sign `−1`, generalising the signed-Laplacian embedding). `protocol/sheaf.py` extracts a pure, numpy-free `SheafStructure`; umbrella-side `polymer_claims/sheaf_spectrum.py` (behind `[embed]`) computes the **Robinson inconsistency energy** (normalized squared edge tension — a distance-to-consensus that falls as recomputation harmonizes claims), `dim H⁰` (consistent components), and signed-BFS-localised `H¹` frustration obstructions (contradiction cycles no pairwise check sees). This is an **instrument, not a gate** — no claim status changes. A cheap `ConsistencyHeadline` (energy + spectral gap λ₂) attaches to every `TopologyExport` as `TopologyExport.consistency` when numpy is present; the full `ConsistencyReport` is available via the `export-consistency` CLI. Cross-unit equivalences are flagged as `DataQualityFlag`s rather than silently dropped. First concrete realisation of the North-Star §3 sheaf-cohomology global-consistency gauge / linchpin A3 (Reproducibility Observatory). The viewer exposes a live **consistency overlay** (one opt-in toggle) driven by a throttled `GET /consistency` route on the local server: an energy HUD + sparkline, per-claim **tension halos**, and an animated **H¹ frustration-cycle overlay** with an obstruction panel. Two precision corrections back this: the per-frame `ConsistencyHeadline` carries **energy only** (P1 — λ₂ is computed only in the on-demand `ConsistencyReport`, never on the tick path), and `per_claim_tension` is a **nonnegative edge-share** attribution (P3 — a valid opacity), not the signed Rayleigh diagonal.

## 5b. Standards-skin attestation (arc 2)

`export-attestation` re-expresses a LICENSED run in the trust standards that already exist, so a third party can verify it **without trusting our service**. **Slice 1** emits, per LICENSED claim, an **in-toto Statement v1** subject with a **SLSA Provenance v1** predicate that casts the recomputation gate as the builder — the air-gap credential pair are the SLSA `builderDependencies`, and the resolved datasets are **GA4GH DRS** objects keyed by the content-address the gate already computes (`dimnames_hash`/`profile_hash`/`semantic_run_id`). The serializer is pure (frozen `_Model` DTOs, stdlib `json`/`hashlib`; `resolve_contract_index` is the only IO); the default bundle is additive. **Slice 2** adds `--format dsse`: each Statement is wrapped in a **DSSE-shaped envelope** with empty `signatures` and emitted as NDJSON — **signing-ready but not trust-valid** (decode `payload` for the bare Statement; a DSSE signature verifier treats it as unsigned). Real signing (Sigstore/cosign/Rekor + the DSSE PAE) is **slice 3**, deferred. This is the first seam of the North-Star §4 standards arc (#3, in-toto/SLSA) — the adoption moat: "point your pipeline at us," not "rewrite for us."

## 5c. Calibration Ledger And Certificate

`q` is the corpus's headline integrity metric — the expected false-license rate. This layer makes
it *validated, not asserted*, and emits it as a shareable **certificate**. Calibration is an
**instrument, not a gate**: it measures the gate's reliability and never changes a claim's status,
and the ledger is a separate meta-structure (the `Corpus` stays four collections).

The calibration ledger records resolutions in three **warrant tiers**, each measuring a different
thing and reported separately (never pooled):

- **DEFINITIONAL** — realized false-discovery rate against *constructed* ground truth. A synthetic
  harness (`calibration_harness.py`, behind the `[calibrate]` numpy extra) generates Beta-distributed
  cohorts with known per-region truth, writes them as SE-Contract files, and runs them through the
  **real gate** (the betting e-value, the two-adapter air-gap, and the e-LOND ledger — reached via a
  scoped contract-root contextvar so the unmodified adapters resolve the synthetic contracts). The
  headline `q` is the **realized FDR = mean per-batch FDP** over *mixed* batches (the Monte-Carlo
  estimate of `E[FDP] ≤ q`); the pooled false fraction is a secondary view, and an all-null batch is
  only a control. This is the one tier that feeds the headline `q`.
- **ANCHORED** — warrant survival: how often LICENSED claims survive the corpus's own continued
  pressure (defeat, drift). The umbrella `calibration_store.py` taps `NodeRunner` (a gated
  `calibration_path` hook, byte-identical when off), allocates a `license_epoch` per claim
  (idempotent across ticks and restarts), and records resolutions to an append-only JSONL event log
  folded per `(claim_id, license_epoch)`. This measures stability under pressure, **not** truth.
- **ATTESTED** — disagreement against external attested events; schema and report slot only for now
  (no ingestion source yet).

The anti-laundering rule is enforced in code: `feeds_headline_q` is a computed property, true only
for DEFINITIONAL realized-FDR, and the certificate renderer surfaces only that as *the* headline
`q` — ANCHORED/ATTESTED appear under a distinct field-calibration heading.

The **certificate** (`certify` CLI; `Certificate` / `build_certificate` /
`certificate_dsse_envelope` in `attestation.py`) is a single-claim artifact composing the existing
in-toto/SLSA Statement with the calibration block (the three tiers + the disclosed generating-model
+ a ledger-snapshot digest), wrapped in a DSSE-shaped envelope so the calibration evidence sits
inside the signed payload. Existing `export-attestation` output stays byte-identical (new public
names only). This is the first realisation of `q` as a *typed reliability statement over warrant
classes* — definitional calibration where truth is constructible, field calibration where only
continued pressure is available.

## 6. Independence And Shared Causes

The system distinguishes reproducibility from error-independent replication.

- **REPRODUCED:** independent implementations agree on the same cohort/data. This is the
  default air-gap tier.
- **REPLICATED:** agreement spans at least two distinct cohorts and may combine cohort
  e-values as a single e-LOND test.

REPLICATED is now common-cause gated. When runs declare
`MaterializationContext.shared_cause_factors`, the tier requires both distinct
`dimnames_hash` values and every pairwise shared-cause Jaccard overlap below
`SHARED_CAUSE_TAU = 0.5`. If overlap is too high, the claim remains REPRODUCED and the
umbrella replication path withholds the e-value product. `Licensing.shared_cause_overlap`
records the assessed maximum overlap.

When no factor sets are declared, behavior falls back to the pre-existing §2E rule so old
fixtures and external contracts remain byte-identical. Bundled SE-Contracts carry flat
operator-authored factors; byte-derived or credential-backed factor provenance is future
hardening.

## 7. Severity Provenance And Incubation

Hypotheses can record `Provenance.prior_cohorts`, the cohorts on which their motivating
prior was established. Verify compares those to the test cohort identities:

- no prior cohorts: inert;
- no overlap: `severity_provenance=HELD_OUT`;
- overlap: `severity_provenance=CONFIRMATORY` and the `severity` strength axis is capped.

Strict shared-cause mode can withhold confirmatory claims. SELECT can use an injected
`cohort_of_ref` mapping to rank confirmatory candidates lower without reading outcome data,
and `register_selected` registers only selected/top-k hypotheses. This keeps incubation
data-blind while preserving the pre-registration accounting.

## 8. Real Computation

The runtime licenses computed evidence, not just asserted values.

- Mean-difference claims can execute over bundled data with two independent stdlib
  adapters.
- Methylation claims run through SE-Contracts and `AnalysisProfile` content addressing.
  The main claim families are `region_delta_beta` and `n_dmps`.
- The n-DMP reduction is earned at REPRODUCED on real TCGA-LAML HM450 betas. The IDH labels
  were upgraded to cBioPortal complete genotyping (`tcga_laml_idh@2`); real data remain
  local and gitignored.
- The region-delta-beta reduction is honest but currently PENDING: after the IDH-source
  swap its held-out e-value is 5.672, below the first e-LOND discovery bar 32.9.

Real second-cohort REPLICATED licensing is intentionally skipped for now. It is
data-access-blocked, not code-blocked: GSE86409 betas are available, but public GEO does
not expose machine-readable per-sample IDH status.

## 9. Umbrella Node

The umbrella package provides:

- CLI: `version`, `validate`, `ingest tcga-laml`, `run-cycle`, `loop`,
  `export-topology`, `export-timeline`, `export-consistency`, `export-attestation`,
  `calibrate`, `certify`, `serve`;
- `NodeRunner`, which owns clock, loop state, layout choice, and live corpus state;
- FastAPI SSE server behind `[serve]`;
- optional `[llm]` generation adapters and `[embed]` spectral layout support.

The local server is hardened for local use with max-frame retention, a tick lock, bounded
SSE queues, and a non-loopback bind guard. Mutating routes remain unauthenticated by
design; this is not a deployed multi-tenant service.

## 10. Viewer

The viewer is a standalone Next/React Three Fiber app. It supports:

- sample timeline playback from `viewer/public`;
- live SSE streaming from `serve`;
- force layout for deterministic protocol exports;
- spectral live layout via signed-Laplacian eigenmap with per-frame Procrustes alignment.

Viewer nodes surface `independence_tier`, `severity_provenance`, and
`shared_cause_overlap` when present. `TopologyExport.consistency` carries a `ConsistencyHeadline` (inconsistency energy + spectral gap) when `[embed]` is installed; `None` otherwise. When the local server exposes `GET /consistency`, the viewer renders the live consistency overlay (energy HUD, tension halos, H¹ frustration-cycle overlay + obstruction panel).

## 11. Current Caveats

- Local adapter registries derive `implementation_hash` values from adapter implementation
  bytecode, and licensed satisfactions record the credential identities that justified the
  registry-independent air gap. Registry owner/trust metadata remains operator-authored.
- `semantic_run_id` is currently the Python digest. R parity is deferred until an R
  serializer exists.
- Bundled SE-Contracts carry flat `shared_cause_factors`, and `materialization.py`
  propagates cohort-A factors into verify's satisfaction context. The factor sets are still
  operator-authored metadata; byte-derived or credential-backed factor provenance is future
  work.
- A real second methylation cohort remains skipped until valid per-sample genotype labels
  are available.
- The DEFINITIONAL realized-FDR is validated against a *synthetic* generating model, named on the
  certificate as a disclosed assumption (calibration is an instrument, not a gate). Deferred:
  ATTESTED ingestion, an exposure-weighted hazard model for the ANCHORED warrant-survival rate, and
  real cryptographic signing of the certificate (Sigstore/Rekor/DSSE PAE — attestation arc-2 slice
  3). The normal-approx CI over the per-batch FDPs is descriptive, not a validity proof.

## 12. References

- Live state and next work: `docs/superpowers/CONTINUE.md`
- Architecture map: `ARCHITECTURE_CURRENT.md`
- Terminology: `GLOSSARY.md`
- Forward roadmap: `docs/superpowers/2026-06-16-autonomous-hypothesis-loop.md`
- Phase 2 north star: `docs/superpowers/2026-06-12-phase-2-north-star.md`
- Calibration ledger + certificate: `docs/superpowers/specs/2026-06-22-calibration-ledger-and-certificate-design.md` (+ the matching plan)
- Current plans/specs: `docs/superpowers/plans/` and `docs/superpowers/specs/`
- Historical plans/specs: `docs/superpowers/archive/`
