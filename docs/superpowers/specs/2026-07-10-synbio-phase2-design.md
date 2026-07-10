# WAYLAND Phase 2 — patterns, ingestion, the licensed spine, and the first core-grammar expansion: design

**Date:** 2026-07-10
**Status:** Design (Phase 2 of the Wayland program). Decomposes Phase 2 into sub-projects, and fully designs the first slice (2a). Entry gate: the Phase 1 gap report (`docs/superpowers/notes/2026-07-10-synbio-grammar-gaps.md`). Program plan: `docs/superpowers/plans/2026-07-10-synbio-claims-universe.md`; Phase 0 spec: `docs/superpowers/specs/2026-07-10-synbio-claims-universe-design.md`.
**Telos:** Turn the Phase 1 probe (reported claims that only *validate*) into a **licensed spine** — at least one synbio claim recomputed from real data through the real gate at REPRODUCED — and, along the way, perform the program's **first core-grammar expansion** under the monotonic-expansion doctrine: additive, classified, proven byte-identical. This is the doctrine's first real test on the pure core, not just the umbrella.

---

## 0. One-paragraph summary + the decomposition

Phase 2 spans several independent subsystems, so per the writing-plans scope check it is **decomposed into four sub-projects**, each with its own later spec+plan, sequenced by dependency:

- **2a — GAP-2 resolution (context-conditioning), core grammar.** Add an optional, structured `MeasurementContext` to `QuantityLeaf`, additive and **byte-identical** (drop-when-None wrap-serializer), so a derived statistic can carry the context it holds in. This is on the Durendal critical path (the topology-rejection move needs *tissue-conditioned* expression) and is the doctrine's first core-primitive expansion. **First slice — designed in full below.**
- **2b — patterns.** Register the missing patterns in the open `pattern.registry`: `reported_quantity`, `mechanistic_law` (GAP-1), and the domain `sense_and_kill` composition pattern. Additive registry entries; no core change.
- **2c — ingestion.** A reviewed markdown→claims extractor over the two compendia (structured, human-in-the-loop, provenance to primary refs), emitting `LITERATURE_EXTRACTED` reported-stratum claims at scale.
- **2d — the licensed spine.** Execution adapters over a real expression atlas (+ genome annotation), reusing the SE-Contract seam and the two-leg registry, so a **computed** claim ("RUNX1-RUNX1T1 clears the ~13 TPM floor in AML") licenses at REPRODUCED. This is Phase 2's exit gate and the "serious traction" deliverable.

**Dependency DAG:** 2a → (enables faithful expression-context claims) → 2d. 2b → 2c, 2d. 2c → 2d (bulk priors). 2a and 2b are independent and can proceed first; 2d is gated on both plus data. **Recommended order: 2a, then 2b, then 2d (with 2c in parallel once 2b lands).**

**GAP-3 (interval/range) is deliberately DEFERRED** (YAGNI): no licensed-spine claim needs it yet (thresholds are point-vs-value), and growing the `Leaf` sum type speculatively violates "no abstraction without a current caller." Its xfail tripwire stays armed until a spine claim genuinely needs a range.

---

## 1. Foundations alignment — the doctrine's first core test

| Foundation | Requirement | How 2a honors it |
|---|---|---|
| **Monotonic IR expansion** (`feedback_ir_monotonic_expansion`, Phase 0 §5) | Additive-or-nothing, proven byte-identical; general fix to the general primitive. | `MeasurementContext` is a **general-class** fix (every field has context) → lands in core `QuantityLeaf`. Optional + drop-when-None → existing corpora serialize and hash byte-identically. Proof obligation discharged in-plan (below). |
| Measurement seam (`measurement-foundation.md`) | A leaf carries no false unit; criteria invariant under admissible transforms. | `MeasurementContext` carries no unit and no value; it conditions interpretation only. It does not enter any licensing criterion. |
| Purity/isolation | grammar/protocol pure + numpy-free; Corpus stays 4. | 2a is a pure additive field on a pure model; no numpy, no Corpus change. |
| de Bruijn kernel | Standing only through the kernel. | Context is descriptive metadata; it never licenses. (Reported claims stay CONJECTURED regardless.) |
| Compute boundary | Polymer never runs the wet assay. | 2d's expression recompute runs on a real atlas the user supplies, gitignored; the wet Gate-1 stays a proposed, attestable partner experiment. |

---

## 2. Slice 2a — GAP-2 (context-conditioning), designed in full

### 2a.1 The change
Add to `QuantityLeaf` (`grammar/src/polymer_grammar/leaf.py`) one optional field:

```python
context: MeasurementContext | None = None
```

with a new pure model in the same module:

```python
class MeasurementContext(_Model):
    tissue: str | None = None        # e.g. "bone marrow" / "AML"
    cell_line: str | None = None     # e.g. the ADAR 277-fold reporter line
    assay: str | None = None         # e.g. "RNA-seq TPM", "luciferase ratio"
    condition: str | None = None     # free-form residual (temperature, timepoint)
```

**Why structured, not a bare `context: str`.** The Durendal topology-rejection move turns on *tissue-conditioned* expression (RUNX1 ubiquitous in blood, ETO silent), and the 2d spine queries "TPM **in AML**." A bare string would defer exactly the structure the spine needs and force re-structuring later. A structured model with all-optional fields is the minimal object that is still queryable. It stays general (tissue/cell_line/assay/condition are field-agnostic).

### 2a.2 Byte-identity — the load-bearing part
`_Model` is `extra="forbid", frozen=True` (`base.py:12`). Two hazards and their resolutions:

1. **JSON serialization drift.** Default pydantic dump of an existing `QuantityLeaf` would now emit `"context":null`, changing the bytes. **Resolution:** add a `@model_serializer(mode="wrap")` to `QuantityLeaf` that omits `context` when None — the exact precedent already in the codebase at `capability.py:188` (the "drop-when-None" pattern used for prior additive fields). Result: a context-less leaf serializes byte-for-byte as before.
2. **Content-hash / model-hash stability.** Frozen-model hashing and any content-addressed claim id must be unchanged for existing (context-less) claims. Because the default is `None` and every unmigrated leaf resolves to `context=None`, the model value is identical to a fresh context-less leaf → same hash. `Proposition.content_hash` enumerates its own fields and is untouched by a leaf change.

**Proof obligations (discharged in the 2a plan, not asserted):**
- A targeted test serializes a representative set of existing `QuantityLeaf`/`Claim` objects **before and after** the field is added and asserts **byte-identical** `model_dump_json()`.
- Round-trip: an existing corpus JSON (methyl/pharmaco) loads, re-serializes byte-identically.
- The full grammar + protocol + umbrella suites stay green (779 umbrella already the baseline).
- Only after all three: the field ships.

### 2a.3 Closing the Phase 1 loop
- Re-express C2 (`adar_dynamic_range_claim`) to populate `context=MeasurementContext(cell_line=…, assay="edited/unedited payload ratio")`.
- The C2 tripwire (`test_c2_context_conditioning_gap`, schema-based) **flips to green-required**: `"context" in QuantityLeaf.model_fields` now True → the `strict` xfail becomes an xpass → the test must be converted to a normal passing assertion in the same commit. (This is the tripwire doing its job.)
- Append the resolution + the byte-identical proof to the gap report (GAP-2 → RESOLVED).

### 2a.4 expansion_class ledger
GAP-2 = **general**, core primitive, byte-identical. This is the template for every future general expansion; the 2a plan's byte-identity proof is the reusable recipe.

---

## 3. Slices 2b / 2c / 2d — sketch (each gets its own spec+plan)

**2b — patterns.** Register in `pattern.registry` (open, additive, no core change): `reported_quantity@v1` (estimand `reported_scalar`, excluded: adjusted/model-relative effects) and `mechanistic_law@v1` (excluded: statistical-estimand claims) — retiring the Phase 1 placeholders GAP-1; then `sense_and_kill@v1` — the domain composition pattern over `(reader, discrimination-topology, actuation, target)`, with its `excluded_applications` (e.g. "surface-antigen CAR targeting — use the antigen pattern"). Domain → periphery, per the doctrine. Exit: Phase 1 claims re-point off the placeholders onto registered patterns.

**2c — ingestion.** A `synbio.ingest` extractor (opt-in `[synbio]` extra) turning treatise sections into reported-stratum `LITERATURE_EXTRACTED` claims: structured extraction → human review gate → provenance to primary refs (`ClaimSource`). Never self-licensing; feeds the prior layer at scale. Exit: N reviewed reported claims in a queryable store, zero licensed.

**2d — the licensed spine (exit gate + traction).** Execution adapters over a real expression atlas (GTEx/TCGA-LAML RNA-seq) + genome annotation, reusing the SE-Contract data seam and the two-leg `AdapterRegistry` from STRATA/methyl. Target claim: **"RUNX1-RUNX1T1 clears the ~13 TPM floor in AML"** — a threshold test recomputed by two independent legs, licensing at REPRODUCED through `run_cycle`. Uses `MeasurementContext(tissue="AML", assay="RNA-seq TPM")` from 2a. **DATA DEPENDENCY (flag):** requires real AML fusion-expression RNA-seq; if absent it is data-blocked like the §2E REPLICATED thread — confirm data availability before committing 2d. Exit gate = the whole Phase 2 gate: one computed synbio claim LICENSED@REPRODUCED.

---

## 4. Decision points (resolve at sign-off; recommendations in brackets)

1. **First slice** — [2a, GAP-2 context]. Foundational, doctrine-proving, on the Durendal critical path, buildable now with no external data. (Alt: jump to 2d for fastest "traction," but 2d depends on 2b + data.)
2. **GAP-2 shape** — [structured `MeasurementContext`, all-optional] vs a bare `context: str`. Structured recommended (the spine queries tissue/assay). 
3. **GAP-3 interval** — [DEFER, YAGNI; tripwire stays armed] vs resolve now. Defer recommended (no spine caller yet).
4. **2d data** — confirm real AML fusion-expression RNA-seq is available (or accept 2d is data-blocked and stop at 2a/2b/2c). Needs a data check before 2d planning.

## 5. Non-goals / risks

- **Not** licensing on context — `MeasurementContext` is descriptive; it never enters a criterion (guard against smuggling a domain axis into the gate — cf. the §2a StrengthVector correction).
- **Byte-identity is a hard gate, not a hope** — 2a does not ship on "should be additive"; it ships on a demonstrated before/after byte-diff + green corpora. A drift = redesign, not a waiver.
- **Scope creep into a mega-change** — 2a is *only* GAP-2. Patterns (2b), ingestion (2c), and the spine (2d) are separate specs; do not fold them into the grammar change.
- **2d may be data-blocked** — surface early; 2a/2b are valuable and unblocked regardless.
