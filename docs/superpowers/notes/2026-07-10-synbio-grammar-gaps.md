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

## GAP-2 — QuantityLeaf has no context-conditioning

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

<!-- Task 4 appends GAP-3 (interval/range values); Task 5 appends GAP-4 (defeater provisionality). -->
