# Next phase — the real-data swap (from *exercised* to *earned*)

**Date:** 2026-06-15 · **Status:** readiness brief (blocked on one external input — a dataset)
**Reconciles:** `ARCHITECTURE_CURRENT.md`, `CONTINUE.md`, the deferred-analysis menu (item 6).

---

## The recommendation, in one line

**Swap the synthetic methylation betas for a real public cohort.** It is the single highest-leverage
move available: it converts the system's central proof — "a claim licenses on a real, independently
recomputed, content-addressed analysis that beats a criterion" — from *exercised* to **earned**, which
is the whole thesis. Every other open item is polish or a parallel arc by comparison.

## Why this, why now

- **It closes the #1 standing caveat.** Every doc carries the same honesty note: the methylation tier
  licenses on a *computed* region-Δβ from two independent legs, but **over synthetic betas**, so the
  recomputable-public tier is *exercised, not earned*. Real data is the one thing that retires it.
- **The swap is designed-in, not a rebuild.** Data enters through the content-addressed SE-Contract
  seam (DRS-shaped, keyed by `dimnames_hash`); the apparatus is a content-addressed `AnalysisProfile`
  (`profile_hash`); the two independent legs and the drift daemon already exist. The load path was
  built so a real cohort is an *identical `load_contract` seam* — point it at real betas and the rest
  runs unchanged.
- **It's the keystone for the next arc.** The standards skin (DRS / RO-Crate / in-toto attestation)
  is far more compelling once there are *real* runs to address and attest. Real data first, standards
  skin second.
- **The rigor core is ready for it.** Phases 2.1–2.4 + §2E + reinstatement + n-DMPs all shipped: the
  e-value/e-LOND gate, defeat-as-update with refund, drift-reopen, REPRODUCED/REPLICATED tiers, and a
  second reduction (n-DMP count) are live. The machine is built; it needs real input.

## What this phase delivers (acceptance)

1. A **real public methylation cohort** licenses a region-Δβ (and the n-DMP count) at **REPRODUCED**,
   on values **computed from real betas** by the two independent legs, beating the stated criterion.
2. The license records its **full content-address** — real dataset `dimnames_hash` + apparatus
   `profile_hash` + `semantic_run_id` — and survives a drift check.
3. The **synthetic-betas caveat is retired** for that tier; `q` (the false-license rate) is reported
   on real data.
4. **Honest failure is an acceptable outcome.** If a region does *not* clear the criterion on real
   data, the gate correctly **withholds** the license — that is the system working, reported plainly,
   not a failure of the phase.

## The one thing blocking it — your call

This needs **a specific public dataset**, which is yours to choose (I won't fabricate a "real"
fixture — that would corrupt the integrity thesis). To unblock, pick a cohort meeting roughly:

- **Platform:** Illumina EPIC / EPICv2 (matches the `epicv2` apparatus profile), case/control.
- **Access:** processed beta matrix (or IDATs we can process) publicly downloadable — a GEO/ENA
  accession (e.g. a `GSExxxxxx`) or equivalent, with a license permitting use.
- **Shape:** enough samples per group for the region-Δβ criterion to be powered (the synthetic demo
  used a powered fixture; real n should be comparable or larger).

**Hand me 1–2 candidate accessions** and I'll evaluate fit, then wire + validate.

## The wiring path (once a dataset is chosen)

1. **Ingest** the cohort through the SE-Contract/DRS seam → real `dimnames_hash`. (First look at the
   existing real-data path — `exec_adapters.py: real_data_seed_corpus`, `StatsPureAdapter`,
   `serve --real-data` — and reuse what transfers.)
2. **Compute** real betas → region-Δβ and the n-DMP count via the two independent legs.
3. **Gate**: confirm the legs agree (air-gap), the e-value beats the e-LOND threshold, the claim
   survives the defeat graph → an **earned** license, not an asserted one.
4. **Pin & verify**: record the full content-address; run the drift daemon to confirm a content move
   re-opens it.
5. **Retire the caveat** in `ARCHITECTURE_CURRENT.md` / `CONTINUE.md`; report `q` on the real run.

Then turn into a spec → plan → subagent-driven build (the established rhythm) — but only after the
dataset fixes the unknowns.

## The natural follow-on (REPLICATED)

One real cohort earns **REPRODUCED** (two methods, one dataset — the air-gap). A **second real cohort**
with a distinct `dimnames_hash` then earns the **REPLICATED** gold tier and licenses the *product*
e-value as one e-LOND test (§2E is already built and waiting for it). So the fully-earned arc is:
real cohort A → REPRODUCED, then real cohort B → REPLICATED. Pick A first; B is the encore.

## What this phase is NOT

- Not a rewrite — the rigor core, the seams, and the drift daemon are done.
- Not the standards skin (that's the next arc, and wants real runs to attest).
- Not federated/multi-tenant (still local-only by design).
- Not blocked on R parity or new math — purely on choosing real input.
