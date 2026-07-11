// Polymer Claims — the one-page spine. Carry-into-the-room reference card. v2.
// Build:  typst compile the-spine-one-pager.typ
#set page(paper: "us-letter", margin: (x: 0.5in, top: 0.42in, bottom: 0.38in))
#set text(font: "New Computer Modern", size: 8.4pt)
#set par(leading: 0.5em, spacing: 0.55em)

#let blue = rgb("#2f5fa6")
#let amber = rgb("#a6602f")
#let green = rgb("#3a7a4a")
#let rose = rgb("#a6392f")

#let sec(label, accent) = text(weight: 700, fill: accent, size: 8.8pt)[#label]
#let anchor(body) = block(width: 100%, inset: (x: 6pt, y: 3.5pt), radius: 2pt,
  fill: blue.lighten(92%), stroke: (left: 2pt + blue))[#text(size: 8.3pt)[#body]]
#let rebut(q, a) = block(width: 100%, inset: 5.5pt, radius: 2pt,
  fill: rose.lighten(93%), stroke: (left: 2pt + rose))[
  #text(weight: 700, size: 7.9pt)[“#q”] #linebreak() #text(size: 8pt)[#a]]

// ── Title + spine mnemonic ──────────────────────────────────────────────
#align(center)[
  #text(size: 15pt, weight: 700)[Polymer Claims — The Spine]
]
#align(center)[#text(size: 8.6pt, fill: luma(80))[
  SPINE (hold three words): #text(fill: blue, weight: 700)[① Warrant] (why) #sym.arrow.r
  #text(fill: amber, weight: 700)[② Locks] (how) #sym.arrow.r
  #text(fill: green, weight: 700)[③ Honesty] (what it delivers) #h(6pt)·#h(6pt) walk it to any question
]]
#line(length: 100%, stroke: 0.5pt + luma(180))
#v(2pt)

// ── The pitch ───────────────────────────────────────────────────────────
#sec("THE PITCH", blue) #h(4pt) #text(size: 7.6pt, fill: luma(110))[slop → which is warranted → protocol → residualism → how → warrant, honestly]
#block(width: 100%, inset: (x: 7pt, y: 6pt), radius: 3pt, fill: luma(248), stroke: 0.4pt + luma(205))[
  #set text(size: 8.6pt)
  We already complain about AI *slop* — we know it when we see it. And the flood is just starting:
  an onslaught of AI-generated science, all plausible, most unchecked. Which raises the only question
  that matters — *which of it is actually warranted?* Polymer is a protocol for answering exactly
  that. It rests on an old truth about science: there is always a *residue of error we can neither
  fully eliminate nor fully locate* — some of what we hold to be true must be false, and we can never
  be sure which. Polymer doesn't pretend otherwise. It *gates out fabrication* and *bounds the false
  positives* (p-hacking at scale), so it can tell you — to a *stated, honest degree* — which claims
  have *earned the right to be believed, without ever condemning the rest as false.*
]

#v(3pt)

// ── Defense in depth ────────────────────────────────────────────────────
#sec("DEFENSE IN DEPTH", amber) #h(4pt) #text(size: 7.6pt, fill: luma(110))[fabrication & p-hacking are the two you name most — the full defense is five layers, each catching a distinct failure]
#v(1pt)
#table(
  columns: (0.85fr, 1.5fr, 1.65fr), inset: (x: 5pt, y: 3.5pt), stroke: 0.35pt + luma(210),
  align: (left + top, left + top, left + top),
  table.header(
    [#text(size: 7.7pt, weight: 700)[Layer — the question]],
    [#text(size: 7.7pt, weight: 700)[Failure it catches]],
    [#text(size: 7.7pt, weight: 700)[The lock]]),
  [*1 · Existence*\ did it happen?],
  [*Fabrication* · faked logs],
  [Attested log (proof-it-ran) + signature & tamper-evident ledger],
  [*2 · Statistics*\ real, or a fluke?],
  [*P-hacking* — multiplicity, peeking, HARKing · weak sources],
  [e-value + e-LOND (FDR ≤ q) + pre-registration + oracle caps],
  [*3 · Structure*\ claim well-formed?],
  [Cooked confounders (Table-2) · smuggled lone p-value · hidden weak dimension],
  [Typed grammar (compile-time) + derived adjustment sets + 6-axis strength],
  [*4 · Independence*\ corroboration circular?],
  [Self-grading · coding artifacts · fake independence],
  [Air gap (proposer ≠ verifier) + independent recompute],
  [*5 · Coherence & time*\ survives \& still true?],
  [Ignored contradictions · improper refunds · drift / staleness],
  [Defeat graph (grounded) + Refund-Validity + drift daemon],
)

#v(3pt)

// ── Two columns: gaps + math | anchors + punches ────────────────────────
#grid(columns: (1.05fr, 1fr), gutter: 9pt,
  [
    #sec("KNOWN GAPS", green) #h(3pt) #text(size: 7.4pt, fill: luma(110))[state them first — naming your flanks is the product]
    #v(1pt)
    #set text(size: 7.9pt)
    #set list(spacing: 0.42em, indent: 2pt)
    - *Conceptual independence* (shared premise) — only partly defended; open problem.
    - The attested log makes forgery a *detectable crime*, not an impossibility.
    - Oracle trust metadata is *operator-authored* today.
    - *False negatives* are acknowledged & re-tested, not bounded (we control Type I, not Type II).
    #v(4pt)
    #sec("THE MATH, IN ONE LINE", blue)
    #v(1pt)
    #block(inset: (x: 6pt, y: 5pt), radius: 2pt, fill: blue.lighten(93%))[
      #set text(size: 7.9pt)
      Believe #sym.arrow.l.r $e >= 1\/alpha_t$, $alpha_t = q dot gamma_t dot (D+1)$.
      *License* reads the bar · *defeat* lowers $D$ · *drift* refreshes $e$ · *q* is the dial.
      $"FDR" <= q$ under *arbitrary dependence* (e-LOND). #linebreak()
      #text(fill: blue, weight: 700)[Your theorem:] Refund-Validity — a defeat refunds the ledger
      *only if it entails the null.*
    ]
  ],
  [
    #sec("ANCHOR LINES", green)
    #v(1pt)
    #anchor[*Sigstore for science* — we *witness & certify*; we never run the science.]
    #v(2pt)
    #anchor[The scarce thing isn't the claim, it's the *right to believe it* — and a generator can't
      grade its own work.]
    #v(2pt)
    #anchor[We produce *warrant, not truth.* Rejected means *unwarranted-for-now*, never false.]
    #v(4pt)
    #sec("THE TWO PUNCHES", rose)
    #v(1pt)
    #rebut("You verify claims → you're a compute engine.",
      [We don't verify — we *witness*. *A referee needs no stadium.* Floor is proof-it-*ran*
       (a log — zero owned compute); recompute is *optional*, run by an independent third party in
       the *user's own environment*.])
    #v(2pt)
    #rebut("If you don't run it, how do you know the log isn't faked?",
      [We make faking a *detectable forgery*, not an *invisible hallucination*: signed by a key the AI
       doesn't hold, in a tamper-evident ledger, author *barred from witnessing itself*. Same
       primitives as Sigstore.])
  ]
)
