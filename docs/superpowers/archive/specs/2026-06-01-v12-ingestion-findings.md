# v1.2 → v1.3 ingestion — sensitivity-test findings

Date: 2026-06-01
Status: diagnostic result (informs the remaining grammar phases; not itself a build spec)
Probe: `grammar/scripts/probe_v12_ingest.py` (run: `cd grammar && uv run python scripts/probe_v12_ingest.py`)

## What this is

A preliminary **sensitivity test** (per the unified spec's sensitivity × specificity criterion):
can the v1.3 grammar *as built so far* (phases 1–4) represent the 47 real claims the frozen
v1.2 corpus holds? The probe attempts a best-effort construction of a v1.3 `Claim` from each
v1.2 claim JSON and reports which v1.2 fields find a home vs. which are homeless. It reads v1.2
JSON as **data only** (no `polymer_formalclaim` import — isolation guard respected).

## Headline

- **47/47 claims construct a v1.3 `Claim` skeleton — but "constructible ≠ faithful."** The
  skeleton only holds because the probe (a) leans on a `PropositionLeaf` fallback carrying the
  free-text conclusion, and (b) **fabricates** a placeholder `PatternRef` + `estimand`. Strip
  those crutches and most claims are *not* faithfully representable yet.
- The grammar reliably holds: `id`, `title`, `status` (from `conclusion.outcome`), scalar
  `statistics → QuantityLeaf`, and a lossy `conclusion → Proposition`.

## Homeless v1.2 fields (no v1.3 slot in phases 1–4)

| field | count | destination |
|---|---|---|
| `subject` | 47/47 | ⚠️ **no `Claim.subject` slot built** (10-variant SubjectRef in v1.2; in unified spec, unbuilt) |
| `external_assumptions` | 47/47 | **Phase 5** — Duhem auxiliaries; this *is* the blame-set material |
| `depends_on` | 47/47 | **Phase 5** — L3 defeat/support edges (or equivalence) |
| `premises` | 47/47 | Phase 7 (provenance) / Phase 8 (evaluator) |
| `operations` | 47/47 | Phase 8 (compute graph / evaluator) |
| `context` (assembly) | 47/47 | no slot (minor; provenance) |
| `domain` | 47/47 | replaced by pattern + profile (by design) |
| `version` | 47/47 | could map to `MaterializationContext` (phase-3 licensing) |
| `posted_at`, `notebook`, `exp_number` | 39–47/47 | provenance metadata (no slot; mostly fine to drop) |

## Statistics that don't fit a single `Leaf`

**29 vector-valued statistics** (+3 other non-scalar) across the corpus — e.g. per-locus Ti/Tv,
per-feature heatmaps: a statistic whose `value` is a list of `{label, value}` pairs. The L0
`Leaf` is scalar; there is **no home for a labeled-vector statistic**. Options to weigh: a
`VectorLeaf` (tuple of labeled scalars sharing one estimand/unit), or modeling a vector statistic
as *N sibling leaves under one pattern instance*. Not currently on any phase.

## Roadmap implications

1. **Phase 5 is empirically well-motivated.** Every one of the 47 claims carries
   `external_assumptions` (typed: design_choice / literature / mechanistic, each with a confidence)
   and `depends_on`. That is exactly the Duhem-auxiliary + inter-claim-dependency structure L3
   represents → proceed with the L3 VAF + blame-set phase. **Refinement:** Phase 5 should let an
   `external_assumption` be a first-class node that a blame-set can point at, not only claim↔claim
   edges — the auxiliaries are where Duhem blame actually lands.
2. **Two gaps are NOT on the current roadmap and surfaced here:**
   - **Subject slot** — arguably the largest single fidelity hole (every claim is *about*
     something). Candidate: a dedicated phase to add the polymorphic `Claim.subject` from the
     unified spec, or fold subject into the pattern/profile binding. Decide before mass-ingest.
   - **Vector-valued statistics** — an L0 extension (`VectorLeaf` or sibling-leaves convention).
3. **Pattern inference is unsolved.** v1.2 claims have no `pattern`; nothing classifies a raw
   claim into a registry pattern. A faithful ingest needs either authored patterns per claim or a
   classifier. Track as a protocol concern (CANONICALIZE stage).

## Bottom line

The 4-phase grammar holds the *shell* of all 47 claims, validates the Phase 5 direction with real
data, and surfaces two off-roadmap gaps (subject, vector statistics) plus the unsolved
pattern-inference problem. A *faithful* full ingest is not yet possible — by design, since phases
5–8 are unbuilt — but nothing in the corpus contradicts the v1.3 foundations.
