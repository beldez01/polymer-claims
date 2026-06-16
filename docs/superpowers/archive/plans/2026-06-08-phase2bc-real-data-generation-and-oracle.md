# Phase 2b + 2c — Real-data LLM generation + apparatus oracle tier — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use `- [ ]`.

**Goal:** The live agent PROPOSES real-data `stats::mean_diff` plans (2b), runnable via `serve --real-data`; and an `OracleDossier` for the apparatus caps the licensed claim's empirical strength to its validation tier, with claims carrying a provisional strength so the cap is visible (2c).

**Architecture:** Umbrella-only (`polymer_claims`); ZERO grammar/protocol changes. Reuses the 2a `mean_diff_claim` builder, the existing `Adapter`/`AdapterRegistry`/`OracleRegistry` seams, and `NodeRunner` (forwards `adapters` + `adapter_registry`/`oracles`/`proposers` through `tick → run_cycle`). Spec: `docs/superpowers/specs/2026-06-08-phase2bc-real-data-generation-and-oracle-design.md`.

**Tech Stack:** Python stdlib (`hashlib`, `json`); `polymer_grammar`/`polymer_protocol`. No new runtime dependency.

**Verify each task:** `cd /Users/zbb2/Desktop/polymer-claims && uv run --project . pytest tests/ -q && uv run --project . ruff check src tests`. ABSOLUTE paths. LOCAL only, no push.

**Confirmed facts (don't re-derive):**
- 2a `src/polymer_claims/exec_adapters.py` has `mean_diff_claim(claim_id, *, value_col="response", group_col="dose", group_a="high", group_b="low", comparator=Comparator.GT, threshold=10.0, ref="dose_response", title=..., ontology_term="dose-response") -> Claim` (builds a `stats::mean_diff` OperationNode + plan), `StatsPureAdapter`/`StatsStdlibAdapter`, `independent_registry()`. `datasets/load_dataset(ref) -> dict[str,list[str]]`.
- `llm_adapter.py` has module-level `_extract_json(raw)->dict|None`, `_COMPARATORS` ({"lt":Comparator.LT,...}), `Proposal` (imported from polymer_protocol), `hashlib`, `json`. `LLMGenerationAdapter._parse` pattern: parse → per proposal `_build_claim` in try/except `(KeyError,ValueError,TypeError)` → dedup vs `corpus.by_id().keys()` + a local `seen` set → `Proposal(operator_id=self.identity, claim=...)`.
- `OperationNode` accepts `oracle_ref: str | None = None`. `verify_stage` writes `strength=oracle_cap(c, registry)` on license; `oracles=None` → empty registry → a declared `oracle_ref` with no dossier caps goodness axes (magnitude/evidence_against_null/world_contact/certainty) to **0.0** (UNVALIDATED); a BENCHMARKED dossier caps them to **0.6**; non-goodness axes (severity/explanatory_virtue) are uncapped.
- Oracle types exported from `polymer_protocol`: `OracleRegistry(dossiers=(...))`, `OracleDossier(oracle_id, validation_tier, applicability_domain=ApplicabilityDomain(), ...)`, `ApplicabilityDomain(subject_kinds=())` (empty → unbounded, always in-domain), `ValidationTier.BENCHMARKED`. `StrengthVector(magnitude, certainty, evidence_against_null, severity, world_contact, explanatory_virtue)` from `polymer_grammar` (or `polymer_protocol`).
- `Provenance`/`GenerationMode` from `polymer_grammar`; `Provenance(generated_by=GenerationMode.AGENT_GENERATED, agent_id=<str>, search_cardinality=1, rationale=<str|None>)`.
- `tests/test_exec_adapters.py` already has `_CTX`, `_ADAPTERS=(StatsPureAdapter(),StatsStdlibAdapter())`, a `_corpus(claim)` helper mirroring conftest's `Corpus(claims=(c,), fdr_ledger=FDRLedger(target_fdr=0.05))`, and `_status(result, id)`. REUSE them.
- `NodeRunner.from_seed(corpus, *, adapters=_ADAPTERS, ctx=_CTX, scheduler_budget=1e9, max_frames=10000, **run_cycle_kwargs)`. `cli.py` `_cmd_serve` builds the `--llm` proposer via `_build_llm_proposer(model)` + `every_n_ticks(p, n=args.llm_every)`; missing-key pattern: `try: ... except RuntimeError as exc: print(str(exc), file=sys.stderr); return 1`. `_CTX`/`_ADAPTERS` are module constants in cli.py too.

---

### Task 1: `mean_diff_claim` gains oracle_ref + provisional strength + rationale; `apparatus_oracle_registry()` (2c core)

**Files:**
- Modify: `src/polymer_claims/exec_adapters.py`
- Test: `tests/test_exec_adapters.py` (append)

- [ ] **Step 1: Write failing tests** (append to `tests/test_exec_adapters.py`):

```python
from polymer_claims.exec_adapters import apparatus_oracle_registry


def test_mean_diff_claim_carries_oracle_ref_and_strength():
    c = mean_diff_claim("c-meta")
    node = c.evaluation_plan.graph.nodes[0]
    assert node.oracle_ref == "dose_response_apparatus"
    assert c.strength is not None
    assert c.provenance is None  # no rationale passed


def test_mean_diff_claim_rationale_sets_provenance():
    c = mean_diff_claim("c-rat", rationale="because dose drives response")
    assert c.provenance is not None
    assert c.provenance.rationale == "because dose drives response"


def test_benchmarked_oracle_caps_goodness_axes_to_0_6():
    c = mean_diff_claim("c-cap", comparator=Comparator.GT, threshold=10.0)
    result = run_cycle(_corpus(c), _ADAPTERS, _CTX,
                       adapter_registry=independent_registry(),
                       oracles=apparatus_oracle_registry())
    lic = next(x for x in result.corpus.claims if x.id == "c-cap")
    assert lic.status == Status.LICENSED
    assert lic.strength.magnitude == 0.6          # goodness axis capped
    assert lic.strength.world_contact == 0.6
    assert lic.strength.certainty == 0.6
    assert lic.strength.evidence_against_null == 0.6
    assert lic.strength.severity == 0.5           # non-goodness axis uncapped


def test_declared_oracle_without_registry_caps_to_unvalidated():
    c = mean_diff_claim("c-unval", comparator=Comparator.GT, threshold=10.0)
    result = run_cycle(_corpus(c), _ADAPTERS, _CTX, adapter_registry=independent_registry())
    lic = next(x for x in result.corpus.claims if x.id == "c-unval")
    assert lic.status == Status.LICENSED
    assert lic.strength.magnitude == 0.0          # oracle_ref declared but no dossier -> UNVALIDATED
```

- [ ] **Step 2: Run to verify fail**

Run: `cd /Users/zbb2/Desktop/polymer-claims && uv run --project . pytest tests/test_exec_adapters.py -q`
Expected: FAIL — `apparatus_oracle_registry` undefined; `oracle_ref`/`strength`/`provenance` assertions fail.

- [ ] **Step 3: Modify `mean_diff_claim` + add helpers** in `src/polymer_claims/exec_adapters.py`. Add to the top-of-file imports: from `polymer_grammar` add `GenerationMode, Provenance, StrengthVector`; add `from polymer_protocol import OracleRegistry, OracleDossier, ApplicabilityDomain, ValidationTier` (alongside the existing `AdapterCredential, AdapterRegistry` import). Add module constants + edit the builder:

```python
_APPARATUS_ORACLE = "dose_response_apparatus"

# Provisional (asserted, pre-cap) empirical strength for a real-data mean_diff claim.
# Earned-from-data derivation is a documented follow-up (see docs/superpowers/notes/
# 2026-06-08-earned-strength-followup.md); the apparatus oracle tier caps these down.
_PROVISIONAL_STRENGTH = StrengthVector(
    magnitude=0.8, certainty=0.7, evidence_against_null=0.8,
    severity=0.5, world_contact=0.9, explanatory_virtue=0.6,
)
```

Then change the `mean_diff_claim` signature + body: add params `rationale: str | None = None` and `strength: StrengthVector | None = _PROVISIONAL_STRENGTH`; set `oracle_ref=_APPARATUS_ORACLE` on the `OperationNode`; build provenance from rationale; pass `strength`+`provenance` to the `Claim`:

```python
def mean_diff_claim(
    claim_id: str,
    *,
    value_col: str = "response",
    group_col: str = "dose",
    group_a: str = "high",
    group_b: str = "low",
    comparator: Comparator = Comparator.GT,
    threshold: float = 10.0,
    ref: str = "dose_response",
    title: str = "high vs low dose mean difference",
    ontology_term: str = "dose-response",
    rationale: str | None = None,
    strength: StrengthVector | None = _PROVISIONAL_STRENGTH,
) -> Claim:
    """Build a PENDING Claim whose plan computes mean_diff over a bundled dataset.
    Carries an apparatus oracle_ref (so its empirical strength is tier-capped at verify)
    and a provisional StrengthVector. (In Phase 2b the LLM emits these.)"""
    node = OperationNode(
        id="n0",
        impl="stats::mean_diff",
        inputs=(DataHandle(ref=ref),),
        params=(
            ("value_col", value_col),
            ("group_col", group_col),
            ("group_a", group_a),
            ("group_b", group_b),
        ),
        oracle_ref=_APPARATUS_ORACLE,
        produces=ProducedLeafSpec(leaf_kind="quantity", measurement_basis=MeasurementBasis.DERIVED),
    )
    plan = EvaluationPlan(
        graph=ComputeGraph(nodes=(node,), terminal="n0"),
        criterion=SatisfactionCriterion(comparator=comparator, threshold=threshold),
    )
    provenance = None
    if rationale is not None:
        provenance = Provenance(
            generated_by=GenerationMode.AGENT_GENERATED,
            agent_id="llm-meandiff-proposer",
            search_cardinality=1,
            rationale=rationale,
        )
    return Claim(
        id=claim_id,
        title=title,
        pattern=PatternRef(id="adjusted_effect", version="v1"),
        leaves=(CategoricalLeaf(ontology_term=ontology_term),),
        status=Status.PENDING,
        pending_reason=PendingReason.UNTESTED,
        strength=strength,
        provenance=provenance,
        evaluation_plan=plan,
    )


def apparatus_oracle_registry() -> OracleRegistry:
    """Oracle dossier for the bundled mean_diff apparatus: BENCHMARKED (validated against a
    computational ground-truth set), unbounded domain. Supplying it to run_cycle caps a
    licensed claim's empirical strength to the BENCHMARKED ceiling (0.6); omitting it leaves
    the declared oracle_ref UNVALIDATED (0.0)."""
    return OracleRegistry(dossiers=(
        OracleDossier(
            oracle_id=_APPARATUS_ORACLE,
            validation_tier=ValidationTier.BENCHMARKED,
            applicability_domain=ApplicabilityDomain(),
        ),
    ))
```

- [ ] **Step 4: Run to verify pass**

Run: `cd /Users/zbb2/Desktop/polymer-claims && uv run --project . pytest tests/test_exec_adapters.py -q`
Expected: PASS (all old 2a tests + the 4 new ones). The 2a status-only tests still pass (oracle_ref/strength don't change status). Then `uv run --project . ruff check src tests` (clean).

- [ ] **Step 5: Commit**

```bash
cd /Users/zbb2/Desktop/polymer-claims
git add src/polymer_claims/exec_adapters.py tests/test_exec_adapters.py
git commit -m "feat(exec): mean_diff_claim oracle_ref + provisional strength + rationale; apparatus_oracle_registry (2c)"
```
(End every commit with a blank line then `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`.)

---

### Task 2: `MeanDiffGenerationAdapter` — the LLM real-data generator (2b)

**Files:**
- Modify: `src/polymer_claims/llm_adapter.py`
- Test: `tests/test_real_data_generation.py` (create)

- [ ] **Step 1: Write failing tests** in `tests/test_real_data_generation.py`:

```python
import json

from polymer_protocol import Corpus
from polymer_grammar import FDRLedger
from polymer_claims.llm_adapter import MeanDiffGenerationAdapter

_DSL = {"proposals": [{
    "title": "high dose lifts response", "value_col": "response", "group_col": "dose",
    "group_a": "high", "group_b": "low", "comparator": "gt", "threshold": 10.0,
    "rationale": "dose drives response",
}]}


def _empty_corpus():
    return Corpus(claims=(), fdr_ledger=FDRLedger(target_fdr=0.05))


def test_proposes_a_mean_diff_claim_from_dsl():
    adapter = MeanDiffGenerationAdapter(lambda _p: json.dumps(_DSL))
    props = adapter.propose(_empty_corpus(), ())
    assert len(props) == 1
    claim = props[0].claim
    assert claim.id.startswith("gen-md-")
    node = claim.evaluation_plan.graph.nodes[0]
    assert node.impl == "stats::mean_diff"
    assert dict(node.params)["value_col"] == "response"
    assert claim.provenance.rationale == "dose drives response"


def test_invalid_column_is_dropped():
    bad = {"proposals": [{**_DSL["proposals"][0], "value_col": "__nope__"}]}
    adapter = MeanDiffGenerationAdapter(lambda _p: json.dumps(bad))
    assert adapter.propose(_empty_corpus(), ()) == ()


def test_bad_comparator_is_dropped():
    bad = {"proposals": [{**_DSL["proposals"][0], "comparator": "approx"}]}
    adapter = MeanDiffGenerationAdapter(lambda _p: json.dumps(bad))
    assert adapter.propose(_empty_corpus(), ()) == ()


def test_prompt_mentions_dataset_and_op():
    adapter = MeanDiffGenerationAdapter(lambda _p: json.dumps({"proposals": []}))
    prompt = adapter._build_prompt(_empty_corpus(), ())
    assert "dose_response" in prompt
    assert "mean" in prompt.lower()
    assert "response" in prompt and "dose" in prompt
```

- [ ] **Step 2: Run to verify fail**

Run: `cd /Users/zbb2/Desktop/polymer-claims && uv run --project . pytest tests/test_real_data_generation.py -q`
Expected: FAIL — `MeanDiffGenerationAdapter` undefined.

- [ ] **Step 3: Add `MeanDiffGenerationAdapter`** to `src/polymer_claims/llm_adapter.py` (it reuses module-level `_extract_json`, `_COMPARATORS`, `Proposal`, `hashlib`; imports `mean_diff_claim`/`load_dataset` lazily inside methods to avoid any import-order issue). Add a module constant `_MD_PREFIX = "gen-md-"` near `_GEN_PREFIX`:

```python
class MeanDiffGenerationAdapter:
    """A GenerationAdapter that maps an injected model's DSL into a REAL-DATA
    `stats::mean_diff` Claim over a bundled dataset (Phase 2b). Mirrors
    LLMGenerationAdapter but targets the real-execution substrate, not builtin::const."""

    def __init__(
        self,
        complete: Callable[[str], str],
        *,
        identity: str = "llm-meandiff-proposer",
        max_proposals: int = 5,
        dataset: str = "dose_response",
    ) -> None:
        self.complete = complete
        self.identity = identity
        self.max_proposals = max_proposals
        self.dataset = dataset

    def propose(self, corpus: Corpus, frontier: tuple[str, ...]) -> tuple[Proposal, ...]:
        return self._parse(self.complete(self._build_prompt(corpus, frontier)), corpus)

    def _build_prompt(self, corpus: Corpus, frontier: tuple[str, ...]) -> str:
        from .datasets import load_dataset
        data = load_dataset(self.dataset)
        cols = ", ".join(data.keys())
        groups = ", ".join(sorted(set(data["dose"]))) if "dose" in data else "(unknown)"
        lines = [f"- {c.id} [{c.pattern.id}] {c.title}" for c in sorted(corpus.claims, key=lambda c: c.id)[:20]]
        existing = "\n".join(lines) or "(none)"
        schema = (
            '{"proposals":[{"title":str,"value_col":str,"group_col":str,"group_a":str,'
            '"group_b":str,"comparator":"lt|le|gt|ge|eq|ne","threshold":number,"rationale":str}]}'
        )
        return (
            "You are a scientific-claim generator working over a REAL dataset. Propose up to "
            f"{self.max_proposals} NOVEL, testable claims, each a two-group MEAN DIFFERENCE on "
            f"dataset '{self.dataset}'.\n"
            f"Columns: {cols}. A numeric value column is 'response'. Group column 'dose' has "
            f"groups: {groups}.\n"
            "Each claim asserts: mean(value_col | group_col==group_a) − mean(value_col | "
            "group_col==group_b) <comparator> threshold.\n"
            "Output ONLY the JSON object, no prose, no markdown, matching:\n"
            f"{schema}\n\n"
            f"Existing claims:\n{existing}\n\nUnresolved frontier: {', '.join(frontier) or '(none)'}\n"
        )

    def _parse(self, raw: str, corpus: Corpus) -> tuple[Proposal, ...]:
        obj = _extract_json(raw)
        if obj is None:
            return ()
        existing_ids = set(corpus.by_id().keys())
        out: list[Proposal] = []
        seen: set[str] = set()
        for p in obj.get("proposals", []):
            try:
                claim = self._build_claim(p)
            except (KeyError, ValueError, TypeError):
                continue
            if claim.id in existing_ids or claim.id in seen:
                continue
            seen.add(claim.id)
            out.append(Proposal(operator_id=self.identity, claim=claim))
            if len(out) >= self.max_proposals:
                break
        return tuple(out)

    def _build_claim(self, p: dict):
        from .datasets import load_dataset
        from .exec_adapters import mean_diff_claim
        title = str(p["title"]).strip()
        value_col = str(p["value_col"]).strip()
        group_col = str(p["group_col"]).strip()
        group_a = str(p["group_a"]).strip()
        group_b = str(p["group_b"]).strip()
        cmp_key = str(p["comparator"]).strip().lower()
        if cmp_key not in _COMPARATORS:
            raise ValueError("bad comparator")
        if not (title and value_col and group_col and group_a and group_b):
            raise ValueError("empty required field")
        if group_a == group_b:
            raise ValueError("groups must differ")
        threshold = float(p["threshold"])
        data = load_dataset(self.dataset)  # unknown dataset -> raises -> dropped
        if value_col not in data or group_col not in data:
            raise ValueError("unknown column")
        rationale = str(p["rationale"]).strip() if p.get("rationale") else None
        cid = _MD_PREFIX + hashlib.sha256(
            f"{title}|{value_col}|{group_col}|{group_a}|{group_b}|{cmp_key}|{threshold}".encode()
        ).hexdigest()[:16]
        return mean_diff_claim(
            cid, value_col=value_col, group_col=group_col, group_a=group_a, group_b=group_b,
            comparator=_COMPARATORS[cmp_key], threshold=threshold, ref=self.dataset,
            title=title, rationale=rationale,
        )
```

- [ ] **Step 4: Run to verify pass**

Run: `cd /Users/zbb2/Desktop/polymer-claims && uv run --project . pytest tests/test_real_data_generation.py -q`
Expected: PASS (4 tests). Then `uv run --project . pytest tests/ -q` (no regressions) + `uv run --project . ruff check src tests` (clean).

- [ ] **Step 5: Commit**

```bash
cd /Users/zbb2/Desktop/polymer-claims
git add src/polymer_claims/llm_adapter.py tests/test_real_data_generation.py
git commit -m "feat(gen): MeanDiffGenerationAdapter — LLM proposes real-data mean_diff plans (2b)"
```

---

### Task 3: `real_data_seed_corpus()` + `serve --real-data` wiring (2b)

**Files:**
- Modify: `src/polymer_claims/exec_adapters.py` (add `real_data_seed_corpus`)
- Modify: `src/polymer_claims/cli.py` (`_build_real_data_proposer` + `--real-data` flag + serve branch)
- Test: `tests/test_real_data_generation.py` (append) and `tests/test_serve_cli.py` (append)

- [ ] **Step 1: Write failing test for the seed** (append to `tests/test_real_data_generation.py`):

```python
def test_real_data_seed_corpus_has_mean_diff_claims():
    from polymer_claims.exec_adapters import real_data_seed_corpus
    corpus, kwargs = real_data_seed_corpus()
    assert len(corpus.claims) >= 1
    assert all(c.evaluation_plan.graph.nodes[0].impl == "stats::mean_diff" for c in corpus.claims)
    assert "budget" in kwargs
```

- [ ] **Step 2: Run to verify fail** — `real_data_seed_corpus` undefined.

- [ ] **Step 3: Add `real_data_seed_corpus`** to `src/polymer_claims/exec_adapters.py` (uses `mean_diff_claim`; provides a `budget` for progressive licensing like `default_seed_corpus`):

```python
def real_data_seed_corpus() -> tuple["Corpus", dict]:
    """A tiny seed of real-data mean_diff claims so the live node isn't empty.
    Returns (corpus, run_cycle_kwargs). The LLM proposer is added by the caller (serve)."""
    from polymer_protocol import Corpus
    from polymer_grammar import FDRLedger
    claims = (
        mean_diff_claim("seed-md-1", comparator=Comparator.GT, threshold=10.0,
                        title="high dose raises response (seed)"),
        mean_diff_claim("seed-md-2", comparator=Comparator.GT, threshold=20.0,
                        title="high dose raises response by >20 (seed)"),
    )
    corpus = Corpus(claims=claims, fdr_ledger=FDRLedger(target_fdr=0.05))
    return corpus, {"budget": 2.5}
```
(`Comparator` and `mean_diff_claim` are already in-module from Task 1. Add `Corpus`/`FDRLedger` imports lazily inside the function as shown, or fold into the top imports if ruff prefers — keep it clean.)

- [ ] **Step 4: Run to verify the seed test passes** — `uv run --project . pytest tests/test_real_data_generation.py -q`.

- [ ] **Step 5: Write failing serve tests** (append to `tests/test_serve_cli.py`):

```python
def test_serve_real_data_threads_real_adapters_and_proposer(monkeypatch):
    seen = {}
    def fake_import():
        def run(app, host=None, port=None): pass
        def create_app(runner, *, interval, origins): seen["runner"] = runner; return "APP"  # noqa: E702
        import types as _t
        return _t.SimpleNamespace(run=run), create_app
    monkeypatch.setattr(cli, "_import_server", fake_import)
    import json
    from polymer_protocol import bridge_proposer
    from polymer_claims.llm_adapter import MeanDiffGenerationAdapter
    dsl = {"proposals": [{"title": "g", "value_col": "response", "group_col": "dose",
                          "group_a": "high", "group_b": "low", "comparator": "gt",
                          "threshold": 10.0, "rationale": "r"}]}
    monkeypatch.setattr(cli, "_build_real_data_proposer",
                        lambda model: bridge_proposer((MeanDiffGenerationAdapter(lambda _p: json.dumps(dsl)),)))
    rc = main(["serve", "--real-data", "--llm-every", "4"])
    assert rc == 0
    runner = seen["runner"]
    from polymer_claims.exec_adapters import StatsPureAdapter
    assert any(isinstance(a, StatsPureAdapter) for a in runner.adapters)  # real adapters wired
    for _ in range(8):
        runner.tick()
    assert any(c.id.startswith("gen-md-") and c.status.value == "licensed" for c in runner.corpus.claims)


def test_serve_real_data_missing_key_errors(monkeypatch, capsys):
    monkeypatch.setattr(cli, "_import_server",
        lambda: (__import__("types").SimpleNamespace(run=lambda *a, **k: None), lambda runner, **k: "APP"))
    monkeypatch.setattr(cli, "_build_real_data_proposer",
        lambda model: (_ for _ in ()).throw(RuntimeError("set ANTHROPIC_API_KEY to use --real-data")))
    rc = main(["serve", "--real-data"])
    assert rc == 1
    assert "ANTHROPIC_API_KEY" in capsys.readouterr().err
```

- [ ] **Step 6: Run to verify fail** — `_build_real_data_proposer` / `--real-data` undefined.

- [ ] **Step 7: Implement in `src/polymer_claims/cli.py`.**
  (a) Add the proposer builder near `_build_llm_proposer`:
```python
def _build_real_data_proposer(model: str):
    """Lazy-build a bridge_proposer over a MeanDiffGenerationAdapter (real-data generation).
    Raises RuntimeError with a key/extra hint if [llm] or ANTHROPIC_API_KEY is missing."""
    import os
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise RuntimeError("set ANTHROPIC_API_KEY to use --real-data")
    from polymer_protocol import bridge_proposer
    from .llm_adapter import MeanDiffGenerationAdapter, _anthropic_complete  # see note
    adapter = MeanDiffGenerationAdapter(_anthropic_complete(model))
    return bridge_proposer((adapter,))
```
  NOTE: reuse however `LLMGenerationAdapter.anthropic(model=...)` obtains its `complete` callable — read `_build_llm_proposer` + `LLMGenerationAdapter.anthropic` and mirror it (e.g. construct the Anthropic-backed `complete` the same way; if `anthropic()` is a classmethod that bundles the SDK call, add a sibling `MeanDiffGenerationAdapter.anthropic(model=...)` classmethod that builds the same `complete` and returns `MeanDiffGenerationAdapter(complete)`, then call that here instead of `_anthropic_complete`). Keep the lazy-import + missing-extra RuntimeError behavior identical to `LLMGenerationAdapter.anthropic`.

  (b) Add the `--real-data` arg to the `serve` subparser in `_build_parser` (next to `--llm`):
```python
p_serve.add_argument("--real-data", action="store_true",
                     help="LLM proposes REAL-DATA mean_diff plans; node runs the local execution adapters + apparatus oracle (needs [llm] + ANTHROPIC_API_KEY)")
```
  (c) In `_cmd_serve`, BEFORE the existing `--llm` handling, add a `--real-data` branch that takes precedence:
```python
    if getattr(args, "real_data", False):
        try:
            proposer = _build_real_data_proposer(args.llm_model)
        except RuntimeError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        from .throttle import every_n_ticks
        from .exec_adapters import (
            StatsPureAdapter, StatsStdlibAdapter,
            independent_registry, apparatus_oracle_registry, real_data_seed_corpus,
        )
        proposer = every_n_ticks(proposer, n=args.llm_every)
        corpus, seed_kwargs = real_data_seed_corpus()
        runner = NodeRunner.from_seed(
            corpus,
            adapters=(StatsPureAdapter(), StatsStdlibAdapter()),
            ctx=_CTX,
            scheduler_budget=args.budget,
            max_frames=args.max_frames,
            adapter_registry=independent_registry(),
            oracles=apparatus_oracle_registry(),
            proposers=(proposer,),
            **seed_kwargs,
        )
        app = create_app(runner, interval=args.interval, origins=args.origins or None)
        uvicorn.run(app, host=args.host, port=args.port)
        return 0
```
  Place this AFTER the loopback-guard + `_import_server()` block (so `uvicorn`/`create_app` exist and the host guard still applies) and BEFORE the `--llm`/default branches. The existing `--llm` (const) and default paths stay unchanged.

- [ ] **Step 8: Run to verify pass** — `uv run --project . pytest tests/test_serve_cli.py tests/test_real_data_generation.py -q` then full `uv run --project . pytest tests/ -q` + `uv run --project . ruff check src tests`. All green.

- [ ] **Step 9: Commit**

```bash
cd /Users/zbb2/Desktop/polymer-claims
git add src/polymer_claims/exec_adapters.py src/polymer_claims/cli.py tests/test_real_data_generation.py tests/test_serve_cli.py
git commit -m "feat(cli): serve --real-data — live node on the real execution substrate (2b) + apparatus oracle (2c)"
```

---

### Task 4: earned-strength follow-up note + full gate

**Files:**
- Create: `docs/superpowers/notes/2026-06-08-earned-strength-followup.md`

- [ ] **Step 1: Write the follow-up note** `docs/superpowers/notes/2026-06-08-earned-strength-followup.md` (~15-20 lines): the 2c first pass assigns a PROVISIONAL (asserted) `StrengthVector` in `mean_diff_claim` (`_PROVISIONAL_STRENGTH`), which the apparatus oracle tier caps. The rigorous extension: derive an EARNED strength from the actual verify result — magnitude from the standardized effect size of the computed mean difference, `evidence_against_null` from the margin over the criterion threshold (and, later, a real test statistic / n), `world_contact` from the data provenance — assigned at license time in `verify_stage` (a protocol-layer change touching the licensing seam), THEN capped by the oracle tier. Note this also generalizes when 2d adds real data sources. Reference `src/polymer_claims/exec_adapters.py` `_PROVISIONAL_STRENGTH` and `protocol/.../verify.py` (the `strength=oracle_cap(...)` lines).

- [ ] **Step 2: Full gate**

```bash
cd /Users/zbb2/Desktop/polymer-claims
bash scripts/check-all.sh 2>&1 | tail -5
bash scripts/build_and_test_install.sh 2>&1 | tail -3
```
Expected: `ALL GREEN` + install SUCCESS.

- [ ] **Step 3: Commit**

```bash
cd /Users/zbb2/Desktop/polymer-claims
git add docs/superpowers/notes/2026-06-08-earned-strength-followup.md
git commit -m "docs: earned-strength follow-up note (2c first pass is provisional)"
```

---

## After all tasks

- `bash scripts/check-all.sh` ALL GREEN.
- Finish the branch with superpowers:finishing-a-development-branch (local merge no-ff to `main`, NO push).
- Update `docs/superpowers/CONTINUE.md` (2b+2c done; NEXT = 2d PolymerGenomicsAPI) + the knowledge-protocol memory.
- Manual live run (needs key): `serve --real-data --interval 3 --llm-every 4 --origins http://localhost:3001` + viewer → agent proposes mean_diff claims licensing on real computation, cards show rationale + a CAPPED (0.6) strength.

## Self-Review

- **Spec coverage:** 2b `MeanDiffGenerationAdapter` (Task 2) ✓; prompt advertises the dataset/op (Task 2 test) ✓; `serve --real-data` + real adapters + registry + seed (Task 3) ✓; 2c oracle_ref + provisional strength + `apparatus_oracle_registry` + cap (Task 1) ✓; oracles wired into serve (Task 3) ✓; earned-strength follow-up note (Task 4) ✓; scope fences (one dataset/op, no grammar/protocol change, const path unchanged) respected. ✓
- **Placeholder scan:** every code step is complete; the one NOTE (Task 3 `_build_real_data_proposer`) explicitly instructs mirroring `LLMGenerationAdapter.anthropic` and gives the exact fallback (a sibling `.anthropic` classmethod) — not a vague placeholder. ✓
- **Type consistency:** `mean_diff_claim` gains `rationale`/`strength` (Task 1) and is called with `rationale=` in Task 2; `apparatus_oracle_registry`/`independent_registry`/`real_data_seed_corpus`/`MeanDiffGenerationAdapter`/`_build_real_data_proposer`/`gen-md-` consistent across tasks; `_APPARATUS_ORACLE`/`oracle_ref` string identical; BENCHMARKED→0.6 / unresolved→0.0 consistent with the verify_stage facts. ✓
- **Grammar/protocol untouched:** all tasks edit umbrella files + docs only. ✓
