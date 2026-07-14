# ⟳ BACKLOG LOOP — autonomous control spine

> **Started 2026-07-14** by an autonomous `/loop` directed at completing `docs/superpowers/BACKLOG.md`.
> This file is the loop's memory. It survives context summarization — **read it first on every fire.**
> Keep the *State* + *Queue* sections current at every item boundary. Check items off in `BACKLOG.md` too.

## Mission
Work through the entire `BACKLOG.md` serially: build the buildable items, verify each, check it off,
update docs. The user is away; act on established work, don't invent scope or make strategic calls.

## Operating policy (HARD RULES — do not violate autonomously)
1. **Preserve the invariants** on every change:
   - Corpus stays **exactly 4** collections.
   - `grammar/` and `protocol/` stay **pure + numpy-free**; no `polymer_claims` imports leak into them.
   - Any additive optional field must be **byte-identical when unset** (drop-when-None serializer; prove it).
   - **Two-stratum**: reported/literature claims never self-license; only recomputed claims join the spine.
   - Every new IR field **declares its scale-type + invariance group** (measurement-foundation discipline).
2. **Do NOT push to origin.** Shared checkout; pushing needs user coordination. Merge to **local main** only.
3. **Respect `DEFER` markers.** The backlog author (the user) marked these "don't build yet" — skip them,
   note them. Section 8 is entirely deferred.
4. **Do NOT make strategic/product decisions** (e.g. the product-identity fork, §9). Flag for the user.
5. **Data-gated items:** build + unit-test the machinery on fixtures/synthetic; mark the live run BLOCKED
   with exactly what real data it needs. Never fabricate genotypes/labels/data.
6. **Never colonize `polymer-db` or sibling project dirs.** Pin needed data subsets into `data/`.
7. Follow the repo workflow: branch off main → (spec exists or write one) → plan → TDD → per-change review
   → verify → merge local. Batch only trivial doc-fix items.
8. **Slow-suite discipline:** full `tests/` + `make_merged_universe.py` regen are ~13–63 min (real GDSC
   scan). Iterate with **targeted tests**; run the full gate only at item/branch close, and note if skipped.

## Work order (respect DEFER + data-gates; check off in BACKLOG.md as shipped)
- **A. Clean the tree** — finish `feat/cross-arm-relations` (restore real bundle → verify → merge local main).
- **B. §1 persistence & parameterization cluster** (interdependent, highest leverage):
  B1 measurement-space registry (shared prereq) → B2 accumulating-universe store → B3 re-parameterization
  evaluator (needs registry + additive "reinterpret" restriction-map edge) → B4 promoter SE-contract (data-gated live).
- **C. §2 warrant/independence** — C1 adapter-independence Step 0 probe (cheap, do-now) → R1–R5 arc,
  neg-whisper ②③④⑤, v2 slices 2/3.
- **D. §3 gate-integrity code debts** — incl. the logged `verify.py::_permitted_by_bar` reference_leaf
  exemption (retires the per-claim run_cycle workaround). Several concrete HARDEN items.
- **E. §4 attested calibration hardening** (slice-4 §11 deferrals).
- **F. §5 synbio capstone** — Phase 3 firewall → Phase 4 Durendal (HEADLINE) → Phase 5 wedge/demo; grammar GAPs.
- **G. §6 wedge/real-data** — mostly data-gated; build machinery, mark live runs blocked.
- **H. §7 infra/hygiene** — quick wins first: doc-reference fixes, CI workflow, test-skip visibility.
- **I. §9 foundations-concordance** — HARDEN "consume the declared-but-unenforced field" items
  (invariance_group check, measured-ρ independence, attested-log floor).
- **SKIP:** §8 (all DEFER), the product-identity fork + other strategic items (flag for user).

## State (update every fire)
- Branch: `feat/cross-arm-relations` (12/12 tasks done, whole-branch review READY-TO-MERGE).
- In flight: **A** — restoring the real merged-universe bundle, then merge to local main.
- Foundations digest: dispatched (agent), pending.
- Nothing merged by the loop yet.

## Flagged for the user (decisions / blockers I will NOT resolve autonomously)
- (none yet)

## Shipped by the loop (newest first)
- (none yet)
