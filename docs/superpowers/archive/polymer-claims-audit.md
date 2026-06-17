# Polymer Claims Full-Stack Audit

> **✅ CLOSED — remediated 2026-06-05/06.** Tier A+B hardening (`c662f1c`), the adapter trust registry
> (`67f98e3`, finding #5 — the one science-weighty item), and Tier-C polish (`2b7ccb5`) all merged; the
> v1.2-specific findings (#13–16) were deliberately **skipped** under the v1.2 freeze. The central
> thesis (*harden + make legible before adding features*) is satisfied. Residual open items are tracked
> in `ARCHITECTURE_CURRENT.md` and `docs/superpowers/CONTINUE.md` (adapter-independence byte-hashing,
> Pydantic→TS codegen, narrowing the protocol public API). Retained as the historical audit of record.

Date: 2026-06-05  
Scope: `/Users/zbb2/Desktop/polymer-claims`  
Mode: read-only project audit. No project files were changed.

## Executive Summary

Polymer Claims is a serious, unusually ambitious system: a v1.3 scientific-claim grammar (`grammar/`), a runtime protocol over that grammar (`protocol/`), an umbrella local-node package (`src/polymer_claims/`), a live 3D viewer (`viewer/`), and a frozen but still usable v1.2 fallback (`v1.2/`). The core architectural intent is coherent: grammar defines what a claim is; protocol defines how a claim corpus evolves; the root package hosts a local node; the viewer renders the evolving topology.

The main risk is not lack of code. The risk is boundary drift. The repo currently contains active v1.3 runtime code, frozen v1.2 public-submission surfaces, local-only server/viewer code, dense historical design logs, and documentation that sometimes describes older states as if they were current. A next implementation instance should first stabilize contracts and deployment boundaries before adding more science/runtime features.

Highest-priority issues:

1. Live server is not deployment-safe: unauthenticated mutation routes, no tick serialization, unbounded frame retention, and unbounded SSE queues.
2. Public/product documentation is split across incompatible stories: v1.3 local node, frozen v1.2 public corpus, and future polymerbio.org integration.
3. No active CI enforces the claimed test/ruff/build health; legacy workflows are archived and path-stale.
4. Protocol/viewer contracts are manually duplicated rather than generated or versioned.
5. The adapter air gap is identity-string based; no registry proves verifier independence.
6. v1.2 remains exposed through plugin/marketplace docs despite being frozen, and its evaluator can treat pinned JSON inference as license-grade evidence.

## Repository Map

| Area | Intended Role | Current State | Audit Read |
|---|---|---|---|
| `grammar/` | v1.3 claim IR and evaluator primitives | Active Python package with many tests and isolation intent | Strong core; contract tightening still needed |
| `protocol/` | Runtime/flywheel over grammar IR | Active Python package with selection, generation, verification, timeline/topology | Strong pure-runtime shape; public API too broad; validation-update discipline uneven |
| `src/polymer_claims/` | Umbrella CLI + live local node/server | Thin package over grammar/protocol plus mutable node host | Good local demo; not production-safe |
| `viewer/` | Next/React Three Fiber claim-universe viewer | Real UI consuming sample/live topology streams | Valuable product surface; weak test/type/lint gates |
| `v1.2/` | Frozen fallback FormalClaim ecosystem | Package, corpus, plugin, schemas, legacy workflows retained | Useful fallback but still reads as active in several places |
| `docs/superpowers/` | Design/status memory | Rich but dense phase logs and specs | Useful for continuity; poor as public roadmap |

## Critical Findings

### 1. Live Node Mutation API Is Not Safe Beyond Localhost

`src/polymer_claims/server.py` exposes `POST /step`, `/pause`, and `/resume` without authentication, CSRF protection, or a hard local-only guard. The CLI defaults to `127.0.0.1`, but it also allows arbitrary `--host`; binding to `0.0.0.0` would expose mutable node controls to any reachable client.

Recommended fix:

- Require an explicit `--unsafe-remote-control` or token for non-loopback bind.
- Protect mutating routes with a bearer token or local-only middleware.
- Split read-only viewer endpoints from control endpoints.

### 2. NodeRunner Can Be Mutated Concurrently

The FastAPI ticker and `/step` route both call the same `_do_tick()` path against a mutable `NodeRunner`. There is no lock or command queue. Concurrent ticks can race on `corpus`, `ledger`, `frame_index`, `prev_positions`, and `frames`.

Recommended fix:

- Serialize all runner mutation behind one `asyncio.Lock`.
- Prefer a command queue if future controls grow.
- Add a test that concurrent `/step` calls produce strictly increasing, gap-free frame indexes.

### 3. Live Timeline Retention Is Unbounded

`NodeRunner.frames` grows forever, `/timeline` returns all frames, and each SSE subscriber gets an unbounded `asyncio.Queue`. A slow client or long-running server can grow memory without bound. The live-node spec mentions a max-frame concept, but the CLI/server do not implement one.

Recommended fix:

- Add `max_frames` retention to `NodeRunner`.
- Add bounded subscriber queues with drop-oldest or disconnect policy.
- Make `/timeline` support windowing or latest-N semantics.

### 4. Internal Model Updates Often Bypass Validation

Several protocol stages use `model_copy(update=...)`, which bypasses Pydantic validators unless manually revalidated. Some use sites are benign or followed by targeted validation, but the pattern is broad enough to become a real integrity risk as trust boundaries open.

Notable areas:

- `protocol/src/polymer_protocol/generate.py` folds claims/edges into `Corpus`.
- `protocol/src/polymer_protocol/select.py` stamps provenance/search cardinality.
- `protocol/src/polymer_protocol/integrate.py` updates claims, edges, and FDR ledger.
- `grammar/src/polymer_grammar/fdr.py` appends tests.

Recommended fix:

- Add small validated constructors/helpers for claim and corpus updates.
- At minimum, revalidate `Corpus` at `run_cycle` exit and after untrusted generation/injection.
- Reserve raw `model_copy(update=...)` for local scalar fields where invariants cannot be violated, and document those cases.

### 5. Adapter Air Gap Is Not an Independence Guarantee

`grammar/src/polymer_grammar/evaluate.py` requires two distinct adapter identities before minting `Satisfaction`, which is a good structural rule. But identity uniqueness is only a string check; the docstring correctly notes that true independence must be enforced by a registry/protocol layer. That layer does not yet exist.

Recommended fix:

- Define an adapter registry with implementation hash, owner identity, version, capabilities, and independence policy.
- Record adapter registry IDs in materialization/evaluation output.
- Refuse license-grade verification when two adapters share owner, implementation lineage, or untrusted provenance.

## Important Findings

### 6. Documentation Describes Multiple Current Products

The root README presents v1.3 grammar/protocol as active, but parts still say protocol is future work or list stale phase status. `v1.2/corpus` and `v1.2/plugins/claim-harness` still describe public claim submission, CI, hooks, and portal behavior as if active. `docs/superpowers/CONTINUE.md` is valuable but too dense to act as canonical onboarding.

Recommended fix:

- Create a short `ARCHITECTURE_CURRENT.md` or rewrite the README top section around current truth:
  - active: v1.3 grammar/protocol/root local node/viewer
  - frozen: v1.2 package/corpus/plugin
  - future/user-gated: PyPI publish, PolymerGenomicsAPI integration, public corpus revival
- Add frozen banners to v1.2 contribution/plugin docs.
- Split `CONTINUE.md` into current state, roadmap, and historical log.

### 7. v1.2 Is Frozen But Still Distributed Through Active Surfaces

`v1.2/README.md` says frozen fallback, but `.claude-plugin/marketplace.json` points at the v1.2 claim harness, and skills still instruct agents to author v1.2 FormalClaim drafts. That is not necessarily wrong, but it must be labeled as legacy-active or frozen-disabled.

Recommended fix:

- Decide one policy:
  - legacy-active: keep plugin installable, but banner it as v1.2-only and not the v1.3 path.
  - frozen-disabled: remove from active marketplace until a v1.3 authoring harness exists.
- Do not let users think v1.2 submissions exercise the v1.3 runtime.

### 8. No Active CI

There is no active `.github/workflows` directory. Legacy workflows live under `v1.2/legacy-workflows` and still reference old paths such as `corpus/...`, `formalclaim`, and root scripts that moved under `v1.2/`. The repo relies on local claims of green tests rather than enforced checks.

Recommended fix:

- Add active CI for:
  - root: `uv run pytest -q`, `uv run ruff check src tests`
  - grammar: `uv run pytest -q`, `uv run ruff check src tests`
  - protocol: `uv run pytest -q`, `uv run ruff check src tests`
  - viewer: `npm run build`, `npm run typecheck`
- Rewrite legacy workflows before any reactivation; do not move them back as-is.

### 9. CLI Stdout Is Not Machine-Clean JSON

Several CLI commands print human summaries before writing JSON when `--out` is omitted. For example, `run-cycle` prints status/frontier before dumping the corpus; `export-timeline` prints frame count before dumping JSON. That makes stdout unsuitable for piping into JSON tools.

Recommended fix:

- Send summaries to stderr and JSON to stdout.
- Or require `--out` for JSON-producing commands and keep stdout human-only.
- Add CLI tests that parse stdout as JSON for export commands.

### 10. Protocol-to-Viewer Contract Is Manual and Fragile

Python defines topology/timeline DTOs in `protocol`, while TypeScript mirrors them manually in `viewer/src/lib/topology.ts` and `viewer/src/lib/timeline.ts`. `TopologyNode.strength` is especially fragile: Python exposes a tuple of floats, while the UI assumes an ordered six-axis vector.

Recommended fix:

- Generate JSON Schema from Pydantic models.
- Generate or validate TypeScript types from that schema in CI.
- Add a contract version field to topology/timeline exports.
- Encode strength as named fields or enforce exact length/order in the export DTO.

### 11. Root Package Reaches Into Protocol Private Helpers

`src/polymer_claims/node.py` imports `_frame_stats` and `_n_licensed` from `polymer_protocol.timeline`. That makes root depend on protocol internals and can break silently if protocol refactors private helpers.

Recommended fix:

- Promote frame-stat construction to public protocol API, or
- Move live-node frame-stat assembly fully into root with duplicated tests.

### 12. Protocol Public API Is Too Broad

`polymer_protocol.__init__` exports a wide mix of stable contracts, scheduler internals, generation adapters, daemon tools, topology/timeline DTOs, and helper models. This invites downstream code to depend on unstable internals.

Recommended fix:

- Define public facades:
  - `polymer_protocol.runtime`
  - `polymer_protocol.contracts`
  - `polymer_protocol.adapters`
  - `polymer_protocol.experimental`
- Keep `__init__` small and stable.

## v1.2-Specific Findings

### 13. v1.2 Evaluator Can Treat Pinned JSON As License-Grade

The v1.2 evaluator maps true inference directly to `LICENSED`, while materialization defaults can skip live recomputation. This means submitted JSON can contain both statistics and inference logic that yield a license-grade verdict.

Recommended fix:

- Split verdicts into at least:
  - schema-valid
  - pinned-consistent
  - materialized/reproduced
  - licensed
- Require materialization, signed evidence, or explicit provenance for license-grade status.

### 14. v1.2 Corpus Evaluator Accepts `--schema` But Does Not Use It

`v1.2/corpus/evaluator/run_evaluator.py` accepts a `--schema` argument but marks it reserved and validates through Pydantic only. Legacy workflows pass the schema path, creating false assurance that JSON Schema drift is checked.

Recommended fix:

- Actually validate changed claim JSON against the pinned schema.
- Fail if JSON Schema and Pydantic model disagree.
- Add tests for schema/model drift.

### 15. v1.2 FormalClaim Has Little Direct Test Coverage

The v1.2 package contains schema, evaluator, materialization, nanopub, CLI, and MCP-related code, but direct tests appear absent. If v1.2 remains a fallback or plugin-distributed surface, this is a confidence gap.

Recommended fix:

- Add minimal unit tests around schema validation, evaluator verdicts, materialization drift, nanopub projection, and CLI behavior.
- If v1.2 is purely archival, state that only corpus-level fixtures are supported.

### 16. v1.2 MCP/Plugin Surfaces Are Over-Advertised

The v1.2 MCP server advertises validation/search-style tooling in docs, but `list_tools()` returns an empty list. The plugin README promises MCP servers and corpus tools that are not evidently implemented by the bundled FormalClaim MCP server. The submission script hardcodes `Local verdict: LICENSED` in the PR body after running validation, rather than parsing the actual verdict.

Recommended fix:

- Implement the advertised MCP tools or remove the claims from docs.
- Parse validator output in `open-pr.sh` and write the actual verdict.
- Make plugin docs clearly state v1.2-only behavior.

## Packaging And Developer Experience

### 17. Packaging Metadata Is Thin

Root, grammar, and protocol pyprojects define names, versions, and dependencies but lack common release metadata: readme, license expression, authors, classifiers, URLs, and stricter dependency bounds. Root depends on `polymer-protocol` and `polymer-grammar` without version constraints, relying on local uv path sources during development.

Recommended fix:

- Add package metadata before publish.
- Define release order and compatible bounds, e.g. `polymer-grammar>=0.1,<0.2`.
- Use one source of truth for versions instead of duplicating in pyproject and `__init__.py`.

### 18. Frontend Verification Is Too Thin

`viewer/package.json` only defines `dev`, `build`, and `start`. There is no `typecheck`, lint, unit test, Playwright smoke, screenshot regression, or canvas nonblank check. `tsconfig.json` uses `allowJs` and `skipLibCheck`, reducing type signal.

Recommended fix:

- Add `npm run typecheck`.
- Add linting or formatting gate.
- Add one Playwright smoke that loads the viewer, verifies canvas renders nonblank, and confirms live controls mount.
- Add a schema-contract test against generated topology/timeline fixtures.

### 19. Developer Quickstart Is Missing

The README is strong on vision but weak on fresh-clone operations. A new instance has to infer commands from package files and scripts.

Recommended fix:

- Add exact commands for:
  - installing root/grammar/protocol dev deps
  - running each Python test suite
  - running ruff
  - building viewer
  - starting `polymer-claims serve`
  - starting viewer and connecting to localhost
  - running the install smoke harness

## Product And UX Findings

### 20. The Best Product Surface Is Under-Documented

The live node and viewer are the most tangible user experience: local `polymer-claims serve` emits `/timeline` and `/stream`, and the Next viewer connects to `http://localhost:8000`. But the README does not present this as the primary quickstart.

Recommended fix:

- Make “Run the live universe locally” the first runnable path.
- Include two terminals:
  - server: `polymer-claims serve`
  - viewer: `cd viewer && npm run dev`
- Explain sample mode versus live mode in one paragraph.

### 21. Terminology Debt Is High

The repo uses many overlapping terms: FormalClaim, grammar, protocol, corpus, claim harness, node, topology, timeline, viewer, portal, PolymerGenomicsAPI, superpowers, IR, runtime, flywheel. Some are versioned; some are product names; some are implementation modules.

Recommended fix:

- Add a glossary.
- Reserve “FormalClaim” for v1.2.
- Reserve “grammar” for v1.3 IR.
- Reserve “protocol” for runtime/flywheel.
- Reserve “node” for the local mutable host.
- Reserve “viewer” for the standalone Next/Three.js UI unless explicitly discussing polymerbio.org integration.

## Recommended Execution Order For Next Instance

### Phase 0: Freeze The Story

Goal: prevent future work from compounding confusion.

Tasks:

1. Write a canonical current architecture/status document.
2. Add frozen/legacy banners to v1.2 corpus/plugin docs.
3. Add local node + viewer quickstart.
4. Create a glossary.

Exit criteria:

- A new contributor can tell what is active, what is frozen, and what the next product milestone is in under five minutes.

### Phase 1: Make Local Node Safe Enough

Goal: make the implemented live experience robust before wider use.

Tasks:

1. Add lock/queue around runner mutation.
2. Add auth/local-only enforcement for mutating routes.
3. Add bounded frame retention and bounded SSE queues.
4. Add tests for concurrent stepping, retention, and slow-client behavior.

Exit criteria:

- The server can be run for hours locally without unbounded memory growth or tick races.

### Phase 2: Enforce Contracts

Goal: stop Python/TypeScript and protocol/root drift.

Tasks:

1. Generate JSON Schema for topology/timeline exports.
2. Generate or validate TS types.
3. Add contract version fields.
4. Promote private timeline helpers or stop importing them.
5. Narrow protocol public API.

Exit criteria:

- Viewer and protocol fail CI if their data contracts diverge.

### Phase 3: Restore Verification Infrastructure

Goal: make “green” real.

Tasks:

1. Add active CI for root, grammar, protocol, viewer.
2. Add frontend typecheck and Playwright smoke.
3. Fix CLI stdout JSON contracts.
4. Normalize packaging metadata and dependency bounds.

Exit criteria:

- Pull requests cannot merge with broken tests, lint, typecheck, build, or viewer smoke.

### Phase 4: Decide v1.2 Policy

Goal: either preserve v1.2 honestly or remove it from active paths.

Tasks:

1. Choose legacy-active or frozen-disabled.
2. If legacy-active: add tests and fix schema validation/materialization/license semantics.
3. If frozen-disabled: remove marketplace/plugin active install claims.
4. Define a v1.2-to-v1.3 migration package with fidelity reports and golden fixtures.

Exit criteria:

- v1.2 no longer creates false confidence or product confusion.

### Phase 5: Define Real Adapter/Oracle Trust

Goal: make license-grade verification meaningful outside deterministic reference adapters.

Tasks:

1. Design adapter registry.
2. Record adapter implementation identity and independence metadata.
3. Add oracle/materialization trust policy.
4. Refuse license-grade status for unverifiable adapter pairs.

Exit criteria:

- “Two implementations agreed” means more than “two identity strings differed.”

## Suggested Audit Labels

| Label | Meaning |
|---|---|
| deploy-blocker | Must fix before non-local deployment |
| contract-risk | Data/API contract can drift silently |
| provenance-risk | Evidence/licensing semantics are weaker than they appear |
| docs-drift | Documentation misleads implementers or users |
| ci-gap | Claimed quality is not automatically enforced |
| legacy-surface | v1.2 frozen code is still reachable through active UX |

## Final Judgment

This codebase has a strong conceptual spine and a substantial amount of real implementation. The v1.3 grammar/protocol split is the right architecture, and the local node plus live viewer is the clearest product wedge. The next instance should resist adding new protocol features until it hardens the local-node boundary, establishes generated contracts, and reconciles v1.2’s public-facing residue.

The most leverage is in making the existing system legible and safe: current-state docs, active CI, bounded live server, schema-driven viewer contracts, and a real adapter trust registry.
