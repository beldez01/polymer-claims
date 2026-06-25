# Polymer Claims — The Epistemology

*Why the verification is not circular, and the honest limit of that claim.*

**Status:** Conceptual anchor. Read this when someone asks "isn't this just
coherentism / isn't the verification tautological?" — or when you need to
explain *why* the machine is built the way it is.

---

## 1. It is a Quinean Web of Belief — with a foundationalist anchor

Quine's confirmation holism: no claim is verified in isolation; beliefs form a
**web** that faces experience together. Peripheral beliefs touch data directly;
core beliefs are insulated and revised only under pressure. Polymer is a near-exact
mechanization of this — and deliberately a **hybrid**, which is the whole point.

| Quine's web | The mechanism in Polymer |
|---|---|
| The web of belief itself | the **defeat + equivalence graph** (grammar L3) |
| Revising the web under pressure | **AGM belief revision** (grammar L4) — AGM *is* the formal theory of revising a Quinean web |
| Global consistency of the web | the **sheaf-consistency gauge** (`H⁰` = consistent worlds, `H¹` = contradiction cycles) |
| The periphery that touches experience | the **L0 empirical leaf + recomputation against real, content-addressed data** |

**Why the hybrid matters.** Pure coherentism — a web judged only by internal
consistency — is *exactly* the tautology trap: you can have a perfectly
self-consistent web of falsehoods. Pure foundationalism ignores the web's
structure. Polymer does both: the web (L3 / L4 / sheaf) supplies global
consistency, and the **L0 anchor + recomputation** forces the web to actually
*touch data somewhere*. The anchor is what stops the web from being free-floating
and tautological.

---

## 2. What "non-tautological verification" means

A verification is **tautological** when the claim *could not have failed it*. A
test the claim passes by construction teaches nothing. So the entire question
"is this circular?" reduces to one demand:

> **The claim must have been able to fail the test, and the two confirmations
> must be able to fail it for *different reasons*.**

This splits into exactly two failure modes, each with a named guard.

### Failure mode A — the test is empty (no severity)

If the criterion is one the claim clears automatically, agreement is worthless.

**Guard: the e-value is the currency.** An e-value against the criterion-null is,
by construction, a measure of how surprising the result would be *if the claim
were false*. A tautological test yields an e-value of ≈ 1 — **no alpha-wealth,
no license.** The math refuses to pay out for a test the claim could not fail.
This is Mayo's *severity* made into the unit of account: standing is earned in
proportion to how badly the claim risked failing and didn't.

### Failure mode B — the two legs are not independent (correlated tautology)

If both implementations share the assumption doing the work, their agreement is
one claim wearing two hats — they agree *because they are the same thing*. This
is direct replication masquerading as independent confirmation, and it is the
engine of the replication crisis (correlated error).

**Guard: the common-cause DAG.** Shared inputs, methods, references, libraries,
and statistical conventions are modeled as edges; a license requires **low
shared-cause overlap**. Independence stops being an asserted premise and becomes
a *measured, evidenced* property (Reichenbach screening-off). What we want is
**conceptual replication** (different algorithm, different assumptions, *fails for
different reasons* — Wimsatt robustness), not **direct replication** (same method
twice, which tests only reproducibility).

---

## 3. The honest limit — Duhem–Quine, and why no system "solves" this

Quine's sharpest claim: *"any statement can be held true come what may, if we
make drastic enough adjustments elsewhere in the system."* The web can always
protect any belief by absorbing the shock somewhere else — adjusting an auxiliary
hypothesis, blaming the apparatus, redefining a term. There is **no purely formal
guarantee** against ad hoc protection, because what counts as "independent" and
"severe" itself rests on background assumptions that are *also part of the web*.

This is the **Duhem–Quine problem**. It is unsolved in general. Polymer does not
solve it. Claiming otherwise would be the dishonesty the project exists to refuse.

**So the honest statement of what Polymer does is not "we guarantee
non-tautological verification." It is:**

1. **It measures** the two things that make verification non-empty — *severity*
   (the e-value) and *independence* (common-cause overlap) — instead of assuming
   them.
2. **It forces a data anchor** (L0 + recomputation), so the web cannot drift into
   pure coherentism. The web must touch experience somewhere.
3. **It makes the residual assumptions explicit and attackable.** The RED-TEAM
   daemon exists to try to make claims fail, and "your test is circular" or "your
   two legs share assumption Z" is itself a **first-class, licensable defeater** —
   not a hidden flaw.

---

## 4. The improvement on Quine: silent protection becomes auditable

Quine's point is that the web can always defend a belief by adjusting itself
*silently*. Polymer's contribution is to make every such adjustment a **visible
edge in the graph carrying an evidence cost**:

- An attack **fires** only once the attacker clears its own evidence bar (an
  unfounded claim cannot undecide a hard-won license).
- **Demotion costs more evidence than promotion** (AGM: contraction is harder
  than expansion). You can still protect a claim — but not for free.
- The protection happens **in the open**, as a recorded operation on the graph,
  never in the dark.

You can still hold a belief "come what may." You just cannot do it *for free or
invisibly*. The web's self-defense becomes auditable — which is the most you can
honestly ask of any empirical system.

---

## 5. The one-paragraph version

Polymer is a computational Web of Belief with a foundationalist anchor. The
coherentist machinery (defeat graph, AGM revision, sheaf consistency) keeps the
web globally honest; the L0 empirical leaf and mandatory recomputation keep it
tethered to data so it cannot become a self-consistent fiction. "Is this
verification circular?" is turned from a philosophical worry into a **measured
quantity** — severity (e-value) × independence (common-cause overlap) — and into
an **attackable claim** the red-team and defeat graph can press. The Duhem–Quine
problem is not solved, because it cannot be; instead, the one move it permits —
protecting a belief by adjusting the web — is made costly, evidenced, and visible
rather than free and silent. That auditability is the honest substitute for a
guarantee no empirical system can give.

---

## 6. Why category theory — and only where it earns its place

Category theory is **not** the foundation of the trust kernel. The kernel — the
part that decides whether a claim earns standing — is statistical (e-values,
online-FDR) and argumentation-theoretic (grounded Dung/ASPIC+). Category theory
earns its place in exactly **two** spots, both in the *consistency-and-integration*
layer that sits on top of the kernel, plus one standing warning.

**The general fit.** Category theory is the mathematics of *relationships and
structure-preserving composition* — the right tool when the objects matter less
than the morphisms between them and those morphisms must compose coherently.
Polymer's primary data is exactly that: not claims-in-isolation but a **web of
relationships** (equivalence, defeat, derivation) operated on by
**structure-preserving transformations of whole corpora** (`run_cycle: Corpus →
Corpus`, ingest, drift-revision). When the subject *is* a web of morphisms,
category theory describes the shape that set theory and ordinary statistics
cannot — and its **universal properties** hand you "the canonical correct
operation," with provenance witnesses built in.

### Place 1 — sheaves: the only mature math of "locally fine, globally broken"

A sheaf is the precise theory of *local data glued into a global whole, plus the
obstruction to gluing.* That is structurally a claims corpus: each claim's
quantitative content is a **stalk**; each equivalence edge ("must agree") and
defeat edge ("antagonistic") is a **restriction map**; "does the corpus admit a
globally consistent picture?" is exactly the question **sheaf cohomology** answers:

- **H⁰** = global sections = the space of globally consistent worlds the corpus admits.
- **H¹** = the obstruction class — nonzero precisely when *every region is locally
  consistent but no global reconciliation exists.*

The H¹ case is the payoff: a contradiction with **no local witness**. Picture
A ≈ B, B ≈ C, C ≈ A with values drifting 1 → 1 → 1 → 2 around the loop — every
edge looks fine, but the cycle does not close (holonomy/frustration). Pairwise
checking is blind to it by construction; cohomology detects it *because the
structure forces the obstruction to appear*. The **sheaf Laplacian's spectrum**
then gives a continuous "global inconsistency energy" that falls as independent
recomputations bring claims into harmony — "grows toward truth" as a number that
goes down (Hansen & Ghrist discourse sheaves; Robinson consistency radius). Built
in the repo: `export-consistency`, with H⁰/H¹/Robinson energy on every
`TopologyExport`.

### Place 2 — functorial data migration: provenance *as* mathematics

The deepest results on combining datasets without corrupting structure are
categorical. "Integrate dataset X under apparatus Y" is a **functor** — preserving
relationships by definition, so the migration is provably coherent. "Merge two
sources" is a **colimit (pushout)**, and the **universal property of the pushout
*is* the provenance**: the colimit is the canonical most-general merge respecting
both sources and their shared part, and its universal-property witnesses record
*exactly how each source maps in*. Provenance is not bolted on — it is the
mathematical content of the merge. For a system whose thesis is content-addressing
+ reproducibility + provenance, that means "merge knowledge and know precisely
where each piece came from" is guaranteed by construction (CQL/Conexus,
AlgebraicJulia/Catlab — research-grade, hence not yet wired).

A smaller third hook: a **recompute-and-revise loop is a lens** (a categorical
optic). The drift daemon "views" world-state and "puts" the update back into the
license — that is a lens, exactly.

### The warning (where category theory is the wrong tool)

- **The kernel stays statistical.** Earned standing comes from e-values and FDR;
  category theory never enters the gate. The categorical layer is the
  *truth-maintenance backbone*, not the licensing decision.
- **Do not sheaf-ify prose.** Sheaf Laplacians are linear algebra over
  vector-space stalks — meaningful only for claims with comparable quantitative
  content (current implementation: Quantity-leaf claims only). Over text you would
  be measuring encoding artifacts.
- **Operads / institutions / DisCoPy are inspiration, not infrastructure** unless
  there are genuinely multiple incompatible *logics* or composing open dynamical
  processes. Reaching for them without that is cargo-cult.

Using category theory *only where its universal properties do real work* — and
fencing it off elsewhere — is itself the evidence that it is the right tool there.

---

## 7. Why e-values and online-FDR are the correct statistical underpinning

The evidence atom is an **e-value**, and the corpus-level error control is
**online-FDR via e-LOND**. This is not a stylistic choice; it is forced by what
the corpus *is*.

### Why an e-value, not a p-value

An e-value is a **betting score against the null**: a non-negative random variable
with `E[e] ≤ 1` under the null (a test supermartingale's terminal capital). "How
many times would you have multiplied your stake betting against the null?" Four
properties make it the right atom here, and a p-value has none of them:

1. **It multiplies across independent evidence.** Two independent e-values combine
   by `e = e₁ · e₂` and the product is still a valid e-value. "Two independent
   implementations beat the criterion" is therefore *natively* an e-value — you
   just multiply. P-values have no valid multiplication.
2. **It is anytime-valid.** By Ville's inequality on the capital process, you may
   accrue evidence and peek at any time without an alpha-spending penalty — exactly
   what a live, continuously-recomputed corpus needs.
3. **It is valid from boundedness alone** (no Gaussianity, variance-adaptive,
   finite at zero variance) — essential for messy biological data.
4. **It is a severity measure and runs both directions.** `e ≥ 1/α` is the
   discovery rule (Mayo severity as currency); a successful defeat is a *downward*
   e-value update. Licensing and defeat become one operation on one quantity —
   impossible with p-values.

### Why online-FDR via e-LOND, not Benjamini–Hochberg

The corpus's own **defeat and equivalence edges are dependence structure.** That
breaks classical FDR:

- **Benjamini–Hochberg** requires independence or positive dependence (PRDS) —
  violated by an arbitrary defeat graph → unsound.
- **Benjamini–Yekutieli** is dependence-robust but pays an ≈ `ln(m)` penalty →
  a growing corpus becomes unable to license anything.
- **e-LOND** (Xu & Ramdas 2024) controls FDR ≤ target under **arbitrary
  dependence with no correction factor**, because the proof rides only on
  `E[e] ≤ 1` and the discount weights summing to 1 — never on a dependence
  assumption. This is the single property that lets a dependence-laden graph stay
  sound, and it is why e-values are load-bearing rather than ornamental.

It is also **online**: claims arrive over time, and α is allocated as a wealth
process without knowing the corpus's final size — each discovery earns budget for
future tests, each defeat refunds it.

### How they are actually calculated (the real code)

**The e-value, from data** (`src/polymer_claims/evidence.py`, impure, umbrella-side).
`betting_evalue` is the Waudby-Smith & Ramdas (JRSS-B 2024) betting /
empirical-Bernstein e-value for the one-sided composite null
`H₀: (μ_B − μ_A) ≤ threshold` over per-sample region-mean betas in `[0,1]`. It runs
a **betting capital process**

```
e = ∏_i (1 + λ_i · W_i),   W_i = (paired diff − θ₀)
```

where `λ_i` is the GRAPA plug-in betting fraction computed from **past-only**
points (predictable), capped to keep every factor positive (Eq. 25). Valid by
Ville's inequality **from boundedness alone**. It is seed-averaged over a fixed
seed set (a convex combination preserves `E[e] ≤ 1`) so the result is
**deterministic** given the data. `count_enrichment_evalue` is the one-sample
sibling for Bernoulli DMP-indicators (`H₀: per-probe DMP-rate ≤ p₀`).

**Combining the two legs** (`src/polymer_claims/replication.py`). Within a cohort,
the two implementations (`RegionMeanDiff`, `RegionLmCoef`) must **agree within
tolerance** or no e-value is issued (the air gap). Across cohorts the e-values
**multiply** — `evidence[cid] = evidence[cid] * e2` — but **only when
`cohorts_error_independent(...) is not False`** (low shared-cause overlap, §E). If
overlap is high, the product is withheld and the single-leg e-value stands. So
*independence gates whether you are allowed to multiply at all.*

**The FDR decision, pure** (`grammar/src/polymer_grammar/fdr.py`). e-LOND assigns
test *t* the level

```
α_t = target_fdr · γ_t · (D_{t-1} + 1),   γ_j = (6/π²)/j²   (Σ γ = 1)
```

where `D_{t-1}` is the live discovery count so far, and the test is a
**DISCOVERY iff `e_t ≥ 1/α_t`**. `register_test` locks `α_t` *before* the e-value
exists (pre-registration — kills post-hoc threshold shopping); `resolve_test`
later fills the e-value and decides against the locked α. `retract_tests`
tombstones a defeated discovery so it drops out of `D` — the alpha refund. The
grammar computes the allocation and decision; **the e-values are supplied from the
umbrella** (purity invariant: the math is a pure transform over passed-in
evidence).

**In one line:** the e-value is a deterministic, boundedness-only betting score
computed from the data umbrella-side; independence gates whether two legs'
e-values may multiply; and a pure e-LOND ledger turns the resulting e-value into a
discovery decision that stays FDR-sound under the graph's arbitrary dependence.

---

## 8. The de Bruijn kernel — concentrate trust, distrust everything else

The trust architecture is borrowed from formal methods. Nicolaas de Bruijn's
*Automath* (late 1960s) gave rise to the **de Bruijn criterion**: a proof system
is trustworthy if its proofs can be checked by a program **small and simple enough
to audit by hand.** The move is a separation of concerns about trust:

- **Generation** can be arbitrarily complex, heuristic, AI-driven — and **untrusted.**
- **Checking** must be tiny, dumb, and **trusted.**

All trust concentrates in the checker (the *kernel*); everything feeding it is
suspect by default. The decisive principle: **trust scales with kernel
minimality, not generator quality.** HOL Light trusts ≈ 500 lines; Lean ≈ 10k;
Metamath Zero a deliberately minuscule, self-verified core. Everything else —
tactics, decision procedures, the whole library — is untrusted scaffolding that
must reduce to primitive inferences the kernel re-checks. This is *why
AlphaProof's hallucinations do not matter*: if the emitted proof checks against
the kernel it is valid, if not it is rejected, and the generator's flakiness is
irrelevant to the output's trustworthiness.

**The Polymer reframe.** Name an explicit, tiny **claim kernel** that asks exactly
one question:

> *Given a fully-pinned computation (content-addressed code + data + environment),
> does re-running it produce the output that licensed the claim?*

Then make it law: AI proposers, the LLM generation adapter, human analysts, and
the apparatus adapters are **all untrusted scaffolding** — they propose claims,
they never confer standing. **Nothing earns standing except by passing the
kernel.** The air-gap + content-addressing exist precisely to make the kernel's
question well-defined: a pinned computation re-runs deterministically and
checkably. (Nearest locus in the code: the grammar's air-gapped evaluator; the
discipline is to keep that path minimal.) This is the formal grounding for the
positioning rule **agents propose, recomputation verifies.**

### The caveat that forces independence

The formal-methods model does **not** transfer in full. A valid deduction from
sound axioms is true; an empirical recomputation has a gap the kernel cannot see:

> A reproducible build of **fabricated** (or batch-confounded, or artifactual)
> data is still perfectly reproducible.

The kernel verifies *"the result follows from this pinned computation"* — never
*"the data is real."* So the kernel alone is insufficient, and that is exactly why
independence (§2, failure mode B) is load-bearing. The division of labor:

| Layer | Catches | Guarantee |
|---|---|---|
| **de Bruijn kernel** | computation errors, environment rot, "the code does not actually produce this number" | the result faithfully follows from the pinned computation |
| **Independence (§2.B)** | shared data, batch effects, fabrication, setup artifacts | two implementations that *fail for different reasons* both clear the bar |

The kernel is the reproducibility floor; independence is what catches false data.
Neither alone suffices — which is why both sit in the gate.

### The invariant

**The kernel stays small.** Every rigor upgrade — e-values, the defeat graph, the
sheaf gauge, the standards skin — is scaffolding *around* the minimal
recomputation kernel, never inside it. The moment the kernel grows, trust dilutes;
new power is added as untrusted-but-kernel-checkable machinery, the way a proof
assistant adds tactics without touching its core.

---

## See also

- `docs/superpowers/foundations/MAP.md` — the simple input/output map of the machine.
- `docs/polymer-claims-overview.md` — the full high-level overview.
- `docs/superpowers/2026-06-12-phase-2-north-star.md` — §2(A) the kernel reframe,
  §2(B) the e-value unification, §2(E) the rigorous definition of "independent".
