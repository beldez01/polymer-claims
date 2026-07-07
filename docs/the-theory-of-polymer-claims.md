# The Theory of Polymer Claims

> **Status:** Foundational statement of the company's thesis. Created 2026-07-07.
> **Premise:** Every company is a theory — a falsifiable bet on a truth about the world that few
> agree with, which the company is uniquely built to exploit if it holds (Thiel's "secret"). This
> document states Polymer's theory precisely, and then — because Polymer is a machine for licensing
> theories — states it *as a Polymer claim* and holds it to its own gate.
> **Synthesizes:** `foundations/residualism.md`, `foundations/compute-boundary.md`,
> `foundations/epistemology.md`, `pitch-competitive-landscape-and-loop.md`.

---

## The theory, in one paragraph

**The defining scarcity of the AI age is not intelligence but *warrant*.** As AI drives the marginal
cost of generating a plausible scientific claim to zero, the binding constraint on knowledge shifts
from *producing* claims to *earning the right to believe them* — and warrant cannot be produced by
the same intelligence that produces the claims, because a generator cannot license its own output.
Warrant is therefore a distinct, measurable, attestable, defeasible quantity that must be produced by
a **protocol structurally separated from the generator**: a schema for what a claim is, a calculus
for what it earned, and a ledger that proves it. That protocol sits *above* bring-your-own-compute and
never becomes a compute service. Whoever establishes it as the default becomes the trust layer of the
AI-science economy — and the value accrues to the schema, the calculus, and the ledger, never to the
FLOPs. **Polymer Claims is that protocol. The company is the bet that warrant, not generation, is
where knowledge gets made and where the value settles.**

---

## The secret (the contrarian core)

> Almost everyone building AI-for-science is racing to build a **better generator** — a smarter
> agent that proposes more, faster. Polymer's bet is that the generator is the commoditizing part,
> and the scarce, defensible thing is the **un-gameable, portable standard for what a
> machine-generated claim earned the right to be believed.**

The field is already conceding the setup — "verification is the central unresolved problem for
autonomous research systems" — while building verification the weak way (checking a claim against its
*cited sources*: EviBound, FutureHouse). Polymer's contrarian move is to verify against *reality*
(did the computation demonstrably run; do independent legs agree under error control) and to make the
result a signed, portable receipt. Citation-checking catches misquotes; it cannot catch a plausible,
well-cited, *wrong* result — which is exactly the failure mode the AI-scientist evaluations report.

---

## The theory stated as a Polymer claim

Polymer's integrity test is whether it will submit its own thesis to its own machine. Here is the
company theory expressed in the claim grammar — pattern, subject, causal roles, empirical leaves,
strength vector, and named defeaters — exactly as the engine would hold any scientific claim.

| Field | The company theory as a claim |
|---|---|
| **pattern** | `adjusted_effect` — a directional causal-forecast claim. |
| **subject** | The market for machine-generated scientific knowledge, 2026→. |
| **roles — cause** | The marginal cost of *generating* a plausible scientific claim collapses toward zero (AI). |
| **roles — effect** | The binding constraint, and the economic value, migrate from *generation* to *warrant* — the attested, independence-measured licensing layer. |
| **roles — confounders (must adjust for)** | (a) generator reliability improving fast enough to make cheap self-checking sufficient; (b) incumbents (ELN/LIMS, journals, NIH) bundling "good-enough" provenance into existing workflows; (c) the market tolerating un-warranted machine science for the sake of velocity. |
| **leaves (empirical anchors)** | Observed, not asserted: AI-scientist evaluations report ~half of experiments failing and *hallucinated numerical results* [Sakana eval]; independent third parties name verification/attestation as the scarce institutional layer [AI-Augmented Science]; the nearest neighbors stop short — Knows is explicitly "an author assertion, not a certification"; EviBound verifies by citation-consistency with no ledger. |
| **strength (6-axis, no hidden scalar)** | **world_contact:** high (rests on observed failure modes, not a projection). **severity:** high (the theory is sharply falsifiable — see defeaters). **evidence_against_null:** moderate–high (multiple independent sources converge on "warrant is the bottleneck"). **magnitude:** uncertain (the *direction* is well-supported; the *timing and size* of the value migration are not). **certainty:** deliberately not maxed — this is a licensed conjecture, not a proof. **explanatory_virtue:** high (one mechanism explains the AI-science reproducibility crisis, the commoditization of generators, and the funded "trust is the moat" theses at once). |
| **independence tier** | REPRODUCED-analogue: the thesis is corroborated by sources that fail for *different reasons* (a Sakana evaluation, an institutional-economics preprint, two competitor design docs) — conceptual, not merely direct, agreement. |
| **status** | **LICENSED as a conjecture** — believed defeasibly, with the paper trail below for what would overturn it. Never LICENSED-simpliciter. |

The point of the exercise is not cuteness. A company whose product is "believe nothing you didn't
earn" must be willing to run itself through its own gate — including publishing its own defeaters.
That willingness *is* the product demonstrated on itself.

---

## The defeaters (what would prove the theory wrong)

Stated first-class, the way the engine demands. If any fires and survives, the thesis is defeated.

- **D1 — Reliability kills the need.** If AI generators become reliable enough that cheap
  citation-checking or self-consistency suffices, no one needs an independent execution+attestation
  gate. *Warrant stops being scarce because generation stops being untrustworthy.*
- **D2 — No buyer for the receipt.** If the market acts on un-warranted machine science anyway
  (velocity beats trust; nobody actually demands the certificate), the trust layer has no customer.
- **D3 — The compute-gravity wins.** If you cannot *witness* a computation without *hosting* it, the
  platform is dragged into a commoditized compute utility after all (the V1→Galaxy failure).
  `foundations/compute-boundary.md` is the standing defense; the day a hosted cluster appears "for
  convenience," this defeater has fired.
- **D4 — Warrant is hollow.** If *conceptual* independence proves impossible even to *measure* (the
  Sellarsian back-door Given), then agreement certifies only a shared frame and the warrant means
  less than it claims. `foundations/residualism.md` §7 lists this as an open problem, not a solved one.
  **Empirical update (2026-07-07):** an audit of the shipped air-gap pairs found all three were
  *algebraic tautologies* (two encodings of the same estimator) — the exact hollow warrant this
  defeater names, live in the trust core. Two are now fixed and *measured*: the n-DMP pair buys genuine
  independence (two methods flag genuinely different probes — Jaccard 0.73), the region-Δβ pair does not
  (two scalar-location estimators nearly coincide, 0.09% apart). The refinement this forced is
  load-bearing: **REPRODUCED is epistemically meaningful for set/count/classification claims but
  structurally thin for scalar point-estimate claims** — you cannot manufacture independence for a
  scalar by computing it two ways, so scalar-effect claims must earn genuine independence from
  **REPLICATED** (cross-cohort, different data), not a second within-cohort leg. D4 is thus now
  *measured, not asserted*: the defensible pitch is "our independence guarantee is claim-shape-aware,
  and we measure how much each buys" — stronger than the old blanket "two implementations agree." Still
  the most exposed flank (correlated *bias* with no truth anchor stays invisible), but now instrumented
  rather than cosmetic. Detail: `docs/superpowers/plans/2026-07-07-adapter-independence-hardening-plan.md` §3.7.
- **D5 — Cold-start.** If a standard never reaches the network effect — agents don't author the IR,
  consumers don't ask for the ledger — the protocol dies of adoption, not of being wrong. (Mitigant:
  agents author the IR automatically; adoption rides the AI-science wave rather than asking humans to
  change how they write.)

A theory with no stated defeaters is not a theory; it is a hope. These are the sentences on which the
whole bet turns.

---

## Why the company — and not just an idea — captures it

If the theory holds, the value settles into three assets that are hard to own and harder to copy,
and Polymer holds all three as an integrated, shipped standard:

1. **The claim IR** — a typed, executable intermediate representation of a scientific claim (sum-typed
   leaves, derived adjustment sets, a 6-axis strength vector). *The schema everyone targets.*
2. **The licensing calculus** — betting e-values + online-FDR (e-LOND) + the air-gap + the
   value-based defeat graph. *The un-gameable rule for what a claim earned.*
3. **The attestation ledger** — in-toto/SLSA statements, DSSE signatures, an RFC-6962 transparency
   log. *The portable proof a third party can verify without trusting us.*

The **compute-boundary** discipline is what keeps these from decaying into a commoditized compute
utility: Polymer specifies, orchestrates, witnesses, and certifies computation that runs *elsewhere*;
it never hosts the compute. A referee needs no stadium. Open the standard and the reference
implementation to win the network; monetize the registry and the hosted trust — Git→GitHub,
Docker→Docker Hub, Sigstore→a trust service.

---

## The theory has two floors, and the deeper one is epistemological

The market theory ("warrant is the bottleneck") rests on a theory of *knowledge*, which is the real
foundation and the project's philosophical identity: **logical residualism**
(`foundations/residualism.md`).

- Truth is **not** the deliverable. The map provably never equals the territory (residualism's
  positive floor); a machine that claims to certify truth is lying. What a mature knowledge system
  delivers is **instrumented warrant** — measured severity (the e-value) × measured independence
  (common-cause overlap) × attested existence (the log) — plus honest instrumentation of its own
  incompleteness (the PENDING graveyard, the `duhem_underdetermined` verdict).
- This is why the company can be radically honest about its limits (D4, the conceptual-independence
  problem) *without weakening the pitch*: not-claiming-truth is the thesis, not a concession. The
  competitors who promise to verify "the finding" are making the claim residualism says is
  impossible. Polymer promises something smaller, achievable, and un-fakeable: **a warrant you can
  audit, bounded by the evidence, with its own defeaters on the table.**

So: the *market* theory is that warrant is the scarce good of the AI age. The *epistemological* theory
is that warrant — not truth — is the most any system can honestly produce, and that it must be
*instrumented*. The company is the first place those two theories are compiled into one running
machine.

---

## The one-sentence version

**Polymer Claims is the wager that the defining scarcity of the AI age is not intelligence but
warrant — a measurable, attestable, defeasible quantity that must be produced by a protocol
structurally separated from the generator — and that the company that owns the schema, the licensing
calculus, and the ledger for warrant becomes the trust layer of machine science.**

*Corollary, and the integrity proof: a company that is a theory of warrant must carry its own warrant
— which is why this theory is written as a claim, with its defeaters published.*
