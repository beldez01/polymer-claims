# The credibility arc — next-steps roadmap (ranked by scientific credibility)

> **✅ ESSENTIALLY COMPLETE (reconciled 2026-06-13).** Tier 1 + Tier 2 shipped: **M1** ✅, **CES-1 →
> CES-2** ✅, **CES-3** ✅ (and CES-0 apparatus + CES-4 live wiring beyond this roadmap). The arc was
> then **superseded by the Phase-2 epistemic core** (e-values / e-LOND FDR / defeat-refund — north star
> `docs/vision/2026-06-12-phase-2-north-star.md`), which is the deeper version of the "beat a criterion"
> leg. **Only carry-forwards from this roadmap:** **1c** adapter-independence hardening (byte-derived
> `implementation_hash` + credential provenance on `Satisfaction` — still operator-asserted) and **2b**
> earned-strength-2d (now largely subsumed by the e-value gate). The live forward plan is
> `docs/superpowers/2026-06-13-overnight-deferred-analysis.md`.
>
> **Status:** roadmap, 2026-06-11. NOT an implementation plan — it surveys the open threads as of
> CES-0-complete and sequences them by one ranking lens: *what makes the system's core claim true*.
> Each slice follows the standard rhythm: `superpowers:brainstorming` (2–3 questions → spec → plan) →
> `superpowers:subagent-driven-development` → merge no-ff → memory. Builds on the COMPLETE grammar
> (8 phases + oracle dossier + provisional edges), the COMPLETE protocol runtime (#1–#5d), the live
> node/server/viewer, and the CES-0 `AnalysisProfile` content-address apparatus (merged 2026-06-10).

## The credibility thesis

The system's core claim is:

> **LICENSED means two independent implementations agreed that a real, fully-pinned analysis beat a
> pre-registered criterion.**

That sentence has four load-bearing words. Each currently has a gap where the claim is not yet fully
true. The whole arc below is ordered to close them.

| Word | What it must mean | Current gap (verified in code, 2026-06-11) |
|---|---|---|
| **real** | computed from actual data | licenses run on LLM-asserted `builtin::const` values or the toy `dose_response.csv` — no real methylation betas yet |
| **fully-pinned** | every analytical choice content-addressed | Layer-C R internals + the design formula escape the SemanticRunID hash (CES audit §2); the `AnalysisProfile` hash is not yet bound into `MaterializationContext` |
| **independent** | two genuinely different implementations | independence is *operator-asserted* — `AdapterCredential.implementation_hash` (`adapter_registry.py:19`) is a supplied string compared with `!=` (`:47`), not derived from adapter bytes |
| **beat a criterion** | passed an evidential test | `canonicalize` mints `EquivalenceClaim(status=LICENSED, severity=1.0)` from a structural-key collapse with **no evidential test** (`canonicalize.py:78`); earned strength is margin-over-threshold, not a test statistic (`earned_strength.py` — its own comment: "recalibrate against real test statistics (with n) in the 2d arc") |

## Tier 1 — make "licensed" honest (the core invariant)

### 1a. M1 — stop minting LICENSED without a test (build FIRST: small, independent) ✅ DONE 2026-06-11

> **✅ DONE (2026-06-11, branch `feat/m1-structural-equivalence-status`, local-only).** Added
> `Status.STRUCTURAL` ("true by construction; not an evidential license"), fenced it out of `Claim`
> (a new `_structural_only_on_equivalence` validator), broadened `equivalence_class`'s back-compat IN
> gate to `{LICENSED, STRUCTURAL}`, and changed `canonicalize.py:78` to mint `STRUCTURAL`. The
> false-license path is closed: no path mints a `LICENSED` equivalence without an evidential test.
> Additive only — Corpus stays 4, viewer/topology contract untouched (`STRUCTURAL` never appears as a
> node status). 333 grammar + 335 protocol + 94 umbrella green; ruff clean; `check-all.sh` ALL GREEN.
> Spec `docs/superpowers/archive/specs/2026-06-11-structural-equivalence-status.md`, plan
> `docs/superpowers/plans/2026-06-11-structural-equivalence-status.md`.

**Seam:** `protocol/src/polymer_protocol/canonicalize.py:53–86`.

`canonicalize` collapses structurally-identical claims into an `EquivalenceClaim(status=LICENSED,
severity=1.0, note="structural-key collapse")`. The structural identity is real, but stamping it
`LICENSED` overloads the exact word the evidential pipeline *earns* through `verify_stage`. Under the
core invariant this is a false-license path: a `LICENSED` edge that never passed a criterion.

**Fix:** give structural equivalences their own non-LICENSED status (a new `Status.STRUCTURAL`, or
keep them `CONJECTURED` with `severity=1.0`) so "structurally identical" and "evidentially licensed"
stop sharing a label. Cheap, removes the false-license path, sharpens the invariant for everything
downstream. **Highest credibility-per-effort — do it first; it is independent of the CES arc.**

**Open fork for the brainstorm:** new `Status` value vs. reuse `CONJECTURED` — decide whether
consumers (grounded extension, viewer color map, `equivalences` semantics) need to distinguish a
*known* structural identity from an *unverified* conjecture. The viewer contract (`CONTRACT_VERSION`)
moves if a new status enters the `TopologyExport`.

### 1b. CES-1 → CES-2 — real-data execution (the spine)

The documented next action, and the single most credibility-load-bearing arc: until it lands,
**real** is unproven. Buildable entirely inside `polymer-claims` with bundled fixtures — **no live
analysis engine required, no external research directory dependency** (the local-first seam was chosen
precisely so this arc is self-contained).

- **CES-1 (B1) — `DataHandle` → SE-Contract ref. ✅ DONE 2026-06-11.** `DataHandle.ref` stays a thin
  `str` (zero grammar change) and resolves umbrella-side to a frozen, DRS-shaped, content-addressed
  `SEContractRef`; bundled EPICv2-shaped methylation fixture (manifest + sidecar betas, **synthetic**
  values with a planted shift for CES-2) + `load_contract` realizer; canonical `dimnames_hash` via a
  shared `canonical_sha256` helper. Data seam only — no computation/licensing. 116 umbrella tests,
  check-all ALL GREEN. Spec `docs/specs/2026-06-11-ces-1-data-seam-design.md`, plan
  `docs/superpowers/plans/2026-06-11-ces-1-data-seam.md`.
- **CES-2 (minimal B2) — one tool, one profile, one claim licenses on real betas.** ✅ DONE 2026-06-12 (licenses on computed Δβ; tier cap + air gap fire; synthetic-data caveat). A local
  `BorisLikeAdapter` computes one **scalar reduction** (region Δβ, or n-DMPs at FDR<0.05) under a
  pinned `AnalysisProfile`, over the CES-1 fixture, with a **methodologically-independent second
  leg** (a different tool, same pinned profile + dataset). The claim licenses on the **computed
  value**, not an asserted one. This is the payoff: the first claim whose LICENSED means "real
  analysis beat the criterion."

**Scope fence (Fork C, already decided):** scalar reduction only for the first slice; a true
`QuantityVectorLeaf` is deferred (Tier 3). `ProducedLeafSpec`/`Leaf` are scalar-only today
(`operations.py:50–75`), so the scalar reduction is buildable now; vector output is a grammar
expansion.

### 1c. Adapter-independence hardening (co-developed with CES-2's second leg)

**Seam:** `protocol/src/polymer_protocol/adapter_registry.py`; the air-gap gate in `verify_stage`;
the frozen `Satisfaction` in `grammar/`.

CES-2 forces this, because for the first time there are two *real* adapters whose independence
actually matters (not two stdlib stand-ins). Two slices:

1. **Byte-derived implementation hash** — replace the operator-asserted `implementation_hash` string
   with a hash computed from adapter implementation bytes, so `adapters_independent` checks real
   lineage divergence, not a claimed one.
2. **Credential provenance on the `Satisfaction`** — record the agreeing credential IDs on the minted
   `Satisfaction` itself (today the gate consults the registry and the credential identities vanish).
   This is the "heavier IR provenance" deferred at #5; it makes "two independent implementations
   agreed" auditable after the fact, not just enforced at the moment of licensing.

**Note:** slice 2 touches the frozen `Satisfaction` (an additive optional field) — confirm the
grammar `CONTRACT_VERSION` / viewer mirror implications in the brainstorm.

## Tier 2 — make "licensed" mean the *full* thing

### 2a. CES-3 — close the content-address (depends on CES-2) ✅ DONE 2026-06-12

**Seam:** `MaterializationContext` (`licensing.py:28–32`); the drift key (`drift.py`); the
substrate→`ValidationTier` cap (the `#2 oracle_cap` seam + CES-0's `profile_oracle_registry`).

Wire the `AnalysisProfile` content hash into `MaterializationContext.semantic_run_id`, fold the
profile hash into the DRIFT freshness key, and bind substrate→tier cap. This closes the Layer-C hash
gap the CES audit found: without it, two "identical" licensed runs can silently diverge on an R
default or a design-formula change. This is the **fully-pinned** leg — a license now content-addresses
*the whole apparatus*, not ⅔ of it.

> **✅ DONE (2026-06-12, branch `feat/ces-3-content-address-completeness`, local-only).** License records `dimnames_hash` + `profile_hash` + `semantic_run_id` on `MaterializationContext`; drift re-opens a LICENSED claim on any content-address move (`dimnames_hash` OR `profile_hash` changed); back-compat for const-plan / pre-CES-3 claims (tighten-only-when-present). The CES B1→B3 spine is complete.

### 2b. Earned-strength 2d — real test statistics (depends on CES-2 outputs)

**Seam:** `protocol/src/polymer_protocol/earned_strength.py`; the selective-inference bar in
`verify_stage`.

Today a license's *strength* is margin-over-threshold (`_sat(x)=1−exp(−K·rel_margin)`,
`_EVIDENCE_SHAPE_K=8.0`), an honest heuristic but **not a p-value with n**. With CES-2 producing real
limma/BH outputs, enrich `evidence_against_null` to derive from the actual test statistic and sample
size. Makes the **strength axis** honest, not only the licensed/not-licensed bit. The module already
flags this as the intended 2d recalibration.

## Tier 3 — expressiveness & deferred (lower under the credibility lens)

These do not create false-license paths; they limit expressiveness or matter only off the science
critical path. Explicitly **out of scope** for this arc, listed so the deferral is deliberate, not
forgotten:

- **Vector leaves (`QuantityVectorLeaf`).** A DMP is intrinsically vector-valued; scalar reduction is
  an *honest* simplification, so this is expressiveness, not a credibility gap. Defer until a claim
  genuinely needs the full vector (Fork C, later phase).
- **I2 / I1 hardening** — `grounded_extension` ~O(N³) fixpoint worklist rewrite + untrusted-corpus
  ingestion size/depth bounds; defense-in-depth cardinality cap. Credibility-neutral; only bites when
  accepting large *untrusted* corpora. Defer until the federated/BYO-compute layer.
- **Card/viewer value display** — `claim_detail.criterion_satisfied` + the computed value are only
  populated for `builtin::const` plans, so a `stats::mean_diff` card shows impl + criterion +
  rationale but not the computed value / ✓✗. Legibility, not credibility. A small viewer/endpoint
  follow-up (worth doing right after CES-2 so the real-data licenses are *watchable*, but it does not
  gate the science).
- **PyPI publish, polymerbio.org viewer integration, federated / BYO-compute** — orthogonal to the
  science under this lens. Each is user-gated and tracked elsewhere (`ARCHITECTURE_CURRENT.md`
  "user-gated / future").

## Recommended critical path

```
M1 (1a) ───────────────────────────────────────────┐   (independent, do first)
                                                    │
CES-1 (1b) ──► CES-2 (1b) ──► CES-3 (2a)
                   │   └─────► earned-strength-2d (2b)
                   └────────► adapter-independence (1c)   ← co-developed with CES-2's 2nd leg
```

1. **M1 first** — small, independent, sharpens the invariant immediately; nothing waits on it.
2. **CES-1 → CES-2** — the main arc; the first license on real methylation betas.
3. **Adapter-independence (1c)** — sibling of CES-2 (CES-2 needs two real adapters anyway).
4. **CES-3 + earned-strength-2d** — once real computation exists, make the license *fully* pinned and
   the strength *real*.
5. Everything in Tier 3 waits.

## Anchored file map (for the next implementer)

- **M1:** `protocol/src/polymer_protocol/canonicalize.py:53–86`; `grammar/src/polymer_grammar/`
  status enum; `viewer/` status color map + `CONTRACT_VERSION`.
- **CES-1/2:** `grammar/src/polymer_grammar/operations.py` (`DataHandle`, `OperationNode`,
  `ProducedLeafSpec`); `src/polymer_claims/{analysis_profile.py,profiles.py,exec_adapters.py,datasets/}`;
  a new local SE-Contract fixture + realizer in the umbrella package.
- **1c:** `protocol/src/polymer_protocol/adapter_registry.py`; `verify_stage`; `grammar/` `Satisfaction`.
- **CES-3:** `grammar/src/polymer_grammar/licensing.py` (`MaterializationContext`);
  `protocol/src/polymer_protocol/{drift.py,oracle.py}`; `src/polymer_claims/analysis_profile.py`.
- **2b:** `protocol/src/polymer_protocol/earned_strength.py`; `verify_stage`.

Reference inputs already in-repo: the CES architecture audit (`docs/specs/2026-06-10-ces-architecture-audit.md`),
the CES-0 spec (`docs/specs/2026-06-10-ces-0-analysis-profile-design.md`), the earned-strength
follow-up note (`docs/superpowers/notes/2026-06-08-earned-strength-followup.md`), and the closed
external audit (`polymer-claims-audit.md`).
