# SELECT (Protocol #3) — Pre-Brainstorm Scoping Notes

> **NOT a spec.** A light primer to launch the #3 brainstorm cleanly after a compact. SELECT
> is the largest sub-project yet and will itself need decomposition during brainstorming. This
> note fixes *what it is*, *where it plugs into the merged spine*, the *build-vs-defer* line,
> and the *genuine forks* to lead the brainstorm with. Deep design source: the keystone
> `~/Desktop/Research/topics/epistemic-claim-foundations/generative-protocol/_FINAL_knowledge_generation_protocol.md`
> **Stage 3 — SELECT** (≈ lines 72–87) + the selection-aware-correction note (≈ line 117) + the
> reverse-engineering table row (line 238). Unified spec §3 SELECT row.

## What SELECT is

The **pursuit / value engine** — "the valve on RAM-bound, oracle-bound execution." It decides
**which** CONJECTURED/PENDING claims (off the frontier #1 emits) actually get committed +
executed this cycle, ranked on a **Pareto front of value under a structured cost**, never a
single `EIG/cost` scalar. It also records the **search cardinality** that prices the implicit
multiple-comparison sweep — which closes a loose end #1 deliberately left open.

## Where it plugs into the merged spine

Today `run_cycle` runs a **dumb driver**: EXECUTE runs *every* committed, non-gated PENDING
claim. SELECT replaces that with a value-ranked, budget-limited selector that sits **between
CANONICALIZE/SAFETY and COMMIT/EXECUTE** (keystone order: REPRESENT→GENERATE→SAFETY→CANONICALIZE
→**SELECT**→COMMIT→EXECUTE→VERIFY→INTEGRATE). Concretely it consumes the frontier + the corpus
and emits a **selection record** (which claims proceed, their Pareto rank, their QD cell, and
`search_cardinality`); the unselected stay PENDING for a later cycle.

## Hooks already in place (what we can build on without new grammar)

- **`provenance.search_cardinality`** — the field already exists (Phase 7 #1); SELECT is the
  stage that *sets it meaningfully* (how many candidates were ranked in the same cell/cycle).
- **The frontier** — `run_cycle` already emits the unresolved-attack frontier (the keystone
  closure); SELECT's highest-value region.
- **`StrengthVector`** Pareto machinery (`dominates`/`meet`/`join`) — a template for a value-vector Pareto front.
- **The defeat/entails graph** (`grounded_extension`, `entails_closure`, `derived_rebut_edges`)
  — **stakes = dependency-cone leverage is purely structural** and computable from this today.
- **#2's `OracleRegistry`** — the natural seat for the cost object's `oracle_queue_depth` /
  per-queue knapsack (oracles already carry tiers; a queue/cost facet is additive).

## The build-vs-defer line (the scoping tension, same as #1/#2)

The spine has stayed **pure, deterministic, no embeddings / no LLM / no external infra.** SELECT's
full design leans hard on embeddings + an external KG + a calibrated posterior. So the likely #3
shape mirrors #1/#2: **build the structural/pure core; defer the embedding-and-infra parts.**

**Candidate BUILD (pure, over grammar IR):**
- **Structured cost object** (`{wall_latency, capital, human_hours, failure_rate, oracle_queue_depth}`) — IR or passed-in config.
- **stakes** = downstream dependency-cone leverage (count high-strength claims that rebuild/break if K flips) — purely structural from the defeat/entails graph.
- **Pareto value front + the knapsack over oracle queues** (budget cap; protected "expensive-decisive" reserve lane; cap on cheap-QD-cell budget fraction; protected-minority/heterodox lane).
- **Selection record + `search_cardinality`** written into provenance.
- **The cardinality-scaled VERIFY bar** — #1 explicitly deferred this ("the spine enforces only that cardinality is *present*, not yet a *scaled* bar"). The highest-value concrete loose-end-closer: VERIFY's significance bar tightens as `search_cardinality` grows.
- **SELECT stage replaces the dumb execute-all driver** in `run_cycle`.

**Candidate DEFER (embedding / external / cross-sub-project):**
- **science-novelty axis** + the **two-axis calibrated posterior** (needs embeddings + an exogenous held-out benchmark + external KG).
- **internal-EIG** *as a real expected belief-shift* — needs a probability/posterior model the spine doesn't have (see Fork 2).
- **Surprise-Goodhart proper-scoring + per-operator credit ledger** (couples to GENERATE #4 and needs cross-cycle realized-grounding history → daemons #5).
- **Real async batch scheduler / in-flight queue re-evaluation.**

## Genuine forks to lead the brainstorm with

1. **Scope** — smallest coherent SELECT that's *real*: (a) cardinality-scaled VERIFY bar + a structural value ranking (stakes + cost) + budget cap replacing the dumb driver; (b) + the full structured-cost knapsack over oracle queues + QD/heterodox lanes; (c) + EIG/posterior. *Lean (a)→(b); (c) needs Fork 2 resolved.*
2. **EIG without a posterior (the crux)** — the spine has no probability model, so a true expected-belief-shift EIG isn't computable. Options: (a) **defer EIG**, rank on **stakes + structural novelty proxy + cost** only (keeps SELECT pure, honest); (b) introduce a **minimal posterior/probability primitive** now; (c) a **proxy-EIG** from strength/defeat structure (e.g. contested-ness / attack in-degree as an information-yield proxy). *Lean (a) for the first cut, with a clearly-named proxy in (c) as the upgrade path.*
3. **Where "value" lives** — ephemeral protocol-computed (like the frontier, recomputed per cycle) vs a persisted grammar `ValueVector` IR. *Lean ephemeral (value is cycle-specific; the spine keeps Corpus at 4 collections).*
4. **Cost representation** — structured cost as grammar IR vs passed-in protocol config (like `OracleRegistry`/`adapters`). *Lean passed-in config + a small structural-stakes computation.*
5. **The selection-aware VERIFY bar** — exact rule for how `search_cardinality` scales the significance threshold (a post-selection-inference / conditional-selective-inference analogue of Benjamini–Hochberg). Concrete, closes #1's deferral, and is the cleanest standalone win — could even be its own first slice.

## Suggested decomposition (to confirm in brainstorm)

#3 is big enough that it likely splits into ≥2 slices, e.g.: **#3a** the selection-aware VERIFY bar + structured cost + stakes-based ranking + budget knapsack replacing the dumb driver (pure, high-value, closes #1's loose end); **#3b** QD portfolio + protected-minority/heterodox lane + surprise-Goodhart guard (needs cross-cycle history; brushes #4/#5). The posterior/EIG/embedding axis is its own later thread once an embedding/benchmark substrate exists.

## Resume

Post-compact: invoke `superpowers:brainstorming` for SELECT, lead with Forks 1 + 2 (scope + EIG-without-posterior), then 3–5. Keep the spine invariants (pure/deterministic, one-way isolation, Corpus at 4 collections, no LLM/embeddings in the core). Same rhythm: brainstorm → spec → plan → subagent-driven → merge no-ff.
