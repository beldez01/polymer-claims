# A Measurement-Theoretic Type Discipline for Polymer Claims

**Status:** Brainstorm-stage foundational proposal. NOT a spec, NOT a plan.
Written to be cross-checked by an independent reviewer (human or another model)
*before* we plan or implement. The goal is to find out whether this is genuinely
sound or merely elegant.

**How to read this:** §1–2 give self-contained context (the reviewer is assumed
to have no other access to the project). §3–6 are the proposal. §7 is the honest
list of ways it could be wrong — **the reviewer should attack these first.**

---

## For the reviewer — the load-bearing claims to check

If any of these is false, the proposal weakens or collapses. Check them directly:

1. **The vulnerability is real and central:** that rigorous downstream machinery
   computing over an ad-hoc world→formalism mapping produces *false confidence*,
   not just noise — and that this is the system's dominant failure mode.
2. **The claimed cure is correctly scoped:** that a type discipline cannot
   *eliminate* this slippage (symbol-grounding / Duhem–Quine is unsolvable), but
   *can* concentrate it at one explicit, auditable seam with a computable detector.
3. **The detector is the right one:** that "meaningfulness = invariance under the
   admissible transformations of the assay's measurement scale" (representational
   theory of measurement) actually catches the dangerous slippage, and is
   checkable in practice.
4. **The MAE layering is correct:** that MultiAssayExperiment solves the
   *sample/entity* axis of comparability but not the *measurement-semantics* axis,
   and that the proposed division of labor is accurate.
5. **The regress terminates:** that choosing the admissible-transformation group
   does not just relocate the original slippage (see §7.1 — the sharpest objection).

---

## 1. Context: what Polymer Claims is

Polymer is a **trust substrate for scientific claims**. A claim moves from
`PENDING` to `LICENSED` only when two genuinely independent implementations agree
on a fully-pinned, content-addressed analysis that beats a pre-stated criterion
(a severe test), survives a defeat graph, and clears an e-value-based
false-discovery-rate budget. The verification mechanism is **recomputation, not
argument**, which is why it does not degrade as AI generators hallucinate.

Four layers: a pure **grammar** (the claim IR — a typed representation of what a
claim *is*); a pure **protocol** (how a corpus evolves); an impure **node** (runs
the loop, touches data); a **viewer** (renders the corpus as a live 3-D universe).
A guiding doctrine borrowed from formal methods (the **de Bruijn kernel**):
concentrate all trust in a tiny recomputation kernel; treat every proposer —
human or AI — as untrusted scaffolding the kernel checks. (More: `docs/superpowers/foundations/MAP.md`,
`docs/superpowers/foundations/epistemology.md`.)

## 2. The problem this addresses — the parameterization seam

Every rigorous component (e-values, sheaf-cohomology consistency gauge, defeat
graph, the kernel) computes over a *representation*. That representation is
produced by an act of **parameterization**: someone or some agent decides "this
assay readout *is* this dimension of biological information; this claim *carves
out* this region of that dimension." 

**If that act is ad hoc, every downstream gear turns over a meaningless encoding —
and the system becomes worse than useless, because it launders garbage into
mathematically-credentialed authority.** Rigor below a sloppy seam manufactures
false confidence.

This is the **symbol-grounding problem** (Harnad 1990) and the deepest form of the
**Duhem–Quine** limit already documented in `docs/superpowers/foundations/epistemology.md`: grounding a
formalism in the world cannot be made perfect by any formal means. The seam
between world and formalism is where rigor leaks, and it leaks *silently*. The
project's existing instincts already flinch at this exact seam (the "do not
sheaf-ify prose — you'd be measuring encoding artifacts" warning; the
unit/dimension-mismatch flagging).

The thesis of this document: **this seam is the single most important place to
install rigor, and there is a century-old, computable theory for doing so.**

---

## 3. The proposal — meaningfulness as invariance, checked at one seam

### 3.1 The core thesis

> A claim may earn standing only if its criterion's truth is **invariant under the
> admissible transformations of the measurement scale of the assay it is
> parameterized over.** Slippage at the parameterization seam shows up precisely
> as a claim whose verdict *changes* under a transformation that should not change
> anything. Meaningfulness = invariance; that invariance is the type-check.

### 3.2 The intellectual lineage (why we believe this is the right object)

*This proposal did not begin with measurement theory — it began here. The
generative intuition was Wittgenstein's "a proposition is a region of logical
space" together with theoretical biology's morphospace; the representational theory
of measurement (§3.3) is what we reached for once we asked how that intuition would
survive contact with a real, messy assay. The lineage below is not a discarded
detour — it is why the rest of the document exists.*

- **Frege → early Wittgenstein.** Frege's *Begriffsschrift* (1879) sought a formal
  logic of content; Wittgenstein's *Tractatus* (1921) made a proposition **a region
  of logical space** — it carves the totality of possible states of affairs into
  permitted vs. excluded, and the truth table makes the carving explicit. A
  proposition's content *is* the region it picks out.
- **The biological translation.** An **assay defines a measurement space** — the
  totality of possible readouts (methylation array → a point in [0,1]^probes;
  RNA-seq → counts in ℕ^genes). A **claim is a predicate over that space** — it
  carves the subset of readouts that would make it true. **Data is one point.**
  The criterion is the *boundary*; the e-value measures how far into the true
  region vs. the null region the point falls.
- **Precedent in theoretical biology — morphospace.** This is not loose analogy.
  Raup (1966) parameterized *all possible shell shapes* with a few coiling
  parameters; real mollusks are points, and one asks which regions are occupied,
  empty, or forbidden (ancestor: D'Arcy Thompson, *On Growth and Form*, 1917). The
  proposal is **morphospace generalized from morphology to any assay readout.**
- **The modern formal tool — refinement / dependent types.** The lineage *logical
  space → model theory → type theory* terminates in refinement types: a type that
  *is* a predicate carving out a subset. "Claim = region of assay-space" is, made
  rigorous, a refinement type over a measurement space.

### 3.3 The actual foundation — the representational theory of measurement

The rigorous, practical theory of "what an assay readout means as a dimension, and
when a claim over it is meaningful" already exists: **Krantz, Luce, Suppes &
Tversky, *Foundations of Measurement* (1971–1990).**

- An **assay is a homomorphism** from an *empirical relational structure* (samples
  and the relations actually observable among them) to a *numerical relational
  structure*. That homomorphism **is** the parameterization. Measurement theory is
  the study of when it is valid.
- **Stevens' scale types** (nominal / ordinal / interval / ratio; Stevens 1946)
  each carry a group of **admissible transformations** — permutations / monotone /
  affine `ax+b` / similarity `ax`. The scale type fixes what the numbers are
  *allowed to mean*.
- **The meaningfulness principle** (Suppes & Zinnes 1963; Narens; Luce): *a
  statement is meaningful iff its truth value is invariant under the admissible
  transformations of the scales involved.* This is a **computable criterion**, not
  a philosophy.
- **Proven special case in hand:** dimensional analysis / the Buckingham π theorem.
  Units-as-types; "you cannot add meters to seconds." Physics has run on typed
  parameterization with an invariance check for a century, and it catches real
  errors. Polymer's grammar already flags unit/dimension mismatches — i.e., it is
  *already doing measurement-theory-lite.* The proposal elevates that from a flag
  to the foundational invariant of licensing.

### 3.4 The typed claim calculus (the concrete shape)

| Calculus element | Biology |
|---|---|
| **Type** | an assay measurement-space (with its scale type + admissible-transformation group) |
| **Value** | a readout (a point in that space) |
| **Claim** | a refinement type — a predicate carving a region `{x : Assay │ φ(x)}` |
| **Program** | the apparatus / evaluation plan — a typed map from raw data to derived quantities |
| **Type-check** | the claim is well-formed in a real assay-space **and** its criterion is invariant under the assay's admissible transformations |

The "theoretical range" = the inhabited region of the type; the null = its
complement.

---

## 4. Why this is the right *role* for type theory (the de Bruijn move at the world boundary)

A type theory **cannot eliminate** the slippage — that would solve symbol grounding
and Duhem–Quine, which is impossible. Its achievable and sufficient job is the
**de Bruijn move applied to the world→formalism boundary**: since the
parameterization cannot be trusted, make it a *tiny, explicit, typed, auditable
seam* with a detector on it, rather than an implicit assumption smeared across
every layer.

The payoff is that it **collapses "consider all levels at once" into "one seam, one
invariant."** Everything above the parameterization seam (e-values, sheaf, defeat
graph) *inherits* its validity from the single invariance check. The infinite
regress of "but is *this* grounded?" terminates at one checkable property. You do
not have to hold all levels simultaneously; you have to certify one seam.

The dangerous slippage stops being invisible rot and becomes a **typed, locatable,
rejectable error**: a claim whose meaning depends on an arbitrary normalization, an
unstated reference, a non-comparable platform (450K vs. EPIC arrays), or an
ordinal-treated-as-interval mistake **fails to type-check** and cannot earn
standing. The exact failure that would render the system useless becomes the exact
failure the system refuses to license. This is also a strong **agent guardrail**:
ungrounded claims become *un-expressible*, not merely un-licensable — the de Bruijn
kernel pushed to the front of the pipeline.

---

## 5. Cross-assay comparability and MultiAssayExperiment (MAE)

Comparing across assays has **two axes**, and a standard Bioconductor format solves
one of them.

### 5.1 What MAE solves — the sample/entity axis

MultiAssayExperiment (Ramos/Waldron et al., *Cancer Research* 2017) coordinates
multiple assays over a **shared set of biological entities**:

- `colData` — one row per biological unit. **The shared base.**
- `ExperimentList` — the assays (each a `SummarizedExperiment`).
- `sampleMap` — maps, per assay, which assay column is which biological unit
  (handles partial overlap, many-to-one aliquots).

This is already categorically structured along the *sample axis*: `colData` is the
**base** (objects = entities), each assay is a **fibration/presheaf** over it,
`sampleMap` is the **indexing morphism** (the gluing data: "this β-column and this
count-column are the same patient"), and coherent cross-assay subsetting is
**functorial**. Additionally, `SummarizedExperiment`'s `rowRanges` (GRanges) means
the **genomic-coordinate axis is already typed** (positions, liftover-able). We
ride all of this — reinventing it would be foolish ("ride, don't rebuild").

### 5.2 What MAE does NOT solve — the measurement-semantics axis

MAE aligns *which samples*; it says nothing about *what readouts mean to each
other*. It does not provide: measurement types / invariance (§3); a semantic
cross-assay map (methylation ↔ expression); or provenance-as-universal-property.
It is a container, not a type theory.

### 5.3 The functor distinction

"Map between assay-spaces" splits into two very different things, and MAE sits
*underneath* both:

- **Structural maps that are real functors and already exist as tooling:** genome
  liftover (GRCh37→38 — a partial map *with provenance baked in* via chain files),
  450K↔EPIC probe harmonization, unit conversions. **Ride these.**
- **Biological maps that are NOT functors — they are claims:** methylation→
  expression is a *hypothesis*, true sometimes, contested often. So the cross-assay
  relationship for biologically-distinct assays becomes a **first-class licensable
  claim in the corpus**, not asserted infrastructure. The platform does not assert
  the functor; it licenses (or defeats) it.

### 5.4 The clean layering

> **MAE = the shared base. Measurement theory = the types on the fibers. The corpus
> = the licensed maps between them.**

We ride MAE for sample/coordinate plumbing; we own the invariance type-check and
the cross-assay relationships-as-claims that make readouts mean something to each
other.

---

## 6. How it fits the existing platform, and the minimal form

### 6.1 Fit

- **Grounds the grammar:** today's syntactic type system becomes *semantic* — a
  claim is a computable region, not a well-formed string.
- **Unifies grammar with the sheaf layer:** sheaf stalks *are* points/regions in
  these assay-spaces; the consistency gauge becomes "do these regions overlap or
  contradict," so the type system and the cohomology become the same geometry.
- **Elevates existing unit/dimension flagging** from a warning to the foundational
  licensing invariant.

### 6.2 The minimal, ship-compatible form (NOT a programming language for biology)

The foundation is a **measurement-theoretic type discipline whose core is a single
invariance check at the assay seam** — a scalpel, not a cathedral. First worked
example:

> **Methylation β-space.** Declare its empirical structure and scale type (bounded
> on [0,1]; specify the admissible-transformation group — normalization choices),
> and require each EWAS claim's criterion to be invariant under that group. One
> assay, one invariance check, wired into the EWAS verification tool we were
> already going to build.

This is the experiment that decides whether the idea is real or merely beautiful:
formalize β-space, take one concrete EWAS criterion, and check it for invariance
end to end.

### 6.3 Morphospace — the generative layer the foundation unlocks

Measurement theory and **morphospace** (theoretical biology's parameterized space
of possible forms, in which a real instance is one point) are not alternatives —
they are a **stack**:

- Measurement theory = the *soundness of the axes* (are the dimensions real, is the
  claim invariant). **Defensive.**
- Morphospace = the *geometry of the populated space* (which regions are occupied,
  empty, or forbidden). **Generative.**

The dependency runs one way: **a meaningful morphospace requires meaningful axes
first** — a morphospace over an ad-hoc parameterization is exactly the "measuring
encoding artifacts" failure of §2. So measurement theory is prerequisite to
morphospace, and morphospace is what turns a *validated* space from merely
trustworthy into scientifically generative. Measurement theory makes Polymer a
verifier; morphospace makes it a **discovery map.**

The organizing structure is the occupied/empty/forbidden trichotomy (the heart of
Raup's original morphospace — the interesting thing was the *empty* shell-shapes no
mollusk occupies):

| Morphospace region | In the corpus | What it is |
|---|---|---|
| **Occupied** | licensed claims | known biology |
| **Empty but reachable** | the frontier | hypotheses / predictions — *where to send agents* |
| **Forbidden** | high-confidence negatives / defeated regions | constraints, laws |

Two connections to what already exists:

- **The viewer is already a morphospace.** The 3-D universe renders claims as points
  in a projected assay-space; the sheaf gauge measures that space's geometry. The
  near-free move is to read **empty-but-reachable regions as the agent frontier** —
  a principled answer to *what to recompute next* (the Arc-3 "deploy an agent to
  examine a region"). The frontier is the structured void in the map, not random.
- **The frame recurs across molecular biology** (so this is not
  evolutionary-morphology-only): protein/sequence space (Maynard Smith 1970),
  expression-state space (the Waddington landscape; single-cell trajectories and RNA
  velocity as a vector field over it), metabolic flux space (the FBA feasible
  polytope), protein fold space. "A parameterized space of biological possibility,
  populated by real instances, with occupied/empty/forbidden structure" is a
  recurring, productive idea at exactly the molecular layers Polymer targets.

**Placement (honest sequencing):** the full theoretical-morphospace program is a
separate, possibly-publishable undertaking — not this project, not now. But the
concept is *not* superseded by measurement theory; it is the generative payoff the
measurement foundation exists to unlock. Near-term: recognize the viewer as a
morphospace and drive the agent frontier from its empty regions (in scope, cheap).
Later: the occupied/empty/forbidden geometry of an assay class as a scientific
result.

---

## 7. Honest open questions — attack these first

These are the places the proposal is most likely wrong. The cross-check should
prioritize them.

1. **Does the regress actually terminate? (The sharpest objection.)** "Meaningful =
   invariant under admissible transformations" requires *specifying the admissible-
   transformation group* — but choosing that group is itself an act of
   parameterization. Does the invariance check genuinely concentrate the slippage,
   or does it merely *relocate* it from "what does the readout mean" to "what is the
   right transformation group"? Argument for termination: the group is a *single,
   explicit, declarable, attackable* object (and itself a licensable meta-claim),
   versus slippage diffused invisibly across all layers — so the regress stops at
   one auditable place even if it does not vanish. Is that argument sound, or
   special pleading?
2. **Survival of contact with real data.** β-values are not cleanly ratio-scale;
   normalization is not a clean mathematical group; batch effects are not a
   transformation at all. Does the formalism survive messy real assays, or does it
   only work on idealized ones?
3. **Does the check have teeth?** Will real criteria mostly pass/fail trivially, or
   does invariance actually discriminate good parameterizations from bad ones on
   realistic examples? If most criteria trivially pass, the check is theater.
4. **Decidability.** Refinement-type / invariance checking is undecidable in
   general. Is the relevant fragment mechanically checkable, or does it require
   per-assay manual proof (which reintroduces an operator-trust seam)?
5. **Early vs. later Wittgenstein.** This proposal is *early* Wittgenstein (meaning
   = position in logical space). The defeat/argumentation graph is *later*
   Wittgenstein (meaning = use in a web of claims). Can both coexist coherently, or
   do they encode incompatible theories of meaning?
6. **Cross-assay claims circularity.** Treating methylation→expression as a
   licensable claim means claims-about-claims-about-assays. Does this create
   vicious circularity in licensing, or is it well-founded?
7. **Strategic necessity vs. gold-plating.** Prior strategy work concluded the
   project's gap is *distribution, not theory.* Is this foundation necessary now,
   or is it an intellectually delicious delay? (Counter: §6.2 claims the minimal
   form is small enough to live *inside* the first shippable tool. Is that true, or
   rationalization?)
8. **Is "forbidden" distinguishable from "unobserved"? (Morphospace's classic
   weakness.)** The generative occupied/empty/forbidden trichotomy (§6.3) is only
   useful if empty regions that are genuinely *forbidden* (a real constraint/law)
   can be told apart from regions that are merely *unsampled* or historically
   contingent — the standard critique of theoretical morphospace. Does Polymer's
   machinery (severity, high-confidence negative claims, the defeat graph) actually
   separate "forbidden" from "not yet looked," or does the trichotomy collapse in
   practice into occupied vs. not-occupied?

---

## 8. Key references (for verifying the lineage)

- **Measurement theory:** Krantz, Luce, Suppes & Tversky, *Foundations of
  Measurement*, vols. I–III (1971, 1989, 1990); Stevens, "On the Theory of Scales
  of Measurement," *Science* (1946); Suppes & Zinnes (1963); Narens, *Theories of
  Meaningfulness*; Buckingham π theorem (dimensional analysis).
- **Theoretical morphology / morphospace:** Raup, "Geometric Analysis of Shell
  Coiling" (1966); D'Arcy Thompson, *On Growth and Form* (1917); McGhee, *The
  Geometry of Evolution: Adaptive Landscapes and Theoretical Morphospaces* (2007).
  Molecular extensions: Maynard Smith, "Natural Selection and the Concept of a
  Protein Space" (*Nature* 1970); the Waddington landscape and single-cell
  state-space / RNA-velocity literature; flux-balance analysis (the metabolic flux
  polytope).
- **Logic / philosophy:** Frege, *Begriffsschrift* (1879); Wittgenstein,
  *Tractatus* (1921) and *Philosophical Investigations* (1953); Harnad, "The Symbol
  Grounding Problem" (1990).
- **Types:** refinement / dependent type theory (the logical-space → type-theory
  lineage).
- **Bioinformatics substrate:** Ramos et al., "Software for the Integration of
  Multiomics Experiments in Bioconductor," *Cancer Research* (2017)
  [MultiAssayExperiment]; Lawrence et al., "Software for Computing and Annotating
  Genomic Ranges," *PLOS Comp Biol* (2013) [GRanges/SummarizedExperiment].
- **Project internal:** `docs/superpowers/foundations/MAP.md`, `docs/superpowers/foundations/epistemology.md` (de Bruijn kernel,
  Duhem–Quine, e-value/FDR), `docs/superpowers/foundations/scaled-infrastructure.md`.

---

## 9. One-paragraph summary (for the reviewer's verdict)

Polymer's rigor is bottlenecked by one seam: the act of parameterizing a messy
biological observation into the typed representation its machinery computes over.
Ad-hoc parameterization launders garbage into mathematically-credentialed
authority. No formalism can eliminate this (symbol grounding / Duhem–Quine), but
the representational theory of measurement supplies a **computable detector** —
*meaningfulness = invariance under the assay scale's admissible transformations* —
that, installed as a licensing precondition at that single seam, makes the
dangerous slippage a typed, rejectable error and lets every upper layer inherit
validity from one check. Bioconductor's MultiAssayExperiment already provides the
*sample/entity* base this sits on; the measurement-type layer and the cross-assay
relationships-as-claims are what Polymer adds. The minimal form is one assay
(methylation β-space) with one invariance check, wired into the first shippable
tool. **The question for the reviewer: is the invariance detector genuinely
load-bearing, or does choosing the transformation group merely relocate the
slippage it claims to catch?**
