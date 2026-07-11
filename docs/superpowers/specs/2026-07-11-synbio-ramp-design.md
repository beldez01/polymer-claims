# WAYLAND — ramping the synthetic-biology arm: design

**Date:** 2026-07-11
**Status:** Design (a ramp within the Wayland program; executes parts of Phase 2b/2c/2d). Program plan: `docs/superpowers/plans/2026-07-10-synbio-claims-universe.md`. Phase 2 design: `docs/superpowers/specs/2026-07-10-synbio-phase2-design.md`. Gap-log (living, the entry/exit artifact): `docs/superpowers/notes/2026-07-10-synbio-grammar-gaps.md`.
**Telos:** Grow the synthetic-biology arm from 5 conjectured probe claims into a substantial, honestly-tiered sub-universe — **and, in the same motion, systematically stress-test the IR schema**, converging the strain points into a fixed, deduplicated, classified gap-log. The claims are the exhaust; the gap-log is the scientific output.

`WAYLAND` is the program codename only. The arm is named by **subject**: `synthetic-biology`.

---

## 0. Locked decisions (brainstorm, 2026-07-11)

1. **Ramp shape — both strata, in a deliberate ratio.** Grow breadth (reported priors) *and* stand up the depth machinery — so the arm has real structure, not an undifferentiated pile of one color. But this session's *depth* is scaffold-only (see #2).
2. **Depth = scaffold, license deferred.** No real AML fusion-expression RNA-seq is pinned in-repo, and self-containment forbids tapping a sibling for a licensed result. So the expression two-leg adapter seam is built and tested, but **no `run_cycle` license is claimed this session.** The data-pin is the explicit next-session gate.
3. **Arm naming — one arm `synthetic-biology` + a topic facet.** Not split into two arms; the technique layer and the therapeutic-application layer are one field. Per-claim `topic` facet (`sensing`/`computing`/`writing`/`delivery`/`actuation`/`chassis`/`measurement`/…) carries the sub-structure. Retires `synbio`/`wayland` as arm *labels* (fine as shorthand).
4. **Ingestion mechanism — manifest-driven** (extraction decoupled from construction; §3).

**Standing principles (session-level, from the operator):**
- **Name by subject, not by project/dir.** The arm facet is `synthetic-biology`.
- **Self-contained.** Pin any data we use into `polymer-claims/data/`; regeneration must not reach into `~/Desktop/Research/` or any sibling.

---

## 1. The gap-log as a first-class deliverable — the "fixed list"

Onboarding a field is, by the expansion doctrine, an exercise in *growing what the IR can ingest*. Every place a claim is tricky, cumbersome, or nonsensical to parameterize into the schema is a signal — and it must be **recorded, not silently worked around**. This ramp elevates that from a side-effect to a primary deliverable.

**Mechanism.** Every manifest entry (§3) carries a mandatory `schema_fit`:
- `clean` — the claim mapped to a leaf/pattern without strain; or
- a structured **gap record**: `{constraint, current_ir_behavior, candidate_resolution, expansion_class, purity_cost}` where `expansion_class ∈ {general, analysis, subject, domain}` (the doctrine's table).

**The fixed list.** After an ingestion pass, an aggregator **deduplicates** these gap records into canonical, numbered entries (`GAP-5`, `GAP-6`, …) appended to the living gap-log, extending `GAP-1…4`. Dedup + canonical id + classification is what makes it *fixed* (definitive and non-sprawling) rather than an ad-hoc scatter. Two entries describing the same strain collapse to one; the count of distinct entries is the honest measure of how far synbio pushed the IR.

**Review emphasis.** When manifests are drafted for review, the `schema_fit` annotations are the part that most needs the operator's eyes — that is where IR-design judgment lives, and it is the part that compounds across every future field.

**Doctrine guardrails (unchanged):** general → core primitive; analysis → pattern/profile; subject → subject/roles layer; domain → namespaced periphery. Additive-or-nothing, proven byte-identical. **This session ships no core-primitive change** (that is a separate, byte-identity-gated slice); it *logs* the candidates the fixed list needs.

---

## 2. Workstreams

Sequenced **W1 → W2 → W3**, with **W4** in parallel after W2. Each has an entry gate, a deliverable, and an exit gate.

### W1 — Self-containment (foundation)
- **Entry:** none.
- **Deliverable:** copy both compendia into `data/synbio_compendia/{synthetic-biology,programmable-living-medicines}/` (26 md, ~676K); retarget `sources.py` `_TREATISE` to the in-repo path; add a `data/synbio_compendia/SOURCE.md` recording origin + fetch provenance.
- **Exit:** `sources.py` refs resolve inside the repo; nothing in the synbio regeneration path reads `~/Desktop/Research/`. Existing 5 claims + their tests stay green.

### W2 — Patterns (Phase 2b)
- **Entry:** W1.
- **Deliverable:** register the missing patterns so ingested claims have real homes instead of placeholders:
  - `reported_quantity@v1` and `mechanistic_law@v1` — **analysis-class, field-agnostic** → registered in the pure grammar registry (`grammar/src/polymer_grammar/pattern.py`), each with `estimand`, `null_model`/`scale`/`invariance_group` as the model requires, and ≥1 `excluded_applications` (Newman-hole pin), e.g. `reported_quantity` excludes "an adjusted or model-relative effect — use adjusted_effect".
  - `sense_and_kill@v1` — **domain** composition pattern over `(reader, discrimination-topology, actuation, target)` → **registered from the umbrella** `synbio/patterns.py` at import (`from polymer_grammar.pattern import registry; registry.register(...)`), so the pure grammar file never learns a synbio concept. This is the concrete realization of "domain to the periphery" against a shared singleton registry.
  - Re-point C1–C5 off the placeholder `PatternRef`s (`_REPORTED_QUANTITY`/`_MECHANISTIC_LAW` in `synbio/claims.py`) onto the now-registered patterns.
- **Exit:** all three patterns resolve via `pattern.get(...)`; C1–C5 reference registered patterns; grammar/protocol/umbrella suites green; registry coverage metric reflects the additions. Additive only — no existing claim changes bytes.

### W3 — Ingestion = the breadth ramp (Phase 2c)
- **Entry:** W2.
- **Deliverable:** the manifest-driven pipeline (§3), run over the **subset-first** scope (§4), producing:
  - reviewed `data/synbio_compendia/manifests/*.yaml` (one per chapter in scope);
  - `synbio/ingest.py` — a deterministic builder: manifest entry → real `Claim` through the grammar (generalizing the C1–C5 factories), all `LITERATURE_EXTRACTED` / `CONJECTURED` / `topic`-faceted;
  - new gap records aggregated into the gap-log as `GAP-5…` (the fixed list, §1);
  - `data/demo/synthetic_biology_universe.json` (mirrors `data/demo/immuno_universe.json`) via a `viewer/scripts/make_synthetic_biology_universe.py` bundler;
  - the arm merged into the faceted universe (`merge_universes.py` + `viewer/scripts/make_merged_universe.py`) with `arm="synthetic-biology"`, `topic=<facet>`.
- **Tiering rules (anti-"toy-questionnaire"):** only **Tier-1** (quantitative floors/constants → `QuantityLeaf`) and **Tier-2** (mechanistic laws/design principles → `PropositionLeaf`, or a `sense_and_kill` composition) become claims. **Tier-3** narrative synthesis stays as `Provenance.rationale`/context — *not* forced into a claim. A manifest entry that can only be Tier-3 is recorded as such and skipped, not fabricated.
- **Exit:** the subset's claims validate through the grammar, all CONJECTURED, render in the merged universe under the `synthetic-biology` arm with topic facets; the gap-log gained ≥1 new canonical entry (or is affirmed complete for the subset); honest yield reported (the real count, not a target); suites green.

### W4 — Spine scaffold, license deferred (Phase 2d foundation)
- **Entry:** W2.
- **Deliverable:** the expression two-leg adapter **seam** — a claim shape using `MeasurementContext(tissue=…, assay="RNA-seq TPM")` and two independent expression-floor estimators wired to the SE-Contract data seam and the two-leg `AdapterRegistry` (mirroring STRATA/methyl) — **stopping short of `run_cycle`**. A test exercises the seam on a small synthetic fixture (no real data), asserting the two legs agree on a threshold decision. The exact real-data dependency (pin TCGA-LAML **or** BLUEPRINT hematopoietic RNA-seq; candidate first claims: "RUNX1-RUNX1T1 clears the ~13 TPM floor in AML" / "RUNX1T1/ETO is silent in normal blood lineages") is documented as the next-session gate.
- **Exit:** the seam is tested on the fixture; **no license claimed**; the data gate is written down explicitly (in this spec's §6 and the gap-log/CONTINUE). W4 is cheap insurance that the depth path is real, not a source of count growth this session.

---

## 3. The manifest schema (W3)

One YAML file per chapter in `data/synbio_compendia/manifests/`. Each entry:

```yaml
- id: sb-<chapter>-<slug>            # stable, hyphen-id (matches the immuno/real-id convention)
  title: <one-line claim statement>
  tier: 1 | 2                        # Tier-3 entries are recorded as tier: 3, skip: true (not built)
  topic: sensing|computing|writing|delivery|actuation|chassis|measurement|control|...
  leaf:
    kind: quantity | proposition
    # quantity:
    value: <float>
    unit: <UCUM str | null>          # only for FUNDAMENTAL; DERIVED must be null + carry formula
    uncertainty: <float | null>      # null when honestly a range, never a faked symmetric bar
    measurement_basis: FUNDAMENTAL | DERIVED
    formula: <str | null>            # required for DERIVED
    context:                         # optional MeasurementContext (2a)
      tissue: <str | null>
      cell_line: <str | null>
      assay: <str | null>
      condition: <str | null>
    # proposition:
    data: <observation>
    warrant: <mechanism>
    rebuttal: <where it fails>
    warrant_type: mechanistic_analogy
  source: <SOURCES key>              # extend SOURCES with the chapter refs
  schema_fit:                        # MANDATORY — the fixed-list input (§1)
    status: clean | gap
    # when gap:
    constraint: <what could not be expressed>
    current_ir_behavior: <what the IR does instead>
    candidate_resolution: <the additive fix>
    expansion_class: general | analysis | subject | domain
    purity_cost: <what it touches; backward-compat obligation>
```

**Why decoupled.** The manifest is the reviewable judgment layer (is this a claim? is the number right? did it map cleanly?), diffable in git and independent of the mechanical build. `synbio/ingest.py` is deterministic and unit-tested: same manifests → same claims, byte-stable. This is the only ingestion form that keeps the "human-in-the-loop, provenance to primary refs" discipline while scaling past hand-written factories, and it refuses the non-deterministic/unauditable LLM-at-runtime route the foundations distrust (untrusted proposer).

---

## 4. Scope for this session — subset-first

Prove the pipeline end-to-end on the **PLM therapeutic chapters that feed the Durendal logic** first — the read/compute/act spine:
- `02-reading-surface-antigen-sensing.md`, `03-reading-intracellular-genome-sensing.md` (sensing)
- `06-computing-synthetic-circuits.md` (computing)
- `07-acting-cellular-effectors.md` (actuation)
- `08-delivery.md` (delivery — the endosomal-escape bottleneck already probed as C4)

Get these merged and rendering + the first new gaps logged, **then** fan out to the remaining PLM chapters and the 12 `synthetic-biology/` technique chapters in subsequent passes (each pass = more manifests, same pipeline). This delivers a real ramp and a working, tested pipeline without gating the session on 26 chapters of review.

---

## 5. Invariants (must hold at exit)

- `grammar/` + `protocol/` stay **pure + numpy-free**; `Corpus` stays **exactly 4**.
- Heavy/ingestion deps behind the opt-in `[synbio]` extra; core import succeeds without it.
- **No core-primitive change this session.** W2 is additive registry entries; W3 logs candidates but ships no `Leaf`/strength change. Any such change is a separate byte-identity-gated slice.
- Two-stratum rule: every W3 claim is `LITERATURE_EXTRACTED` → `CONJECTURED`; nothing self-licenses.
- Real data gitignored; the compendia (text, licence-permitting) may be committed — confirm at W1. Self-containment: regeneration reads only `data/`.
- Existing corpora (methyl/pharmaco/immuno) validate byte-identically; their suites stay green.

## 6. Data gate (explicit, for the deferred depth)

The first **licensed** synbio claim needs real expression data pinned into `data/`:
- **Option A (on-plan):** TCGA-LAML RNA-seq TPM from UCSC Xena → "RUNX1-RUNX1T1 clears the ~13 TPM floor in AML." Needs a network fetch.
- **Option B (self-contained now, next session):** pin the BLUEPRINT hematopoietic RSEM quantifications → "RUNX1T1/ETO is silent in normal blood lineages" (the topology-rejection premise). No network.

Decide at the depth session; W4 builds the seam either target plugs into.

## 7. Risks

- **Low Tier-1/2 yield** (Tier-3 dominates a chapter). → The tiering rule *expects* this; skip honestly, report real yield, don't fabricate. Subset-first surfaces the yield before committing to 26 chapters.
- **Manifest review is the bottleneck.** → Subset-first bounds it; the `schema_fit` fields are the priority review target.
- **Gap-log sprawl** (the anti-goal of a "fixed list"). → Dedup to canonical numbered entries is a required aggregator step, not optional.
- **Domain pattern leaking into the pure core.** → `sense_and_kill` registered from the umbrella against the shared singleton, never written into `pattern.py`.
- **Scope creep into a core-grammar change.** → Explicitly out of scope this session (§5); logged for a future byte-identity-gated slice.

## 8. Non-goals

- No licensed synbio claim this session (depth deferred; §0.2, §6).
- No new `Corpus` collection; no `Leaf`/`StrengthVector` change.
- No ingestion of all 26 chapters this session (subset-first; §4).
- No LLM-at-runtime extractor (manifest-driven only; §3).
