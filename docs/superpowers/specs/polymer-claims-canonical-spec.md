# Polymer Claims — Canonical Specification (current state of record)

> **The single canonical spec for polymer-claims.** It describes what the system *is* as built and
> merged on `main`, not a design target. It supersedes and consolidates the per-feature design specs
> now in `docs/superpowers/archive/specs/` (foundations, protocol-spine, earned-strength,
> structural-equivalence, §2E, n-DMPs, reinstatement, procrustes) — read those for the design rationale
> behind any one slice.
>
> **State of record:** `main`, as of 2026-06-15 (last merge: `procrustes-embedding-alignment`).
> `scripts/check-all.sh` green — **226 umbrella + 351 grammar + 363 protocol + 2 isolation** tests;
> viewer `tsc`+build clean. Local-only (commits not pushed — flagged account, no active CI).
>
> Companion docs: live build log `docs/superpowers/CONTINUE.md` · one-page map `ARCHITECTURE_CURRENT.md`
> · reserved terminology `GLOSSARY.md`.

---

## 1. What the system is

A **compiler + runtime for science**. The grammar defines *what a claim is*; the protocol defines *how
a corpus of claims evolves toward truth*; the local node *hosts* a running corpus; the viewer *renders*
the evolving topology.

```
grammar            →  protocol                  →  node (src/polymer_claims)  →  viewer
"what a claim is"     "how a corpus evolves"        a local mutable host          renders the live
 (v1.3 IR, 5 layers)   (run_cycle flywheel +         (NodeRunner + serve)          topology over SSE
                        3 daemons + scheduler)
```

| Layer | Package | Path | State |
|---|---|---|---|
| Grammar (v1.3 claim IR) | `polymer_grammar` | `grammar/` | Complete — 8 layer-phases |
| Protocol runtime | `polymer_protocol` | `protocol/` | Complete — 5 sub-projects + 3 daemons + scheduler |
| Umbrella distribution (CLI + live node) | `polymer-claims` | `src/polymer_claims/` | Active — `pip install` works end-to-end |
| Viewer (3D claims universe) | Next 16 app | `viewer/` | Active — `tsc`+build clean |

---

## 2. The grammar (v1.3) — what a claim is

A 5-layer grammar plus protocol-imposed fields and an air-gapped evaluator. All models subclass a
frozen `_Model` (`extra="forbid"`); **collections are tuples** (deep immutability + content-addressing);
there are no `dict`/`list` fields on models.

- **L0 — leaf:** the empirical anchor, a sum type (`Quantity` / `Categorical` / `Existence` /
  `Proposition`) so qualitative and warrant findings are first-class, not faked into statistics.
- **L1 — proposition:** molecular claim content; identity is an *asserted, licensed equivalence*, never
  a hash. Defeasible `Equivalence` edges.
- **L2 — licensing bridge + roles/units:** the bridge that mints `LICENSED` status via an (σ, M)
  satisfaction (severe-test or replication route) with required rival-set closure — there is no
  "LICENSED-simpliciter." Typed causal roles + a Dimension algebra (units).
- **L3 — defeat graph (VAF) + Duhem blame:** value-based argumentation; a strength-mediated
  effective-defeat relation whose **grounded extension** is the accepted set.
- **L4 — AGM/TMS revision:** belief-base expand/contract/revise + entrenchment for how the corpus
  changes under incompatible claims.

**Strength** is a 6-axis Pareto vector (magnitude, certainty, evidence_against_null, severity,
world_contact, explanatory_virtue), uniformly higher-is-better, with no hidden scalar collapse.

**Phase-7 protocol-imposed fields:** provenance · governance · the online-FDR ledger · subject slot ·
a `representation_revision` meta-tier (a schema change expressed as a first-class licensable claim).

**Phase-8 evaluator (the air gap):** a typed compute-graph IR with an air-gapped `verify()` — a
`Satisfaction` is minted only when **≥2 distinct adapter identities agree**.

---

## 3. The protocol runtime — how a corpus evolves

A `Corpus` is **exactly 4 collections** (claims, defeat_edges, equivalences, fdr_ledger) — the unit the
protocol transforms.

**`run_cycle`** is one pass of the flywheel, threading a frozen `Corpus` + `SelectionLedger`:

```
represent → generate → canonicalize → safety_gate → select → commit → execute_ground → verify_stage → integrate
```

**Three standing daemons** (pure, caller-scheduled):
- **DRIFT** — re-examine `LICENSED` claims as the world (or content) moves; re-opens drifted licenses.
- **ORACLE-VALIDATION** — decay failing oracles (an oracle is a credibility dossier whose validation
  tier *caps* a claim's empirical strength axes).
- **REPRESENTATION RED-TEAM** — attack the corpus's representation.

**Scheduler (`next_action`)** — a recommend-only budget scheduler that value-ranks the next action
(RUN_CYCLE vs a daemon pass) under a shared budget.

**Exports (protocol ↔ viewer contract):** `TopologyExport` (nodes/edges/clusters + a deterministic 3D
layout) and `TopologyTimeline` (warm-started frames + per-frame stats).

**Purity invariant:** `grammar/` and `protocol/` are pure/deterministic and **numpy-free** — no
clock/random/IO; time-like inputs are passed in. `grammar/` must never import `polymer_formalclaim`
(isolation-tested); `protocol/` depends one-way on `grammar/` (isolation-tested). The only impure piece
is the umbrella node/server.

---

## 4. The epistemic core (e-value native)

Licensing, the corpus FDR budget, and defeat are **one mechanism**:

```
LICENSED ⇔ adapter-agreement ∧ SATISFIED ∧ grounded ∧ live e-LOND discovery
```

- **FDR ledger = e-LOND** — an online process giving FDR control under arbitrary dependence over the
  open-ended test stream. **One e-test per claim lifetime** (a cross-cycle duplicate-entry bug was found
  and fixed in audit remediation).
- **Evidence atom = a Waudby-Smith-Ramdas betting e-value.**
- **Defeat de-licenses *through the ledger* and refunds** the discovery (`FDRTest.retracted` tombstone +
  alpha-wealth refund). The 4-way gate runs live in the node; the drift path preserves
  `LICENSED ⇒ a live discovery`.
- **Reinstatement → PENDING** (symmetric counterpart to defeat-as-de-license): a `RejectionReason`
  marker {DEFEAT_GROUNDED_OUT, REFUTED, ROBUSTLY_BLAMED} + an INTEGRATE reinstatement pass reopen a
  *defeat-rejected* claim to **PENDING** (to re-test on current data — never auto-relicense) when its
  attacker falls. **Refuted** claims stay terminal; `ROBUSTLY_BLAMED` is reserved (no protocol consumer
  yet).
- **§2E tiered independence** — `Licensing.independence_tier` {**REPRODUCED**, **REPLICATED**}, additive
  (default REPRODUCED → byte-identical). **REPRODUCED** = agreeing implementations share the dataset (the
  air gap). **REPLICATED** = reproduced across ≥2 cohorts with distinct `dimnames_hash` — the only tier
  that may **multiply** the cohorts' e-values (`e₁·e₂`) as *one* e-LOND test/discovery, with no α-budget
  double-count.

**The air gap & adapter independence:** independence is enforced by the **adapter trust registry**
(trusted ∧ different owner ∧ different `implementation_hash`); a same-owner pair is held PENDING.

---

## 5. Real computation — from asserted values to computed evidence

The system no longer licenses only on asserted values.

- **Real execution adapters** — claims compute a two-group mean difference from a bundled dataset via
  two genuinely independent stdlib adapters and license/reject on the **computed** value
  (`serve --real-data`).
- **CES-0 → CES-4, the credibility-evidence spine:** a content-addressed `AnalysisProfile` apparatus
  (CES-0) → a DRS-shaped SE-Contract data seam (CES-1) → the first claim to license on a value computed
  from a methylation matrix (CES-2, **region Δβ**, two methodologically-independent legs) → a license
  recording its **full content-address** — dataset `dimnames_hash` + apparatus `profile_hash` +
  `semantic_run_id` (CES-3) → all of it running **live** in `NodeRunner`/`serve` with a drift daemon that
  re-opens content-drifted licenses (CES-4).
- **Second methylation reduction — n-DMPs-at-FDR:** the **count of differentially-methylated probes**
  (a probe is a DMP iff its per-probe pooled-t p < α) licenses on a **one-sample count-enrichment
  betting e-value** (testing H0: per-probe DMP-rate ≤ p0 = α). Two independent legs (manual pooled-t vs
  numpy-lstsq OLS-coef t) **agree on the integer count** (air gap). Pure-Python Student-t p-value
  (incomplete beta, no scipy). Umbrella-only.

---

## 6. The umbrella node + product

- **`pip install polymer-claims`** → a CLI: `version` / `validate` / `run-cycle` / `loop` /
  `export-topology` / `export-timeline` / `serve`.
- **Live local node:** `NodeRunner` (owns the loop/clock) + a FastAPI SSE server (`[serve]` extra; owns
  the network). `NodeRunner` is the one impure piece.
- **Optional extras:** `[serve]` (FastAPI server), `[llm]` (the Anthropic-backed `LLMGenerationAdapter`,
  driving the live node via `serve --llm` with an `every_n_ticks` throttle), `[embed]` (numpy, behind
  which `embedding.py`/`methyl_adapters.py` live so base import stays numpy-free).
- **Local-node hardening:** `--max-frames` ring retention, an `asyncio.Lock` serializing ticks, bounded
  SSE queues, and a **non-loopback bind guard** (`serve --host` other than loopback refuses without
  `--unsafe-remote-control`). Still **local-only** by design: the mutating routes
  (`/step`/`/pause`/`/resume`) are unauthenticated.

---

## 7. The viewer

A standalone Next 16 / React Three Fiber app (`viewer/`) with the D2 metrological aesthetic.

- **Sample mode** — plays a precomputed `viewer/public/sample-timeline.json`.
- **Live mode** — streams from a running node over SSE.
- **Layout (`serve --layout {spectral,force}`):** **spectral** (default) is the signed-Laplacian
  eigenmap (`embedding.py`), **orthogonal-Procrustes-aligned per frame** to the previous displayed frame
  so the universe grows smoothly instead of thrashing on eigenbasis sign/rotation ambiguity
  (`layout_id="external:spectral-v1"`; reflection allowed, no det-correction; 6dp round). **force** is
  the legacy id-hash Fruchterman-Reingold path and is **byte-identical** to the prior implementation.
  Spectral lazy-imports the embedder (base import stays numpy-free) and gracefully falls back to force
  (warn once) when `[embed]`/numpy is absent. Offline `export_timeline` stays force-directed (protocol
  purity — it cannot compute the spectral embedding).

---

## 8. Invariants (working agreements)

- `Corpus` = exactly 4 collections; all models frozen `_Model` (`extra="forbid"`); collections are
  tuples; no `dict`/`list` fields.
- `grammar/` + `protocol/` are pure/deterministic + numpy-free; the only impurity is the umbrella
  node/server. `grammar/` never imports `polymer_formalclaim`; `protocol/` → `grammar/` one-way (both
  isolation-tested).
- New cross-cutting fields land **additive/optional** (`X | None = None`) with a present-only-when-Y
  validator; opt-in features default to byte-identical behavior when off.
- numpy lives behind the `[embed]` extra; `embedding.py` / `methyl_adapters.py` are not re-exported.
- Tests: per-package `uv run pytest -q` + `uv run ruff check src tests`; full gate
  `scripts/check-all.sh`. TDD: failing test first. Merge to `main` `--no-ff`, local-only.

---

## 9. Standing caveats (carry forward)

- **Methylation betas are synthetic** — the BENCHMARKED/recomputable-public tier is *exercised, not
  earned*. Real public GEO/ENA data is a self-contained swap (identical `load_contract` seam) and is the
  recommended next move (`docs/superpowers/2026-06-15-next-phase-real-data.md`).
- The two methylation adapters are **reproducibility-independent, not error-independent** (same estimand,
  same data) → the single-cohort demo licenses at **REPRODUCED**. The **REPLICATED** demo runs on a 2nd
  *synthetic* cohort (`epicv2_casectrl_demo_b`) — also exercised, not earned, until a real 2nd cohort is
  swapped in.
- Adapter independence is **operator-asserted** (`implementation_hash` is a supplied string compared with
  `!=`); byte-derived hashing + credential provenance on the frozen `Satisfaction` are still open.
- `semantic_run_id` is the **Python** digest; an R-parity golden fixture is deferred (needs an R
  serializer).

---

## 10. Frozen, user-gated & future

**Frozen (v1.2 — fallback, not the active path):** `v1.2/` holds the complete v1.2 FormalClaim
ecosystem (`polymer_formalclaim`, the 47-claim corpus, the `claim-harness` Claude Code plugin, schema,
legacy workflows). Frozen 2026-06-01. It does **not** exercise the v1.3 grammar/protocol runtime; known
v1.2 limitations are left as-is under the freeze.

**User-gated / future (needs an explicit go):**
- **PyPI publish** of `polymer-claims` — build + `[serve]` ready; blocked operationally by the flagged
  GitHub account (Actions/OIDC suppressed → no active CI; `scripts/check-all.sh` is the substitute).
  Publish locally with a token only when asked.
- **polymerbio.org / PolymerGenomicsAPI integration** — lift `<ClaimUniverse>` + theme + live mode into
  the API repo's viewer (aesthetic already matches by construction).
- **Adapter-independence hardening** — byte-derived `implementation_hash` + recorded agreeing credential
  IDs on `Satisfaction`.
- **Federated / BYO-compute layer** — the "users run their own node" vision; a `POST /inject` endpoint is
  a noted future hook.
- **Deferred audit Tier-C** — schema→TypeScript contract codegen, narrowing the protocol public API,
  broad `model_copy` revalidation.

---

## 11. Where the rest lives

- **Live build log + NEXT plan:** `docs/superpowers/CONTINUE.md`
- **One-page architecture map:** `ARCHITECTURE_CURRENT.md` · **Glossary:** `GLOSSARY.md`
- **Per-feature design rationale (archived):** `docs/superpowers/archive/specs/` and
  `docs/superpowers/archive/plans/`
- **Recommended next phase (real-data swap):** `docs/superpowers/2026-06-15-next-phase-real-data.md`
- **Phase-2 north star:** `docs/vision/2026-06-12-phase-2-north-star.md`
- **Credibility-arc roadmap:** `docs/superpowers/archive/roadmaps/2026-06-11-credibility-arc-roadmap.md`
- **Spectral-layout guides:** `docs/spectral-layout-how-to-use.md` (usage) ·
  `docs/spectral-layout-how-it-works.md` (eigenmap + Procrustes theory)
</content>
</invoke>
