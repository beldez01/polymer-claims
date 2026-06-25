# Polymer Claims — Grounding Sufficiency & The Build Path

**Status:** Strategic plan / sequencing brief. v1.0
**Date:** 2026-06-21
**Author:** Z. Belden (synthesis at peak project context)
**Purpose:** Mark the moment the theoretical grounding became *sufficient*, name the
critical path that now de-risks everything, and convert the vision into a concrete,
sequenced build — with explicit "do not build yet" boundaries.

### Relationship to the other docs

Downstream of and consistent with `docs/superpowers/2026-06-12-phase-2-north-star.md`
(the technical-philosophical charter) and
`docs/superpowers/2026-06-16-linchpin-thesis-three-layer-arc.md` (the commercial
arc). This document is the **sequencing layer**: given the charter, the arc, and the
foundations work in `docs/superpowers/foundations/`, what to nail, what to defer, and
what to build first. It adds nothing to the worldview; it commits to an order.

---

## 0. The pivot: grounding is now sufficient — the risk has inverted

Up to this point the project's risk was *insufficient rigorous grounding*. As of the
foundations work (`MAP.md`, `epistemology.md`, `measurement-foundation.md`,
`scaled-infrastructure.md`), that risk is closed. **The risk now flips to its
opposite: theory as procrastination.**

> **Stop deepening the theory. It is good enough to build on. Further grounding has
> sharply diminishing returns against the one thing that actually de-risks the whole
> vision — the kernel licensing one real claim, on real public data, with an honest
> `q` and a real independence check.**

Every seductive open thread (the measurement-theory language, morphospace, the
bio-DSL) is now correctly *named and parked*. Re-opening them before the critical
path is closed is the procrastination trap wearing an intellectual costume.

---

## 1. The critical path (the one proof that de-risks everything)

> **The kernel licenses *one real claim* on *real public data*, end to end, with a
> real independence check and an honest `q`, emitted as a shareable certificate.**

Everything aspirational — Layer A substrate, epistemic underwriting, the AML twin,
the universe at scale — is *amplification* of that single event. If it works, you
have a linchpin seed. If it doesn't, no amount of vision matters. Build toward this
and nothing above it.

---

## 2. Theoretical grounding — what's still worth nailing, what to stop

Four points, priority order.

### 2.1 The one genuinely missing piece: `q`-calibration *(add this)*
Every doc makes `q` the headline metric and currency (NS; Linchpin §1, §6.2). None
answers *how you know `q` is calibrated.* "We expect ≤ `q`% of LICENSED claims to be
false" is an empirical promise that must be *checkable*: claims that later resolve,
against which the realized false rate is compared to the stated `q`. Today `q` is
asserted by the FDR math, not validated against ground truth. The Linchpin's entire
"epistemic underwriting / rating agency" ceiling rests on `q` being *earned*. A
calibration loop is the missing grounding — and it outranks the measurement
language.

### 2.2 Operationalize independence — the load-bearing unsolved thing *(nail this)*
NS §E and Linchpin §8 both name it as *the* risk: "a confident lie is worse than no
`q`," and the infra review found it under-specified. If one more concept gets nailed
before/within the build, make it the **common-cause / shared-cause check** —
minimally, concretely, for the methylation legs and cross-cohort. The code already
has the hook (`cohorts_error_independent` in `src/polymer_claims/replication.py`).
This is the difference between the wedge being real and being a beautiful
self-deception. It outranks measurement theory and morphospace on the critical path.

### 2.3 Keep the measurement-foundation OFF the critical path *(validate, don't wire)*
`docs/superpowers/foundations/measurement-foundation.md` §3.1 already elevated
"meaningful = invariant at the seam" to a *licensing precondition*. That is an
**unvalidated architectural commitment.** Do not wire it into the grammar yet.
Instead:
- run the planned adversarial cross-check, prioritizing §7.1 (the regress objection);
- do the methylation β-space worked example as a **time-boxed spike**, not production.

Promote it to foundational *only* if it survives both. Otherwise you commit the exact
slippage you feared, one level up: rigor built on an elegant-but-wrong foundation.

### 2.4 Park morphospace and the bio-language *(named vision, build neither)*
Correctly placed in the foundations docs as the generative payoff / future direction.
Leave them there. Re-opening now is procrastination.

### 2.5 Doc-corpus housekeeping *(low effort, high coherence)*
The doc set is now substantial and minor drift exists (the infra doc under-links to
the Linchpin arc). Add a one-page `docs/superpowers/foundations/README.md`: canonical
reading order + each doc's altitude **and status** (charter / strategy /
proposal-under-review / endgame-vision). Keeps the set coherent for the cross-check
reviewer and future-you.

---

## 3. The build path (against the docs we have)

The docs already converge: **the Linchpin's Layer C *is* the strategy's single-player
tool.** Build that, nothing above it.

### Build sequence
1. **Real-data swap** — synthetic betas → real GEO / TCGA-LAML. The Linchpin calls
   this "literally the repo's current next-phase brief"; the overview's honest-status
   flags it as the gap between *exercised* and *earned*. Highest-leverage step: it
   turns the recomputable-public tier real. **First.**
2. **Independence hardening** (per §2.2) — make the common-cause check real for the
   two methylation legs + cross-cohort; gate the e-value product on low overlap. This
   is what makes step 1's `q` honest rather than a confident lie. **Inseparable from
   step 1** — real data without this produces a dishonest `q`, which is worse than
   synthetic.
3. **Single-player surface + the certificate** — a CLI/tool: point at a claim + data
   → licensed / withheld + `q` + an attestable certificate. The **certificate is the
   spreadable social object** (the GitHub-badge / arXiv-link equivalent from the
   strategy work). Build only this.
4. **One legible wedge claim** — toward the Linchpin's strongest artifact (the AML
   epistemic twin, C1+C2+C3), but the *minimal* version is one variant or biomarker
   claim, real data, earned license, certificate. Make one thing a person can look at.

### Do NOT build now (name the seduction)
- The entire `scaled-infrastructure.md` — that is **Layer A, the endgame, built
  last.** Vision, not sprint.
- The measurement-theory language / morphospace machinery — validate, don't build
  (§2.3–2.4).
- Auth, multi-tenant, federation, the standards skin beyond what the wedge needs.

### Process / rhythm
The repo already encodes the right loop (`CONTINUE.md`, `plans/`, `specs/`), and the
NS prescribes it: **brainstorm → spec → plan → subagent-driven build, with TDD.** The
grammar/protocol are pure and deterministic — a gift for TDD; lean into it. Immediate
move: a tight written plan for steps 1–2, executed test-first.

---

## 4. Why this sequencing is correct (mapping back)

- **Linchpin arc:** this is **Layer C (Wedge)**. "Stage C needs no one else." Layer A
  (the infra doc) is the endgame; the standards-adoption chicken-and-egg does not
  bite until the gate is proven alone.
- **Strategy precedents:** single-player value first (GitHub/HuggingFace/arXiv); the
  certificate is the spreadable unit; **do not build the commons first** — that is the
  graveyard (nanopublications, ORKG, the Underlay). The corpus accretes from
  single-player use; it is never launched.
- **De Bruijn / honesty invariants:** the wedge keeps the kernel tiny and the impurity
  umbrella-side; `q` is reported, not hidden — which is *why* §2.1 (calibration) and
  §2.2 (independence) are non-negotiable before the certificate means anything.

---

## 5. The immediate next action

Write the plan for **step 1 + step 2** (real-data swap + minimal independence check) —
they are inseparable. That single plan, executed test-first, reaches the
critical-path proof in §1.

### Guardrails to carry into the build
- `q` must be **calibrated, not asserted** — design step 1 so a calibration loop is
  possible later (§2.1).
- Independence is **load-bearing and unsolved** — a dishonest `q` discredits
  everything (§2.2).
- The measurement foundation is **a proposal under review**, not adopted — do not let
  it shape the schema until validated (§2.3).

---

## 6. One-paragraph version

The theory is sufficient; the risk is now procrastination. The single proof that
de-risks the entire vision is the kernel licensing one real claim on real public data
with an honest, independence-checked `q`, emitted as a shareable certificate. Get
there via the Linchpin's Layer C / the strategy's single-player tool: swap synthetic
betas for real GEO/TCGA-LAML data and harden the common-cause independence check
(inseparable), then wrap it as a CLI that emits the certificate, then make one wedge
claim legible. Do not build Layer A, the measurement language, or morphospace yet —
validate the first, park the rest. Add a `q`-calibration story and operationalize
independence, because without them the certificate is a confident lie. Next concrete
move: write and execute the step 1+2 plan, test-first.
