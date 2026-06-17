# Refund-Validity: theorem, counterexample, and the one real fix

**Polymer Claims · evalue-claim-graph · 2026-06-17 · v2**

> Resolves the open conjecture of `formal-core.md` §7. **v2 incorporates an independent adversarial review** (2026-06-17) that corrected v1 on three points: it *proved* the live-allocation case I had left open (Claim E), supplied a correct expectation-level counterexample (Claim C), and corrected the drift classification (Claim F). Those corrections are folded in below and credited inline.
>
> **Result in one line.** Refund-Validity holds for the system's *actual* allocation (live), provided every ledger refund is genuinely **null-bearing**. It fails for warrant-only refunds. So the allocation math is fine; the **one real bug is tombstoning regardless of edge kind**.
>
> Legend: `[E]` established · `[P]` proved here · `[O]` open.

---

## 1. Setup and notation

e-LOND (Xu & Ramdas 2024) `[E]`. Claim stream $t=1,2,\dots$; each carries an e-value $e_t$ valid for null $H_0(t):\mu_B-\mu_A\le\tau$ ($\mathbb E[e_t]\le1$ for true nulls $t\in\mathcal H_0$; arbitrary dependence). $\gamma_t=(6/\pi^2)/t^2$, $\sum\gamma_t\le1$. Allocate $\alpha_t=\alpha\gamma_t(D_{t-1}+1)$, discover iff $e_t\ge1/\alpha_t$.

Counts:
- $G_{t-1}$ = **all-ever** prior discoveries (never decremented).
- $L_{t-1}$ = **live** prior discoveries at the moment $t$ is processed (decremented by retractions so far). Always $L_{t-1}\le G_{t-1}$.

Allocation conventions: **gross** uses $D_{t-1}=G_{t-1}$; **live** uses $D_{t-1}=L_{t-1}$. The code uses **live** (§6).

Refund: a defeat may tombstone a discovery (`retracted:=true`; frozen $\alpha,e$). Final live set $\mathcal L$ = discovered ∧ not retracted; $R_{\text{live}}=|\mathcal L|$, $V_{\text{live}}=|\mathcal L\cap\mathcal H_0|$, $q=\mathbb E[V_{\text{live}}/(R_{\text{live}}\vee1)]$.

A retraction is **null-bearing** if the accepted defeat *genuinely entails* $H_0(t)$ for the retracted claim (it bears on the effect-size null), versus **warrant-only** (it attacks the inference/interpretation while the effect may be real). *Note (from review): "null-bearing" must mean semantic entailment of $H_0(t)$, not merely an edge typed as such — otherwise the proofs below smuggle in soundness of the defeat system. Edge-kind is the operational proxy; entailment is the real condition.*

---

## 2. Monotonicity lemma `[P]` (review: CORRECT)

For integers $0\le k\le V\le R$, $R\ge1$: $\dfrac{V-k}{(R-k)\vee1}\le\dfrac VR.$

*Proof.* $R-k\ge1$: $(V-k)R\le V(R-k)\iff kV\le kR\iff V\le R$. $R-k=0$: then $k=R$, and $k\le V\le R$ forces $V=R$, so LHS $=0$. $\square$

Removing equal counts from numerator and denominator lowers the ratio — *provided the removed items are all true nulls.* That proviso is the whole game.

---

## 3. The theorem `[P]` (general allocation — v2, stronger than v1)

**Theorem 1 (Refund-Validity).** Suppose
1. **(allocation bounded by all-ever count)** $D_{t-1}\le G_{t-1}$ at every step — satisfied automatically by **both** gross ($=G_{t-1}$) and live ($L_{t-1}\le G_{t-1}$); and
2. **(null-bearing refunds)** every retraction genuinely entails $H_0(t)$ for the retracted claim.

Then $q=\mathbb E[V_{\text{live}}/(R_{\text{live}}\vee1)]\le\alpha$.

*Proof (charge against the all-ever count — the v1→v2 correction).* Let $\mathcal D$ be all discoveries ever made, $R=|\mathcal D|$, $V=|\mathcal D\cap\mathcal H_0|$. For a true null $t$, on the event $t\in\mathcal D$ we have $R\ge G_{t-1}+1$, so
$$\frac{\mathbf 1\{t\in\mathcal D\}}{R\vee1}\le\frac{\mathbf 1\{e_t\ge1/\alpha_t\}}{G_{t-1}+1}\le\frac{\alpha_t e_t}{G_{t-1}+1}=\alpha\gamma_t e_t\cdot\frac{D_{t-1}+1}{G_{t-1}+1}\le\alpha\gamma_t e_t,$$
where the last step uses (1): $D_{t-1}+1\le G_{t-1}+1$. Summing over true nulls and taking expectations, $\mathbb E[V/(R\vee1)]\le\alpha\sum_{t\in\mathcal H_0}\gamma_t\mathbb E[e_t]\le\alpha$.

Under (2), retractions remove only true-null discoveries, so $V_{\text{live}}=V-k$, $R_{\text{live}}=R-k$, $0\le k\le V\le R$. By the Lemma, $V_{\text{live}}/(R_{\text{live}}\vee1)\le V/(R\vee1)$ pointwise; take expectations. $\square$

**Why this is the right proof.** v1 charged against the *final* $R_{\text{live}}$ and broke, because later retractions can pull $R_{\text{live}}$ below $L_{t-1}+1$. Charging against $G_{t-1}$ sidesteps that entirely, and the live allocation's smaller $\alpha_t$ supplies the ratio $\frac{L_{t-1}+1}{G_{t-1}+1}\le1$ exactly where needed. **Consequence: the v1 recommendation to switch to gross allocation is unnecessary — live is already in the safe regime.** Hypothesis (1) is essentially free; hypothesis (2) does all the work.

---

## 4. Hypothesis (2) is necessary — the warrant/null counterexample `[P]`

**Proposition 2a.** Drop null-bearing and Refund-Validity fails *even when every defeat is epistemically correct.*

*Illustrative path.* $R=100$ gross discoveries — $99$ true positives (real effects $>\tau$, large $e_t$) and $1$ true-null false discovery. A single *correct* `undercut` ("all $99$ share a confounded normalization") de-licenses all $99$; live set $=\{$the true null$\}$, so $V_{\text{live}}/R_{\text{live}}=1$.

*Correct expectation-level proof (supplied by review — v1's "just repeat it" was invalid, since one true-null discovery cannot occur w.p.$\to1$ at fixed level while keeping $\mathbb E[e_t]\le1$).* Let true positives be discovered deterministically at positive density. For true nulls, set conditionally on the past $e_t=1/\alpha_t$ w.p. $\alpha_t$ and $e_t=0$ otherwise, so $\mathbb E[e_t\mid\mathcal F_{t-1}]=1$ (valid). Positive density of true positives gives $D_{t-1}\asymp t$, hence $\alpha_t\asymp c/t$ and $\sum_{t\in\mathcal H_0}\alpha_t=\infty$, so $\Pr(\ge1$ true-null discovery$)\to1$. If a correct warrant-only undercut then retracts all real-effect discoveries, the live set contains only true nulls whenever any occurred, so $q=\Pr(V_{\text{live}}>0)\to1\gg\alpha$. $\square$

**Diagnosis.** FDR is an invariant about the *effect-size null*; defeat is an operation about *epistemic warrant*. For `undercut`/`reinterpret`/`reclassify`, a correct defeat removes a *statistically true positive* — shrinking the denominator while the true-null numerator is untouched. The two notions coincide only for defeats that entail the null. *You may refund alpha-wealth for "the effect isn't there," but not for "the effect is there and means something else."*

---

## 5. The originally-proposed condition is insufficient `[P]` (review: CORRECT)

"Every defeater is itself a live e-LOND discovery" controls the *defeater's own* null, not the *defeated claims'* nulls. (i) A valid discovered undercutter can correctly destroy the warrant for many real effects (§4). (ii) **Out-degree is uncontrolled:** one node can retract $m$ true positives, changing the denominator by $m$ with no change to $V$. The correct axis is **per-edge entailment of the defeated claim's null**, not the defeater node's standing. A node-standing condition suffices only if strengthened to "every retraction edge is separately charged against the defeated claim's null" — i.e., back to null-bearing.

---

## 6. The code, and the one real fix

**Allocation — settled and SAFE** (`grammar/src/polymer_grammar/fdr.py`). `process_test` uses `alpha = target_fdr · _gamma(t) · (n_discoveries + 1)` (line 58) with `n_discoveries` excluding `retracted` (lines 45–46): **live allocation**. By Theorem 1 (hypothesis (1) holds since $L_{t-1}\le G_{t-1}$), this is in the proven-safe regime. **No allocation change is needed** — correcting v1, which wrongly flagged this as risky.

**The one real bug — refund scope.** `retract_tests` (lines 73–84) tombstones every defeated `claim_id` **regardless of edge kind**. So warrant-only defeats currently refund the ledger, and the §4 counterexample applies to the code as written. **Fix:** gate `retract_tests` so only genuinely null-bearing refunds tombstone the `FDRTest`; warrant-only defeats (`undercut`/`reinterpret`/`reclassify`) de-license in the graph (leave `grounded_extension`, lose `status=licensed`) but **leave the `FDRTest` live**. Then every ledger refund is null-bearing, hypothesis (2) holds by construction, and $q\le\alpha$ follows. A claim can thus be `rejected` in the graph while its evidence test stays a live discovery — which is *correct*: "the effect is real but no longer means claim $c$."

**Alternative (principled, longer-term).** Re-target $q$ to a **false-warrant rate** over the proposition "$c$ is licensed-warranted," so defeat and the metric speak about the same thing. Requires e-values calibrated to the warrant proposition (harder than the effect-size betting e-value already in the code). Recommend the edge-kind gate now; keep re-targeting as the direction.

---

## 7. Status

- **Resolved `[P]`:** Unconditional Refund-Validity is **false** (§4); the §7-formal-core condition is **insufficient** (§5); **Theorem 1 holds for any allocation $\le G_{t-1}$ — including the code's live allocation — under null-bearing refunds** (§3); the one code fix is edge-kind gating of `retract_tests` (§6).
- **Open `[O]`:**
  1. **Quantitative slack for partial null-bearing.** If a fraction of refunds are warrant-only, bound the excess: $q\le\alpha+(\text{true-positive retraction rate})$? Characterize.
  2. **Edge-kind → entailment soundness.** Theorem 1 needs refunds to *genuinely* entail $H_0(t)$; typing an edge `rebut`/`undermine` is only a proxy. What licenses the proxy? (A calibration/audit question, not a probability one.)
  3. **Drift classification (see §8).**

---

## 8. Drift is NOT automatically null-bearing (review correction)

v1 claimed "drift = self-undermine on the data ⇒ always null-bearing ⇒ safe." **Too strong.** A rerun yielding a weaker e-value, or falling below the original threshold, does **not** entail $H_0(t)$ is true — it may mean insufficient (new) evidence, changed measurement conditions, batch shift, population shift, or schema change. Those are warrant/data-quality defeats. For refund safety the bar is not "no longer licensed" but "this discovered claim is a **true null**."

**Corrected rule.** A drift-driven retraction is null-bearing — and so safe to tombstone — **only when the drift finding entails the effect no longer exceeds $\tau$ for the target estimand/materialization.** Otherwise treat drift as warrant-only: de-license, but leave the `FDRTest` live. This folds drift into the §6 edge-kind gate rather than giving it a free pass.

---

## 9. Bottom line for the project

The headline — *"defeat is a downward e-value update; license/defeat/drift/FDR are one operation"* — is **true exactly for refunds that entail the effect-null, and false for refunds that only move warrant.** The system's live-allocation ledger is already statistically sound; the single change that makes the FDR guarantee provably hold is to **stop tombstoning warrant-only (and non-null-bearing drift) defeats.** Independent review strengthened the theorem (live allocation is fine), tightened one counterexample, and removed a false safety claim about drift — net, the guarantee is *more* attainable than v1 thought, and the fix is smaller.
