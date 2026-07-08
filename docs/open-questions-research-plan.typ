// Open Questions & How We Close Them — a falsifiable research program.
// Build:  typst compile open-questions-research-plan.typ
#set page(
  paper: "us-letter", margin: (x: 0.9in, y: 0.9in), numbering: "1",
  header: context { if counter(page).get().first() > 1 [
    #set text(size: 8pt, fill: luma(120))
    Open Questions & How We Close Them #h(1fr) Polymer Claims
    #line(length: 100%, stroke: 0.3pt + luma(200)) ] },
)
#set text(font: "New Computer Modern", size: 10pt)
#set par(justify: true, leading: 0.6em, spacing: 0.95em)
#set heading(numbering: "1.1")
#show heading: set block(above: 1.3em, below: 0.7em)
#show heading.where(level: 1): set text(size: 12.5pt)
#show heading.where(level: 2): set text(size: 10.5pt)

#let blue = rgb("#2f5fa6")
#let amber = rgb("#a6602f")
#let green = rgb("#3a7a4a")
#let notebox(kind, body, accent) = block(width: 100%, inset: (x: 10pt, y: 8pt), radius: 3pt,
  fill: accent.lighten(91%), stroke: (left: 2pt + accent), breakable: true)[#strong[#kind.] #body]

#align(center)[
  #text(size: 17pt, weight: 700)[Open Questions & How We Close Them]
  #v(2pt)
  #text(size: 11.5pt)[A falsifiable research program for the parameterization seams]
  #v(5pt)
  #text(size: 9.5pt, fill: luma(90))[
    Each open question stated as a testable hypothesis — with the metric that decides it and the
    first study that closes it. The goal is a *program*, not a claimed solution.
  ]
  #v(3pt) #line(length: 52%, stroke: 0.5pt)
]
#v(4pt)

= The stance

These are **genuinely open problems** — several are self-flagged in `foundations/formal-core.md` §9.
The honest goal is *not* to claim they are solved; it is to make each one **decidable**: to state what
a good answer looks like, the number that would confirm it, and the study that produces the number.
That is Polymer's own discipline — *believe nothing you did not earn* — turned inward on its own
design. Two consequences frame everything below:

- **These are empirical, not armchair.** The right strength-axis definitions, role protocol, and
  independence gate cannot be *reasoned* into existence; they are found by running real claims through
  and measuring what breaks. So the **bootstrap universe is the research instrument**, not merely a
  demo: it is *how* these questions get closed.
- **The residual is instrumented, not hidden.** Some seams will never reach high reliability. For
  those, the answer is to *report the uncertainty as part of the claim* (defeasible, attackable), not
  to fake precision. Deciding which questions get *solved* versus *honestly bounded* is itself part of
  the program.

= The method (applied to every question below)

+ **Frame it falsifiably** — for each seam, write what a good answer looks like, what you'd measure,
  and what failure looks like. (The tables below are this ledger.)
+ **Build a small labeled benchmark** — a few dozen real claims with expert-assigned roles, strength,
  leaf-types, and ontology grounding. The ground truth. Hard, essential, start small.
+ **Run calibration studies** — get the numbers *before* betting the architecture on a guess.
+ **Iterate the design against the numbers** — sharpen, split, merge, or further-constrain where a
  metric is poor.
+ **Scale to stress-test** — dozens become thousands; scale surfaces gaming and distribution shift no
  benchmark will.
+ **Instrument the residual** — report variance where convergence fails.

#notebox("Two reflexive shortcuts", [
  *Judgments-as-claims:* run competing parameterization schemes as *rival claims* and let the defeat
  graph adjudicate — dogfood the engine on its own design. *Red-team-first:* for each seam, build the
  attack ("how would I game this?") before the defense — the RED-TEAM daemon, pointed inward.
], green)

= Group A — the parameterization seams (the neurosymbolic frontier)

Where the symbolic type-system meets irreducible judgment. The symbolic layer supplies the typed
slots and constraints; a neural component fills them; the open question is *how reliably*, and *how
much the cage catches.*

#table(
  columns: (1.35fr, 1fr, 1.25fr), inset: 7pt, stroke: 0.4pt + luma(205),
  align: (left + top, left + top, left + top),
  table.header(
    [#text(size: 9pt, weight: 700)[Open question]],
    [#text(size: 9pt, weight: 700)[Success = / metric]],
    [#text(size: 9pt, weight: 700)[First study]]),
  [*A1 · Strength-axis parameterization.* Can the 6 axes — especially the qualitative `world_contact`, `explanatory_virtue` — be assigned reproducibly? *(§9-flagged; most exposed.)*],
  [High *inter-rater reliability* (κ / ICC) between two independent assessors on the same claims. Low κ ⇒ the axis isn't operationally defined.],
  [Assign N real claims by ≥2 independent assessors (or 2 models); compute per-axis κ; sharpen or split the low-reliability axes.],
  [*A2 · Causal role assignment.* Can roles (confounder / mediator / collider) be assigned correctly? The anti-Table-2 guarantee is only as good as this.],
  [*Accuracy vs. a labeled benchmark* of known causal structures; per-role confusion matrix.],
  [Benchmark of claims with expert-labeled DAGs; measure neural-assignment accuracy; red-team the confusable pairs.],
  [*A3 · Ontology grounding.* Do claims about the *same* entity resolve to the same term? (Equivalence & defeat edges require it.)],
  [*Precision / recall* of entity resolution on a labeled set (MONDO / HGVS / `cg`-accession).],
  [Labeled entity set; measure P/R of the grounding step; error-analyze the misses.],
  [*A4 · Neurosymbolic caging.* How much bad neural judgment does the symbolic layer actually catch?],
  [*Red-team catch rate* — inject wrong roles / inflated strengths, measure interception by the type-check + defeat graph.],
  [Adversarial injection suite; measure catch rate; tighten constraints wherever it leaks.],
)

= Group B — the statistical & epistemic frontiers (self-flagged, §9)

#table(
  columns: (1.35fr, 1fr, 1.25fr), inset: 7pt, stroke: 0.4pt + luma(205),
  align: (left + top, left + top, left + top),
  table.header(
    [#text(size: 9pt, weight: 700)[Open question]],
    [#text(size: 9pt, weight: 700)[Success = / metric]],
    [#text(size: 9pt, weight: 700)[First study]]),
  [*B1 · Conceptual independence.* Code-distinctness ≠ statistical independence (the shared-premise / common-cause problem — the *most exposed flank* of the whole construction).],
  [A *shared-premise injection* is detected and correctly *blocks* the e-value product; measure detection rate + false-multiply rate.],
  [Construct leg-pairs with deliberately shared premises; verify the common-cause DAG refuses to multiply; measure the false-multiply rate.],
  [*B2 · Valid e-values from real / literature evidence.* A betting e-value is valid only if its test is well-specified; an e-value *read off* a paper or an LLM is not an e-value without a data model. *(§9: "the single biggest practical risk.")*],
  [On synthetic data with known truth, the extracted e-value is *valid*: realized $bb(E)[e | H_0] <= 1$.],
  [Run the calibration harness (synthetic → real gate) on the extraction pipeline; measure realized validity; reject any extraction path that violates it.],
  [*B3 · Strength ↔ e-value coupling.* The Pareto strength order decides defeats *independently* of the e-value magnitude; the relationship is asserted, not proven *(§9 #4).*],
  [`evidence_against_null` *tracks* the e-value (monotone, no inversions); no counterexample where a Pareto-dominant claim carries weaker evidence.],
  [Correlate the axis with the e-value across the corpus; adversarial counterexample search; couple them formally if inversions appear.],
)

= Sequencing — what to close first

Order by *exposure × cheapness-to-test*, not by intellectual appeal:

+ **A1 (strength inter-rater reliability)** — cheapest to run, and the seam `formal-core` flags as most
  exposed. Start here; the number tells you immediately whether the qualitative axes are real.
+ **B2 (e-value validity from real evidence)** — the *highest-risk* item ("biggest practical risk"):
  if extracted e-values aren't valid, the entire FDR guarantee is void. Close early, on synthetic
  ground truth where validity is checkable.
+ **A4 (caging catch-rate)** — cheap adversarial suite; tells you how much the symbolic layer is
  actually protecting versus how much you're trusting the model.
+ **B1 (conceptual independence)** — hardest and least likely to fully resolve; begin *measuring* it
  early even if the full solution is long-horizon, and instrument the residual honestly.
+ **A2, A3, B3** — fold into the benchmark work; they share the labeled-corpus infrastructure.

= For the pitch

You do not need answers to these before the pitch — you need *this document* as your posture. The
strong line in a room with skeptics: **"Here is the open question, here is the metric that decides it,
and here is why our bootstrap universe is also the instrument that closes it."** A founder who names
exactly what is open and shows a falsifiable plan to close it is *more* credible than one who claims
it is all solved — and it is the honesty identity applied to the roadmap, which is precisely where a
technical reviewer probes.

#notebox("Bottom line", [
  These seams are where objectivity is most at risk — the neural judgment is the subjective part of an
  otherwise-attested system. The program above does not pretend that risk away; it makes each instance
  *measurable*, closes the cheap-and-exposed ones first, and instruments whatever residual won't
  converge. That is not a detour from the thesis — it *is* the thesis, run on Polymer itself.
], blue)
