# export_topology slice — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Steps use `- [ ]`.

**Goal:** A pure, deterministic `export_topology(corpus, *, layout) -> TopologyExport` in `polymer_protocol` — the data contract the separate 3D viewer consumes. No rendering.

**Architecture:** New module `protocol/src/polymer_protocol/topology.py`. Frozen models (TopologyNode/Edge/Cluster/Export). Nodes from `corpus.claims`; edges from `defeat_edges` (+ effective/provisional) ∪ `equivalences` ∪ entails; clusters by pattern/subject_kind; deterministic Fruchterman-Reingold layout (seeded from claim-id hashes — NO clock/random). Grammar untouched; Corpus stays 4 collections; pure/deterministic.

**Spec:** `docs/superpowers/specs/2026-06-05-topology-viewer-design.md`.

**Commands:** `cd /Users/zbb2/Desktop/polymer-claims/protocol && uv run pytest -q` / `uv run ruff check src tests`. ABSOLUTE paths (Bash cwd persists).

---

### Task 1: Frozen TopologyExport models + node/edge/cluster extraction (no layout yet)

**Files:** Create `protocol/src/polymer_protocol/topology.py`; Test `protocol/tests/test_topology.py`. Export the public names from `protocol/src/polymer_protocol/__init__.py`.

- [ ] **Step 1 — failing test:** nodes/edges/clusters extracted from a small corpus (positions all `(0,0,0)` for now).

```python
def test_nodes_carry_claim_attributes():
    # corpus with one LICENSED claim (pattern p1, subject genomic_region) + one CONJECTURED
    exp = export_topology(corpus, layout=Layout.NONE)   # NONE = zero positions, for testing extraction
    n = {x.id: x for x in exp.nodes}
    assert n["a"].status == "licensed"
    assert n["a"].pattern_id == "adjusted_effect"
    assert n["a"].subject_kind == "genomic_region"
    assert n["a"].strength is not None and len(n["a"].strength) == 6
    assert n["b"].is_representation_revision is False

def test_defeat_edge_effective_and_provisional_flags():
    # a provisional edge from an unlicensed source -> effective False, provisional True
    exp = export_topology(corpus, layout=Layout.NONE)
    e = next(x for x in exp.edges if x.kind == "rebut")
    assert e.provisional is True and e.effective is False
```

- [ ] **Step 2 — run, confirm fail.**
- [ ] **Step 3 — implement models + extraction.** Frozen `_Model` subclasses exactly per spec (`TopologyNode`, `TopologyEdge`, `TopologyCluster`, `TopologyExport`). A `Layout` enum `{NONE, FORCE_DIRECTED}` (NONE = all-zero positions, for deterministic extraction tests; FORCE_DIRECTED in Task 2). Extraction:
  - **Nodes:** for each claim — `id`, `status=claim.status.value`, `pattern_id=claim.pattern.id`, `subject_kind=claim.subject.kind if claim.subject else None`, `strength=tuple(getattr(s, ax) for ax in AXES) if s else None`, `is_representation_revision=is_representation_revision(claim)`, `position` from layout.
  - **Effective set:** reuse `represent(corpus)` (gives `grounded_extension`) and `effective_defeats(corpus.defeat_edges, strength_map, licensed_ids)` to mark each defeat edge `effective`. Mirror how `represent.py` builds `strength` map + `licensed_ids`.
  - **Edges:** defeat_edges → `TopologyEdge(source,target,kind=edge.kind.value, effective=<in effective set>, provisional=edge.provisional)`; equivalences → `kind="equivalence", effective=True, provisional=False` (use the equivalence's member pair/representative — inspect `EquivalenceClaim` shape); entails → from each claim's `conclusion.neighborhood` ENTAILS edges, mapping target `content_hash` → claim id (skip unresolved), `kind="entails", effective=True, provisional=False`.
  - **Clusters:** one per distinct `pattern_id` (label `f"pattern:{pid}"`, member_ids sorted) — pattern clustering is the v1 axis; subject clustering is a follow-up. Deterministic order (sort by label).
  - Sort nodes by id, edges by (source,target,kind), clusters by id — determinism.
- [ ] **Step 4 — run green.**
- [ ] **Step 5 — commit** (`feat(protocol): export_topology data contract — nodes/edges/clusters`).

### Task 2: Deterministic Fruchterman-Reingold 3D layout

**Files:** Modify `topology.py`; Test `test_topology.py`.

- [ ] **Step 1 — failing test:**

```python
def test_layout_is_deterministic_and_3d():
    e1 = export_topology(corpus, layout=Layout.FORCE_DIRECTED)
    e2 = export_topology(corpus, layout=Layout.FORCE_DIRECTED)
    assert e1 == e2                                   # byte-identical (no clock/random)
    assert all(len(n.position) == 3 for n in e1.nodes)
    assert e1.layout_id.startswith("fruchterman-reingold")
    # distinct claims get distinct seed positions (no all-collapsed-to-origin)
    assert len({n.position for n in e1.nodes}) > 1
```

- [ ] **Step 2 — run, confirm fail.**
- [ ] **Step 3 — implement** a self-contained Fruchterman-Reingold over the defeat ∪ entails ∪ equivalence graph:
  - **Deterministic seed positions:** for each node id, derive an initial `(x,y,z)` from a stable hash of the id (e.g. `hashlib.sha256(id.encode())` → split digest bytes into 3 floats in [-1,1]). NO `random`, NO `time`.
  - Fixed `ITERATIONS` (e.g. 50), fixed `k` (ideal edge length), standard repulsive (k²/d) + attractive (d²/k) forces over the undirected adjacency, cooling schedule fixed. Pure float math (`math` only). Record `layout_id=f"fruchterman-reingold:iters={ITERATIONS},seed=sha256"`.
  - Round positions to a fixed precision (e.g. 6 dp) so equality is robust and JSON is clean.
- [ ] **Step 4 — run green** + full protocol suite + ruff + isolation.
- [ ] **Step 5 — commit** (`feat(protocol): deterministic Fruchterman-Reingold layout for export_topology`).

### Task 3: JSON round-trip + __init__ exports

- [ ] **Step 1 — failing test:** `TopologyExport.model_validate_json(exp.model_dump_json()) == exp`; and the public names import from `polymer_protocol`.
- [ ] **Step 2-4 — confirm fail, ensure exports in `__init__.py` + `__all__`, run green.**
- [ ] **Step 5 — commit** (`feat(protocol): export TopologyExport public surface + JSON round-trip`).

**After:** finish branch via superpowers:finishing-a-development-branch (merge local no-ff, no push).

## Self-Review
- Spec coverage: TopologyNode/Edge/Cluster/Export shapes (Task 1) ✓; deterministic force-directed layout + layout_id (Task 2) ✓; JSON-serializable (Task 3) ✓. Scale-gating is a usefulness note, not a build gate — the contract is built now.
- No placeholders: extraction rules, layout algorithm, and seed derivation are all concrete.
- Purity: seed from id-hash (no random/clock); equality-testable; grammar untouched.
