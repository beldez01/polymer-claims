# Live Agent Cycle — Implementation Plan (TONIGHT)

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Steps use `- [ ]`.
> Written 2026-06-06 to survive a context-clear. **Resume here: the goal is a LIVE viewer streaming a REAL LLM agent generating + licensing claims in real time.**

**Goal (tonight):** `polymer-claims serve --llm` runs a live node whose GENERATE stage is a **real LLM agent**; the viewer (live mode) shows the universe actually evolving — the agent proposes executable claims, they get selected, executed, and **light up as they license**, in a watchable rhythm.

**Why it's close:** every hard piece is already built + merged on `main`:
- Live node + SSE server + viewer live mode (`serve`, `/stream`, Connect → LIVE). ✓
- Real LLM generation adapter (`LLMGenerationAdapter`, injected `complete`, `.anthropic()`, `[llm]` extra) that emits **executable plan-bearing claims** and licenses end-to-end through `run_cycle`. ✓ (verified with a stub)
- `run-cycle --llm` CLI seam + the `_build_llm_proposer(model)` helper in `cli.py`. ✓

**The only gap:** the LLM proposer is wired into `run-cycle` but **NOT into the live node (`serve`)** — Task 3 of the LLM slice skipped `serve --llm` (the default-seed proposer merge was fiddly). Phase 1 closes exactly that, plus a tick-cadence throttle so a live loop is watchable + affordable.

**Verify (each task):** `cd /Users/zbb2/Desktop/polymer-claims && uv run --project . pytest tests/ -q && uv run --project . ruff check src tests`; `bash scripts/check-all.sh`; install smoke without extras `bash scripts/build_and_test_install.sh`. ABSOLUTE paths. LOCAL only, no push.

**Honesty caveat (carries over):** Phase 1 executes on the DETERMINISTIC REFERENCE adapters (`builtin::const`), so the agent's claims license on LLM-asserted values — this is the real generation→execute→license loop driven by a real agent, but NOT real-data science. Real-data execution is **Phase 2** (below). This is fine and intended for tonight: a real agent visibly growing + licensing a live universe is the deliverable.

---

## PHASE 1 — `serve --llm`: the live agent loop (TONIGHT)

Branch `feat/serve-llm-live-agent`.

### Task 1: a tick-throttle wrapper for proposers

**Files:** `src/polymer_claims/llm_adapter.py` (add a small helper) OR a new `src/polymer_claims/throttle.py`; Test `tests/test_throttle.py`.

**Why:** calling the LLM every tick (interval ~1.5–3s) is too costly/slow and floods the corpus. A throttle calls the inner proposer only every Nth invocation; on the other ticks it returns `()` so the engine SELECTs/EXECUTEs/LICENSEs the already-proposed claims — producing the burst → light-up → burst rhythm the viewer should show.

- [ ] **Step 1 — failing test:**
```python
from polymer_claims.throttle import every_n_ticks

def test_every_n_ticks_fires_on_multiples():
    calls = []
    inner = lambda corpus, frontier: (calls.append(1), ("proposal",))[1]  # returns a 1-tuple
    p = every_n_ticks(inner, n=3)
    out = [p(None, ()) for _ in range(7)]   # ticks 1..7
    # fires on the 1st call then every 3rd: ticks 1,4,7 -> non-empty; others empty
    assert [bool(o) for o in out] == [True, False, False, True, False, False, True]
    assert len(calls) == 3
```
- [ ] **Step 2 — confirm fail.**
- [ ] **Step 3 — implement** `every_n_ticks(inner: Proposer, *, n: int) -> Proposer`: a closure holding a mutable counter; fire `inner(corpus, frontier)` when `counter % n == 0` (so it fires on the FIRST call and every nth after), else return `()`. `n<=1` → always fire (pass-through). Document it's a stateful driver-layer wrapper (umbrella only; the engine stays pure). Type the param/return as the protocol `Proposer` alias.
- [ ] **Step 4 — green** (umbrella + ruff).
- [ ] **Step 5 — commit** `feat(node): every_n_ticks proposer throttle`.

### Task 2: `serve --llm` wires the agent into the live node

**Files:** `src/polymer_claims/cli.py`; Test `tests/test_serve_cli.py`.

- [ ] **Step 1 — failing tests:** (monkeypatch `cli._build_llm_proposer` to a stub `bridge_proposer((LLMGenerationAdapter(lambda _p: json.dumps(DSL)),))` — NO network)
```python
def test_serve_llm_threads_proposer_into_runner(monkeypatch):
    seen = {}
    def fake_import():
        def run(app, host=None, port=None): pass
        def create_app(runner, *, interval, origins): seen["runner"] = runner; return "APP"
        import types; return types.SimpleNamespace(run=run), create_app
    monkeypatch.setattr(cli, "_import_server", fake_import)
    import json
    from polymer_protocol import bridge_proposer
    from polymer_claims.llm_adapter import LLMGenerationAdapter
    dsl = {"proposals": [{"title": "g", "pattern_id": "adjusted_effect", "ontology_term": "g1",
                          "value": 0.01, "comparator": "lt", "threshold": 0.05}]}
    monkeypatch.setattr(cli, "_build_llm_proposer",
                        lambda model: bridge_proposer((LLMGenerationAdapter(lambda _p: json.dumps(dsl)),)))
    rc = main(["serve", "--llm", "--llm-every", "4"])
    assert rc == 0
    runner = seen["runner"]
    # the runner ticks; the LLM-generated claim eventually appears + licenses
    for _ in range(8):
        runner.tick()
    assert any(c.id.startswith("gen-llm-") and c.status.value == "licensed"
               for c in runner.corpus.claims)

def test_serve_llm_missing_key_errors(monkeypatch, capsys):
    monkeypatch.setattr(cli, "_import_server",
        lambda: (__import__("types").SimpleNamespace(run=lambda *a, **k: None), lambda runner, **k: "APP"))
    monkeypatch.setattr(cli, "_build_llm_proposer",
        lambda model: (_ for _ in ()).throw(RuntimeError("set ANTHROPIC_API_KEY to use --llm")))
    rc = main(["serve", "--llm"])
    assert rc == 1
    assert "ANTHROPIC_API_KEY" in capsys.readouterr().err
```
- [ ] **Step 2 — confirm fail.**
- [ ] **Step 3 — implement** in `_cmd_serve`: add args `--llm` (store_true), `--llm-model` (default "claude-sonnet-4-6"), `--llm-every` (int, default 4) to the `serve` subparser. When `args.llm`:
  - build `proposer = _build_llm_proposer(args.llm_model)` inside a `try/except RuntimeError` → stderr hint + `return 1` (same pattern as `run-cycle --llm`).
  - wrap it: `from .throttle import every_n_ticks; proposer = every_n_ticks(proposer, n=args.llm_every)`.
  - thread it into BOTH branches:
    - `--seed-corpus` branch: `NodeRunner.from_seed(corpus, scheduler_budget=..., max_frames=..., proposers=(proposer,))`.
    - default-seed branch: `kwargs["proposers"] = tuple(kwargs.get("proposers", ())) + (proposer,)` then `NodeRunner.from_seed(corpus, ..., **kwargs)` (so the LLM agent runs ALONGSIDE the seed's rival/revision proposers — the agent adds genuinely new hypotheses while the seed keeps the universe lively).
  - Default (no `--llm`) path unchanged.
- [ ] **Step 4 — green** (umbrella + ruff; protocol unaffected; the install smoke still passes WITHOUT `[serve]`/`[llm]` — core CLI imports clean).
- [ ] **Step 5 — commit** `feat(cli): serve --llm — live node driven by a real LLM agent`.

### Task 3: runbook + docs + a stub live-loop smoke

**Files:** `README.md`; `ARCHITECTURE_CURRENT.md`; Test `tests/test_serve_cli.py` (a stub end-to-end already covered by Task 2 — optionally add a multi-batch convergence assertion).

- [ ] **Step 1 — README "Watch a live agent" section** (under the live-universe quickstart), EXACT runbook:
```bash
pip install -e '.[serve,llm]'         # both extras
export ANTHROPIC_API_KEY=sk-ant-...
# Terminal 1 — the live agent node:
polymer-claims serve --llm --interval 3 --llm-every 4   # LLM proposes ~every 4th tick
# Terminal 2 — the viewer:
cd viewer && npm run dev               # http://localhost:3000 → Connect to http://localhost:8000
```
With the honesty caveat (reference-substrate execution) + a note: lower `--llm-every` / `--interval` = more agent activity (more cost); the agent runs alongside the seed proposers.
- [ ] **Step 2 — ARCHITECTURE_CURRENT.md:** move "real LLM generation" from a seam note to "the live node can be agent-driven (`serve --llm`)"; keep the substrate caveat + point Phase 2 at real execution adapters.
- [ ] **Step 3 — commit** `docs: live-agent runbook (serve --llm + viewer)`.

**After 1–3:** `bash scripts/check-all.sh` ALL GREEN; finish the branch (merge local no-ff, no push); update `CONTINUE.md` + memory. **THEN — the actual live run (needs the user's real key, so it's a manual step, not a test):** `serve --llm` + viewer, confirm real `gen-llm-*` nodes appear and license live. If the real model returns prose-wrapped JSON that `_extract_json` misses, tighten the prompt (add "Output ONLY the JSON object, no prose, no markdown") — a prompt tweak in `llm_adapter._build_prompt`, not an engine change.

---

## PHASE 2 — real execution adapters (the deeper arc; NOT tonight)

> This is what makes the agent's licenses mean real science instead of LLM-asserted constants. Scope it as its OWN spec+plan later; sketch only here.

The substrate today is `IdentityAdapter`/`ReferenceAdapter` executing `builtin::const`. Real execution = an `Adapter` (the Phase-8 grammar `Adapter` Protocol: resolves `DataHandle`s + executes `OperationNode`s) that computes from REAL data, so a generated plan's verdict reflects the world, not a number the LLM picked.

Design seeds (for the future spec):
- A real adapter pair with DISTINCT owners/impl-hashes (registered in the #5 `AdapterRegistry`) so cross-adapter agreement is GENUINE independence (the trust registry finally bites). e.g. two independent stats implementations, or two data sources.
- The LLM DSL grows to reference a real `impl` + a `DataHandle` (a dataset/query id) instead of a bare const — the adapter resolves + computes it. Candidate first substrate: the **PolymerGenomicsAPI** (a real queryable biophysics DB the user owns) as the data/oracle backend, or a local CSV/stats adapter for a self-contained demo.
- Oracle dossiers (#2) for the real apparatus → generated claims get a real `ValidationTier` cap (no more full-strength licenses from an unvalidated source).
- The air-gap (#5) + oracle-tier (#2) + online-FDR (#4) were ALL built for exactly this moment — Phase 2 is where they earn out.

Risks/unknowns to resolve in the Phase-2 spec: how the LLM emits a valid real-data plan (constrained DSL extension + validation), data-handle binding + caching, adapter independence in practice, cost/latency of real execution in a live loop, and whether to keep it local (self-contained adapter) or wire PolymerGenomicsAPI.

---

## Self-Review
- Phase 1 closes the one real gap (`serve --llm`) with a throttle for watchability; every step is concrete + stub-tested (no network in CI); the real run is a documented manual step (needs the user's key). ✓
- Purity/isolation: throttle + wiring live in the umbrella only; grammar/protocol untouched; `[serve]`/`[llm]` optional; core import/smoke clean without them. ✓
- Honesty caveat preserved; Phase 2 (real execution) explicitly scoped as the next, separate arc that makes licenses meaningful. ✓
