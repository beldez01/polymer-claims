# Polymer Claims — The Simple Map

*The shape of the whole thing on one page. Read this whenever the shape slips away.*

---

## The one-line version

**You feed in an unproven claim plus the ingredients to test it. The machine
re-runs the test independently and stamps a verdict. You get back a claim with
earned (or denied) standing — and that verdict stays alive.**

It is a **trust stamping machine** for scientific claims.

---

## The I/O map

```
        INPUTS                      THE MACHINE                    OUTPUTS
   (what you feed it)            (what it does)               (what comes back)

  ┌────────────────────┐                                  ┌────────────────────┐
  │ 1. A CLAIM         │                                  │ 1. A VERDICT        │
  │   "Region X is     │     ┌───────────────────┐        │   PENDING →         │
  │    hyper-methylated│────▶│                   │───────▶│   LICENSED          │
  │    in disease Y"   │     │   RE-RUN THE TEST  │        │   (or stays PENDING)│
  ├────────────────────┤     │   TWO INDEPENDENT  │        ├────────────────────┤
  │ 2. THE DATA        │     │   WAYS, then ask:  │        │ 2. A RECEIPT        │
  │   a pointer to the │────▶│                   │───────▶│   tamper-proof proof │
  │   dataset (address)│     │  • do they AGREE?  │        │   of what was run   │
  ├────────────────────┤     │  • beat the BAR?   │        ├────────────────────┤
  │ 3. THE METHOD      │     │  • survive ATTACKS?│        │ 3. THE HONESTY #    │
  │   how to test it,  │────▶│  • fit the error   │───────▶│   q = "we expect    │
  │   ≥2 indep. recipes│     │    BUDGET?         │        │   ≤ q% of licensed  │
  ├────────────────────┤     │                   │        │   claims are wrong" │
  │ 4. THE BAR         │     └───────────────────┘        ├────────────────────┤
  │   the criterion it │────▶                             │ 4. THE 3D UNIVERSE  │
  │   must beat        │                                  │   live map of it all│
  └────────────────────┘                                  └────────────────────┘
```

**Four things in, four things out.** If you can hold that, you have the shape.

| In | What it really is |
|---|---|
| A claim | the assertion to be judged (starts `PENDING`) |
| The data | a content-addressed pointer (`dimnames_hash`), not the bytes |
| The method ×2 | ≥2 **independent** implementations (`AnalysisProfile` + adapters) |
| The bar | the stated criterion / severe test the claim must beat |

| Out | What it really is |
|---|---|
| A verdict | `PENDING` / `LICENSED` (and later maybe defeated / re-opened) |
| A receipt | content-addressed, attestable proof (`semantic_run_id`) |
| The honesty # | `q`, the expected false-license rate of the whole corpus |
| The universe | the live 3-D map (spectral eigenmap, streamed over SSE) |

---

## How they connect — the life of ONE claim

A claim is not checked once and forgotten. It **lives**.

```
            you submit it
                 │
                 ▼
            ┌─────────┐      passes the 4 checks
            │ PENDING │ ───────────────────────────▶ ┌──────────┐
            └─────────┘                               │ LICENSED │
                 ▲                                    └──────────┘
                 │                                      │      │
                 │  someone attacks it & wins           │      │  the data/method
                 │  (defeat → de-licensed,              │      │  underneath changes
                 │   alpha refunded)                    │      │  (drift → re-opened)
                 └──────────────────────────────────────┘      │
                 └───────────────────────────────────────────────┘
```

- Starts **PENDING** (unproven).
- Earns **LICENSED** only by passing all four checks at once.
- Falls back two ways: a winning **defeat** (a challenge it loses), or **drift**
  (the data/method it relied on moved, so its proof is stale and it must re-earn
  standing).

The thing nothing else does: **the verdict is never permanent — it is
continuously re-examined as the world changes.**

---

## The four checks (the machine's whole job)

A claim is LICENSED only when **all four** hold:

1. **AGREE** — two genuinely independent implementations get the same answer.
2. **BEAT THE BAR** — that answer clears a pre-stated criterion (a severe test).
3. **SURVIVE ATTACKS** — it withstands the corpus's defeat graph (grounded).
4. **FIT THE BUDGET** — it clears the live false-discovery-rate budget.

The deep idea: checks 1–4 are not four subsystems — licensing, defeat, drift,
and FDR control are **one mechanism** (an e-value updated up and down). That
unification is the flag the project plants.

---

## How it maps to the code (so it is not floating in the air)

```
  grammar   →   protocol   →   node   →   viewer
 "what a       "how a         "the         "the live
  claim IS"     claim earns    machine       3D map"
                standing"      that runs
                               the loop"
  (pure)        (pure)         (impure:      (Next +
                               data, clock,  Three.js)
                               network)
```

- **grammar** (`grammar/`) — the *shape* of claims, verdicts, defeats. Pure.
- **protocol** (`protocol/`) — the *rules* (the four checks, the lifecycle). Pure.
- **node** (`src/`) — the *running machine*; the only part touching real data,
  the clock, the network.
- **viewer** (`viewer/`) — the *window* onto the universe of claims, live.

---

## In one breath

Claims go in unproven, get independently re-run and judged against a bar, and
come out either earning a tamper-proof "licensed" stamp or not — and that stamp
stays alive, knocked back down if the claim is defeated or if the data drifts.
**In: claim, data, method ×2, bar. Out: verdict, receipt, honesty number, live map.**

---

## Positioning — how to describe it

The banner line: **a compiler and runtime for agentic science.** It's accurate,
but only with one bright line held in place.

- **Compiler** = the grammar. A claim is parsed into a typed IR and only
  "type-checks" — earns `LICENSED` — if it passes the gate. The twist: the
  "type-checker" is empirical **recomputation**, and the "type" is *earned
  epistemic standing*.
- **Runtime** = the protocol + node: the flywheel, daemons, and live loop that
  execute claims and maintain the corpus over time.

**The bright line: agents *propose*, recomputation *verifies*.**

- ✅ True as *clientele / why-now*: AI agents are first-class **producers** of
  claims, and the era they create (a flood of unverified science) is exactly the
  gap this fills.
- ❌ False as *mechanism*: the gate is **recomputation, not an LLM arguing** —
  that is the whole reason it does not degrade as models hallucinate. We are the
  **gate, not the generator.**

The strongest accurate framing (de Bruijn reframe): **the trusted runtime for
agentic science** — AI agents are *untrusted scaffolding* that propose claims; the
recomputation kernel is the only thing that lets the verified ones earn standing,
the way a memory-safe runtime safely runs untrusted programs.

When pressed, retreat one step to the durable truth: **the trust substrate for
empirical claims** — agentic science is the wedge and the why-now, but the
mechanism is recomputation, and it works for human science too.

### The "GitHub for science" bridge

A useful on-ramp, because the world it describes already exists: every biomedical
paper now ships a GitHub repo + a Zenodo/controlled-access dataset. That FAIR/
RO-Crate/DRS substrate is exactly what Arc 2 plugs into. But the phrase is a
**bridge, never the headline** — said unqualified it files you next to OSF,
Zenodo, Code Ocean, Papers with Code (which *are* "GitHub for science" in the
hosting sense).

What's right: content-addressed object model (like git's SHAs); rides the existing
repo+data+provenance world; a social/adversarial layer (attacks ≈ issues/PRs over
claims).

The two breaks — and they *are* the product:

1. **GitHub never verifies correctness, and the author controls the badge.** CI is
   opt-in, author-written, gameable; a green check means "the author's tests
   passed," not "this is true." Our inversion: the author **cannot confer
   standing** — verification is *mandatory*, *independent* (the air gap),
   *quantified* (e-value / q / FDR, not a binary badge), and *drift-aware*
   (it re-opens). **GitHub hosts; we adjudicate.**
2. **Repos are islands; our corpus is a connected web.** GitHub has no notion of
   "does repo A contradict repo B." The sheaf gauge + defeat graph are exactly that
   cross-claim global-consistency layer — no GitHub analog exists.

Unit difference: GitHub's unit is a repo/commit (the *materials*); ours is a claim
with earned standing (the *conclusion*, and whether it holds).

The bridge line: *"Every paper now ships a GitHub repo and a Zenodo dataset —
we're the layer none of those have: where a finding earns the right to be believed
by independent recomputation, verification is a live statistic not an
author-controlled badge, and the whole corpus is checked for global consistency.
GitHub hosts your science; we adjudicate it."* Which is just the compiler-and-
runtime framing again, sitting *on top of* the GitHub-for-science world rather than
competing with it.
