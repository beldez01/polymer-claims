# Pitch Notes — Competitive Landscape, the AI-Scientist Loop, and the Verification Model

> **Status:** Working pitch / positioning notes. Created 2026-07-07.
> **Scope:** (1) who else is in this space and where the white space is; (2) a concrete trace of
> an autonomous AI scientist ("Claude Science") using Polymer; (3) the honest defense of the
> verification model against the "isn't this just a compute layer?" objection.
> **Grounding:** competitive facts are from a 2026-07 web scan (references at the end); internal
> claims are grounded in `docs/superpowers/foundations/compute-boundary.md`,
> `foundations/epistemology.md`, and `foundations/residualism.md`.

---

## Part 1 — Competitive landscape

### Verdict

The white space is real, but the honest framing is **not** "nobody is doing this." Everyone now
agrees verification is the bottleneck of AI-generated science. Polymer's differentiated position:
**it is the only approach that verifies by attested execution + independent recomputation +
cryptographic provenance, rather than by checking a claim against its cited sources.** Early in a
validated, heating category with a stronger trust primitive — not alone in an empty one.

### The market thesis is confirmed by third parties (the tailwind)

- "Verification is the central unresolved problem for autonomous research systems" — recurring across
  the AI-scientist survey literature.
- Evaluations of Sakana's AI Scientist found roughly half of experiments failed and manuscripts
  contained *hallucinated numerical results* [1].
- "AI-Augmented Science and the New Institutional Scarcities" argues the bottleneck shifts from
  *producing* findings to *verifying* them; verification / provenance / attestation infrastructure
  becomes the scarce, high-value institutional layer [2].

You don't have to convince an investor the problem exists. The field is saying it out loud.

### The two nearest neighbors — and what they deliberately leave out

| System | What it is | Trust mechanism | What it deliberately lacks |
|---|---|---|---|
| **Knows / Ara** [3] | YAML sidecar on papers: typed statements, quantitative evidence, typed relations (`challenged_by`, `supersedes`, `retracts`), provenance | Structural linting only | Explicitly **"an author assertion, not a certification."** Semantic truth is "the authoring party's responsibility." No independent re-execution, no attestation, no truth-maintenance. It is a token-efficiency layer for weak models. |
| **EviBound** [4] | Dual-gate "evidence-bound execution" governance to eliminate false AI claims | Checks claims against their **cited evidence sources** (consistency-with-the-record) | Research prototype. No independent re-implementation, no cryptographic attestation, no typed IR, no FDR/e-value control. A governance wrapper, not a standard + ledger. |
| **FutureHouse / Robin** [5] | Multi-agent discovery system | "Every statement backed by a cited source" | Provenance-to-literature, not recomputation. |
| **Google Co-Scientist** [6] | Tournament / debate of hypotheses + Reflection agent | Self-critique + external search | No attestation, no independent-recompute gate. |
| **Nanopublications / ORKG** [7,8] | RDF claim atoms with provenance | Semantic-web citability | "None provides execution semantics or captures decision history"; RDF authoring cost has capped adoption for a decade. |

**Read the two headline rows together and the position pops out in one sentence:**

> Knows built the representation half and explicitly stopped before certification. EviBound built
> the governance half but verifies by citation-consistency, not recomputation, and has no ledger.
> Polymer is the integrated thing neither will ship: an executable typed claim IR + attested-execution
> licensing + independence-measured strength + a cryptographic transparency log.

Every competitor verifies a claim against **the cited record** (does the paper say what you say it
says?). Polymer verifies against **reality** (did the computation demonstrably run, and do independent
corroborators agree under FDR control?) and then signs a portable receipt. Citation-checking catches
misquotes; it does not catch a plausible, well-cited, *wrong* result. That is the gap the scan's
failure modes (hallucinated numbers, half the experiments failing) actually call for.

### Three strategic implications

1. **Differentiator line:** "Others check whether an AI's claim is *consistent with the literature*.
   We check whether it was *earned by a computation that demonstrably ran*, corroborated by
   independent legs under statistical error control, and we sign a transparency-logged certificate."
2. **Adoption lesson from Knows:** Knows won usage by being a *capability* win (weak models use 29–86%
   fewer tokens). A pure "trust layer" is an eat-your-vegetables sell. Pair the trust gate with a
   direct agent win — the corpus is persistent cross-run memory, the scheduler saves compute, the
   certificate is a sellable/publishable artifact.
3. **Don't claim to be alone.** Claim to be early in a category the field just admitted it needs,
   with the one approach that verifies by execution + cryptography rather than by citation.

---

## Part 2 — The AI-scientist loop, with "Claude Science"

**The division of labor:** Claude Science is the **generator and the compute**. Polymer is the
**governor and the ledger**. The generator is swappable and commoditized; the licensing harness is
the moat. This maps directly onto the scan's core finding — "some systems lack a provenance layer and
can't verify claimed results." Polymer *is* that layer, as a substrate any agent plugs into.

Not hypothetical: the repo already ships `LLMGenerationAdapter` (Anthropic-backed) driving the live
node via `serve --llm`, and `verify-kernel --real` licenses a real TCGA-LAML methylation finding at
REPRODUCED. The loop below has a real, reproduced instance today.

### The loop, stage by stage

Using the AML example — *"IDH-mutant AML is hypermethylated at region X vs. wild-type."*

| # | Claude Science does… | Polymer stage | The governor bites here |
|---|---|---|---|
| 1 | Reads corpus + literature, proposes a hypothesis in English | — | — |
| 2 | **Emits it as a typed claim** (pattern=`adjusted_effect`; subject with typed refs → MONDO/HGVS/`cg`-accession; roles: cause=IDH, effect=methylation, confounders **derived** from causal structure; leaves empty; strength unknown) | **CONJECTURE** (compile) | Grammar type-checks it. Table-2-fallacy adjustments or a smuggled lone p-value → rejected at compile time. Claude **structurally cannot self-license.** |
| 3 | Commits the analysis plan *before seeing data* | **Pre-registration ledger** | `commitment_hash` locks the plan; a later reshape-to-fit-data → terminal `HYPOTHESIS_ALTERED`. No competitor has this. |
| 4 | Proposes many conjectures (a firehose) | **SELECT** | Scheduler ranks by expected-info-gain × stakes under a budget; runs only the winners. Makes Claude strategic, not just prolific. |
| 5 | Runs the analysis through **two independent adapters** it does not own the pair of (e.g. one local stdlib leg + one external BioNeMo/NVIDIA leg) | **EXECUTE** (BYO-compute) | Claude cannot assert the number. Value must be computed by distinct code lineage (bytecode-hash-distinct, different owner). |
| 6 | Waits for the verdict | **VERIFY** (the ladder) | Floor: an **attested log** must exist for every satisfaction (see Part 3). Above the floor, standing is earned: independent legs agree within tolerance (REPRODUCED) and the live e-LOND betting e-value clears its α-budget. If it's a fluke, the gate withholds the license (as it really did — region-Δβ held PENDING at e-value 0.867). |
| 7 | Receives a portable certificate | **Attestation** | in-toto/SLSA statement + DSSE signature + Merkle transparency-log inclusion proof. A third party who trusts Claude zero can verify the claim. This is the artifact pharma/journals buy. |
| 8 | Reads back "what is now believed" | **INTEGRATE** | Licensed claim joins the corpus and fights; a winning rebuttal de-licenses the loser through the FDR ledger and refunds budget; the sheaf gauge shows where the new claim created contradiction. Claude's next hypothesis is generated against the **grounded extension**, not raw literature. |

Then it repeats. The corpus is persistent, shared, self-correcting memory across runs — and across
*different* agents: a Sakana agent and a Claude agent can write to the same corpus, and their claims
fight on neutral ground with attested provenance. (Architecturally implied by `Corpus` + attestation
+ the noted `POST /inject` hook; not yet demonstrated end-to-end.)

### One-slide division of labor

```
CLAUDE SCIENCE  ─────────────────►   POLYMER CLAIMS
(generator + compute)                (governor + ledger)
• proposes hypotheses                • type-checks the claim (compile-time linter)
• runs the analyses                  • pre-registers the plan (no HARKing)
• supplies adapter legs it           • floor: requires an attested log that the computation ran
  does not own as a pair             • earns standing by independence it WITNESSES, not owns
• reads the believed state           • signs a transparency-logged certificate
  commoditized, swappable            • maintains the shared, self-correcting truth-state
                                       ── THE MOAT ──
```

**Why an agent-builder plugs in** (trust *and* capability): persistent cross-run memory so the agent
stops re-deriving; SELECT saves compute; the certificate is sellable/publishable; pre-registration +
FDR means outputs survive peer review and regulatory scrutiny.

---

## Part 3 — The verification model: what it is, what it is not, and why it is not a compute layer

The load-bearing objection: *"Two independent implementations agreeing only checks the output. That's
recomputation — the thing we're trying to avoid. It has no bearing on truth, and it says nothing about
the experimental priors. Doesn't the second method inevitably make us a compute layer?"*

The objection is sharp and **mostly answered by the foundations already** — by agreeing with three of
its four points and moving the floor off recomputation. See
`foundations/compute-boundary.md` and `foundations/epistemology.md`.

### 1. The floor is *existence*, not *correctness* — so the floor is not recompute at all

Two different things wear the name "verification" (`compute-boundary.md`):

- **Correctness** — did the number come out *right*? Checking this means re-deriving with another
  algorithm. The moment that is *your* job, you own a second implementation, you version it, you carry
  a correctness SLA — that **is** a compute engine, and it is the gravity to resist.
- **Existence** — did the computation *happen at all*, and is the stated number the one that actually
  came out? This is **provenance, not correctness.**

The verification *floor* under every license is the **attested log**: *this code, on this data
(hashed), produced this output (hashed), in this environment*, produced by a substrate the generator
does not control (the air gap, one level deeper). Requiring a *log* costs no compute you own;
requiring a *recomputation* would. Existence is the point because **fabrication is the distinctly
agentic failure mode** — a human faking a number is rare fraud; an agent emitting a fluent number it
never computed is a routine hallucination. The attestation skin (in-toto/SLSA + DSSE) is not merely an
export format; it is the conceptual floor of verification.

### 2. Two-implementation agreement is one *tier*, not the foundation

`compute-boundary.md` explicitly demotes recompute-agreement from the floor to **one
`independence_tier` (REPRODUCED)**. An earlier draft that put "recompute agreement" at the floor is
flagged as *wrong*: the `EVIDENCE_LICENSED` route already licenses from a single source at a recorded-
weaker standing. So the verification ladder is:

- **Floor — attested execution** (a precondition, not a belief tier): the log must exist.
- **Single-source evidence** — one e-value clears a baseline.
- **Reproduced** — two independent legs agree within tolerance (correctness-*by-redundancy*).
- **Replicated** — holds across ≥2 independent cohorts.

Every tier is *strength*, never *truth*, and adds to the 6-axis vector. Treating the two-implementation
gate as "the verification" is the outdated mental model that makes the whole thing feel like a compute
layer. It isn't the floor; it's one optional rung.

### 3. "No bearing on truth" is a feature, stated proudly — the system licenses, it does not *mean*

Per `residualism.md` and `epistemology.md`: the agreement gate confers **warranted assertibility**
(Dewey), not truth. Polymer certifies *honesty-of-derivation* — the claim was earned by a computation
that demonstrably ran — never correspondence to reality. The de Bruijn kernel says exactly this:

| Layer | Catches | Guarantees |
|---|---|---|
| Recompute kernel | computation errors, environment rot, "the code doesn't produce this number" | the result faithfully follows from the pinned computation |
| Independence | shared data, batch effects, fabrication, setup artifacts | two implementations that *fail for different reasons* both clear the bar |

"A reproducible build of *fabricated* data is still perfectly reproducible." The kernel verifies "the
result follows from this pinned computation" — never "the data is real." The project **knows** recompute
doesn't touch truth. Not aspiring to truth is the residualist identity, and it is the thing that keeps
Polymer honest where competitors overclaim.

### 4. The one point that genuinely lands: implementation independence ≠ conceptual independence

This is the real, unresolved edge, and it is already named in `residualism.md` §7 (Decorrelation) as
the **Sellarsian back-door Given**:

> The air-gap secures *implementation* independence (distinct code, distinct authors) but not
> *conceptual* independence. If both implementations inherit the same operationalizations, ontology,
> and measurement conventions, their agreement tracks the shared frame, not the territory.

So the objection "it says nothing about the experimental priors" is **correct about the recompute gate
in isolation.** The partial answers already in the system:

- The **common-cause DAG** (`§E shared_cause_factors`): shared inputs, methods, references, libraries,
  and statistical conventions are modeled as edges; a license requires *low shared-cause overlap*, and
  independence gates whether two legs' e-values may even multiply. The goal is *conceptual* replication
  (different assumptions, fails for different reasons — Wimsatt robustness), not direct replication.
- The **defeat graph + RED-TEAM daemon**: "your two legs share prior Z" or "your test is circular" is
  a **first-class, licensable defeater**, not a hidden flaw. Critiquing the experimental priors is done
  *here*, in the argumentation layer — not by the recompute.
- The honest stance: the gate is reclassified as a **method-dependence detector, not a correspondence
  oracle**; the strength of a license is *bounded by the breadth of independence actually sampled*,
  which the engine must certify and log, not infer from code diversity alone. That last part is an
  open problem, listed as such.

### 5. So: does the second method inevitably make Polymer a compute layer?

**No — conditionally, and the condition is enforceable.**

- If verification means **correctness** and *you own* the second implementation → yes, you become a
  compute product with a correctness SLA. This is the V1 → Galaxy gravity, and it is the thing to
  refuse.
- Polymer's floor is **existence** (an attested log), which costs no owned compute.
- Where recompute-agreement *does* happen (the REPRODUCED tier), the second leg is **owned and run by
  an independent third party Polymer merely witnesses** — a referee, not a stadium. Polymer never runs
  either leg.
- Polymer does grow a computational *surface* (the Science Claw: a local-first, BYO-compute environment
  agent), because you cannot *witness* a computation unless it happens inside a boundary whose logging
  you control. But that compute runs with the **user's credentials, in the user's environment.** The
  enforceable test: *does this make Polymer run/host/store the science, or make it better at
  specifying/orchestrating/witnessing/certifying science that runs elsewhere?* The first crosses the
  line; the second does not.

**Pitch consequence:** stop leading with "two independent implementations must agree." It is the most
compute-flavored, most attackable framing, and it isn't even the floor. Lead with: *every believed
claim carries a cryptographic proof that the computation that earned it demonstrably ran, and its
strength is a measured function of how independent its corroboration is — we never assert truth, we
bound standing by evidence.* That is provenance + measured independence: un-ownable, un-commoditizable,
and what the system actually is.

---

## References

1. Beel J, et al. Evaluating Sakana's AI Scientist: bold claims, mixed results, and a promising future?
   Preprint. 2026. arXiv:2502.14297 [Preprint — not peer reviewed].
2. [Author(s)]. AI-augmented science and the new institutional scarcities. Preprint. 2026.
   arXiv:2605.02566 [Preprint — not peer reviewed].
3. [Author(s)]. Knows: agent-native structured research representations. Preprint. 2026.
   arXiv:2604.17309 [Preprint — not peer reviewed].
4. [Author(s)]. Evidence-Bound Autonomous Research (EviBound): a governance framework for eliminating
   false claims. Preprint. 2025. arXiv:2511.05524 [Preprint — not peer reviewed].
5. IntuitionLabs. FutureHouse AI agents: a guide to its research platform.
   https://intuitionlabs.ai/articles/futurehouse-ai-agents-platform. Accessed 2026-07-07.
6. [Author(s)]. Accelerating scientific discovery with co-scientist. Nature. 2026.
   doi:10.1038/s41586-026-10644-y.
7. Kuhn T, et al. Underspecified scientific claims in nanopublications. Preprint. 2012.
   arXiv:1209.1483 [Preprint — not peer reviewed].
8. Clark T, Ciccarese PN, Goble CA. Micropublications: a semantic model for claims, evidence, arguments
   and annotations in biomedical communications. J Biomed Semantics. 2014;5:28. doi:10.1186/2041-1480-5-28.

*Verification-model sections (Part 3) are grounded in the internal foundations docs
`docs/superpowers/foundations/compute-boundary.md`, `foundations/epistemology.md`, and
`foundations/residualism.md`.*
