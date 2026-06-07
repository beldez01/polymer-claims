# Polymer Claims — Current Architecture (the short, true version)

> One-page map of what is **active**, what is **frozen**, and what is **user-gated/future**, as of 2026-06-05.
> For the detailed phase-by-phase build log, see `docs/superpowers/CONTINUE.md` (continuity log — dense by design).
> For terminology, see `GLOSSARY.md`.

## The system in one line

A **compiler + runtime for science**: the grammar defines *what a claim is*; the protocol defines *how a corpus of claims evolves toward truth*; the local node *hosts* a running corpus; the viewer *renders* the evolving topology.

```
grammar  →  protocol            →  node (src/polymer_claims)  →  viewer
"what a     "how a corpus           a local mutable host           renders the live
 claim is"   evolves" (run_cycle      (NodeRunner + serve)          topology over SSE
             flywheel + daemons)
```

## Active (v1.3 — the real system)

| Path | Package | What it is | State |
|---|---|---|---|
| `grammar/` | `polymer_grammar` | The v1.3 claim IR — a 5-layer grammar (L0 sum-typed leaf → L4 AGM revision) + the air-gapped evaluator. | **Complete** — all 8 layer-phases merged. |
| `protocol/` | `polymer_protocol` | The runtime over the grammar: the `run_cycle` flywheel (generate → select → execute → verify → integrate) + 3 standing daemons (DRIFT / ORACLE-VALIDATION / RED-TEAM) + the `next_action` budget scheduler + topology/timeline exports. | **Complete** — all 5 sub-projects + daemons + scheduler merged. One-way dep on grammar (isolation-tested). |
| `src/polymer_claims/` | `polymer-claims` | The umbrella distribution: a CLI (`version`/`validate`/`run-cycle`/`loop`/`export-topology`/`export-timeline`/`serve`) over the complete runtime, plus the **live local node** (`NodeRunner` + a FastAPI SSE server behind the optional `[serve]` extra). | **Active** — `pip install polymer-claims` → local node works end-to-end. Local-only (see Hardening below). |
| `viewer/` | (Next 16 app) | The claims-universe 3D viewer (React Three Fiber, D2 metrological aesthetic). Plays a precomputed timeline (**sample mode**) or streams from a running node (**live mode**). | **Active** — `tsc`+`build` clean. |
| `docs/superpowers/` | — | Specs, plans (with Progress Logs), and `CONTINUE.md`. | Active continuity log. |

**Purity invariant:** `grammar/` and `protocol/` are pure/deterministic (no clock/random/IO; time-like inputs are passed in). The ONLY impure piece is the umbrella node/server (`NodeRunner` owns the loop/clock; the server owns the network). The `Corpus` is exactly 4 collections.

**Local-node hardening (2026-06-05):** the live server is bounded and serialized for hours-long local runs — `--max-frames` ring retention, an `asyncio.Lock` serializing ticks, bounded SSE queues, and a **non-loopback bind guard** (`serve --host` other than loopback refuses unless `--unsafe-remote-control` is passed). It is still **local-only**: the mutating routes (`/step`/`/pause`/`/resume`) are unauthenticated by design. Real auth/multi-tenant/deploy is the future federated step, not shipped.

**Agent-driven live node (2026-06-06):** the real `LLMGenerationAdapter` (the `[llm]` extra, Anthropic-backed) is built behind the existing generation-bus seam and can now drive the **live node** itself via `serve --llm` (flags: `--llm-model`, `--llm-every N`). The `every_n_ticks` throttle wrapper (`src/polymer_claims/throttle.py`) calls the inner proposer on the 1st tick then every Nth tick, making a live LLM loop watchable and affordable. The LLM adapter runs alongside the seed corpus's existing rival/revision proposers; the universe stays lively on quiet ticks. Substrate caveat: v1 plans execute on the deterministic reference adapters (`builtin::const`), so the agent's claims license on LLM-asserted values — the full generate→execute→license loop is real and agent-driven, but not real-data science; meaningful data execution is Phase 2 (real execution adapters, a separate future arc).

## Frozen (v1.2 — fallback, not the active path)

| Path | What it is |
|---|---|
| `v1.2/` | The complete v1.2 FormalClaim ecosystem (the `polymer_formalclaim` IR package, the 47-claim corpus, the `claim-harness` Claude Code plugin, schema, legacy workflows). Frozen 2026-06-01, kept as a fallback. |

**v1.2 does NOT exercise the v1.3 grammar/protocol runtime.** The `claim-harness` plugin remains installable (legacy-active), banner-labelled as v1.2-only. Known v1.2 limitations (left as-is under the freeze, not fixed): the v1.2 evaluator can treat pinned JSON inference as license-grade; its corpus evaluator accepts a `--schema` arg it does not use; it has little direct test coverage; its MCP/plugin docs over-advertise tools (`list_tools()` is empty). These matter only if v1.2 is ever un-frozen.

## User-gated / future (not done; needs an explicit go)

- **PyPI publish** of `polymer-claims` — the build + `[serve]` extra are ready; blocked operationally by the flagged `beldez01` GitHub account (Actions/OIDC suppressed account-wide). Publish locally with a token only when asked. This is also why there is **no active CI** — workflows would never run; `scripts/check-all.sh` is the local substitute.
- **PolymerGenomicsAPI / polymerbio.org integration** — lift `<ClaimUniverse>` + `theme.ts` + live mode into `PolymerGenomicsAPI/viewer/` to replace the obsolete `FormalClaimUniverse` there. The aesthetic already matches by construction; no API-repo change has been made.
- **Adapter trust registry** — today the evaluator's air gap requires two *distinct adapter identity strings*; true verifier independence (owner/implementation-lineage/version) needs a registry. The most science-weighty open item.
- **Federated / BYO-compute layer** — the eventual "users run their own node" vision; a `POST /inject` claim endpoint is a noted future hook on the live server.
- **Deferred audit Tier-C** — schema→TypeScript contract codegen, narrowing the protocol public API, broad `model_copy` revalidation. Tracked, not urgent.
