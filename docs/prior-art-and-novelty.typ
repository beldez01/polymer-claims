// Prior Art & Novelty Positioning for Polymer's epistemic core.
// Build:  typst compile prior-art-and-novelty.typ
// Companion to epistemic-core-derivation.typ.

#set page(
  paper: "us-letter",
  margin: (x: 1.15in, y: 1.0in),
  numbering: "1",
  header: context {
    if counter(page).get().first() > 1 [
      #set text(size: 8pt, fill: luma(120))
      Prior Art & Novelty Positioning #h(1fr) Polymer Claims
      #line(length: 100%, stroke: 0.3pt + luma(200))
    ]
  },
)
#set text(font: "New Computer Modern", size: 10.5pt)
#set par(justify: true, leading: 0.64em, spacing: 1.05em)
#set heading(numbering: "1.1")
#show heading: set block(above: 1.4em, below: 0.8em)
#show heading.where(level: 1): set text(size: 13pt)
#show heading.where(level: 2): set text(size: 11pt)

#let notebox(kind, body, accent) = block(
  width: 100%, inset: (x: 11pt, y: 9pt), radius: 3pt,
  fill: accent.lighten(90%), stroke: (left: 2pt + accent), breakable: true,
)[#strong[#kind.] #body]
#let claimbox(body) = notebox("The novelty claim", body, rgb("#2f5fa6"))
#let honest(body) = notebox("Honest boundary", body, rgb("#a6602f"))

#align(center)[
  #text(size: 18pt, weight: 700)[Prior Art & Novelty Positioning]
  #v(2pt)
  #text(size: 12pt)[Where Polymer's epistemic core sits in the literature]
  #v(6pt)
  #text(size: 9.5pt, fill: luma(90))[
    The novel composition — FDR-gated claims fused with a formal defeat graph — its nearest
    published neighbors, and the honest limits of the novelty claim.
  ]
  #v(4pt)
  #line(length: 55%, stroke: 0.5pt)
]

#v(4pt)

#text(size: 9pt, fill: luma(110))[
  Companion to `epistemic-core-derivation.pdf`. Prior-art findings are from a structured adversarial
  web search (2026-07); see §6 for what that search did and did not cover, and the References for
  what was actually located. Bibliographic details should be confirmed against primary sources
  before external distribution.
]

// ======================================================================
= The claim, stated precisely

It is easy to overclaim novelty and easy to underclaim it. This document does neither: it states
exactly what is new, concedes loudly what is borrowed, and names the two published systems that come
closest.

#claimbox[
  Polymer's epistemic core is the *composition* of three ingredients into one operation:
  $ "LICENSED" quad <==> quad underbrace(("live e-LOND discovery"), "online e-value FDR")
    thick and thick underbrace(("in the grounded extension"), "formal defeat graph") $
  where a successful **defeat** acts as a **retraction** in the FDR ledger, valid only under a
  **null-bearing** soundness condition (a refund requires the defeat to entail the effect-null, not
  merely attack the warrant — see the Refund-Validity theorem in the companion document). *Every
  ingredient is established prior art. The composition — online e-value FDR control as the
  acceptance-and-retraction mechanism for a value-based argumentation framework — was not found
  published anywhere.*
]

The one-sentence positioning: **the pairing of online-FDR/e-value machinery with Dung-style
argument-graph semantics is an empty cell in the literature** — before one even adds the
null-bearing retraction theorem on top. The two nearest neighbors each occupy *one* of the two axes
and stop.

// ======================================================================
= The composition, decomposed

Intellectual honesty first: each ingredient, taken alone, is fully anticipated — sometimes by
decades-old work. If a reviewer names any of these as "not yours," the correct response is instant
agreement. The novelty lives only in the weld, not the parts.

#table(
  columns: (1.1fr, 1.6fr, auto),
  inset: 8pt, align: (left + top, left + top, left + top),
  stroke: 0.4pt + luma(200),
  table.header([*Ingredient*], [*Fully anticipated, alone, by*], [*Status*]),
  [*A — Value-based defeat graph*\ (Dung grounded extension; an attack defeats unless the target
   Pareto-dominates it on the strength vector)],
  [Dung (1995) for grounded semantics; Bench-Capon (2003) for value/preference-filtered defeat;
   strength-based argumentation (Rossit et al., 2022).],
  [`[E]` established],
  [*B — Online FDR via e-values*\ (e-LOND allocation $alpha_t = q gamma_t(D+1)$; discovery iff
   $e_t >= 1\/alpha_t$; FDR control under arbitrary dependence)],
  [Xu & Ramdas (2024) for e-LOND; Waudby-Smith & Ramdas (2024) and Shafer (2021) for betting
   e-values; Wang & Ramdas (2022) for e-value FDR.],
  [`[E]` established],
  [*C — Defeat-as-retraction under a null-bearing condition*\ (a successful defeat tombstones /
   refunds the ledger only if it entails the effect-null)],
  [Closest analogues only: AGM-style belief revision over argumentation frameworks
   (Coste-Marquis et al.) — but purely qualitative, no statistics; Traxia (2026) — a heuristic
   staleness decay, no formal semantics, no error control.],
  [`[P]` the weld],
  table.cell(colspan: 3, inset: 8pt)[
    #set text(size: 9.5pt)
    *Reading:* A and B are each a direct hit against a mature, separate literature. Ingredient C —
    coupling the two so that an argument defeat becomes a *statistically sound* retraction — is where
    no prior art was located, and is where the companion document's Refund-Validity theorem lives.
  ],
)

#pagebreak(weak: true)

// ======================================================================
= The positioning map

Place every relevant system on two axes: how much *statistical error control* it enforces (none →
p-value online FDR → e-value online FDR under arbitrary dependence), and how much *formal claim
structure* it carries (flat claims → a heuristic contradiction graph → a formal defeasible
argumentation framework). The two component-exact prior works sit on the two margins; Polymer is the
corner where the axes meet.

#table(
  columns: (8.5em, 1fr, 1fr, 1.15fr),
  inset: 7pt, align: (left + horizon, center + horizon, center + horizon, center + horizon),
  stroke: 0.4pt + luma(200),
  table.header(
    [], [*No error\ control*], [*Online FDR\ (p-values, LORD++)*],
    [*Online FDR\ (e-values, e-LOND —\ arbitrary dependence)*],
  ),
  [*Formal defeasible\ argumentation*\ #text(size: 8pt, fill: luma(120))[(Dung + value/Pareto defeat)]],
  [#text(size: 9pt)[Bench-Capon 2003;\ AGM-AF revision\ #emph[(pure logic)]]],
  [#text(size: 9pt, fill: luma(150))[— empty —]],
  [#block(fill: rgb("#2f5fa6").lighten(78%), inset: 5pt, radius: 3pt, width: 100%)[
    #strong[POLYMER]\ #text(size: 8pt)[with null-bearing\ retraction theorem]]],
  [*Heuristic\ contradiction graph*\ #text(size: 8pt, fill: luma(120))[(edges, staleness score)]],
  [#text(size: 9pt)[Traxia 2026\ #emph[(staleness decay)]]],
  [#text(size: 9pt, fill: luma(150))[— empty —]],
  [#text(size: 9pt, fill: luma(150))[— empty —]],
  [*Flat / no claim\ structure*],
  [#text(size: 9pt, fill: luma(120))[most AI-scientist\ generators]],
  [#text(size: 9pt)[Sargsyan 2026\ #emph[(Lean-verified\ p-FDR gate)]]],
  [#text(size: 9pt)[Xu & Ramdas 2024\ #emph[(e-LOND, pure stats)]]],
)

#v(2pt)

The map makes the position legible in one glance: **the two papers that *exactly* match a single
ingredient sit on the margins** — Bench-Capon in the left column (formal argumentation, no
statistics), Xu & Ramdas in the bottom row (e-value FDR, no claim structure) — and **Polymer is the
only entry in the top-right corner.** The middle column (p-value online FDR) and the corner cell
were both empty until placed here.

// ======================================================================
= The two nearest neighbors

Two 2026 systems reach *part* of the composition. Both are worth being able to discuss precisely,
because they are what a well-read reviewer will raise.

== Sargsyan (2026) — the statistical half, no claim graph

*"Structural Enforcement of Statistical Rigor in AI-Driven Discovery"* (arXiv:2511.06701). A Haskell
`Research`-monad + OS-sandbox architecture that structurally *forces* an AI-scientist pipeline to run
online FDR control, with a machine-checked Lean 4 proof of the FDR bound down to floating point.

- *What it shares (strong overlap, ingredient B):* it frames Polymer's exact problem sentence —
  autonomous systems manufacture spurious discoveries through uncontrolled multiple testing; gate
  every hypothesis through an online-FDR error budget — and ships a *working* FDR-gated
  claim-acceptance architecture for automated science.
- *The distance (ingredients A and C absent):* it uses **p-values and LORD++**, not e-values /
  e-LOND, so it carries **no arbitrary-dependence guarantee** — the very property that lets a defeat
  graph (which is nothing but dependence structure) live *inside* the statistics. It has **no
  argument graph, no defeat relation, no retraction**: its only ledger event is a *fresh* test,
  never a claim attacked by another claim. The null-bearing condition has nothing to attach to.

*One-line placement:* Sargsyan solved the statistical-engineering half Polymer also needs; he does
not touch the knowledge-representation half that is Polymer's contribution.

== Traxia (2026) — the graph half, no statistics

*"Traxia: A Framework for Verifiable, Agent-Native Scientific Publishing"* (arXiv:2606.08256). A
living knowledge graph of "epistemic artefacts" (claims with confidence intervals + reasoning
traces), with `contradicts` / `replicates` edges and a *staleness score* that spikes on retraction,
major revision, or replication of cited work.

- *What it shares (adjacent, ingredients A and C in spirit):* it is thematically the closest thing to
  Polymer's corpus — a self-correcting claim graph in which contradiction propagates and standing
  decays on retraction.
- *The distance (formality and statistics both absent):* the contradiction handling is **pairwise
  detection, not a Dung admissibility / grounded-extension computation**; there is **no
  strength/Pareto defeat filtering**; and the staleness score is a **heuristic decay function, not a
  ledger with a soundness condition**. There is **no FDR and there are no e-values** — no statistical
  error-rate guarantee of any kind.

*One-line placement:* Traxia has the *vibe* of a self-correcting graph; Polymer has the grounded
extension and the theorem. It reaches for ingredient C by heuristic and never touches B.

// ======================================================================
= The dangerous citation, and the defense

Of everything found, **Sargsyan (2026) is the single citation a hostile reviewer would weaponize** —
raise it *yourself* before they do. The attack: *"online FDR control for AI-driven discovery is
already solved — 2511.06701, with a Lean proof."* The defense is three clean distances:

+ *Different statistics.* p-values + LORD++ vs. e-values + e-LOND — no arbitrary-dependence guarantee,
  which is the enabling property for coupling to a defeat graph.
+ *No knowledge representation.* No claims attacking claims, no grounded extension, no defeat — the
  entire argumentation layer that is Polymer's subject is absent.
+ *No retraction, hence no null-bearing condition.* Its budget events are fresh tests only; there is
  nothing to retract, so the Refund-Validity result has no analogue there.

Net: *close on the plumbing, absent on the epistemics.* Traxia is the thematically-closest paper but
a much weaker mechanism, and it is easy to distinguish ("they have the staleness heuristic; we have
the grounded extension and the FDR theorem").

// ======================================================================
= Honest boundaries of the search

The novelty claim is *"to the best of a structured prior-art search,"* not *"proven first."* The
search's limits, which travel with the claim:

- It used **general web search, not a paywalled DBLP / Scopus / ACM / IEEE full-text citation-chase.**
  A workshop paper (COMMA, TAFA, NMR) or a poorly-indexed stats-venue paper **cannot be ruled out.**
- **Non-English literature** was not searched.
- **Very recent (last-few-weeks) preprints** or non-arXiv venues may not yet be crawled.
- **Closed / internal industry systems** — e.g. pharma safety-signal adjudication, which sometimes
  blends argumentation-like review with sequential testing — are unpublishable and therefore outside
  reach.

#honest[
  The defensible phrasing for a pitch or a paper: *"To the best of a structured prior-art search, no
  published work fuses defeasible argumentation with online e-value FDR control; the nearest neighbor
  gates AI discovery on p-value FDR but carries no argument graph. We treat this as strong evidence of
  a novel composition, not proof — a systematic citation-database search is the step before any
  first-in-literature claim."* Claiming "novel composition" is supported; claiming "the first, full
  stop" is not yet supported and should wait for the database search.
]

// ======================================================================
= Bottom line

#notebox("In one paragraph", [
  Every ingredient of Polymer's epistemic core is borrowed and old: Dung grounded semantics and
  value-based defeat (Bench-Capon), online FDR via e-values under arbitrary dependence (Xu & Ramdas),
  betting e-values (Waudby-Smith & Ramdas). The contribution is the **weld** — using e-value online
  FDR as the *acceptance-and-retraction* mechanism for a value-based argumentation framework, with a
  null-bearing soundness condition governing when a defeat may refund the ledger. The two 2026 systems
  that come closest each reach one axis and stop: Sargsyan gates AI discovery on FDR but has no
  argument graph; Traxia has a self-correcting claim graph but no statistics. The pairing itself is an
  empty cell in the searched literature. That makes this a *novel composition* — the Git/Sigstore
  shape, where no component is new but the synthesis is — which is exactly the defensible kind, held
  honestly to the limits of the search.
], rgb("#2f5fa6"))

// ======================================================================
#v(6pt)
#line(length: 100%, stroke: 0.4pt + luma(200))
#text(size: 8.5pt)[
  *References* (located by the 2026-07 prior-art search; confirm details before external distribution).
  #set enum(numbering: "[1]", spacing: 0.5em)
  + K. Sargsyan. Structural Enforcement of Statistical Rigor in AI-Driven Discovery: A Functional
    Architecture. arXiv:2511.06701, 2026. #link("https://arxiv.org/abs/2511.06701")
  + W. Dogah. Traxia: A Framework for Verifiable, Agent-Native Scientific Publishing. arXiv:2606.08256,
    2026. #link("https://arxiv.org/abs/2606.08256")
  + T. Bench-Capon. Persuasion in practical argument using value-based argumentation frameworks.
    #emph[J. Logic and Computation] 13(3), 2003.
  + P. M. Dung. On the acceptability of arguments and its fundamental role in nonmonotonic reasoning,
    logic programming and n-person games. #emph[Artificial Intelligence] 77(2), 1995.
  + Z. Xu, A. Ramdas. Online multiple testing with e-values (e-LOND). #emph[AISTATS], 2024.
    #link("https://proceedings.mlr.press/v238/xu24a/xu24a.pdf")
  + R. Waudby-Smith, A. Ramdas. Estimating means of bounded random variables by betting.
    #emph[J. R. Stat. Soc. B], 2024. G. Shafer. Testing by betting. #emph[J. R. Stat. Soc. A], 2021.
  + R. Wang, A. Ramdas. False discovery rate control with e-values. #emph[J. R. Stat. Soc. B], 2022.
  + A. Hunter. Probabilistic argumentation (survey); H. Prakken. Probabilistic strength of arguments
    with structure. — probability *as credence over graphs*, not sequential FDR control.
  + S. Coste-Marquis et al. Belief revision in abstract argumentation (extension-based / minimal-change
    of argument statuses). #emph[Artificial Intelligence] / AAAI.
  + M. Rossit et al. Admissibility in strength-based argumentation. arXiv:2207.02258, 2022.
]
