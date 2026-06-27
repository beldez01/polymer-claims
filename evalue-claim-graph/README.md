# evalue-claim-graph

Formalization of the e-value ↔ claim-graph bridge — the mathematical spine behind Polymer Claims' "evidential licensing, not consistency" thesis.

> **Status (2026-06-26): the one real bug is SHIPPED.** The edge-kind refund gate is live in code —
> `grammar/src/polymer_grammar/defeat.py` (`is_null_bearing`, `entails_null` override) +
> `protocol/src/polymer_protocol/integrate.py` (`null_bearing_knockout_ids`): only null-bearing
> defeats (`rebut`/`undermine` entailing H₀) tombstone the `FDRTest`; warrant-only defeats de-license
> in the graph but leave the test live. See `fix-edge-kind-refund.md` §0 (IMPLEMENTED 2026-06-17).
> The notes below describing the bug as open are retained for the derivation; the fix is done.

## Contents
- **`formal-core.md`** — definitions in the codebase's own notation (`e_value`, `independence_tier`, `dimnames_hash`, `grounded_extension`, `FDRTest.retracted`), the unification of license/defeat/drift/FDR, and the first theorem to prove.
- **`refund-validity.md`** — attacks `formal-core.md` §7 and **resolves it**: conditional theorem + counterexample + design fix (below).
- **`fix-edge-kind-refund.md`** — the concrete code change for the one real bug: gate the e-LOND refund by null-bearing defeats (`defeat.py` classifier + `integrate.py`/`drift.py` call sites + tests).
- *(companion, on Desktop)* `Polymer Claims — E-value Claim Graph (Priority Note).md` — the external-facing position/priority note (less codebase-specific, more "why this is white space").

## Refund-Validity — RESOLVED (see `refund-validity.md`, v2 after independent review)
**Unconditional Refund-Validity is false**; the originally-proposed condition ("defeater is itself a live e-LOND discovery") is **insufficient**. What holds (Theorem 1, proved): **any allocation count ≤ the all-ever discovery count + null-bearing refunds ⟹ `q ≤ target_fdr`** — and this *includes the code's live allocation*, so `fdr.py`'s allocation is already safe (the earlier "switch to gross" idea was unnecessary). It **fails** for warrant-only defeats (`undercut`/`reinterpret`/`reclassify`), which can correctly de-license real effects and corrupt an effect-null FDR.

**The one real bug:** `retract_tests` (fdr.py:73) tombstones regardless of edge kind, so warrant-only refunds hit the ledger (the §4 counterexample applies as written). **Fix:** only null-bearing refunds (`rebut`/`undermine` that entail H₀) tombstone the FDRTest; warrant-only defeats de-license in the graph but leave the test live.

**Drift is NOT automatically safe** (review correction): "evidence weakened" ≠ "null true"; a drift retraction is null-bearing only when it entails the effect no longer exceeds τ — otherwise treat as warrant-only.

## Established vs. ours
Rests on Ville's inequality, the e-LOND FDR theorem (Xu–Ramdas 2024), and grounded-extension uniqueness (Dung 1995) — all `[E]`. The novel step is composing them through `retract_tests` (the refund), plus the rebutting/undercutting → counter-wealth/admissibility mapping.

## Honest gaps
Refund-Validity now proved (Theorem 1); remaining open: quantitative slack for *partial* null-bearing refunds; edge-kind→entailment soundness (typing ≠ entailment); `dimnames_hash`-distinctness ≠ statistical independence (the replication product rule); real evidence → valid e-value calibration (betas still synthetic pre-Phase-A); adversarial evidence.

## Next steps
1. ~~**Code fix:** gate `retract_tests` by edge kind — only null-bearing refunds tombstone.~~ **DONE (shipped, see status banner above).**
2. Spec the ClinVar retrospective experiment (early-warning of VUS reclassification) from the priority note §8 — the empirical result that tethers the theory.
3. Fold both into the Damon Runyon specific aim.
