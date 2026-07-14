"""Cellular-sheaf STRUCTURE extraction over the claims graph (pure, numpy-free).

This module turns a Corpus into a SheafStructure: scalar-ℝ stalks on Quantity-leaf claims,
equivalence edges (agreement) and defeat edges (antagonism, sign-flipped). The numpy spectrum
(energy/H⁰/H¹) lives umbrella-side in polymer_claims.sheaf_spectrum behind the [embed] extra.
"""
from __future__ import annotations

from collections import deque

from polymer_grammar import ATTACK_KINDS, RelationKind, Status, effective_defeats, is_relation

from .base import _Model
from .corpus import Corpus

_DEFAULT_FILTER = frozenset({Status.LICENSED, Status.PENDING})
_FRUSTRATION_ROUND = 6  # 6dp byte-stable output, matching umbrella's _ROUND


class SheafVertex(_Model):
    claim_id: str
    value: float
    dimension_sig: tuple[tuple[str, int], ...] | None = None
    unit: str | None = None


class SheafEdge(_Model):
    kind: str          # "equivalence" | "defeat"
    u: str             # equivalence: lower id; defeat: attacker (source)
    v: str             # equivalence: higher id; defeat: target
    weight: float
    sign: int          # +1 equivalence (agreement), -1 defeat (antagonism). d_e = x_u - sign*x_v


class DataQualityFlag(_Model):
    kind: str          # "dimension_mismatch" | "unit_mismatch"
    claim_ids: tuple[str, str]
    detail: str


class SheafStructure(_Model):
    vertices: tuple[SheafVertex, ...] = ()
    edges: tuple[SheafEdge, ...] = ()
    flags: tuple[DataQualityFlag, ...] = ()


class ClaimTension(_Model):
    claim_id: str
    tension: float


class Obstruction(_Model):
    claim_ids: tuple[str, ...]
    edges: tuple[tuple[str, str], ...]
    magnitude: float


class ConsistencyHeadline(_Model):
    inconsistency_energy: float
    spectral_gap: float | None = None


class ConsistencyReport(_Model):
    inconsistency_energy: float
    equivalence_energy: float
    defeat_energy: float
    spectral_gap: float
    h0_dim: int
    h1_obstructions: tuple[Obstruction, ...] = ()
    per_claim_tension: tuple[ClaimTension, ...] = ()
    flags: tuple[DataQualityFlag, ...] = ()


def _quantity_leaf(claim):
    # Take the FIRST QuantityLeaf encountered (deterministic, since leaves is an ordered tuple).
    # The grammar allows multiple quantity leaves per claim, but for the scalar stalk we
    # deliberately pick the first one. Multi-quantity stalks are a planned future enrichment.
    for lf in claim.leaves:
        if lf.kind == "quantity":
            return lf
    return None


def _commensurable(a: SheafVertex, b: SheafVertex) -> bool | None:
    """Return True if a and b can form an equivalence edge, False for unit mismatch, None for dimension mismatch.

    None  → either dimension_sig is None, or they differ (dimension_mismatch flag, edge skipped).
    False → same dimension, different unit (unit_mismatch flag, edge skipped).
    True  → same dimension AND same unit (edge built).
    """
    if a.dimension_sig is None or b.dimension_sig is None or a.dimension_sig != b.dimension_sig:
        return None
    if a.unit != b.unit:
        return False
    return True


def _check_commensurable(
    a: SheafVertex,
    b: SheafVertex,
    left_id: str,
    right_id: str,
    flags: list[DataQualityFlag],
) -> bool:
    """Call _commensurable, append the correct DataQualityFlag on mismatch, return True only when an edge should be built."""
    comm = _commensurable(a, b)
    if comm is None:
        flags.append(DataQualityFlag(
            kind="dimension_mismatch",
            claim_ids=(left_id, right_id),
            detail=f"{a.dimension_sig} vs {b.dimension_sig}",
        ))
        return False
    if comm is False:
        flags.append(DataQualityFlag(
            kind="unit_mismatch",
            claim_ids=(left_id, right_id),
            detail=f"{a.unit!r} vs {b.unit!r}",
        ))
        return False
    return True


def _attacker_evalue(latest: dict, claim_id: str) -> float:
    """Return the attacker's latest non-retracted e-value, or 1.0 as the neutral fallback."""
    t = latest.get(claim_id)
    if t is None or t.retracted or t.e_value is None:
        return 1.0
    return float(t.e_value)


def _restriction_map_pairs(corpus: Corpus) -> set[frozenset[str]]:
    """Unordered claim-id pairs bridged by a ``RESTRICTION_MAP`` relation claim.

    The re-parameterization "reinterpret" semantics: a restriction map declares two claims to be
    over DIFFERENT measurement spaces — non-comparable — so an equivalence/defeat edge between them
    is NOT a contradiction and must be dropped from the sheaf (otherwise the Duhem layer would fire
    spurious frustration between e.g. "REJECTED over gene-body" and "LICENSED over promoter").
    Empty — hence byte-identical to prior behavior — when the corpus has no such relation.
    """
    pairs: set[frozenset[str]] = set()
    for c in corpus.claims:
        if not is_relation(c):
            continue
        if c.leaves[0].relation_kind is not RelationKind.RESTRICTION_MAP:
            continue
        s = c.subject  # ClaimSetSubject — is_relation guarantees the relation shape
        for a in s.source_set:
            for b in s.target_set:
                if a != b:
                    pairs.add(frozenset((a, b)))
    return pairs


def extract_sheaf(
    corpus: Corpus,
    *,
    status_filter: frozenset[Status] = _DEFAULT_FILTER,
    effective_only: bool = True,
) -> SheafStructure:
    """Extract a SheafStructure from a Corpus.

    Only Quantity-leaf claims whose status is in ``status_filter`` become vertices.
    Equivalence edges (Task 2) and defeat edges (Task 3) are built here; the numpy
    spectrum (Task 4) lives umbrella-side.

    ``effective_only`` (default True) restricts defeat edges to those that survive the VAF
    licensing/dominance filter (byte-identical to prior behavior). ``False`` builds defeat
    edges from every authored ``corpus.defeat_edges``, ignoring attacker licensing/dominance
    — the STRUCTURAL sheaf, used to detect contradictions that persist even when a demotion
    has de-licensed (and so inertted) the effective attack.
    """
    vertices: list[SheafVertex] = []
    for c in corpus.claims:
        if c.status not in status_filter:
            continue
        lf = _quantity_leaf(c)
        if lf is None:
            continue
        dim_sig = lf.dimension.exponents if lf.dimension is not None else None
        vertices.append(
            SheafVertex(
                claim_id=c.id,
                value=float(lf.value),
                dimension_sig=dim_sig,
                unit=lf.unit,
            )
        )

    vmap = {v.claim_id: v for v in vertices}
    restriction_pairs = _restriction_map_pairs(corpus)  # non-comparable pairs -> drop their edges
    edges: list[SheafEdge] = []
    flags: list[DataQualityFlag] = []

    for eq in corpus.equivalences:
        if eq.status not in status_filter:
            continue
        if eq.left not in vmap or eq.right not in vmap:
            continue
        if frozenset((eq.left, eq.right)) in restriction_pairs:
            continue  # non-comparable via a restriction map — no agreement edge
        a, b = vmap[eq.left], vmap[eq.right]
        if not _check_commensurable(a, b, eq.left, eq.right, flags):
            continue
        u, v = sorted((eq.left, eq.right))
        edges.append(SheafEdge(kind="equivalence", u=u, v=v, weight=float(eq.severity), sign=1))

    if effective_only:
        defeat_pairs = effective_defeats(
            corpus.defeat_edges, corpus.strength_map(), licensed_ids=corpus.licensed_ids()
        )
    else:
        # structural: every authored ATTACK edge, regardless of licensing/dominance — but
        # support (evidence_for) edges are never antagonism, so keep the kind filter.
        defeat_pairs = {(e.source, e.target) for e in corpus.defeat_edges if e.kind in ATTACK_KINDS}
    latest = {t.claim_id: t for t in corpus.fdr_ledger.tests}   # last write wins = latest test per claim
    for src, tgt in sorted(defeat_pairs):
        if src not in vmap or tgt not in vmap:
            continue                                            # synthetic ':' source or non-quantity endpoint
        if frozenset((src, tgt)) in restriction_pairs:
            continue                                            # non-comparable via a restriction map — no attack edge
        a, b = vmap[src], vmap[tgt]
        if not _check_commensurable(a, b, src, tgt, flags):
            continue
        edges.append(SheafEdge(kind="defeat", u=src, v=tgt, weight=_attacker_evalue(latest, src), sign=-1))

    return SheafStructure(vertices=tuple(vertices), edges=tuple(edges), flags=tuple(flags))


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
    (tree path u→…→v plus that edge) — a contradiction with no local witness. Deterministic:
    sorted ids.
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
                        edges = tuple(
                            (cyc[i], cyc[(i + 1) % len(cyc)]) for i in range(len(cyc))
                        )
                        mag = round(
                            float(sum(e.weight for e in structure.edges if {e.u, e.v} <= key)),
                            _FRUSTRATION_ROUND,
                        )
                        obstructions.append(
                            Obstruction(claim_ids=tuple(cyc), edges=edges, magnitude=mag)
                        )
    return tuple(obstructions)


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
