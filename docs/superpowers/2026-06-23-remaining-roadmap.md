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

> **STATUS UPDATE (2026-06-25) — reconciled after H0.1 / H0.1b / H1.A1 shipped.** The
> reproducibility gap above is **closed in code**: H0.1 shipped `polymer-claims verify-kernel`
> (synthetic, offline, CI-guarded — pipeline integrity), and **H0.1b shipped
> `polymer-claims verify-kernel --real`** (merged to `main` `32670bb`) — a content-address-parity
> gate that rebuilds the real `se:tcga_laml_idh@2` proof from three pinned inputs and re-runs the
> real n-DMP gate to `LICENSED @ REPRODUCED`. The *real* proof is now re-runnable from a fresh
> checkout once the (gitignored) inputs are supplied/fetched. **Real pins captured + verified
> (2026-06-25):** the two-mode bootstrap was run — the new builder reproduced the trusted `@2`
> addresses *exactly* (clean diff, no self-fulfilling parity), the real pins are committed, and
> `verify-kernel --real` returns **`LICENSED @ REPRODUCED`** end-to-end (n_probes=378,894,
> n_dmps=115,405, e-value=∞, IDH-mut n=36). **H0.1b is fully closed.** **H1.A1 (real signing)** also shipped
> (local ed25519 DSSE sign/verify + `keygen`/`verify-dsse` + `--key`); the Sigstore/cosign/**Rekor**
> transparency-log layer remains open (see H1.A1 below).

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

- [x] **H0.1 — Offline-reproducible kernel *pipeline* proof (synthetic).** ✅ SHIPPED. Spec'd + planned
  (`specs/2026-06-23-offline-kernel-proof-design.md`, `plans/2026-06-23-offline-kernel-proof.md`).
  A fully synthetic, deterministic HM450-shaped fixture run through the **real** n-DMP gate, guarded
  by a committed test and a `verify-kernel` CLI, plus a hardened retrieval runbook. *Why:* gives a
  fresh checkout a deterministic, offline `LICENSED @ REPRODUCED` proof of the gate pipeline — closes
  the "nothing reproduces offline" gap. *Note:* this proves **pipeline integrity, not the real
  biology** (nothing real committed). *Size:* S–M.
- [x] **H0.1b — Real `@2` data: retrievable, fresh-checkout-runnable artifact.** ✅ SHIPPED + VERIFIED (merged `32670bb`; real pins captured 2026-06-25) — `verify-kernel --real` rebuilds `@2` from three pinned inputs, asserts byte-level content-address parity + the real gate result, and returns `LICENSED @ REPRODUCED` against the committed real pins (the bootstrap diff was clean — no self-fulfilling parity). **Acceptance criterion #5 satisfied; no residual.** Spec/plan: `docs/superpowers/{specs/2026-06-25-h01b-real-kernel-parity-design,plans/2026-06-25-h01b-real-kernel-parity}.md`. The *real* proof
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

- [~] **H1.A1 — Arc-2 slice 3: real signing.** ✅ PARTIALLY SHIPPED — **local ed25519 DSSE signing**
  merged (`feat/dsse-signing`): DSSE PAE, `keygen` / `verify-dsse` subcommands, opt-in `--key` on
  `certify` + `export-attestation` (`[sign]` extra). Turns `certify --format dsse` into a locally
  verifiable signed artifact. **Still open:** the **Sigstore/cosign/Rekor transparency-log** layer
  (third-party verifiability without trusting the signer) — that's the remaining slice. *Size:* M.
  **UPDATE (2026-06-25):** the LOCAL transparency layer shipped (feat/transparency-log) — a local
  RFC-6962 Merkle inclusion log + C2SP signed checkpoint + a trust-gated, offline-verifiable Polymer
  bundle (Sigstore-INSPIRED, not wire-compatible), behind a `TransparencyLog` seam. New CLI:
  `verify-bundle`, and `--transparency-log` on `certify`/`export-attestation`. Still open: the
  NETWORKED public-Rekor backend (`--rekor-url`, reserved+erroring today) and consistency proofs —
  what add public non-repudiation + verified append-only-ness.
  **UPDATE (2026-06-26):** the networked Rekor backend is fully **designed and build-ready** but
  **intentionally TABLED** (`specs/2026-06-26-networked-rekor-backend-design.md`, status DEFERRED) —
  public non-repudiation isn't needed before there's real first-use/wedge work to anchor. Resume that
  spec via `writing-plans` when a claim is actually being shared externally. Do first-use work first.
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
  partly gated on **H0.1b** + H1.A2 (needs real, resolvable claims — H0.1's synthetic proof does not
  supply real data).

## Horizon 2 — Layer C consolidated (the wedge as a product)

- [ ] Pick and prove **one legible wedge claim** end-to-end (AML variant engine / biomarker ledger /
  AML disease-twin per linchpin §3C) — the "prove it where you're unmatched" deliverable. Depends on
  H0.1 (reproducible pipeline) and, **if the wedge cites actual TCGA-LAML `@2` numbers, on H0.1b**
  (real-data reproducibility); plus H1.A1 (signed cert) and H1.A2 (replication or a replicable claim).
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
H0.1 kernel pipeline proof  ──▶  H1.A1 signing  ──▶  H1.A2 real 2nd-cohort / replicable claim  ──▶  H2 wedge claim shipped
   ✅ SHIPPED          ✅ local ed25519 (Rekor open)    (data sourcing — start now, long lead)        (the deliverable)
        │
        └─ H0.1b ✅ real-data parity gate SHIPPED + VERIFIED (real pins committed; --real = LICENSED @ REPRODUCED)
        └─ parallel deepening when capacity allows: H1.B1→B2 credence engines, H1.B4 defeat wiring, H1.C calibration completeness
```

**Immediate next action (updated 2026-06-25):** the cheap, code-only spine is done *and verified* —
H0.1, **H0.1b (real pins captured; `verify-kernel --real` = LICENSED @ REPRODUCED)**, and the
local-signing half of H1.A1 are shipped and merged. The single remaining critical-path gate to a
demonstrable wedge is **H1.A2 — source a real 2nd HM450 cohort** with machine-readable IDH status
(long lead — start now; it's the gate to §2E REPLICATED and H2). Optional parallel code slices:
finish **H1.A1 (Sigstore/Rekor)** for third-party verifiability, and the Track-B credence engines.
Each H1+ slice gets its own brainstorm → spec → plan → subagent-driven build, the same loop that
shipped H0.1b.

---

## Vision-derived additions (2026-06-27)

Surfaced by reconciling `docs/superpowers/vision.md` against the shipped system. These are **net-new
primitives the vision names that the codebase does not yet have as first-class objects** — slotted into
the existing horizon vocabulary. **None are data-blocked** (unlike H1.A2), so they are pure-build and
can run in parallel with the wedge's cohort sourcing.

### V1 — Capability cell + Capability Registry (the spine) *(highest leverage)*

> **Scope honesty:** V1 delivers capability **description, discovery, and conformance reporting** —
> *not* closed-world enforcement. Unregistered claims still execute and license exactly as before; the
> conformance check is advisory (unwired). Enforcement (refusing non-conformant claims at the gate) is
> a deliberately separate later slice. V1 is the highest-value *non-data-blocked parallel* build — it
> does **not** outrank the wedge (H1.A2 → H2), which stays the critical path.

- [ ] **V1.1 — Formalize the capability cell.** A first-class, versioned object unifying what is today
  scattered across a claim pattern + `impl` string (`stats::mean_diff`, `methyl::region_delta_beta`,
  `n_dmps`) + execution adapters + SE-Contract + oracle dossier + agreement/licensing rule + typed
  outputs + resource limits + schema/capability versions. *Why:* it is the vision's organizing spine —
  agent-first **closed-world execution** means agents compile proposals into *registered* cells, not
  arbitrary computations. *Size:* M–L. *Rhythm:* brainstorm → spec → plan → subagent build.
- [ ] **V1.2 — Capability Registry.** Register the three existing reductions as the first cells; the
  registry is "what Polymer knows how to claim and evaluate." Pairs with the existing **adapter trust
  registry** and a future **claim registry** to form the three-registry product surface. *Size:* M.

### V2 — Menu expansion (prove generalization on ONE first, then fan out)

- [ ] **V2.0 — One genuinely new / external capability as the generalization test.** Before designing
  three more internal cells, register **one** capability that is genuinely new or backed by an
  **external adapter** (not a re-expression of an existing reduction). The point is to discover where
  the V1 abstraction does *not* fit — three internally-designed cells could merely reproduce the
  assumptions baked into the three existing reductions. What this slice teaches gates the fan-out below.
  *Size:* M.
- [ ] **V2.1 — Enrichment analysis** capability — candidate (gated on V2.0).
- [ ] **V2.2 — Fixed-protocol classifier evaluation** capability — candidate (gated on V2.0).
- [ ] **V2.3 — Feature–phenotype association** capability — candidate (gated on V2.0).

  *Discipline (vision §"Start Narrow"):* a capability is real only with schema + fixtures + typed
  outputs + comparison rule + ≥1 adapter + verifiable artifacts; expand the core IR only when ≥2
  capabilities need the same abstraction. *Size:* S–M each. (Two-group numerical = `mean_diff` ✓;
  DMP/region = `region_delta_beta`/`n_dmps` ✓.)

### V3 — Verification ladder rung 6 + explicit operational states

- [ ] **V3.1 — Temporal reproducibility as an earned tier/state.** Partly realized
  (`verify-kernel --real` pinned inputs + the drift daemon); make "rerunnable later under pinned or
  explicitly migrated infrastructure" an explicit *standing*, not just a proof script. *Size:* M.
- [ ] **V3.2 — Explicit operational states.** Add the vision's missing lifecycle states —
  **resource-exceeded**, **migrated**, **untrusted** — to the status vocabulary. *Size:* S–M.

### V4 — Claim registry product surface *(later — needs the wedge first)*

- [ ] The signed, machine-readable **claim registry** as a published surface (vs. today's in-repo
  corpus + attestation/signing). Gated on H2 (a real shareable claim worth publishing). *Size:* M–L.

> **Where these sit vs. the critical path:** the wedge (H1.A2 → H2) stays the spine. **V1** is the
> highest-leverage *parallel* build — it productizes what already exists and unblocks closed-world
> agent execution + clean menu growth, with no dependency on cohort data. Recommended pull order when
> capacity allows: **V1 → V2 → V3**, with V4 after the wedge.
