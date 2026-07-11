# The re-parameterization evaluator — reasoning about measurement-scale artifacts on REJECTED claims

**Date:** 2026-07-10
**Status:** Design brainstormed and **approved by user 2026-07-10** ("makes perfect
sense"). NOT yet built. Formal repo spec+plan were deferred once before (pivoted to
the SPC-demo universe scaling); this document is that deferred spec, written now.
Prompted by the MGMT→Temozolomide REJECTED result turning out to be a measurement-
scale artifact — see `docs/superpowers/notes/2026-07-10-parameterization-rejection-
reasoning.md`.

---

## 0. One-paragraph summary

A REJECTED claim is not automatically a trustworthy negative. Under the residue
taxonomy this project already ships, REJECTED is read as a morphospace **forbidden
region** — a high-confidence negative — but that reading is sound only when the claim
was tested over the *right* measurement space. The re-parameterization evaluator is a
post-verify harness component that, on a REJECTED claim, reasons about whether the
rejection is a genuine forbidden-region negative or an artifact of testing over the
wrong measurement space, and — if the latter — re-proposes the same subject over an
apt alternate space and re-tests it. In this project's terms, a **parameterization**
is *which measurement dimension of an SE-Contract a claim's plan reads* (gene-body
vs. promoter methylation are two dimensions over the same cell lines), so
"re-parameterize" means re-issuing the same claim (same marker/drug/criterion) with
its plan pointed at a different contract dimension. The worked motivating case is
MGMT→Temozolomide: gene-body-averaged methylation washes out the promoter-localized
MGMT-silencing signal that actually predicts temozolomide sensitivity, so the
REJECTED verdict over gene-body β-space is confounded by the wrong assay dimension,
not necessarily a genuine biological negative. Three decisions were approved for v1
— a hybrid LLM-plus-registry generator, declare-and-charge FDR over a pre-registered
alternate set, and REJECTED/`RejectionReason.REFUTED` as the sole v1 trigger — and
the whole mechanism is grounded in the same provenance-as-ontologically-prior
argument that Spec 1 (the accumulating universe store) establishes for modality: a
re-parameterization is a new provenance act, not a hack bolted onto the gate.

---

## 1. Foundations alignment

| Foundation | Requirement | How this design honors it |
|---|---|---|
| Measurement seam (`measurement-foundation.md` §2–§3, and its own note `2026-07-10-parameterization-rejection-reasoning.md`) | A criterion's truth must be invariant under the assay scale's admissible transformations; a claim evaluated over an ill-chosen assay dimension "measures encoding artifacts," and rigor below that seam manufactures false confidence. | The evaluator exists precisely because the note names a **false negative** produced this way: MGMT→TMZ rejected over gene-body β-space, when the mechanistically apt space is promoter β-space. Gene-body and promoter methylation are treated as **different measurement spaces**, not admissible transformations of one another — re-parameterization is a change of *space*, never a rescaling within one. |
| Morphospace forbidden-vs-unobserved (`measurement-foundation.md` §7, item 8; the same note) | Distinguishing "forbidden" (a genuine constraint) from "merely unsampled/mis-parameterized" is morphospace's classic weakness; Polymer's severity + defeat-graph machinery is asked to actually separate them rather than collapsing to occupied-vs-not. | The evaluator's whole purpose is exactly this discrimination: a REJECTED claim only counts as a trustworthy forbidden-region negative once it has been rejected over the *right* space. It does not weaken the existing REJECTED-as-forbidden-region reading; it adds the missing precondition. |
| de Bruijn kernel (`epistemology.md` §8) | Proposers — human, deterministic, or AI — are untrusted scaffolding; nothing earns standing except by passing the kernel. | The LLM in the hybrid generator (decision 1, §3) is a **pure proposer**: it reasons from the claim's asserted mechanism to a candidate measurement space, but it never confers standing and can never propose a space the harness has no data for — the measurement-space registry grounds it. Only `run_cycle`/`verify_stage`, unchanged, licenses the re-test. |
| e-value / online-FDR, pre-registration (`epistemology.md` §7) | `register_test` locks the e-LOND α-slot *before* the result is seen; post-hoc threshold shopping is exactly what pre-registration exists to kill; e-LOND controls FDR under arbitrary dependence because it does not assume independence, but it still requires the slots to be declared, not adaptively chased. | Decision 2 (§3), declare-and-charge: all K apt-available alternates are enumerated and **all K slots are pre-registered upfront**, before any of the K is tested. This is non-adaptive by construction — no peek-then-try-another fishing across alternates — and gives a clean, bounded FDR guarantee over the whole re-parameterization move, not just over each individual alternate test. |
| Residualism (`residualism.md` §7, "The Claims Engine"; "what is monotone is the audit trail, not the licensed set") | Un-licensed/rejected ≠ false; residue is demoted, never erased; a defeated or superseded claim's record persists. | The original REJECTED claim (over gene-body β-space) is **retained**, exactly as filed, per residualism. Each alternate is a **new, distinct claim** over a different space — never an edit or replacement of the original. Nothing about a successful re-parameterization deletes or overwrites the original's REJECTED status or its evidence trail. |
| Sheaf / Duhem consistency (`epistemology.md` §6, Place 1; `2026-07-07-duhem-consistency-fold-design.md`'s domain) | The sheaf-consistency gauge treats disagreeing claims over the same subject as a potential contradiction (an H¹ obstruction) unless a restriction map explains why they are not comparable. | The **reinterpret edge** (§4) is exactly that restriction-map-shaped explanation: it tells the sheaf/Duhem layer that "REJECTED over gene-body" and "LICENSED over promoter" are not a contradiction, because they are claims over two different measurement spaces, not two claims over the same stalk. Without the edge, the consistency layer would have no principled reason not to fire frustration between them. |
| Corpus / purity invariants (`GLOSSARY.md`; `epistemology.md` §7) | `Corpus` stays exactly 4 collections; grammar/protocol pure + numpy-free. | Everything in this design is umbrella-side, **with one flagged exception**: the reinterpret edge may require a small, additive grammar change if no suitable edge type exists yet (§4). This is called out explicitly as the one place this design is not purely umbrella-side, and it is scoped as additive (a new edge kind), never a change to the 4-collection shape of `Corpus` itself. |
| Compute boundary (`compute-boundary.md`) | Polymer specifies/orchestrates/witnesses/certifies; it does not become a hosted compute utility; provenance roots at ingestion. | The evaluator adds no new compute surface beyond what the existing gate already runs (an LLM call for proposal, then the standard `run_cycle` re-test). The promoter SE-Contract (a prerequisite, §6) roots its own provenance at ingestion exactly as `gdsc_pharmaco.py` does today. |

---

## 2. The telos

On a REJECTED, agreed-refuted claim, reason about whether the rejection reflects a
genuine forbidden region or an artifact of the measurement scale the claim was tested
over, and, where it is the latter, re-test the same subject over the apt assay space.

**What "re-parameterize" means here, precisely:** a **parameterization** is *which
dimension of an SE-Contract a claim's plan reads*. Gene-body-averaged methylation and
promoter-region methylation are two different dimensions available over the same
cell lines — two different columns/derivations off related but distinct measurement
spaces, not two views of one space related by an admissible transformation. To
**re-parameterize** a claim is to re-issue the *same* claim — same marker, same drug,
same criterion — with its evaluation plan pointed at a different contract dimension.
Nothing about the claim's subject or criterion changes; only which measurement space
its plan reads changes.

---

## 3. The three approved decisions

All three were user-chosen, and each was presented with a recommended option; the
recommended option was the one approved. None is second-guessed here.

### Decision 1 — Generator = HYBRID (LLM reasons, harness grounds)

An LLM (untrusted scaffolding, in the same trust position as `llm_adapter.py`)
reasons from the claim's **asserted mechanism** to the mechanistically apt
measurement space — e.g., "MGMT silencing is promoter-localized → the apt space is
promoter methylation." The harness then **intersects** that reasoning with a
**measurement-space registry**: the set of SE-Contract dimensions the system
actually has data for. The LLM proposes *which* space is apt; it never confers
standing, and it cannot hallucinate a space the registry does not know about,
because the registry is what actually grounds the proposal into something
testable. This is the de Bruijn separation applied here: generation stays
arbitrarily complex and heuristic; the registry-plus-gate stays small and grounding.

### Decision 2 — FDR = DECLARE-AND-CHARGE the alternate set upfront

Enumerate the **K** apt-and-available alternate spaces the hybrid generator surfaces
for a given rejected claim, and **pre-register all K** — charging all K e-LOND slots
— *before* any of the K alternates is actually tested. Only after all K slots are
locked does testing proceed. This is bounded and non-adaptive by construction: there
is no peek-at-one-then-decide-whether-to-try-another fishing expedition across the
alternate space. It gives a clean FDR guarantee over the whole re-parameterization
move, using the same pre-registration discipline (`register_test` locks `α` before
the result exists) the rest of the system already relies on.

### Decision 3 — Trigger = REJECTED / `RejectionReason.REFUTED` only, for v1

The evaluator fires only on claims that are `Status.REJECTED` with
`RejectionReason.REFUTED` (`grammar/src/polymer_grammar/status.py`) — i.e.,
"the data refuted it (terminal)," agreed-refuted by both independent legs. This is
the sharpest true-negative-vs.-mis-parameterization fork, and it is exactly the
MGMT case: both legs agree the effect fails the criterion over gene-body β-space,
which is precisely the situation where "genuinely forbidden" and "wrong assay
dimension" are hardest to tell apart and most consequential to get right. Later
extensions (flagged, not built for v1): under-powered PENDING claims; any
non-licensed claim generally. v1 deliberately does not attempt those — REFUTED is
the load-bearing case and the only one this design commits to.

---

## 4. Depth-1 and the reinterpret edge

**Depth-1 for v1.** A rejected ORIGINAL claim spawns its K alternates. If one of
those K alternates is *itself* rejected, it is **not** further re-parameterized in
v1 — the recursion is bounded to one level. Genuine multi-level recursion (an
alternate's rejection triggering its own re-parameterization search) is explicitly a
later extension, not part of this design.

**The reinterpret edge (load-bearing bookkeeping).** The original REJECTED claim
(tested over, e.g., gene-body β-space) is **retained exactly as filed** — this is
residualism, not an optional nicety. Each alternate is a **new, distinct claim**
over a **different** measurement space, linked to its parent by a **reinterpret
edge**: "re-parameterizes ⟨parent⟩ over ⟨promoter⟩." The edge's job is to tell the
sheaf/Duhem consistency layer that "REJECTED over gene-body" and "LICENSED over
promoter" (should the alternate license) are **not** a contradiction — they are
claims over different assay dimensions, not two claims over the same stalk that
disagree. The edge must suppress frustration between the two; it must not fire the
consistency machinery as though the corpus contains a straightforward contradiction.

**This may require a small, additive grammar change.** If no edge type currently
captures "these two claims are about different measurement spaces and therefore not
in tension" (as opposed to defeat or equivalence, which both presuppose comparability
over the same stalk), the reinterpret edge is a new, versioned, additive meta-tier
addition to the grammar — the foundations already list "protocol pushes back on
grammar" as a pending category this can fall into. This is flagged explicitly as the
one place this design is not purely umbrella-side. Everything else — the generator,
the registry, the FDR bookkeeping, the depth-1 bound — is umbrella-side.

---

## 5. LLM as pure untrusted proposer

The LLM in the hybrid generator (Decision 1) occupies exactly the trust position
`epistemology.md` §8 names for every proposer in this system: it proposes candidate
measurement spaces from the claim's asserted mechanism; the measurement-space
registry grounds the proposal against what data actually exists; and only the
standard gate (`run_cycle`/`verify_stage`) confers standing on whatever gets tested.
The LLM never earns standing for a claim by reasoning well about mechanism — it only
ever narrows *which* re-test to run. If it reasons badly (proposes a mechanistically
implausible space, or one the registry does not recognize), the worst outcome is a
wasted registered slot or no candidate at all — never a false license.

---

## 6. Ontological grounding

Re-parameterization is not a hack bolted onto the gate; it is grounded in the same
ontology Spec 1 (`2026-07-10-accumulating-universe-store-design.md`) establishes for
modality. Modality has two moments — a CHOICE (a provenance act, ontologically
prior) and a REALIZED FACT (pinned on the SE-Contract). Re-parameterization **is** a
new instance of the CHOICE moment: an agent (here, the hybrid generator, grounded by
the registry) **re-chooses** the modality/measurement-space a claim's plan reads.
The parameterization choice lives in the claim's provenance; the re-parameterization
evaluator's job is to **read** that provenance (what space was chosen, and why it
may have been wrong) and **revise** it (propose a new choice); the reinterpret edge
is what **records** that revision in the corpus. This is what makes the move
ontologically clean rather than an ad hoc "try again with different data": it is the
same provenance-as-ontologically-prior structure Spec 1 already establishes,
exercised a second time on the same subject.

---

## 7. Prerequisites (shared with Spec 1)

Two things must exist before the evaluator can be proven against the real MGMT→TMZ
case, though the evaluator itself can be built and unit-tested on synthetic
two-space contracts *before* either lands:

- **(0) A promoter-methylation SE-Contract.** Lift
  `Hack/data/master/methylation_promoter_bycosmic.csv.gz` / CCLE RRBS TSS-1kb data
  as a second contract dimension, alongside the existing gene-body-averaged contract
  built by `ingest/gdsc_pharmaco.py`. This is also the standing "lift promoter
  methylation" follow-up named in the parameterization-rejection note.
- **(1) The measurement-space registry** — the set of available SE-Contract
  dimensions per assay, keyed so the hybrid generator's harness-side grounding step
  (Decision 1) can intersect an LLM's mechanistic proposal against what data
  actually exists. **This registry is shared with Spec 1** (the accumulating
  universe store): it is the same structure that lets a facet/census query ask
  "which measurement spaces does this subject have claims over," read from the
  evaluator's side as "which measurement spaces are available to re-parameterize
  into." One registry, two consumers.

The evaluator's mechanism (trigger → hybrid generation → declare-and-charge →
re-test → reinterpret-edge bookkeeping) can be built and unit-tested against
synthetic contracts with two or more fabricated measurement spaces before either
prerequisite lands. The *proof* — does MGMT→TMZ actually reinterpret correctly and,
ideally, license — needs the real promoter data.

---

## 8. The honest risk

Re-parameterizing MGMT→TMZ over promoter methylation is the *correct move* — the
mechanism is genuinely promoter-localized, and testing it over gene-body-averaged
methylation is a genuine measurement-scale error. But **whether it then licenses is
an open empirical question**, not a guaranteed outcome. Cell-line TMZ AUC in the GDSC
data is compressed near 0.98 — there may simply not be enough dynamic range left in
the drug-response readout for even a mechanistically apt promoter signal to clear
the licensing bar. The evaluator's value is in the **reasoning and the honest
re-test** — correctly distinguishing "rejected because wrong space" from "rejected
because genuinely negative," and then actually re-testing rather than asserting —
not in guaranteeing a flip from REJECTED to LICENSED. A re-parameterized claim that
is *also* rejected, over the correct space this time, is itself a valuable and more
trustworthy result: it upgrades a possibly-confounded forbidden-region reading into
an actually-trustworthy one.

---

## 9. Build order

1. **Promoter-methylation SE-Contract** (§7, prerequisite 0).
2. **The measurement-space registry** (§7, prerequisite 1) — shared with Spec 1.
3. **The evaluator itself**: trigger (REJECTED + `RejectionReason.REFUTED`) → hybrid
   generator (LLM proposes, registry grounds) discovers the K apt-available
   alternates → declare-and-charge (pre-register all K slots) → re-test each via the
   unchanged gate → reinterpret-edge bookkeeping (retain the original, link each new
   alternate claim, suppress false sheaf/Duhem frustration).

---

## 10. Testing strategy

Behavior, not implementation; the mechanism can be exercised entirely on synthetic
fixtures before the real promoter lift exists.

- **Trigger scoping.** Only claims with `Status.REJECTED` and
  `RejectionReason.REFUTED` fire the evaluator; claims REJECTED for
  `DEFEAT_GROUNDED_OUT`, `ROBUSTLY_BLAMED`, or `HYPOTHESIS_ALTERED`, and any
  non-REJECTED status, do not.
- **Hybrid generation, grounded.** On a synthetic claim whose asserted mechanism
  names a space the registry does not contain, the generator proposes zero
  candidates (or an explicit "no apt-available alternate" result) — it must not
  fabricate a space. On a synthetic claim whose mechanism names a space the
  registry *does* contain, the generator proposes it.
- **Declare-and-charge, non-adaptive.** All K slots are locked before any of the K
  alternates is tested; a test asserts the harness cannot register slot *k+1* after
  having already seen the result of slot *k* (no adaptive peeking).
- **Depth-1 bound.** A synthetic alternate that is itself REJECTED with
  `RejectionReason.REFUTED` does not spawn a second-generation re-parameterization
  search in v1.
- **Reinterpret edge and residualism.** After a successful re-parameterization
  (regardless of whether the alternate licenses), the original REJECTED claim is
  still present in the corpus, unmodified, with its original status and evidence
  trail intact. The reinterpret edge exists between original and alternate. A
  sheaf/Duhem consistency check over a fixture containing both a REJECTED original
  and a LICENSED alternate, linked by the reinterpret edge, does **not** fire
  frustration; the same fixture *without* the edge is used as a contrast case to
  confirm the edge is actually load-bearing for the suppression.
- **The MGMT case, data-gated.** On the real (gitignored) promoter contract,
  MGMT→Temozolomide re-parameterized over promoter β-space produces *some* outcome
  (license or a second REJECTED, over the correct space) — marked slow/data-gated,
  run behind whatever extra gates the promoter contract lands under, excluded from
  core CI. This test asserts the mechanism runs correctly end-to-end on real data;
  it does **not** assert the outcome is a license (per §8, that is explicitly open).

---

## 11. Open questions / deferred

- **Whether the reinterpret edge needs a grammar change**, and if so its exact
  shape — deferred to implementation time, once it is clear whether an existing
  edge kind can be repurposed or a genuinely new one is needed (§4).
- **Recursion beyond depth-1** — a rejected alternate spawning its own
  re-parameterization search — is a later extension, not v1.
- **Triggers beyond REJECTED/`REFUTED`** — under-powered PENDING claims, and
  eventually any non-licensed claim — are named as later work, not v1.
- **The measurement-space registry's own design** is shared with, and partially
  deferred to, Spec 1 (`2026-07-10-accumulating-universe-store-design.md`) — this
  spec assumes it exists and is queryable, but does not itself specify its schema.

---

## See also

- `[[project_polymer_reparameterization_evaluator]]` — the source memory this spec
  renders.
- `[[project_polymer_universe_organization]]` — modality's two moments,
  provenance-prior; the ontological grounding in §6 depends on it directly.
- `docs/superpowers/specs/2026-07-10-accumulating-universe-store-design.md` — Spec
  1; shares the measurement-space registry (§7) and supplies the "re-parameterization
  = a provenance operation" framing this spec exercises.
- `docs/superpowers/notes/2026-07-10-parameterization-rejection-reasoning.md` — the
  worked MGMT→TMZ example that prompted this design.
- `docs/superpowers/foundations/measurement-foundation.md` — the parameterization
  seam and the forbidden-vs-unobserved morphospace weakness this evaluator resolves.
- `[[feedback_flag_engine_gaps]]`, `[[project_polymer_spc_demo]]`.
