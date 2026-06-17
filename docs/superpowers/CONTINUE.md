# ⟳ Polymer Claims — RESUME HERE

> Hook-loaded continuity file (a SessionStart hook surfaces it). **Keep the *Current state* + *NEXT*
> sections current at every phase boundary.** Detailed build history lives in git (`git log --oneline`),
> the canonical spec (`docs/superpowers/polymer-claims-canonical-spec.md`), the per-slice plans
> (`docs/superpowers/archive/plans/`), and the archived per-feature design specs (`docs/superpowers/archive/specs/`).
> One-page architecture map: `ARCHITECTURE_CURRENT.md`. Reserved terminology: `GLOSSARY.md`.

---

## Current state (2026-06-15)

`main` ALL GREEN — **226 umbrella + 351 grammar + 363 protocol + 2 isolation**; viewer `tsc`+build
clean; `scripts/check-all.sh` green. grammar/protocol pure + numpy-free; **Corpus = 4 collections**;
local-only. (Procrustes embedding alignment — spectral as the live node layout — just merged; §2E
tiered independence + reinstatement→PENDING + n-DMPs-at-FDR before it — see NEXT.)

What the system *is* — the full architecture (grammar → protocol → node → viewer; the e-value-native
epistemic core; real computation + CES) — lives in the canonical spec
**`docs/superpowers/polymer-claims-canonical-spec.md`**. This file tracks **state + what's next**, not the
design.

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

**Recently shipped** (most recent first, all 2026-06-14/15, local-only): Procrustes / live-spectral layout
· §2E tiered independence (REPRODUCED / REPLICATED) · reinstatement → PENDING · n-DMPs-at-FDR. SHAs +
one-line summaries in the *Done* checklist below; design rationale in `docs/superpowers/archive/specs/`.

**▶ RECOMMENDED NEXT PHASE — the real-data swap (from *exercised* to *earned*).** The rigor core is
built; its central proof still runs on **synthetic betas**. Swapping in a real public methylation cohort
is the single highest-leverage move — it retires the #1 caveat and is the keystone for the standards skin.
Dataset is **chosen (TCGA-LAML HM450, GDC open-access, IDH1/2-mut vs WT)** and it's the designed-in next
step (identical `load_contract` seam), ready for brainstorm → spec → plan. Full path + dataset +
acceptance: **Phase A of `docs/superpowers/2026-06-16-autonomous-hypothesis-loop.md`** — the forward
roadmap (Phase A is the swap; B–D build the autonomous agent loop on top of it). Natural encore: a 2nd
real cohort → the §2E **REPLICATED** gold tier.

Other safe slices (the historical decision menu is archived at `docs/superpowers/archive/2026-06-13-overnight-deferred-analysis.md`):

1. **§2E follow-ups** — the viewer REPLICATED badge + live-node `replication_map` wiring, when wanted.
   (Plus the viewer spectral-layout follow-ups — UMAP / content features.)
2. **n-DMPs as a REPLICATED second reduction** — run the n-DMP count on a second cohort and multiply the
   two count-enrichment e-values (combines §2E's REPLICATED machinery with the new reduction). ~1 slice.
3. **ROBUSTLY_BLAMED wiring** — wire the Duhem robust-blame REJECTED verdict into the protocol and stamp
   it (tiny; the enum value is reserved). Optional/legibility.

**Deferred / blocked-on-external (supervised):** Python/R hash parity (needs the R side);
standards-skin attestation JSON (in-toto/SLSA/DRS
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

**Credibility arc + CES** (`docs/superpowers/archive/roadmaps/2026-06-11-credibility-arc-roadmap.md`):
- ✅ M1 structural-equivalence status (`Status.STRUCTURAL` — no more false LICENSED on structural
  collapse) · earned-strength · relational graph embedding v1 (signed-Laplacian eigenmap, silhouette 0.62)
  · live spectral layout (`procrustes-embedding-alignment`) — eigenmap as the live `NodeRunner` default,
  Procrustes-aligned per frame; `serve --layout`; force path byte-identical (design rationale in archive/specs/)
- ✅ CES-0 analysis-profile content-address · CES-1 data seam · CES-2 methylation Δβ licensing ·
  CES-3 content-address completeness · CES-4 live wiring

**Phase 2 — epistemic core** (north star: `docs/superpowers/2026-06-12-phase-2-north-star.md`):
- ✅ 2.1 e-value / FDR / VERIFY unification (`6960100`) — e-LOND (FDR under arbitrary dependence) +
  Waudby-Smith-Ramdas betting e-value + the hard 4-way VERIFY gate
- ✅ 2.2 defeat-as-e-value-update + alpha-wealth refund (`eef6143`) — `FDRTest.retracted` tombstone;
  defeat de-licenses through the ledger
- ✅ Audit remediation (`3241c8d`) — fixed a CRITICAL cross-cycle duplicate-FDR-entry bug (one e-test
  per claim lifetime)
- ✅ 2.3 live e-gate (`a8ab596`) · 2.4 drift-reopen tombstone + live-dedup (`bb619f1`)
- ✅ §2E tiered independence (`feat/2e-tiered-independence`) — REPRODUCED / REPLICATED; product e-value
  across independent cohorts as one e-LOND test; 2nd synthetic cohort demo (design rationale in archive/specs/)
- ✅ Reinstatement → PENDING (`feat/reinstatement-pending`) — `RejectionReason` marker + INTEGRATE
  reinstatement block; a defeat-rejected claim reopens to re-test when its attacker falls (symmetric to
  Phase 2.2); refuted claims stay terminal (design rationale in archive/specs/)
- ✅ n-DMPs-at-FDR (`feat/n-dmps-at-fdr`) — second methylation reduction; per-probe-significant DMP count
  licenses on a one-sample count-enrichment betting e-value; two pooled-t legs agree on the count
  (air-gap); umbrella-only (design rationale in archive/specs/)

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

- **Forward roadmap:** `docs/superpowers/2026-06-16-autonomous-hypothesis-loop.md` · historical decision menu (archived): `docs/superpowers/archive/2026-06-13-overnight-deferred-analysis.md`
- **Phase-2 north star:** `docs/superpowers/2026-06-12-phase-2-north-star.md`
- **Credibility-arc roadmap:** `docs/superpowers/archive/roadmaps/2026-06-11-credibility-arc-roadmap.md`
- **Architecture map:** `ARCHITECTURE_CURRENT.md` · **Glossary:** `GLOSSARY.md`
- **Spectral layout guides:** `docs/spectral-layout-how-to-use.md` (usage) ·
  `docs/spectral-layout-how-it-works.md` (eigenmap + Procrustes math/theory)
- **Memory:** `project_polymer_claims_knowledge_protocol` (full phase history + follow-ups)
- **Deep design source:**
  `~/Desktop/Research/topics/epistemic-claim-foundations/generative-protocol/_FINAL_knowledge_generation_protocol.md`

## Open follow-ups (tracked, non-blocking)

- **Context-separation / pre-ship scrub (Option 3).** The TET2-vs-WT methylation example (the author's
  separate research) is removed from the live code AND genericized in the historical CES docs (case/control,
  `pinned_design` profile; local R-pipeline paths + the real cross-reactive digest stripped) — 2026-06-15.
  **Still to do before any public release** (external users won't have this content): genericize the remaining
  **Polymer Genomics / Boris / PlumberClient** integration references in the CES design docs; strip the
  `~/Desktop/Research/topics/epistemic-claim-foundations/...` design-source absolute paths cited across the
  protocol specs + this file; and scrub the v1.2 plugin/corpus fixtures that name other research projects
  (e.g. `Polymer_Evolution`). None affect the running system — pure documentation/context hygiene.
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
