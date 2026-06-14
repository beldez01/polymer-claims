# §2E — Tiered independence: REPRODUCED / REPLICATED

> **Design spec, 2026-06-14.** Phase-2 north-star arc 1, item §2E (the one product decision flagged in
> `docs/superpowers/2026-06-13-overnight-deferred-analysis.md`). Resolves "what does *independent* mean
> for LICENSED" by splitting the single licensed standing into two tiers, and lets the gold tier do what
> the current air-gap cannot: **multiply two genuinely-independent e-values**.
>
> Rhythm: brainstorm (this spec) → `superpowers:writing-plans` → `superpowers:subagent-driven-development`
> → merge `--no-ff` → update `CONTINUE.md` + memory.

## Problem

The system's core claim is: *LICENSED means two independent implementations agreed that a real,
fully-pinned analysis beat a pre-registered criterion.* Today "independent" is **operator-asserted and
reproducibility-grade only**:

- `adapter_registry.adapters_independent(a, b)` (`protocol/.../adapter_registry.py:40`) = both trusted ∧
  different `owner` ∧ different `implementation_hash` — all asserted strings.
- The methylation apparatus's two legs (`RegionMeanDiffAdapter`, `RegionLmCoefAdapter`,
  `src/polymer_claims/methyl_adapters.py`) compute the **same estimand on the same data**. They are
  **reproducibility-independent** (catch implementation bugs) but **not error-independent** (they share
  the data, the cohort, the batch, the biology).
- Phase 2.1 (`evidence.py` §3.2) therefore emits exactly **one** effective e-value per claim and refuses
  to multiply: "Multiplying them would double-count evidence. Genuine e-value multiplication is
  conceptual replication (a different cohort/assay, low common-cause overlap)."

So the word *independent* is only ⅔ true: the air-gap catches bugs, not shared error. There is no way
to express — or earn — the stronger standing that real science calls replication.

## Decision

Two standings, both real, additive (decisions made in the brainstorm):

| Tier | Means | Today's air-gap |
|---|---|---|
| **REPRODUCED** | two reproducibility-independent implementations agree on one cohort | the current behavior — every existing license is this |
| **REPLICATED** | the claim was *independently reproduced on ≥2 datasets with different data* (different `dimnames_hash`), each cohort itself air-gapped, and the cohorts' e-values agree | new gold tier |

`REPLICATED ⇒ REPRODUCED` by construction (each cohort is itself air-gapped; the cohorts cross).

**The common-cause gate (decided): a different cohort is necessary and sufficient.** Independent samples
break the sample/batch/biology confounds, which is exactly what makes multiplying the two cohorts'
e-values valid. Different analysis profile / assay / owner are **recorded** (audit trail, future
tightening) but **not required**. v1 common-cause "graph" = the dataset is the single load-bearing cause
node; the rule is crisp and defensible (in the grain of the e-LOND / e-value rigor, against an arbitrary
weighted score).

**What REPLICATED unlocks:** the e-LOND test for a replicated claim uses the **product** `e₁·e₂` (a valid
e-value for the shared null `H0: Δβ ≤ θ0` under independent data), as **one** test → **one** discovery →
**one** α-budget slot. REPRODUCED keeps one effective e-value (today's rule, preserved) — no
multiplication for same-cohort/two-estimator evidence (they are dependent; multiplying would double-count).

## Approach (chosen: A)

Considered three; chose A.

- **A (chosen) — tier as a `Licensing` field + a threaded `replications=` map.** Additive; mirrors the
  established CES-3 `materializations=` and Phase-2.1 `evidence=` threading idiom; no new `Status`, no
  grammar-evaluator surgery, one e-LOND test.
- **B — replication pair of claims + equivalence link.** Rejected: two separate e-LOND discoveries →
  multiplying post-hoc **double-counts the α-budget**; "tier of a pair" doesn't fit the per-claim
  `Licensing`.
- **C — new `Status` values REPRODUCED/REPLICATED.** Rejected: replacing `LICENSED` ripples through every
  `== LICENSED` site (grounded extension, drift, defeat-refund, the `LICENSED ⇒ live discovery`
  invariant, the viewer `CONTRACT_VERSION`). Huge blast radius for a refinement label.

## Components

### Grammar (pure, additive — `grammar/src/polymer_grammar/`)

- `IndependenceTier(str, Enum)` = `{REPRODUCED, REPLICATED}` (new, in `licensing.py` beside `LicenseRoute`).
- `Licensing.independence_tier: IndependenceTier = IndependenceTier.REPRODUCED` — additive field with a
  back-compat default, so every existing `Licensing` reads REPRODUCED and every existing test stays
  byte-identical.
- Pure `independence_tier_of(satisfactions: tuple[Satisfaction, ...]) -> IndependenceTier`:
  `REPLICATED` iff the SATISFIED satisfactions carry **≥2 distinct `materialization.dimnames_hash`**,
  else `REPRODUCED`. (`MaterializationContext.dimnames_hash` already exists from CES-1/3.) This is the
  whole "common-cause graph" in v1 — the dataset is the cause node.

### Umbrella (impure — `src/polymer_claims/`)

- **2nd synthetic cohort fixture** — a second SE-Contract (`contracts/epicv2_casectrl_demo_b` or similar),
  clearly labeled **synthetic**, with an independent planted +Δβ on the same signal region and a distinct
  `dimnames_hash`. Built by the existing deterministic no-RNG fixture generator. Same honesty posture as
  CES-2's first cohort (the BENCHMARKED tier is *exercised, not earned* — carried caveat).
- `replication_map(corpus, *, profiles, ...) -> dict[str, ReplicationEvidence]` — for a claim that
  **declares a replication cohort** (see "How a claim declares replication" below), air-gap the two
  methyl adapters on cohort B, and only if they **agree ∧ SATISFIED** return that cohort's
  `Satisfaction` (its own `MaterializationContext` with cohort-B `dimnames_hash`) + its e-value `e₂`. If
  B disagrees or is unsatisfied → no entry (claim stays REPRODUCED). Impure (reads the contract), like
  `evidence_map` / `materialization_map`.
- `evidence_map` extension — when a claim has a replication entry with a **distinct** `dimnames_hash`,
  return the **product** `e₁·e₂`; otherwise unchanged (one e-value). The validity guard (distinct cohort)
  lives here next to the e-value math.

### Protocol (pure — `protocol/src/polymer_protocol/verify.py`)

- `verify_stage(... , replications: dict[str, ReplicationEvidence] | None = None)` and the matching
  `run_cycle(replications=None)` — additive, default `None` → **byte-identical** to today.
- In the LICENSED branch (after the air-gap gate passes, where `Licensing(route=SEVERE_TEST,
  satisfactions=(ev.satisfaction,))` is minted at `verify.py:179`): if a replication entry exists for
  this claim and its `dimnames_hash` differs from the primary satisfaction's, build
  `satisfactions = (ev.satisfaction, *replication_satisfactions)` and set
  `independence_tier = independence_tier_of(satisfactions)` (→ REPLICATED). The product e-value is already
  carried into the e-LOND test via the existing `evidence=` threading (umbrella supplies `e₁·e₂`).
- The MDL / representation-revision branch and the REJECTED / PENDING branches are untouched.

### Viewer / live node — **out of scope (deferred follow-ups)**

The tier is a `Licensing` field, not a node `status`, so the topology DTO, `CONTRACT_VERSION`, and the
status color map are **untouched**. Tracked follow-ups: (1) a REPLICATED badge on licensed nodes; (2)
wiring `replication_map` into `NodeRunner.tick` (mirrors CES-4) so REPLICATED appears in a live `serve`
run.

## How a claim declares replication

The primary claim is the existing `region_delta_beta_claim` bound to cohort A. Replication is declared
**umbrella-side** (where the impurity already lives) as a **side map keyed by claim id** — chosen to
match `replications=` being `dict[str, ReplicationEvidence]` keyed by claim id, consistent with CES-3's
`materializations=` and Phase-2.1's `evidence=`. A small umbrella binding maps a claim id to its
**replication cohort ref** (cohort B's SE-Contract); `replication_map` consumes that binding, air-gaps
cohort B, and produces the finished map. The grammar/protocol stay ignorant of cohort B until verify
receives the pre-computed `replications=` map — identical to how CES-2/3 keep the methyl impurity
umbrella-side and hand the pure core a finished map.

## Invariants preserved

- grammar + protocol **pure + numpy-free**; the new umbrella code (`replication_map`, the 2nd-cohort
  reader) imports numpy only behind the existing non-re-exported `methyl_adapters` seam → base import
  stays numpy-free.
- **Corpus = 4 collections** — the tier rides on the existing `Licensing` (no new collection, no new IR
  entity); `replications=` is an ephemeral threaded arg, never persisted (like `evidence=` /
  `materializations=`).
- **One e-LOND test per claim per lifetime** (the audit-critical invariant) — REPLICATED supplies a
  *different value* (the product) for the **same single** test, not a second test. No double-count.
- **Back-compat:** `replications=None` ⇒ byte-identical; `independence_tier` defaults REPRODUCED on every
  existing `Licensing`.
- **`LICENSED ⇒ a live e-LOND discovery`** unchanged — the product e-value still goes through the one
  e-LOND gate.

## Acceptance criteria

1. A claim replicated across cohort A + cohort B (distinct synthetic `dimnames_hash`) licenses at
   **REPLICATED**, recording ≥2 satisfactions with distinct dataset addresses, with the e-LOND discovery
   earned on the **product** `e₁·e₂`.
2. The existing single-cohort methylation demo (CES-2) still licenses at **REPRODUCED** — unchanged.
3. A same-cohort pair (same `dimnames_hash`) does **not** multiply and stays REPRODUCED (the validity
   guard bites).
4. A replication cohort that **disagrees or is unsatisfied** confers no replication — the claim stays
   REPRODUCED (honest: REPLICATED requires each cohort independently air-gapped + agreeing).
5. `run_cycle(replications=None)` is byte-identical to today; all existing grammar/protocol/umbrella tests
   stay green; `scripts/check-all.sh` ALL GREEN.
6. grammar/protocol stay pure + numpy-free; Corpus = 4; one e-LOND test per claim.

## Out of scope (tracked)

- Viewer REPLICATED badge; live-node (`NodeRunner`) `replication_map` wiring.
- Byte-derived `implementation_hash` + credential provenance on `Satisfaction` (roadmap 1c — the *other*
  independence-hardening thread; orthogonal to the tier).
- Real public-data cohorts (the synthetic-betas caveat carries forward unchanged; the gold tier is
  *exercised, not earned* until a real 2nd cohort is swapped in on the identical `load_contract` seam).
- A weighted multi-axis common-cause score; >2-cohort meta-analytic combination; per-assay technical
  common-cause beyond the dataset node.

## Anchored file map (for the plan)

- `grammar/src/polymer_grammar/licensing.py` — `IndependenceTier`, `Licensing.independence_tier`,
  `independence_tier_of`.
- `src/polymer_claims/methyl_adapters.py`, `evidence.py`, `contracts/`,
  `analysis_profile.py`/`profiles.py` — 2nd synthetic cohort fixture, `replication_map`, product e-value.
- `protocol/src/polymer_protocol/verify.py` (the LICENSED branch ~`:166–223`), `cycle.py` (`run_cycle`
  signature) — thread `replications=`, append satisfactions, stamp the tier.
- Reference inputs: `docs/specs/2026-06-12-phase-2-1-evalue-fdr-verify-design.md` (§3.2 one-e-value
  rationale), `docs/specs/2026-06-12-ces-3-content-address-completeness-design.md` (the
  `materializations=` threading precedent), `docs/vision/2026-06-12-phase-2-north-star.md` (§2E).
