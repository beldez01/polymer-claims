# Sheaf Consistency Gauge — Design

**Date:** 2026-06-21 · **Status:** Design (approved in brainstorm; pre-plan)
**North-star anchor:** `2026-06-12-phase-2-north-star.md` §3 (sheaf cohomology as the corpus's
global-consistency gauge — the *lead* category-theory bet) and §5 (the living universe). Linchpin
`2026-06-16-linchpin-thesis-three-layer-arc.md` A3 (the Reproducibility Observatory — `q` and H¹ as
the field's instruments).

> **One line.** Model the claims graph as a cellular sheaf over scalar quantitative content; compute
> the sheaf Laplacian's energy, H⁰, and localized H¹ obstructions; expose a corpus-level
> **distance-to-consensus** number that falls as independent recomputation brings claims into harmony —
> and that flags contradiction cycles no pairwise check can see. An **instrument, not a gate.**

---

## 1. Goal & non-goals

**Goal.** Turn "the corpus grows toward truth" from a slogan into a measured, falling number, and surface
**H¹ obstructions** — sets of claims that are pairwise-satisfiable but jointly irreconcilable — localized
to the claims responsible. This is North-star §3's lead bet and the most legible form of linchpin A3.

**Non-goals (this slice).**
- **Not a gate.** The gauge observes; it does **not** change any license/reject/PENDING decision. The
  recomputation kernel stays exactly as small as it is today (north-star §7 invariant: every rigor
  upgrade is scaffolding *around* the kernel, never inside it).
- **No prose.** Only claims carrying comparable quantitative content are sheaf-ified (§3 warning:
  "do not sheaf-ify prose — you'd be measuring encoding artifacts").
- **No rich viewer visualization** of obstruction cycles — slice 1 ships a single falling readout; the
  per-cycle rendering is a named fast-follow (§8).

## 2. Invariants this design must not violate

(From `CONTINUE.md` "Invariants / working agreements" and north-star §7.)

- `grammar/` and `protocol/` stay **pure, deterministic, numpy-free** (no clock/random/IO). The sheaf
  *structure extractor* is pure protocol; all linear algebra lives **umbrella-side behind `[embed]`**,
  lazy-imported and **not re-exported**, exactly like `embedding.py`.
- `Corpus` stays **4 collections**. No new collection; the gauge is a pure read.
- All models subclass frozen `_Model` (`extra="forbid"`); collections are **tuples**; no `dict`/`list`
  fields. The report DTOs are content-addressable.
- New cross-cutting fields land **additive/optional** (`X | None = None`) and are **byte-identical when
  off** or when numpy is absent.

## 3. The cellular sheaf

Graph `G = (V, E)` built from a frozen `Corpus`:

### 3.1 Vertices `V` — who participates

A claim is a vertex **iff** its leaf is a `QuantityLeaf` (it has `value: float` and, for the constraint
to be meaningful, a `Dimension`). `CategoricalLeaf` / `ExistenceLeaf` / `PropositionLeaf` claims are
**excluded** — that is the "no prose" line. Participation is further governed by a **status filter**
(parameter, default = claims whose status carries a computed value: `LICENSED` ∪ `PENDING`; `REJECTED`/
refuted excluded). Stalk `F(v) = ℝ`; the assigned section value `x*_v = leaf.value`.

### 3.2 Edges `E` — equivalence (agreement) and defeat (antagonism)

- **Equivalence edges** from `EquivalenceClaim(left, right, severity, status)` whose **both endpoints are
  vertices**. Oriented by canonical id-order. Edge stalk `F(e) = ℝ`.
- **Defeat edges** from the corpus `defeat_edges`, restricted to **effective** attacks via the existing
  `effective_defeats(edges, strength, licensed_ids)` VAF filter (so a Pareto-dominated or inert
  provisional attack contributes nothing). Oriented attacker→target. Edge stalk `F(e) = ℝ`.

### 3.3 Restriction maps (the honest core)

For an edge `e` incident to `u, v`, the coboundary `δ` produces a scalar discrepancy `d_e`:

- **Equivalence:** `d_e = x_u − ρ·x_v`, an agreement constraint (`d_e = 0` ⟺ the two genuinely agree).
  **Commensurability gate on ρ (honesty correction):** the `Dimension` algebra proves *dimensional
  commensurability* (same exponent signature) but carries **no numeric scale factor** between named
  units, and there is no unit-conversion registry in the repo today. Therefore in slice 1:
  - both endpoints share a `Dimension` **and** an identical `unit` → `ρ = 1` (a real value-constraint);
  - dimensions **differ** → the equivalence is **incommensurable**, excluded from the value sheaf, and
    reported as a `data_quality_flag` (you cannot sheaf-ify a kg against a second);
  - dimensions match but `unit` strings differ with no known conversion → a `unit_mismatch` flag
    (a degenerate, real obstruction: an asserted equivalence across unconvertible units), edge excluded
    from the numeric Laplacian but surfaced in the report.
  A numeric unit-conversion registry supplying real `ρ ≠ 1` is a future enrichment (§8).
- **Defeat:** `d_e = x_a + ρ·x_t` — **antagonistic** (sign-flip), the Hansen-Ghrist discourse-sheaf
  treatment of antagonistic coupling. This is the *exact stalk-generalization* of the signed Laplacian
  already in `embedding.py` (positive edge → `(x_u − x_v)²`, polar/defeat edge → `(x_u + x_v)²`). The
  same commensurability gate applies (`ρ = 1` on matching unit; mismatches flagged, edge excluded).

> **Interpretive caveat (carried into the report and the docs — honesty over polish).** Equivalence
> edges are *hard value-constraints* with unambiguous meaning. Defeat-as-sign-flip is a **modeling
> choice**: it encodes "a strong defeater and its strong target are in tension," which is defensible and
> consistent with the existing signed embedding, but its quantitative reading is **softer** than
> equivalence. The `ConsistencyReport` therefore **separates `equivalence_energy` from `defeat_energy`**
> so the two tension kinds are never silently conflated, and the spec/GLOSSARY state the assumption
> explicitly.

### 3.4 Edge weights `w_e` — by confidence (chosen)

`L = δᵀ W δ`, `W = diag(w_e)`:

- **Equivalence weight** = the `EquivalenceClaim.severity` scalar (already in `[0, 1]`), optionally
  scaled by a status multiplier (`LICENSED` = 1, `PENDING` < 1; parameter).
- **Defeat weight** = the **attacker claim's e-value** from the FDR ledger (a genuine scalar already in
  the system), falling back to `1.0` for an effective-but-unscored attacker. We use the e-value rather
  than projecting `StrengthVector`, because strength is **deliberately non-collapsed** (6-axis Pareto, no
  hidden scalar) — the e-value is the honest scalar confidence and ties the gauge to the e-value-native
  core, exactly as the brainstorm chose.

## 4. What we compute

Weighted sheaf Laplacian `L = δᵀ W δ` over the scalar stalks. Computed **per connected component**
(mirroring `embedding.py`), with deterministic sign/ordering handling.

- **`inconsistency_energy`** `= x*ᵀ L x*`, **normalized by total edge weight `Σ w_e`** (a per-edge mean
  tension, so the number is comparable as the corpus grows). This is **Robinson's consistency radius**:
  the squared distance from the corpus's *actual* values to the nearest globally-consistent assignment.
  **The headline "distance-to-consensus" that falls as recomputation harmonizes claims.** Reported as the
  total and the `equivalence_energy` / `defeat_energy` split.
- **`spectral_gap`** `= λ₂(L)` (smallest non-trivial eigenvalue) — the continuous algebraic-connectivity
  gauge; a separate, structure-only consensus readout.
- **`h0_dim`** `= dim ker L` — the consistent-world degrees of freedom (≈ count of independent consensus
  clusters / global sections).
- **`h1_obstructions`** — the differentiator. On a graph sheaf these live on the **cycle space**. A cycle
  carries an obstruction iff it is **closed but inexact** (its discrepancies are locally consistent yet
  admit no global value assignment) — equivalently, nontrivial holonomy / a nonzero harmonic H¹
  representative around the loop. Each is returned **localized**: the `claim_ids` and `edges` on the
  cycle plus a scalar `magnitude`. *This is the contradiction no pairwise check sees.*
- **`per_claim_tension`** — each claim's contribution to `inconsistency_energy` (its rows of `x*ᵀ L x*`),
  so blame is localizable to the specific claim dragging consensus down.

## 5. Architecture & components

```
Corpus ──extract_sheaf()──▶ SheafStructure ──consistency_report()──▶ ConsistencyReport
        protocol, pure        tuples, no numpy   umbrella, [embed]      protocol DTO (frozen)
```

### 5.1 `protocol/src/polymer_protocol/sheaf.py` (pure, numpy-free)

- `extract_sheaf(corpus, *, status_filter=...) -> SheafStructure` — the pure structure extractor.
- DTOs (frozen `_Model`, tuples): `SheafVertex(claim_id, value, dimension_sig, unit)`,
  `SheafEdge(kind, u, v, weight, sign)` (every edge in the tuple is commensurable by construction;
  incommensurable/mismatched pairs never become edges — they land in `flags`),
  `SheafStructure(vertices, edges, flags)`,
  and the output `ConsistencyReport`, `Obstruction(claim_ids, edges, magnitude)`,
  `ClaimTension(claim_id, tension)`, `DataQualityFlag(kind, claim_ids, detail)`, and the lightweight
  `ConsistencyHeadline(inconsistency_energy, spectral_gap)`.
- Protocol can **describe** the sheaf and **define** the report, but **cannot compute** the spectrum
  (no numpy) — the same boundary as force-vs-spectral layout today.

### 5.2 `src/polymer_claims/sheaf_spectrum.py` (umbrella, numpy behind `[embed]`)

- `consistency_report(structure: SheafStructure) -> ConsistencyReport` — builds `δ`/`L` per component,
  computes energy / `λ₂` / `h0_dim` / H¹ obstructions / per-claim tension, returns the filled DTO.
- **Lazy-imported and NOT re-exported** (base import stays numpy-free); graceful "needs `[embed]`" path
  when numpy is absent, identical to the spectral-layout fallback.
- Reuses `embedding.py` numerical-determinism patterns: per-component decomposition, symmetric
  normalization, 6-dp rounding before sign/pivot choices so cross-BLAS float noise can't flip results.

## 6. Surface

- **CLI `export-consistency <corpus.json>`** (mirrors `export-topology`) → full `ConsistencyReport`
  JSON, on-demand. Requires `[embed]`; clean message if absent.
- **Live headline:** `TopologyExport` gains optional `consistency: ConsistencyHeadline | None`, carrying
  only the **cheap** scalars — `inconsistency_energy` (a sparse mat-vec, no eigendecomposition) and
  `spectral_gap` (a few Lanczos iterations). The expensive parts (H⁰ nullity, H¹ cycle analysis,
  per-claim tension) stay on-demand. Additive/optional → byte-identical when off or numpy absent.
- **Viewer:** a minimal readout of the falling energy over the timeline. Rich per-cycle obstruction
  rendering is the §8 fast-follow.
- **Relationship to `q`:** a complementary instrument shown alongside `q`. It does **not** gate
  licensing in this slice.

## 7. Testing (TDD — failing test first)

**Pure extractor (protocol, no numpy):**
- hand-built corpus → exact `SheafStructure` (vertices, oriented edges, weights, signs, commensurability
  flags); non-quantity claims excluded; dimension-mismatch and unit-mismatch surface as flags.

**Spectrum (umbrella, `[embed]`), against analytic answers:**
- one equivalence edge, agreeing values → `energy = 0`, `h0_dim = 1`; disagreeing → `energy = w·d²`
  (after normalization).
- **the differentiator test:** a 3-cycle of equivalences, pairwise-satisfiable but with nontrivial
  holonomy / no global assignment → one `h1_obstruction` localized to those three claims.
- **defeat sign:** two equal-valued claims + a defeat edge → `defeat_energy = w·(2x)²` while an
  equivalence would give `0` — confirms antagonism, and confirms the equivalence/defeat split.
- **monotonicity ("grows toward truth"):** move two equivalent claims' values closer → `energy`
  strictly decreases.
- **determinism:** same corpus → byte-identical `ConsistencyReport` (content-addressable).
- **purity guard:** extend the isolation/import test — base import stays numpy-free; `sheaf_spectrum`
  is lazy and not re-exported.

**Acceptance.**
1. `inconsistency_energy` is a normalized, monotone distance-to-consensus that falls as equivalent
   claims harmonize.
2. An H¹ obstruction is detected and **localized** for a locally-consistent-but-globally-contradictory
   cycle that pairwise checks miss.
3. Purity invariants hold; the whole spectrum path is `[embed]`-gated and byte-identical when off.
4. Honest failure is fine: if the corpus is genuinely inconsistent, the gauge **reports** it — that is
   the instrument working.

## 8. Future enrichments (recorded, deferred)

- **Stalk enrichments:** standardized-effect stalk (`value ÷ SE`, using `QuantityLeaf.uncertainty`); the
  `ℝ²` `(value, uncertainty)` stalk so agreement is precision-weighted; vector stalks for
  `QuantityVectorLeaf`.
- **Weights:** `confidence × stalk-precision` once per-claim uncertainty is in the stalk.
- **Unit-conversion registry** supplying real `ρ ≠ 1` so cross-unit equivalences become live constraints
  rather than flags.
- **Viewer:** rich rendering that highlights obstructed cycles and per-claim tension on the universe.
- **Instrument → gate:** an H¹ obstruction as a first-class defeat-trigger, or folding the consistency
  radius into `q` — the step that makes the gauge *act*, taken only once the encoding is proven honest.
- **Connection to the embedding:** the sheaf Laplacian generalizes `embedding.py`'s signed Laplacian;
  a later unification could drive the hyperbolic/Lorentz layout (north-star §5) from the same operator.
- **Functorial merge / colimit** (north-star §3 second bet) — a separate arc, not this gauge.

## 9. Open questions for the plan stage

- Exact H¹ localization algorithm (cycle-basis choice + harmonic representative) and its cost bound;
  confirm it stays off the per-tick path.
- Status-multiplier defaults for PENDING equivalences (weight vs exclude).
- Whether `export-consistency` reads a corpus JSON only, or also a live node snapshot.
