# Frustrated-Vertices Reopen — design (post-critique)

**Date:** 2026-07-07
**Status:** Approved. Two independent critique passes folded in; the audit-provenance choice (§4.1),
the public-API compatibility choice (§4.2), and the reopen transition fixture (§7.8) are now
**pinned** — no open decisions remain for the builder. Ready for plan → build.
**Depends on:** the merged duhem consistency fold (`2026-07-07-duhem-consistency-fold-design.md`).
**Origin:** whole-branch review finding #3 (reopen keys on spanning-tree-dependent obstruction
membership) + an independent critique that reproduced the bug and tightened the design. This spec
folds that critique in; the review brief (`2026-07-07-frustrated-vertices-reopen-review-brief.md`)
is the self-contained problem statement.

---

## 1. The confirmed bug

The fold decides demote/reopen by **membership in the union of *reported* frustration obstructions**.
`frustration_obstructions` emits only the **violated fundamental cycles** of a BFS spanning tree
(one per label-violating back-edge, de-duped by vertex-set) — **not** a full cycle basis, and
tree-dependent. A vertex can lie on a frustrated cycle yet appear in no reported obstruction.

**Verified witness (independently reproduced against the real detector).** Four vertices, signed
edges (`+` equivalence, `−` defeat):

```
a—b  +     a—p2 +     p2—b +     a—p3 +     p3—b −
```

This is a theta graph: `a,b` joined by three internally-disjoint paths `a-b` (P1), `a-p2-b` (P2),
`a-p3-b` (P3), with `balance(P1)=+`, `balance(P2)=+`, `balance(P3)=−`. Cycles: `P1∪P2` balanced,
`P1∪P3` **frustrated**, `P2∪P3` **frustrated**. The detector emits exactly one obstruction —
`('b','a','p3')` — so **`p2` is missed**, even though `p2` lies on the frustrated cycle `P2∪P3`
(which is not fundamental and never emitted). This is the regression fixture.

Consequences on the current fold:
- **Reopen** (flagged): a demoted claim can drop out of the reported union while still structurally
  frustrated → **premature un-suspension**.
- **Demote** (symmetric): a LICENSED claim on an *effective* frustrated cycle can be missed →
  **escapes suspension, keeps unwarranted `LICENSED` standing** (warrant-only — this is *not* a
  claim that the effect is false; it is standing the corpus cannot currently cohere).

Correction note for the brief's own text: the reported cycles are **not a basis** — the full set of
fundamental cycles (all non-tree edges) is a basis; the detector reports only the *violated* subset.

---

## 2. The fix: `frustrated_vertices`, multigraph-aware

### 2.1 Characterization

> A vertex lies on a frustrated cycle **iff** it is touched by an edge of a **sign-unbalanced
> block**.

**A block is an edge-index set** (the unit of the biconnected decomposition), *not* a vertex set —
block identity is by **edge indices**, never by vertex-set (the old detector's `frozenset(vertices)`
dedup is wrong here: it would merge a self-loop or a parallel bundle into a neighboring cycle). A
block's vertices are *derived* from its edges. The decomposition:

- **Ordinary biconnected components** — normatively, **the edge sets emitted by the
  vertex-biconnected decomposition of the undirected multigraph** (the edge-identity Tarjan BCC of
  §2.2). *(Intuition, not the definition: within a block any two edges lie on a common cycle.)* A
  **bridge** is a singleton block; it holds no cycle and is always balanced.
- **Self-loops** are singleton edge-index blocks (one edge, one vertex).
- **Parallel edges** are handled purely by edge identity: if `u,v` sit inside a larger biconnected
  region, their parallel edges belong to *that* block and participate in its balance — they are
  **not** peeled into a separate bundle-only block. Only when the parallel pair is otherwise
  isolated (a bridge-like 2-vertex component) does it form its own block.

**Unbalanced** per block:
- 2-vertex-connected block, unbalanced ⇒ every vertex on it is on a frustrated cycle (proof sketch,
  review brief §5.2: two vertex-disjoint paths from any `v` to a frustrated `C` split `C`; the two
  resulting `v`-cycles multiply to `balance(C) = −1`, so one is frustrated).
- A self-loop block is unbalanced iff its sign is `−1` (a frustrated 1-cycle).
- A block whose only cycle is opposite-sign parallel edges (`+` and `−`) is unbalanced (frustrated
  2-cycle `u-v-u`); a **same-sign** parallel pair is *balanced* and contributes nothing unless the
  block holds another unbalanced cycle.

So `frustrated_vertices = ⋃ { vertices touched by an edge in an unbalanced block }`.

### 2.2 Algorithm (must be multigraph-correct)

New pure function `frustrated_vertices(structure: SheafStructure) -> frozenset[str]` in
`protocol/…/sheaf.py`:

1. **Edge-identity biconnected components.** Tarjan BCC over the undirected signed multigraph,
   keyed on **edge identity, not parent vertex** — a naive `skip the edge to parent` check drops one
   of two parallel parent edges and mis-merges/mis-splits blocks. Track edges by index; a block is
   the set of edge indices popped off the DFS edge-stack at an articulation point (never a vertex
   set). Self-loops are handled as their own singleton edge-index blocks (they never enter the DFS
   stack as ordinary tree/back edges); collect them separately.
   **Invalid edges — validate endpoints FIRST.** Like `frustration_obstructions`, the input is
   expected to reference only existing vertices — but because unit tests build `SheafStructure` by
   hand, `frustrated_vertices` must **defensively skip** any edge whose endpoint is not in
   `structure.vertices` (do not raise). Endpoint validation happens **before** self-loop
   classification: a negative self-loop on a *missing* vertex is skipped, never returned. (In
   production, `extract_sheaf` only emits edges between real vertices, so this is a test-robustness
   guard, not a behavior change.)
2. **Per-block balance.** For each block's edge set, run the existing signed-BFS 2-coloring
   (`label[v] = sign · label[u]`); a block edge whose endpoints violate the running label ⇒ the
   block is **unbalanced**. Parallel edges are naturally covered: the second edge to an
   already-labeled endpoint is the balance check. A self-loop block is unbalanced iff its sign is
   `−1`.
3. `frustrated_vertices` = union of the vertex-endpoints of all edges in unbalanced blocks, plus
   negative-self-loop vertices.

**Edge-identity Tarjan BCC (pseudocode — this is the highest-risk part; follow it exactly).** Build
`edges = [(u, v, sign), …]` (self-loops and invalid-endpoint edges excluded up front, per step 0
above), and `adj: vid -> [edge_index, …]`. Then:

```
disc, low = {}, {};  timer = 0;  edge_stack = [];  blocks = []   # blocks are lists of edge indices

def other(ei, u):                      # endpoint of edge ei that isn't u
    a, b, _sign = edges[ei];  return b if a == u else a

def dfs(u, parent_edge):               # parent_edge is an EDGE INDEX, not a vertex
    global timer
    disc[u] = low[u] = timer;  timer += 1
    for ei in adj[u]:
        if ei == parent_edge:          # skip ONLY the exact incoming edge id (parallel edges to
            continue                   #   the parent are NOT skipped — this is the whole point)
        w = other(ei, u)
        if w not in disc:              # tree edge
            edge_stack.append(ei)
            dfs(w, ei)
            low[u] = min(low[u], low[w])
            if low[w] >= disc[u]:       # u is an articulation point (or DFS root): pop one block
                block = []
                while True:
                    e = edge_stack.pop();  block.append(e)
                    if e == ei:  break    # pop through the triggering edge id
                blocks.append(block)
        elif disc[w] < disc[u]:         # back edge to a proper ancestor
            edge_stack.append(ei);  low[u] = min(low[u], disc[w])

for s in sorted(adj):                   # deterministic; each undiscovered vertex roots a DFS
    if s not in disc:  dfs(s, -1)
```

Then per `block` (a list of edge indices): its vertices are the endpoints of its edges; run the
signed-BFS 2-coloring over *only that block's edges*; if any edge violates the running label, the
block is unbalanced → add its vertices to the result. Finally add every negative-self-loop vertex.
(Recursion depth = graph depth; corpus sheaves are small, but convert to an explicit stack if depth
is ever a concern.)

Pure, numpy-free, deterministic (sorted iteration), `O(V+E)`.

`frustration_obstructions` is **kept unchanged** — it still names reported cycles for the audit and
the viewer's `h1_obstructions`. Only the fold's *membership test* moves to `frustrated_vertices`.

---

## 3. Where it's used — both demote and reopen

The fold replaces both obstruction-union membership tests with `frustrated_vertices`:
- **demote** iff `LICENSED` and `id ∈ frustrated_vertices(effective_sheaf)`.
- **reopen** iff `PENDING duhem_underdetermined` and `id ∉ frustrated_vertices(structural_sheaf)`.

For simple cycles the two notions coincide, so the fold's **status behavior on simple cycles is
unchanged** (the divergence appears only on theta-like multi-path structures, where
`frustrated_vertices` is the correct one). Note this is behavioral compatibility only — the fold's
function *signature* and its unit tests do change (§4).

### 3.1 Named reopen policy (stated, not implied)

The fold carries **no provenance** of *which* contradiction suspended a claim. Therefore the reopen
rule is, explicitly:

> **Reopen a duhem-suspended claim when it lies on NO structural frustrated cycle *anywhere* in the
> corpus — not "when the specific contradiction that originally suspended it is gone."**

This is deliberately **conservative**: a claim that migrates onto a *different* frustrated cycle
stays suspended. Adding per-claim suspension provenance (reopen only when *its* originating block
rebalances) is a possible future refinement, explicitly **out of scope** here. Naming this is part
of the design: reviewers and the viewer should read a reopen as "no live structural contradiction
touches this claim," nothing finer.

---

## 4. API seam (keep the fold pure and unit-testable)

Do **not** collapse to `duhem_fold(corpus)`. Keep a pure fold that takes the computed sets:

```
def duhem_fold(
    corpus: Corpus,
    effective_frustrated: AbstractSet[str],          # membership only (frustrated_vertices returns frozenset)
    structural_frustrated: AbstractSet[str],
    effective_obstructions: Sequence[Obstruction],   # for the audit's contradiction_ids only
) -> tuple[Corpus, DuhemFoldAudit]: ...
```

(`frustrated_vertices` returns `frozenset[str]`; the fold only tests membership, so it accepts the
wider `collections.abc.AbstractSet[str]`.)

- demote keys on `effective_frustrated`; reopen keys on `structural_frustrated`; `contradiction_ids`
  come from `effective_obstructions` (audit provenance).
- `apply_duhem_consistency(corpus)` computes both sheaves, both `frustrated_vertices` sets, and the
  effective obstructions, then calls `duhem_fold`.

This preserves trivial unit testing (inject vertex sets directly; no corpus/sheaf construction
needed for the fold's own tests). Replaces the current `duhem_fold_from_obstructions(corpus,
eff_obs, struct_obs)` — a rename + argument-shape change; update its callers/tests.

### 4.1 Audit compatibility — DECIDED

`contradiction_ids` (from `frustration_obstructions`) can now **omit** claims that drove demotion or
blocked reopen (a theta-missed `p2` demotes but is in no reported obstruction). **Decision:** keep
`contradiction_ids` as **best-effort *named cycles*** and do **not** add `frustrated_block_ids` in
this slice. The authoritative demotion/reopen sets are already `audit.demoted` / `audit.reopened`;
add a one-line docstring on `DuhemFoldAudit` stating `contradiction_ids` is display-only named
cycles and may not enumerate every demoted/held claim. Introduce block/membership provenance only
when a concrete viewer or API consumer needs it (none does today) — deferring avoids a premature,
serialized audit-schema change.

Also note (do not lean on it): `frustration_obstructions`'s `magnitude` sums all edges whose
endpoints fall inside the cycle's vertex-set — including chords/parallel edges — so reported
obstructions are display-only, never precise membership or precise cycle evidence.

### 4.2 Public-API compatibility — DECIDED

`duhem_fold_from_obstructions` is currently exported from `polymer_protocol` (`__all__`). It is
**internal machinery** — the stable public entry point is `apply_duhem_consistency`, and the only
callers of the `_from_obstructions` form are `apply_duhem_consistency` itself and the fold's unit
tests. **Decision:** rename it to `duhem_fold` with the new signature, update `__all__`
accordingly, and add **no deprecated wrapper** (there is no external consumer to preserve; a wrapper
would carry the old obstruction-union bug forward). Treat this as a deliberate internal-API change,
called out in the commit message. If a future external consumer of the old name is discovered, add
the wrapper then.

---

## 5. Reachability under `extract_sheaf` filters

The theta shape must be reachable through the real sheaf builder, not just abstractly. `extract_sheaf`
vertices are Quantity-leaf claims with status ∈ {LICENSED, PENDING}; equivalence edges (`+1`) come
from `EquivalenceClaim`s (commensurable endpoints), defeat edges (`−1`) from `ATTACK_KINDS`
DefeatEdges (effective ones filtered by licensing/dominance; structural ones not). Three
internally-disjoint `a↔b` paths are authored as: `a≡p2`, `p2≡b` (path P2), `a≡p3`, `p3⊣b` (path P3,
the negative one via a defeat), `a≡b` (path P1) — all among commensurable Quantity-leaf claims of the
same dimension.

**Effective-sheaf guard (critical for the *demote* case).** For the effective sheaf, the negative
path's defeat (`p3⊣b`) is only present if its **attacker is LICENSED and not dominated** — otherwise
`effective_defeats` filters it out and the effective sheaf is *balanced* (no frustration, no demote).
So the reachability test must **first assert the extracted effective sheaf has exactly the intended
five edges** (i.e. the defeat survived the effective filter) *before* asserting
`frustrated_vertices(extract_sheaf(corpus))` includes `p2`. (The structural-sheaf case has no such
guard — structural keeps all `ATTACK_KINDS` edges regardless of licensing.)

---

## 6. File structure

| File | Change |
|---|---|
| `protocol/src/polymer_protocol/sheaf.py` | add `frustrated_vertices` (edge-id BCC + per-block balance + self-loop/parallel handling) |
| `protocol/src/polymer_protocol/duhem_fold.py` | `duhem_fold(corpus, eff_frustrated, struct_frustrated, eff_obs)`; `apply_duhem_consistency` computes the sets |
| `protocol/src/polymer_protocol/__init__.py` | export `frustrated_vertices`; update fold export name |
| `protocol/tests/test_frustrated_vertices.py` | the graph-theory test matrix (§7) |
| `protocol/tests/test_duhem_fold.py` | update to the new fold signature; theta demote + reopen witnesses |
| `protocol/tests/test_cycle.py` | integration unchanged in spirit; confirm still green |

---

## 7. Done-when — the concrete test matrix

`frustrated_vertices` unit tests (`test_frustrated_vertices.py`):
1. **Theta omitted vertex is included.** The §1 witness (`a-b +, a-p2 +, p2-b +, a-p3 +, p3-b −`):
   `frustrated_vertices == {a, b, p2, p3}`, and specifically `p2 ∈ frustrated_vertices` while the
   union of `frustration_obstructions` claim_ids is `{a, b, p3}` (assert the divergence explicitly).
2. **Balanced articulation + one unbalanced block:** a balanced triangle sharing a cut vertex with a
   frustrated triangle ⇒ only the frustrated block's vertices are returned (the balanced block's
   non-shared vertices are excluded; the cut vertex is included).
3. **Opposite-sign parallel edges** between `u,v` (`+` and `−`) ⇒ `{u, v}` returned (frustrated
   2-cycle). This also asserts block identity is by **edge index**, not vertex-set (a vertex-set dedup
   would collapse the pair into an adjacent cycle and mis-handle it).
4. **Same-sign parallel edges** between `u,v` ⇒ **`{}` returned** — the 2-cycle is balanced. Assert
   **both** cases explicitly: two `+` edges *and* two `−` edges. The `−`/`−` case specifically guards
   against an "any negative edge means unbalanced" mistake; both guard "any parallel bundle is
   suspicious."
5. **Negative self-loop** at `v` ⇒ `{v}` returned; **positive self-loop** ⇒ excluded.
6. **Disconnected graph:** two components, one balanced one unbalanced ⇒ only the unbalanced
   component's frustrated-block vertices returned.
7. **Simple frustrated cycle** (no chords) ⇒ equals the obstruction-union (the common case is
   unchanged).
8. **Invalid edge** (endpoint absent from `vertices`) ⇒ skipped, no raise (test-robustness guard).

Fold + integration tests (`test_duhem_fold.py`, `test_cycle.py`):

**7. Theta demote.** A corpus whose effective sheaf is the theta witness (with the §5 effective-sheaf
edge-count guard), `p2` LICENSED ⇒ `p2` demotes to `PENDING duhem_underdetermined` (missed under the
old obstruction-union).

**8. Theta reopen does NOT fire — the end-to-end transition witness (pinned; critique #1).** The
transition is **two distinct corpus states**, NOT an additive chord (the theta is not the triangle
plus an edge — it needs `b` introduced and the `p2–p3` edge gone). Cleanest at the
`apply_duhem_consistency` level (the run_cycle integration test may reuse the same two corpora):

- **State 1 — a simple frustrated triangle so `p2` demotes.** Vertices `{a, p2, p3}`, edges (exact):
  ```
  a≡p2 (+)     a≡p3 (+)     p2⊣p3 (−)        # cycle a-p2-p3-a: +·−·+ = − → frustrated
  ```
  `frustration_obstructions` reports `{a, p2, p3}` — `p2` is in the union. `p2` LICENSED (and the
  `p2⊣p3` defeat effective, per §5). `apply_duhem_consistency(state1)` ⇒ `p2` → `PENDING
  duhem_underdetermined`.
- **State 2 — the theta witness, carrying `p2` as PENDING-duhem.** Vertices `{a, b, p2, p3}`; `p2`
  starts `PENDING duhem_underdetermined` (as left by state 1); edges (exact — the `p2⊣p3` edge is
  **removed**, `b` and three edges **added**):
  ```
  a≡b (+)     a≡p2 (+)     p2≡b (+)     a≡p3 (+)     p3⊣b (−)
  ```
  This is the reviewer's verified witness: `frustration_obstructions` reports only `{a, b, p3}`, yet
  `p2` lies on the frustrated cycle `a-p2-b-p3-a` (`+·+·−·+ = −`), so `p2 ∈
  frustrated_vertices(structural)`.
- **Assert `p2` stays suspended.** Under the OLD reported-union reopen, `p2 ∉ {a,b,p3}` ⇒ it would
  wrongly `REINSTATE`. Under `frustrated_vertices`, `p2` is still frustrated ⇒ it must **remain
  `PENDING duhem_underdetermined`**. This is the reopen bug's regression guard — assert BOTH that the
  reported-obstruction union excludes `p2` AND that `p2` stays suspended, so the test pins the exact
  divergence.
- **Complement (policy fires correctly).** From state 2, remove the `p3⊣b` defeat edge ⇒ no structural
  frustrated cycle touches `p2` ⇒ `apply_duhem_consistency` ⇒ `p2` reopens to `REINSTATED` (the
  conservative §3.1 policy firing correctly when the contradiction is genuinely gone).

**9. Structural/effective split intact:** the merged effective-vs-structural behavior (support edges
excluded, de-licensed attackers structural-only) still holds with `frustrated_vertices`.

**10. Ledger-neutral + demote-only preserved** end-to-end.

**11. Non-test checklist item (§4.1):** the `DuhemFoldAudit` docstring states that `contradiction_ids`
is best-effort *named cycles* (display-only) and may not enumerate every demoted/held claim — the
authoritative sets are `demoted`/`reopened`. (Listed here so the docstring change is not missed;
it has no test but is a required deliverable.)

---

## 8. Scope guards / non-goals

- Still **ledger-neutral**, still **demote-only**.
- `frustration_obstructions` unchanged (audit + viewer keep using it).
- **No per-claim suspension provenance** (the conservative reopen policy of §3.1 is intended, not a
  gap). Provenance-aware reopen is a future refinement.
- Not touching the double-`extract_sheaf`-per-cycle cost (separate deferred follow-up); though this
  spec adds two `frustrated_vertices` passes, keep them un-guarded for now unless the plan finds it
  trivial to fold in.

## See also
- `2026-07-07-frustrated-vertices-reopen-review-brief.md` — the self-contained problem statement + the theta derivation.
- `2026-07-07-duhem-consistency-fold-design.md` — the fold this refines.
- `protocol/src/polymer_protocol/sheaf.py` — `frustration_obstructions` (the detector kept for audit) and `extract_sheaf`'s effective/structural switch.
