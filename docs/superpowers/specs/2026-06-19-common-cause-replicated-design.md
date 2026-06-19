# Common-Cause §E — Earn REPLICATED on Evidenced Low Shared-Cause Overlap — Design Spec

> **Date:** 2026-06-19 · **Status:** approved (design), pre-implementation
> **Scope:** pure-code grammar + umbrella replication + minimal viewer + tests (no external data; fully CI-gated)
> **Roadmap:** north-star §E ("define 'independent' rigorously" — the common-cause DAG) · autonomous-hypothesis-loop §5b (implementation-independence condition) · §2E tiered independence
> **Predecessor machinery:** §2E `IndependenceTier`/`independence_tier_of` (`grammar/licensing.py:57-77`), the REPLICATED e-value product (`src/polymer_claims/replication.py:110`), the adapter trust registry (`protocol/adapter_registry.py`), and Phase D slice 2's `grammar/shared_cause.py` (the first shared-cause edge).

## 1. Goal

Make the **REPLICATED** tier — the only tier that licenses **multiplying two cohorts' e-values** (`e₁·e₂` as one e-LOND test) — require *evidenced low shared-cause overlap* between the runs, not merely *distinct `dimnames_hash`*.

Today `independence_tier_of` (`licensing.py:69-77`) returns REPLICATED iff ≥2 satisfactions carry distinct `dimnames_hash`. That is **direct replication** (different data) but says nothing about whether the two runs share a manifest, a normalization convention, a reference build, a library, or a prior — and **correlated error is exactly how "two beats one" becomes a lie** (the §5b / Ioannidis failure mode). Multiplying `e₁·e₂` across runs whose errors are correlated overstates the evidence.

This slice makes the §5b independence condition **derived and evidenced**, symmetric to how Phase D slice 2 made the §5a hypothesis-source condition derived:
1. Each run declares a structured **shared-cause factor set** (what its result causally depends on).
2. A pure **graded overlap** (Jaccard) over two runs' factor sets, with a threshold τ.
3. REPLICATED now requires distinct `dimnames_hash` **AND** low pairwise overlap (`< τ`); else REPRODUCED.
4. The umbrella **gates the e-value multiplication on the same predicate**, so the tier label and the evidence can never disagree.

This is **Reichenbach screening-off in its first concrete form** (few shared causes ⇒ residual error-independence) and §E's **second concrete edge** (slice 2 was the first). The full per-implementation causal **DAG** and the formal probability derivation stay deferred.

## 2. Decisions (locked)

| Decision | Resolution |
|---|---|
| What the overlap gates | **The REPLICATED tier** (hence the e-value product). High overlap → REPRODUCED (single e-value, no multiplication). |
| Where the factor set lives | **`MaterializationContext.shared_cause_factors`** — the per-run identity §2E already keys off (`dimnames_hash`). Captures both data- and method-side causes (manifest/cohort + library/prior). NOT `AdapterCredential` (the gated privilege is cross-*run*, not per-adapter). |
| Overlap measure | **Jaccard** `|A∩B| / |A∪B|` over factor-tag sets; `0.0` for disjoint. |
| Threshold | **`SHARED_CAUSE_TAU = 0.5`** — pairwise overlap `< τ` ⇒ error-independent. Named, tunable. |
| Trust model | **Operator-asserted factors** (same as `dimnames_hash`/`owner`/`implementation_hash` today); the *gate* is byte-mechanical, the *population* is asserted. |
| Opt-in / byte-identity | **Presence of `shared_cause_factors` on the relevant satisfactions.** If ANY distinct-cohort satisfaction lacks factors → "can't assess" → fall back to today's behavior (REPLICATED on distinct dimnames, e-values multiplied). Byte-identical when off. |
| Visibility | Record the assessed max pairwise overlap on **`Licensing.shared_cause_overlap: float | None`**; surface in the viewer. |

## 3. No import cycle (load-bearing constraint)

`licensing.py` already imports `SeverityProvenance` from `shared_cause.py` (slice 2), so `licensing → shared_cause` is the established one-way edge. Therefore:
- **`shared_cause.py`** gains only **factor-set-level** primitives that operate on plain `tuple[str, ...]` (no `licensing` import): `shared_cause_jaccard`, `SHARED_CAUSE_TAU`.
- **`licensing.py`** owns everything that touches `Satisfaction`/`MaterializationContext`: the new field, `cohorts_error_independent`, `max_shared_cause_overlap`, and the overlap-aware `independence_tier_of`. It calls `shared_cause_jaccard`.

This keeps `shared_cause.py → strength` only and `licensing → shared_cause → strength` acyclic (verified in Task 1).

## 4. Grammar changes (pure, numpy-free, stdlib only)

### 4.1 `shared_cause.py` — graded factor-set overlap

- `SHARED_CAUSE_TAU: float = 0.5` — module constant; pairwise overlap `< τ` ⇒ error-independent. Documented tunable.
- `shared_cause_jaccard(a: tuple[str, ...], b: tuple[str, ...]) -> float` — `|set(a) ∩ set(b)| / |set(a) ∪ set(b)|`; returns `0.0` when the union is empty (two empty factor sets are treated as non-overlapping — they are only ever reached through the licensing layer's "absent ⇒ can't assess" guard, never here).

### 4.2 `licensing.py` — factor field, predicate, overlap-aware tier

- `MaterializationContext.shared_cause_factors: tuple[str, ...] = ()` — additive, default inert. Namespaced causal-dependency tags (e.g. `manifest:HM450`, `norm:noob`, `ref:GRCh38`, `lib:numpy-lstsq`, `prior:idh-hypermeth`). Frozen-model/tuple, content-addressable.
- `Licensing.shared_cause_overlap: float | None = None` — additive; the recorded max pairwise overlap among the distinct-cohort satisfactions (`None` when not assessed).
- `cohorts_error_independent(satisfactions: tuple[Satisfaction, ...]) -> bool | None`:
  - Consider the distinct-cohort group: satisfactions with non-None `dimnames_hash`, one representative per distinct hash.
  - If fewer than 2 distinct cohorts → `None` (not a replication question).
  - If **any** representative has empty `shared_cause_factors` → `None` (can't assess → caller falls back).
  - Else → `True` iff **every** pairwise `shared_cause_jaccard(...) < SHARED_CAUSE_TAU`, else `False`.
- `max_shared_cause_overlap(satisfactions) -> float | None` — the max pairwise Jaccard among distinct-cohort representatives that carry factors; `None` if not assessable (matches `cohorts_error_independent`'s `None` cases). Recorded on the license.
- `independence_tier_of(satisfactions)` — **same signature**, now overlap-aware:
  - `indep = cohorts_error_independent(satisfactions)`.
  - REPLICATED iff (`≥2 distinct dimnames_hash`) AND (`indep is None` → today's behavior | `indep is True`). Else REPRODUCED.
  - `indep is False` (factors present, high overlap) → **REPRODUCED** (the new gate).
  - **Byte-identity:** with no factors anywhere, `indep is None`, so REPLICATED reduces to "≥2 distinct dimnames" — identical to today.

### 4.3 Validator interaction

`Licensing._replicated_tier_needs_two_distinct_cohorts` (`licensing.py:109-119`) asserts `independence_tier == REPLICATED ⇒ independence_tier_of(sats) == REPLICATED`. Because the new `independence_tier_of` is strictly *stricter*, this invariant still holds: a hand-built REPLICATED license whose satisfactions show high overlap now correctly fails validation (you cannot claim REPLICATED when the evidence says the runs share cause). Existing §2E fixtures (distinct dimnames, no factors) are unaffected → byte-identical.

## 5. Umbrella change — gate the e-value multiplication (`src/polymer_claims/replication.py`)

`build_replication_inputs` (≈`replication.py:50-112`) currently always multiplies: `evidence[cid] = evidence[cid] * e2` (line 110). Make it consult the **same grammar predicate** on the base + replication satisfactions before multiplying:
- `indep = cohorts_error_independent((sat_base, sat_b))`.
- `indep is None` (factors absent) or `indep is True` (low overlap) → multiply (`e₁·e₂`) **exactly as today** (byte-identical when factors absent).
- `indep is False` (high overlap) → **do not multiply**; keep `e₁` (single-cohort evidence). Still record `sat_b` in `replications[cid]` (the run happened, distinct cohort) — so `independence_tier_of` sees both cohorts and correctly stamps **REPRODUCED** with `shared_cause_overlap` recorded. The label (REPRODUCED) and the evidence (un-multiplied) now agree.

Single source of truth: both the grammar tier and the umbrella multiplication consult `cohorts_error_independent`, so they cannot diverge.

## 6. Protocol change — record the overlap on the license (`protocol/verify.py`)

Where verify builds the REPLICATED-eligible `Licensing` (`verify.py:243-250`), additionally set `shared_cause_overlap=max_shared_cause_overlap(sats)`. `independence_tier=independence_tier_of(sats)` already flows (now overlap-aware) — no call-site signature change. Additive; `None` when not assessable → byte-identical.

## 7. Viewer (minimal)

Surface `shared_cause_overlap` (and/or a "REPLICATED-withheld-shared-cause" reading) on `TopologyExport` + node, mirroring the existing `independence_tier` pill, so a REPRODUCED-despite-two-cohorts license is legible. Contract version stays "1.0" (additive optional field; viewer reads `?? null`). Light — passthrough + a small display, like slice 2.

## 8. What this does NOT change (invariants)

- **Corpus = exactly 4 collections.** No new collection; factors ride `MaterializationContext`, overlap rides `Licensing`.
- **grammar stays pure + numpy-free.** Jaccard is stdlib set arithmetic; no `polymer_formalclaim`; `licensing → shared_cause → strength` stays acyclic.
- **Additive/opt-in, byte-identical when off.** No factors anywhere ⇒ `cohorts_error_independent` is `None` ⇒ REPLICATED + multiplication behave exactly as today. The full §2E suite stays green unchanged.
- **§2E orthogonality preserved.** `independence_tier` still answers "did agreeing legs span ≥2 cohorts?"; the new overlap *refines when that earns REPLICATED*. `severity_provenance` (slice 2, hypothesis-source) is a distinct axis and untouched.
- **One e-test per claim lifetime.** Unchanged. This slice changes whether two e-values may be *multiplied into one* test, not how many tests exist.

## 9. Success criteria (what the tests must prove)

1. **High overlap denies REPLICATED:** two satisfactions, distinct `dimnames_hash`, factor sets with Jaccard `≥ 0.5` → `independence_tier_of` returns REPRODUCED; `cohorts_error_independent` returns `False`.
2. **Low overlap earns REPLICATED:** distinct cohorts, Jaccard `< 0.5` → REPLICATED; `cohorts_error_independent` returns `True`.
3. **Multiplication gated:** `build_replication_inputs` multiplies `e₁·e₂` on low-overlap (or factor-absent) inputs and keeps a single `e₁` on high-overlap inputs; `replications[cid]` still records `sat_b` in both cases.
4. **Byte-identical when off:** no `shared_cause_factors` anywhere → `independence_tier_of` and `build_replication_inputs` are identical to today (existing §2E suite green + a golden equality test on a distinct-cohort, factor-less case: REPLICATED + multiplied).
5. **Overlap recorded:** a licensed claim records `Licensing.shared_cause_overlap` = the assessed max pairwise Jaccard (`None` when not assessable); viewer node carries it.
6. **Validator holds:** a hand-built REPLICATED license with high-overlap satisfactions fails `_replicated_tier_needs_two_distinct_cohorts`; a factor-less distinct-cohort one passes (as today).
7. **Invariants:** Corpus still 4; grammar isolation + numpy-free import preserved; `severity_provenance` (slice 2) behavior unchanged.

## 10. Out of scope (later slices)

- **The real per-implementation causal DAG** — factors with causal structure + transitive shared causes, instead of a flat tag set. This slice is the flat first form; the DAG is the §E endgame.
- **Formal Reichenbach screening-off probability derivation** — turning "low overlap" into an evidenced *probability* of error-independence (vs the current threshold proxy).
- **Byte-derived / credential-backed factors** — population is operator-asserted here, exactly like `implementation_hash`; hardening it is the same deferred class.
- **Per-adapter factor sets + gating the base `adapters_independent` registry check** — this slice gates the REPLICATED privilege (where multiplication inflates evidence), not the per-license adapter gate; refining `adapters_independent` to be overlap-graded is a separate later slice.
- **Weighted / non-Jaccard overlap, or a learned τ** — fixed Jaccard + constant τ here.

## 11. Open implementation details (for the plan)

- Exact `replication.py` shape: confirm the base satisfaction (`sat_base`) available at the multiplication site and that skipping the product while still appending `sat_b` produces the intended REPRODUCED+single-e outcome end-to-end (a `run_cycle`/node test).
- Confirm `independence_tier_of`'s "distinct-cohort representative" selection is deterministic (sorted by `dimnames_hash`) so `max_shared_cause_overlap` and the tier agree on the same pair set.
- Whether any existing call site passes a hand-built REPLICATED `Licensing` with factors that would now fail validation (search `independence_tier=IndependenceTier.REPLICATED` across tests) — update only genuine high-overlap fixtures, if any.
- `SHARED_CAUSE_TAU` value confirmation against a realistic factor-tag vocabulary (Task 1) — document as tunable.
