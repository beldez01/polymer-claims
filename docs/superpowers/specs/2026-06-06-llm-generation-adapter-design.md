# Real LLM Generation Adapter — Design Spec

**Date:** 2026-06-06
**Status:** Approved direction (forks resolved: real generation = LLM; v1 output = executable plan-bearing claims).
**Goal:** Make the flywheel actually GENERATE. Plug a real LLM operator into the existing #4b-3 `GenerationAdapter` bus seam so it proposes **executable, plan-bearing claims** that flow through select → execute → verify → license. The deterministic reference adapters stay; this adds the first real-intelligence generator.

## Where it lives (purity preserved)
- New module **`src/polymer_claims/llm_adapter.py`** — the umbrella `polymer_claims` package is the impure layer (it already hosts the node + server). **`grammar/` and `protocol/` stay pure and untouched; Corpus stays 4.** The model call (network, nondeterminism) is the ONLY impure part and is **injected**, so the adapter's own logic (prompt build + JSON→Claim mapping) is pure/deterministic and unit-testable with a stub.
- Optional extra **`polymer-claims[llm]`** (`anthropic>=0.40`). The core adapter needs no SDK — only the `.anthropic(...)` convenience constructor lazy-imports it.

## The seam it targets (already built, unchanged)
`GenerationAdapter` Protocol = `identity: str` + `propose(corpus, frontier) -> tuple[Proposal, ...]`. `bridge_proposer((adapter,))` wraps it onto the bus: forces `operator_id = identity`, runs `compile_untrusted` (rejects licensing/LICENSED/PENDING-without-plan; forces `AGENT_GENERATED` provenance; coerces edges provisional), drops rejected, plugs into `run_cycle(proposers=...)`. The adapter is **untrusted by construction** — it can PROPOSE but never LICENSE.

## The constrained proposal DSL (robustness)
The LLM does NOT emit the full frozen `Claim` JSON (huge, many invariants it would trip). It emits a small constrained JSON the **adapter** maps into a valid executable `Claim`:
```json
{"proposals": [
  {"title": "...", "pattern_id": "adjusted_effect", "ontology_term": "...",
   "value": 0.02, "comparator": "lt", "threshold": 0.05, "rationale": "..."}
]}
```
- `comparator ∈ {lt, le, gt, ge, eq, ne}` → grammar `Comparator`.
- The adapter constructs: `Claim(id=<content-addressed gen-llm-*>, title, pattern=PatternRef(pattern_id, "v1"), leaves=(CategoricalLeaf(ontology_term),), status=PENDING, pending_reason=UNTESTED, strength=None, evaluation_plan=EvaluationPlan(ComputeGraph(OperationNode(impl="builtin::const", params=(("value", str(value)),), produces=ProducedLeafSpec(quantity, DERIVED)), terminal), SatisfactionCriterion(comparator, threshold)))`. (Exactly the shape `protocol/tests` `make_plan` produces — so the reference adapters execute it and it can license.)
- **Executability is guaranteed by the adapter's construction**, not by the LLM. Any proposal with a missing/out-of-range field, unknown comparator, non-numeric value, or unknown `pattern_id` (validated against the corpus's pattern registry / a small allowlist) is **dropped** (counted, logged). `compile_untrusted` is the independent second gate.
- **Convergence:** content-addressed ids via `_gen_id("llm", <hash of title+value+threshold>)`; the adapter skips any corpus claim whose id starts with its `gen-llm-` prefix when building context, and dedups against existing ids (the bus already discards dup ids).

## The adapter
```
class LLMGenerationAdapter:
    identity: str = "llm-claim-proposer"
    def __init__(self, complete: Callable[[str], str], *, max_proposals=5, allowed_patterns=None): ...
    @classmethod
    def anthropic(cls, *, model="claude-...", api_key=None, **kw) -> "LLMGenerationAdapter": ...  # lazy-imports anthropic, builds `complete`
    def propose(self, corpus, frontier) -> tuple[Proposal, ...]:
        prompt = self._build_prompt(corpus, frontier)   # pure
        raw = self.complete(prompt)                      # impure (injected)
        return self._parse(raw, corpus)                  # pure: DSL JSON -> validated executable Claims -> Proposals
```
- `_build_prompt` (pure): a compact summary of the corpus (existing claim titles + patterns + conclusions, capped) + the unresolved `frontier`, instructing the model to propose up to `max_proposals` NOVEL, testable claims in the DSL, using only the allowed `pattern_id`s, NOT restating existing claims. Asks for STRICT JSON only.
- `_parse` (pure): extract the JSON object (tolerant of code-fences/prose around it), validate each proposal, build executable `Claim`s, wrap as `Proposal(operator_id=identity, claim=...)`. Robust: malformed top-level JSON → return `()`; per-proposal errors → skip that one.
- `complete` signature `Callable[[str], str]` keeps the adapter provider-agnostic and STUB-INJECTABLE in tests.

## Honesty caveat (documented, not hidden)
v1 plans use `builtin::const` — the only impl the reference adapters execute — so a generated claim's value + threshold are LLM-asserted. This proves the **plumbing** (real generation → executable → license) end-to-end, but the execution substrate is the deterministic reference adapters, NOT real data. **Meaningful data execution is gated on real execution adapters** (the Phase-8 "real adapters live outside the package" deferral) — a separate arc. A generated claim carries `provenance.generated_by=AGENT_GENERATED` (forced by `compile_untrusted`) so it is always distinguishable from human/imported claims; the oracle-tier (#2) + adapter-trust (#5) mechanisms are the path to making generated licenses carry real evidential weight once real adapters/oracles exist. The module docstring + the CLI help state this.

## Wiring
- `bridge_proposer((adapter,))` → a `Proposer` passed to `run_cycle(proposers=...)` or `NodeRunner.from_seed(..., proposers=(bridge_proposer((adapter,)),))`.
- A thin CLI seam: `polymer-claims run-cycle <corpus> --llm [--llm-model M]` and/or `serve --llm` that builds `LLMGenerationAdapter.anthropic(...)` from `ANTHROPIC_API_KEY` and wires the bridge. Lazy-imports the `[llm]` extra; prints a helpful hint if missing or the key is absent. The default (no `--llm`) stays fully deterministic. (Keep the CLI surface minimal; the adapter + bridge is the core deliverable.)

## Determinism / purity / invariants
- Engine pure/deterministic, grammar/protocol untouched, Corpus 4. The adapter's only impurity is the injected `complete`; with a stub, the whole path (and a `run_cycle` over it) is byte-deterministic. The `[llm]` extra is optional — core import + CLI work without it; `scripts/check-all.sh` + the install smoke run without installing `[llm]` or hitting the network.

## Acceptance
- Pure unit tests with a STUB `complete` (canned DSL JSON): `propose` yields valid `Proposal`s carrying executable `builtin::const` plans; malformed JSON → `()`; a per-proposal bad field (unknown comparator / non-numeric value / unknown pattern) → that one dropped, others kept; content-addressed ids stable; own-output skipped (convergence).
- End-to-end through `run_cycle` with the stub adapter via `bridge_proposer`: a generated PENDING+plan claim is admitted, SELECTed, EXECUTEd by the reference adapters, and reaches LICENSED (satisfying value), threading provenance `AGENT_GENERATED`. Belief-neutral + deterministic (byte-identical CycleResult across two runs with the same stub).
- `compile_untrusted` still rejects a forged-licensed proposal from this adapter (reuse the existing guard test pattern).
- Core CLI imports + `check-all.sh` green WITHOUT the `[llm]` extra. A real `.anthropic()` call is NOT exercised in tests (no network); it is smoke-doc'd only.

## Non-goals (this slice)
- Real execution adapters (computing from real data/oracles) — the substrate limitation above; the next arc.
- Plans beyond a single `builtin::const` node (multi-node graphs, composing real corpus leaves, referencing other claims' values).
- Embedding-neighbor seeding (the other modality) — a follow-on adapter behind the same seam.
- Prompt-injection hardening of corpus content fed into the prompt, retries/streaming, multi-provider beyond the injected `complete`, cost/token budgeting.
- Any push/publish; any GitHub Action (account flagged).
