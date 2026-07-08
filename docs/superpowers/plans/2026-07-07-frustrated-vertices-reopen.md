# Frustrated-Vertices Reopen Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the duhem fold's spanning-tree-dependent "in a reported obstruction" membership test with `frustrated_vertices` (vertices on *any* frustrated cycle, via unbalanced biconnected blocks), applied to BOTH demote and reopen — fixing premature reopen and escaped demotion.

**Architecture:** Add a pure, multigraph-correct `frustrated_vertices(structure)` to `sheaf.py` (edge-identity Tarjan BCC + per-block signed-balance + self-loops). Rework the fold to key demote on `frustrated_vertices(effective)` and reopen on `¬frustrated_vertices(structural)`. `frustration_obstructions` is kept unchanged (audit/viewer). Ledger-neutral and demote-only throughout.

**Tech Stack:** Python 3, pydantic frozen models, pytest. No numpy in protocol.

## Global Constraints

- **Purity:** `polymer_protocol` stays pure — pydantic + stdlib only, no numpy, no `polymer_claims` import.
- **Ledger-neutral, demote-only:** the fold never calls `retract_tests`, never mutates `fdr_ledger`, never sets `Status.REJECTED`. (Unchanged from the merged fold.)
- **Block identity by EDGE INDEX, never vertex-set:** a vertex-set dedup mis-handles parallel edges and self-loops.
- **Endpoint validation FIRST:** skip edges whose endpoint ∉ `structure.vertices` (no raise); classify self-loops only after validation.
- **Conservative reopen policy (named):** reopen iff the claim is on NO structural frustrated cycle anywhere — not "the originating contradiction is gone." No per-claim provenance.
- **Determinism:** sorted iteration everywhere ids are ordered.
- Spec: `docs/superpowers/specs/2026-07-07-frustrated-vertices-reopen-design.md` (§2.2 has the exact BCC pseudocode; §7 the test matrix; §7.8 the exact reopen fixture).

## File structure

| File | Change |
|---|---|
| `protocol/src/polymer_protocol/sheaf.py` | add `frustrated_vertices` |
| `protocol/src/polymer_protocol/duhem_fold.py` | rename `duhem_fold_from_obstructions`→`duhem_fold` (new signature); `apply_duhem_consistency` computes vertex sets; `DuhemFoldAudit` docstring |
| `protocol/src/polymer_protocol/__init__.py` | export `frustrated_vertices`; rename fold export |
| `protocol/tests/test_frustrated_vertices.py` | the graph-theory unit matrix (create) |
| `protocol/tests/test_duhem_fold.py` | update to the new fold signature; theta demote + reopen-transition |

Reference facts (current code):
- `SheafVertex(claim_id: str, value: float, …)`, `SheafEdge(kind: str, u: str, v: str, weight: float, sign: int)`, `SheafStructure(vertices, edges, flags)`, `Obstruction(claim_ids, edges, magnitude)` — all in `polymer_protocol.sheaf`. `deque` is already imported there.
- `extract_sheaf(corpus, *, status_filter=…, effective_only: bool = True) -> SheafStructure`.
- Current fold: `duhem_fold_from_obstructions(corpus, effective_obstructions, structural_obstructions)`, `apply_duhem_consistency(corpus)`, `_demote_duhem`, `_reopen_duhem`, `DuhemFoldAudit(demoted, reopened, contradiction_ids)` in `duhem_fold.py`.
- `__init__.py`: fold names exported at lines ~113-115 and ~240-242; `frustration_obstructions` at ~105/236.
- Test helpers (`protocol/tests/conftest.py`): `_make_quantity_claim(cid, *, value, status, dim, unit)`; `from polymer_grammar import DefeatEdge, DefeatEdgeKind, EquivalenceClaim, FDRLedger, PendingReason, Status`; `EquivalenceClaim(id, left, right, severity, status)`; `DefeatEdge(source, target, kind=DefeatEdgeKind.REBUT|EVIDENCE_FOR)`; `Corpus(claims=…, fdr_ledger=FDRLedger(target_fdr=0.05))`.

---

### Task 1: `frustrated_vertices` — the BCC algorithm

**Files:**
- Modify: `protocol/src/polymer_protocol/sheaf.py`
- Modify: `protocol/src/polymer_protocol/__init__.py`
- Test: `protocol/tests/test_frustrated_vertices.py`

**Interfaces:**
- Produces: `frustrated_vertices(structure: SheafStructure) -> frozenset[str]` — every claim on some frustrated cycle. Exported from `polymer_protocol`.

- [ ] **Step 1: Write the failing unit matrix**

Create `protocol/tests/test_frustrated_vertices.py`:

```python
from polymer_protocol.sheaf import SheafEdge, SheafStructure, SheafVertex, frustration_obstructions
from polymer_protocol import frustrated_vertices


def _v(cid):
    return SheafVertex(claim_id=cid, value=0.0)


def _e(u, v, sign):
    return SheafEdge(kind="equivalence" if sign > 0 else "defeat", u=u, v=v, weight=1.0, sign=sign)


def _struct(vids, edges):
    return SheafStructure(vertices=tuple(_v(x) for x in vids), edges=tuple(edges))


def test_theta_includes_the_vertex_that_obstructions_miss():
    # a-b +, a-p2 +, p2-b +, a-p3 +, p3-b - : reviewer-verified witness
    s = _struct(("a", "b", "p2", "p3"), [
        _e("a", "b", 1), _e("a", "p2", 1), _e("p2", "b", 1), _e("a", "p3", 1), _e("p3", "b", -1),
    ])
    assert frustrated_vertices(s) == frozenset({"a", "b", "p2", "p3"})
    # the divergence that is the whole point: reported obstructions miss p2
    reported = frozenset().union(*(frozenset(o.claim_ids) for o in frustration_obstructions(s)))
    assert "p2" not in reported
    assert "p2" in frustrated_vertices(s)


def test_opposite_sign_parallel_edges_frustrate_both_endpoints():
    s = _struct(("u", "v"), [_e("u", "v", 1), _e("u", "v", -1)])
    assert frustrated_vertices(s) == frozenset({"u", "v"})


def test_same_sign_parallel_edges_are_balanced_both_signs():
    plus = _struct(("u", "v"), [_e("u", "v", 1), _e("u", "v", 1)])
    minus = _struct(("u", "v"), [_e("u", "v", -1), _e("u", "v", -1)])
    assert frustrated_vertices(plus) == frozenset()
    assert frustrated_vertices(minus) == frozenset()     # guards "any negative edge ⇒ unbalanced"


def test_self_loops():
    neg = _struct(("v",), [_e("v", "v", -1)])
    pos = _struct(("v",), [_e("v", "v", 1)])
    assert frustrated_vertices(neg) == frozenset({"v"})
    assert frustrated_vertices(pos) == frozenset()


def test_balanced_articulation_plus_unbalanced_block():
    # balanced triangle {a,b,c} sharing cut-vertex c with a frustrated triangle {c,d,e}
    s = _struct(("a", "b", "c", "d", "e"), [
        _e("a", "b", 1), _e("b", "c", 1), _e("a", "c", 1),          # balanced (all +)
        _e("c", "d", 1), _e("d", "e", 1), _e("c", "e", -1),         # frustrated
    ])
    assert frustrated_vertices(s) == frozenset({"c", "d", "e"})     # cut-vertex c included; a,b excluded


def test_disconnected_only_unbalanced_component_returned():
    s = _struct(("a", "b", "c", "x", "y", "z"), [
        _e("a", "b", 1), _e("b", "c", 1), _e("a", "c", 1),          # balanced component
        _e("x", "y", 1), _e("y", "z", 1), _e("x", "z", -1),         # frustrated component
    ])
    assert frustrated_vertices(s) == frozenset({"x", "y", "z"})


def test_simple_frustrated_cycle_equals_obstruction_union():
    s = _struct(("a", "b", "c"), [_e("a", "b", 1), _e("b", "c", 1), _e("a", "c", -1)])
    reported = frozenset().union(*(frozenset(o.claim_ids) for o in frustration_obstructions(s)))
    assert frustrated_vertices(s) == reported == frozenset({"a", "b", "c"})


def test_invalid_edge_endpoint_is_skipped_not_raised():
    s = _struct(("a",), [_e("a", "ghost", -1)])                     # ghost not a vertex
    assert frustrated_vertices(s) == frozenset()
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd protocol && python -m pytest tests/test_frustrated_vertices.py -v`
Expected: FAIL, `ImportError: cannot import name 'frustrated_vertices'`.

- [ ] **Step 3: Implement `frustrated_vertices`**

Append to `protocol/src/polymer_protocol/sheaf.py` (follows §2.2 pseudocode exactly):

```python
def frustrated_vertices(structure: SheafStructure) -> frozenset[str]:
    """Every claim on some frustrated (sign-unbalanced) cycle — independent of any spanning tree.
    A vertex is frustrated iff it is touched by an edge of an unbalanced biconnected block, or is a
    negative self-loop. Multigraph-correct: edge-identity Tarjan BCC. Pure; no numpy.

    Contrast with `frustration_obstructions`, which reports only violated *fundamental* cycles and
    can miss a genuinely-frustrated vertex (see the theta witness in the design spec)."""
    verts = {v.claim_id for v in structure.vertices}
    edges: list[tuple[str, str, int]] = []            # (u, v, sign) for non-loop, valid edges
    neg_self_loops: set[str] = set()
    adj: dict[str, list[int]] = {vid: [] for vid in verts}
    for e in structure.edges:
        if e.u not in verts or e.v not in verts:      # validate endpoints FIRST
            continue
        if e.u == e.v:                                # self-loop, only after validation
            if e.sign < 0:
                neg_self_loops.add(e.u)
            continue
        idx = len(edges)
        edges.append((e.u, e.v, e.sign))
        adj[e.u].append(idx)
        adj[e.v].append(idx)

    disc: dict[str, int] = {}
    low: dict[str, int] = {}
    edge_stack: list[int] = []
    blocks: list[list[int]] = []
    timer = 0

    def other(ei: int, u: str) -> str:
        a, b, _s = edges[ei]
        return b if a == u else a

    def dfs(root: str) -> None:
        nonlocal timer
        # explicit stack: (vertex, parent_edge_index, neighbor-iterator)
        disc[root] = low[root] = timer
        timer += 1
        stack: list[tuple[str, int, object]] = [(root, -1, iter(adj[root]))]
        while stack:
            u, pe, it = stack[-1]
            descended = False
            for ei in it:
                if ei == pe:                          # skip ONLY the exact incoming edge id
                    continue
                w = other(ei, u)
                if w not in disc:
                    edge_stack.append(ei)
                    disc[w] = low[w] = timer
                    timer += 1
                    stack.append((w, ei, iter(adj[w])))
                    descended = True
                    break
                elif disc[w] < disc[u]:               # back edge to a proper ancestor
                    edge_stack.append(ei)
                    low[u] = min(low[u], disc[w])
            if descended:
                continue
            stack.pop()
            if stack:
                p = stack[-1][0]
                low[p] = min(low[p], low[u])
                if low[u] >= disc[p]:                 # p is an articulation point / root
                    block: list[int] = []
                    while True:
                        e = edge_stack.pop()
                        block.append(e)
                        if e == pe:                   # pop through the triggering edge id
                            break
                    blocks.append(block)

    for s in sorted(adj):
        if s not in disc:
            dfs(s)

    result: set[str] = set(neg_self_loops)
    for block in blocks:
        block_adj: dict[str, list[tuple[str, int]]] = {}
        for ei in block:
            u, v, sign = edges[ei]
            block_adj.setdefault(u, []).append((v, sign))
            block_adj.setdefault(v, []).append((u, sign))
        label: dict[str, int] = {}
        unbalanced = False
        for r in sorted(block_adj):
            if r in label:
                continue
            label[r] = 1
            dq = deque([r])
            while dq:
                x = dq.popleft()
                for y, sign in block_adj[x]:
                    want = sign * label[x]
                    if y not in label:
                        label[y] = want
                        dq.append(y)
                    elif label[y] != want:
                        unbalanced = True
        if unbalanced:
            result.update(block_adj.keys())
    return frozenset(result)
```

(Note: this uses an **explicit** DFS stack — equivalent to the spec's recursive pseudocode but
avoids Python recursion limits on long chains. The `parent_edge`-is-an-edge-index rule and
`pop-through-the-triggering-edge` rule are preserved exactly.)

- [ ] **Step 4: Export it**

In `protocol/src/polymer_protocol/__init__.py`, add `frustrated_vertices` to the `from .sheaf import (...)` block (next to `frustration_obstructions`) and to `__all__`.

- [ ] **Step 5: Run to verify it passes**

Run: `cd protocol && ruff check . && python -m pytest tests/test_frustrated_vertices.py -v`
Expected: PASS (all 8 tests), ruff clean.

- [ ] **Step 6: Commit**

```bash
git add protocol/src/polymer_protocol/sheaf.py protocol/src/polymer_protocol/__init__.py protocol/tests/test_frustrated_vertices.py
git commit -m "feat(sheaf): frustrated_vertices via edge-identity biconnected blocks (multigraph-correct)"
```

**Scope guard:** pure, numpy-free; `frustration_obstructions` untouched. Block identity by edge index; endpoint validation before self-loop classification.

---

### Task 2: Rework the fold onto `frustrated_vertices`

**Files:**
- Modify: `protocol/src/polymer_protocol/duhem_fold.py`
- Modify: `protocol/src/polymer_protocol/__init__.py`
- Test: `protocol/tests/test_duhem_fold.py`

**Interfaces:**
- Produces: `duhem_fold(corpus, effective_frustrated: AbstractSet[str], structural_frustrated: AbstractSet[str], effective_obstructions: Sequence[Obstruction]) -> tuple[Corpus, DuhemFoldAudit]` (renamed from `duhem_fold_from_obstructions`).
- `apply_duhem_consistency(corpus)` computes both `frustrated_vertices` sets + effective obstructions and delegates.

- [ ] **Step 1: Update the existing fold tests to the new signature (write the failing tests)**

In `protocol/tests/test_duhem_fold.py`: change the import `from polymer_protocol.duhem_fold import apply_duhem_consistency, duhem_fold_from_obstructions` to `... import apply_duhem_consistency, duhem_fold`. Convert every `duhem_fold_from_obstructions(corpus, eff_obs, struct_obs)` call to `duhem_fold(corpus, eff_set, struct_set, eff_obs)` where `eff_set`/`struct_set` are the **frozensets of implicated ids** the test intends:
- demote tests (obstruction `_obstruction("A","B","C")`): `duhem_fold(corpus, frozenset({"A","B","C"}), frozenset({"A","B","C"}), [obs])`.
- ledger-untouched test: same shape as its demote.
- reopen test (was `[], []`): `duhem_fold(corpus, frozenset(), frozenset(), [])` — structural empty ⇒ reopen fires.
- structural-stays-put test: `duhem_fold(corpus, frozenset(), frozenset({"A", "B"}), [])` — effective empty (no demote), A in structural ⇒ NOT reopened.

Do not change any assertion values; only the call shape. Keep `test_apply_duhem_consistency_demotes_on_a_real_frustrated_corpus` (it calls `apply_duhem_consistency`, unaffected).

- [ ] **Step 2: Run to verify they fail**

Run: `cd protocol && python -m pytest tests/test_duhem_fold.py -v`
Expected: FAIL, `ImportError: cannot import name 'duhem_fold'`.

- [ ] **Step 3: Rework `duhem_fold.py`**

Replace `duhem_fold_from_obstructions` with:

```python
from collections.abc import AbstractSet, Sequence


def duhem_fold(
    corpus: Corpus,
    effective_frustrated: AbstractSet[str],
    structural_frustrated: AbstractSet[str],
    effective_obstructions: Sequence[Obstruction],
) -> tuple[Corpus, DuhemFoldAudit]:
    """Demote LICENSED claims that lie on an EFFECTIVE frustrated cycle; reopen PENDING-duhem claims
    that lie on NO STRUCTURAL frustrated cycle anywhere (the conservative, provenance-free policy).
    `effective_obstructions` is used only for the audit's display-only `contradiction_ids`."""
    demoted: list[str] = []
    reopened: list[str] = []
    new_claims: list[Claim] = []
    for c in corpus.claims:
        if c.status == Status.LICENSED and c.id in effective_frustrated:
            new_claims.append(_demote_duhem(c)); demoted.append(c.id)
        elif (
            c.status == Status.PENDING
            and c.pending_reason == PendingReason.DUHEM_UNDERDETERMINED
            and c.id not in structural_frustrated
        ):
            new_claims.append(_reopen_duhem(c)); reopened.append(c.id)
        else:
            new_claims.append(c)
    contradiction_ids = tuple("h1:" + "|".join(sorted(o.claim_ids)) for o in effective_obstructions)
    audit = DuhemFoldAudit(
        demoted=tuple(sorted(demoted)),
        reopened=tuple(sorted(reopened)),
        contradiction_ids=tuple(sorted(contradiction_ids)),
    )
    return corpus.model_copy(update={"claims": tuple(new_claims)}), audit


def apply_duhem_consistency(corpus: Corpus) -> tuple[Corpus, DuhemFoldAudit]:
    """Compute effective and structural frustrated-vertex sets from the corpus's sheaf, then apply
    the fold. Self-contained entry point for run_cycle."""
    eff_sheaf = extract_sheaf(corpus)
    struct_sheaf = extract_sheaf(corpus, effective_only=False)
    return duhem_fold(
        corpus,
        frustrated_vertices(eff_sheaf),
        frustrated_vertices(struct_sheaf),
        frustration_obstructions(eff_sheaf),
    )
```

Update the imports at the top of `duhem_fold.py`: add `frustrated_vertices` to the `from .sheaf import (...)` line (it already imports `Obstruction, extract_sheaf, frustration_obstructions`); add `from collections.abc import AbstractSet, Sequence` (Sequence may already be imported — dedupe). Remove the now-unused `blame_verdict_from_obstructions` import if present. Add to `DuhemFoldAudit`'s docstring: "`contradiction_ids` is best-effort display-only *named cycles* and may not enumerate every demoted/held claim; the authoritative sets are `demoted`/`reopened`."

- [ ] **Step 4: Update `__init__.py` export**

In `protocol/src/polymer_protocol/__init__.py`, rename `duhem_fold_from_obstructions` → `duhem_fold` in both the `from .duhem_fold import (...)` block and `__all__`. (No deprecated wrapper — internal machinery; `apply_duhem_consistency` is the stable entry point.)

- [ ] **Step 5: Run to verify they pass**

Run: `cd protocol && ruff check . && python -m pytest tests/test_duhem_fold.py -v`
Expected: PASS, ruff clean.

- [ ] **Step 6: Commit**

```bash
git add protocol/src/polymer_protocol/duhem_fold.py protocol/src/polymer_protocol/__init__.py protocol/tests/test_duhem_fold.py
git commit -m "refactor(duhem-fold): key demote/reopen on frustrated_vertices; rename duhem_fold"
```

**Scope guard:** ledger-neutral, demote-only unchanged. Rename is an intentional internal-API change (no external caller).

---

### Task 3: Theta demote + reopen-transition end-to-end

**Files:**
- Test: `protocol/tests/test_duhem_fold.py` (extend)

**Interfaces:** Consumes `apply_duhem_consistency`. Proves the fix end-to-end on real corpora (through `extract_sheaf`), not hand-built vertex sets.

- [ ] **Step 1: Add the theta-demote test (with the effective-sheaf edge-count guard)**

Read the existing frustrated-corpus construction in `test_duhem_fold.py` for the `make_quantity_claim`/`EquivalenceClaim`/`DefeatEdge` idiom. Build the theta corpus — `a,b,p2,p3` LICENSED Quantity-leaf claims (same dim, `unit=None`), equivalences `a≡b, a≡p2, p2≡b, a≡p3`, and defeat `p3⊣b` (REBUT). Assert the demote path:

```python
def test_theta_demotes_the_vertex_obstructions_would_miss():
    corpus = _theta_corpus()   # a,b,p2,p3 LICENSED; a≡b, a≡p2, p2≡b, a≡p3, p3⊣b(REBUT)
    from polymer_protocol.sheaf import extract_sheaf, frustration_obstructions
    eff = extract_sheaf(corpus)
    assert len(eff.edges) == 5, "the REBUT defeat must survive the effective filter (attacker licensed)"
    reported = frozenset().union(*(frozenset(o.claim_ids) for o in frustration_obstructions(eff)))
    assert "p2" not in reported                       # obstruction-union would miss p2
    out, audit = apply_duhem_consistency(corpus)
    assert "p2" in audit.demoted                       # frustrated_vertices catches it
    assert out.by_id()["p2"].pending_reason == PendingReason.DUHEM_UNDERDETERMINED
```

The `len(eff.edges) == 5` guard (spec §5) proves the defeat wasn't filtered out (else no frustration, vacuous test). If it isn't 5, the claims/defeat aren't licensed/commensurable as intended — fix the corpus construction, do not weaken the assert.

- [ ] **Step 2: Add the reopen-transition test (the pinned §7.8 fixture)**

```python
def test_reopen_does_not_fire_while_structurally_frustrated_but_fires_when_resolved():
    # STATE 1 — simple frustrated triangle {a,p2,p3}: a≡p2, a≡p3, p2⊣p3(REBUT) → p2 demotes
    state1 = _triangle_corpus()                        # a,p2,p3 LICENSED
    s1, a1 = apply_duhem_consistency(state1)
    assert "p2" in a1.demoted
    assert s1.by_id()["p2"].pending_reason == PendingReason.DUHEM_UNDERDETERMINED

    # STATE 2 — the theta witness, carrying p2 as PENDING-duhem; p2⊣p3 removed, b + 3 edges added
    state2 = _theta_corpus_with_pending_p2()           # a,b,p3 LICENSED; p2 PENDING duhem; a≡b,a≡p2,p2≡b,a≡p3,p3⊣b
    from polymer_protocol.sheaf import extract_sheaf, frustration_obstructions
    reported = frozenset().union(*(frozenset(o.claim_ids)
                                   for o in frustration_obstructions(extract_sheaf(state2, effective_only=False))))
    assert "p2" not in reported                        # reported structural obstructions miss p2 ...
    s2, a2 = apply_duhem_consistency(state2)
    assert "p2" not in a2.reopened                     # ... but frustrated_vertices keeps it suspended
    assert s2.by_id()["p2"].pending_reason == PendingReason.DUHEM_UNDERDETERMINED

    # COMPLEMENT — remove the p3⊣b defeat → p2 on no structural frustrated cycle → reopens
    resolved = state2.model_copy(update={"defeat_edges": ()})
    s3, a3 = apply_duhem_consistency(resolved)
    assert "p2" in a3.reopened
    assert s3.by_id()["p2"].pending_reason == PendingReason.REINSTATED
```

Build `_triangle_corpus`, `_theta_corpus_with_pending_p2`, and `_theta_corpus` as local helpers using the exact edge lists from spec §7.8. For `_theta_corpus_with_pending_p2`, `p2` starts `status=PENDING, pending_reason=DUHEM_UNDERDETERMINED` (mirror the existing PENDING-claim construction in the file); the others LICENSED. Verify each helper's structural sheaf is what the assertions assume (non-empty where required) before finalizing.

- [ ] **Step 3: Run + full protocol suite**

Run:
```bash
cd /Users/zbb2/Desktop/polymer-claims/protocol && ruff check . && python -m pytest tests/test_duhem_fold.py -v && python -m pytest -q
```
Expected: the new tests pass; full protocol suite green (the effective/structural split and ledger-neutral/demote-only behaviors are unchanged for simple cycles, so existing cycle/fold tests hold). If the theta demote or reopen-hold assertion fails, that is a real finding — report it, do not weaken the test.

- [ ] **Step 4: Commit**

```bash
git add protocol/tests/test_duhem_fold.py
git commit -m "test(duhem-fold): theta demote + reopen-transition end-to-end (frustrated_vertices)"
```

**Scope guard:** test-only. If making these pass needs production changes, that means Task 1/2 has a gap — report it, don't bury a fix in the test.

---

## Self-review

- **Spec coverage:** §2 `frustrated_vertices` (BCC, self-loops, parallel, invalid edges) → Task 1 + its 8-test matrix; §3/§4 fold rework (demote-effective/reopen-structural, AbstractSet, rename, audit docstring) → Task 2; §5 effective-sheaf edge-count guard + §7.7 theta demote + §7.8 exact reopen transition → Task 3. Named reopen policy (§3.1) is realized by "reopen iff not in structural frustrated set." Audit-docstring done-when (§7.11) is in Task 2 Step 3.
- **Placeholder scan:** none — `frustrated_vertices` and `duhem_fold` are given in full; Task 3 helpers are "build from the exact §7.8 edge lists using the file's existing idiom," a construction instruction with concrete assertions and a finding-guard.
- **Type consistency:** `frustrated_vertices -> frozenset[str]`; `duhem_fold(..., AbstractSet[str], AbstractSet[str], Sequence[Obstruction])`; `apply_duhem_consistency(corpus)` unchanged signature. `DuhemFoldAudit` fields unchanged.

## Execution note

Task 1 (the BCC algorithm) is the real risk and carries the full graph-theory matrix; the whole-branch review should scrutinize its multigraph mechanics (edge-identity, self-loops, parallel bundles) hardest. Tasks 2–3 are the wiring and the end-to-end witnesses. The reopen-transition test (Task 3 Step 2) is the regression guard the whole feature exists for — it must exercise the exact theta divergence (reported-union misses `p2`, `frustrated_vertices` keeps it), not a weaker proxy.
