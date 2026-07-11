# Adapter-Independence Hardening — testing for false priors

**Date:** 2026-06-29
**Status:** Exploratory / horizon. Recommendation set, not a plan. Companion to
[`2026-06-29-claim-type-menu-design.md`](2026-06-29-claim-type-menu-design.md).

This note grew out of a peripheral-vision (`/neg`) read of the claim-type menu. The menu's
air-gap gate scores independence **organizationally** (different owner, different code lineage —
T1/T2/T3). This document is about the thing that score cannot see.

---

## The problem: organizational independence ≠ epistemic independence

Two adapters can be organizationally independent (different owner, different runtime, different
code lineage) yet **statistically correlated** — same training corpora, same reference databases,
same modeling assumptions. When that's true, their agreement is **not two witnesses; it is closer
to one witness counted twice.** The air-gap protects against a *spatial* danger (one party rigging
both legs). The false-prior danger is *epistemic*, and it walks straight across the gap, carried
in shared assumptions.

### The bias/variance split (the sharp edge)

This is the distinction that organizes every recommendation below:

- **Correlated *variance*** — the two tools wobble together on noise. **Detectable without ground
  truth**, by perturbing shared inputs and watching whether the legs move together.
- **Correlated *bias*** — the two tools are wrong in the *same direction by the same amount*.
  **Invisible to agreement by construction**: they agree *because* they are both wrong. The only
  instrument that catches it is an external truth anchor. This is the worst case, and it is why
  the verification story cannot be purely self-referential.

> AlphaMissense and ESM1v both learned the world from overlapping evolutionary-sequence data.
> DESeq2 and edgeR both assume counts behave roughly the same way (a negative-binomial-ish prior).
> Their agreement is informative only to the extent their *errors* are independent.

---

## Recommendation set

Each recommendation names the existing seam it plugs into, so none of this is greenfield.

### R1 — Provenance lineage in the oracle dossier *(the cheap prior)*

Extend `AdapterCredential` — today `(identity, owner, implementation_hash, version, trusted)` —
with a **provenance lineage**: declared training corpora, reference databases, and assumption
class. Compute a **prior-overlap coefficient** between the two legs; high overlap (e.g. two
variant-effect models both trained on gnomAD/ClinVar) sets an independence *prior* well below
T1's nominal "full strength."

- Static, declaration-based → gameable and incomplete, but free, and it upgrades the binary tier
  to a graded coefficient.
- **Plugs into:** the oracle dossier that already records the independence tier.

### R2 — The decorrelation battery *(the actual empirical test for false priors)*

You cannot observe shared priors directly, but you can measure **correlated error** given ground
truth:

1. Assemble a **calibration battery** per claim type where the answer is known — ClinVar
   high-confidence pathogenic/benign for variant effect; spike-in / simulated RNA-seq with known
   fold-changes; null-permuted data for false-positive behaviour.
2. Run *both* legs across the battery. Record each leg's **signed error vector** (residual per
   item), not its output.
3. Compute the **error correlation ρ** between the legs; for categoricals, the **double-fault
   rate** (fraction both get wrong the same way). These are the standard ensemble-diversity
   measures (Kuncheva & Whitaker: Q-statistic, disagreement, double-fault) — established,
   defensible math.

**The strength cap becomes a function of measured ρ, not of the tier label.** Two unbiased
witnesses with error correlation ρ provide effective independent-witness count

```
N_eff = 2 / (1 + ρ)
```

— ρ≈0 → two real witnesses (full credit); ρ→1 → one witness (their agreement is nearly
worthless). The organizational tier (T1/T2) is the **prior** on ρ; the battery gives the
**posterior**.

- **Honest boundary:** the battery catches correlated **bias** *only where ground truth exists*.
  For the vast majority of real claims with no truth anchor, input-perturbation catches correlated
  *variance* but correlated *bias stays invisible* — which is exactly why R1 (provenance prior) and
  R4 (heterodox witness) exist to bound what R2 cannot see.
- **Plugs into:** the `calibrate` / `certify` warrant-tiered q-calibration ledger already shipped —
  this is one more column in that ledger.

### R3 — Adversarial shared-failure probing *(active; no waiting for benchmarks)*

Don't only measure on a fixed battery — *hunt* for inputs where the two legs likely share a blind
spot: out-of-distribution probes near the edge of their common training support, or inputs
engineered to violate a *shared* assumption (for count models: zero-inflated / heavily overdispersed
data that breaks the negative-binomial prior both DESeq2 and edgeR lean on). **Co-failure on these
probes is the fingerprint of a shared prior.**

- **Plugs into:** the existing RED-TEAM daemon — a "decorrelation red-team."

### R4 — The heterodox third witness *(architectural; for the bias R2 can't see)*

When two legs are suspected of shared priors, audit with a **third** adapter chosen for *maximal
methodological distance* — for variant effect, a structural/biophysical model rather than another
evolutionary-sequence model. The third witness's job is not to agree but to **disagree
informatively**. Agreement that survives a methodologically-distant third is the only agreement
that argues meaningfully against correlated bias.

- **Plugs into:** the heterodox reserve lane already in SELECT (#3b) — extend the idea from
  *selection* into *verification*.

### R5 — Effective-N as the cap, not the tier *(the integration)*

Tie R1–R4 together: the strength vector's evidence axes should reflect **effective independent
witnesses**, computed from measured ρ (and bounded by the provenance prior when ρ is unmeasurable),
instead of a hand-set tier discount. The tier label degrades to a *fallback prior, used only until
the battery has spoken.*

- **Plugs into:** the oracle strength-cap mechanism that already exists — this changes what *feeds*
  it, not the gate itself.

---

## Do this first — the weekend-scale experiment

Before building any machinery, **measure whether the problem is real and how scary it is:**

> Take AlphaMissense and ESM1v. Run both on a held-out, high-confidence ClinVar set. Compute their
> **error correlation** and **double-fault rate**. If ρ is alarmingly high — two "independent"
> models from two companies failing on the *same* variants — you have empirically shown that
> organizational independence is a comfortable illusion, and R2 becomes a priority instead of a
> paragraph.

A real, falsifiable experiment that costs a day. Either it justifies the whole hardening arc or it
tells you the concern is smaller than feared. Both outcomes are worth knowing.

---

## Adjacent recommendations (from the same `/neg` read)

- **Mine the disagreement graveyard.** Make the PENDING-on-disagreement set a first-class *output*,
  not a dead end: "claims that are method-dependent" is itself a discovery about the tools. A small
  method-sensitivity report turns a failure state into a product.
- **A provenance edge for derivative claims.** When pathway enrichment consumes an upstream DE
  claim, record a *claim-on-claim* provenance edge so strength and defeat propagate. This is where
  the flywheel literally turns; it deserves to leave the caveats section.
- **Positioning: "disagreement-cartographer."** The honest and more compelling pitch may be "a
  machine that finds exactly where methods and evidence fail to agree" — sharper and more believable
  than "a truth engine," and closer to what the architecture actually is.

---

## What this is not

Not a plan, not a schedule. A recommendation set to explore when adapter-independence hardening
leaves the horizon. R2 + the weekend experiment are the natural first probe.
