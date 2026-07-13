# Cross-Arm Relations — Slice 1: proposer + meta-claim promotion + spectral projection (design)

**Status:** approved direction, **hardened 2026-07-13 after code review** (see §0.1). First slice of a
three-slice program that gives the merged claims universe genuine cross-arm connectivity — so a
**true** signed-Laplacian spectral layout renders biological/computational argument structure instead of
a disconnected dust of islands. **Slice 2** = Tier-1 statistical adjudication (which null/background is
right); **Slice 3** = Tier-2 experiment resolution (SELECT the cheapest test that resolves a biological
tension). Each is its own spec → plan.

**Related:** backlog §1 (accumulating-universe cross-links + this spec's own hardening row),
`measurement-foundation.md §5.3` (cross-assay relationships as licensable meta-claims), `residualism.md`
(tension as structured, queryable, to-be-tested residue), and the documented `equivalence.py` promotion
("*promotable to a full meta-claim once 'subject = set of claims' exists*").

---

## 0. One-paragraph summary

The merged universe is a union of independently-decided arms: 1,386 claims, 54 within-arm edges, 96.7%
of nodes edgeless. Spectral layout is the signed-Laplacian eigenmap of the claim graph, so on this graph
it is meaningless. The fix is *edges the engine can defend*, not layout scaffolding. We model a
**claim-to-claim relation** as a first-class, defeasible **meta-claim** — a `Claim` whose subject is a
**pair of claim sets** (a new `ClaimSetSubject`) — carrying a **tier** (computational vs biological), a
**relation kind** (its own enum, *not* the attack `DefeatEdgeKind`), and a **graded signed severity**
(coherence `+` ↔ tension `−`). An umbrella **proposer** reasons over candidate claim pairings and emits
these as **CONJECTURED**. `export_topology` **projects** each relation into signed `TopologyEdge`s (a
versioned contract change, so the viewer and the eigenmap both see them); the umbrella eigenmap gains
**true signed weights** so coherent claims attract and claims in tension repel. Relations *earn* their
standing later (Slices 2–3); in Slice 1 they are honest conjectures that connect the universe.

### 0.1 Corrections folded in from the 2026-07-13 review

1. **Signed projection is new, not assumed.** `embedding.py:KIND_WEIGHT` gives *every* kind a **positive**
   (attraction) weight; the only repulsion today is a narrow `polar` case (opposite-`direction` `rebut`,
   `RHO=0.3`). Slice 1 **introduces** genuine signed weights (negative for tension).
2. **Edges must be in the topology contract, not just the layout.** Projecting only inside `build_graph`
   would move nodes but hide tier/sign/status from `export_topology` and the viewer. Relations project
   into a **versioned `TopologyEdge`** so both consumers see them.
3. **Concrete IR shape.** A new **`ClaimSetSubject`** Subject variant + a **relation pattern/leaf**; the
   relation is a `Claim` in `Corpus.claims`. No new collection (Corpus stays 4).
4. **No "reproduces existing types exactly."** Relations are a *new additive object*; `EquivalenceClaim`
   and `DefeatEdge` are untouched. Byte-identity holds because the new Subject variant, pattern, and
   `TopologyEdge` fields are absent/defaulted in old corpora — *not* because a singleton relation equals a
   legacy edge. An explicit **lowering rule** is defined only if we later want a relation to also emit a
   legacy edge (opt-in, §4.1).
5. **No REINTERPRET overload.** A relation's kind is a **new `RelationKind`** enum (`coheres`, `tension`,
   `restriction_map`) that is **non-attack** (never de-licenses/tombstones). `DefeatEdgeKind.REINTERPRET`
   stays what it is — an attack/de-license edge — and the restriction-map the reparam evaluator needs is a
   `RelationKind`, resolving the backlog §1 name collision instead of repeating it.
6. **Purity layering fixed.** `embedding.py` is **umbrella / numpy** by design (its own docstring). The
   *pure* piece is the `TopologyEdge` contract in the protocol; the numpy signed-Laplacian in the umbrella
   consumes it.

### 0.2 Corrections folded in from the 2026-07-13 *second* review pass

7. **Byte-identity needs an explicit serializer.** `_Model` is `extra="forbid", frozen=True` with **no
   `exclude_none`**, and exports use `model_dump_json()`. A `model_serializer` on `TopologyEdge` (and the
   new grammar types) omits unset fields — the `capability.py` precedent (§1, §9, §10).
8. **Relata are sorted `tuple`s, not `frozenset`** — matching the subject schema's deterministic
   content-addressing (`CompositeSubject.parts`) (§1, §4).
9. **The relation leaf is concrete** — a named `RelationLeaf` in the `Leaf` union, since a `Claim` requires
   ≥1 leaf (`Field(min_length=1)`) (§4).
10. **Signed-edge aggregation is defined** — sum-then-clamp with status weighting, so a tension edge can't
    be erased by the current `max()` collapse (§6).
11. **`restriction_map` scope is consistent** — Slice 1 *defines + renders* it only; the sheaf-suppression
    behavior is Slice 2 (§5, §11).
12. **Protocol-lane guard** — relation claims are excluded from SELECT/EXECUTE/FDR by an explicit
    `is_relation` guard, not by convention (§9).

## 1. Architecture & placement (corrected layering)

- **Grammar (pure).** A new `ClaimSetSubject(_SubjectBase)` whose relata are **sorted `tuple[str, ...]`**
  (`source_set`, `target_set`) — tuples, not `frozenset`, matching the subject schema's deterministic
  content-addressing (`CompositeSubject.parts` is a tuple), with a validator enforcing sorted + disjoint.
  Plus a new **`RelationLeaf`** in the `Leaf` union carrying `tier`, `kind: RelationKind`, signed
  `severity ∈ [−1, +1]` — a `Claim` requires ≥1 `Leaf`, so the relation's nature is a concrete leaf, not
  vague metadata. A relation is therefore an ordinary
  `Claim(subject=ClaimSetSubject(...), leaves=(RelationLeaf(...),))` → lives in `Corpus.claims`,
  **Corpus stays 4 collections**. Additive; byte-identical when absent.
- **Protocol (pure).** `TopologyEdge` gains optional `tier`, `signed_weight`, and `relation_status`
  fields — a **versioned topology contract** (`v?→v?+1`). Byte-identity is **not** automatic: `_Model` is
  `extra="forbid", frozen=True` with **no `exclude_none`**, and exports use `model_dump_json()`. So we add
  an explicit **`model_serializer` on `TopologyEdge`** that omits the new fields when unset, mirroring the
  byte-identity serializer precedent (`capability.py`). `export_topology` learns to **project** each
  relation `Claim` into signed `TopologyEdge`s (§6). Pure data; viewer + eigenmap both read it.
- **Umbrella (impure, numpy).** `embedding.py` extends `KIND_WEIGHT`/`build_graph` to honor
  `signed_weight` (true negative weights for tension), generalizing today's `polar`/`RHO` hack. Plus the
  **proposer** (candidate-gen + agent reasoning). All reasoning and numpy stay here.

## 2. The two-tier model (what a cross-arm relation *is*)

- **Tier-1 — computational.** Two claim sets engage the **same target** via **different statistical
  setups** (nulls/backgrounds/controls/parameterizations). Concordant angles corroborate; discordant
  angles are **adjudicable**. Resolved by statistical adjudication (Slice 2).
- **Tier-2 — biological.** Claims related "in the greater network sense" — computations don't engage but
  the biology does (TP53 dominant-negative activity *coheres* with TP53 → apoptosis-resistance; an
  epigenetic differentiation-bias claim is in *tension* with the same change raising apoptosis
  susceptibility). Resolved by a **new experiment** (Slice 3).

Same object, two resolution engines: a typed, signed, graded, defeasible relation that starts CONJECTURED
and earns through the appropriate test.

## 3. What already exists (reuse) vs. what Slice 1 adds (build)

| Concept | State today | Slice 1 |
|---|---|---|
| Graph feeds spectral | `build_graph` reads `export_topology(...).edges`; the eigenmap embeds per component | reuse — but see signs below |
| Edge signs | **all positive** (`KIND_WEIGHT` 0.4–1.0); only opposite-`direction` `rebut` repels via `polar`/`RHO` | **add** true `signed_weight` (negative for tension) |
| Relation-as-defeasible-claim | `EquivalenceClaim` (symmetric, `severity ∈ [0,1]`, `status`) | **generalize** into a signed, set-relata meta-`Claim` |
| Graded magnitude | `EquivalenceClaim.severity` (nonnegative); defeat ungraded | **add** signed `severity ∈ [−1,1]` on the relation |
| Set-relata / meta-claim | documented, **not built** (`Subject` has no claim-set variant) | **build** `ClaimSetSubject` |
| Relation kinds | `DefeatEdgeKind` are all **attacks/support** | **add** non-attack `RelationKind` (`coheres`/`tension`/`restriction_map`) |
| Topology edge fields | `source,target,kind,effective,provisional` only | **add** `tier,signed_weight,relation_status` (versioned) |
| The proposer | **absent** | **build** |

## 4. The relation meta-claim (concrete additive schema)

A relation is a `Claim` with:
- **`subject: ClaimSetSubject`** — `source_set`, `target_set`, each a **sorted `tuple[str, ...]`** (tuples
  for deterministic content-addressing, matching `CompositeSubject.parts`; a validator enforces sorted +
  **disjoint** — no claim on both sides, no self-relation). Symmetric kinds (`coheres`/`tension`)
  canonicalize the two tuples into a stable order; `restriction_map` keeps `source→target`.
- **A new `RelationLeaf`** (added to the `Leaf` union — a `Claim` requires ≥1 leaf) carrying
  `tier: {COMPUTATIONAL, BIOLOGICAL}`, `kind: RelationKind`, and signed `severity ∈ [−1, +1]` (`+`
  coherence, `−` tension; binary is the `±1` endpoint).
- The `Claim`'s own `status` (starts `CONJECTURED`), `licensing`, provenance (proposer id, rationale, the
  candidate signal) — i.e. it earns its license through the *existing* `Claim` lifecycle.

**Additive per the IR-monotonic-expansion doctrine.** New `Subject` variant + new pattern + new
`TopologyEdge` fields are all optional/defaulted → **byte-identical** for any corpus without relations.
Classify the schema strain: `ClaimSetSubject` and `RelationKind` are `subject`/`relation`-class additions,
not general-core changes.

### 4.1 Lowering rule (optional, explicit)

Slice 1 does **not** claim a singleton relation equals a legacy `EquivalenceClaim`/`DefeatEdge`. If a
relation should *also* appear as a legacy edge (e.g. a Tier-1 `restriction_map` that a later slice wants
the sheaf to read), we define an explicit, opt-in lowering `relation → {EquivalenceClaim | DefeatEdge}` —
a deliberate projection, tested for the intended semantics, never an implicit identity.

## 5. The tier model + relation kinds

An **explicit `tier`** pairs with a **new `RelationKind`** (distinct from the attack `DefeatEdgeKind`):
- `coheres` — Tier-1 or Tier-2 support (positive severity); **non-attack**, never tombstones.
- `tension` — conflict needing reconciliation (negative severity); **non-attack**, flags for testing,
  never tombstones.
- `restriction_map` — the Tier-1 non-contradiction edge the reparam evaluator will need; **non-attack**.
  **In Slice 1 it is only *defined and rendered*** — the semantics it is *intended* to carry (telling the
  sheaf that "REJECTED over gene-body" and "LICENSED over promoter" are not a contradiction) is **wired in
  Slice 2**, not active here (§11).

Tombstone/null-bearing behavior is unchanged and stays on the *attack* `DefeatEdgeKind`s; **no
`RelationKind` tombstones or de-licenses.** Tier is not permanent: a `BIOLOGICAL` `tension` can **resolve
into** a `COMPUTATIONAL` relation (or a genuine attack) when Slice 2 adjudicates it — a status transition
on the same relation, preserving provenance.

## 6. Projection into signed `TopologyEdge`s (protocol) + signed eigenmap (umbrella)

- **Protocol (`export_topology`):** for each relation `Claim`, emit **all-pairs** `TopologyEdge`s between
  the two relata sets with `kind = relation.kind`, `signed_weight = severity × status_factor /
  (|A|·|B|)`, `tier`, `relation_status`. `status_factor` down-weights CONJECTURED relations; the
  `|A|·|B|` normalizer stops a big set dominating. The relation node itself gets weak positive edges to
  its relata so it localizes at the seam. All-pairs (not a hub node) so a **tension** pair genuinely
  repels rather than being pulled together by two positive hub edges. Pure, ordered, byte-stable.
- **Umbrella (`embedding.py`):** `build_graph` reads `signed_weight` and builds a **truly signed**
  adjacency (negative entries for tension), replacing the current all-attract assumption and the `max()`
  collapse. **Signed aggregation rule:** per unordered pair, **sum** the signed contributions then **clamp
  to [−1, 1]** — *not* `max()`, which would let any positive edge silently erase a negative tension. Because
  CONJECTURED relations are down-weighted (`status_factor < 1`), a speculative tension cannot fully cancel a
  strong legacy (equivalence/entails) attraction — legacy structure is protected. (Alternative: `separate
  channels` — a distinct relation-Laplacian combined at embed time — if sum-clamp proves too blunt; decided
  in the plan.) The existing `polar`/`RHO` `rebut` repulsion becomes a special case. `spectral_layout`
  otherwise unchanged.
- **Viewer:** reads the same `TopologyEdge`s → renders relations dashed/weak while CONJECTURED, colored by
  `tier`, coherence-vs-tension by sign.

## 7. The proposer (umbrella)

Two stages (≈1M pairs over 1,386 claims is infeasible to reason over directly):

1. **Candidate generation** — cheap, deterministic blocking. *Tier-1:* claims engaging the same target
   (normalized subject/entity + comparable measurement space) via different statistical setups. *Tier-2:*
   claims sharing biological entities/pathways/topics. Needs a **normalized subject identity** the thin
   topology nodes lack, so it reads the **source claims** (their `Subject` — `GeneOrProtein`,
   `OntologyTerm`, `PathwayRef`, `GenomicRegion` — plus topics). **Primary feasibility risk** (§12); v1
   uses a lightweight extractor over the existing `Subject` variants, deeper resolution ties to the
   backlog entity-axis work.
2. **Agent reasoning** — an LLM adapter (mirroring `LLMGenerationAdapter`): per candidate pairing emit a
   relation meta-claim (`tier`, `kind`, signed `severity`, **rationale**) or decline. All **CONJECTURED**.

**Liberality guardrail:** a proposal threshold + required rationale; because every relation is
CONJECTURED/provisional, an over-eager proposal is a *testable mistake*, not a false fact. All proposals +
rationales are audit-logged.

## 8. Data flow

```
proposer (candidate-gen → agent reasoning)
  → relation Claims (CONJECTURED, ClaimSetSubject) into Corpus.claims
  → export_topology projects all-pairs signed TopologyEdges (tier/signed_weight/relation_status)
  → build_graph (umbrella) builds a truly signed adjacency
  → spectral_layout embeds the now-connected graph
  → viewer renders relation nodes + edges: dashed/weak (CONJECTURED), colored by tier, signed by coherence/tension
```

## 9. Integrity guardrails

- Relations are **CONJECTURED/defeasible**; `RelationKind` is **non-attack** — a relation can never
  de-license or tombstone, and can never masquerade as an earned computational adjudication.
- **Protocol-lane guard.** Relation claims carry a `RelationLeaf`/`ClaimSetSubject`, have **no
  `evaluation_plan`**, and are filtered out of SELECT / EXECUTE / the FDR ledger by an explicit
  `is_relation` guard (subject/leaf-type check) — so **"nothing charges the FDR ledger in Slice 1"** is
  enforced mechanically, not by convention. Relations earn via a dedicated path in Slices 2–3.
- Proposer liberality bounded + fully audited.
- **Purity:** grammar (`ClaimSetSubject` + `RelationLeaf`) and protocol (`TopologyEdge` contract +
  projection) stay pure + numpy-free; the numpy signed eigenmap and all reasoning stay umbrella-side
  (`embedding.py`, proposer).
- **Byte-identity proven** for any corpus with no relation claims — via the explicit `model_serializer`
  (§1), not default drop-when-None.

## 10. Testing (behavioral)

- **Grammar:** `ClaimSetSubject` round-trip; relation pattern validators (disjoint sets, `severity`
  bounds, `pending_reason` iff pending); **byte-identical serialization** for a relation-free corpus.
- **Protocol:** `export_topology` projects the right all-pairs signed `TopologyEdge`s + weights; the
  `model_serializer` omits unset new fields so a relation-free export is **byte-identical** (assert against
  a golden); signed aggregation (sum-clamp) — a positive legacy edge + a CONJECTURED tension nets the
  expected sign and a strong tension is not erased; the `is_relation` lane guard keeps relation claims out
  of SELECT/EXECUTE/FDR; versioned contract bump asserted.
- **Umbrella eigenmap:** a `coheres` relation pulls two components together; a `tension` relation pushes
  them apart (behavioral, on a tiny fixture) — the true-signed behavior that does **not** exist today.
- **Proposer:** on a known-biology fixture (two TP53 claims) candidate-gen pairs them and the agent emits
  a `coheres` relation + rationale; declines on unrelated claims (agent mocked; live smoke behind a
  tripwire).
- **Property:** whole-bundle byte-identity when no relations present (no regression).

## 11. Scope / YAGNI — what Slice 1 does *not* do

No Tier-1 adjudication (Slice 2); no Tier-2 experiment resolution (Slice 3); no license-earning /
FDR-charging (relations stay CONJECTURED); the `restriction_map` kind is *defined and rendered* but its
sheaf-suppression wiring is Slice 2; no viewer interactions beyond rendering the new nodes/edges.

## 12. Open questions / risks

1. **Subject normalization** is load-bearing: candidate-gen is only as good as the entity key it extracts
   from source-claim `Subject`s. Mitigation: start with arms known to share subjects (AML/RUNX1 across
   synbio + fusion-expression); measure realized connectivity before scaling.
2. **Proposer calibration** has no ground truth in Slice 1 (relations don't earn until Slice 2). Interim:
   cap proposals per candidate, require rationale, eyeball the audit log; treat the CONJECTURED graph as a
   hypothesis set, not a result.
3. **Projection hyper-params** (`status_factor`, the `|A|·|B|` normalizer, per-kind base weights incl.
   negative magnitudes) are layout knobs; pick defaults, expose them, validate on the fixture.
4. **Topology contract version** — bumping `TopologyEdge` touches every bundle consumer; confirm the
   drop-when-None serializer keeps existing bundles byte-identical and the viewer tolerates absent fields.

## 13. References

- `grammar/src/polymer_grammar/{subject,claim,defeat,equivalence,proposition}.py` — the reused/extended schema.
- `protocol/src/polymer_protocol/{corpus,topology}.py` — `Corpus` (4 collections), `TopologyEdge` (the
  versioned contract), `export_topology` (the projection site).
- `src/polymer_claims/embedding.py` — umbrella/numpy `build_graph` (`KIND_WEIGHT`, `polar`/`RHO`) +
  `spectral_layout`; gains true signed weights.
- `docs/superpowers/foundations/measurement-foundation.md §5.3`; `residualism.md`; `BACKLOG.md §1`.
