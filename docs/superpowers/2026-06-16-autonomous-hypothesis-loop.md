# Autonomous data→claims loop — overall plan (arc decomposition)

**Date:** 2026-06-16 · **Status:** concept plan for cross-checking (pre-spec, pre-implementation)
**Purpose:** Lay out the whole concept — *a user with underlying data assets gets an autonomously-
generated, gate-tested claims universe* — decomposed into buildable phases with dependencies, grounded
in what already exists, so it can be reviewed/cross-checked before we spec the first phase.

> This is an **overall plan**, not an implementation plan. No code yet. The terminal step is to pick
> one phase and run it through the normal brainstorm → spec → plan → subagent-driven rhythm.

> **Status as of 2026-06-21 — partially superseded.** Phase A (real TCGA-LAML n-DMP at REPRODUCED) shipped. The integrity layer described in Phase D (pre-registration ledger, shared-cause gate, §E common-cause REPLICATED machinery) also shipped, ahead of B/C. Phase B/C (methylation hypothesizer, asset catalog) had first slices, but the project pivoted to the north-star living-universe arc (`docs/superpowers/2026-06-12-phase-2-north-star.md`), anchored by the linchpin (`docs/superpowers/2026-06-16-linchpin-thesis-three-layer-arc.md`). The sheaf consistency gauge (arc 3, Reproducibility Observatory) shipped 2026-06-21. Real-2nd-cohort REPLICATED (Phase C) remains data-blocked — no open HM450 AML cohort with machine-readable IDH. This doc is preserved as a design-rationale anchor; §5 in particular remains the live epistemic contract for agent-chosen hypotheses.

---

## 0. The thesis

**An agent, given underlying data assets, generates its own hypotheses, pulls the data needed to test
them, runs them through the polymer-claims gate, and the licensed/rejected results accumulate into a
live claims universe.** The gate is **independent recomputation + an e-value criterion + the defeat
graph + the FDR budget** — *not the agent's say-so* — which is exactly why the universe does not
degrade as the model hallucinates. This is the "agents-for-science write-target" from the north star,
made real on data.

The loop, in one line:
```
data asset  →  agent hypothesizes  →  agent pulls the slice  →  gate (recompute+e-value+defeat+FDR)  →  universe
```

## 1. What already exists (the embryonic harness)

The skeleton of **every** layer is already in the repo — this is an extension, not a greenfield build:

| Layer | Already built |
|---|---|
| Generation seam | `run_cycle` GENERATE stage + proposer bus (`protocol/.../{generate,proposers,generation_adapter,plan_synthesis}.py`) |
| **Data-aware agent (the key precedent)** | `MeanDiffGenerationAdapter` (`llm_adapter.py:208`) — an LLM that **reads a real dataset** (`load_dataset`), is prompted *"you are a scientific-claim generator working over a REAL dataset, propose claims,"* emits **executable** `stats::mean_diff` claims, and is wired to `serve --real-data` via `_build_real_data_proposer`. **The autonomous data→claims loop is already proven end-to-end for the `dose_response` CSV.** |
| Real execution gate | Two independent legs (`StatsPure`/`StatsStdlib`; methyl mean-diff + OLS-coef), e-value / online e-LOND FDR, defeat-as-update, drift-reopen, REPRODUCED/REPLICATED tiers — all live |
| Methylation execution path | `region_delta_beta_claim` + `n_dmps_claim` over an SE-Contract (`load_contract`, `dimnames_hash`), the content-addressed `AnalysisProfile` apparatus |
| Universe | `NodeRunner` + the live SSE viewer (spectral layout) |

So the question is **not "can the loop exist"** — it does, for a toy CSV. The question is what it takes
to make it *real and general*.

## 2. The gap (what the full vision adds)

1. A **real data asset** (a cohort) instead of a toy CSV. → needs ingestion + a matching apparatus profile.
2. A **methylation hypothesizer** (region/contrast hypotheses) instead of `mean_diff`. → a `MethylGenerationAdapter`.
3. A **catalog of data assets** the agent chooses from, with queryable metadata (what contrasts/covariates exist).
4. An **incubation phase**: generate *many* hypotheses, prioritize/rank, not one-shot.
5. **The epistemic integrity of agent-chosen hypotheses** — the deep one (see §5). Two orthogonal honesty
   conditions: naive severity is violated if the agent picks *where* to test by looking at the data
   (§5a), and the agreeing legs only multiply severity if their errors are uncorrelated (§5b). This is
   where the real rigor lives.

## 3. The decomposition (phases A→D)

### Phase A — Real execution substrate (the foundation)
Make a methylation claim license on a **real cohort** through the existing gate. This phase **is** the
"real-data swap" — the single highest-leverage move available: it converts the system's central proof
("a claim licenses on a real, independently recomputed, content-addressed analysis that beats a
criterion") from *exercised* to **earned**, which is the whole thesis. The swap is designed-in, not a
rebuild: data enters through the content-addressed SE-Contract seam (DRS-shaped, keyed by `dimnames_hash`),
the apparatus is a content-addressed `AnalysisProfile` (`profile_hash`), and the two independent legs + the
drift daemon already exist — point the *identical* `load_contract` seam at real betas and the rest runs
unchanged. (Dataset + data-handling decisions in §6.)

**Dataset fit (TCGA-LAML, HM450, GDC open-access).** ~194 cases with HM450 methylation, **fully open
access** — Level-3 betas + the somatic MAF (for grouping) + clinical (age/sex), no dbGaP/controlled
access; harmonized **GRCh38** (SeSAMe-processed Level-3). Contrast **IDH1/2-mut vs WT (~38 vs ~155)** — the
strongest, most-replicated hypermethylation signal in AML (IDH→2-HG inhibits TET2 demethylation; Figueroa
2010, confirmed in TCGA 2013), well powered. (Backup: DNMT3A-mut ~51, larger N but co-mutation-confounded;
not the ~17 TET2-mut group.)

**Two adjustments from the synthetic EPICv2 demo:**
- **Add a 450K `AnalysisProfile`** (450K manifest, GRCh38, distinct `profile_hash`). Running HM450 data
  through the EPICv2 profile would be wrong; a *named* platform profile is the apparatus working as
  designed — and a proof point that the abstraction spans platforms.
- **Ingest GDC Level-3 betas directly** → the Python legs run on them (no R normalization for the demo).
  The profile honestly becomes *"GDC HM450 Level-3 SeSAMe pipeline"* — a real, citable upstream apparatus.

**Wiring path:**
1. Ingest TCGA-LAML HM450 Level-3 betas + the open MAF + clinical from GDC → real `dimnames_hash`; derive
   `Sample_Group` = IDH1/2-mut vs WT from the MAF, carry Age/Sex. (First reuse what transfers from the
   existing real-data path — `exec_adapters.py: real_data_seed_corpus`, `StatsPureAdapter`, `serve
   --real-data`.)
2. Add the 450K `AnalysisProfile` → its `profile_hash`.
3. Compute real betas → region-Δβ and the n-DMP count via the two independent legs. (Region selection is a
   spec fork for Phase A; ultimately it is the **agent's** job — see Phase B/D.)
4. **Gate:** legs agree (air-gap) ∧ e-value beats the e-LOND threshold ∧ survives the defeat graph → an
   **earned** license, not an asserted one.
5. **Pin & verify:** record the full content-address; run the drift daemon to confirm a content move
   re-opens it.
6. **Retire the caveat** in `ARCHITECTURE_CURRENT.md` / `CONTINUE.md`; report `q` (the false-license rate)
   on the real run.

**Acceptance:**
1. A real cohort licenses a region-Δβ (and the n-DMP count) at **REPRODUCED**, on values **computed from
   real betas** by the two independent legs, beating the stated criterion.
2. The license records its **full content-address** — real `dimnames_hash` + `profile_hash` +
   `semantic_run_id` — and survives a drift check.
3. The **synthetic-betas caveat is retired** for that tier; `q` is reported on real data.
4. **Honest failure is an acceptable outcome.** If a region does *not* clear the criterion on real data,
   the gate correctly **withholds** the license — the system working, reported plainly, not a phase failure.

**Why first:** the agent needs a working real substrate to test against, or it generates into a void (the
precise failure mode the north star indicts). For this phase the region/contrast can be a single concrete
one — it proves the path, not the agent.

### Phase B — The methylation hypothesizer (the agent)
A `MethylGenerationAdapter` (mirroring `MeanDiffGenerationAdapter`): reads the registered asset (betas +
mutation/clinical metadata), prompts the LLM to propose **region/contrast hypotheses** as executable
`region_delta_beta` / `n_dmps` claims, wired to `serve`. Acceptance: the agent **autonomously** proposes
≥1 testable methylation claim from the real asset that flows through Phase A's gate into the universe.

### Phase C — Data-asset catalog + the agent's "what can I test?" view
A registry of assets (cohorts) with queryable metadata (available contrasts, covariates, platform). The
agent **selects** an asset and frames hypotheses against it. Acceptance: ≥2 assets registered; the agent
picks + hypothesizes across them. (A 2nd real cohort here also unlocks the §2E **REPLICATED** gold tier.)

### Phase D — Incubation, ranking, and the integrity layer
Multi-hypothesis generation + prioritization (the "incubation" phase), and — critically — the
**severity / anti-cherry-picking discipline** for agent-chosen tests (see §5), tied into the e-LOND FDR
budget so an agent fishing across many hypotheses cannot inflate the corpus false-license rate `q`.
Acceptance: an agent generates N hypotheses, tests them, and `q` stays honest because the FDR ledger
absorbs the multiplicity.

## 4. Dependency order & recommended sequence

**A → B → (C, D).** A is the genuine foundation (real substrate to test against). B proves the autonomous
loop on real data — the smallest thing that demonstrates the actual thesis. C and D scale it to many
assets and many hypotheses with honest multiplicity control. Each phase is its own spec → plan → build.

## 5. The crux: keeping agent-chosen hypotheses rigorous (the deepest design question)

This is where the project's whole reason-for-being is at stake, so it deserves its own section even in a
high-level plan.

**`q` is honest only if TWO orthogonal conditions hold — and they are distinct failure modes.** An
autonomous agent can quietly violate either, so the design must control both and not let one masquerade
as the other (this is exactly what north-star §2E and the linchpin doc §8 exist to guard):

1. **Selective inference / severity** — the hypothesis must not be tested on the data that suggested it.
2. **Implementation independence** — the agreeing implementations must not share a common cause.

A license can clear (1) and still fail (2): two methods run on the *same* betas/manifest/normalization
test **reproducibility, not conceptual replication** — which is precisely why that tier is named
**REPRODUCED, not REPLICATED**. Both bars are real; neither substitutes for the other.

### 5a. The selective-inference / severity condition

**The problem.** Classical severe testing requires that a hypothesis not be tested on the same data that
suggested it. If the agent scans the betas, sees a hypermethylated region, and then "tests" a claim about
that region on the *same* betas, the e-value is not valid — that is data-dredging, the engine of the
replication crisis. An autonomous agent fishing for signal is *structurally* prone to this.

**Why the system is well-placed:**
- The **e-LOND FDR ledger controls false-discovery rate under arbitrary dependence** (e-BH, Wang-Ramdas).
  The agent's stream of hypotheses *is* an open-ended, dependent test stream — exactly what e-LOND is
  designed to govern. Each hypothesis gets **one** e-test; `q` is reported honestly.
- **Plug into machinery that already exists, don't reinvent it.** The SELECT stage already applies a
  *cardinality-scaled Benjamini–Hochberg selective-inference correction* — the search cardinality of each
  selection tightens VERIFY's significance bar. Phase-D multiplicity control should extend that, not add a
  parallel scheme.

**The candidate disciplines (a Phase-D design fork to resolve and cross-check):**
- **(a) Generate-from-metadata, test-on-betas.** The agent hypothesizes from *mutation/clinical metadata
  + the research landscape* (not the beta values), then the betas are the held-out test. Clean validity;
  closest to how a scientist forms a hypothesis ("IDH mutation should drive hypermethylation") before
  looking at the methylation. **Recommended default — with one caveat (see below).**
- **(b) Sample-splitting.** Generate on a discovery split, test on a held-out split. Valid but halves power.
- **(c) Pre-registration ledger.** The agent commits the hypothesis (region + contrast + criterion) to an
  append-only ledger *before* execution; the FDR budget is charged at registration. The corpus's own
  ledger already has the shape for this.
- The likely answer is **(a) as the default discipline + (c) the ledger as the enforcement mechanism**,
  with `q` as the honest headline — but this is the #1 thing to cross-check.

> **The leak in (a).** "Generate from the research landscape" is clean *only if* the landscape claim was
> not itself derived from an overlapping cohort. The IDH→hypermethylation signal was discovered in
> overlapping AML cohorts (Figueroa 2010; TCGA 2013), so the prior literature is a **shared cause** (the
> north-star common-cause-DAG sense): an agent reasoning "IDH should drive hypermethylation" from a
> literature born of *this same data* is closer to confirmation than to a held-out severe test. Track the
> hypothesis's provenance, not just its phrasing.

### 5b. The implementation-independence condition

The agreeing legs make "two beats one" a real severity multiplier *only* to the degree their errors are
uncorrelated. Today's legs share the beta matrix, the HM450 manifest, and the normalization convention —
so REPRODUCED is the honest tier, and the e-values must **not** be multiplied at this tier (the §2E rule).
Two paths raise the bar, both already designed: a **second real cohort** with a distinct `dimnames_hash`
earns **REPLICATED** and licenses the *product* e-value as one e-LOND test (Phase C); and, longer-horizon,
a **common-cause DAG per implementation** makes probabilistic independence a *derived, evidenced* claim
rather than an asserted one. Phase D must keep this accounting visible so a REPRODUCED license is never
read as having cleared the independence bar it did not clear.

## 6. Decisions already made (this conversation)

- **Dataset:** TCGA-LAML, HM450, GDC open-access; contrast **IDH1/2-mut vs WT** (~38 vs ~155, strongest
  replicated signal). (The TET2 example was the author's separate research — removed; see CONTINUE.)
- **Data handling:** **fully local, nothing committed** — repo ships the tooling (ingestion + profile +
  adapter), the SE-Contract is generated locally and gitignored, tests skip-if-absent.
- **Region selection is the AGENT's job**, not a human pre-registration — which is *why* §5 matters.
- **Apparatus:** a HM450 profile whose provenance is the GDC SeSAMe Level-3 pipeline.

## 7. Open questions to cross-check with the other instance

1. **§5 — the two honesty conditions for agent-chosen hypotheses.** (5a) Is "generate-from-metadata,
   test-on-betas" + a pre-registration ledger the right severity model, and how do we close the (a) leak
   (literature derived from overlapping cohorts)? Is sample-splitting needed as a fallback? (5b) How is
   the REPRODUCED-vs-REPLICATED independence accounting surfaced so a REPRODUCED license is never misread
   as having cleared the independence bar?
2. **Phase granularity** — is A→B→C→D the right cut, or should A+B be one "thin vertical slice" spec?
3. **How much research-landscape understanding** does the hypothesizer need — literature retrieval, or
   just the asset metadata + a strong prompt?
4. **Asset-catalog scope** — how rich does the registry need to be before Phase B is useful?
5. **Ingestion home** — a `polymer-claims ingest` CLI command vs. a standalone script.
6. **Universe semantics** — should rejected/contested agent hypotheses be first-class in the universe
   (they're scientifically informative), and how does the viewer convey "agent-proposed, gate-rejected"?

## 8. What this is NOT

- Not a rewrite — every layer exists in embryo (§1).
- Not federated/multi-tenant — still local-only by design (that's a later arc).
- Not the standards skin (DRS/RO-Crate/in-toto) — parallel, and more compelling once real runs exist.
- Not committing any real data — the data stays local; the repo ships the loop, not the dataset.
