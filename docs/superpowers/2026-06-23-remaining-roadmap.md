# Remaining Work — Forward Plan

**Reconciled: 2026-07-07** (supersedes the 2026-06-23 draft — shipped items removed; history in `git log` + `CONTINUE.md`).
**Authoritative current state:** `docs/superpowers/CONTINUE.md` (2026-07-01 snapshot). **This doc carries forward-only, pending work.**

> **Why this was rewritten.** The 2026-06-23 version listed the Capability Cell (V1), V2.0, and
> ontology-typed subjects as *pending* — all three had shipped (V1 `b058d3c`; V2.0 Slice 1
> `9b8848c`; the 10-variant `Subject` union in `grammar/src/polymer_grammar/subject.py`). Planning
> against it caused a full re-plan of shipped work. **Rule going forward: confirm status against
> `git log` + `CONTINUE.md`, never against a dated design doc.** Filename kept (referenced by
> `CONTINUE.md` / `ARCHITECTURE_CURRENT.md`); content is current as of the reconcile date above.

---

## Shipped — do NOT re-plan (pointer only; detail in `CONTINUE.md` + `git log`)

Capability Cell + Registry (V1) · V2.0 Slice 1 evidence-licensed capability (`eval::benchmark_advantage`, `EVIDENCE_LICENSED` route) · ontology-typed `Subject` union (MONDO/HPO/UBERON/VRS/HGVS/HGNC…) · H0.1 + H0.1b kernel proofs · local ed25519 DSSE signing + local RFC-6962 transparency log · foreign-claim ingestion (WITNESSED) · Phase 1/2 real-data licensing (TCGA-LAML n-DMP + HLA-A promoter on BLUEPRINT WGBS — on `main` via `c4fe813`/`b8fbb1f`; `CONTINUE.md`'s "not yet merged" note is stale).

---

## The spine (unchanged): Path α — wedge-first

The **wedge (H2)** is the deliverable; everything else is parallel deepening or wedge-enabling. The wedge is gated on a real 2nd cohort (H1.A2), being sourced separately. Three-layer arc context: `docs/superpowers/2026-06-16-linchpin-thesis-three-layer-arc.md`.

---

## NEAR-TERM PRIORITY (new) — Adapter-Independence Hardening (the D4 defense)

The theory's most exposed defeater (`docs/the-theory-of-polymer-claims.md`, D4): **organizational independence ≠ epistemic independence** — two "independent" adapters can share priors and fail together, making agreement one witness counted twice. Today this is only a recommendation set (`specs/2026-06-29-adapter-independence-hardening-notes.md`).

- **Plan:** `plans/2026-07-07-adapter-independence-hardening-plan.md` (turns the notes into a scheduled arc).
- **Non-data-blocked.** Starts with a **1-day falsifiable experiment** (AlphaMissense vs ESM1v error-correlation on ClinVar) that gates the rest.
- **Highest-leverage non-data-blocked build** — it decides whether the warrant is real or hollow.

---

## Pending — wedge-enabling (Track A, spine)

- **H1.A2 — real 2nd HM450 AML cohort** with machine-readable IDH status → §2E **REPLICATED** (cross-cohort product e-value). Data sourcing/curation (**in progress in a separate instance**). The critical-path gate to H2.
- **Networked Rekor backend → public non-repudiation** (Layer-A1 "Earn-Standing"). DESIGNED, intentionally TABLED (`specs/2026-06-26-networked-rekor-backend-design.md`). **Un-table timed to the first externally-shared wedge** — the wedge and its third-party-verifiable certificate should ship together.
- **H2 — one legible wedge claim shipped** as a public, signed, calibrated certificate (variant-adjudication / biomarker ledger / AML disease-twin, per linchpin §3). The deliverable.

## Pending — capability-menu growth (V2.0's lesson is now in hand)

- **CORRELATION_CELL + two independent correlation adapters + a generation adapter** — unlocks the `spearman_rho` claims (a large fraction of the 47-claim universe, e.g. `hla_a_dg37_vs_tpm`). Concrete near-term build (`CONTINUE.md` NEXT). **Scope first** — none of the three parts exists.
- **More `mean_diff` migrated claims** — cheap generalization; reuse the `hla_promoter_meth_claim` pattern (bind real data → CSV, set threshold).
- **V2.0 Slice 2** (full attestation chain + certificate/SLSA `resolvedDependencies`) and **Slice 3** (defeat/drift/reinstatement/replay-over-time). Deferred follow-ons of shipped Slice 1.
- **V2.1 enrichment / V2.2 fixed-protocol classifier-eval / V2.3 feature–phenotype association** — candidate cells.

## Pending — deepening (Track B, credence layer)

- **H1.B1** proper scoring for resolvable attested claims (log/Brier vs a baseline — needs a baseline source; design first).
- **H1.B2** surrogate scoring / peer-prediction over the corpus graph.
- **H1.B3** live external feeds (ClinVar/trial-registry taps replacing the operator file-drop).
- **H1.B4** defeat-edge auto-wiring between contradictory attestations.

## Pending — calibration completeness (Track C, opportunistic)

- **H1.C1** `q_anchored` Kaplan–Meier hazard curve.
- **H1.C2** real-claim `q`-resolution loop (gated on real, resolvable claims).

## Pending — conceptual / lifecycle

- **First-class `WITNESSED` status** (today: `--sheaf-active` pending + the compute-boundary discipline).
- **V3.1** temporal reproducibility as an explicit earned standing; **V3.2** operational states (`resource-exceeded`, `migrated`, `untrusted`).
- **Parameterization-seam research program (the neurosymbolic frontier — the IR leaves layer).** The open questions at the seam where the symbolic type-system meets neural judgment that fills the typed slots (strength-axis parameterization, causal-role assignment, ontology grounding, leaf-types, and *neurosymbolic caging* — how much bad neural judgment the symbolic layer catches) are laid out as a **falsifiable research program** — each seam stated as a testable hypothesis with the metric that decides it and the first study that closes it: **`docs/open-questions-research-plan.typ`**. Group A is the leaves/parameterization frontier; Group B carries the statistical seams (its **B1 conceptual-independence** is exactly backlog item ② *independence-as-claim*). This is the "validate from foundations" discipline the *NOT building now* line below refers to — the calibration studies, not new machinery. Companion to `docs/superpowers/foundations/measurement-foundation.md` (the parameterization-seam whisper).

## Hygiene / small (do opportunistically)

- **H0.2** `ingest-attested` write-time idempotency (skip if `source_claim_id` on disk). **H0.3** UX edges (`validate` silently rejects a `Corpus`; confirm the custom `export-attestation` `bundleType`).

---

## Horizon — vision, not sprint (Layer A / B substrate)

- **Layer B:** full autonomous hypothesizer; negative-capacity corpus; red-team marketplace.
- **Layer A:** Earn-Standing API; federated / BYO-compute (`POST /inject` hook noted); the reproducibility observatory (the **Science Claw** — agent-facing, local-first, BYO-compute).
- **V4** claim registry as a published surface (gated on H2 — a real shareable claim worth publishing).
- **Deferred infra** (pull in only when they block a higher item): Python/R hash parity (needs an R serializer); schema→TypeScript codegen / API narrowing; PyPI publish + a CI workflow mirroring `scripts/check-all.sh` (`beldez01` flag resolved — publish unblocked). *(`ROBUSTLY_BLAMED` wiring — done 2026-07-07 via the H¹→blame-set coupling; no longer deferred.)*

## Explicitly NOT building now

Scaled infrastructure (Layer-A endgame); measurement-theory / morphospace machinery (validate from foundations, don't build); auth / multi-tenant / federation beyond what the wedge needs.

---

## Recommended critical path

```
adapter-independence Step 0 (1-day experiment) ─┐   ← non-data-blocked; do now
                                                 ├─▶ R1→R2→R5 hardening (D4 defense)
H1.A2 real 2nd cohort (separate instance) ──────▶ H2 wedge claim ──▶ public signed certificate
                                    (+ un-table networked Rekor, timed to the wedge)
```

**Immediate next action:** run the adapter-independence Step-0 experiment (spec in the plan doc) — it's the cheapest falsifiable probe of the theory's load-bearing defeater and needs no cohort. Each larger slice gets its own `writing-plans` → `subagent-driven-development` (TDD) → whole-branch review → merge `--no-ff` → update `CONTINUE.md`.
