# Remaining Work — Roadmap at All Levels

**Date:** 2026-06-23
**Author:** Z. Belden (synthesized with Claude)
**Basis:** spot-verified project state (every shipped slice exercised end-to-end 2026-06-23) +
the north-star (`2026-06-12-phase-2-north-star.md`), linchpin three-layer arc
(`2026-06-16-linchpin-thesis-three-layer-arc.md`), and build-path
(`2026-06-21-build-path-and-grounding-recommendations.md`) docs.

> **Verified ground truth (2026-06-23).** Grammar (396t), protocol (430t), umbrella CLI, viewer,
> the full calibration roadmap (5/5), Arc-2 attestation slices 1–2, the sheaf gauge, and the new
> ATTESTED ingestion credence-layer slice all run end-to-end. **One correction to the docs:** the
> Phase-A real-data n-DMP "kernel proof" is **not reproducible offline** — `data/tcga_laml/` holds
> metadata/scripts but no HM450 beta matrices, and `ingest tcga-laml` calls the live GDC API
> (404 in a network-constrained env). The proof was real when run; it is not currently re-runnable.

---

## The one strategic fork

The project's own build-path doc says the critical path is **Layer C — the wedge**: prove one
legible claim end-to-end where we're unmatched. But we just shipped the first credence-layer slice,
which invites *deepening that moat* instead. These compete for the next few sprints:

- **Path α — Wedge-first (build-path doc's stated critical path):** make the kernel proof
  reproducible, make its certificate externally verifiable (real signing), unblock the real 2nd
  cohort, and land one shareable wedge claim. Optimizes for an external, demonstrable result.
- **Path β — Credence-moat-first:** build the proper-scoring and peer-prediction engines on top of
  the ATTESTED typing we just shipped. Optimizes for technical depth / differentiation.

**Recommendation: Path α.** A kernel proof that isn't reproducible (H0 below) is the single biggest
latent liability — it undermines the whole "validated, not asserted" value proposition. The credence
engines (Path β) are high-value but not on the critical path to a demonstrable wedge, and they need
inputs (baselines, peer corpora) we don't have yet. Sequence α as the spine; pull β slices in as
parallel deepening once the wedge is reproducible and signable.

> **DECISION (2026-06-23, confirmed by Z. Belden): Path α — wedge-first.** Sprint order follows the
> Path-α critical path below; Track B (credence engines) is parallel deepening, not the spine.

---

## Horizon 0 — Reproducibility & hygiene (small, high-leverage, do first)

These are cheap, unblock everything downstream, and close gaps the spot-verification surfaced.

- [ ] **H0.1 — Offline-reproducible kernel *pipeline* proof (synthetic).** Spec'd + planned
  (`specs/2026-06-23-offline-kernel-proof-design.md`, `plans/2026-06-23-offline-kernel-proof.md`).
  A fully synthetic, deterministic HM450-shaped fixture run through the **real** n-DMP gate, guarded
  by a committed test and a `verify-kernel` CLI, plus a hardened retrieval runbook. *Why:* gives a
  fresh checkout a deterministic, offline `LICENSED @ REPRODUCED` proof of the gate pipeline — closes
  the "nothing reproduces offline" gap. *Note:* this proves **pipeline integrity, not the real
  biology** (nothing real committed). *Size:* S–M.
- [ ] **H0.1b — Real `@2` data: retrievable, fresh-checkout-runnable artifact.** The *real* proof
  (`se:tcga_laml_idh@2`: local Xena methylation450 matrix + cBioPortal `laml_tcga_pub` genotyping)
  currently depends on **local-only, gitignored** files under `data/tcga_laml/`
  (`build_contract_xena.py`, `run_gate.py`, the cBioPortal inputs) — not in a fresh checkout. Make
  the real proof reproducible from clean: commit the cBioPortal genotyping inputs + a parameterized
  (non-hardcoded-path) build/gate script via explicit `.gitignore` exceptions, and provide a
  retrievable/cached Xena artifact recipe. *Why:* H0.1 reproduces the pipeline; H0.1b reproduces the
  actual headline numbers. *Size:* M (data governance + script de-hardcoding). *Residual split out of
  H0.1 so the synthetic slice is not mistaken for closing real-data offline reproducibility.*
- [ ] **H0.2 — `ingest-attested` write-time idempotency (optional).** Today re-ingest appends a
  duplicate JSONL line; `load_ledger` folds it away on read. Add an opt-in "skip if `source_claim_id`
  already on disk" to stop unbounded file growth. *Size:* S. *(Low priority — read-time semantics
  are already correct; this is storage hygiene.)*
- [ ] **H0.3 — UX sharp edges from verification.** `validate` silently rejects a `Corpus` (it's
  claim-level); document/curb it. Confirm the custom `export-attestation` `bundleType` is intended
  vs. the SLSA bundle envelope. *Size:* S.

## Horizon 1 — Two parallel tracks once H0 lands

### Track A (spine) — make the wedge demonstrable

- [ ] **H1.A1 — Arc-2 slice 3: real signing.** Sigstore/cosign/Rekor + DSSE PAE on top of the
  unsigned DSSE certificate export we shipped. Turns `certify --format dsse` into an externally
  verifiable artifact. *Why:* the wedge's whole pitch is "shareable, verifiable certificate";
  unsigned bytes don't deliver that. Self-contained. *Size:* M. Needs brainstorm + spec.
- [ ] **H1.A2 — Unblock §2E REPLICATED on a real 2nd cohort (data-blocked today).** The gating
  activity for a credible wedge is sourcing a second HM450 AML cohort with machine-readable IDH
  status (or pivoting the wedge claim to data we *can* replicate). This is sourcing/curation work,
  not just code. *Size:* M–L (data-dependent). *Currently STAGED* (`replicated-second-cohort` plan).

### Track B (deepening) — the credence layer (§5 north star)

The ATTESTED ingestion slice records *resolvability typing* but builds neither scoring engine. Next:

- [ ] **H1.B1 — Proper scoring for resolvable attested claims.** Log-score (or Brier) vs. a
  community/prior baseline, scored at resolution. *Blocker:* needs a baseline source — design that
  first. *Size:* M.
- [ ] **H1.B2 — Surrogate Scoring Rules / peer-prediction for unresolvable claims.** Over the corpus
  graph as the correlation structure (the highest-leverage unexploited mechanism per the spec).
  *Size:* M–L. Depends conceptually on B1's scoring scaffolding.
- [ ] **H1.B3 — Live external feeds.** ClinVar API / trial-registry ingestion replacing the operator
  file drop (`ingest-attested` becomes a live tap). *Size:* M.
- [ ] **H1.B4 — Defeat-edge auto-wiring between contradictory attestations.** This slice leaves
  attested-event claims defeasible-*capable* but doesn't wire contradiction edges; close that.
  *Size:* S–M.

### Track C (calibration completeness — opportunistic)

- [ ] **H1.C1 — `q_anchored` Kaplan–Meier hazard curve** (deferred follow-up). *Size:* S–M.
- [ ] **H1.C2 — Real-claim `q`-resolution loop.** DEFINITIONAL FDR is validated on the *synthetic*
  model only; close the loop on at least one real claim's eventual resolution. *Size:* M, and
  partly gated on H0.1 + H1.A2 (needs real, resolvable claims).

## Horizon 2 — Layer C consolidated (the wedge as a product)

- [ ] Pick and prove **one legible wedge claim** end-to-end (AML variant engine / biomarker ledger /
  AML disease-twin per linchpin §3C) — the "prove it where you're unmatched" deliverable. Depends on
  H0.1 (reproducible), H1.A1 (signed cert), H1.A2 (replication or a replicable claim).
- [ ] Package it as the spreadable artifact: a public, signed, calibrated certificate for a claim
  that matters to a real audience.

## Horizon 3 — Layer B (engine) & Layer A (substrate): vision, not sprint scope

- [ ] **Layer B:** Phase-B autonomous hypothesizer (first slice shipped; full program deferred);
  negative corpus; red-team marketplace.
- [ ] **Layer A:** Earn-Standing API; federated / BYO-compute (`POST /inject` hook noted);
  reproducibility observatory.
- [ ] **Deferred infra** (pull in when they block a higher item, not before): Python/R hash parity
  (needs an R serializer); `ROBUSTLY_BLAMED` wiring (enum reserved, unwired); schema→TypeScript
  codegen / API narrowing (audit Tier-C); 3D latent-space topology viewer (gated on corpus scale).

## Explicitly NOT building now (per build-path §3 — keep parked)

Scaled infrastructure (Layer-A endgame), measurement-theory / morphospace machinery (validate from
foundations, don't build), auth / multi-tenant / federation beyond what the wedge needs, v1.2 PyPI
publish.

---

## Recommended critical path (Path α)

```
H0.1 reproducible kernel proof  ──▶  H1.A1 real signing  ──▶  H1.A2 real 2nd-cohort / replicable claim  ──▶  H2 wedge claim shipped
        (foundation)                  (verifiable cert)         (data sourcing — start now, long lead)        (the deliverable)

        └─ parallel deepening when capacity allows: H1.B1→B2 credence engines, H1.B4 defeat wiring, H1.C calibration completeness
```

**Immediate next action:** H0.1 (synthetic offline pipeline proof) — it's small, it's the foundation
everything cites, and the spot-verification proved the gate is currently not reproducible offline.
Pinning the *real* Phase-A `@2` data into a fresh-checkout-runnable artifact is the separate H0.1b
residual. Then confirm the α-vs-β fork before committing the H1 sprint order. Each H1+ slice gets its own brainstorm → spec → plan →
subagent-driven build, the same loop that shipped the calibration and ATTESTED slices.
