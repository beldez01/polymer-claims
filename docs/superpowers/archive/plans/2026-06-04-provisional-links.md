# Provisional Links #4b Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a provisional ("activate-on-license") defeat edge — inert while its source claim is not LICENSED, effective once it is — so GENERATE's `frontier_attack`/`rival_generation` can plant real-but-inert-until-validated rebuttals instead of isolated nodes.

**Architecture:** A small additive grammar change — `DefeatEdge.provisional: bool` + an optional `licensed_ids` set on `effective_defeats`/`grounded_extension` that skips provisional edges whose source isn't licensed (intrinsic, automatic activation/deactivation, no registry/stage). The protocol's `represent` (and grammar's AGM recompute `_in_set`) supply `licensed_ids`; the two GENERATE operators emit provisional rebut edges. Belief-neutral while conjectured (the edge is inert), and rivals use a rebut edge — never `incompatible_with` — so `_conflicts` never fires.

**Tech Stack:** Python 3.14, Pydantic v2 (frozen models), `uv`, `pytest`. Two packages: `grammar/` (`polymer_grammar`) and `protocol/` (`polymer_protocol`, one-way dep on grammar via path source — grammar source changes are immediately visible to protocol).

**Spec:** `docs/superpowers/specs/2026-06-04-provisional-links-design.md`

---

## Conventions

- **Grammar tasks run in `grammar/`:** `cd /Users/zbb2/Desktop/polymer-claims/grammar && uv run pytest -q`. **Protocol tasks run in `protocol/`:** `cd /Users/zbb2/Desktop/polymer-claims/protocol && uv run pytest -q`. Lint each with `uv run ruff check src tests` from that package dir.
- Commit after each task with the message shown. Commits are LOCAL only.
- This is a COORDINATED two-package change: Tasks 1–2 (grammar) land first; Tasks 3–5 (protocol) depend on them.

---

## File Structure

| File | Pkg | Change |
|---|---|---|
| `grammar/src/polymer_grammar/defeat.py` | grammar | `DefeatEdge.provisional` field; `licensed_ids` param + inert-skip on `effective_defeats`/`grounded_extension` |
| `grammar/src/polymer_grammar/revision.py` | grammar | `_in_set` passes `licensed_ids` to its `grounded_extension` recompute |
| `protocol/src/polymer_protocol/represent.py` | protocol | compute + pass `licensed_ids` to both grammar calls |
| `protocol/src/polymer_protocol/proposers.py` | protocol | both operators emit a provisional rebut edge |
| grammar + protocol tests | both | as below |

No new modules. `Corpus` unchanged (provisional edges live in the existing `defeat_edges`).

---

### Task 1: grammar — `DefeatEdge.provisional` + `licensed_ids`

**Files:**
- Modify: `grammar/src/polymer_grammar/defeat.py`
- Test: `grammar/tests/test_defeat.py`

- [ ] **Step 1: Write the failing tests** — append to `grammar/tests/test_defeat.py` (consolidate imports to the top to avoid ruff E402; `DefeatEdge`, `DefeatEdgeKind`, `effective_defeats`, `grounded_extension` are imported from `polymer_grammar` there):

```python
def test_defeat_edge_provisional_defaults_false():
    assert DefeatEdge(source="d", target="b", kind=DefeatEdgeKind.REBUT).provisional is False


def test_provisional_edge_inert_without_licensed_source():
    e = DefeatEdge(source="d", target="b", kind=DefeatEdgeKind.REBUT, provisional=True)
    strength = {"d": None, "b": None}
    assert effective_defeats((e,), strength) == frozenset()                          # default empty
    assert effective_defeats((e,), strength, licensed_ids=frozenset()) == frozenset()


def test_provisional_edge_effective_when_source_licensed():
    e = DefeatEdge(source="d", target="b", kind=DefeatEdgeKind.REBUT, provisional=True)
    strength = {"d": None, "b": None}
    assert effective_defeats((e,), strength, licensed_ids=frozenset({"d"})) == frozenset({("d", "b")})


def test_nonprovisional_edge_still_effective_from_conjectured_source():
    # LOAD-BEARING: a NORMAL edge from a strengthless source is STILL effective (#1 frontier semantics)
    e = DefeatEdge(source="d", target="b", kind=DefeatEdgeKind.REBUT)  # provisional=False
    strength = {"d": None, "b": None}
    assert effective_defeats((e,), strength) == frozenset({("d", "b")})


def test_grounded_extension_honors_provisional_activation():
    e_ba = DefeatEdge(source="b", target="a", kind=DefeatEdgeKind.REBUT)
    e_db = DefeatEdge(source="d", target="b", kind=DefeatEdgeKind.REBUT, provisional=True)
    strength = {"a": None, "b": None, "d": None}
    ids = ["a", "b", "d"]
    g0 = grounded_extension(ids, (e_ba, e_db), strength)                       # d not licensed -> inert
    assert "a" not in g0 and "b" in g0 and "d" in g0
    g1 = grounded_extension(ids, (e_ba, e_db), strength, licensed_ids=frozenset({"d"}))
    assert "a" in g1 and "b" not in g1 and "d" in g1                           # d licensed -> d defeats b -> a reinstated
```

- [ ] **Step 2: Run to verify they fail**

Run: `cd /Users/zbb2/Desktop/polymer-claims/grammar && uv run pytest tests/test_defeat.py::test_provisional_edge_effective_when_source_licensed -v`
Expected: FAIL — `effective_defeats() got an unexpected keyword argument 'licensed_ids'` (and `provisional` unknown field).

- [ ] **Step 3: Implement** — in `defeat.py`:

(a) Add the field to `DefeatEdge` (after `note`):
```python
    provisional: bool = False
```

(b) Change `effective_defeats` signature + add the skip (the new line is the `if e.provisional ...` check, placed right after the `ATTACK_KINDS` check):
```python
def effective_defeats(
    edges: Iterable[DefeatEdge],
    strength: Mapping[str, StrengthVector | None],
    licensed_ids: frozenset[str] = frozenset(),
) -> frozenset[tuple[str, str]]:
    out: set[tuple[str, str]] = set()
    for e in edges:
        if e.kind not in ATTACK_KINDS:
            continue
        if e.provisional and e.source not in licensed_ids:
            continue  # provisional: inert until its source claim is LICENSED
        s_src = strength.get(e.source)
        s_tgt = strength.get(e.target)
        if s_src is not None and s_tgt is not None and s_tgt.dominates(s_src):
            continue
        out.add((e.source, e.target))
    return frozenset(out)
```

(c) Change `grounded_extension`'s signature + pass `licensed_ids` to its internal `effective_defeats` call:
```python
def grounded_extension(
    claim_ids: Iterable[str],
    edges: Iterable[DefeatEdge],
    strength: Mapping[str, StrengthVector | None],
    licensed_ids: frozenset[str] = frozenset(),
) -> frozenset[str]:
    # ... docstring unchanged ...
    defeats = effective_defeats(edges, strength, licensed_ids)
    # ... rest of the body UNCHANGED ...
```

- [ ] **Step 4: Run to verify they pass**

Run: `cd /Users/zbb2/Desktop/polymer-claims/grammar && uv run pytest tests/test_defeat.py -v`
Expected: existing defeat tests + 5 new all PASS. Then the FULL grammar suite `uv run pytest -q` — green (back-compat: existing callers pass no `licensed_ids`, every existing edge has `provisional=False`). `uv run ruff check src tests`.

- [ ] **Step 5: Commit**

```bash
cd /Users/zbb2/Desktop/polymer-claims
git add grammar/src/polymer_grammar/defeat.py grammar/tests/test_defeat.py
git commit -m "feat(grammar): DefeatEdge.provisional + licensed_ids activation in the defeat graph

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: grammar — AGM recompute `_in_set` honors provisional activation

**Files:**
- Modify: `grammar/src/polymer_grammar/revision.py`
- Test: `grammar/tests/test_revision.py`

`_in_set` (revision.py ~156) is the central grounded recompute used by every AGM op. It must pass `licensed_ids` so a provisional edge from a LICENSED source is active in restore_consistency / revise / etc., consistent with `represent`. `Status` is already imported in `revision.py`.

- [ ] **Step 1: Write the failing tests** — append to `grammar/tests/test_revision.py` (it already imports `Status`, `DefeatEdge`, `DefeatEdgeKind`, and defines the `_claim(cid, prop=None, status=Status.LICENSED, strength=None)` helper; add `from polymer_grammar.revision import _in_set` to the top imports):

```python
def test_in_set_provisional_inert_when_source_not_licensed():
    a = _claim("a", status=Status.CONJECTURED)
    b = _claim("b", status=Status.CONJECTURED)
    d = _claim("d", status=Status.CONJECTURED)  # NOT licensed
    edges = (
        DefeatEdge(source="b", target="a", kind=DefeatEdgeKind.REBUT),
        DefeatEdge(source="d", target="b", kind=DefeatEdgeKind.REBUT, provisional=True),
    )
    in_set = _in_set((a, b, d), edges)
    assert "a" not in in_set and "b" in in_set  # provisional inert -> b defeats a


def test_in_set_honors_provisional_from_licensed_source():
    a = _claim("a", status=Status.CONJECTURED)
    b = _claim("b", status=Status.CONJECTURED)
    d = _claim("d", status=Status.LICENSED)  # licensed source -> provisional active
    edges = (
        DefeatEdge(source="b", target="a", kind=DefeatEdgeKind.REBUT),
        DefeatEdge(source="d", target="b", kind=DefeatEdgeKind.REBUT, provisional=True),
    )
    in_set = _in_set((a, b, d), edges)
    assert "a" in in_set and "b" not in in_set and "d" in in_set
```

- [ ] **Step 2: Run to verify they fail**

Run: `cd /Users/zbb2/Desktop/polymer-claims/grammar && uv run pytest tests/test_revision.py::test_in_set_honors_provisional_from_licensed_source -v`
Expected: FAIL — `_in_set` does not pass `licensed_ids`, so the provisional edge is inert even with `d` LICENSED → `"b" in in_set` (assertion `"b" not in in_set` fails).

- [ ] **Step 3: Implement** — change `_in_set` in `revision.py` to compute and pass `licensed_ids`:

```python
def _in_set(claims: tuple[Claim, ...], edges: tuple[DefeatEdge, ...]) -> frozenset[str]:
    """<keep the existing docstring>"""
    all_edges = tuple(edges) + derived_rebut_edges(claims)
    licensed = frozenset(c.id for c in claims if c.status == Status.LICENSED)
    return grounded_extension([c.id for c in claims], all_edges, _strength_map(claims), licensed)
```

- [ ] **Step 4: Run to verify they pass**

Run: `cd /Users/zbb2/Desktop/polymer-claims/grammar && uv run pytest tests/test_revision.py -v`
Expected: existing revision tests + 2 new all PASS. Then FULL grammar suite `uv run pytest -q` — green (existing AGM tests use non-provisional edges, unaffected). `uv run ruff check src tests`.

- [ ] **Step 5: Commit**

```bash
cd /Users/zbb2/Desktop/polymer-claims
git add grammar/src/polymer_grammar/revision.py grammar/tests/test_revision.py
git commit -m "feat(grammar): AGM _in_set recompute honors provisional-edge activation

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: protocol — `represent` supplies `licensed_ids`

**Files:**
- Modify: `protocol/src/polymer_protocol/represent.py`
- Test: `protocol/tests/test_represent.py`

- [ ] **Step 1: Write the failing tests** — append to `protocol/tests/test_represent.py` (consolidate imports to the top to avoid E402; it likely already imports `Corpus`, `represent`, `make_claim`; add `from polymer_grammar import DefeatEdge, DefeatEdgeKind, FDRLedger, Status` as needed):

```python
def test_represent_activates_provisional_edge_from_licensed_source():
    d = make_claim("d", status=Status.LICENSED)
    a = make_claim("a")  # CONJECTURED
    b = make_claim("b")  # CONJECTURED
    edges = (
        DefeatEdge(source="b", target="a", kind=DefeatEdgeKind.REBUT),
        DefeatEdge(source="d", target="b", kind=DefeatEdgeKind.REBUT, provisional=True),
    )
    corp = Corpus(claims=(a, b, d), defeat_edges=edges, fdr_ledger=FDRLedger(target_fdr=0.05))
    scaf = represent(corp)
    assert "a" in scaf.grounded_extension and "b" not in scaf.grounded_extension


def test_represent_provisional_inert_when_source_conjectured():
    d = make_claim("d")  # CONJECTURED -> provisional inert
    a = make_claim("a")
    b = make_claim("b")
    edges = (
        DefeatEdge(source="b", target="a", kind=DefeatEdgeKind.REBUT),
        DefeatEdge(source="d", target="b", kind=DefeatEdgeKind.REBUT, provisional=True),
    )
    corp = Corpus(claims=(a, b, d), defeat_edges=edges, fdr_ledger=FDRLedger(target_fdr=0.05))
    scaf = represent(corp)
    assert "a" not in scaf.grounded_extension  # b defeats a (provisional d->b inert)
    assert "a" in scaf.frontier
```

- [ ] **Step 2: Run to verify they fail**

Run: `cd /Users/zbb2/Desktop/polymer-claims/protocol && uv run pytest tests/test_represent.py::test_represent_activates_provisional_edge_from_licensed_source -v`
Expected: FAIL — `represent` doesn't pass `licensed_ids`, so the provisional `d->b` stays inert even with `d` LICENSED → `"a"` is NOT grounded.

- [ ] **Step 3: Implement** — modify `represent.py`:

Change the grammar import to add `Status`:
```python
from polymer_grammar import Status, effective_defeats, grounded_extension
```
Compute `licensed_ids` and pass it to both calls (replace the two call lines):
```python
def represent(corpus: Corpus) -> CycleScaffolding:
    claim_ids = [c.id for c in corpus.claims]
    id_set = set(claim_ids)
    strength = {c.id: c.strength for c in corpus.claims}
    licensed_ids = frozenset(c.id for c in corpus.claims if c.status == Status.LICENSED)
    grounded = grounded_extension(claim_ids, corpus.defeat_edges, strength, licensed_ids)
    defeats = effective_defeats(corpus.defeat_edges, strength, licensed_ids)
    # ... rest UNCHANGED ...
```

- [ ] **Step 4: Run to verify they pass**

Run: `cd /Users/zbb2/Desktop/polymer-claims/protocol && uv run pytest tests/test_represent.py -v`
Expected: existing represent tests + 2 new PASS. Then FULL protocol suite `uv run pytest -q` — green (no existing corpus has provisional edges; non-provisional behavior unchanged). `uv run ruff check src tests`.

- [ ] **Step 5: Commit**

```bash
cd /Users/zbb2/Desktop/polymer-claims
git add protocol/src/polymer_protocol/represent.py protocol/tests/test_represent.py
git commit -m "feat(protocol): represent supplies licensed_ids -> provisional edges activate on license

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: protocol — operators emit provisional rebut edges

**Files:**
- Modify: `protocol/src/polymer_protocol/proposers.py`
- Test: `protocol/tests/test_proposers.py`, `protocol/tests/test_cycle.py`

Both operators switch from #4a's isolated node to a node + a provisional rebut edge.

- [ ] **Step 1: Update + add tests**

In `protocol/tests/test_proposers.py`, REPLACE the existing `test_frontier_attack_emits_seed_without_edge` with this (frontier_attack now emits a provisional edge):
```python
def test_frontier_attack_emits_provisional_rebut_edge():
    from polymer_grammar import DefeatEdgeKind
    a, b = make_claim("a"), make_claim("b")
    edges = (DefeatEdge(source="b", target="a", kind=DefeatEdgeKind.REBUT),)
    props = frontier_attack(_corpus_e([a, b], edges), frontier=("a",))
    assert len(props) == 1
    p = props[0]
    assert p.claim.status == Status.CONJECTURED and p.claim.conclusion is None
    assert len(p.edges) == 1
    e = p.edges[0]
    assert e.source == p.claim.id and e.target == "b"
    assert e.kind == DefeatEdgeKind.REBUT and e.provisional is True
```
And APPEND a rival-edge test (the rival keeps its empty neighborhood AND gains a provisional edge):
```python
def test_rival_emits_provisional_rebut_edge_to_source():
    from polymer_grammar import DefeatEdgeKind
    c = make_claim("c", conclusion=_concl(Direction.POSITIVE))
    props = rival_generation(_corpus([c]), ())
    for p in props:
        assert p.claim.conclusion.neighborhood == ()       # still no incompatible_with
        assert len(p.edges) == 1
        e = p.edges[0]
        assert e.source == p.claim.id and e.target == "c"
        assert e.kind == DefeatEdgeKind.REBUT and e.provisional is True
```
(The existing `test_frontier_attack_is_belief_neutral` still passes unchanged — the provisional edge is inert under the default `licensed_ids=frozenset()` that `grounded_extension` uses there. Leave it. The existing `test_rival_has_empty_neighborhood`/skip/deterministic tests also still pass.)

In `protocol/tests/test_cycle.py`, UPDATE `test_frontier_attack_plants_a_seed`: it asserted `len(result.corpus.defeat_edges) == 1`; frontier_attack now adds one provisional edge, so change to `== 2` and assert the new edge is provisional + inert:
```python
    # a provisional rebut edge into b was added (inert while the seed is CONJECTURED)
    assert len(result.corpus.defeat_edges) == 2
    new_edge = next(e for e in result.corpus.defeat_edges if e.source.startswith("gen-fa-"))
    assert new_edge.target == "b" and new_edge.provisional is True
```

- [ ] **Step 2: Run to verify they fail**

Run: `cd /Users/zbb2/Desktop/polymer-claims/protocol && uv run pytest tests/test_proposers.py::test_frontier_attack_emits_provisional_rebut_edge -v`
Expected: FAIL — frontier_attack currently emits no edge (`p.edges == ()`).

- [ ] **Step 3: Implement** — modify `proposers.py`:

Add `DefeatEdge, DefeatEdgeKind` to the grammar import:
```python
from polymer_grammar import (
    CategoricalLeaf,
    Claim,
    DefeatEdge,
    DefeatEdgeKind,
    Direction,
    GenerationMode,
    Provenance,
    Status,
)
```

In `rival_generation`, give the rival id a local name and emit a provisional edge (replace the `rival = Claim(... id=_gen_id(...) ...)` + append):
```python
            rid = _gen_id("rival", c.id, d.value)
            rival = Claim(
                id=rid,
                title=f"rival({d.value}) of {c.id}",
                pattern=c.pattern,
                leaves=c.leaves,
                status=Status.CONJECTURED,
                subject=c.subject,
                conclusion=rival_concl,
                provenance=_generated_by(corpus, RIVAL_OP),
            )
            edge = DefeatEdge(source=rid, target=c.id, kind=DefeatEdgeKind.REBUT, provisional=True)
            proposals.append(Proposal(operator_id=RIVAL_OP, claim=rival, edges=(edge,)))
```

In `frontier_attack`, give the seed id a local name and emit a provisional edge (replace the `d_claim = Claim(... id=_gen_id("fa", f, b) ...)` + append):
```python
            did = _gen_id("fa", f, b)
            d_claim = Claim(
                id=did,
                title=f"challenge to {b}",
                pattern=by_id[b].pattern,
                leaves=(CategoricalLeaf(ontology_term=f"frontier-attack-{b}"),),
                status=Status.CONJECTURED,
                provenance=_generated_by(corpus, FRONTIER_OP),
            )
            edge = DefeatEdge(source=did, target=b, kind=DefeatEdgeKind.REBUT, provisional=True)
            proposals.append(Proposal(operator_id=FRONTIER_OP, claim=d_claim, edges=(edge,)))
```

Also update the module docstring (lines 3-6) to say both operators plant a **provisional rebut edge** (activate-on-license) rather than "no defeat edge".

- [ ] **Step 4: Run to verify they pass**

Run: `cd /Users/zbb2/Desktop/polymer-claims/protocol && uv run pytest tests/test_proposers.py tests/test_cycle.py -v`
Expected: updated + new proposer tests PASS; the updated `test_frontier_attack_plants_a_seed` PASS; `test_generation_converges` still PASS (content-addressed ids unchanged → dedup still converges; the provisional edges dedup too since `generate_stage` re-adds the same edge but `compile_to_IR` admits the claim only once and the edge rides with it — verify convergence still holds). Then FULL protocol suite `uv run pytest -q` — green. `uv run ruff check src tests`. If `test_generation_converges` or a belief-neutrality test regresses, STOP and report.

- [ ] **Step 5: Commit**

```bash
cd /Users/zbb2/Desktop/polymer-claims
git add protocol/src/polymer_protocol/proposers.py protocol/tests/test_proposers.py protocol/tests/test_cycle.py
git commit -m "feat(protocol): GENERATE operators emit provisional rebut edges (activate on license)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 5: protocol — end-to-end activation test

**Files:**
- Test: `protocol/tests/test_cycle.py`

Pin the mechanism the operators rely on: a *planned* claim carrying a provisional edge activates it on license.

- [ ] **Step 1: Write the test** — append to `protocol/tests/test_cycle.py`:

```python
def test_provisional_edge_activates_when_source_licenses(empty_ledger, ctx, adapters):
    from polymer_grammar import DefeatEdge, DefeatEdgeKind
    from polymer_protocol.represent import represent
    # b attacks a (normal). d (PENDING, with a satisfiable plan) provisionally attacks b.
    a = make_claim("a")  # CONJECTURED
    b = make_claim("b")  # CONJECTURED
    d = make_claim("d", status=Status.PENDING, plan=make_plan(0.01, 0.05))
    edges = (
        DefeatEdge(source="b", target="a", kind=DefeatEdgeKind.REBUT),
        DefeatEdge(source="d", target="b", kind=DefeatEdgeKind.REBUT, provisional=True),
    )
    corp = Corpus(claims=(a, b, d), defeat_edges=edges, fdr_ledger=empty_ledger)
    r1 = run_cycle(corp, adapters, ctx)
    # d is the only candidate (a,b are CONJECTURED/no-plan); it executes (0.01<0.05) and licenses
    assert r1.corpus.by_id()["d"].status == Status.LICENSED
    # now d is LICENSED -> the provisional d->b is active -> b OUT of the grounded extension -> a reinstated
    scaf = represent(r1.corpus)
    assert "a" in scaf.grounded_extension and "b" not in scaf.grounded_extension
    assert "a" not in scaf.frontier  # a is no longer an unresolved-attack target


def test_provisional_edge_inert_while_source_pending(empty_ledger, ctx, adapters):
    from polymer_grammar import DefeatEdge, DefeatEdgeKind
    from polymer_protocol.represent import represent
    a = make_claim("a")
    b = make_claim("b")
    d = make_claim("d", status=Status.PENDING, plan=make_plan(0.01, 0.05))
    edges = (
        DefeatEdge(source="b", target="a", kind=DefeatEdgeKind.REBUT),
        DefeatEdge(source="d", target="b", kind=DefeatEdgeKind.REBUT, provisional=True),
    )
    corp = Corpus(claims=(a, b, d), defeat_edges=edges, fdr_ledger=empty_ledger)
    # before d licenses: the provisional edge is inert -> b defeats a -> a on the frontier
    scaf = represent(corp)
    assert "a" not in scaf.grounded_extension and "a" in scaf.frontier
```

- [ ] **Step 2: Run to verify**

Run: `cd /Users/zbb2/Desktop/polymer-claims/protocol && uv run pytest tests/test_cycle.py::test_provisional_edge_activates_when_source_licenses -v`
Expected: PASS (the mechanism is already implemented by Tasks 1–4; this is the end-to-end pin). If it FAILS, STOP and report (a real integration gap).

- [ ] **Step 3: Full gate + commit**

```bash
cd /Users/zbb2/Desktop/polymer-claims/protocol
uv run pytest -q
uv run ruff check src tests
uv run pytest tests/test_isolation.py -q
```
Expected: all green; isolation 3 passed. Then:
```bash
cd /Users/zbb2/Desktop/polymer-claims
git add protocol/tests/test_cycle.py
git commit -m "test(protocol): end-to-end provisional-edge activation on source license

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 6: README + CONTINUE docs

**Files:**
- Modify: `README.md`, `docs/superpowers/CONTINUE.md`

- [ ] **Step 1: Get the test counts**

Run: `cd /Users/zbb2/Desktop/polymer-claims/grammar && uv run pytest -q 2>&1 | tail -1` (grammar count `<G>`) and `cd /Users/zbb2/Desktop/polymer-claims/protocol && uv run pytest -q 2>&1 | tail -1` (protocol count `<P>`).

- [ ] **Step 2: Update `README.md`**

Update the grammar + protocol table rows with the new counts, and after the GENERATE paragraph add:

> A `DefeatEdge` can be **provisional** — inert until its source claim is LICENSED, then effective
> (`effective_defeats`/`grounded_extension` take a `licensed_ids` set; `represent` supplies it). GENERATE's
> `frontier_attack` and `rival_generation` now plant a provisional rebut edge instead of an isolated node:
> belief-neutral while the seed/rival is a conjecture (the edge is inert), it wires a real defeat the moment
> the claim is validated — closing the #4a limitation. (The pure operators' no-plan seeds stay dormant until
> they gain a plan; executable-generation is deferred.)

- [ ] **Step 3: Update `docs/superpowers/CONTINUE.md`**

Mark #4b-slice-1 (provisional links) DONE on branch `feat/provisional-links-4b` (merge SHA `<merge-sha pending>`). Note it's the **first slice to touch both packages** (grammar `DefeatEdge.provisional` + protocol wiring). List the load-bearing decisions: (1) grammar-flag (not a protocol registry) — intrinsic activate-on-license, automatic deactivation, no stage/registry; (2) `licensed_ids` defaults empty so the change is fully back-compat; (3) operators use a **rebut edge** (not `incompatible_with`) so `_conflicts` never fires — belief-neutrality preserved while conjectured; (4) honest limitation: the pure operators' no-plan seeds stay dormant until they gain a plan (executable-generation deferred). Repoint the NEXT action at the remaining fronts: #4b executable-generation / embedding operators, #5 daemons, or the grammar `representation_revision` meta-tier. Keep the existing CONTINUE format.

- [ ] **Step 4: Commit**

```bash
cd /Users/zbb2/Desktop/polymer-claims
git add README.md docs/superpowers/CONTINUE.md
git commit -m "docs: record provisional-links #4b in README + CONTINUE primer

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Final review

After Task 6, dispatch the whole-package Opus review (per subagent-driven-development) — note it spans BOTH packages this time (run both grammar + protocol suites; confirm grammar↔protocol isolation still holds). Then `superpowers:finishing-a-development-branch` (merge no-ff to main, verify both suites on the merged result, delete the branch). Update memory (`project_polymer_claims_knowledge_protocol.md` + `MEMORY.md`) with the merge SHA + decisions.

## Progress Log

- (fill in per task: commit SHA + any decisions/deviations)
