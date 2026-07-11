// The Epistemic Core of Polymer Claims — a mathematical derivation.
// Build:  typst compile epistemic-core-derivation.typ
// (or via the Python `typst` package: typst.compile(src, output=pdf))

#set page(
  paper: "us-letter",
  margin: (x: 1.15in, y: 1.0in),
  numbering: "1",
  header: context {
    if counter(page).get().first() > 1 [
      #set text(size: 8pt, fill: luma(120))
      The Epistemic Core of Polymer Claims #h(1fr) Mathematical Derivation
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
#set math.equation(numbering: "(1)")

// ---- helper boxes ----
#let notebox(kind, body, accent) = block(
  width: 100%, inset: (x: 11pt, y: 9pt), radius: 3pt,
  fill: accent.lighten(90%), stroke: (left: 2pt + accent),
  breakable: true,
)[#strong[#kind.] #body]

#let theorem(body) = notebox("Theorem", body, rgb("#2f5fa6"))
#let defn(body) = notebox("Definition", body, rgb("#4a7a4a"))
#let lemma(body) = notebox("Lemma", body, rgb("#2f5fa6"))
#let honest(body) = notebox("Boundary of rigor", body, rgb("#a6602f"))
#let proofblk(body) = block(inset: (left: 6pt), stroke: none)[
  #emph[Proof.] #body #h(1fr) $qed$
]

// ---- title ----
#align(center)[
  #text(size: 18pt, weight: 700)[The Epistemic Core of Polymer Claims]
  #v(2pt)
  #text(size: 12pt)[A mathematical derivation of the licensing–defeat–drift–FDR unification]
  #v(6pt)
  #text(size: 9.5pt, fill: luma(90))[
    How belief, statistical error control, and argumentation collapse into a single comparison
    $e >= 1\/alpha_t$ — and exactly why that is justified.
  ]
  #v(4pt)
  #line(length: 55%, stroke: 0.5pt)
]

#v(6pt)

// ======================================================================
= What this document proves

Polymer's technical claim is that four things a knowledge engine normally builds as *separate
subsystems* — deciding what to *believe* (licensing), controlling the *false-discovery rate*,
letting claims *defeat* one another, and *re-examining* claims as the world changes (drift) — are in
fact a single mechanism: reads and writes of one comparison,
$ "believe a claim" quad <==> quad e >= 1\/alpha_t, $
where $e$ is the claim's evidence expressed as an *e-value* and $alpha_t$ is a level the *whole
corpus* sets through one shared counter. This document derives that statement from first principles.

The plan. #ref(<sec:evalue>) builds the evidence atom (the e-value) and proves the single-test
guarantee that makes the comparison legitimate. #ref(<sec:stream>) extends one test to an endless
stream and states the false-discovery-rate theorem the corpus rests on, with its assumptions made
explicit. #ref(<sec:unify>) shows — by inspection of the rule itself — that licensing, FDR control,
defeat, drift, and pre-registration are all the same comparison, and maps each to the exact function
in `grammar/src/polymer_grammar/fdr.py`. #ref(<sec:limits>) states precisely what the mathematics
does *not* buy, which is where Polymer's honesty (and its open problems) live. #ref(<sec:refund>)
proves the one theorem that is the project's *own* — Refund-Validity — establishing exactly when a
defeat may return budget to the ledger without breaking the guarantee.

Three derivations — the single-test bound, the e-value composition rule, and Refund-Validity — are
given in full. The stream-level false-discovery theorem is instead a *published* result (Xu &
Ramdas, 2024), which `fdr.py` cites by name: it is stated exactly, its rigorous first step is given,
and the boundary where the full proof lives is marked rather than reconstructed. That distinction is
the point of this document — it is the line between the established machinery Polymer *assembles* and
the one result it *proves for itself*.

// ======================================================================
= The atom: e-values <sec:evalue>

== The problem an endless machine has with p-values

A p-value is calibrated for *one pre-planned test*: under the null hypothesis $H_0$, a valid p-value
$p$ satisfies $bb(P)_(H_0)(p <= alpha) <= alpha$. Its guarantee dissolves under the two things an
autonomous research engine does constantly — *testing many hypotheses* and *looking at the evidence
as it accumulates and choosing whether to continue*. Under such optional continuation the event "$p$
dipped below $alpha$ at some point" has probability far exceeding $alpha$. A machine that proposes
and tests claims forever is precisely the adversary a p-value is not built to survive. Polymer
therefore needs an evidence measure that is valid under *arbitrary continuation and combination*.
That measure is the e-value.

== Definition and the betting picture

#defn[
  A non-negative random variable $E >= 0$ is an *e-value* for a null hypothesis $H_0$ if
  $ bb(E)_(H_0)[E] <= 1. $
  Equivalently (Shafer; Vovk & Wang; Ramdas et al.), $E$ is the final wealth of a bettor who starts
  with one unit of capital and wagers against $H_0$ in a game that is *fair under $H_0$*: the
  constraint $bb(E)_(H_0)[E] <= 1$ says "you cannot expect to make money betting against the truth."
  A large realized $E$ is therefore evidence *against* $H_0$: you multiplied your stake, which a fair
  game rarely lets you do by luck. Waudby-Smith & Ramdas construct exactly such betting e-values for
  bounded means — the family Polymer's evaluator emits.
]

The whole edifice rests on this one inequality, $bb(E)_(H_0)[E] <= 1$. Everything below is a
consequence of it; #ref(<sec:limits>) returns to what happens if it is only *asserted* rather than
*earned*.

== The single-test guarantee (full derivation)

Why is it legitimate to *believe* a claim the instant $e >= 1\/alpha$? Because that threshold is a
level-$alpha$ test — the false-alarm probability is at most $alpha$ — and this follows in two lines.

#theorem[
  Let $E$ be an e-value for $H_0$ and fix $alpha in (0, 1]$. Then
  $ bb(P)_(H_0)(E >= 1\/alpha) <= alpha. $
  Rejecting $H_0$ (i.e. "licensing the claim") when $E >= 1\/alpha$ is thus a test of level $alpha$.
]
#proofblk[
  Markov's inequality states that for a non-negative random variable $X$ and any $a > 0$,
  $bb(P)(X >= a) <= bb(E)[X] \/ a$. Apply it under $H_0$ with $X = E$ and $a = 1\/alpha$:
  $
  bb(P)_(H_0)(E >= 1\/alpha) <= (bb(E)_(H_0)[E]) / (1\/alpha) = alpha dot bb(E)_(H_0)[E] <= alpha,
  $
  where the last step uses the defining property $bb(E)_(H_0)[E] <= 1$.
]

This is the justification for the one line at the heart of the code —
`discovery = e_value >= 1.0 / alpha` (`fdr.py:67`). The number $1\/alpha$ is not a tuning knob; it
is the exact reciprocal that converts an error budget $alpha$ into a wealth threshold, with the
false-alarm rate provably bounded by $alpha$.

== Combining evidence: why independence is load-bearing (full derivation)

Polymer's REPLICATED tier multiplies two legs' e-values, $e_1 dot e_2$, and treats the result as a
*single* discovery. The following lemma is why that is allowed — and its hypothesis is why
independence is not a nicety but a precondition.

#lemma[
  If $E_1$ and $E_2$ are e-values for $H_0$ and are *independent under $H_0$*, then their product
  $E_1 dot E_2$ is again an e-value for $H_0$.
]
#proofblk[
  Independence under $H_0$ factorizes the expectation:
  $ bb(E)_(H_0)[E_1 dot E_2] = bb(E)_(H_0)[E_1] dot bb(E)_(H_0)[E_2] <= 1 dot 1 = 1. $
  So $E_1 E_2 >= 0$ has null-expectation at most $1$, i.e. it is an e-value.
]

The evidence of two independent legs compounds by multiplication — bankroll from two fair games
placed in series. But read the hypothesis carefully: *independence under $H_0$*. Without it the
factorization fails, and $bb(E)_(H_0)[E_1 E_2]$ can exceed $1$, so the product is *not* a valid
e-value and multiplying is double-counting. This is the precise mathematical location of Polymer's
common-cause gate: two legs' e-values "may even multiply" (the code's phrase) *only* when the
independence hypothesis holds. #ref(<sec:limits>) shows this is also where the deepest open problem
sits — implementation independence does not, by itself, secure the *statistical* independence this
lemma demands.

== Anytime validity (stated; the reason a forever-machine is safe)

Betting e-values extend to *e-processes*: a sequence $(E_t)_(t >= 0)$ with $E_0 <= 1$ that is a
non-negative supermartingale under $H_0$. Ville's inequality (1939) then gives, for every
$alpha in (0,1]$,
$ bb(P)_(H_0)(exists t: E_t >= 1\/alpha) <= alpha. $
The guarantee holds *uniformly over time* — you may stop, peek, and continue at will, and the
false-alarm probability is still bounded by $alpha$. This is the formal reason the licensing gate
survives being run in an unbounded loop, which no p-value threshold does. (We use this as a cited
inequality; the single-test Markov bound derived above is what the ledger applies per test.)

// ======================================================================
= From one test to an endless stream: e-LOND <sec:stream>

== What we must control now

Testing thousands of claims, we no longer want per-test level control; we want to bound the fraction
of *believed* claims that are false. Let, at horizon $T$, $R_T$ be the number of discoveries
(licensed claims) and $V_T <= R_T$ the number of them that are actually null (false). The
*false-discovery rate* is
$ "FDR"_T = bb(E) [ V_T / (R_T or 1) ], $
the expected proportion of licensed claims that are wrong ($R_T or 1 = max(R_T, 1)$ avoids dividing
by zero). The corpus's honest headline metric $q$ is the *target* for this quantity: "we expect at
most a fraction $q$ of licensed claims to be false."

== The budget, and why the discount sums to one (full derivation)

`fdr.py` spreads a fixed total significance budget across the infinite stream using the discount
$ gamma_t = (6 \/ pi^2) / t^2, quad t = 1, 2, 3, dots $
The choice of constant is exact, not cosmetic:
$
sum_(t=1)^oo gamma_t = 6/pi^2 sum_(t=1)^oo 1/t^2 = 6/pi^2 dot pi^2/6 = 1,
$
using Euler's solution to the Basel problem, $sum_(t >= 1) t^(-2) = pi^2\/6$. So $(gamma_t)$ is a
probability distribution over test positions: a *total significance budget of exactly one unit*,
handed out in shares that decrease with position — the earliest hypotheses get the largest slices.
This is what makes "spend more of your error budget on the first, highest-stakes tests" a theorem
rather than a preference.

== The allocation and the decision rule

For the test at position $t$, e-LOND sets the level
$ alpha_t = q dot gamma_t dot (D_(t-1) + 1), $ <eq:alloc>
where $D_(t-1)$ is the number of live discoveries recorded *before* $t$, and licenses iff
$ e_t >= 1 \/ alpha_t. $ <eq:rule>
The factor $(D_(t-1) + 1)$ is the *reward* (the "LOND" — Levels On Number of Discoveries — term):
every confirmed discovery *raises* the level, and therefore *lowers* the bar $1\/alpha_t$, for the
tests that follow. Discoveries fund discoveries. This exact expression is
`target_fdr * _gamma(t) * (n_discoveries + 1)` in `_next_alpha` (`fdr.py:26–29`).

== The false-discovery theorem

#theorem[
  #emph[(e-LOND; Xu & Ramdas, 2024, cited by name in `fdr.py`.)] Let $(e_t)_(t>=1)$ be valid
  e-values for their respective nulls — permitted to be *arbitrarily dependent* on one another — and
  run the online rule #ref(<eq:rule>) with levels #ref(<eq:alloc>) and any non-negative discount with
  $sum_t gamma_t <= 1$. Then at every horizon $T$,
  $ "FDR"_T = bb(E)[ V_T / (R_T or 1) ] <= q. $
]

The single most important word is *arbitrarily dependent*. The classical Benjamini–Hochberg
procedure controls FDR only under independence or a positive-dependence (PRDS) condition. Polymer's
corpus violates any such condition on purpose: its claims *defeat* and are asserted *equivalent* to
one another, so their test statistics are entangled by construction. e-LOND is the tool that keeps
the guarantee with *no* dependence assumption — and that is precisely the mathematical permission
slip that lets Polymer fold the argument graph *into* the FDR ledger instead of keeping them apart
(#ref(<sec:unify>)).

#honest[
  The rigorous engine of the bound is one inequality that needs no dependence assumption. Because
  $e_t >= 1\/alpha_t$ exactly on rejection, and $0 <= bb(1)[e_t >= 1\/alpha_t] <= alpha_t e_t$ for
  every $t$ (the indicator is $0$ or $1$, and $alpha_t e_t >= 0$ with $alpha_t e_t >= 1$ whenever the
  indicator is $1$), the count of *false* discoveries obeys
  $
  V_T = sum_(t in H_0, thin t <= T) bb(1)[e_t >= 1\/alpha_t]
      thick <= thick sum_(t in H_0) alpha_t e_t
      thick = thick q sum_(t in H_0) gamma_t (D_(t-1)+1) e_t.
  $
  Taking expectations, using $bb(E)_(H_0)[e_t] <= 1$ for null $t$ and $sum_t gamma_t <= 1$, bounds
  the expected *number* of false discoveries. The remaining step — dividing by $R_T or 1$ and
  handling the data-dependent reward $D_(t-1)$ *inside* the level so the ratio telescopes to $q$
  under arbitrary dependence — is the technical core established by Xu & Ramdas. We give the
  distribution-free first inequality in full and cite the paper for the telescoping step, rather than
  reproduce a proof whose delicacy is exactly that self-reference. The takeaway that survives without
  the citation: *each false discovery is "paid for" by a null e-value whose expected budget is capped
  at one, so false discoveries cannot run away.*
]

// ======================================================================
= The unification: four operations, one comparison <sec:unify>

Now the payoff. Fix the corpus's ledger state and summarize it by the single running counter $D$ =
number of live (un-retracted) discoveries. Define one primitive predicate,
$ "Discover"(e, thin t, thin D) thick := thick [ thin e >= 1 \/ alpha_t thin ], quad
  alpha_t = q dot gamma_t dot (D + 1). $
The claim is that every epistemic operation in the engine is a read or a write of this one predicate.

#block(breakable: false)[
#table(
  columns: (auto, 1fr, auto),
  inset: 8pt, align: (left + top, left + top, left + top),
  stroke: 0.4pt + luma(200),
  table.header([*Operation*], [*What it is, mathematically*], [*`fdr.py`*]),
  [*License*],
  [Evaluate the predicate for the claim's e-value against its allocated level:
   $"Discover"(e, t, D) = "true"$. This *is* belief. Nothing else confers it.],
  [`process_test`\ `resolve_test`],
  [*FDR / $q$*],
  [Not a separate check. The level $alpha_t$ used to license *is* the FDR-controlling allocation of
   #ref(<eq:alloc>); by the theorem the guarantee $"FDR" <= q$ falls out of the very comparison used
   to believe. Licensing and error control are the same $alpha_t$.],
  [`FDRLedger`\ (`n_discoveries`)],
  [*Defeat*],
  [Set the discovery's `retracted` flag, i.e. $D arrow.l D - 1$. Because *every* future level
   $alpha_(t') = q gamma_(t') (D+1)$ reads $D$, one decrement re-prices every subsequent bar.
   Direction: $D arrow.b => alpha arrow.b => 1\/alpha arrow.t$ — the bar *rises*. Defeat is not a
   second engine; it edits the one shared counter that licensing reads.],
  [`retract_tests`],
  [*Drift*],
  [Supply a fresh e-value for the claim (its data content-address moved) and re-evaluate the
   identical predicate. Same rule, new input.],
  [drift daemon\ → `resolve_test`],
  [*Pre-register*],
  [Lock $alpha_t$ at commit time *before* $e$ exists, via #ref(<eq:alloc>) evaluated at registration;
   later fill $e$ against the *frozen* level. This forbids moving the bar after seeing the data — the
   one way the single-test guarantee of #ref(<sec:evalue>) could otherwise be gamed.],
  [`register_test`\ `resolve_test`],
)
]

#v(2pt)

*The conservation statement.* The entire believed state of the corpus is the pair
$ ( thin {e_i}, thin D thin ), $
the claims' e-values and the one live-discovery counter. Licensing reads the predicate; defeat
writes $D$; drift rewrites an $e_i$; pre-registration freezes the $t$-slot before $e_i$ exists. There
is no independent "FDR module" and no independent "argumentation engine" to keep in sync, because
there is nothing to synchronize: they are projections of the *same* comparison $e >= 1\/alpha_t$.
That absence of a synchronization problem — the thing that, in a three-subsystem design, is exactly
how a corpus ends up believing contradictory things while claiming statistical rigor — is what
"one mechanism" means, stated formally. It is provable by inspection, because the predicate is the
only place belief is ever conferred or removed.

// ======================================================================
= The theorem the project proves for itself: Refund-Validity <sec:refund>

#ref(<sec:unify>) asserted that a defeat lowers $D$. That silently assumed the #ref(<sec:stream>)
guarantee still holds after a discovery is *removed* from the ledger — and it does not hold for free.
This is the one place Polymer proves a theorem of its *own* rather than citing one. The result, its
counterexample, and the condition it rests on are established in the repository's
`refund-validity.md`, corrected by an independent adversarial review; they are reproduced here.

*Two counts, and the null-bearing distinction.* Write $G_(t-1)$ for the number of discoveries
*ever* made before step $t$ (never decremented) and $L_(t-1)$ for the *live* count before $t$
(decremented by every retraction so far); always $L_(t-1) <= G_(t-1)$, and the code allocates with
the live count. A retraction *tombstones* a discovery — its $alpha$ and $e$ are frozen, never
recomputed. Write the final live set $cal(L)$, with $R_"live" = |cal(L)|$ and
$V_"live" = |cal(L) inter cal(H)_0|$ the false ones among them, and
$q = bb(E)[V_"live" \/ (R_"live" or 1)]$. Call a retraction *null-bearing* if the accepted defeat
genuinely entails the effect-null $H_0(t)$ for the retracted claim (the effect is not there), and
*warrant-only* if it attacks the inference or interpretation while the effect may well be real.

#lemma[
  #emph[(Monotonicity.)] For integers $0 <= k <= V <= R$ with $R >= 1$,
  $ (V - k) / ((R - k) or 1) <= V / R. $
]
#proofblk[
  If $R - k >= 1$: $(V-k) R <= V (R - k) <==> k V <= k R <==> V <= R$, which holds. If $R - k = 0$
  then $k = R$, and $k <= V <= R$ forces $V = R$, so the left side is $0$.
]

Removing *equal* counts from numerator and denominator lowers the ratio — but only if the removed
items are all true nulls. That proviso is the whole theorem.

#theorem[
  #emph[(Refund-Validity.)] Suppose (1) the allocation count satisfies $D_(t-1) <= G_(t-1)$ at
  every step — true automatically for both the gross count and the code's live count $L_(t-1)$ —
  and (2) every retraction is *null-bearing*. Then, under *arbitrary dependence* among the
  e-values,
  $ q = bb(E)[ thin V_"live" \/ (R_"live" or 1) thin ] <= alpha, quad (alpha = "target_fdr"). $
]
#proofblk[
  Let $cal(D)$ be the set of *all* discoveries ever made, $R = |cal(D)|$,
  $V = |cal(D) inter cal(H)_0|$. For a true null $t$, on the event $t in cal(D)$ we have
  $R >= G_(t-1) + 1$, so
  $
  bb(1)[t in cal(D)] / (R or 1)
    &<= bb(1)[e_t >= 1\/alpha_t] / (G_(t-1) + 1)
     <= (alpha_t thin e_t) / (G_(t-1) + 1) \
    &= alpha thin gamma_t thin e_t dot (D_(t-1) + 1) / (G_(t-1) + 1)
     <= alpha thin gamma_t thin e_t,
  $
  the last step by hypothesis (1). Summing over true nulls and taking expectations, with
  $bb(E)_(H_0)[e_t] <= 1$ and $sum_t gamma_t <= 1$,
  $ bb(E)[ thin V \/ (R or 1) thin ] <= alpha sum_(t in cal(H)_0) gamma_t thin bb(E)[e_t] <= alpha. $
  Under (2), retraction removes only true-null discoveries, so $V_"live" = V - k$ and
  $R_"live" = R - k$ with $0 <= k <= V <= R$; the Lemma gives
  $V_"live" \/ (R_"live" or 1) <= V \/ (R or 1)$ pointwise, and expectations preserve it.
]

The move is to *charge each false discovery against the all-ever count* $G_(t-1)$ rather than the
shifting live denominator; the live allocation's smaller $alpha_t$ supplies exactly the ratio
$(D_(t-1)+1) \/ (G_(t-1)+1) <= 1$ where it is needed. Hypothesis (1) is essentially free;
hypothesis (2) does all the work — as the next result shows it must.

#notebox("Counterexample — why null-bearing is necessary", [
  Drop hypothesis (2) and the guarantee fails *even when every defeat is epistemically correct.*
  Take $R = 100$ discoveries: $99$ genuine effects (real, large $e_t$) and $1$ true-null false
  discovery. A single *correct* `undercut` — "all $99$ share a confounded normalization step" —
  de-licenses the $99$. The live set is now exactly the one true null, so
  $V_"live" \/ R_"live" = 1$. Made rigorous (true positives at positive density force a true-null
  discovery with probability $-> 1$), this drives $q -> 1$, far above any $alpha$. The diagnosis:
  FDR is an invariant about the *effect-size null*; defeat is an operation about *epistemic
  warrant*; the two coincide only for defeats that entail the null. #emph[You may refund the ledger
  for "the effect isn't there," never for "the effect is there but means something else."]
], rgb("#a6392f"))

*What the code does, and the integrity of the record.* The system enforces hypothesis (2)
directly: only null-bearing knockouts refund the ledger (`integrate.py` routes retractions through
`null_bearing_knockout_ids`; `NULL_BEARING_KINDS = {rebut}` in `defeat.py`). A warrant-only defeat
(`undercut` / `reinterpret` / `reclassify`) de-licenses the claim in the graph — it leaves the
grounded extension and loses `status = licensed` — but its `FDRTest` stays *live*. That is exactly
correct: *the effect is real; it simply no longer warrants claim $c$.* An earlier version tombstoned
regardless of edge kind; the adversarial review proved the unconditional theorem *false*, produced
the counterexample above, and the code was gated to the theorem's condition. A system whose product
is "believe nothing you did not earn" found, and corrected, a false-discovery leak in its own core —
the thesis demonstrated on itself.

#honest[
  Theorem 1 requires each refund to *genuinely* entail $H_0(t)$. Typing an edge `rebut` (or flagging
  `entails_null`) is only an *operational proxy* for that semantic entailment; that the proxy is
  faithful — that the labels the ledger consumes really track null-entailment — is a
  calibration-and-audit obligation, listed open, not a proved one. The theorem is sound; one of its
  hypotheses is discharged by an *assumption* about the defeat vocabulary, not by a proof. Naming
  that seam is itself part of the result.
]

// ======================================================================
= What the mathematics does — and does not — justify <sec:limits>

A derivation is only as honest as its stated scope. Three boundaries, each already named in
Polymer's foundations, and each now located precisely in the math above.

/ FDR $<= q$ is a statement about the discovery #emph[process], not about reality.: The theorem
  bounds the fraction of licensed claims that are false *relative to their specified nulls*. It says
  nothing about whether a null was the *right* null, or whether the measured quantity corresponds to
  the world. This is the residualist identity restated as a theorem's fine print: the engine
  certifies *warrant* — an audited, bounded right to believe — never *truth*. A competitor promising
  to verify "the finding" is claiming something no FDR bound delivers.

/ The whole guarantee rests on $bb(E)_(H_0)[e] <= 1$ actually holding.: Every result in
  #ref(<sec:evalue>) and #ref(<sec:stream>) is a consequence of e-value *validity*. If the null or
  the betting construction is misspecified — a mismodeled apparatus, a bet tuned after glancing at
  the data — the number is not a valid e-value and the guarantee is void. The system's three
  defenses are exactly aimed here: *pre-registration* locks the bet before the data (closing the
  optional-stopping and HARKing leak the single-test bound assumes away), *oracle strength caps*
  bound $e$ by the credibility of the measuring apparatus, and the *air gap* bars the claim's
  proposer from being its verifier so the bet is not constructed by an interested party.

/ Independence under $H_0$ is required to multiply legs — and code independence does not supply it.:
  The composition lemma needs *statistical* independence under the null. The air gap secures
  *implementation* independence (distinct authors, distinct bytecode). These are not the same thing:
  two implementations that inherit the same operationalization, ontology, and measurement priors are
  statistically dependent under $H_0$ even with disjoint code, so their product over-counts. Polymer
  models this with the common-cause DAG (a license requires low shared-cause overlap, which *gates
  whether the product is formed at all*) and treats "your two legs share premise $Z$" as a
  first-class, licensable defeater in the argument layer. But *certifying* the breadth of conceptual
  independence, rather than inferring it from code diversity, is an acknowledged open problem — the
  most exposed flank of the whole construction, and the one place the pitch should concede rather than
  bluff.

// ======================================================================
= The one theorem to carry

#notebox("In one breath", [
  A claim's evidence is an *e-value*: money won betting against "nothing is going on," and you cannot
  expect to win betting against the truth. Believe a claim exactly when it clears the bar
  $e >= 1\/alpha_t$; Markov makes that a level-$alpha_t$ test. The bar's height,
  $alpha_t = q gamma_t (D+1)$, is set by one shared counter $D$ of live discoveries and one dial $q$;
  because the discounts $gamma_t$ sum to one and e-values are valid, the realized false-discovery rate
  stays $<= q$ *under arbitrary dependence between claims* — which is the only reason the argument
  graph can live inside the statistics. Licensing reads that bar, defeat lowers $D$ and raises the
  bar, drift refreshes the evidence, pre-registration freezes the bar before the data. One comparison,
  one counter, a free guarantee. It certifies warrant, never truth — and the single hypothesis it
  cannot yet certify on its own, statistical independence of "independent" legs, it names out loud.
], rgb("#2f5fa6"))

// ======================================================================
#v(6pt)
#line(length: 100%, stroke: 0.4pt + luma(200))
#text(size: 8.5pt)[
  *Key references* (bibliographic details should be confirmed against the primary sources before
  external distribution).
  #set enum(numbering: "[1]", spacing: 0.5em)
  + Z. Xu and A. Ramdas. Online multiple hypothesis testing with e-values (the e-LOND procedure),
    2024. — the stream-level FDR theorem; cited by name in `grammar/src/polymer_grammar/fdr.py`.
  + A. Ramdas, P. Grünwald, V. Vovk, G. Shafer. Game-theoretic statistics and safe anytime-valid
    inference. #emph[Statistical Science], 2023. — e-values, e-processes, Ville's inequality.
  + V. Vovk and R. Wang. E-values: calibration, combination and applications. #emph[Annals of
    Statistics], 2021. — e-value validity and combination.
  + R. Waudby-Smith and A. Ramdas. Estimating means of bounded random variables by betting.
    #emph[J. R. Stat. Soc. B], 2024. — the betting e-values the evaluator emits.
  + Y. Benjamini and Y. Hochberg. Controlling the false discovery rate. #emph[J. R. Stat. Soc. B],
    1995. — the classical procedure, for contrast (independence / PRDS assumption).
  + J. Ville. #emph[Étude critique de la notion de collectif], 1939. — Ville's inequality.
  + L. Euler, 1734. Solution of the Basel problem, $sum_(n>=1) n^(-2) = pi^2\/6$.

  #v(3pt)
  Code references are to this repository at the state described in `ARCHITECTURE_CURRENT.md`;
  line numbers refer to `grammar/src/polymer_grammar/fdr.py`.
]
