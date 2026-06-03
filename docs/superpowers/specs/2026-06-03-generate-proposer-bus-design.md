# GENERATE — the proposer bus (protocol sub-project #4a)

> **Status:** design spec, approved 2026-06-03. Scope = **#4a** (the structural proposer-bus core
> + two pure endogenous operators + the exogenous port). The embedding/LLM operators and the
> grammar-blocked representation-revision lane are deferred (§9). Keystone source:
> `~/Desktop/Research/topics/epistemic-claim-foundations/generative-protocol/_FINAL_knowledge_generation_protocol.md`
> Stage 1 — GENERATE (≈ lines 38–52) + reverse-engineering row 235.

## 1. Purpose

The protocol runtime works end-to-end (REPRESENT → CANONICALIZE → SAFETY → SELECT → COMMIT →
EXECUTE → VERIFY → INTEGRATE) but nothing **proposes** — claims enter by the caller stuffing the
`Corpus` before `run_cycle`. GENERATE closes the flywheel: a **bus of proposers** that injects new
claims mid-cycle, so the frontier INTEGRATE emits becomes the next cycle's proposals.

The keystone is emphatic that **generation is an *open port*, not rule-governed**: exogenous
hypotheses (human, another model, literature) are first-class; the latent operators *populate* the
port but never *monopolize* it. #4a builds the **pure structural core** of that port and leaves the
intelligent (embedding/LLM) operators as **pluggable proposers behind the bus seam** — the same
move as the `Adapter` Protocol in EXECUTE (the air-gapped core is pure; real adapters live outside).

**Load-bearing scope decision:** #4a touches **zero grammar**. Generated origin rides on the
existing `provenance` (`generated_by` / `method` / `agent_id`); the discard log is ephemeral on
`CycleResult`. **Spine invariants preserved:** pure / deterministic, one-way isolation
(`protocol` → `grammar` only; never `v1.2/formalclaim`), `Corpus` stays at exactly 4 collections,
no LLM / no embeddings in the core.

## 2. Where it plugs into the spine

Keystone order: `REPRESENT → GENERATE → SAFETY → CANONICALIZE → SELECT → …`. Our spine currently
runs `canonicalize` before `safety_gate`; #4a inserts `generate_stage` **right after `represent`**,
preserving the existing canon/safety order:

```
represent → generate → canonicalize → safety_gate → select → commit → execute → verify → integrate
```

`generate_stage` reads the corpus + the frontier `represent` already emits, runs the proposer bus +
the exogenous injection, validates each proposal through `compile_to_IR`, and returns a new corpus
(new claims, plus any defeat edges a proposal carries) and an ephemeral `GenerationRecord`.

**New claims are `CONJECTURED` / no-plan, and the pure operators add no defeat edges**, so they are
**belief-neutral this cycle** — not SELECT candidates (SELECT requires `PENDING` + `evaluation_plan`),
not executed, and a fresh CONJECTURED node defeats nothing, so the **grounded extension of the
existing claims is unchanged**. This is why inserting after `represent` (whose scaffolding is already
computed) creates no stale-scaffolding problem: the scaffolding's grounded extension / frontier
describe the pre-generation claims, the executed claims this cycle are among them, and the generated
claims first act in the *next* cycle's `represent`. (An *exogenous* proposal that carries a
belief-changing defeat edge is the caller's responsibility — such a claim is normally a `PENDING`
hypothesis assessed on its own merits, not a graph rewrite; the pure endogenous operators never add
edges.)

## 3. The generation core

### 3.1 The bus (`generate.py`)

A `Proposer` is any callable with one signature:

```
Proposer = Callable[[Corpus, tuple[str, ...]], tuple[Proposal, ...]]
#                     corpus, frontier(claim ids)  -> proposals
```

`Proposal` (frozen `_Model`, in `corpus.py` to keep imports acyclic — see §3.4):

```
class Proposal(_Model):
    operator_id: str                       # e.g. "rival-generation"
    claim: Claim                           # the candidate (CONJECTURED, generated_by set)
    edges: tuple[DefeatEdge, ...] = ()      # defeat edges the proposal implies (frontier-attack)
```

`generate_stage` runs the passed-in proposers in the **caller-provided tuple order** (a
deterministic sequence — no need to sort by id, which a bare callable doesn't carry), concatenates
the exogenous injections (§3.5), runs every proposal through `compile_to_IR` (§3.3), and folds
survivors into the corpus. If two proposals share a content-addressed id (near-impossible across the
two operators, which hash distinct parts), the first in order wins deterministically. Each operator
embeds its own `operator_id` in every `Proposal` it emits (and uses it for the skip-own-output guard,
§3.6) — the bus never needs to know an id up front. Proposers are passed into `run_cycle` like
`adapters` / `cost_model`. Pure proposers are deterministic; the protocol **is** the seam where
external/LLM proposers plug in later.

### 3.2 The two pure operators (`proposers.py`)

Both are pure, deterministic, and **skip their own prior outputs** (the convergence guard, §3.6).

**`rival_generation`** — for each claim `C` with a conclusion `Proposition` (skip claims without a
conclusion, and skip claims this operator generated), emit a `CONJECTURED` rival claim for **each
`Direction` value other than `C`'s own** (`Direction` ∈ {POSITIVE, NEGATIVE, NULL}; a POSITIVE claim
yields NEGATIVE and NULL rivals — the complete rival set). Each rival:
- same `subject`, `pattern`, `leaves` as `C`; `status = CONJECTURED`; `evaluation_plan = None`;
- `conclusion` = `C.conclusion` with `direction` swapped and a `NeighborEdge(kind=INCOMPATIBLE_WITH,
  target=C.conclusion.content_hash)` added to its neighborhood (records the rivalry; once both
  license, the grammar's `derived_rebut_edges` can wire mutual rebut — full mutual wiring needs the
  source to also declare incompatibility, a #4b/exogenous concern, noted);
- `provenance` = generated (§3.4); deterministic id (§3.6).

This concretely populates the rival pool that L2 `rival_set_closure` needs.

**`frontier_attack`** — for each frontier node `F` (an unresolved-attack claim id), find its
**claim-sourced attackers** `B` (defeat edges with `target == F` whose `source` is a real claim id —
skip synthetic `:`-containing sources like `refutation:<id>`). For each `(F, B)`, emit a `CONJECTURED`
"defense" seed claim `D` — minimal-valid (title naming the challenge, `B`'s `pattern`, a single
`CategoricalLeaf(ontology_term="frontier-attack-<B>")`, no conclusion, no plan, generated
provenance) — and **no defeat edge**. This is the keystone closure made mechanical: the frontier the
cycle emits becomes a tagged generation target next cycle.

> **Why no edge — the belief-neutrality invariant (load-bearing).** In this spine an explicit defeat
> edge is *always* effective: `effective_defeats` filters an attack only when the target *strictly
> dominates* the source, so a **strengthless** `D`'s attack on `B` is **not** filtered — adding
> `D → B` would immediately defeat `B` and silently reinstate `F`, changing the grounded extension
> off an unvalidated conjecture. (The existing spine semantics, established and tested in #1, are
> that conjectured claims *do* attack and create frontiers — so there is no "inert explicit edge.")
> The only belief-neutral move is to add **no edge**: a fresh CONJECTURED node changes no other
> node's grounded-membership, so GENERATE stays a pure proposer. The actual `D ⊣ B` defeat is
> **derived later** — once `D` is executed and LICENSED, INTEGRATE's LICENSED-gated
> `derived_rebut_edges` (and a future provisional-edge mechanism) can wire it. **Generation
> proposes; only EXECUTE/VERIFY decides.**

> **Honest limitation (documented, not hidden):** pure operators enrich *structure* — a rival pool,
> a tagged frontier-defense seed. They do not author *content*, the defense's contradicting
> proposition, or an executable `evaluation_plan` (that needs domain knowledge), and they do not
> wire defeats (that is earned by validation). Executable novelty + content enter through the
> exogenous port (§3.5) and, later, the embedding/LLM operators (§9). #4a proves the bus + closes
> the loop structurally while staying strictly belief-neutral.

### 3.3 `compile_to_IR` — pressure-sensor, not just guillotine

Each proposal is validated; survivors fold in, failures are **discarded with a reason** into the
ephemeral `GenerationRecord`. #4a checks:
1. **structural validity** — the candidate is a well-formed grammar `Claim` (guaranteed by
   construction; a proposer that builds an invalid claim raises inside itself — the bus catches and
   logs `reason="invalid: <msg>"`);
2. **id de-duplication** — a candidate whose id already exists in the corpus is discarded
   `reason="duplicate"` (the idempotency rule, §3.6);
3. **referential validity** — any `edges` the proposal carries must resolve once the claim is added
   (target a real claim id; source = the new claim). An edge that would dangle ⇒ discard
   `reason="unresolved-edge"`.

The discard log is the structural seed the deferred MDL-recurrence / operator-5 lane will mine — we
**produce it now, consume it later** (§9). Richer checks (pattern-registry membership, oracle-exists)
are where the log gets interesting in #4b; #4a's proposers reuse valid patterns, so the load-bearing
#4a check is de-duplication.

```
class DiscardEntry(_Model):
    operator_id: str
    claim_id: str
    reason: str

class GenerationRecord(_Model):
    proposed: int = 0                       # total proposals seen
    admitted: tuple[str, ...] = ()          # claim ids folded in (sorted)
    discarded: tuple[DiscardEntry, ...] = ()
```

### 3.4 Generated provenance

Reuse the grammar `Provenance` (no new field). An endogenous proposal sets
`generated_by = GenerationMode.AGENT_GENERATED`, `agent_id = <operator_id>` (the grammar validator
requires `agent_generated ⇒ agent_id`), and `method = f"{operator_id}@{corpus_fingerprint}"`, where
`corpus_fingerprint = stable_sha(sorted(corpus claim ids))` — deterministic, records the generative
origin + the corpus state it was derived from. The exogenous port (§3.5) folds claims that carry
their own provenance, or stamps `generated_by = HUMAN_AUTHORED` / `IMPORTED` if absent.

### 3.5 The exogenous injection port

`run_cycle(..., injected: tuple[Claim, ...] = ())` — externally authored claims (human, another
model family, freshly ingested literature) enter through the **same** `compile_to_IR` path as the
bus and fold in. This is the real validated entry path replacing "stuff the Corpus before calling
`run_cycle`." **Executable hypotheses (claims *with* `evaluation_plan`s) arrive here**; the pure
endogenous operators only enrich structure. Injected claims keep their own provenance if present;
otherwise `generate_stage` stamps a minimal IMPORTED provenance (mirroring `commit`).

### 3.6 Determinism, idempotency, convergence (load-bearing)

- **Content-addressed ids.** Generated claim ids are
  `f"gen-{operator_short}-{stable_sha([operator_id, *parts])[:16]}"` (rival-gen parts =
  `[source_id, direction]`; frontier-attack parts = `[frontier_id, attacker_id]`). Dash-delimited
  (no `:`, to stay clear of the synthetic-edge-source convention). Deterministic ⇒ two identical
  `run_cycle` calls produce byte-identical results.
- **De-dup against existing ids.** A proposal whose id already exists in the corpus is discarded
  (§3.3 #2). This is the idempotency rule — mirrors `commit`'s "never overwrite."
- **Convergence guard.** Each operator **skips claims it generated itself** (detected via
  `provenance.method` starting with the operator id) and operates only on the corpus's
  **pre-generation** claims (proposals added this pass are not re-fed within the same pass). Without
  this, rival-generation would breed rivals-of-rivals forever (a rival has a conclusion, so id-dedup
  alone — different id each level — would *not* stop it). With it, the corpus **converges**: once
  every rival and frontier-defense exists, GENERATE adds nothing new. (`frontier_attack`'s outputs
  have no conclusion and are never themselves frontier nodes, so it self-converges via id-dedup; the
  skip-own-output guard is uniform belt-and-suspenders.)
- **Optional cap.** `run_cycle(..., generation_cap: int | None = None)` bounds proposals admitted
  per cycle (a stable-order truncation), a defensive bound; `None` = unbounded.

## 4. `run_cycle` signature

```
run_cycle(
    corpus, adapters, ctx, oracles=None, *,
    cost_model=None, budget=None, value_weights=..., cost_weights=...,   # #3a, unchanged
    proposers: tuple[Proposer, ...] = (),       # the endogenous bus
    injected: tuple[Claim, ...] = (),           # the exogenous port
    generation_cap: int | None = None,
) -> CycleResult   # now also carries `generation: GenerationRecord`
```

All new params keyword-only with defaults that reproduce pre-#4 behavior: `proposers=()` +
`injected=()` ⇒ `generate_stage` is a no-op (the corpus passes through unchanged, an empty
`GenerationRecord`), so the entire #1/#2/#3a suite stays green.

## 5. Files

All protocol-side; **no grammar changes**.

| File | New/Modify | Responsibility |
|---|---|---|
| `protocol/src/polymer_protocol/generate.py` | new | `Proposer` type, `compile_to_IR`, `generate_stage`, `_corpus_fingerprint`, `_gen_id` |
| `protocol/src/polymer_protocol/proposers.py` | new | `rival_generation`, `frontier_attack` |
| `protocol/src/polymer_protocol/corpus.py` | modify | `Proposal`, `DiscardEntry`, `GenerationRecord`; `generation: GenerationRecord` on `CycleResult` |
| `protocol/src/polymer_protocol/cycle.py` | modify | insert `generate_stage` after `represent`; thread `proposers`/`injected`/`generation_cap`; return `GenerationRecord` |
| `protocol/src/polymer_protocol/__init__.py` | modify | export the new public symbols |

## 6. Determinism & purity

- `generate_stage` is a pure `Corpus → (Corpus, GenerationRecord)` transform — no I/O, clock, or
  randomness; content-addressed ids; proposers sorted; `discarded`/`admitted` sorted.
- `Corpus` stays at exactly 4 collections — `GenerationRecord` is cycle-ephemeral output on
  `CycleResult`, never persisted state.
- The new claims and edges are existing grammar IR added to existing `Corpus` collections; the
  corpus-level referential-integrity validators already guard them (unique ids, resolvable edges).

## 7. Testing

**`proposers.py`** — `rival_generation` emits the correct other-direction rivals for a POSITIVE /
NEGATIVE / NULL conclusion, each marked `incompatible_with` the source; skips claims without a
conclusion; skips its own prior outputs. `frontier_attack` emits a `CONJECTURED` defense seed `D`
(no conclusion, **no defeat edge**) for each claim-sourced attacker of a frontier node; skips
synthetic (`:`-source) attackers; deterministic ids. **Belief-neutrality:** running a proposer over a
corpus must leave `grounded_extension` of the pre-existing claims unchanged (a `frontier_attack`
proposal adds an isolated CONJECTURED node and no edge — assert the grounded extension before/after
is identical).

**`generate.py`** — `compile_to_IR` discards a duplicate-id proposal (`reason="duplicate"`), an
unresolved-edge proposal (`reason="unresolved-edge"`); admits a valid one. `generate_stage` is a
no-op with no proposers/injections; folds bus + injected claims; writes a faithful
`GenerationRecord`; the exogenous port validates through the same path. **Convergence:** running
`generate_stage` twice with the same proposers admits zero new claims the second time.

**`cycle.py`** — a frontier-attack proposer over a corpus with an unresolved attack adds a defense
claim + edge that appears in next cycle's structure; an injected `PENDING`-with-plan claim flows
through GENERATE → SELECT → EXECUTE → VERIFY and can license; the full #1/#2/#3a suite stays green
with default (empty) generation; `CycleResult.generation` is populated; determinism — two identical
`run_cycle` calls byte-identical.

**Isolation** — the one-way guard still passes; no new grammar import of protocol.

## 8. Constants & conventions (v1, all named)

`GEN_ID_PREFIX = "gen"`, id-hash slice length `16`. Operator ids: `"rival-generation"`,
`"frontier-attack"`. `corpus_fingerprint = stable_sha(sorted(claim ids))`. No magic literals in
function bodies.

## 9. Scope boundary

**#4a (this spec):** §1–§8 — the proposer bus, `compile_to_IR` + discard log, `generated_by` trace,
exogenous port, two pure operators (rival-generation + frontier-attack), wiring into `run_cycle`,
determinism/idempotency/convergence.

**Deferred to #4b** (needs an embedding/LLM substrate, lives outside the pure core behind the bus
seam): latent-offset / analogical-transport, abductive, recombination operators; the per-operator
**credit ledger** (realized-truth credit redistribution + track-record-throttled budget share —
couples to SELECT value + the #5 daemons).

**Deferred — grammar-blocked:** operator-5 **schema-induction** + the **representation-revision
meta-corpus** + **MDL discard-recurrence mining**. These need the grammar's `representation_revision`
meta-tier (§5 #5), which is **unbuilt** — a separate grammar phase must land first. #4a *produces*
the discard log so that lane has something to mine when it arrives.

**Deferred (cross-cutting, noted elsewhere):** the EXPLORATORY serendipity pool; oracle-construction
as a first-class frontier node (binds to #2's oracle registry + the oracle-less generative queue);
exogenous-variance injection / tail-coverage (the D3 model-collapse guard).
