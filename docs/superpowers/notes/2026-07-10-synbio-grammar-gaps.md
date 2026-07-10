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
