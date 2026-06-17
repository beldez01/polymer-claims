# Polymer Claims — Phase 2 North Star

**Status:** Vision / strategic anchor. v1.0
**Date:** 2026-06-12
**Author:** Z. Belden (synthesis grounded in a seven-territory landscape survey)
**Purpose:** Anchor the next several arcs the way the credibility-arc roadmap anchored Phase 1.
Read this first when a Phase-2 task touches the rigor core, the integration layer, or the universe.

> **One-line thesis.** Every system in the landscape either *stores* assertions or *generates*
> them; none makes a claim **earn its standing through independent recomputation**. We are the
> trust substrate that hole implies — the write-target where a claim becomes a durable,
> content-addressed object whose standing is *earned* and *continuously re-examined as the world
> drifts*. Phase 1 proved one claim can be licensed this way. Phase 2 makes the licensing
> **mathematically sound, standards-native, and alive.**

---

## 0. How Phase 1 sets up Phase 2

Phase 1 (grammar → protocol → node → the CES spine) proved the hard kernel: a claim can move
PENDING → LICENSED only when **two genuinely independent implementations agree on a real,
fully-pinned, content-addressed analysis that beats a criterion**, and a drift daemon re-opens that
license when the data/apparatus content-address moves. That is already further than anything
surveyed. Phase 2 does not replace it — it makes it *rigorous*, *interoperable*, and *visible*.

---

## 1. The convergent white space (why this is the right bet)

A landscape survey across seven territories returned the **same hole from every side** — the
strongest possible signal that the position is real and unoccupied:

- **Scholarly knowledge graphs** (nanopublications, ORKG, OpenAlex, Semantic Scholar/S2ORC,
  Wikidata/Scholia, SEPIO, the Underlay): store statements + provenance. *"Content-addressing is
  solved; computation-addressing is not. No system models epistemic state as a lifecycle.
  Independence is never operationalized."* Nanopublications' Trusty-URI content-addressing and the
  Underlay's raw-vs-curated two-layer split are the ideas worth keeping; neither ships earned
  standing.
- **AI agents for science** (FutureHouse/Kosmos, Google AI Co-Scientist, Sakana AI Scientist, CMU
  Coscientist, A-Lab): generate claims *into a void where verification is optional, identity is
  unstable, and independent replication has no formal channel.* **The epistemic OS is the missing
  write-target beneath all of them.**
- **Provenance / FAIR infra** (W3C PROV, RO-Crate, GA4GH DRS/WES/TRS, Sigstore/Rekor, in-toto/SLSA,
  Nix/Guix, CODECHECK): operate in *record mode* or *replay mode*. *No machine-enforced gate
  requires independent re-execution before a claim is granted standing; nothing is drift-aware.*
  CODECHECK is closest (independent re-execution → certificate) but manual, non-cryptographic,
  one-shot, drift-blind.
- **Formal methods** (Lean/mathlib, Isabelle/AFP, HOL Light, AlphaProof): **solved** earned standing
  — a result is valid because its proof checks against pinned dependencies in a tiny trusted kernel —
  but only for *deduction*. The trust model does not transfer to empirical claims for free.

The cautionary tales share **one root cause** — no mandatory independent-recomputation gate before a
claim gets standing:

- **Galactica** (Meta, 2022): fabricated plausible papers/authors; pulled in 72 hours.
- **A-Lab** (Berkeley/DeepMind, *Nature* 2023): "discovered" materials already in the crystal
  database; *Nature* correction Jan 2026.
- **Sakana AI Scientist** (2025): passed blind peer review with hallucinated numbers — the only gate
  didn't have the code.
- **Google Co-Scientist** (2025): internally, agents ignored available contrary evidence 68% of the
  time; the "debate" was performative.

**We are the gate each of those needed — and our gate is recomputation, not an LLM arguing, which is
exactly why it does not degrade as the models hallucinate.**

---

## 2. The rigor agenda (the intellectual moat)

Five commitments, in leverage order. (A) and (B) are the spine. This is what takes us from "good
system" to "mathematically and philosophically sound system."

### (A) The de Bruijn kernel reframe — concentrate trust, distrust everything else
Formal methods' deepest lesson: HOL Light trusts ~500 lines, Lean ~10k; *everything else* — tactics,
AI provers, elaboration — is untrusted scaffolding that must emit kernel-checkable artifacts. This is
**why AlphaProof's hallucinations don't matter**: the kernel catches them. Trust scales with kernel
*minimality*, not model quality.

**Our doctrine:** name an explicit, tiny **claim kernel** — *given a fully-pinned computation
(content-addressed code + data + environment), does re-running it produce the output that licensed
the claim?* AI proposers, human analysts, methylation adapters are all untrusted scaffolding. We
already have the instinct (air-gap + content-address); the reframe makes it law: nothing earns
standing except by passing the kernel. **What does not transfer:** data integrity — a reproducible
build of fabricated data is still reproducible. That is precisely why the kernel alone is
insufficient and why *independence* (E) is load-bearing.

### (B) The e-value / FDR / defeat unification — highest leverage, and genuinely novel
Today defeat edges, LICENSED status, and the FDR ledger are three subsystems. The literature says
they should be **one mechanism**, and the math is post-2020 and nearly unused in this context:

- Make the **evidence atom an e-value** (a betting score / likelihood ratio against the
  criterion-null), not a p-value. Our "two independent implementations beat a criterion" event is
  *naturally* an e-value.
- Make the **FDR ledger an alpha-investing wealth process** over those e-values. The decisive
  property: **e-BH (Wang–Ramdas 2022) controls false-discovery rate under *arbitrary* dependence
  with no correction factor.** Our defeat/equivalence edges *are* dependence structure — under
  classical Benjamini–Hochberg that makes us unsound, and the dependence-robust Benjamini–Yekutieli
  pays an ~ln(m) penalty that would make a growing corpus unable to license anything. e-values
  dissolve this.
- e-values **multiply** across independent evidence and are **anytime-valid** (online e-LOND,
  Xu–Ramdas 2024) — a claim accrues evidence over time and across implementations with no
  alpha-spending crisis as the universe grows.
- **The unification:** a successful **defeat is a downward e-value update**; if it pushes the claim
  below the e-BH threshold it de-licenses *and refunds alpha-wealth*. Licensing, defeat, drift, and
  FDR become the same operation viewed from different angles.

Making *the argumentation attack-relation and the multiple-testing dependence structure the same
object* does not exist in the literature. We would not cite a paper for it — we would write it.
**This is the flag to plant, and it retroactively unifies everything CES already built.**

### (C) Credence primary; LICENSED is a thresholded view
Binary-only standing is provably incoherent under conjunction (lottery / preface paradoxes). The fix
is not to deny it but to make the **e-value primary** and **LICENSED a thresholded projection**, and
to *instrument* the preface paradox: the FDR ledger **is** the honest statement "we expect ≤ q of
LICENSED claims to be false." That q becomes our **headline integrity metric** — we are sound
precisely because we report it. (Leitgeb's stability theory is the model for "stably LICENSED";
Foley's Lockean thesis is the bridge.)

### (D) Grounded argumentation, with gated attacks and hysteresis
Our defeat typology (rebut / undercut / undermine) is **literally ASPIC+'s**; our
LICENSED/PENDING/contested is **literally Caminada's IN/OUT/UNDEC** labelling — a principled third
state for free. Adopt **grounded semantics** (unique, polynomial-time, skeptical — the only semantics
that won't thrash or spuriously promote under graph updates). Two dampeners so the universe doesn't
flicker: an attack **fires** only once the *attacker* clears its own evidence bar (an unfounded
PENDING claim cannot undecide a hard-won license); and **demotion costs more evidence than
promotion** (AGM: contraction is harder than expansion; Levi/Harper identities). Recomputation
localizes to the attack-reachable subgraph — bounded blast radius.

### (E) Define "independent" rigorously — the criterion most likely to be quietly violated
We conflate two things: **probabilistic independence of errors** (what makes "two beats one" a real
severity multiplier) and **methodological diversity**. The first is almost always *false* — two
implementations share data, a reference genome, a library, a statistical convention, a prior;
correlated error is exactly how replication crises happen (the engine of Ioannidis). What we want is
**conceptual replication** (Wimsatt robustness — different algorithm, different assumptions, *fails
for different reasons*), not **direct replication** (same method twice, which tests only
reproducibility). Concretely: build a **common-cause DAG** per implementation (shared
inputs/methods/assumptions = edges) and require a license to show *low shared-cause overlap*.
Probabilistic independence then becomes a **derived, evidenced claim** (Reichenbach screening-off),
not an asserted premise. No one else even names this distinction; it is a real differentiator.

**The spine in one sentence:** e-values + online-FDR (Vovk/Wang/Ramdas) for the evidence-and-error
layer, grounded Dung/ASPIC+ semantics for the defeat-and-status layer, glued by a severity (Mayo)
reading of the criterion — and the contribution-no-one-has is making the attack relation and the
testing dependence structure *the same object*.

---

## 3. Where category theory genuinely earns its place

Two places, one warning. Category theory is the **hard truth-maintenance backbone**; embeddings are
the **soft perceptual projection** on top. Do not conflate them — the embedding is the *view*, the
categorical layer is the *truth*.

**Lead bet — sheaf cohomology as the corpus's global-consistency gauge.** Model the claims graph as a
**cellular sheaf**: each claim a stalk (its quantitative content), each equivalence edge a restriction
map demanding agreement, each defeat edge an antagonistic map. Then **H⁰** (kernel of the sheaf
Laplacian) = the space of globally consistent worlds the corpus admits; **H¹** = a *computable,
localizable obstruction class*, nonzero exactly when every region is locally consistent but no global
reconciliation exists — a contradiction cycle no pairwise check can see. The **sheaf Laplacian's
spectrum** is a continuous "global inconsistency energy" that *falls as independent recomputations
bring claims into harmony* — a mathematically-grounded **distance-to-consensus gauge** for "grows
toward truth." Near-exact precedent: **Hansen & Ghrist, discourse sheaves** (opinion dynamics with a
nonlinear Laplacian discounting antagonistic communication) — swap agents/opinions for
claims/recomputations and it transfers almost verbatim. Robinson's *consistency radius* is the
applied-engineering form.

**Second bet — functorial data migration as provably-coherent ingest.** "Integrate dataset X under
apparatus Y" becomes a **functor**; "merge sources" becomes a **colimit (pushout)** in which
**provenance is the universal-property witnesses** — not bolted on, but the mathematical content of
the merge. CQL/Conexus is deployed-but-niche; AlgebraicJulia/Catlab (ACSets) is lively-but-research-
grade.

**The warning (cargo-cult line):** sheaf Laplacians are *linear algebra over vector-space stalks*.
Sheaf-ify claims that carry comparable quantitative content (effect sizes, parameter estimates); **do
not sheaf-ify prose** — you'd be measuring encoding artifacts. Operads / institutions / DisCoPy are
inspiration, not infrastructure, unless we genuinely have multiple incompatible *logics* (institutions)
or compose open dynamical processes (operads — and note: a recompute-and-revise loop *is* a lens).

---

## 4. The pan-integrator play (the adoption moat)

The strategic inversion: **we do not integrate the world's data and compute — we integrate *trust
over* them.** Ride the existing FAIR/GA4GH fabric and add the one layer it structurally lacks
(adjudication + drift). Express our content-address model *as the standards that already exist*, so we
are natively a node in the fabric, and adoption is "point your existing pipeline at us," not "rewrite
for us." Seams, ranked by leverage:

1. **GA4GH DRS** — our content-addressed dataset handle (we already mirror its shape). Speak `drs://`
   → interoperate with Terra, Seven Bridges, *All of Us*, BioData Catalyst on day one. Our
   `semantic-run-id` can be a DRS compound object over dataset + apparatus.
2. **Workflow Run RO-Crate + GA4GH TRS** — apparatus pin = a version-pinned workflow descriptor
   (CWL/Nextflow/WDL) in WorkflowHub plus a hashed `ro-crate-metadata.json`.
3. **in-toto / SLSA + Sigstore/Rekor** — emit each run as a signed, transparency-logged attestation
   (`subject` = output hash, `resolvedDependencies` = input DRS checksums). Any third party verifies
   a run *without trusting our service* — trust lives in a public Merkle log, not in us.
4. **GA4GH WES** — our compute bus. Dispatch re-execution to anyone's WES endpoint; we are the
   licensing layer and never build execution infra.
5. **FAIR Signposting** — near-free HTTP headers making every claim/dataset/run machine-navigable to
   any FAIR crawler (Zenodo/Dataverse/DSpace already consume it).
6. **Refget SeqCol** — the exact primitive that kills "same GRCh38, different patch" drift for
   genomics (SHA-512t24u over the canonical sequence collection).

**Reframe of our own work:** the CES content-address / apparatus / drift machinery is a *first
implementation of the adjudication layer the provenance world is missing*. Re-express it in their
vocabulary and our drift daemon already does the thing nobody else has.

---

## 5. The living universe (the vision made well-founded)

- **Geometry:** keep the signed-Laplacian backbone (it correctly separates refuting claims), but
  project the eigenvectors into **Lorentz/hyperbolic** space, not Euclidean. Knowledge has
  hierarchical depth (theory ⊃ claim ⊃ sub-claim); hyperbolic space embeds trees with arbitrarily low
  distortion, Euclidean provably cannot. **Procrustes-align each incremental update** (≈ free,
  O(k²n)) so the universe evolves smoothly instead of thrashing — this retires our deferred
  "live-streaming stability" item with a principled fix. Embed high-D for search; project to 3D only
  for the view. Use Lorentz-model (not Poincaré-disk) implementations for numerical stability.
- **The buzz (agents):** "a user deploys an agent from their own compute to examine a region" is
  supported by *nothing* that exists. It requires our object model plus a protocol: **region manifest
  → pull locked artifacts → re-execute → post verification/attack events with hardware attestation.**
  Attack agents are first-class (the Co-Scientist Elo-tournament insight) — but **grounded in
  recomputation, not LLM debate**, which is the precise fix for what made their debate performative.
- **Credence layer:** proper scoring (log-score vs. a community baseline, à la Metaculus) for
  *resolvable* claims; **Surrogate Scoring Rules / peer-prediction over batches of graph-neighboring
  claims** for the unresolvable ones (our graph *is* the correlation structure those mechanisms need —
  the highest-leverage unexploited mechanism for us). Prediction markets only where claims resolve
  (DARPA SCORE: 73% on replication forecasts). **Avoid token economies** until a large pseudonymous
  base exists — Goodhart destroys the signal before it compounds. Keep scores private until
  resolution; prefer relative to absolute scoring.

---

## 6. Phase 2 sequencing

Through-line: **Phase 1 proved a claim can be licensed by real, pinned, independent recomputation;
Phase 2 makes that licensing sound, standards-native, and alive.** Three arcs, in dependency order:

1. **The epistemic core (rigor — the moat).** e-values as the evidence atom + FDR-ledger-as-
   alpha-wealth + defeat-as-e-value-update unification; grounded semantics with gated/hysteretic
   transitions; the common-cause graph that makes "independent" measurable. *Start here* — highest
   leverage, where we're past the literature, and it snaps CES + the drift daemon + defeat edges into
   one coherent mechanism.
2. **The standards skin (pan-integrator — the adoption moat).** Re-express content-address / apparatus
   / run as DRS + RO-Crate/TRS + in-toto/SLSA/Rekor + WES; become a node in the GA4GH/FAIR fabric.
   Additive, can proceed in parallel.
3. **The living universe (the vision).** Hyperbolic + Procrustes embedding; the local-compute agent
   protocol; the credence layer; and — the long-horizon flourish — the sheaf-consistency gauge
   humming underneath, turning "grows toward truth" into a number that goes down. Design toward the
   sheaf layer now; build it once the quantitative-stalk encoding is honest.

**Recommended first slice:** the **e-value / FDR / defeat unification** (arc 1) — brainstorm → spec →
plan → subagent-driven, the established rhythm. It is the keystone the rest leans on.

---

## 7. Invariants this vision must not violate

- **Purity:** grammar/protocol stay pure/deterministic; all impurity (e-value computation from data,
  re-execution, embedding) stays umbrella-side. The new math is still a pure transform over
  passed-in evidence.
- **The kernel stays small.** Every rigor upgrade is scaffolding around the minimal recomputation
  kernel, never inside it.
- **Honesty over polish.** The headline metric is the corpus false-license rate (q), reported, not
  hidden. Synthetic-data and deferred-rigor caveats travel with every claim until earned.
- **Ride, don't rebuild.** Prefer expressing our model in an existing standard over inventing a
  parallel one.

---

## 8. Key sources (for the next builder)

- **e-values / FDR under dependence:** Wang & Ramdas, *FDR control with e-values* (JRSS-B 2022);
  Xu & Ramdas, online e-LOND (2024); Ramdas et al., LORD/SAFFRON/ADDIS (online FDR).
- **Argumentation / belief:** Dung (abstract AF); Prakken (ASPIC+); Caminada (IN/OUT/UNDEC labelling);
  AGM + Hansson base revision; Leitgeb, *stability theory of belief*; Mayo, *severe testing*;
  List & Pettit (judgment-aggregation impossibility — the warning label).
- **Formal-methods trust model:** Lean/mathlib ("Growing Mathlib", 2025); HOL Light / Metamath Zero
  (de Bruijn criterion); DeepMind AlphaProof (*Nature* 2025).
- **Category theory:** Hansen & Ghrist, *Opinion Dynamics on Discourse Sheaves* (2020); Robinson,
  *consistency radius* (2016); Bodnar et al., *Neural Sheaf Diffusion* (2022); Spivak, *Functorial
  Data Migration* (2010); Schultz/Spivak/Wisnesky, *Categorical Data Integration* (2019); CQL,
  AlgebraicJulia/Catlab.
- **Pan-integrator standards:** GA4GH DRS / WES / TRS / Refget-SeqCol; Workflow Run RO-Crate
  (*PLOS ONE* 2024); in-toto/SLSA; Sigstore/Rekor v2; FAIR Signposting; CODECHECK.
- **Universe / credence:** Lorentz/hyperbolic KG embeddings; Procrustes embedding alignment (2025);
  parametric UMAP / Nomic Atlas; Metaculus scoring; DARPA SCORE replication markets; Liu & Chen,
  *Surrogate Scoring Rules* (2023).
- **Landscape (what we transcend):** nanopublications/Knowledge Pixels; ORKG; OpenAlex; Semantic
  Scholar/S2ORC; Wikidata/Scholia; SEPIO; the Underlay; FutureHouse/Kosmos; Google AI Co-Scientist;
  Sakana AI Scientist; CMU Coscientist; A-Lab; Galactica (the cautionary tale).
