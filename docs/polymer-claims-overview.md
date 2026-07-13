# Polymer Claims — A High-Level Overview

*What it is, why it exists, what goes in and comes out, how it's built, and where it's headed.*

---

## In one sentence

**Polymer Claims is a compiler and runtime for science: a machine-readable grammar for scientific
claims, plus a protocol that grows a corpus of them toward truth by letting each claim *earn* its
standing through independent recomputation — and a live 3-D universe that renders that corpus
evolving.**

It is not a database of facts and it is not an LLM that generates papers. It is the **trust
substrate** underneath both: the write-target where a claim becomes a durable, content-addressed
object whose standing is *earned*, *governed against a false-discovery budget*, and *continuously
re-examined as the world drifts*.

---

## Why it exists (the purpose)

Every system in the landscape either **stores** assertions (knowledge graphs, provenance infra) or
**generates** them (AI co-scientists) — but **none makes a claim earn its standing through
independent recomputation**. That gap is exactly where things break:

- AI agents for science generate claims *into a void where verification is optional* — Galactica
  fabricated papers, Sakana's "AI Scientist" passed peer review with hallucinated numbers, A-Lab
  "discovered" materials already in the database.
- Provenance/FAIR infrastructure records *what was run* but never **gates** standing on an
  independent re-run, and nothing is **drift-aware**.
- Formal methods (Lean, HOL) *did* solve earned standing — a result is valid because its proof
  checks against a tiny trusted kernel — but only for deduction, not for empirical claims.

Polymer Claims is **the gate each of those needed**, and the gate is **recomputation, not an LLM
arguing** — which is precisely why it does not degrade as models hallucinate. The headline integrity
metric is honest by construction: the corpus reports `q`, the expected fraction of LICENSED claims
that are false.

---

## The core idea (how a claim earns standing)

A claim moves from `PENDING` to `LICENSED` **only when**:

```
LICENSED  ⇔  two genuinely independent implementations AGREE
              ∧ on a real, fully-pinned, content-addressed analysis
              ∧ that beats a stated criterion (a severe test)
              ∧ the claim survives the corpus's defeat graph (grounded)
              ∧ it clears a live false-discovery-rate budget
```

The breakthrough is that **licensing, the FDR budget, and defeat are one mechanism, not three**:

- The **evidence atom is an e-value** (a betting score against the criterion-null), not a p-value.
  "Two independent implementations beat a criterion" is *naturally* an e-value.
- The **FDR ledger is an alpha-wealth process** over those e-values (online e-LOND), which controls
  false-discovery rate under **arbitrary dependence** — essential, because the corpus's own defeat
  and equivalence edges *are* dependence structure.
- A successful **defeat is a downward e-value update**; if it pushes a claim below the threshold it
  **de-licenses and refunds** the alpha-wealth it spent.

So licensing, defeat, drift, and FDR control all become the same operation viewed from different
angles. (This unification is genuinely novel — not something you'd cite a paper for; it's the flag
the project plants.)

---

## Composition (the four layers)

```
  grammar      →      protocol          →   node (umbrella)     →   viewer
 "what a            "how a corpus            a local mutable         renders the live
  claim IS"          evolves toward truth"   host that runs it       universe over SSE
 polymer_grammar    polymer_protocol         polymer-claims          Next + Three.js
   (pure)             (pure)                  (the ONE impure part)
```

| Layer | Package | What it is |
|---|---|---|
| **Grammar** | `polymer_grammar` (`grammar/`) | The claim IR — *what a claim is*. A 5-layer type system: L0 sum-typed leaf (the empirical anchor) → L1 proposition → L2 licensing bridge → L3 defeat graph (value-based argumentation) → L4 AGM belief revision. Plus the air-gapped evaluator. |
| **Protocol** | `polymer_protocol` (`protocol/`) | The runtime over the grammar — *how a corpus evolves*. The `run_cycle` flywheel + 3 standing daemons + a budget scheduler + the topology/timeline exports. |
| **Node** | `polymer-claims` (`src/`) | The umbrella distribution: a CLI over the runtime **and** the live local node (`NodeRunner` + a FastAPI SSE server). The only **impure** piece — it owns the loop, the clock, and the network. |
| **Viewer** | (Next 16 app, `viewer/`) | The 3-D claims universe (React Three Fiber). Plays a precomputed timeline (**sample mode**) or streams a running node (**live mode**). |

**The purity invariant:** `grammar` and `protocol` are **pure and deterministic** — no clock, no
randomness, no I/O; any time-like input is passed in. *All* impurity (reading data, running
computations, the network) lives in the umbrella node. And a `Corpus` is **exactly four
collections**: claims, defeat edges, equivalences, and the FDR ledger.

---

## Inputs

What flows *into* the system:

- **Claims & a corpus** — the seed material the protocol transforms (each claim is pattern-typed,
  with sum-typed leaves, a status, and optional strength / licensing / conclusion / provenance / an
  evaluation plan).
- **Proposers** — what generates *new* candidate claims each cycle: built-in rival/revision
  proposers, and a real **LLM generation adapter** (Anthropic-backed, the `[llm]` extra) that can
  drive the live node (`serve --llm`).
- **Data, content-addressed** — datasets enter through an **SE-Contract** seam shaped like GA4GH DRS,
  identified by a `dimnames_hash`; the analysis apparatus enters as a content-addressed
  `AnalysisProfile` (`profile_hash`).
- **Adapters** — the injected, *independent* implementations that resolve data and run a claim's
  computation. The **air gap** requires ≥2 from a trust registry (trusted ∧ different owner ∧
  different implementation).
- **Oracles & criteria** — a credibility dossier per measurement apparatus (it *caps* a claim's
  strength), and the stated criterion/severe-test a claim must beat.

---

## Outputs

What the system *produces*:

- **An evolving, licensed corpus** — claims promoted to `LICENSED` only via the gate above, demoted
  on defeat, and re-opened on drift. The unit of truth.
- **A governed discovery stream + the integrity metric `q`** — every license is an entry in the
  online FDR ledger; the corpus can state honestly "we expect ≤ `q` of LICENSED claims to be false."
- **Content-addressed, attestable licenses** — each records its full address: dataset `dimnames_hash`
  + apparatus `profile_hash` + a `semantic_run_id`, so a license is reproducible and — via `export-attestation` (in-toto/SLSA bundle, unsigned DSSE) — **attestable today**; full trust-validity (Sigstore/Rekor signing) is slice 3.
- **Topology / timeline exports** — `TopologyExport` (nodes/edges/clusters + a deterministic 3-D
  layout) and `TopologyTimeline` (warm-started frames + per-frame stats): the protocol↔viewer
  contract, streamed over SSE.
- **The live 3-D universe** — the corpus rendered as a spatial map (the signed-Laplacian spectral
  eigenmap, Procrustes-aligned so it grows smoothly), watchable as the node generates, licenses, and
  revises claims in real time. The demo universe now unifies **four subject arms** —
  pharmacogenomics, polymergenomics, immuno/ERV methylation, and synthetic-biology — into one
  faceted corpus (~800 claims) carrying additive `arm` / `modality` / `topic` facets, so a single map
  spans multiple sciences (a union of per-arm bundles, with each arm's statuses preserved verbatim).

---

## How it works (the lifecycle of a claim)

The engine is the **`run_cycle` flywheel** — one pure pass that threads a frozen corpus forward:

```
 generate  →  select  →  execute  →  verify  →  integrate  →  duhem-consistency
 (propose     (budget-    (run the    (≥2 indep.   (commit status,
  rivals/      ranked      pinned       adapters     update FDR ledger,
  revisions)   pursuit)    computation) must AGREE)  resolve defeat graph)
```

Around the flywheel run **three standing daemons** (pure, caller-scheduled):

- **DRIFT** — re-examines LICENSED claims as the data/apparatus content-address moves; re-opens a
  license whose world has shifted.
- **ORACLE-VALIDATION** — decays the strength caps of apparatus whose credibility is failing.
- **RED-TEAM** — attacks the corpus's own representation (a claim that the *schema* is wrong is a
  first-class, licensable meta-claim).

A **budget scheduler** (`next_action`) value-ranks what to do next — another `run_cycle` vs. a daemon
pass — under a shared budget. The **node** wraps all of this in a mutable loop, accumulates frames,
and streams them. So a single claim's arc is: *proposed → selected → independently recomputed →
(agreement + beats criterion + survives the defeat graph + clears the FDR budget) → LICENSED →
possibly defeated (de-licensed, alpha refunded) or drifted (re-opened to re-test)*.

---

## Direction (where it's headed)

**Phase 1 proved** a single claim can be licensed by real, pinned, independent recomputation, with a
drift daemon that re-opens it when the world moves. **Phase 2 makes that licensing sound,
standards-native, and alive**, in three arcs:

1. **The epistemic core (the moat)** — the e-value / online-FDR / defeat unification, grounded
   argumentation with hysteresis, and a rigorous, *measurable* definition of "independent"
   (conceptual replication, not just two runs of the same method). *Largely built — and now
   exercised end-to-end on real cross-cohort data: the WAYLAND synthetic-biology arm derived a
   licensed **expression-floor spine** (RUNX1-RUNX1T1 in t(8;21), plus a four-claim CBF
   fusion-marker family with 2×2 specificity) at **REPLICATED** across two real AML RNA-seq cohorts
   (TCGA-LAML + TARGET-AML) — the first claims the engine licensed by recomputation through the real
   gate rather than by ingesting a citation. The licensing criterion there is literally an interval
   **bound** on a quantity leaf (`low`/`high`, added to the grammar in 2026-07 as an additive,
   byte-identical-when-boundless expansion).*
2. **The standards skin (the adoption moat)** — re-express the content-address / apparatus / run
   model as the standards that already exist (GA4GH DRS/WES/TRS, Workflow Run RO-Crate,
   in-toto/SLSA/Sigstore). The strategic inversion: **don't integrate the world's data and compute —
   integrate *trust over* them**, so adoption is "point your pipeline at us," not "rewrite for us." *Slices 1–2 are built:* `export-attestation` emits an in-toto Statement v1 / SLSA Provenance v1 bundle keyed by the DRS content-address; `--format dsse` wraps each Statement in an unsigned DSSE envelope (signing-ready, not yet trust-valid). Real signing (Sigstore/Rekor) is slice 3.
3. **The living universe (the vision)** — hyperbolic geometry for the embedding (knowledge is
   hierarchical), the local-compute **agent protocol** ("deploy an agent to examine a region,
   re-execute, post verification/attack events"), a credence layer, and — the long horizon — a
   **sheaf-cohomology consistency gauge** that turns "grows toward truth" into a number that falls as
   independent recomputations bring claims into harmony. *The first piece of this is built:* a cellular sheaf over the claims graph computes Robinson inconsistency energy, `dim H⁰`, and `H¹` frustration obstructions, available via `export-consistency` and as a live headline on every `TopologyExport`. The energy/`H⁰` gauge is instrument-only, but **`H¹` frustration now *acts*** — since 2026-07-07 it drives the **duhem consistency fold** (a `run_cycle` stage that demotes claims on a frustrated cycle to `PENDING duhem_underdetermined` and reopens them when the contradiction resolves; ledger-neutral, demote-only). *The viewer overlay is also built:* a throttled `GET /consistency` route feeds a live consistency overlay — energy HUD, per-claim tension halos (nonnegative edge-share), and an animated H¹ frustration-cycle overlay with an obstruction panel.

---

## Honest status (what's real vs. exercised)

The project's discipline is **honesty over polish** — caveats travel with every claim until earned:

- **The kernel is real, and it now licenses on real data.** The genome-wide **n-DMP count** licenses
  at **REPRODUCED** on a real TCGA-LAML HM450 cohort (IDH-mut vs WT; two independent legs agree; full
  content-address recorded), and the WAYLAND expression-floor spine (above) licenses at
  **REPLICATED** across two real AML RNA-seq cohorts. Still honest about the edges: the finer
  **region-Δβ** methylation reduction remains **PENDING** on real data (held-out e-value 5.672, below
  the e-LOND first-test bar) — power-limited, not refuted — and some earlier demos still stand on
  synthetic betas until their real-cohort swap lands.
- **Independence is partly operator-authored.** Local registries derive `implementation_hash` from adapter
  bytecode, and licensed satisfactions record the credential pair that justified the air gap. Owner/trust
  metadata still comes from the operator registry.
- **It is local-only.** The live node's mutating routes are unauthenticated by design; real
  auth / multi-tenant / a federated "run your own node" layer is future work (a `POST /inject` hook
  is the noted seam). There is no CI — `scripts/check-all.sh` is the local gate.
- **The sheaf gauge covers Quantity-leaf claims only.** Non-quantity claims (categorical, existence, proposition) are excluded from the cellular sheaf; unit/dimension-mismatched equivalence pairs are flagged but not connected. The energy reflects the scalar-value sub-graph, not the full topology.

---

## The one-paragraph version

Polymer Claims is a **compiler and runtime for science**. A **grammar** defines what a scientific
claim is; a pure **protocol** grows a corpus of claims toward truth by a flywheel that proposes,
independently recomputes, and gates each claim — promoting it to LICENSED only when two independent
implementations agree on a pinned, content-addressed analysis that beats a criterion, survives the
defeat graph, and clears an e-value-based false-discovery budget. A local **node** runs that loop and
streams it; a **viewer** renders the result as a living 3-D universe. The bet is that the missing
piece beneath every AI-for-science system is not more generation but a **recomputation gate** — and
that licensing, defeat, drift, and FDR control are all the same mechanism. That is what this builds.
