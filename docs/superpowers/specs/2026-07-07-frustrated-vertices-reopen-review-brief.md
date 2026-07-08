# Review Brief — "Frustrated-vertices" reopen for the duhem consistency fold

**Status:** Design proposal, pre-implementation. Written to be critiqued by an independent
reviewer (human or another model) who has **no other access to this project or conversation.**
§1–3 are self-contained context; §4 is the bug; §5 is the proposal; §6 is the two open design
decisions; §7 is the honest attack surface — **the reviewer should go after §7 first.** §8 is the
actual current source so you can check the claims against real code, not paraphrase.

---

## 0. For the reviewer — the load-bearing claims to check

If any of these is false, the proposal weakens or collapses. Attack them directly:

1. **The bug is real:** that "a claim is in a *reported* frustration obstruction" is genuinely
   *not* the same as "a claim lies on some frustrated cycle," because the reported obstructions are
   spanning-tree-dependent fundamental cycles (§4). Concretely: does a chorded frustrated cycle
   actually leave a genuinely-frustrated vertex out of every reported obstruction?
2. **The characterization is correct:** that *a vertex lies on a frustrated (sign-unbalanced)
   cycle **iff** it belongs to an unbalanced biconnected block* (§5.2). The "only if" is easy; the
   "if" is the load-bearing half — check the proof sketch.
3. **The fix is well-scoped:** that computing `frustrated_vertices` and using it for the fold's
   demote and reopen sets is the right and minimal correction, versus (a) a different graph
   invariant, or (b) leaving it as-is because the divergence is unreachable in practice.
4. **Fixing demote too is correct, not scope creep:** the original review flagged only *reopen*;
   §6.1 argues *demote* has the identical gap. Is that argument right, or is under-demotion
   actually harmless/desirable?
5. **No hidden cost or regression:** the new function runs per cycle over a signed graph; is the
   biconnected-components + per-block balance approach sound, terminating, and free of edge cases
   (self-loops, parallel edges, disconnected graph, isolated vertices) that the current code
   doesn't already rule out?

---

## 1. Context: what the system is (minimal)

**Polymer** is a trust substrate for scientific claims: a claim earns `LICENSED` standing only by
passing a recomputation-and-statistics gate, and its standing is continuously re-examined. Relevant
here: claims can be **equivalent** to one another (they must agree) or **defeat** one another
(antagonistic). The corpus is processed in a `run_cycle` loop; one late stage, `integrate`,
resolves the defeat graph under grounded argumentation semantics.

**The sheaf consistency gauge.** The corpus's quantitative claims are modeled as a *signed graph*
(a "cellular sheaf" structure): each claim with a scalar readout is a **vertex**; an **equivalence**
edge carries sign `+1` (agreement), a **defeat** edge carries sign `−1` (antagonism). A cycle in
this signed graph is **frustrated** (a.k.a. *unbalanced*) iff the product of its edge signs is `−1`
— equivalently, the cycle cannot be 2-colored `{+1,−1}` consistently with its edge constraints
(`label[v] = sign · label[u]` along each edge). A frustrated cycle is a genuine contradiction with
**no local witness**: every edge is locally satisfiable, but the cycle as a whole is not (e.g.
`A≡B`, `B≡C`, `C⊣A` — the two equivalences say A=B=C, the defeat says C contradicts A).

**The duhem consistency fold (just merged).** When the sheaf shows a frustrated cycle, the claims
on it are jointly implicated but **non-localizably** so — you cannot say *which* one is wrong. So
instead of rejecting them, the fold **demotes** each `LICENSED` implicated claim to
`PENDING duhem_underdetermined` (a reversible "unwarranted-for-now" suspension), and later
**reopens** it (to `PENDING reinstated`, to be re-tested) once the contradiction is resolved. The
fold is *ledger-neutral* (it does not touch the statistical false-discovery ledger — the suspension
is "warrant-only," not a claim that the effect is null) and *demote-only* (it never terminally
rejects).

Two sheaf variants matter:
- **Effective** frustration: built from defeat edges that are currently *in force* (the attacker is
  itself licensed and not dominated). Used to decide **demote** — you only suspend a claim for a
  contradiction that is actually live.
- **Structural** frustration: built from *all authored attack edges* regardless of current
  licensing/dominance. Used to decide **reopen** — a claim stays suspended until the contradiction
  is *structurally* gone (a defeat edge actually removed), not merely because suspending it made
  the attacker inert. (This effective/structural split was itself a fix for a "reopen flapping"
  bug and is not under review here; assume it correct.)

## 2. The frustration detector (current)

`frustration_obstructions(structure)` (full source in §8) does a signed **BFS**: label the BFS root
`+1`, propagate `label[v] = sign · label[u]` down tree edges; when a **back-edge** `(u,v)` is found
whose endpoints violate the running label (`label[v] ≠ sign · label[u]`), the **fundamental cycle**
through that back-edge (tree path `u→…→v` plus the edge) is a frustrated cycle, emitted as an
`Obstruction` carrying its `claim_ids`. Cycles are de-duplicated by their vertex-set.

## 3. How the fold uses obstructions (current)

`duhem_fold_from_obstructions(corpus, effective_obstructions, structural_obstructions)` (full source
in §8):
- **demote** iff the claim is `LICENSED` and its id is in `union(effective_obstructions.claim_ids)`.
- **reopen** iff the claim is `PENDING duhem_underdetermined` and its id is **not** in
  `union(structural_obstructions.claim_ids)`.

So both decisions key on **membership in the union of reported obstructions.**

---

## 4. The bug: reported-obstruction membership is spanning-tree-dependent

`frustration_obstructions` reports **fundamental cycles** relative to the BFS spanning tree — one
per violated back-edge. These are a *basis* for the cycle space, not *all* cycles. A vertex can lie
on a frustrated cycle and yet appear in **no reported fundamental cycle**, because a chord
re-decomposes the cycle space.

**Concrete witness — the theta graph.** Two vertices `a, b` joined by three internally-disjoint
paths `P1, P2, P3` (each a chain of equivalence/defeat edges). This is a single biconnected block
with three cycles: `P1∪P2`, `P2∪P3`, `P1∪P3`. Give them per-path balances (product of edge signs)
`balance(P1)=+`, `balance(P2)=+`, `balance(P3)=−`. Then:
- `P1∪P2` is **balanced** (`+·+`), `P1∪P3` is **frustrated** (`+·−`), `P2∪P3` is **frustrated**
  (`+·−`).
- A BFS spanning tree takes `P1` and all-but-one edge of `P2` and of `P3`; the two non-tree edges
  give the two **fundamental** cycles `P1∪P2` (balanced) and `P1∪P3` (frustrated). The detector
  emits only the frustrated fundamental cycle, `P1∪P3` — so the reported vertices are `P1 ∪ P3`.
- **The internal vertices of `P2` are on the frustrated cycle `P2∪P3`, but `P2∪P3` is not a
  fundamental cycle** (it equals `(P1∪P2) ⊕ (P1∪P3)` in the cycle space), so it is never emitted.
  Those vertices appear in **no reported obstruction**, yet they genuinely lie on a frustrated cycle.

So `union(reported obstruction claim_ids) ⊊ frustrated_vertices`: `P2`-internal claims are missed.
The theta graph is a realistic corpus shape (two claims linked by three independent chains of
equivalences/defeats), so the divergence is **reachable, not a hand-built pathology.**

*Why the GF(2) intuition does not save the current code:* balance is a GF(2)-linear functional on
the cycle space, so a *frustrated* cycle decomposes into an **odd** number of frustrated fundamental
cycles — at least one exists. But that frustrated fundamental cycle need not pass through the
particular vertex in question (here `P1∪P3` misses `P2`'s interior). "Some frustrated fundamental
cycle exists" ≠ "every frustrated vertex is on a frustrated *fundamental* cycle." That gap is the
bug.

**Consequences of keying the fold on reported-union:**
- **Reopen (the flagged bug):** a demoted claim `D` on a still-frustrated cycle can be *absent* from
  every reported obstruction after the cycle space re-decomposes, so the fold **reopens it while the
  contradiction persists** — a silent, incorrect un-suspension.
- **Demote (the symmetric gap, §6.1):** a `LICENSED` claim on an *effective* frustrated cycle can
  likewise be absent from every reported obstruction, so it **escapes demotion** and keeps false
  standing.

The current code documents the reopen weakness honestly ("no longer implicated by any *reported*
structural obstruction (blame may re-localize)") but does not fix it.

---

## 5. The proposal

### 5.1 A membership function, not a cycle enumeration

Add a pure function:

```
frustrated_vertices(structure: SheafStructure) -> frozenset[str]
```

returning **every vertex that lies on some frustrated cycle** — independent of any spanning tree.
The fold then uses it directly:
- demote iff `LICENSED` and `id in frustrated_vertices(effective_sheaf)`;
- reopen iff `PENDING duhem_underdetermined` and `id not in frustrated_vertices(structural_sheaf)`.

`frustration_obstructions` is **kept** (it still names the reported cycles for the audit trail's
`contradiction_ids` and for the viewer's display); only the fold's *membership test* changes.

### 5.2 The characterization (the load-bearing claim)

> A vertex lies on a frustrated cycle **iff** it belongs to an **unbalanced biconnected block**.

- Cycles live inside biconnected components (blocks); a cut vertex separates cycles, so any single
  cycle is within one block.
- A block is *balanced* iff it has no frustrated cycle (signed-graph balance = 2-colorable).
- **"only if":** if `v` is on a frustrated cycle, that cycle is in `v`'s block, so the block is
  unbalanced. Trivial.
- **"if" (the real content):** in an unbalanced block, **every** vertex is on a frustrated cycle.
  *Sketch:* a block is 2-vertex-connected, and it contains some frustrated cycle `C`. Take any
  vertex `v`. By 2-connectivity there are two vertex-disjoint paths from `v` to `C`, meeting `C` at
  distinct vertices `a, b`; these split `C` into two arcs `C₁, C₂`. Combining the two `v`-paths with
  `C₁` and with `C₂` gives two cycles through `v`. Their sign-product equals
  `sign(pathA)² · sign(pathB)² · sign(C₁) · sign(C₂) = sign(C) = −1` (frustrated). So at least one of
  the two cycles through `v` is frustrated. ∎

Therefore `frustrated_vertices = ⋃ { vertices(block) : block is sign-unbalanced }`.

### 5.3 Algorithm

1. **Biconnected components** of the (undirected) signed graph — standard Tarjan DFS with low-link,
   pure Python, ~40 lines, `O(V+E)`.
2. **Per block, balance check** — reuse the existing signed-BFS 2-coloring (the same
   `label[v] = sign·label[u]` propagation already in `frustration_obstructions`), restricted to the
   block's edges; a violated edge ⇒ the block is unbalanced.
3. Union the vertices of the unbalanced blocks.

Pure protocol, numpy-free, deterministic (sorted ids). Runs on the effective sheaf (for demote) and
the structural sheaf (for reopen), i.e. twice per cycle — same call pattern as today.

---

## 6. The two open decisions (I want the reviewer's read)

### 6.1 Fix **both** demote and reopen, or only reopen?

The original whole-branch review flagged only *reopen*. I argue **both**: demote keys on the same
reported-union, so a frustrated `LICENSED` claim can escape demotion by the same
spanning-tree accident (§4) — which means a claim in a live contradiction keeps `LICENSED` standing,
arguably worse than a premature reopen. For **simple** cycles (the common case) the reported-union
and `frustrated_vertices` coincide, so this is strictly-more-correct with no behavior change on the
existing tests. Counter-argument to consider: is under-demotion actually acceptable (the corpus is
"innocent until a *clearly* reported contradiction"), making the demote change unnecessary scope?

### 6.2 Keep the `..._from_obstructions` seam, or collapse to `duhem_fold(corpus)`?

Today the fold takes two obstruction *sequences* as arguments; with `frustrated_vertices` the fold
needs the corpus (to build both sheaves) rather than pre-computed obstructions. Option A: keep
`duhem_fold_from_obstructions(corpus, eff_obs, struct_obs)` and additionally pass/compute the vertex
sets (awkward). Option B: collapse to `duhem_fold(corpus)` that computes effective/structural
sheaves, `frustrated_vertices`, and the `contradiction_ids` internally — cleaner, but changes the
tested unit's signature. I lean **B** (the obstruction-sequence signature was an artifact of the
original implementation, and unit tests can inject a corpus). Is there a reason to preserve the
current seam?

---

## 7. Honest open questions — attack these first

1. **Does the bug actually exist? (I believe yes — verify the theta witness in §4.)** An earlier
   draft used a 4-cycle+chord example that a GF(2) balance argument breaks (the symmetric difference
   of two balanced cycles is balanced, so that example did *not* hide a frustrated vertex). The
   **theta graph in §4 is the corrected witness** and I believe it is sound: `P2`'s internal
   vertices lie on the frustrated cycle `P2∪P3`, which is not fundamental and never emitted, so they
   are absent from the reported-obstruction union while genuinely being frustrated. **Check this
   directly:** (a) confirm `P2∪P3` is frustrated and non-fundamental for the stated tree; (b)
   confirm the detector in §8.1 emits only frustrated *fundamental* cycles (one per label-violating
   back-edge, de-duplicated by vertex-set — it does **not** span the basis), so `P2`-internal is
   genuinely omitted. If either fails — if the emitted union always covers every unbalanced-block
   vertex — then the bug does not exist and the whole proposal is moot. This is still the single
   most important thing to settle.
2. **Even if reported-union ⊊ frustrated_vertices, is the difference reachable** in a real corpus,
   or only in hand-built pathologies? If unreachable, this is correctness-theater.
3. **Biconnected components on a multigraph:** the sheaf can have parallel edges (an equivalence and
   a defeat between the same pair) and the balance check treats the graph as undirected with signs —
   does Tarjan-BCC need special handling for parallel/anti-parallel edges, and does the per-block
   balance check see the right edge multiset?
4. **Is "on a frustrated cycle" even the semantics we want for reopen?** Alternative framings:
   reopen when the claim's *incident* structural attack edges are gone; reopen when the block's
   balance is restored. The biconnected-block criterion is the "lies on a frustrated cycle" reading;
   is that the right notion of "the contradiction that suspended me is resolved," or does blame
   legitimately re-localize (a claim on a *different* frustrated cycle than the one that originally
   suspended it — should it stay suspended)? The fold does not track *which* contradiction suspended
   a claim; is that provenance actually needed?
5. **Performance:** two BCC + balance passes per `run_cycle`, every cycle, even when nothing is
   suspended and nothing is frustrated. Acceptable, or does it need a guard (skip unless some claim
   is already `PENDING duhem_underdetermined` / some defeat edge exists)?

---

## 8. Appendix — actual current source (so you can check, not trust)

### 8.1 `frustration_obstructions` and `_cycle_ids` (`protocol/src/polymer_protocol/sheaf.py`)

```python
def _cycle_ids(parent: dict, u: str, v: str) -> list[str]:
    """Tree path v→root and u→root, spliced into the fundamental cycle through edge (u,v)."""
    def up(x: str) -> list[str]:
        path = []
        while x is not None:
            path.append(x)
            x = parent[x]
        return path
    pu, pv = up(u), up(v)
    sv = {p: i for i, p in enumerate(pv)}
    anc = next(p for p in pu if p in sv)            # lowest common ancestor
    left = pu[: pu.index(anc) + 1]                  # u → anc (inclusive)
    right = pv[: sv[anc]]                            # v → (just below anc)
    return left + right[::-1]


def frustration_obstructions(structure: SheafStructure) -> tuple[Obstruction, ...]:
    """Signed-BFS frustration detection (pure; no numpy).

    Each vertex gets a label in {+1,-1}; edge (u,v,sign) demands label[v] == sign*label[u].
    A back-edge that violates the running label witnesses a frustrated fundamental cycle
    (tree path u→…→v plus that edge). Deterministic: sorted ids.
    """
    adj: dict[str, list[tuple[str, int, float]]] = {v.claim_id: [] for v in structure.vertices}
    for e in structure.edges:
        adj[e.u].append((e.v, e.sign, e.weight))
        adj[e.v].append((e.u, e.sign, e.weight))    # undirected for balance check

    label: dict[str, int] = {}
    parent: dict[str, str | None] = {}
    obstructions: list[Obstruction] = []
    seen_cycles: set[frozenset[str]] = set()

    for root in sorted(adj):
        if root in label:
            continue
        label[root] = 1
        parent[root] = None
        queue: deque[str] = deque([root])
        while queue:
            u = queue.popleft()
            for v, sign, _w in sorted(adj[u]):
                want = sign * label[u]
                if v not in label:
                    label[v] = want
                    parent[v] = u
                    queue.append(v)
                elif label[v] != want:
                    cyc = _cycle_ids(parent, u, v)
                    key = frozenset(cyc)
                    if key not in seen_cycles:
                        seen_cycles.add(key)
                        edges = tuple((cyc[i], cyc[(i + 1) % len(cyc)]) for i in range(len(cyc)))
                        mag = round(float(sum(e.weight for e in structure.edges if {e.u, e.v} <= key)), 6)
                        obstructions.append(Obstruction(claim_ids=tuple(cyc), edges=edges, magnitude=mag))
    return tuple(obstructions)
```

Note for the reviewer: this is a **BFS**, and it emits **one** cycle per label-violating back-edge,
de-duplicated by vertex-set (`seen_cycles`). It is *not* enumerating a full cycle basis, and it is
BFS-tree-dependent. Whether its union-of-emitted-`claim_ids` can miss a vertex that lies on a
frustrated cycle is the crux of §7.1.

### 8.2 The fold (`protocol/src/polymer_protocol/duhem_fold.py`)

```python
def duhem_fold_from_obstructions(
    corpus: Corpus,
    effective_obstructions: Sequence[Obstruction],
    structural_obstructions: Sequence[Obstruction],
) -> tuple[Corpus, DuhemFoldAudit]:
    """Demote LICENSED claims implicated by an EFFECTIVE frustration; reopen PENDING-duhem claims
    no longer implicated by any *reported* structural obstruction (blame may re-localize ...)."""
    implicated_eff = blame_verdict_from_obstructions(effective_obstructions).possibly_blamed
    implicated_struct = blame_verdict_from_obstructions(structural_obstructions).possibly_blamed
    demoted, reopened, new_claims = [], [], []
    for c in corpus.claims:
        if c.status == Status.LICENSED and c.id in implicated_eff:
            new_claims.append(_demote_duhem(c)); demoted.append(c.id)
        elif (c.status == Status.PENDING
              and c.pending_reason == PendingReason.DUHEM_UNDERDETERMINED
              and c.id not in implicated_struct):
            new_claims.append(_reopen_duhem(c)); reopened.append(c.id)
        else:
            new_claims.append(c)
    contradiction_ids = tuple("h1:" + "|".join(sorted(o.claim_ids)) for o in effective_obstructions)
    audit = DuhemFoldAudit(demoted=tuple(sorted(demoted)), reopened=tuple(sorted(reopened)),
                           contradiction_ids=tuple(sorted(contradiction_ids)))
    return corpus.model_copy(update={"claims": tuple(new_claims)}), audit
```

(`blame_verdict_from_obstructions(obs).possibly_blamed` is simply the union of all `claim_ids`
across the obstructions in `obs`.)

### 8.3 The structural/effective sheaf switch (`extract_sheaf`, abbreviated)

```python
# vertices: Quantity-leaf claims whose status ∈ {LICENSED, PENDING}
# equivalence edges: sign +1 ; defeat edges: sign -1
if effective_only:
    defeat_pairs = effective_defeats(corpus.defeat_edges, corpus.strength_map(),
                                     licensed_ids=corpus.licensed_ids())
else:
    # structural: all authored ATTACK edges (support edges excluded), regardless of licensing/dominance
    defeat_pairs = {(e.source, e.target) for e in corpus.defeat_edges if e.kind in ATTACK_KINDS}
# ... build SheafEdge(sign=-1) for each pair whose endpoints are both vertices ...
```

---

## 9. One-paragraph summary (for the reviewer's verdict)

The duhem fold suspends claims that sit on a *frustrated* (sign-unbalanced) cycle of the claim graph
and reopens them when the contradiction resolves — but it decides membership by "is the claim in a
*reported* frustration obstruction," and the reported obstructions are BFS-spanning-tree-dependent
fundamental cycles, not all cycles. The proposal replaces that membership test with
`frustrated_vertices`, computed as the union of vertices in *unbalanced biconnected blocks* (a
vertex lies on a frustrated cycle iff it is in an unbalanced block), and applies it to both the
demote and reopen decisions. **The decisive question for the reviewer: can a vertex that lies on a
frustrated cycle ever be absent from the union of the emitted fundamental obstructions in §8.1? If
no, the bug and this proposal are moot; if yes, is the unbalanced-biconnected-block characterization
the right and minimal fix?**
