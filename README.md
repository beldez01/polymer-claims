# polymer-claims

Home for the Polymer Claims agent-scientist ecosystem — a machine-readable representation
of scientific claims, and the beginnings of a protocol for generating new ones.

| Subdir | What it is | Status / Distribution |
|---|---|---|
| `formalclaim/` | **The FormalClaim IR v1.2** — pydantic models, three-valued inference evaluator, materialization dispatcher, Nanopublications projection, CLI + MCP server. The **live, canonical** IR (what powers polymerbio.org today). | PyPI: `polymer-formalclaim` (tag `formalclaim-vX.Y.Z`) |
| `grammar/` | **The v1.3 grammar** (`polymer_grammar`) — the next-generation claim schema, built in isolation from v1.2. A five-layer grammar derived from first principles (see Direction below). | In progress — 4 of 8 grammar phases merged |
| `corpus/` | The public claims corpus: domains, tiers, contributors, governance, JSON Schema contract, and the CI evaluator. PR-as-submission target. | GitHub PRs to `corpus/domains/**/claims/*.json` |
| `plugins/claim-harness/` | The Claude Code plugin: MCP bundle, claim-authoring skills, submission pipeline. | `/plugin marketplace add beldez01/polymer-claims` |

---

## Direction & goals

**The claim schema is not the product — it is the intermediate representation of a protocol
for the systematic generation of scientific knowledge.** The long-term artifact is a
flywheel: an agent operates on the latent space of existing claims to generate new,
testable hypotheses, executes and verifies them, and folds the verified results back in as
new claims; the corpus self-corrects and accumulates. The IR earns its existence by making
that loop machine-runnable, falsifiable, and reversible. "Compiler + runtime for science,"
not "file format."

Two artifacts define the system, a **compiler/runtime pair over one IR**:

- **The Grammar** — what a claim *is* (well-formed, interpreted, licensable). → `grammar/`
- **The Protocol** — how a corpus of claims *grows toward truth* (generate → pursue →
  assess → integrate). → future work, atop the grammar.

Every design decision is judged against one test: **sensitivity** (capture the fullest
semantic + syntactic richness of real science — lose nothing real) × **specificity** (admit
nothing false; never force science into a shape it isn't). The anti-pattern is a "toy
questionnaire" that sounds rigorous but silently loses or distorts the science.

Full derivation (two adversarially-stress-tested research swarms) lives in
`~/Desktop/Research/topics/epistemic-claim-foundations/`. The consolidated design is the
**unified foundations spec**.

### The v1.3 grammar — five dependency-ordered layers

```
  L4  REVISION    AGM/TMS belief revision + entrenchment over the corpus   (temporal change)   [planned]
  L3  CORPUS      value-based defeat graph (VAF) → grounded extensions      (composition)        [planned]
  L2  CLAIM       pattern-typed DAG → 3-valued satisfaction + strength       (licensing bridge)   [partial]
  L1  PROPOSITION molecular content + asserted, defeasible identity          (semantics)          [done]
  L0  LEAF        sum-typed empirical anchor (Quantity/Categorical/…)         (empirical)          [done]
```

Load-bearing commitments already realized in `grammar/`: a **sum-typed leaf** (qualitative /
existence / Toulmin-warrant findings are first-class, not fake statistics); a **molecular
Proposition** whose identity is an *asserted, licensed equivalence* — never a hash
(Halvorson 2012); a **6-axis Pareto strength vector** (no hidden scalar, genuine
incomparability); an **open axis-derived pattern registry**; a **licensing bridge**
((σ,M) satisfaction, severe-test-or-replication routes, required rival-set-closure — *no
LICENSED-simpliciter*); and **typed causal roles** whose adjustment set is *derived, never
authored* (a Table-2-fallacy guard) plus a **units-of-measure `Dimension`** algebra.

### Phase status (grammar)

| Phase | Scope | Status |
|---|---|---|
| 1 | foundation: L0 leaf, status, strength vector, pattern registry, claim skeleton + immutability | ✅ merged |
| 2 | L1: molecular Proposition + Equivalence | ✅ merged |
| 3 | L2: licensing bridge ((σ,M), dual route, rival_set_closure) | ✅ merged |
| 4 | typed causal roles + units-of-measure algebra | ✅ merged |
| 5 | L3: VAF defeat graph + Duhem blame-sets | ⬜ next |
| 6 | L4: AGM/TMS revision | ⬜ |
| 7 | protocol-imposed fields (generated_by, oracle credibility, hazard/governance, online-FDR, …) | ⬜ |
| 8 | the evaluator (runs the grammar) | ⬜ |

87 tests, all green, ruff clean. `grammar/` imports nothing from `formalclaim/` (enforced by
an isolation guard test) — v1.2 stays live and canonical while v1.3 is built and validated.

### Where the design lives

- **Foundations spec (canonical):** `docs/superpowers/specs/2026-05-31-unified-claim-foundations-spec.md`
- **Schema overview (HTML):** `docs/superpowers/specs/2026-05-31-claim-schema-overview.html`
- **Spatial architecture map (HTML):** `docs/superpowers/specs/2026-05-29-claim-architecture-map.html`
- **Per-phase specs + plans (with Progress Logs):** `docs/superpowers/specs/` and `docs/superpowers/plans/`

---

## Source of truth (v1.2, current production)

- **Python IR:** `formalclaim/src/polymer_formalclaim/` — everything else imports it. The corpus
  evaluator consumes it via a uv path source (`corpus/evaluator/pyproject.toml`); no PyPI needed
  for local CI.
- **JSON Schema:** `corpus/schema/formal_claim_v1.2.schema.json` is canonical; `scripts/sync_schema.sh`
  copies it into the plugin and `scripts/sync_schema.sh --check` guards against drift.

> Note: `formalclaim/` (v1.2) is the live schema; `grammar/` (v1.3) is the next-generation
> grammar under construction. When v1.3 lands, a deliberate, separately-reviewed migration —
> never an implicit import — will bridge the two.

## History

Consolidated 2026-05-26 from three now-archived repos: `beldez01/claims`,
`beldez01/polymer-formalclaim`, `beldez01/polymer-claim-marketplace`. The v1.3 grammar effort
began 2026-05-31 from the foundations research.

## Deferred

- The flagship `PolymerGenomicsAPI` still vendors its own copy of the v1.2 IR
  (`src/polymer_genomics/formal_claims/`). Once `polymer-formalclaim` is published to PyPI, the API
  will depend on the package and drop its vendored `schema/evaluate/materialize/nanopub`, keeping
  only its API-specific `projection.py` + `feature_extractor.py`.
- A navigable **3D latent-space claim-topology viewer** (lasso clusters; network-as-subject) —
  gated on corpus scale; extends the existing `PolymerGenomicsAPI/viewer` universe.

## PyPI publishing

`polymer-formalclaim` is not yet on PyPI. To publish: configure the PyPI pending Trusted Publisher
(Project `polymer-formalclaim`, Owner `beldez01`, Repository `polymer-claims`, Workflow
`publish-formalclaim.yml`), then push a `formalclaim-vX.Y.Z` tag.
