# Phase 2b + 2c — Real-data LLM generation + apparatus oracle tier (design)

**Date:** 2026-06-08 · **Branch:** `feat/real-data-generation-2bc` · **Status:** approved design

## Context

Phase 2a shipped real execution adapters: a claim's plan computes a two-group mean difference from a bundled dataset via two independent adapters, licensing/rejecting on the COMPUTED value, with the #5 trust registry biting. But the **live agent still proposes `builtin::const` plans** (2a's machinery was exercised by hand-built plans), and licensed claims carry **no empirical strength** (the card shows "—").

- **2b:** the LLM agent PROPOSES real-data (`stats::mean_diff`) plans, and a `serve --real-data` mode runs the live node on the real substrate — so the viewer shows claims licensing on real computation.
- **2c:** an `OracleDossier` for the apparatus caps the licensed claim's empirical strength to its validation tier (#2), and `mean_diff` claims carry a **provisional** `StrengthVector` so the cap is visible (earned-from-data strength is a documented follow-up).

Both are **umbrella-only; zero grammar/protocol changes** — they reuse the 2a `mean_diff_claim` builder, the existing `Adapter`/`AdapterRegistry`/`OracleRegistry` seams, and `NodeRunner` (which already forwards `adapters` + `adapter_registry`/`oracles`/`proposers` through `tick → run_cycle`).

## Confirmed API facts

- `LLMGenerationAdapter` (`src/polymer_claims/llm_adapter.py`): `__init__(complete, *, identity, max_proposals, allowed_patterns)`; `propose(corpus, frontier)` calls `self.complete(self._build_prompt(...))` then `self._parse(raw, corpus)`; `_parse` builds claims, dedups by id + against corpus, wraps in `Proposal(operator_id=self.identity, claim=...)`. Reuse `_extract_json` (module-level) for parsing.
- 2a `exec_adapters.py`: `mean_diff_claim(claim_id, *, value_col, group_col, group_a, group_b, comparator, threshold, ref, title, ontology_term) -> Claim`; `StatsPureAdapter`/`StatsStdlibAdapter`; `independent_registry() -> AdapterRegistry`. `load_dataset(ref)` in `datasets/`.
- `NodeRunner.from_seed(corpus, *, adapters=_ADAPTERS, ctx=_CTX, scheduler_budget, max_frames, **run_cycle_kwargs)`; `tick()` calls `run_cycle(self.corpus, self.adapters, self.ctx, ledger=self.ledger, **self.run_cycle_kwargs)`.
- `cli.py`: `_cmd_serve` already builds a throttled LLM proposer for `--llm` via `_build_llm_proposer(model)` + `every_n_ticks`. `serve` subparser flags live in `_build_parser`.
- Oracle (all exported from `polymer_protocol`): `OracleDossier(oracle_id, validation_tier, applicability_domain=ApplicabilityDomain(), ...)`, `ApplicabilityDomain(subject_kinds=(), predicates=())` — EMPTY subject_kinds ⇒ `in_domain` always True (unbounded). `OracleRegistry(dossiers=(...,))`. `ValidationTier.{UNVALIDATED,INDIRECT,BENCHMARKED,ANCHORED,GOLD}`; goodness-axis ceilings `{UNVALIDATED:0.0, INDIRECT:0.4, BENCHMARKED:0.6, ANCHORED:0.85, GOLD:1.0}` applied to `(magnitude, evidence_against_null, world_contact, certainty)` via `meet` (min); `severity`/`explanatory_virtue` uncapped. `oracle_cap` runs in `verify_stage`'s LICENSED seam over `referenced_oracle_ids(plan)` = the plan nodes' `OperationNode.oracle_ref`s. **An oracle_ref with NO matching dossier ⇒ UNVALIDATED ⇒ goodness axes capped to 0.0.**
- `StrengthVector(magnitude, certainty, evidence_against_null, severity, world_contact, explanatory_virtue)` — all 6 required, each in [0,1].

## Part 2b — Real-data LLM generation + `serve --real-data`

### Components (all `src/polymer_claims/`)

1. **`MeanDiffGenerationAdapter`** (new, in `llm_adapter.py` — it's LLM-generation machinery; imports `mean_diff_claim` from `.exec_adapters`, no cycle):
   - Same injected-`complete` shape as `LLMGenerationAdapter`; `identity="llm-meandiff-proposer"`.
   - `_build_prompt` describes the **bundled dataset schema** (dataset `dose_response`; `value_col` candidates `response`; `group_col` `dose` with groups `high`/`low`; mediators present) + the mean-diff op, and asks for STRICT JSON: `{"proposals":[{"title":str,"value_col":str,"group_col":str,"group_a":str,"group_b":str,"comparator":"lt|le|gt|ge|eq|ne","threshold":number,"rationale":str}]}`.
   - `_build_claim(p)` validates: `group_col`/`value_col` exist in `load_dataset("dose_response")`, comparator ∈ the 6, threshold numeric; then returns `mean_diff_claim(<content-addressed id>, value_col=…, group_col=…, group_a=…, group_b=…, comparator=…, threshold=…, title=…)`. Invalid → raise → dropped (mirrors `LLMGenerationAdapter._parse`). Content-addressed id prefix `gen-md-` for convergence/dedup.
   - `propose`/`_parse` mirror `LLMGenerationAdapter` (reuse `_extract_json`, dedup, `Proposal`). The rationale rides via `mean_diff_claim` once 2c adds the strength/provenance pass — for 2b, pass `rationale` into a provenance like the const adapter does (so the card shows it). *(If `mean_diff_claim` doesn't yet take rationale/provenance, 2b adds an optional `rationale=` param to it that sets `Provenance(generated_by=AGENT_GENERATED, agent_id=…, rationale=…, search_cardinality=1)`.)*

2. **`real_data_seed_corpus()`** (new, in `exec_adapters.py` or a small `real_data_seed.py`): returns `(corpus, kwargs)` — a 1–2 claim `mean_diff_claim` seed (so the universe isn't empty) + `kwargs` with `budget` (progressive licensing) like `default_seed_corpus`. No proposers in the seed (the LLM proposer is added by serve).

3. **`serve --real-data`** (`cli.py`): a new flag on the `serve` subparser. When set, `_cmd_serve`:
   - builds the real-data proposer: `_build_real_data_proposer(args.llm_model)` (sibling to `_build_llm_proposer`, but wraps a `MeanDiffGenerationAdapter` via `bridge_proposer`), then `every_n_ticks(proposer, n=args.llm_every)`; missing-key → stderr hint + `return 1`.
   - builds the node: `NodeRunner.from_seed(real_data_seed_corpus_corpus, adapters=(StatsPureAdapter(), StatsStdlibAdapter()), ctx=_CTX, adapter_registry=independent_registry(), oracles=apparatus_oracle_registry()  # (2c), proposers=(proposer,), scheduler_budget=…, max_frames=…, **seed_kwargs)`.
   - `--real-data` implies LLM real-data generation (needs `[llm]` + `ANTHROPIC_API_KEY`); composes with `--llm-model`/`--llm-every`/`--interval`/`--origins`. The existing `--llm` (const) path is unchanged.

### Data flow (2b)

LLM → mean_diff DSL → `MeanDiffGenerationAdapter` → `mean_diff_claim` (PENDING+plan over `dose_response`) → `bridge_proposer`/`compile_untrusted` (propose-not-license; AGENT_GENERATED) → live node `run_cycle` with the **stats adapters + independent registry** → claim licenses/rejects on the **computed mean difference** → viewer shows `plan: mean_diff(response | high vs low)` with the rationale.

## Part 2c — Apparatus oracle tier caps strength

### Components

1. **`mean_diff_claim` gains** (in `exec_adapters.py`): an `oracle_ref: str = "dose_response_apparatus"` set on the mean_diff `OperationNode`, and a `strength: StrengthVector | None = <provisional default>` set on the `Claim`. Provisional default (asserted, pre-cap): `StrengthVector(magnitude=0.8, certainty=0.7, evidence_against_null=0.8, severity=0.5, world_contact=0.9, explanatory_virtue=0.6)`. Back-compat: 2a tests assert status only, so still pass.
2. **`apparatus_oracle_registry()`** (new, in `exec_adapters.py`): `OracleRegistry(dossiers=(OracleDossier(oracle_id="dose_response_apparatus", validation_tier=ValidationTier.BENCHMARKED, applicability_domain=ApplicabilityDomain()),))`. BENCHMARKED is apt — a computational ground-truth set; unbounded domain so claims with `subject=None` are in-domain.
3. **Wiring:** the `serve --real-data` node passes `oracles=apparatus_oracle_registry()` (already in the 2b serve construction). `run_cycle`'s existing `oracle_cap` caps the licensed claim's goodness axes to **0.6** (BENCHMARKED).
4. **Follow-up note** `docs/superpowers/notes/2026-06-08-earned-strength-followup.md`: derive an EARNED `StrengthVector` from the actual verify result (|mean_diff|, margin over threshold, n) at license time instead of the provisional assertion — a protocol-layer change touching the verify/license seam, deferred.

### Data flow (2c)

A licensed `mean_diff` claim carries the provisional strength → `verify_stage` calls `oracle_cap(claim, apparatus_oracle_registry())` → goodness axes `meet` the BENCHMARKED ceiling 0.6 → the card shows `magnitude 0.6, certainty 0.6, evidence_against_null 0.6, world_contact 0.6, severity 0.5, explanatory_virtue 0.6` (no longer "—"). With NO oracle registry the same claim's goodness axes cap to 0.0 (UNVALIDATED) — declaring an apparatus you don't register is penalized.

## Error handling

- 2b: malformed DSL / unknown column / bad comparator → `_build_claim` raises → dropped (no crash), exactly like the const adapter. Prose-wrapped JSON handled by `_extract_json`; if the real model still wraps, tighten the prompt ("Output ONLY the JSON object").
- 2c: an oracle_ref with no dossier → UNVALIDATED cap (intended). `subject=None` + unbounded domain → in-domain (intended).

## Testing

- **2b unit:** a stubbed `complete` returning a valid mean_diff DSL → `MeanDiffGenerationAdapter.propose` yields a `Proposal` whose claim has a `stats::mean_diff` plan over `dose_response`; an invalid column / bad comparator is dropped; ids are `gen-md-*` and dedup against the corpus.
- **2b integration (stub, no network):** monkeypatch `cli._build_real_data_proposer` to a stub `bridge_proposer((MeanDiffGenerationAdapter(lambda _p: json.dumps(DSL)),))`; `main(["serve","--real-data","--llm-every","4"])` threads the stats adapters + registry + proposer into the runner; ticking licenses a `gen-md-*` claim (computed value). Missing-key → exit 1 + stderr hint.
- **2c unit/integration:** `mean_diff_claim(...)` has `evaluation_plan.graph.nodes[0].oracle_ref == "dose_response_apparatus"` and a non-None `strength`; running a true claim through `run_cycle(..., oracles=apparatus_oracle_registry())` licenses with goodness axes == 0.6; with `oracles=None` the goodness axes cap to 0.0; a `GOLD` dossier → 1.0 (uncapped).
- **Gate:** `bash scripts/check-all.sh` ALL GREEN; install-smoke clean; grammar/protocol untouched; existing 2a tests still pass.

## Files

- New: `src/polymer_claims/real_data_seed.py` (or a `real_data_seed_corpus()` in `exec_adapters.py`); `docs/superpowers/notes/2026-06-08-earned-strength-followup.md`.
- Modify: `src/polymer_claims/llm_adapter.py` (add `MeanDiffGenerationAdapter`); `src/polymer_claims/exec_adapters.py` (mean_diff_claim: `oracle_ref` + provisional `strength` + optional `rationale`; add `apparatus_oracle_registry()`); `src/polymer_claims/cli.py` (`--real-data` flag + `_build_real_data_proposer` + the real-data serve branch).
- New tests: `tests/test_real_data_generation.py` (2b unit + serve integration); extend `tests/test_exec_adapters.py` (2c oracle cap).

## Scope fences

- No grammar/protocol changes. No new runtime dependency. The const `serve --llm` path is unchanged.
- 2b: ONE dataset (`dose_response`) + ONE op (`stats::mean_diff`); the prompt advertises exactly that. Multi-dataset/op is a later slice.
- 2c: provisional (asserted) strength only; **earned-from-data strength is a documented follow-up** (`2026-06-08-earned-strength-followup.md`).
- 2d (PolymerGenomicsAPI as a second data source) remains separate.

## Verification (end-to-end)

1. `bash scripts/check-all.sh` → ALL GREEN; install-smoke clean.
2. Manual (needs key): `serve --real-data --interval 3 --llm-every 4 --origins http://localhost:3001` + viewer → agent proposes `mean_diff` claims that license/reject on real computation; clicking one shows `plan: mean_diff(...)`, the rationale, and a CAPPED strength (0.6 goodness axes) — not "—".
