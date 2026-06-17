# Formal Core — Evidential Licensing as Anytime-Valid FDR Control over a Defeasible Claim Graph

**Polymer Claims · formal-core working draft · 2026-06-17**

> **Purpose.** Pin the definitions of the *built* system in standard notation and state the first theorem worth proving. This is the mathematical spine of the e-value↔claim-graph bridge described in `../Polymer Claims — E-value Claim Graph (Priority Note).md`, but written to be consistent with the code: it reuses `e_value`, `Licensing.independence_tier`, `dimnames_hash`, `grounded_extension`, `FDRTest.retracted`, and the `betting_evalue` evidence atom verbatim. A symbol↔code map is in §10.
>
> **Status legend.** `[E]` established in cited literature; `[P]` proposed/planted by this project; `[O]` open — not yet proven. The contribution of the *formal core* is concentrated in §6–§7 (`[P]/[O]`); §2–§5 are mostly `[E]` machinery assembled in a new arrangement.

---

## 1. Objects

A **claim** `c` carries `status ∈ {pending, licensed, rejected, conjectured, exploratory, structural}` and an optional `licensing` record. Claims decompose by layer: `L0` leaf (the empirical anchor — Quantity / Categorical / Existence / Proposition), `L1` proposition (molecular content), `L2` licensing bridge, `L3` defeat graph, `L4` AGM belief revision.

A **materialization context** `M = (api_version, data_version, dimnames_hash, semantic_run_id, profile_hash)` is the content-address of *what was computed on what data with which profile*. `dimnames_hash` is the canonical dataset content-address (the drift key for a cohort); `semantic_run_id = SHA256(tool · params · inputs · profile_hash)`.

A **satisfaction** is a pair `(σ, M)` with `verdict ∈ {satisfied, refuted, undetermined}`. `σ` is the test outcome; `M` is never implicit.

A **corpus** is exactly four collections: `(claims, defeat_edges, equivalences, fdr_ledger)`.

---

## 2. The evidence atom: the betting e-value `[E]`

Each test of a claim against a null produces `e_value = betting_evalue(a, b; threshold τ, comparator)` — the Waudby-Smith & Ramdas (JRSS-B 2024, Eqs. 24–26) betting / empirical-Bernstein **e-value** for the **severe-test composite one-sided null**

$$H_0(c):\quad \mu_B - \mu_A \le \tau .$$

Two properties carry the whole construction:

- **Validity (Ville).** `[E]` The betting capital process $\prod_i (1 + \lambda_i W_i)$ is a nonnegative supermartingale under $H_0$, so $\mathbb{E}_{H_0}[e] \le 1$. A claim's `e_value` is therefore *evidence against $H_0$* in the strict testing-by-betting sense (Shafer): the factor by which a skeptic's stake against $H_0$ multiplied.
- **Severe-test semantics.** Because $H_0$ is the *one-sided composite* "effect does not exceed $\tau$," a large `e_value` is not merely "the effect is nonzero" but "the effect **severely** passes a threshold of scientific size" (Mayo). The threshold $\tau$ is the bridge between statistical and substantive significance, and it is recorded in `M`.

This is the atom. Everything above is bookkeeping over atoms.

---

## 3. The licensing rule: online FDR via e-LOND `[E] / [P]`

Claims arrive as a stream. At step $t$ (1-based) the **e-LOND** procedure (Xu & Ramdas 2024) allocates

$$\alpha_t \;=\; \text{target\_fdr}\cdot \gamma_t \cdot (D_{t-1} + 1),\qquad \gamma_t = \frac{6/\pi^2}{t^2},\quad \textstyle\sum_t \gamma_t = 1\ (\text{Basel}),$$

and records a **discovery** iff

$$e_t \;\ge\; 1/\alpha_t .$$

Here $D_{t-1}$ is the **live** discovery count strictly before $t$ (see §6 for "live"). The ledger stores one `FDRTest = (index t, claim_id, e_value, alpha_allocated = α_t, discovery, retracted)` per test.

`[E]` **e-LOND guarantee.** e-LOND controls the false-discovery rate under **arbitrary dependence among the e-values**, with no correction factor — in contrast to Benjamini–Hochberg (needs independence/PRDS) or Benjamini–Yekutieli (pays an $\sim\ln m$ penalty that grows with the corpus). This is the reason the corpus can grow without an alpha-spending crisis.

**The headline metric.** `[P]` $q$ := the **corpus false-license rate** $= \mathbb{E}[V/R]$, where $R$ = number of live discoveries (`n_discoveries`) and $V$ = number of those that are false licenses. The whole point of the construction is the guarantee $q \le \text{target\_fdr}$. (Note: $q$ is a *corpus-level* FDR, **not** a per-claim confidence; the per-claim quantity is `e_value`. The priority note's "q per claim" phrasing is superseded by this.)

**Full licensing predicate.** A claim is `licensed` iff **all** hold:
1. **Air gap** `[P]` — $\ge 2$ distinct trusted adapter implementations (distinct `implementation_hash`, distinct owner) agree. (Reproducibility-independence; catches implementation bugs, not statistical error.)
2. **Verdict** — both adaptations return `verdict = satisfied`.
3. **Grounded** — $c \in$ `grounded_extension` (§5).
4. **e-LOND discovery** — $c$'s test is a *live* discovery (§3 + §6).

---

## 4. Independence tiers and the product rule `[P] / [O]`

A claim's `Licensing.independence_tier` records how its supporting e-values relate:

| Tier | Condition (`independence_tier_of`) | e-value used in the ledger |
|---|---|---|
| `reproduced` (default) | satisfactions share one cohort (one distinct `dimnames_hash`) | one effective `e_value` |
| `replicated` | $\ge 2$ **distinct** non-null `dimnames_hash` | the **product** $e_1 \cdot e_2$, as a single e-LOND test |

**Common-cause gate (v1).** Distinct `dimnames_hash` is treated as necessary-and-sufficient for the product rule; the dataset is the single load-bearing cause node. Distinct profile/assay/owner are recorded for audit but not required.

**Soundness statement and its gap.**
- `[E]` If $e_1, e_2$ are e-values for the *same* null on **statistically independent** data, then $e_1 e_2$ is an e-value for that null (independent multiplication).
- `[O]` **The gap:** *distinct `dimnames_hash` is a content-address distinctness, not a guarantee of statistical independence.* Two cohorts with different content hashes can still be dependent — shared reference panel, shared controls, overlapping individuals, same batch/platform, the same upstream normalization. When they are, $e_1 e_2$ over-states evidence and the per-claim license is anti-conservative. This is a genuine soundness hole in the v1 gate and must be either (a) narrowed (a stronger common-cause criterion than hash-distinctness) or (b) made conservative (merge by averaging — Vovk–Wang — which is valid under arbitrary dependence but loose). **Crucially, this gap is bounded to the *within-claim* replication step; it does not touch the *across-claim* e-LOND guarantee, which already tolerates arbitrary dependence (§3).** Stating that boundary precisely is part of §7.

---

## 5. The defeat graph: value-based argumentation `[E]`

Defeat is represented as a value-based argumentation framework (VAF), not as an e-value comparison.

**Edge kinds** (`DefeatEdgeKind`): `undermine` (attacks a premise / the data basis), `undercut` (attacks the inferential warrant), `rebut` (asserts the contrary conclusion), `reclassify` (disputes the pattern/profile), `reinterpret` (meaning moves, statistics unchanged), and `evidence_for` (**support — never a defeat**). The first five generalize Pollock's rebutting/undercutting pair; in particular `undermine`+`undercut` split Pollock's "undercutting defeater" into data-attack vs warrant-attack.

**Strength is a 6-axis Pareto vector — no hidden scalar:** `StrengthVector = (magnitude, certainty, evidence_against_null, severity, world_contact, explanatory_virtue)`.

**Effective defeat.** An edge $a \to b$ is *effective* unless `strength(b)` **Pareto-dominates** `strength(a)`. Provisional edges stay inert until their source is `licensed`.

**Acceptance.** Over the effective-defeat relation, the accepted set is the **grounded extension** (Dung 1995; Caminada labelling), which is unique, polynomial-time, and skeptical. The three Caminada labels IN / OUT / UNDEC correspond to `licensed`-eligible / `rejected` / `pending`.

**Reinstatement.** A claim `rejected` with reason `defeat_grounded_out` may reopen to `pending` (never auto-relicense) if its attacker is itself later defeated.

---

## 6. The unification (the planted flag) `[P]`

The project's central claim — and the thing the formal core exists to make precise — is that **licensing, defeat, drift, and FDR are one operation viewed from different angles.** Formally:

Let `live` discoveries at step $t$ be
$$D_t \;=\; \#\{\,s \le t : \text{discovery}_s \wedge \neg\,\text{retracted}_s\,\}.$$

The flywheel's `integrate` stage runs, in order: AGM `restore_consistency` → recompute `grounded_extension` → for every claim that **was** `licensed` and is now grounded-OUT (or AGM-retracted), set `status := rejected` and call `retract_tests(fdr_ledger, defeated_ids)`, which sets `FDRTest.retracted := true` (a **tombstone**: `alpha_allocated` and `e_value` are *frozen*, never recomputed).

So the four phenomena are the same ledger-and-graph operation:

| Phenomenon | Operation |
|---|---|
| **License** | a new e-LOND discovery enters `grounded_extension` |
| **Defeat** | an effective defeater pushes a claim grounded-OUT → tombstone → $D$ drops |
| **Drift** | `dimnames_hash` of `M` goes stale → re-execution updates `e_value` → may fall below $1/\alpha_t$ → de-license (a self-inflicted defeat) |
| **FDR** | $q = \mathbb{E}[V/R]$ over the **live** discovery set, maintained $\le$ `target_fdr` |

A defeat is, in this picture, a **downward update of the live discovery set**; drift is a defeat a claim deals itself when the world moves under it.

---

## 7. The first theorem to prove — Refund-Validity `[O→P, RESOLVED]`

> **Resolved — see `refund-validity.md` (v2).** Theorem 1: for any allocation count ≤ the all-ever discovery count (including the code's *live* allocation) and **null-bearing** refunds, $q \le \text{target\_fdr}$. Unconditional Refund-Validity is **false** (warrant-only defeats break it); the one code fix is to gate `retract_tests` by edge kind. The conjecture below is the original framing, kept for context.

The unification of §6 is *asserted* by the system but not yet *proven*. The non-trivial obligation is this:

> **Conjecture (Refund-Validity).** Let e-LOND run online over a claim stream, with $\alpha_t = \text{target\_fdr}\cdot\gamma_t\cdot(D_{t-1}+1)$ computed from the **live** count $D_{t-1}$, and let the `integrate` operation of §6 tombstone any discovery that leaves the grounded extension (freezing its `alpha_allocated` and `e_value`). Then at every step $t$, the live discovery set satisfies
> $$q_t \;=\; \mathbb{E}\!\left[\frac{V_t}{R_t \vee 1}\right] \;\le\; \text{target\_fdr},$$
> under arbitrary dependence among the e-values.

**Why it is not free** (the proof obligations, stated so they can be discharged or refuted):

1. **Retraction changes the denominator and numerator non-monotonically.** The e-LOND FDR proof bounds $\mathbb{E}[V/R]$ for the *discovery set the procedure makes*. Tombstoning removes elements from that set. If defeat removes a **false** license (the intended case), $V$ and $R$ both drop and $q$ should improve. But a **mistaken defeater** can remove a **true** license: $R$ drops while $V$ is unchanged, which *raises* $V/R$. So Refund-Validity cannot hold unconditionally — it needs a condition on defeaters (e.g., a defeater is itself a licensed claim subject to the same FDR control, so false defeats are themselves rate-limited). **Characterizing that condition is the heart of the theorem.**
2. **Frozen α-allocations were computed from soon-to-be-retracted discoveries.** $\alpha_t$ used $D_{t-1}$, which counted discoveries later tombstoned. The ledger does *not* rewind history. One must show the guarantee survives this "stale generosity" — likely true because larger $\alpha_t$ is *anti*-conservative at allocation time but the retraction removes the very discovery that inflated it; the bookkeeping needs to be made exact.
3. **Interaction with grounded semantics.** Defeat is decided by Pareto/grounded labelling (§5), a *deterministic* function of the corpus, while the FDR guarantee is *probabilistic*. The theorem must treat the grounded extension as a (data-dependent) stopping/selection rule and confirm it does not break the supermartingale argument.

**Target form of the result.** Either (a) a clean sufficient condition — *"if every defeater is itself a live e-LOND discovery, Refund-Validity holds under arbitrary dependence"* — or (b) a counterexample showing tombstoning can violate FDR, which would force the design to switch from "freeze-and-drop" to a re-allocating ledger. Both outcomes are publishable; (a) is the one the current code is implicitly betting on.

**Established pieces it rests on:** Ville's inequality (§2) `[E]`; the e-LOND FDR theorem without retraction (Xu & Ramdas 2024) `[E]`; uniqueness/skepticism of the grounded extension (Dung 1995) `[E]`. The novel step is composing them through `retract_tests`.

---

## 8. Drift is the same theorem, dynamically

The `DRIFT` daemon watches `M.dimnames_hash`. When the underlying cohort changes, the satisfaction's `M` is stale; re-execution yields a new `e_value`; if it falls below $1/\alpha_t$ the claim de-licenses. This is *exactly* a self-defeat (§6), so **drift is governed by the same Refund-Validity theorem** — no separate argument is needed once §7 is settled. This is the formal payoff that makes "drift-aware claims" a property rather than a feature: a license is a standing bet that is continuously re-settled as data arrives, and its validity is the validity of the refund.

---

## 9. Open problems (codebase-aware, honest)

1. **Refund-Validity (§7)** — the gating theorem. Until it is proven or a counterexample forces a redesign, the corpus-level $q \le$ `target_fdr` claim *after defeat* is conjectural, not guaranteed.
2. **Independence gate (§4)** — `dimnames_hash`-distinctness ≠ statistical independence. Either strengthen the common-cause criterion or fall back to dependence-robust merging for the replication product.
3. **Calibrating real evidence into valid e-values** — the betting e-value is only valid if the test it bets on is well-specified. The current methylation betas are **synthetic** (exercised, not earned); the Phase-A real GEO/ENA swap is where this guarantee meets reality. An e-value extracted from a literature claim (or an LLM's reading of one) is *not* an e-value without an explicit data model — the single biggest practical risk.
4. **Strength→defeat determinism vs. evidential strength** — the 6-axis Pareto `StrengthVector` decides defeats independently of the e-value magnitude. The relationship between "Pareto-dominant" (graph layer) and "more evidence against the null" (ledger layer) is asserted by the `evidence_against_null` axis but not formally tied to the e-value; §7 may require they be coupled.
5. **Adversarial evidence** — a betting semantics invites strategic submission; robustness to bad-faith e-values is unaddressed.

---

## 10. Symbol ↔ code map

| Math | Code object / field |
|---|---|
| claim $c$, status | `Claim.id`, `Claim.status ∈ {pending, licensed, rejected, …}` |
| null $H_0(c): \mu_B-\mu_A \le \tau$ | severe-test composite one-sided null in `betting_evalue(…, threshold, comparator)` |
| e-value $e_t$ | `FDRTest.e_value` ← `betting_evalue` (WSR JRSS-B 2024) |
| materialization $M$ | `MaterializationContext(api_version, data_version, dimnames_hash, semantic_run_id, profile_hash)` |
| satisfaction $(\sigma, M)$ | `Satisfaction(verdict, materialization)` |
| licensing $L2$ | `Licensing(route, satisfactions, rival_set_closure, rivals_considered, independence_tier)` |
| tier reproduced/replicated | `IndependenceTier`; `independence_tier_of(satisfactions)` |
| corpus | `Corpus(claims, defeat_edges, equivalences, fdr_ledger)` |
| $\alpha_t,\ \gamma_t$ | `alpha_allocated`; e-LOND `γ_t = (6/π²)/t²` in `fdr.py` |
| discovery $e_t \ge 1/\alpha_t$ | `FDRTest.discovery` |
| live count $D_t$ | `FDRLedger.n_discoveries` (excludes `retracted`) |
| tombstone | `FDRTest.retracted = True`; `retract_tests(ledger, ids)` |
| effective defeat | `effective_defeats` (Pareto on `StrengthVector`) |
| accepted set | `grounded_extension` (Dung/Caminada) |
| $q = \mathbb{E}[V/R]$ | the headline corpus false-license rate (FDR) |

---

## 11. References (verify exact venues/years before external posting)

- Waudby-Smith R, Ramdas A. Estimating means of bounded random variables by betting. *JRSS-B* 2024 (betting / empirical-Bernstein e-values, Eqs. 24–26).
- Xu Z, Ramdas A. Online multiple testing with e-values / e-LOND (FDR control under arbitrary dependence), 2024.
- Vovk V, Wang R. E-values: calibration, combination, applications. *Ann. Statist.* 2021 (independent multiplication; merging under dependence).
- Grünwald P, de Heide R, Koolen W. Safe testing. *JRSS-B*.
- Ramdas A, Grünwald P, Vovk V, Shafer G. Game-theoretic statistics and safe anytime-valid inference. *Statistical Science* 2023.
- Shafer G. Testing by betting. *JRSS-A* 2021.
- Wang R, Ramdas A. False discovery rate control with e-values. *JRSS-B* 2022.
- Dung PM. On the acceptability of arguments. *Artificial Intelligence* 1995. (+ Caminada on labellings.)
- Pollock JL. Defeasible reasoning. *Cognitive Science* 1987.
- Mayo DG. *Statistical Inference as Severe Testing*, 2018 (severe-test semantics of $\tau$).
- Benjamini Y, Yekutieli D. FDR under dependency. *Ann. Statist.* 2001 (the $\ln m$ penalty e-LOND avoids).
