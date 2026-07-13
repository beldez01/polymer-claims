# Cross-Arm Relations — Slice 1: proposer + meta-claim promotion + spectral projection (design)

**Status:** approved (brainstorm 2026-07-13). First slice of a three-slice program that gives the
merged claims universe genuine cross-arm connectivity — so the *existing* signed-Laplacian spectral
layout finally renders biological/computational argument structure instead of a disconnected dust of
islands. **Slice 2** = Tier-1 statistical adjudication (which null/background is right); **Slice 3** =
Tier-2 experiment resolution (SELECT the cheapest test that resolves a biological tension). Each is its
own spec → plan.

**Related:** backlog §1 (accumulating-universe cross-links), `measurement-foundation.md §5.3`
(cross-assay relationships as licensable meta-claims), `residualism.md` (tension as structured,
queryable, to-be-tested residue), and the documented `equivalence.py` promotion
("*promotable to a full meta-claim once 'subject = set of claims' exists*").

---

## 0. One-paragraph summary

The merged universe is a union of independently-decided arms: 1,386 claims, 54 within-arm edges, 96.7%
of nodes edgeless. Spectral layout is the signed-Laplacian eigenmap of the claim graph, so on this
graph it is meaningless (a lattice of singletons). The fix is *edges the engine can defend*, not layout
scaffolding. We model a **claim-to-claim relation** as a first-class, defeasible **meta-claim** whose
relata are **sets of claims**, carrying a **tier** (computational vs biological), a **kind** (reusing
the existing `DefeatEdgeKind` taxonomy), and a **graded signed severity** (coherence `+` ↔ tension `−`).
An umbrella **proposer** reasons over candidate claim pairings and emits these relations as
**CONJECTURED** (defeasible, provisional, never tombstoning). `build_graph` **projects** each relation
into signed graph edges; the existing spectral layout then pulls coherent claims together and pushes
claims in tension apart. Relations *earn* their standing later (Slices 2–3); in Slice 1 they are honest
conjectures that connect the universe.

## 1. The problem

- **Spectral == the defeat/equivalence graph.** `embedding.py:build_graph` sources edges from the
  resolved topology export (`entails ∪ equivalence ∪ defeat`), weights equivalence/entails **positive**
  and defeat **negative**, and `spectral_layout` embeds **per connected component**, placing components
  on a deterministic lattice. With 96.7% singletons the eigenmap has almost no graph to reflect — hence
  the merged bundle ships force-directed instead.
- **Arms don't link.** `merge_universes` concatenates each arm's *within-arm* edges; nothing proposes
  *cross-arm* relations. Connectivity is zero by construction.
- **The trap.** We must not fabricate edges to make the picture connected. An edge has to be a genuine
  relationship the engine can later test and be wrong about.

## 2. The two-tier model (what a cross-arm relation *is*)

Relations come in two tiers, distinguished by *what "testing" means* to resolve them:

- **Tier-1 — computational.** Two claims (sets) engage the **same target** via **different statistical
  setups** — different null ranges, background scopes, negative controls, parameterizations. Concordant
  angles corroborate; discordant angles are **adjudicable** (one setup is the right lens). Resolved by
  statistical adjudication (Slice 2; the re-parameterization / background-null machinery).
- **Tier-2 — biological.** Claims related "in the greater network sense" — the computations don't
  directly engage, but the biology does (e.g. *TP53 dominant-negative activity* coheres with
  *TP53 → apoptosis resistance*; an epigenetic differentiation-bias claim is in *tension* with the same
  change raising apoptosis susceptibility). Resolved by a **new experiment** (Slice 3; SELECT).

Both are the same object viewed through different resolution engines: a typed, signed, graded,
defeasible relation that starts as a conjecture and earns standing through the appropriate test.

## 3. What already exists (reuse, do not reinvent)

| Concept | Already in the codebase |
|---|---|
| Signed graph for spectral | `embedding.py:build_graph` reads `entails ∪ equivalence ∪ defeat`; equivalence/entails `+`, defeat `−`. |
| Syntax(computational)/semantics(biological) split | `DefeatEdgeKind`: `undermine`/`rebut` are null-bearing (tombstone); `undercut`/`reclassify`/`reinterpret` = "meaning moved, statistics unchanged" (never tombstone); `evidence_for` = support. |
| Graded magnitude | `EquivalenceClaim.severity ∈ [0,1]`; defeat graded via claims' `StrengthVector` Pareto order. |
| Relation as a defeasible, status-bearing claim | `EquivalenceClaim` (`status`, `pending_reason`, `severity`). |
| Provisional / earns-through-testing | `DefeatEdge.provisional` — "inert until its source claim is LICENSED". |
| Set-relata → meta-claim | Documented anticipated promotion (`equivalence.py`, `measurement-foundation.md §5.3`). |
| The proposer | **Absent** — the real new work of Slice 1. |

## 4. The relation meta-claim (grammar promotion)

A relation is a first-class **meta-claim** in `Corpus.claims` (**Corpus stays exactly 4 collections**),
executing the documented `subject = set of claims` promotion. Fields:

- **`relata`** — an **ordered** pair of claim-id sets `(source_set, target_set)`, `frozenset[str]` each.
  Order is **canonicalized and ignored for symmetric kinds** (coherence/tension/equivalence) but is
  **`source → target` for the directional attack kinds** (`undermine`/`undercut`/`rebut`/`reclassify`/
  `reinterpret`), matching today's `DefeatEdge.source`/`target`. Singleton sets reproduce today's pairwise
  `EquivalenceClaim` / `DefeatEdge` exactly.
- **`tier`** — `COMPUTATIONAL | BIOLOGICAL` (§5).
- **`kind`** — the existing `DefeatEdgeKind` taxonomy (`evidence_for`, `undermine`, `undercut`, `rebut`,
  `reclassify`, `reinterpret`), refining *how* the relation acts within its tier.
- **`sign` / `severity`** — a graded **signed** scalar in **[−1, +1]**: `+` coherence/support, `−`
  tension/conflict. Binary is the endpoint case (`±1`). `EquivalenceClaim.severity`/kind fold in as the
  singleton special case.
- **`status`** — starts `CONJECTURED`; later earns `LICENSED`, *resolves into* a genuine Tier-1
  defeat/equivalence, or is defeated and dissolved (Slices 2–3).
- **`pending_reason`**, **provenance** (proposer id, rationale text, the candidate signal that paired
  the relata).

**Additive per the IR-monotonic-expansion doctrine.** Validators mirror the existing ones (**disjoint**
relata sets — no claim on both sides, no self-relation; `severity` bounds; `pending_reason` iff pending). **Proof
gate:** serialization is **byte-identical** to today when relata are singletons and no relation
meta-claims are present. Whether this lands as a new `RelationClaim` type or a generalization of
`EquivalenceClaim` is an implementation choice for the plan; the field set above is the contract.

## 5. The tier model

An **explicit `tier` field** pairs with the existing `kind`. The **null-bearing / tombstone behavior
keys off `(tier, kind)`** exactly as today: a `COMPUTATIONAL` + `rebut`/`undermine` relation *can*
tombstone once it earns; a `BIOLOGICAL` relation **never** tombstones — it only clusters (coherence) or
flags for reconciliation (tension). Tier is not a permanent label: a `BIOLOGICAL` tension **can resolve
into** a `COMPUTATIONAL` relation when Slice 2 picks the null that adjudicates it — represented as a
status transition on the same relation, preserving its provenance and audit trail.

## 6. Set-to-set projection into the signed graph

`build_graph` learns to project each relation meta-claim into signed edges:

- **Direct all-pairs signed edges** between the two relata sets, weight
  `w = severity × status_factor / normalizer`, where `status_factor` down-weights CONJECTURED relations
  (so unearned conjectures nudge, not dominate) and `normalizer` divides by `|A|·|B|` so a large set
  can't overpower the graph. **Coherence → positive** (sets attract, cluster); **tension → negative**
  (sets repel, separate). All-pairs is chosen over a synthetic hub node precisely because a hub with two
  positive edges would wrongly pull a *tension* pair together.
- The **meta-claim node itself** (it is a claim, hence a node) gets weak positive edges to its relata so
  it localizes at the seam it describes.
- Determinism/byte-stability: projection is pure, ordered, and rounded like the rest of `embedding.py`;
  **byte-identical when no relation meta-claims exist.**

## 7. The proposer (umbrella)

Two stages, because ~1M pairs over 1,386 claims is infeasible to reason over directly.

1. **Candidate generation** — cheap, deterministic blocking into candidate pairings:
   - *Tier-1 candidates:* claims engaging the **same target** (normalized subject/entity + comparable
     measurement space) via **different statistical setups**.
   - *Tier-2 candidates:* claims sharing **biological entities/pathways/topics** (subject overlap,
     shared ontology terms, topic facets).
   - Requires a **normalized subject identity**, which the thin topology nodes lack — so candidate-gen
     reads the **source claims** (leaves, `ontology_term`, ids, topics) and extracts a pragmatic entity
     key. **Primary feasibility risk:** weak normalization → weak candidates (§12). v1 uses a
     lightweight extractor; deeper entity resolution ties into the backlog's measurement-space/entity-axis
     work.
2. **Agent reasoning** — an LLM adapter (mirroring `LLMGenerationAdapter`): per candidate pairing it
   emits a relation meta-claim (`tier`, `kind`, signed `severity`, **rationale**) or declines. All
   **CONJECTURED**.

**Liberality guardrail:** a proposal threshold + a required rationale; because every relation is
CONJECTURED/provisional, an over-eager proposal is a *testable mistake*, not a false fact. All proposals
and rationales are audit-logged.

## 8. Data flow

```
proposer (candidate-gen → agent reasoning)
  → relation meta-claims (CONJECTURED) into Corpus.claims
  → build_graph projects all-pairs signed edges (+ meta-claim node localization)
  → spectral_layout embeds the now-connected graph
  → topology export (relation nodes + projected edges tagged tier/sign/status)
  → viewer renders: dashed/weak while CONJECTURED, colored by tier, coherence vs tension by sign
```

The merged bundle switches to (or offers) spectral layout, since it is now meaningfully connected.

## 9. Integrity guardrails

- Relations are **CONJECTURED/defeasible**; `(tier, kind)`-typed so a biological coherence can never
  masquerade as an earned computational adjudication.
- **Nothing tombstones or charges the FDR ledger in Slice 1** — relations only earn in Slices 2–3.
- Proposer liberality is bounded and fully audited (every relation carries its rationale + candidate
  signal).
- **Purity preserved:** the meta-claim (grammar) and the projection (protocol) stay pure + numpy-free;
  all reasoning and I/O live in the umbrella.
- **Byte-identity proven** when relata are singletons / no relation meta-claims exist.

## 10. Testing (behavioral)

- **Grammar:** byte-identical serialization for singleton relata (the doctrine proof); set-relata
  round-trip; validators (distinct relata sets, severity bounds, pending-reason-iff-pending).
- **Protocol:** all-pairs projection yields the correct signed edges + weights; a relation genuinely
  joins two previously-disconnected components; coherence pulls / tension pushes on a tiny fixture
  (behavioral, not implementation-coupled).
- **Proposer:** on a known-biology fixture (two TP53 claims) candidate-gen pairs them and the agent
  emits a coherence relation + rationale; it declines on unrelated claims. Agent mocked for determinism;
  a live smoke sits behind a data/key tripwire.
- **Property:** whole-bundle byte-identity when no relations are present (no regression).

## 11. Scope / YAGNI — what Slice 1 does *not* do

- No **Tier-1 adjudication** (which null/background is right — Slice 2).
- No **Tier-2 experiment resolution** (SELECT the cheapest resolving test — Slice 3).
- No **license-earning / FDR-charging** — relations stay CONJECTURED (the earning lifecycle is designed
  here but its gate is Slices 2–3).
- No **viewer interactions** beyond rendering the new nodes/edges (colors + dashed conjectured).

## 12. Open questions / risks

1. **Subject normalization** is the load-bearing risk: candidate-gen is only as good as the entity key
   it extracts from source claims. If arms share little normalizable biology, connectivity stays thin
   even with a perfect agent. Mitigation: start with the arms known to share subjects (e.g. AML/RUNX1
   across synbio + fusion-expression); measure realized connectivity before scaling the proposer.
2. **Proposer calibration** — the liberality knob has no ground truth yet in Slice 1 (relations don't
   earn until Slice 2). Interim: cap proposals per candidate, require rationale, and eyeball the audit
   log; treat the CONJECTURED graph as a hypothesis set, not a result.
3. **Projection weight tuning** — `status_factor` and the `|A|·|B|` normalizer are layout hyper-params;
   pick defaults, expose them, and validate on the fixture rather than the full universe.

## 13. References

- `grammar/src/polymer_grammar/{defeat,equivalence,proposition}.py` — the reused relation schema.
- `src/polymer_claims/embedding.py` — `build_graph` (signed graph) + `spectral_layout` (per-component
  eigenmap); the projection extends `build_graph`.
- `docs/superpowers/foundations/measurement-foundation.md §5.3` — cross-assay relationships as
  licensable meta-claims.
- `docs/superpowers/foundations/residualism.md` — tension as structured, queryable, to-be-tested residue.
- `docs/superpowers/BACKLOG.md §1` — accumulating-universe cross-links (the home of this program).
