# WAYLAND Phase 1 — grammar gap report

> Living record of where synthetic-biology claims strained the v1.3 IR during the Phase 1
> formalization probe. Governed by the **expansion doctrine** (Phase 0 spec §5, memory
> `feedback_ir_monotonic_expansion`): every strain is an *additive* candidate, classified by
> the scope of its fix, and no resolution ships unless every existing corpus still validates
> byte-identically. **This document is the entry gate for Phase 2.**

Each entry: constraint · current IR behavior · candidate resolution · `expansion_class` ·
purity/backward-compat cost · byte-identical proof (once resolved).

---

## GAP-1 — no home pattern for a bare reported quantity

- **Constraint.** C1 (mismatch energy) and C2 (ADAR dynamic range) are bare reported
  point-quantities. The `pattern.registry` carries only `adjusted_effect@v1` — there is no
  pattern for "a reported scalar measurement." Using `adjusted_effect` would be semantically
  false (these are not adjusted effects).
- **Current IR behavior.** `Claim.pattern` is an unresolved `PatternRef(id, version)`, not a
  registry lookup, so the claim validates with a placeholder `reported_quantity@v1` that is
  **not registered**. Structurally legal, semantically unhomed.
- **Candidate resolution.** Register a `reported_quantity` (or `point_measurement`) `Pattern`
  with its `estimand="reported_scalar"`, `null_model`, `scale`, `invariance_group`, and ≥1
  `excluded_applications` (e.g. "an adjusted or model-relative effect — use adjusted_effect").
- **expansion_class:** analysis-specific (a measurement form reusable by any field), lands in
  the open `pattern.registry` — the periphery, per "domain to the periphery."
- **Cost/backward-compat.** Additive registry entry only; touches no core primitive, no
  existing claim. Byte-identical to existing corpora by construction (registry is append-only).

## GAP-2 — QuantityLeaf has no context-conditioning ✅ RESOLVED (Phase 2a, 2026-07-10)

> **Resolution shipped.** Added an optional structured `MeasurementContext`
> (`tissue`/`cell_line`/`assay`/`condition`, all optional) to `QuantityLeaf`, plus a
> `@model_serializer(mode="wrap")` that **drops `context` when None** (mirrors `capability.py:188`).
> **Byte-identity proven:** a context-less leaf serializes to the exact pre-field baseline (test
> `grammar/tests/test_leaf_context.py::test_context_less_leaf_is_byte_identical`), and the full
> grammar (582) + protocol (497) + umbrella suites stay green. C2 re-expressed to populate the
> context; its schema tripwire flipped to a passing assertion. expansion_class: **general** (core
> primitive) — this is the reusable recipe for every future general expansion. Design:
> `docs/superpowers/specs/2026-07-10-synbio-phase2-design.md` §2.
>
> Original finding retained below for the record.


- **Constraint.** C2's 277-fold dynamic range is **cell-line-specific** and degrades in other
  contexts. Synbio (and every field — "context-independent design" is a field-wide open
  frontier) needs a derived statistic to carry the context it holds in.
- **Current IR behavior.** `QuantityLeaf` carries `value`/`uncertainty`/`unit`/`formula`/
  `dimension` but **no context field**. The context is unrepresentable; it currently survives
  only as free-text in the title/provenance. Tripwire: `test_claims_c2::test_c2_context_conditioning_gap`
  (xfail, strict).
- **Candidate resolution (weigh in Phase 2).** (a) an optional `context: str | None` on
  `QuantityLeaf`; or (b) a structured `MeasurementContext` model (cell line / assay / temperature).
  (b) is richer but heavier.
- **expansion_class:** **general** (helps every field), so it lands in the **core primitive** —
  strongest backward-compat obligation.
- **Cost/backward-compat.** Touches a core `Leaf` variant. An optional field defaulting to
  None is additive and should keep existing corpora byte-identical (must be *proven*: run the
  methyl/pharmaco/immuno suites + a serialization byte-diff before shipping).

## GAP-3 — no interval / range value

- **Constraint.** C3 (CAR threshold) is honestly a range spanning two decades (~10²–10⁴/cell):
  killing ~10², full activation ~10⁴. C4 (endosomal escape) is 1–5%. A single `value` plus a
  *symmetric* `uncertainty` cannot represent an asymmetric, multi-decade range without lying.
- **Current IR behavior.** `QuantityLeaf` offers only `value` + symmetric `uncertainty`. The
  probe records the representative point and sets `uncertainty=None` (refusing a fake bar); the
  range is lost. Tripwire: `test_claims_intervals::test_c3_interval_gap` (xfail, strict).
- **Candidate resolution (weigh in Phase 2).** (a) an additive `IntervalLeaf` variant in the
  `Leaf` sum type (`low`, `high`, optional `scale`); or (b) optional `low`/`high` on
  `QuantityLeaf`. (a) is cleaner (keeps `QuantityLeaf` a point); (b) is smaller.
- **expansion_class:** **general** (every field has ranges), core primitive.
- **Cost/backward-compat.** (a) adds a `Leaf` union member — additive, but the discriminated
  union and every exhaustive leaf-kind switch must be checked. (b) adds two optional fields.
  Either way: prove byte-identical against existing corpora before shipping.

## GAP-4 — reported defeaters must be provisional (a wiring constraint, not a missing field)

- **Constraint.** C5 (the affinity–discrimination law) is the claim that defeats the SNV-sensing
  lane. `defeat.py` confirms defeat is a corpus-level edge graph over claim *ids* — leaf-type-
  agnostic — so a `PropositionLeaf` law defeating another claim is expressible today.
- **The finding.** `effective_defeats` makes an attack stand whenever the target does not
  strength-dominate the source; a reported claim with `strength=None` is **never** dominated, so
  an unlicensed literature prior could knock out a LICENSED computed claim — violating "standing
  only through the kernel."
- **Resolution (decided, Phase 0 spec §2b).** Reported-stratum (`LITERATURE_EXTRACTED`) claims
  may author only `provisional=True` defeat/support edges (inert until the source itself gains
  standing) and may serve as L1 `incompatible_with` context. Precedent: `bridge_proposer`
  already coerces untrusted proposal-supplied edges to provisional (the C1 security fix).
- **expansion_class:** none — no IR change. This is a **Phase 2 wiring rule** for the
  `sense_and_kill` defeat construction, recorded here so it is not forgotten.
- **Also noted (extends GAP-1):** a mechanistic *law* likewise has no home pattern; C5 uses a
  placeholder `mechanistic_law@v1`. Fold into the GAP-1 registry work (a `mechanistic_law` /
  `principle` pattern with its own excluded_applications).

---

## Summary (entry gate for Phase 2)

| Gap | Class | Lands in | Ships when |
|---|---|---|---|
| GAP-1 reported-quantity / law patterns | analysis | open `pattern.registry` | Phase 2 (cheap, additive) |
| GAP-2 context-conditioning | **general** | core `QuantityLeaf` | Phase 2, byte-identical proof required |
| GAP-3 interval/range | **general** | core `Leaf` (new variant or fields) | Phase 2, byte-identical proof required |
| GAP-4 reported-defeater provisionality | — (wiring) | `sense_and_kill` construction | Phase 2 |

**Yield verdict:** all five Tier-1/Tier-2 claims formalized and validated through the real
grammar with no core change; the two *general* gaps (context, interval) are the highest-value
finds — they compound across every field, exactly the doctrine's intended payoff.

---

## Ramp gaps (2026-07-11, GAP-5+) — the manifest-ingestion harvest

Source: `aggregate_gaps` over the five reviewed chapter manifests
(`data/synbio_compendia/manifests/plm-{02,03,06,07,08}-*.json`, 39 buildable claims). **11
canonical gaps, none resolved this session** — every one is core-primitive-adjacent and
byte-identity-gated, so all are *logged, not patched* (per the ramp's Global Constraints:
W3 ships no `Leaf`/`StrengthVector` change). Numbering continues from GAP-4.

### GAP-5 [general] — floor/threshold vs point-measurement
- **constraint:** a value stated as a floor/threshold (e.g. CD19 <~2,000 molecules/cell *below which* response drops) is stored identically to a directly measured point.
- **candidate:** optional `value_relation` enum (`floor|ceiling|point|range`) on `QuantityLeaf`, default `point` for byte-identity.
- **RESOLVED (2026-07-12):** `QuantityLeaf.low`/`high` (additive, byte-identical when boundless). `sb-plm02-cd19-density-floor` now carries `low=2000` (open above); `schema_fit` → clean. See `docs/superpowers/specs/2026-07-12-gap3-interval-bounds-design.md`.

### GAP-6 [general] — multi-study range collapsed to symmetric error
- **constraint:** a leak range ("1–3%") jointly attributed to two independent systems, forced into `value ± symmetric uncertainty`, discarding provenance and asymmetry.
- **candidate:** optional `value_range: [low, high]` on the leaf.
- **RESOLVED (2026-07-12):** `QuantityLeaf.low`/`high`. `sb-plm03-adar-leak-floor` now `low=0.01, high=0.03` (fabricated symmetric `uncertainty` dropped); `schema_fit` → clean.

### GAP-7 [domain] — no basis for an analytic constant
- **constraint:** an information-theoretic constant (2 bits = log2(4)) is neither instrument-measured (FUNDAMENTAL) nor a data ratio (DERIVED); forced into FUNDAMENTAL with `unit="bits"`.
- **candidate:** a third `measurement_basis` value (`ANALYTIC`).

### GAP-8 [subject] — no gene/locus context sub-key
- **constraint:** a "77% of TET2 lesions are truncating" figure is a property of the *locus*, but `MeasurementContext` has only tissue/cell_line/assay/condition; gene identity leaks into free-text `condition`.
- **candidate:** optional `gene`/`target_locus` sub-key on `MeasurementContext`.

### GAP-9 [domain] — order-of-magnitude (log-scale) range
- **constraint:** a 10–100× span forced to an arithmetic midpoint (55±45), misrepresenting a multiplicative claim. **candidate:** `value_min`/`value_max` or log-scale uncertainty.
- **RESOLVED (2026-07-12):** `QuantityLeaf.low`/`high`. `sb-plm06-transcriptional-gate-dynamic-range` now `low=10, high=100` (`value=10`, fake `55±45` gone); `schema_fit` → clean. The log/geometric-scale marker is **DEFERRED** (YAGNI — no consumer computes inside the interval), tripwire-armed: `test_gap9_logscale_marker_deferred`.

### GAP-10 [domain] — discrete integer range
- **constraint:** "3–4 gate layers" forced to continuous `3.5±0.5` (a circuit cannot have 3.5 layers). **candidate:** inclusive integer range `[3,4]`.
- **RESOLVED (2026-07-12):** `QuantityLeaf.low`/`high`. `sb-plm06-cascade-depth-ceiling` now `low=3, high=4` (`value=3`, fake `3.5±0.5` gone); `schema_fit` → clean. The discrete-integer marker is **DEFERRED** (YAGNI — no consumer interpolates), tripwire-armed: `test_gap10_discrete_marker_deferred`.

### GAP-11 [domain] — pooled prevalence needs per-indication stratification
- **constraint:** "~10–20% HLA-LOH across many solid tumors" collapses to one figure with no tumor-type context. **candidate:** per-tumor-type `context.condition` once a breakdown exists.
- **PARTIAL (2026-07-12):** the range facet is now carried honestly — `sb-plm06-hla-loh-prevalence` uses `low=10, high=20` (fabricated `15±5` dropped) via the GAP-3 low/high fields. GAP-11 stays **OPEN** for its defining residue: the pooled figure still lacks the per-tumor-type stratification (a `context` refinement, not an interval one).

### GAP-12 [general] — one-sided bound (floor) direction
- **constraint:** ">10 weeks B-cell depletion" is a one-sided floor; `QuantityLeaf` has only a point `value` + symmetric `uncertainty`, so it collapses to `value=10` indistinguishable from an exact estimate.
- **candidate:** optional `bound: Literal['exact','floor','ceiling']` (or fold into the interval work), default `exact` for byte-identity. **Touches the core Leaf — standard byte-identity proof required.**
- **RESOLVED (2026-07-12):** folded into the interval work — an open-ended `QuantityLeaf.low` *is* a floor. `sb-plm07-vivovec-bcell-depletion` now `low=10` (open above); `schema_fit` → clean. No separate `bound` enum needed.

### GAP-13 [analysis] — measured-endpoint ≠ clinically-relevant endpoint
- **constraint:** a ~90% figure the chapter flags as *reporter/cargo delivery, not durable editing* has no structured field to encode the endpoint-type mismatch; the caveat survives only as prose. **candidate:** `endpoint_type`/`validity_caveat` field.

### GAP-14 [general] — composite/vector quantity
- **constraint:** a joint 4-component LNP molar ratio (50:10:38.5:1.5) is load-bearing, but the leaf carries one scalar; only the PEG term survives structured. **candidate:** a composite/vector quantity leaf (list of named value+unit pairs).

### GAP-15 [domain] — structured categorical mapping
- **constraint:** a 3-way SORT-lipid→organ mapping (cationic→lung, anionic→spleen, neutral→liver) flattened into one `PropositionLeaf` `data` string. **candidate:** a structured list of (perturbation, outcome) tuples, or three linked propositions sharing a warrant.

### Harvest verdict + two aggregator findings

- **The interval/range/floor/bound family — RETIRED 2026-07-12 (GAP-3 slice).** GAP-5, GAP-6,
  GAP-9, GAP-10, GAP-12 (5 of 11) were all facets of one strain: **the leaf cannot hold a range or a
  bound-direction.** That was precisely the pre-existing **GAP-3 (interval/range)**. The corpus demanded
  it, so it was un-deferred and shipped: `QuantityLeaf.low`/`high` (additive, optional, byte-identical
  when boundless; open ends encode floor/ceiling; `_bound_discipline` enforces ordering/containment/
  spread-exclusivity). All five entries re-expressed with honest bounds; `schema_fit` → clean. Two
  domain refinements (GAP-9 log-scale, GAP-10 discrete-integer) are DEFERRED with armed tripwires.
  **Open gaps remaining (6):** GAP-7 (analytic measurement basis), GAP-8 (gene/locus context sub-key),
  GAP-11 (per-tumor stratification — its range facet is now expressible via low/high, but the
  stratification residue keeps it open), GAP-13 (endpoint-type), GAP-14 (composite/vector quantity),
  GAP-15 (structured categorical mapping).
- **`aggregate_gaps` dedup is too literal (engine gap).** It keys on the normalized
  `(expansion_class, constraint)` *prose*, so the five interval-family gaps — phrased differently
  by five independent extractors — did **not** collapse; 11 raw → 11 canonical (zero merge). And
  it renumbers from 5 without reconciling against the canonical GAP-1..4, so interval strains
  surface as new GAP-9/10/12 rather than as instances of GAP-3. The "fixed list" is only as fixed
  as the wording. *Candidate:* dedup on a small controlled `gap_kind` tag (extractor-assigned)
  rather than free-text constraint, and seed the aggregator with the existing GAP-1..4 keys.
  (Both logged, non-blocking — the aggregator shipped to spec; this is a precision follow-up.)
