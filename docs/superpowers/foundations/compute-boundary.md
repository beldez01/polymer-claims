# The Compute Boundary — Polymer certifies, it does not serve compute

**Status:** Foundational orientation — **a strong default, no longer an absolute law** (softened
2026-07-13). This still constrains every other doc, but as the reasoned default position, not an
inviolable constraint.
**Date:** 2026-06-29 · **Updated:** 2026-06-30 (added: existence-vs-correctness, the verification
ladder, the four-part spine, the Science Claw) · **Amended:** 2026-07-13 (doctrine → default).

---

## Amendment (2026-07-13) — from doctrine to default

The "never host or serve compute" rule below was written as an absolute. **It is now the strong
default, not a law.** The trust-first thesis and the V1→Galaxy lesson (owning the runtime *pulls* you
toward hosted compute — "gravity, not a choice") remain the reason to *default* to certifying compute
that runs elsewhere. What has changed: some viable **business models** may require hosting *some*
compute — e.g. a claims API a user pings to have us compute a concordance/consistency metric.

Where the line actually falls is **downstream of an unresolved product-identity decision** (active as
of this amendment): is Polymer

1. **local software** that extracts meaning from a user's own data (line stays where this doc drew it),
2. an **open-source public claims world** where claims are submitted and adjudicated in the open,
3. a **hosted claims/concordance API** (users ping; we compute a bounded metric), or
4. an **in-house drug-discovery engine** for a first-party bioAI company (the boundary is internal)?

Each puts the compute line in a different place. Until that fork resolves, treat hosting as a **graded
policy decision** — permitted where a real capability or business model requires it, defaulting to
trust-first otherwise — rather than a forbidden act. The body below is preserved **as the argument for
the default**, not as a prohibition. (Tracked in `BACKLOG.md` §9 as a strategic decision.)

---

## The principle, in one sentence

**Polymer specifies, orchestrates, witnesses, and certifies computation. It never hosts or serves
the computation itself.**

Pipelines run on the user's machine, the user's cloud, or a third party's API — with the user's
credentials, in the user's environment. Polymer ships the orchestrator, the verifier, the
catalogs, the provenance store, and the viewer. **It does not ship a compute backend.**

---

## What Polymer is, and is not

| Polymer **is** | Polymer **is not** |
|---|---|
| a certification standard for claim strength | a place you rent compute |
| a referee between pipelines it did not run | a runtime that executes pipelines |
| a navigator that knows *where* data lives | a warehouse that stores your data |
| local-first / bring-your-own-compute | a hosted cluster |

The analogy: UL and ISO do not manufacture anything — they certify what other people manufacture.
Polymer is to bioinformatics compute what a certification standard is to a factory. **Galaxy is the
factory you rent; Polymer is the standard that says this claim was established to spec, with the
audit trail to prove it.** The two sit on different layers of the stack and do not need to touch.

---

## Why this is the boundary that matters most

The original point of the platform was never execution. It was a **standardized way of establishing
claim strength.** The verification core makes this concrete: the two-implementation gate does not
require Polymer to *run* either implementation — it requires Polymer to *witness and compare two
runs that happened elsewhere.* That is adjudication, not execution. A referee does not need a
stadium.

This is also exactly why the architecture's own logic forbids owning the compute. Independence —
the thing that makes a claim strong — is a property you get by *not* owning the legs. Two adapters
owned by strangers (NVIDIA vs DeepMind) beat two of your own modules. The deepest principle in the
system is already telling you: **don't be the engine, be the referee that plays other engines off
against each other.**

### The hard-won lesson (V1 → Galaxy)

Polymer V1 became a deterministic bioinformatic execution pipeline. Once its job was *execution*, it
owned the runtime; and owning the runtime at scale forces hosted cloud compute — that is gravity,
not a choice. That path ends at the Galaxy ecosystem: people paying to use someone's hosted compute.
**That is the thing we are explicitly not building.** The escape is structural: this architecture's
job is adjudication, so it never acquires the runtime that drags everything toward a compute utility.

---

## What we actually require: that the computation *happened*, not that it's *correct*

Two different things wear the name "verification," and the boundary depends on keeping them apart.

- **Correctness** — did the number come out *right*? Checking this means re-deriving the result with
  an alternative algorithm. The moment that is your job, you own a second implementation, you version
  it, you stand behind it, and you own every discrepancy. That is a compute product with a
  correctness SLA. That is the engine, and that is the gravity this whole doc exists to resist.
- **Existence** — did the computation *happen at all*, and is the stated number the one that actually
  came out? This is provenance, not correctness.

Existence is the one that matters now, because **fabrication is the distinctly-agentic failure
mode.** Traditional science takes existence for granted: a person sat at the bench and ran the code,
so the number is assumed real and the only open question is whether it is right. Agentic science
loses that assumption. An agent can emit a fluent, plausible number it never computed. A human faking
a number is fraud — rare and socially policed; an agent doing it is a routine hallucination — common
and unpoliced.

So the foundational thing Polymer requires is not a recomputation. It is a **runtime log**: an
attested record that *this code*, on *this data* (hashed), produced *this output* (hashed), in *this
environment*. **The attested log is the verification floor.** We certify honesty-of-derivation — that
the claim was *earned by a computation that demonstrably ran* — not truth. And requiring a log is
exactly what keeps us off the engine path: requiring a *log* costs no compute we own; requiring a
*recomputation* would.

This is not a new thing to build. It is what the `attestation / standards skin` (in-toto Statement /
SLSA Provenance, DSSE-signed) and the `certificate` already produce, and it is why the system's stated
goal is to let a third party *verify a run without trusting our service.* Today's reframing is only
this: **that attestation skin is not merely an export format — it is the conceptual floor of
verification.**

Two guards keep the log load-bearing rather than decorative:

1. **The typed claim must bind to fields of the logged output.** The claim's `leaves` come from the
   log, not from agent prose. If a free-text narration layer sits between the logged output and the
   claim, fabrication just moves up one level — the agent runs a real computation, gets a real number,
   and narrates a different one.
2. **The log cannot be produced by the thing being witnessed.** A generator that writes its own log
   can forge its own log. This is the system's existing **`air gap`** (writer ≠ verifier), applied one
   level deeper: the log must come from a substrate the generator does not control.

---

## The verification ladder

Verification is not one gate. There is a **floor that sits under all belief**, then a set of
**belief tiers** above it. Every tier is *strength*, never *truth*; each adds to the 6-axis strength
vector rather than collapsing into a single pass/fail; and **no tier is owned compute** — each one
witnesses runs that happened elsewhere.

**The floor — attested execution (a precondition, not a belief tier).** Every `Satisfaction` that
licenses anything must carry a verifiable attested log: *this code, on this data (hashed), produced
this output (hashed), in this environment.* This is the anti-fabrication guard, required under
*every* license. It is what the `attestation / standards skin` (in-toto/SLSA) + DSSE signing already
emit. It does not, by itself, make a claim believed.

**The belief tiers** — how a `Licensing` is earned and what standing it carries:

| Tier | What it adds | In the system as |
|---|---|---|
| **Single-source evidence** | an e-value clears a baseline, one source | `EVIDENCE_LICENSED`, `independence_tier=None`, `verification_standing="single_source_baseline"` |
| **Reproduced** | two independent legs agree within tolerance (correctness-by-redundancy) | the `air gap` — trusted ∧ different owner ∧ different `implementation_hash` |
| **Replicated** | holds across ≥2 independent cohorts (external robustness) | `independence_tier=REPLICATED` (distinct `dimnames_hash`, error-independent) |
| **External attestation / credence** | an outside authority's determination, as defeasible testimony in the defeat graph | `ATTESTED ingestion` (instrument, never an oracle) — orthogonal |

An earlier draft of this ladder put "recompute agreement" at the floor. That was wrong: the
`EVIDENCE_LICENSED` route already licenses from a *single source* (no air-gap) at a recorded-weaker
standing, so recompute-agreement is **one `independence_tier`, not the floor of belief.** The floor
of belief is the attested log; recompute is one of several ways to earn standing above it.

**The decision (2026-06-30): WITNESSED.** Below all belief sits the claim that *ran and is attested
but cleared no tier* — in code, **a SATISFIED, attested `Satisfaction` with no `Licensing`.** Whether
that needs its own home turns on one property of the flywheel: if execution and adjudication happen in
the same cycle, the gap is a transient that needs no status; if they decouple — the claw runs now, but
clearing a tier waits on a baseline, a second independent leg, or a Foundry cohort that arrives later
— the gap is a real, possibly long-lived population. We take the **decoupled** case as the operating
assumption, and resolve it in three moves:

1. **Enforce the floor as a precondition** — no `Satisfaction` licenses anything without an attested
   log. Pure upside; do it regardless of the rest.
2. **Name the gap with a `PendingReason`** (`WITNESSED_UNADJUDICATED`): the claim is `PENDING`, its
   reason recording "ran, attested, no tier cleared." Non-belief-bearing by construction — never in
   the grounded extension, never multiplied into e-values, never certified.
3. **Defer a first-class `WITNESSED` status** until the viewer concretely needs to render these as
   distinct from `PENDING`.

---

## The four-part spine

The platform is **designed as** four parts, and the boundary runs through all of them. Three are below;
the fourth, the Foundry, is the boundary test that already had a section, now joined by the Claw.
*(Status: the Verification stack and Viewer are built; the **Science Claw and Cohort Foundry are horizon
— no code yet**. This is the intended spine, not four shipped components.)*

| Part | Its job | Stays on the right side of the boundary because |
|---|---|---|
| **Science Claw** | *generation* — the environment runtime where agents source data and run pipelines | it is the substrate we *witness*, run with the user's compute; we never host it |
| **Verification stack** | *honesty* — binds each claim to its attested runtime log (the floor + the single-source / reproduced tiers) | it adjudicates runs that happened elsewhere; a referee needs no stadium |
| **Cohort Foundry** | *strength* — proposes corroborating cohorts (the replicated + external-credence tiers) | it emits specs and provenance contracts, not data and not compute |
| **Viewer** | *consumption* — the 3D spectral universe + sheaf consistency overlay | it reads the corpus; it changes no claim's status |

In one line: **the Claw generates, the stack keeps it honest, the Foundry makes it strong, the Viewer
makes it legible — and at no part does Polymer own a correct computation.**

---

## Where the boundary gets tested: the Cohort Foundry

"The Foundry assembles validation cohorts" can quietly drift into "Polymer fetches, stores, and
processes your data" — which is a half-step from a hosted data service. The discipline that keeps it
on the right side:

- The Foundry **emits a specification and a provenance contract** for a validation cohort, and
  **orchestrates its assembly in the user's environment.**
- The data-source catalog is **knowledge about where data lives** — a navigator — **not a
  warehouse.**
- The data pull and the harmonization compute run on the **user's side**; Polymer **records and
  certifies** what happened.

The alarm bell: the day "for convenience" we spin up a hosted cluster to assemble cohorts or run
pipelines on Polymer's servers, we have crossed back into Galaxy. As long as that line holds, the
growing computational surface is a standard growing into its body — not a utility we did not mean to
build.

---

## Where the boundary gets tested: the Science Claw

The Claw is the third component and the largest boundary test of all, because it *literally runs
pipelines.* It is a **single-user, local-first environment-agent runtime** — an open agent for
science. You drag in datasets (your own, or something like the terabyte of ancient-genome data
sitting on Kaggle); an agent carrying the polymer-claims harness context sources, downloads, and runs
bioinformatic pipelines *in your environment*; and every output lands as a typed claim in your
universe. As the agent elaborates experiments, the universe accretes structure you can see in the
viewer. A federated, publicly hosted universe people contribute to is possible later, but the primary
product is **individual science** — a place to pull in whatever you want to work on and let the agent
fill out its claims universe.

**The apparent contradiction, and why it dissolves.** The Claw runs pipelines, so doesn't it cross
the boundary? No — for the same reason the Foundry does not. You cannot *witness* an execution unless
the execution happens inside a boundary whose logging you control. The Claw *is* that boundary. It is
the lab bench; Polymer is still the notary standing at it. The agent runs whatever it wants; Polymer
never curates a method catalog, never guarantees correctness, never maintains the pipelines, and the
compute runs with the user's credentials in the user's environment. The Claw is **bring-your-own-
compute wearing a single-user skin**, not a hosted runtime. The alarm bell is the same one: the day
the Claw "for convenience" runs pipelines on Polymer's servers, it is Galaxy.

**Provenance roots at ingestion, not at the run.** When a dataset is dragged in, it becomes a typed,
hashed, licensed *source node* — the system already mints a GA4GH **DRS** object per dataset. The
lineage is then typed end to end: *source → run → attested output → claim.* A claim whose lineage
bottoms out in "a file the agent found" is the exact hole the attestation is there to close, so
ingestion is a first-class attested event, not an afterthought.

**The moat is not the agent.** Bioinformatics agents are commoditizing; competing on "best agent at
running RNA-seq" is a funding race against teams that do only that, and it is a losing one. The moat
is that every output the agent produces lands as a **typed, attested, navigable claim**. Compete on
honesty, typing, and legibility — never on the agent.

**The trust spectrum (the existing `honest boundary`, local vs networked).** Run locally, the log is
only as trustworthy as the user — and that is fine, because personal science is self-trusted; you are
not trying to fool yourself. Federate, and a claim's log is meaningful only if produced by a witness
the *consumer* trusts: in a shared universe the user can no more forge it than the agent can. This is
already the system's stated boundary — local DSSE gives tamper-evidence and signed timestamps but
**not** public non-repudiation; that needs the networked Rekor backend, which is designed and
intentionally tabled. Federation is the day that rung gets turned on. Staying single-user-first also
keeps the arbitrary-code-execution surface (sourcing and running untrusted code and data) out of
scope until the core is proven.

---

## The test, stated as an enforceable rule

Before adding any capability, ask: **does this make Polymer run, host, or store the science — or
does it make Polymer better at specifying, orchestrating, witnessing, and certifying science that
runs elsewhere?** The first crosses the boundary. The second does not. Local-first is not a
constraint we tolerate; it is the moat.
