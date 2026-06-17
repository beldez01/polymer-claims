# polymer-claims

Home for the Polymer Claims agent-scientist ecosystem — a **compiler + runtime for science**:
a machine-readable grammar for scientific claims, a protocol that grows a corpus of them
toward truth, a local node that runs it, and a 3D viewer that renders the live universe.

> **New here?** Read `ARCHITECTURE_CURRENT.md` (what's active vs frozen vs future, one page) and
> `GLOSSARY.md` (reserved terms). `docs/superpowers/CONTINUE.md` is the detailed continuity log.

| Subdir | What it is | Status / Distribution |
|---|---|---|
| `grammar/` | **The v1.3 grammar** (`polymer_grammar`) — the active claim IR. A five-layer grammar derived from first principles (see Direction below). | **Active** — all 8 layer-phases merged |
| `protocol/` | **The v1.3 protocol** (`polymer_protocol`) — the runtime over the grammar: the `run_cycle` flywheel + 3 daemons + the `next_action` scheduler + topology/timeline exports. | **Active** — all 5 sub-projects + daemons + scheduler merged |
| `src/polymer_claims/` | **The umbrella distribution** (`polymer-claims`) — the CLI over the complete runtime + the live local node (`serve`, behind the optional `[serve]` extra). | **Active** — `pip install polymer-claims` → local node works |
| `viewer/` | **The claims-universe 3D viewer** (Next 16 + React Three Fiber). Plays a sample timeline or streams a live node. Live layout is the signed-Laplacian spectral eigenmap, Procrustes-aligned (`serve --layout spectral`, default; `--layout force` for the legacy force-directed). | **Active** — `tsc`+`build` clean |
| `docs/superpowers/` | The canonical spec (`polymer-claims-canonical-spec.md`), `CONTINUE.md` resume primer, and `archive/` of shipped per-feature design docs (specs + plans). | Active |

---

## Quickstart — run the live universe locally

The most tangible experience is the **live node + viewer**: a local process runs the claims
universe forward and streams each frame; the viewer renders it evolving in real time.

```bash
# Terminal 1 — the node (install the serve extra once):
pip install -e '.[serve]'          # or: uv sync (the dev group includes serve deps)
polymer-claims serve               # → http://localhost:8000  (ticks the universe, streams SSE)

# Terminal 2 — the viewer:
cd viewer && npm install && npm run dev   # → http://localhost:3000
# In the viewer, click Connect (default http://localhost:8000) to enter LIVE mode.
```

### Real generation (optional)

`run-cycle` can generate executable claims via a real LLM (behind the `[llm]` extra):

```bash
pip install '.[llm]'
export ANTHROPIC_API_KEY=...
polymer-claims run-cycle corpus.json --llm     # --llm-model defaults to claude-sonnet-4-6
```

Honesty caveat: v1 plans run on the deterministic reference adapters (`builtin::const`), so this
proves the generation→execute→license plumbing end-to-end; meaningful data execution is gated on
real execution adapters.

### Watch a live agent

Run the live node with a real LLM driving the GENERATE stage and watch the universe evolve in the
viewer in real time:

```bash
pip install -e '.[serve,llm]'         # both extras
export ANTHROPIC_API_KEY=sk-ant-...
# Terminal 1 — the live agent node:
polymer-claims serve --llm --interval 3 --llm-every 4   # LLM proposes ~every 4th tick
# Terminal 2 — the viewer:
cd viewer && npm run dev               # http://localhost:3000 → Connect to http://localhost:8000
```

The execution substrate for *this `--llm` quickstart* is still the deterministic reference adapters
(`builtin::const`), so the agent's proposed claims license on LLM-asserted values — the real
generate→execute→license loop driven by a real agent, but not real-data science. (Real-data
execution has since shipped: `serve --real-data` runs the node on genuinely independent stdlib
execution adapters, and the methylation apparatus licenses on a *computed* region-Δβ — over
synthetic betas for now; see the CES / Phase-2 arc in `ARCHITECTURE_CURRENT.md`. Wiring real
adapters into the `--llm` path is a small tracked follow-up.) To tune cost vs. activity: lower
`--llm-every` or lower `--interval` to
increase agent cadence (and API spend); the agent runs alongside the seed proposers, so the
universe stays lively even on the throttle's quiet ticks.

**Sample mode vs live mode:** with no connection the viewer plays a precomputed
`viewer/public/sample-timeline.json` (sample mode); clicking **Connect** switches to **live
mode**, streaming frames from the running node as the corpus actually generates, licenses, and
revises claims. The `serve` node binds loopback only; binding a non-loopback `--host` requires
`--unsafe-remote-control` (the mutating routes are unauthenticated by design — local only).

### Fresh-clone dev commands

```bash
# Python suites (each subpackage is its own uv project):
uv run --project . pytest tests/ -q          # umbrella (node/cli/server)
cd grammar  && uv run pytest -q              # the grammar
cd protocol && uv run pytest -q              # the protocol runtime
cd grammar  && uv run pytest tests/test_isolation.py -q   # the one-way-dependency invariant
# Lint:        uv run ruff check src tests   (in each package dir)
# Viewer:      cd viewer && npm run typecheck && npm run build

# One command for everything (local CI substitute — GitHub Actions are unavailable):
bash scripts/check-all.sh

# Build all three wheels + smoke the installed console script:
bash scripts/build_and_test_install.sh
```

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
  assess → integrate). → `protocol/` (the full flywheel + 3 daemons + scheduler, complete).

Every design decision is judged against one test: **sensitivity** (capture the fullest
semantic + syntactic richness of real science — lose nothing real) × **specificity** (admit
nothing false; never force science into a shape it isn't). The anti-pattern is a "toy
questionnaire" that sounds rigorous but silently loses or distorts the science.

Full derivation (two adversarially-stress-tested research swarms) lives in
`~/Desktop/Research/topics/epistemic-claim-foundations/`. The consolidated design is the
**unified foundations spec**.

### The v1.3 grammar — five dependency-ordered layers

```
  L4  REVISION    AGM/TMS belief revision + entrenchment over the corpus   (temporal change)   [done]
  L3  CORPUS      value-based defeat graph (VAF) → grounded extensions      (composition)        [done]
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
authored* (a Table-2-fallacy guard) plus a **units-of-measure `Dimension`** algebra; and (L3) a **value-based defeat graph** whose
grounded extension is computed over a single *strength-mediated* effective-defeat relation (an
attack defeats only if the target does not Pareto-dominate the attacker), plus **Duhem–Quine
blame-sets** that surface under-determined contradictions (`duhem_underdetermined`) instead of
laundering them into one verdict; and (L4) **belief-base AGM revision** (`expand`/`contract`/`revise`)
over a *partial* entrenchment order, where `restore_consistency` makes an inconsistent corpus
consistent by incising the least-entrenched claims and **surfaces the ambiguity** (robust vs
underdetermined) when entrenchment can't decide — rather than silently picking a winner.

### Phase status (grammar)

| Phase | Scope | Status |
|---|---|---|
| 1 | foundation: L0 leaf, status, strength vector, pattern registry, claim skeleton + immutability | ✅ merged |
| 2 | L1: molecular Proposition + Equivalence | ✅ merged |
| 3 | L2: licensing bridge ((σ,M), dual route, rival_set_closure) | ✅ merged |
| 4 | typed causal roles + units-of-measure algebra | ✅ merged |
| 5 | L3: VAF defeat graph + Duhem blame-sets | ✅ merged |
| 6 | L4: AGM/TMS revision | ✅ merged |
| 7 | protocol-imposed fields + polymorphic subject | ◐ provenance ✅ (`provenance.py`), governance ✅ (`governance.py`), online-FDR ✅ (`fdr.py`), `reinterpret` ✅ (L3), `Claim.subject` ✅ (`subject.py`); oracle (#2) now unblocked by Phase 8; only `representation_revision` (#5) remains |
| 8 | the evaluator (runs the grammar) | ✅ merged — typed compute-graph IR (`operations.py`) + air-gapped runtime (`evaluate.py`): `evaluate()` + the two-implementation `verify()` gate that mints an L2 `Satisfaction` only on cross-adapter agreement (no self-licensing) |

All green, ruff clean. `grammar/` imports nothing from the legacy `polymer_formalclaim` IR
(enforced by an isolation guard test).

### Where the design lives

- **Canonical spec (current state of record):** `docs/superpowers/polymer-claims-canonical-spec.md` — the single authoritative spec; consolidates the per-feature design docs.
- **Original foundations spec (archived):** `docs/superpowers/archive/specs/2026-05-31-unified-claim-foundations-spec.md` · **Schema overview (HTML):** `docs/superpowers/archive/specs/2026-05-31-claim-schema-overview.html`
- **Per-feature design rationale + plans (with Progress Logs):** `docs/superpowers/archive/specs/` and `docs/superpowers/archive/plans/` (shipped per-slice specs and their plans are archived together)
- **Resume primer (kept current):** `docs/superpowers/CONTINUE.md`

---

## Protocol runtime (`polymer_protocol`)

The `protocol/` package (`polymer_protocol`) is the **runtime half of the compiler/runtime split** — it reads and writes the `polymer_grammar` IR and depends on it one-way (isolation-tested; `protocol/` never imports the legacy `polymer_formalclaim` IR).

State is a frozen `Corpus` = (claims, defeat_edges, equivalences, fdr_ledger). `run_cycle(corpus, adapters, ctx)` chains seven pure assessment stages:

```
represent → canonicalize → safety_gate → commit → execute_ground → verify_stage → integrate
```

returning a new `Corpus` plus the unresolved-attack `frontier`, the `gated_lane` (claims blocked by governance), and a per-stage `audit`.

EXECUTE reuses the Phase-8 air-gapped `verify()` — two-implementation agreement, no self-licensing — to mint an L2 `Satisfaction`. GENERATE (the proposer bus, see below) is now live; the daemons are a later sub-project.

An optional oracle registry (`run_cycle(..., oracles=...)`) caps a licensed claim's **empirical** strength axes (magnitude / uncertainty / evidence-against-null / world-contact) by the validation tier of the weakest oracle its plan references. Unresolved or out-of-domain oracles count as `UNVALIDATED` (zero empirical strength) — the guarantee is always-on, not disableable by omitting the registry. Builtin-only claims (no `oracle_ref`) are unaffected.

`run_cycle` no longer executes every committed claim. The **SELECT** stage ranks eligible
PENDING claims on a two-axis value `(expected-information-gain, stakes)` under a structured,
passed-in cost and a budget (`run_cycle(..., cost_model=, budget=)`), executing only the
selected subset; the rest stay PENDING for a later cycle. EIG comes from a minimal
Beta–Bernoulli posterior derived from each claim's `StrengthVector` (deterministic, no
embeddings); stakes is the size of its forward dependency cone. The search cardinality of each
selection is recorded and **tightens VERIFY's significance bar** — a cardinality-scaled
Benjamini–Hochberg selective-inference correction — as the competed pool grows (identity at
cardinality 1). Quality-diversity portfolios, a heterodox reserve lane, and cross-cycle
accumulating belief land in **#3b** (below).

**SELECT #3b** hardens the valve against monoculture and reward-hacking on a threaded
`SelectionLedger` (`run_cycle(..., ledger=)` in/out — `Corpus` stays grammar-IR-only). Belief now
*accumulates* per claim across cycles from realized outcomes (with a settled-concentration EIG
guard); a per-operator **surprise-Goodhart** credit discounts the fill-order priority of proposers
whose high-EIG claims fail to ground (the Pareto front + belief stay undistorted); a
**quality-diversity** portfolio spreads the budget across structural cells `(pattern, subject-kind)`
with per-cell caps; and a **heterodox reserve lane** pursues dominated/contrarian candidates the
main lane would never pick. The hardening is OFF by default (`reserve_fraction=0.0`,
`cell_cap_fraction=1.0` → exact #3a back-compat); a deployment turns it on with the recommended
`0.2`/`0.5`.

> `run_cycle` no longer requires claims to be pre-loaded. The **GENERATE** stage (right after
> REPRESENT) runs a bus of passed-in proposers plus an exogenous injection port
> (`run_cycle(..., proposers=, injected=)`) through `compile_to_IR`, folding new CONJECTURED claims
> into the corpus. Two pure operators ship: *rival-generation* (direction-flipped alternative-hypothesis rivals)
> and *frontier-attack* (a CONJECTURED defense seed at each unresolved-frontier node). Both are strictly
> **belief-neutral** — the grounded extension is unchanged when they fire (generation proposes; only
> EXECUTE/VERIFY decides). Content-addressed ids + a skip-own-output guard keep the corpus
> convergent. Injected executable claims license the same cycle; pure proposals first act next.
> Embedding/LLM operators plug in behind the bus seam; operator-5's representation-revision lane is
> deferred (it needs the grammar's `representation_revision` meta-tier).

> A `DefeatEdge` can be **provisional** (#4b) — inert until its source claim is LICENSED, then effective
> (`effective_defeats`/`grounded_extension` take a `licensed_ids` set; `represent` and the AGM recompute
> `_in_set` supply it). GENERATE's `frontier_attack` and `rival_generation` now plant a provisional rebut
> edge instead of an isolated node: belief-neutral while the seed/rival is a conjecture (the edge is inert),
> it wires a real defeat the moment the claim is validated — closing the #4a limitation. A **rebut** edge
> (never an `incompatible_with` neighbor) keeps `restore_consistency._conflicts` out of the loop, so nothing
> is retracted while still conjectured. (The pure operators' no-plan seeds stay dormant until they gain a
> plan; executable-generation is deferred.)

> GENERATE is now **self-driving** (#4b slice-2): a rival of a *planned* claim transplants the source's
> compute graph with a direction-**mirrored** criterion (`mirror_criterion`/`transplant_plan`), so the
> rival is a real SELECT candidate — running it adjudicates source-vs-rival on the same data, and a
> winning rival's provisional edge autonomously defeats its source (the flywheel turns with no injection).
> And GENERATE allocates its budget across operators by their `SelectionLedger` credit
> (`run_cycle(..., generation_credit_floor=)`), throttling chronic Goodhart-failers to a recoverable
> probation slot — never killed. Both OFF by default.

> The bus is now open to **injected intelligence** (#4b slice-3, completing #4b): a `GenerationAdapter`
> (real LLM/embedding operators implement it *outside* the package; `TemplateGenerationAdapter` is the
> in-package reference) plugs in via `bridge_proposer`, and `compile_untrusted` enforces the load-bearing
> rule that **external generation can propose but never license** — a claim arriving pre-licensed is
> dropped, and provenance is forced to `AGENT_GENERATED` with the adapter's identity (which the slice-2
> credit economy then governs). Executable frontier-attack defense and real model adapters live behind
> the seam.

- **Design spec:** `docs/superpowers/archive/specs/2026-06-02-protocol-spine-design.md`
- **Tests:** `cd protocol && uv run pytest -q`

| Subdir | Package | Status |
|---|---|---|
| `grammar/` | `polymer_grammar` | ✅ 8 phases complete + oracle dossier + provisional defeat edges (#4b) — 268 tests |
| `protocol/` | `polymer_protocol` | ✅ Sub-projects #1 + #2 + #3a + #3b + #4a + #4b-complete (assessment spine + oracle dossier + SELECT [value engine + QD/heterodox/Goodhart/accumulating belief] + GENERATE [proposer bus + provisional links + executable rivals + credit economy + intelligent-operator seam]) — 208 tests |

---

## The v1.2 fallback (moved out of the repo)

v1.2 — the frozen FormalClaim ecosystem (`polymer_formalclaim` IR, the 47-claim corpus, the
`claim-harness` plugin, schema, legacy workflows) — has been **moved out of this repository**
(preserved locally, pending eventual deletion). The v1.3 system never depended on it: `grammar/`
imports nothing from `polymer_formalclaim` (isolation-guard enforced), and it was never a build
dependency or workspace member. Restoring it (e.g. to validate v1.3 by ingesting the v1.2 corpus)
would be a deliberate, separately-reviewed step, never an implicit import.

## History

Consolidated 2026-05-26 from three now-archived repos: `beldez01/claims`,
`beldez01/polymer-formalclaim`, `beldez01/polymer-claim-marketplace`. The v1.3 grammar effort
began 2026-05-31 from the foundations research. On 2026-06-01 the v1.2 surface was consolidated
under `v1.2/` and frozen as a fallback while v1.3 was built and validated; on 2026-06-17, with v1.3
validated, v1.2 was moved out of the repository (preserved locally, pending eventual deletion).

## Deferred

- A navigable **3D latent-space claim-topology viewer** (lasso clusters; network-as-subject) —
  gated on corpus scale; extends the existing `PolymerGenomicsAPI/viewer` universe.
- **v1.2 PyPI publish** (`polymer-formalclaim`) and the API IR-dedup are deferred indefinitely in
  favor of the v1.3 rebuild. Revival instructions live in v1.2's own README (preserved with the
  v1.2 tree outside the repo) if v1.2 is ever reactivated.
