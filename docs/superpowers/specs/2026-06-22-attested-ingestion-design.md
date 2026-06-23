# ATTESTED Ingestion (the credence layer) — Design Spec

**Status:** Design / draft for review. v0.1
**Date:** 2026-06-22
**Author:** Z. Belden (brainstormed with Claude)
**Roadmap:** calibration follow-up **slice 4/5** (`docs/superpowers/plans/` + the in-session roadmap
`.claude/plans/cozy-growing-naur.md`). Slices 1,2,3,5 shipped; this is the last and deepest.

> **One line.** Let **external determinations** about a LICENSED claim's standing enter the
> calibration ledger as the **ATTESTED** tier — recorded as *defeasible corpus claims*, typed by
> *resolvability*, feeding a `q_attested` disagreement rate that is **never** the headline `q`. The
> first concrete realisation of the North-Star §5 credence layer and the linchpin §6.2 *epistemic
> underwriting* thesis.

---

## 0. Where this sits

The calibration ledger (shipped 2026-06-22) has three warrant tiers. DEFINITIONAL (realized FDR vs
constructed truth — the only headline-`q` feeder) and ANCHORED (warrant survival under the corpus's
own pressure) are wired. **ATTESTED was a schema stub** — fields exist (`attestation_ref`,
`source_claim_id`), `_attested_stat` aggregates a disagreement rate, but **no code ever creates an
ATTESTED `ResolutionRecord`.** This slice builds the ingestion.

## 1. The epistemic frame (load-bearing — the foundations, not invented here)

`q` is never calibrated against a single "ground truth" (`foundations/epistemology.md` §3:
external-authority resolution smuggles in a *foundationalist oracle the project disclaims*;
internal-verdict resolution is *coherentist tautology*). The discipline is **measure and label the
warrant, never assert truth.** ATTESTED therefore obeys three hard rules:

1. **Defeasible, never oracle.** An external determination is *testimony*, not truth. It is
   recorded as a **defeasible corpus claim** (decision below), can be attacked/defeated through the
   gate, and is **never superior to ANCHORED**.
2. **Never the headline `q`.** Only DEFINITIONAL realized-FDR may be the headline (the
   `feeds_headline_q` computed property already enforces this; the renderer keeps ATTESTED under
   the "warrant stability / field calibration" heading). This slice must not weaken that.
3. **Typed by resolvability** (North-Star §5 credence layer): *resolvable* claims (a definitive
   later determination is possible) will admit **proper scoring** against a baseline; *unresolvable*
   ones fall to **Surrogate Scoring Rules / peer-prediction** over graph-neighbours. Markets only
   where claims resolve; avoid token economies; scores private until resolution. **This slice
   records the typing; it does NOT build the scoring engines** (they need baselines/peer-predictions
   we do not have yet).

### 1.1 Resolvability — operator-declared (authoritative), with a structural prior

The foundations contain no resolvability *taxonomy*. `epistemology.md` §1–2 gives a related but
**distinct** principle worth not conflating: the **L0 empirical anchor + recomputation is the
foundationalist tether** — a claim is *recomputably decidable* when it carries a content-addressed
test (a non-None `evaluation_plan`, the signal DRIFT keys on). **But recomputability ≠ credence-sense
resolvability.** Every LICENSED claim is recomputable (the gate licensed it by recomputation), yet
whether a *definitive external verdict will ever arrive* (a confirmatory trial, a ClinVar
reclassification) is a fact about the **external world**, not the claim's structure. Marking
everything recomputable as "resolvable" would defeat the typing.

So the honest design: **resolvability is operator-declared and authoritative** (it is a judgment
about whether the external world will deliver a verdict — exactly the kind of thing the project's
"label the warrant, don't infer" discipline says to *declare*, and which is itself defeasible since
the attested event is a claim). When the operator does **not** declare it, fall back to a
**structural recomputability prior**:

> `resolvability_prior(claim)` = **resolvable** iff `claim.evaluation_plan is not None` (a
> recomputable test exists, so a definitive determination is at least *possible*), else
> **unresolvable**. This is a **prior/default, not a definition** of resolvability — an explicit
> operator value always wins.

Mechanically: operator value if present, else the structural prior. (The credence-sense distinction
only *bites* once the scoring engines land — §11 — so this slice records the typing correctly now
and routes it later.)

## 2. Decisions (settled this session)

- **Scoring depth:** MVP = file ingester + resolvability typing + `q_attested` disagreement rate.
  Proper-scoring (resolvable) and surrogate/peer-prediction (unresolvable) engines are **deferred**.
- **Defeasible link:** **wire attested-as-corpus-claim now** — each attested event becomes a real,
  defeasible corpus claim; the ATTESTED `ResolutionRecord.source_claim_id` points at it.
- **Resolvability:** operator-declared and authoritative; a structural recomputability **prior**
  (`evaluation_plan` present → resolvable) fills in only when the operator does not declare. Note
  the recomputability ≠ resolvability distinction (§1.1).
- **First source:** a file-based operator/authority ingester (no external feed exists). Live
  feeds (ClinVar API, trial registries) are a later slice.

## 3. Components & flow

```
resolutions file ──▶ attested_ingest.py ──▶ (a) build an attested-event CLAIM per row, inject into
(operator/authority)   (umbrella, impure)        the corpus (defeasible, non-LICENSED)
                                            ──▶ (b) derive resolvability (structural default | override)
                                            ──▶ (c) build an ATTESTED ResolutionRecord (source_claim_id
                                                    = the attested-event claim) → append to the ledger
                                            ──▶ (d) write the updated corpus
                       ingest-attested CLI ─┘
certificate ──▶ q_attested (+ resolvability counts) under the field-calibration heading (never headline)
```

| Piece | Location | Purity |
|---|---|---|
| `Resolvability` enum + `resolvability` field on `ResolutionRecord` | `protocol/src/polymer_protocol/calibration.py` | **Pure** (additive, attested-only) |
| Resolvability prior `resolvability_prior(claim) -> Resolvability` | `protocol/.../calibration.py` (reads `claim.evaluation_plan`) | **Pure** |
| Resolutions-file parse + validate + attested-event-claim build + ledger append | `src/polymer_claims/attested_ingest.py` (new) | **Impure** (filesystem) |
| `ingest-attested` CLI | `src/polymer_claims/cli.py` | **Impure** |
| Certificate render (resolvability counts) | `src/polymer_claims/attestation.py` | **Impure** |

## 4. The resolutions file (operator/authority input)

A JSON array of resolution objects (validatable, round-trippable; a TSV adapter is a follow-on):

```json
[
  {
    "subject_claim_id": "region-iDH-hyper-001",
    "verdict": "failed",
    "attestation_ref": "doi:10.1056/NEJMoa2026xxxx",
    "resolvability": "resolvable",        // optional — overrides the structural default
    "observed_at_cycle": 412,             // optional — default: the corpus's current/max cycle, else 0
    "license_epoch": 0                    // optional — which licensing episode (default 0)
  }
]
```

- `subject_claim_id` (req) — the LICENSED claim whose standing the external authority assessed.
- `verdict` (req) — `upheld` (external determination **agreed** with our license) | `failed`
  (**disagreed** — the claim turned out wrong externally). `q_attested` = failed / (failed+upheld).
- `attestation_ref` (req) — the external reference (DOI / URL / ClinVar VCV / registry id).
- `resolvability` (opt) — operator override; else derived from the subject claim (§1.1).
- `observed_at_cycle`, `license_epoch` (opt) — defaults as noted.

Validation: `subject_claim_id` must exist and be (or have been) LICENSED in the corpus; `verdict` ∈
{upheld, failed}; unknown fields rejected (mirror `extra="forbid"`).

## 5. Attested-as-corpus-claim (the defeasible link)

For each resolution, the ingester **creates an attested-event claim** and injects it into the corpus,
then sets `source_claim_id` to it. This is what makes the external determination *defeasible* rather
than an oracle.

- **Shape (existing grammar primitives only — no new grammar types):** an L0 **Proposition** leaf
  claim asserting *"external authority `attestation_ref` determined that LICENSED claim
  `subject_claim_id` is `verdict`"*, with `Provenance` recording the external ref and an
  `EXTERNAL_ATTESTATION` origin. Content-addressed id (deterministic from subject+verdict+ref).
- **Injected via the existing untrusted-proposal seam** (`compile_untrusted` / the injection path)
  so it is **forced non-LICENSED** — an attested event cannot forge a license (trust-boundary C2:
  *licensing is minted only by verify*). It enters as an asserted, defeasible claim that lives in
  the corpus and defeat graph; a later contradicting attestation can attack it.
- **Resolvability** is read from the **subject** claim (the thing whose standing is attested), not
  the attested-event claim.

> Open build-time detail: the exact Proposition/pattern construction for an attested-event claim
> (which pattern id, leaf shape, provenance fields) — pin against the grammar at spec-review/plan
> time. The umbrella builds it; grammar/protocol stay pure + additive.

## 6. The pure model changes (additive)

- New enum `Resolvability(str, Enum)` = `resolvable | unresolvable`.
- New optional field `resolvability: Resolvability | None = None` on `ResolutionRecord`
  (present-only-when `kind == attested`; validated like the other kind-coupled fields).
- `resolvability_prior(claim) -> Resolvability` — pure: `resolvable` iff `claim.evaluation_plan is
  not None`, else `unresolvable`. A **fallback prior**, used by the ingester only when the operator
  does not declare resolvability (which is authoritative).
- `_attested_stat` unchanged for the headline number (`q_attested` = disagreement rate) but gains
  `n_resolvable` / `n_unresolvable` counts on the tier (additive `TierStat` fields) so the
  certificate can show the typing split. **Still never feeds headline `q`.**

## 7. CLI

`polymer-claims ingest-attested --corpus PATH --resolutions FILE --calibration LEDGER [--out CORPUS]`
- reads + validates the resolutions file; for each row: derive resolvability, build + inject the
  attested-event claim, build the ATTESTED `ResolutionRecord` (`source_claim_id` set), append to the
  calibration ledger; write the updated corpus (`--out`, else stdout).
- Deterministic; additive; no network.

## 8. Certificate

`q_attested` already renders under the "warrant stability / field calibration" heading. This slice
adds the resolvability split (`N resolvable / N unresolvable`) and the disclosure that ATTESTED is
*external testimony recorded as defeasible claims*, never truth. The headline `q` is untouched.

## 9. Testing (TDD)

**Pure (`protocol`):** `resolvability_prior` (evaluation_plan present → resolvable; absent →
unresolvable); the `resolvability` field validator (attested-only); `_attested_stat` resolvability
counts + `q_attested` unchanged; ATTESTED still cannot be `feeds_headline_q`.
**Umbrella:** resolutions-file parse/validate (good + malformed); the attested-event claim is built,
injected, and is **non-LICENSED** (cannot forge a license); `source_claim_id` links correctly;
operator override beats the structural default; ledger append + fold; `ingest-attested` CLI smoke;
certificate render shows ATTESTED under field-calibration (never headline) with the resolvability
split.

## 10. Invariants

Additive / byte-identical when unused (no resolutions file → no ATTESTED records, certificate
unchanged). `Corpus` stays 4 collections. Calibration is an instrument, not a gate (the
attested-event claim is *defeasible corpus content*, but it does **not** change any other claim's
licensing status). Anti-laundering preserved (ATTESTED never headline). grammar/protocol stay pure +
numpy-free (the new pure pieces are an enum, a field, and a structural predicate). The attested-event
claim is forced non-LICENSED by the untrusted-proposal seam.

## 11. Deferred (the credence-layer north star)

- **Proper scoring** for resolvable claims (log-score vs a community/prior baseline; needs a
  baseline source).
- **Surrogate Scoring Rules / peer-prediction** for unresolvable claims over graph-neighbours (the
  highest-leverage unexploited mechanism; the corpus graph is the correlation structure).
- **Live external feeds** (ClinVar API, trial/registry ingestion) replacing the file drop.
- **Markets** only where claims genuinely resolve; **epistemic underwriting** (`q` as an insurable,
  attested-trail actuarial quantity — linchpin §6.2).
- TSV input adapter; richer `observed_at_cycle`/epoch resolution against the live ledger.

## 12. References

- `docs/superpowers/2026-06-12-phase-2-north-star.md` §5 (credence layer), §2(C) (credence-primary)
- `docs/superpowers/foundations/epistemology.md` §1–3 (the anchor/recomputation tether; resolvability)
- `docs/superpowers/2026-06-16-linchpin-thesis-three-layer-arc.md` §6.2 (epistemic underwriting)
- `docs/superpowers/specs/2026-06-22-calibration-ledger-and-certificate-design.md` §1 (warrant tiers,
  anti-laundering), §7 (certificate)
- Existing substrate: `protocol/.../calibration.py` (`ResolutionRecord`, `_attested_stat`),
  `src/polymer_claims/calibration_store.py`, `src/polymer_claims/attestation.py`, the
  `compile_untrusted` injection seam.
