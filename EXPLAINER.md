# polymer-claims, explained for a human

A plain-language walkthrough of what this system is and how it actually works. Written to be
handed to someone with no background — a friend, a collaborator, an investor. No prior knowledge
assumed. Everything below is grounded in the real code; file paths are given where it helps.

---

## The one sentence

**polymer-claims is a machine that does science in a loop, and never lets itself believe
something it didn't earn the right to believe.**

The project's own tagline is the real description: a **compiler + runtime for science.** Think
about a normal programming language:

- A **compiler** checks your source code is well-formed and turns it into something runnable.
- A **runtime** actually executes it and manages state as it runs.

This system does the same two things, except the "source code" is *scientific claims* and the
"program output" is *verified knowledge that accumulates over time*.

- **The Grammar** (`grammar/`) = the compiler. It defines what a scientific claim *is* and
  whether it's well-formed.
- **The Protocol** (`protocol/`) = the runtime. It runs a whole corpus of claims forward and
  grows it toward truth.

The rest of this document makes that concrete by following one hypothesis through the entire
machine, then showing what happens when claims disagree, then opening up the two parts people
find hardest to believe.

---

## Example 1: one hypothesis, cradle to grave

Say we're studying acute myeloid leukemia (AML), and an automated agent proposes a hypothesis:

> *"In AML patients, a specific DNA region is more methylated in IDH-mutant tumors than in
> IDH-wildtype tumors."*

Here is what physically happens to that sentence inside the machine.

### Step 1 — It becomes a structured object, not a sentence

The machine doesn't store English. It stores a **claim** — a typed data structure. The fields
that matter:

- **`leaves`** — the actual empirical anchor: the raw number(s) the claim rests on (a measured
  methylation difference, its uncertainty, its units). Leaves are *sum-typed* — a leaf can be a
  number, **or** a yes/no existence finding, **or** a qualitative judgment. The system refuses to
  fake everything into a p-value. "We observed that X happens at all" is a first-class result.
- **`pattern`** — the *shape* of the claim. Our example is an `adjusted_effect` ("X differs from
  Y, controlling for confounders"). The pattern tells the machine how to interpret the leaves.
- **`subject`** — what the claim is *about* (these tumors, this region).
- **`roles`** — which variable is the cause, which is the effect, which are confounders. Sharp
  design choice here: the set of things you must adjust for is **derived from the causal
  structure, not authored by hand** — a guard against a classic statistics mistake (the "Table 2
  fallacy," controlling for the wrong things and reporting garbage).
- **`strength`** — *not a single score.* A **6-axis vector** (magnitude, uncertainty,
  evidence-against-null, world-contact, and so on). Two claims can be genuinely incomparable —
  one stronger on magnitude, the other on certainty — and the machine preserves that rather than
  crushing it into one number that hides the tradeoff.

At this point the claim is just **CONJECTURED**. Nobody believes it. It's a well-formed guess.

### Step 2 — The machine decides if it's even worth testing (SELECT)

Testing costs something (compute, data, money). So a scheduler ranks every pending conjecture on
two axes:

- **expected information gain** — how much would we learn if we ran this?
- **stakes** — how many other claims depend on this one?

Given a budget, it runs *only the winners* this cycle; the rest stay pending. This is what makes
the system a research *strategy* and not just a firehose — it spends limited attention where it
will learn the most.

### Step 3 — It runs the experiment, twice, by two strangers (EXECUTE + VERIFY)

There are two different questions here, and the system keeps them apart — this is the part worth
being precise about (full detail in the section below and in
`docs/superpowers/foundations/compute-boundary.md`).

**The floor, under every licensed claim: did the computation actually happen?** The machine demands
an *attested log* — *this code, on this data (hashed), produced this output (hashed), in this
environment* — produced by a substrate the proposer doesn't control. Requiring a log costs no
compute the system itself runs, and it guards against the distinctly-agentic failure mode: an agent
emitting a fluent, plausible number it never computed. This is provenance, not correctness, and it
is the actual foundation of belief.

**A strength tier on top of the floor: do two independent implementations agree?** The machine can
recompute the claim's result with **two implementations that don't share code** (different owner,
different code-lineage) and, if they agree within tolerance on the same data, the claim earns the
**REPRODUCED** tier. A claim can never confirm itself — the thing that *writes* a claim is barred
from being the thing that *verifies* it. But be clear about what this tier buys: it tests
**reproducibility, not truth** — it catches coding artifacts and fabrication, not a wrong
experimental premise. It is one rung on a ladder, not the whole of trust.

After this step the claim is either **LICENSED** (both agreed, verdict SATISFIED), or it stays
**PENDING** / gets **REJECTED**.

Even when licensed, there's a ceiling: if the evidence came through some external "oracle" (a
third-party model or apparatus), the claim's strength is **capped by the weakest oracle it relied
on**. Weak evidence source means the claim simply *cannot* score high, no matter what. That
guarantee is always on.

### Step 4 — It folds back in, and the corpus argues with itself (INTEGRATE)

The licensed claim joins the population of all other claims — and claims **defeat each other**.
The corpus is literally an argument graph:

- A new claim can **rebut** an existing one.
- But an attack only *wins* if the attacker isn't dominated by its target on the strength vector.
  A weak claim can't knock out a strong one just by disagreeing.

The machine computes which claims currently survive all attacks — the **grounded extension**,
i.e. "what the corpus currently believes." Add a claim, and beliefs elsewhere can flip
automatically.

**That's the whole flywheel:** generate a guess → decide if it's worth it → run it twice
independently → license only on agreement → fold it in and let it fight → repeat. The corpus
self-corrects and accumulates.

---

## Example 2: what happens when claims contradict each other

The `data/demo/frustrated_cycle_corpus.json` demo shows this in miniature. Three claims, A, B, C:

- A and B are asserted **equivalent** (they're "the same claim").
- B and C are also asserted equivalent.
- But C **rebuts** A.

Follow the chain: A = B, B = C, so transitively A should equal C. But C *attacks* A. The corpus
is saying "A is the same as C" and "C destroys A" at once. That's a **frustrated cycle** — a
genuine logical tension.

A naive system would silently pick a winner and move on, hiding the problem. This machine does
the opposite: it **surfaces the contradiction** as an explicit, named state
(`duhem_underdetermined` — "the evidence genuinely can't tell us which to drop"). When it must
restore consistency, it removes the *least-entrenched* claim — and if entrenchment can't decide,
it tells you it can't decide rather than pretending.

That honesty about its own limits is the personality of the whole system. It would rather say
"underdetermined" than launder a guess into a verdict.

---

## How verification really works: the floor, then the reproduced tier

Verification is not one gate; it is a **floor** with **strength tiers** on top. The floor under
every licensed claim is the **attested log** — proof that the computation happened at all
(*existence*), the anti-fabrication guard that costs the system no compute of its own. What follows
describes the tier *above* the floor: **REPRODUCED**, earned when two independent implementations
agree. (The full ladder — single-source evidence → reproduced → replicated, all resting on the
attestation floor — is specified in `docs/superpowers/foundations/compute-boundary.md`; the "is this
verification circular?" question is answered in `foundations/epistemology.md`.)

People hear "two independent implementations must agree" and reasonably ask: independent *how*?
Different data? Different code? How independent can they really be?

**The answer: same data, different code — plus different owner and different code-lineage.**

### What an "adapter" is

An adapter is a small object with one string `identity` and one method, `execute(...)`, that
computes a claim's value. (`grammar/src/polymer_grammar/evaluate.py`)

To verify a claim, the machine takes the **same** plan, the **same** context, and the **same**
data leaves, and runs them through **two different adapters**. Only the executing code differs.
The data is held fixed on purpose — the independence is in the computation and where it comes
from, not in using different datasets.

### How different the two can be

The design spans a wide range, and the repo has examples across it:

- **Mild:** one adapter computes a mean as naive `sum(xs)/len(xs)`; the other uses
  `statistics.fmean` (exact `math.fsum`). The code calls this "a deliberate second
  implementation."
- **Real-but-local:** `StatsPureAdapter` (hand-rolled accumulation) vs `StatsStdlibAdapter`
  (stdlib). They share the data-access layer but each computes the statistic with its own code.
  (`src/polymer_claims/exec_adapters.py`)
- **Genuinely external:** `BioNeMoNIMAdapter` (owner `"NVIDIA"`) hits a remote NVIDIA inference
  endpoint — your code vs a third party's neural net on someone else's server.
  (`examples/bionemo_plumbing/`)

### How independence is defined and enforced — two stacked gates

1. **Weak structural gate** (grammar): you need ≥2 adapters with ≥2 *distinct identity strings*,
   else it raises `SelfLicensingError`. The code itself admits this is "necessary but not
   sufficient" — identity strings could be faked.
2. **The real gate** (the protocol's `AdapterRegistry`): each adapter carries an
   operator-asserted credential — `(identity, owner, implementation_hash, version, trusted)`. Two
   adapters count as independent **only if: both `trusted` AND different `owner` AND different
   `implementation_hash`.** The `implementation_hash` is derived from the `execute` method's
   **bytecode**, so two classes with byte-identical code collide on the hash and are rejected as
   the same lineage. (`protocol/src/polymer_protocol/adapter_registry.py`,
   `src/polymer_claims/adapter_identity.py`)

Using the same adapter twice fails gate 1. Two cosmetically-different adapters owned by one actor
fail gate 2. When the registry is active, a claim that can't produce an independent credential
pair is held PENDING with reason `ADAPTER_NOT_INDEPENDENT`, and the winning pair's IDs are
stamped onto the licensed result as an audit trail.

### What "agree" means numerically

Not exact equality. Two conditions:

1. **Verdict parity** — both adapters must reach the same satisfaction verdict.
2. **Numeric tolerance** — `abs_diff ≤ 1e-9 OR rel_diff ≤ 1e-6` (exact equality only for
   strings / None).

A claim licenses only if they agree **and** the verdict is SATISFIED.

### "No self-licensing," concretely

The thing that *writes* a claim must not be the thing that *verifies* it. A single implementation
can never mint a license. This is structurally enforced, not a convention.

### Two honest caveats to pass along

**Implementation independence is not conceptual independence — a real limit, not a footnote.** The
gate secures *code* independence (distinct authors, distinct bytecode). It does *not*, on its own,
secure independence of the shared operationalization, ontology, and measurement priors both legs may
inherit. If both implementations rest on the same experimental premise, their agreement tracks that
shared frame, not reality — so the gate is a *method-dependence detector, not a correspondence
oracle*. The system's partial answers are the **common-cause DAG** (`shared_cause_factors`: a
license requires low shared-cause overlap, and independence gates whether two legs' e-values may
even multiply) and the **defeat graph + RED-TEAM daemon**, where "your two legs share premise Z" is
a *first-class, licensable defeater* — critique of the experimental priors happens there, in the
argument layer, never in the recompute. Certifying the *breadth* of independence rather than
inferring it from code diversity is an acknowledged open problem (`foundations/residualism.md` §7;
`foundations/epistemology.md` §2).

**The strongest external example is still partly a stand-in.** BioNeMo currently uses a *fenced
synthetic corroborator* as its second leg — a test double, owner-tagged `polymer-claims-test` and
barred from any real certifying run until a genuine independent model replaces it. So "two radically
independent real models" is fully wired, but the headline external demo's second leg is a stand-in
today.

---

## The sheaf-consistency instrument (and the 3D viewer)

The corpus has a built-in way to measure **how much it contradicts itself**, using real
cellular-sheaf Laplacian math (not merely "inspired by" — it computes the actual objects). It's
explicitly an **instrument, not a gate**: it never changes a claim's status. It just shows you
where the tension is. (`protocol/src/polymer_protocol/sheaf.py`,
`src/polymer_claims/sheaf_spectrum.py`)

How it works, in plain terms:

- Each claim with a quantity becomes a **vertex holding a scalar value** (a "stalk"). Edges come
  in two kinds: **equivalence** (agreement, +1) and **defeat** (antagonism, −1).
- The **coboundary** measures tension on each edge: equivalence edges measure disagreement
  (`x_u − x_v`); defeat edges measure `x_u + x_v`.
- **Inconsistency energy** = Σ (weight × tension²) — the *Robinson consistency radius* / the H⁰
  obstruction. A single global number for "how much does the corpus contradict itself right now."
- It builds the **sheaf Laplacian** `L = δᵀWδ` and eigendecomposes it. The number of near-zero
  eigenvalues = **dim H⁰** = how many internally-consistent components the corpus has; the
  smallest positive eigenvalue λ₂ = how tightly knit the weakest component is.
- A **signed-BFS frustration detector** finds **H¹ obstructions** — frustrated cycles like
  "A ≈ B, B ≈ C, but A defeats C," the irreducible contradictions (the frustrated-cycle demo,
  generalized).
- **Per-claim tension** attributes the global energy back to individual claims. High tension = a
  claim sitting at the center of contradictory edges.

What it's *for*: it surfaces **high-tension / self-contradiction**, not "value" in a ranking
sense. But the claims it lights up are exactly the interesting ones to investigate, because
they're where the corpus is unstable. It's a "where is the corpus arguing with itself" detector.

**The viewer** (`viewer/`, Next + React Three Fiber) renders the live universe of claims in 3D.
Layout is the **signed-Laplacian spectral eigenmap, Procrustes-aligned** frame-to-frame (a legacy
force-directed layout is also selectable). The sheaf gauge appears as an **opt-in "consistency
overlay"**: a falling inconsistency-energy HUD with λ₂, animated H¹ frustration-cycle ribbons, and
heat-colored per-claim tension halos. The math needs the optional `[embed]` extra (numpy); the
core engine stays numpy-free by design.

Caveat worth knowing: today only the *first* quantity leaf per claim becomes a stalk, so claims
with no quantity don't participate in the consistency math yet — flagged in the code as a planned
enrichment.

---

## Why it's built this counter-intuitive way

Every odd design choice traces back to one fear: **a science machine that fools itself.** An AI
that generates hypotheses and grades its own work will produce a beautiful, confident, growing
pile of nonsense. So the architecture is a series of locks against exactly that:

| The lock | What it prevents |
|---|---|
| **Attested log required under every license** (the floor: proof the computation ran) | Fabrication — an agent asserting a number it never computed |
| Two independent adapters agree → the **REPRODUCED** tier (one rung, not the floor) | Coding artifacts; self-confirmation (a claim can't confirm itself) |
| Generators can propose but **never** license | The proposer rigging its own grade |
| 6-axis strength vector, no hidden scalar | Hiding a weak dimension behind a strong one |
| Adjustment sets *derived*, not authored | Cooking the confounders |
| Oracle strength caps | Trusting weak evidence too much |
| Contradictions surfaced (`duhem_underdetermined`), not silently resolved | Laundering uncertainty into false confidence |
| Sheaf instrument is a gauge, never a gate | Letting a heuristic quietly overrule the evidence |

The payoff: a corpus where every believed claim has a paper trail for *why* it's believed, *what
would overturn it*, and *how strong the evidence actually is* — and the whole thing can run
forward on its own, getting less wrong over time.

---

## See it run

- **Offline, one command** — drive a single claim to LICENSED and emit a certificate:
  `uv run --project . python -m examples.bionemo_plumbing.run` (prints `Status.LICENSED`).
- **Live node + 3D viewer** — watch the universe of claims evolve in real time:
  `polymer-claims serve` (terminal 1) and `cd viewer && npm run dev` (terminal 2), then click
  Connect. Turn on the consistency overlay to watch the corpus's self-contradiction energy fall.

See `README.md` for full quickstart options, `ARCHITECTURE_CURRENT.md` for what's active vs
deferred, and `GLOSSARY.md` for the reserved terms.
