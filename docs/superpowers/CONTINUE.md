# ⟳ Polymer Claims — RESUME HERE

> Hook-loaded continuity file (a SessionStart hook surfaces it). **Keep the *Current state* + *NEXT*
> sections current at every phase boundary.** Detailed build history lives in git (`git log --oneline`),
> the per-slice specs (`docs/superpowers/specs/`) and plans (`docs/superpowers/plans/`). One-page
> architecture map: `ARCHITECTURE_CURRENT.md`. Reserved terminology: `GLOSSARY.md`.

---

## Current state (2026-06-15)

`main` ALL GREEN — **226 umbrella + 351 grammar + 363 protocol + 2 isolation**; viewer `tsc`+build
clean; `scripts/check-all.sh` green. grammar/protocol pure + numpy-free; **Corpus = 4 collections**;
local-only. (Procrustes embedding alignment — spectral as the live node layout — just merged; §2E
tiered independence + reinstatement→PENDING + n-DMPs-at-FDR before it — see NEXT.)

The system is a **compiler + runtime for science**: grammar (*what a claim is*) → protocol (*how a
corpus evolves* — the `run_cycle` flywheel + 3 daemons + scheduler) → umbrella node/server
(`NodeRunner` + FastAPI SSE) → viewer (live 3D topology). The epistemic core is now **e-value native**:
licensing, the FDR ledger, and defeat are ONE mechanism —
`LICENSED ⇔ adapter-agreement ∧ SATISFIED ∧ grounded ∧ live e-LOND discovery`, and a successful defeat
de-licenses *through the ledger* and refunds the discovery. The methylation demo licenses on a
**computed** region-Δβ (synthetic betas — see caveat) with full content-addressing (dataset +
apparatus), running live in the node.

**Standing caveats (carry forward):**
- Methylation betas are **synthetic** — the BENCHMARKED/recomputable tier is *exercised, not earned*.
  Real public GEO data is a self-contained swap (identical `load_contract` seam). [menu item 6]
- `semantic_run_id` is the **Python** digest; an R-parity golden fixture is deferred (needs an R
  serializer). [menu item 7]
- Adapter independence is **operator-asserted** (`implementation_hash` is a supplied string compared
  with `!=`); byte-derived hashing + credential provenance on `Satisfaction` still open. [roadmap 1c]
- The two methylation adapters are **reproducibility-independent, not error-independent** (same estimand,
  same data) → the single-cohort demo licenses at **REPRODUCED**. **§2E now expresses the stronger tier:**
  a claim reproduced across two cohorts with distinct `dimnames_hash` licenses at **REPLICATED** (the
  cross-cohort independence that error-decorrelates). The REPLICATED demo runs on a **2nd synthetic
  cohort** (`epicv2_casectrl_demo_b`) — still exercised, not earned, until a real 2nd cohort is swapped in.

## ▶ NEXT (concrete plan)

**✅ PROCRUSTES EMBEDDING ALIGNMENT DONE (2026-06-15, branch `procrustes-embedding-alignment`, local-only).**
The signed-Laplacian spectral eigenmap is now the **live `NodeRunner` default layout** (was a static
snapshot only), orthogonal-Procrustes-aligned each frame to the previous displayed frame so the universe
grows smoothly instead of thrashing on eigenbasis sign/rotation ambiguity. New `embedding.procrustes_align`
(orthogonal R, reflection allowed — sign-flips ARE the reflections we undo — **no det-correction**; 6dp
round). `NodeRunner(layout="spectral"|"force")`: spectral default lazy-imports the embedder (base import
stays numpy-free) and threads a `_prev_spectral` alignment chain via the protocol's existing
`export_topology(positions=)` seam (`layout_id="external:spectral-v1"`); **`layout="force"` is byte-identical**
to the prior Fruchterman-Reingold path. Graceful fallback to force (warn once) when `[embed]`/numpy absent.
`serve --layout {spectral,force}` (default spectral). Protocol untouched + numpy-free; Corpus = 4.
**Design tradeoff (documented):** the small default `serve` seed never grows a ≥4-node component, so it
never reaches the eigenmap — spectral won't look smoother there (lattice/scale churn, which Procrustes
can't fix); `--layout force` is the escape hatch. The anti-thrash mechanism (raw≈2.70 → aligned≈1.27) and
the `make_spectral_timeline.py` demo run on a **growing ≥4-node component** (planted `c0_*` cluster revealed
one claim at a time) where the alignment provably applies. **Deferred (still):** UMAP / content features
(embedding spec §8); offline `export_timeline` stays force-directed (protocol purity — it can't compute the
spectral embedding). Spec `docs/superpowers/specs/2026-06-15-procrustes-embedding-alignment-design.md`,
plan `docs/superpowers/plans/2026-06-15-procrustes-embedding-alignment.md`.

**✅ §2E TIERED INDEPENDENCE DONE (2026-06-14, branch `feat/2e-tiered-independence`, local-only).**
`IndependenceTier` {REPRODUCED, REPLICATED} as an additive `Licensing.independence_tier` field (default
REPRODUCED → byte-identical back-compat) + pure `independence_tier_of` keying on distinct
`materialization.dimnames_hash`. A claim reproduced across **≥2 cohorts with distinct datasets** licenses
at **REPLICATED**, and its e-LOND test uses the **product** `e₁·e₂` — **ONE** test/discovery, no α-budget
double-count. Umbrella `replication.py` (`build_replication_inputs`) air-gaps a 2nd synthetic cohort
(`epicv2_casectrl_demo_b`) and emits the extra satisfaction + product e-value; protocol threads an additive
`run_cycle(replications=)` (default None → byte-identical) and stamps the tier. Demo: powered cohort A +
`demo_b` → REPLICATED (product e≈80k ≫ e-LOND bar); single-cohort stays REPRODUCED; same-cohort doesn't
multiply. grammar/protocol pure + numpy-free; Corpus = 4. **Deferred follow-ups:** viewer REPLICATED
badge; live-node (`NodeRunner`) `replication_map` wiring; byte-derived `implementation_hash` +
credential provenance (roadmap 1c). Spec `docs/superpowers/specs/2026-06-14-2e-tiered-independence-design.md`,
plan `docs/superpowers/plans/2026-06-14-2e-tiered-independence.md`.

**✅ REINSTATEMENT → PENDING DONE (2026-06-14, branch `feat/reinstatement-pending`, local-only).** The
symmetric counterpart to Phase 2.2's defeat-as-de-license. New grammar `RejectionReason`
{DEFEAT_GROUNDED_OUT, REFUTED, ROBUSTLY_BLAMED} + additive `Claim.rejection_reason` (one-directional:
reason ⟹ REJECTED) + `PendingReason.REINSTATED`. VERIFY/INTEGRATE stamp the rejection cause (refutation
takes precedence); a reinstatement block in INTEGRATE mirrors the `flipped_out` de-license — a defeat-
rejected claim that grounds-IN again (its attacker fell) reopens to **PENDING** to **re-test** on current
data (never auto-relicense; has-plan gated). No new tombstone (its e-LOND test was already retracted at
defeat; Phase-2.4 dedup grants a fresh one). The correctness guard holds: a REFUTED claim sitting in the
grounded `in_set` is NOT reopened. grammar/protocol pure + numpy-free; Corpus = 4; back-compat (dormant
unless a defeat-rejected claim flips in). `ROBUSTLY_BLAMED` is reserved (the Duhem-blame path has no
protocol consumer yet). Spec `docs/superpowers/specs/2026-06-14-reinstatement-pending-design.md`, plan
`docs/superpowers/plans/2026-06-14-reinstatement-pending.md`.

**✅ n-DMPs-at-FDR DONE (2026-06-14, branch `feat/n-dmps-at-fdr`, local-only).** The second methylation
reduction (alongside region-Δβ): the **count of differentially-methylated probes** (a probe is a DMP iff
its per-probe two-group pooled t-test p < α) licenses on a new **one-sample count-enrichment e-value**
(`count_enrichment_evalue`, a WSR/Ville betting e-value testing H0: per-probe DMP-rate ≤ p0=α — the
"binomial-tail" e-value). Two independent legs (`NDmpTTestAdapter` manual pooled-t vs `NDmpOlsCoefAdapter`
numpy-lstsq OLS-coef t) **agree on the integer count** → air-gap. Pure-Python Student-t p-value (incomplete
beta, no scipy). **Umbrella-only** (new `methyl_ndmp.py`; `_load_betas` extracted from `methyl_adapters`;
`evidence_map` dispatches on impl) — grammar/protocol untouched, base import numpy-free, Corpus = 4. Demo
(powered fixture, all 24 probes): **10 DMPs → REPRODUCED license** (e≈164 ≫ e-LOND bar); the null/control
region (0 DMPs, e=1.0) is **REJECTED** (money-shot); same-owner pair held PENDING. Single-cohort; n-DMPs as
a REPLICATED second reduction is a §2E follow-up. Spec `docs/superpowers/specs/2026-06-14-n-dmps-at-fdr-design.md`,
plan `docs/superpowers/plans/2026-06-14-n-dmps-at-fdr.md`.

Next safe slices (decision-ready menu, `docs/superpowers/2026-06-13-overnight-deferred-analysis.md`):

1. **§2E follow-ups** — the viewer REPLICATED badge + live-node `replication_map` wiring, when wanted.
   (Now also: the viewer spectral-layout follow-ups deferred above — UMAP / content features.)
2. **n-DMPs as a REPLICATED second reduction** — run the n-DMP count on a second cohort and multiply the
   two count-enrichment e-values (combines §2E's REPLICATED machinery with the new reduction). ~1 slice.
3. **ROBUSTLY_BLAMED wiring** — wire the Duhem robust-blame REJECTED verdict into the protocol and stamp
   it (tiny; the enum value is reserved). Optional/legibility.

**Deferred / blocked-on-external (supervised):** real-public-data swap (point me at a GEO/ENA dataset);
Python/R hash parity (needs the R side); standards-skin attestation JSON (in-toto/SLSA/DRS
serialization — the safe first slice of the north-star "standards" arc). Literal per-attack e-value
combination is **largely a mirage** — Phase 2.2 already caught its sound core; don't build a generic
combination.

Rhythm: `superpowers:brainstorming` (2–3 forks → spec → plan) →
`superpowers:subagent-driven-development` → merge `--no-ff` → update this file + memory.

## Done — checklist (git has the detail; SHAs for spelunking)

**Grammar** (`polymer_grammar`) — complete, all 8 phases:
- ✅ L0–L4: sum-typed leaf · status lifecycle · 6-axis Pareto strength · Proposition + defeasible
  Equivalence · L2 licensing bridge · typed causal roles + Dimension algebra · L3 VAF defeat graph +
  Duhem blame · L4 AGM/TMS revision
- ✅ Phase 7 protocol-imposed fields: provenance · governance · online-FDR ledger · subject slot ·
  `representation_revision` meta-tier
- ✅ Phase 8 evaluator: typed compute-graph IR + air-gapped `verify()` (≥2 distinct adapter identities)

**Protocol runtime** (`polymer_protocol`) — complete, 5 sub-projects + 3 daemons + scheduler:
- ✅ #1 Corpus + assessment spine (`c8b7279`) · #2 oracle dossier (`a61d7dd`) · #3a/#3b SELECT pursuit
  engine + QD/heterodox/Goodhart/accumulating-belief (`03ae863`/`4293faf`) · #4a/#4b GENERATE proposer
  bus + provisional links + executable rivals + intelligent-operator seam
  (`5d7899f`/`64b8042`/`8e0bba0`/`7c7a953`)
- ✅ #5 daemons: DRIFT (`ce107b9`) · ORACLE-VALIDATION + F2 fix (`ea517c7`) · REPRESENTATION RED-TEAM
  (`9996e49`) · #5d loop-economics scheduler (`7e1d5c9`)

**Umbrella + product:**
- ✅ `pip install polymer-claims` CLI + live local node (`NodeRunner` + FastAPI SSE, `[serve]` extra) +
  3D viewer (Next 16 / React Three Fiber; sample + live modes), verified in-browser
- ✅ Real LLM generation adapter (`[llm]` extra) driving the live node (`serve --llm`)

**External audit — CLOSED** (`polymer-claims-audit.md`):
- ✅ Tier A+B (`c662f1c`): bounded frame retention · tick-serialization lock · bounded SSE queues ·
  non-loopback bind guard · machine-clean JSON · `ARCHITECTURE_CURRENT.md` + `GLOSSARY.md` · v1.2 frozen
  banners
- ✅ Adapter trust registry (`67f98e3`) — the independence gate (registry core done; byte-hash +
  credential-provenance hardening still open, see caveat)
- ✅ Tier-C (`2b7ccb5`): viewer `CONTRACT_VERSION` + 6-axis strength validator · `run_cycle` output
  revalidation · packaging metadata

**Credibility arc + CES** (`docs/superpowers/roadmaps/2026-06-11-credibility-arc-roadmap.md`):
- ✅ M1 structural-equivalence status (`Status.STRUCTURAL` — no more false LICENSED on structural
  collapse) · earned-strength · relational graph embedding v1 (signed-Laplacian eigenmap, silhouette 0.62)
  · live spectral layout (`procrustes-embedding-alignment`) — eigenmap as the live `NodeRunner` default,
  Procrustes-aligned per frame; `serve --layout`; force path byte-identical (see NEXT for detail)
- ✅ CES-0 analysis-profile content-address · CES-1 data seam · CES-2 methylation Δβ licensing ·
  CES-3 content-address completeness · CES-4 live wiring

**Phase 2 — epistemic core** (north star: `docs/vision/2026-06-12-phase-2-north-star.md`):
- ✅ 2.1 e-value / FDR / VERIFY unification (`6960100`) — e-LOND (FDR under arbitrary dependence) +
  Waudby-Smith-Ramdas betting e-value + the hard 4-way VERIFY gate
- ✅ 2.2 defeat-as-e-value-update + alpha-wealth refund (`eef6143`) — `FDRTest.retracted` tombstone;
  defeat de-licenses through the ledger
- ✅ Audit remediation (`3241c8d`) — fixed a CRITICAL cross-cycle duplicate-FDR-entry bug (one e-test
  per claim lifetime)
- ✅ 2.3 live e-gate (`a8ab596`) · 2.4 drift-reopen tombstone + live-dedup (`bb619f1`)
- ✅ §2E tiered independence (`feat/2e-tiered-independence`) — REPRODUCED / REPLICATED; product e-value
  across independent cohorts as one e-LOND test; 2nd synthetic cohort demo (see NEXT for detail)
- ✅ Reinstatement → PENDING (`feat/reinstatement-pending`) — `RejectionReason` marker + INTEGRATE
  reinstatement block; a defeat-rejected claim reopens to re-test when its attacker falls (symmetric to
  Phase 2.2); refuted claims stay terminal (see NEXT for detail)
- ✅ n-DMPs-at-FDR (`feat/n-dmps-at-fdr`) — second methylation reduction; per-probe-significant DMP count
  licenses on a one-sample count-enrichment betting e-value; two pooled-t legs agree on the count
  (air-gap); umbrella-only (see NEXT for detail)

## Invariants / working agreements (don't relearn)

- `grammar/` must NEVER import `polymer_formalclaim` (enforced by `grammar/tests/test_isolation.py`);
  `protocol/` depends one-way on `grammar/` (isolation-tested).
- `grammar/` + `protocol/` are **pure/deterministic + numpy-free** (no clock/random/IO; time-like inputs
  are passed in). The ONLY impurity is the umbrella node/server. **`Corpus` = exactly 4 collections**
  (claims, defeat_edges, equivalences, fdr_ledger).
- All models subclass `_Model` (frozen, `extra="forbid"`); **collections are tuples** (deep immutability
  + content-addressing). No `dict`/`list` fields on models.
- New cross-cutting fields land **additive/optional** (`X | None = None`) with a present-only-when-Y
  validator. Opt-in features default to byte-identical behavior when off.
- numpy lives behind the umbrella `[embed]` extra; `embedding.py` / `methyl_adapters.py` are NOT
  re-exported, so base import stays numpy-free.
- Tests: per-package `uv run pytest -q` + `uv run ruff check src tests`; full gate `scripts/check-all.sh`.
  TDD: failing test first.
- Merge to `main` `--no-ff`, **local-only** — commits are NOT pushed to origin (flagged account; no
  active CI; `check-all.sh` is the substitute).

## Reference pointers

- **Forward plan / decision menu:** `docs/superpowers/2026-06-13-overnight-deferred-analysis.md`
- **Phase-2 north star:** `docs/vision/2026-06-12-phase-2-north-star.md`
- **Credibility-arc roadmap:** `docs/superpowers/roadmaps/2026-06-11-credibility-arc-roadmap.md`
- **Architecture map:** `ARCHITECTURE_CURRENT.md` · **Glossary:** `GLOSSARY.md`
- **Spectral layout guides:** `docs/spectral-layout-how-to-use.md` (usage) ·
  `docs/spectral-layout-how-it-works.md` (eigenmap + Procrustes math/theory)
- **Memory:** `project_polymer_claims_knowledge_protocol` (full phase history + follow-ups)
- **Deep design source:**
  `~/Desktop/Research/topics/epistemic-claim-foundations/generative-protocol/_FINAL_knowledge_generation_protocol.md`

## Open follow-ups (tracked, non-blocking)

- **Adapter-independence hardening** (roadmap 1c): byte-derived `implementation_hash` + credential
  provenance on the frozen `Satisfaction`.
- **Earned-strength 2d:** `evidence_against_null` from a real test statistic with n (now partly
  subsumed by the e-value gate).
- **I2 / I1:** `grounded_extension` ~O(N³) worklist rewrite + untrusted-corpus ingestion size/depth
  bounds (only bites with large untrusted corpora — federated layer).
- **Vector leaves** (`QuantityVectorLeaf`): a DMP is vector-valued; scalar reduction is an honest
  simplification until a claim needs the full vector.
- **Card/viewer value display** for `stats::mean_diff` plans (computed value + ✓✗ only populated for
  `builtin::const` today).
- **Multi-dataset drift** (CES-4 single-world `current` → per-claim) · per-frame viewer drift annotation
  ("knowledge breathing").
- **User-gated:** PyPI publish · polymerbio.org viewer integration · federated / BYO-compute
  (`POST /inject` hook).
