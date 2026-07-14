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
- **On `feat/reparam-evaluator`** (B3 in progress, grounding). main is `b80957c` (30 ahead of origin, NOT pushed).
- **B1 + B2(primitive) DONE. IN PROGRESS: B3 — re-parameterization evaluator.**
- **B3 KEY PIVOT (2026-07-14):** the "reinterpret" non-contradiction edge the spec (§4) flagged as a NEEDED
  grammar change **ALREADY EXISTS** — `RelationKind.RESTRICTION_MAP` in `grammar/src/polymer_grammar/leaf.py:138`
  (added by the cross-arm relations work; a non-attack relation CLAIM, stored in Corpus.claims via `is_relation`,
  NOT a new collection → Corpus stays 4). So B3 = **NO grammar change**; instead: (a) PROTOCOL sheaf/Duhem
  suppression hook — treat two claims linked by a RESTRICTION_MAP relation as NOT a contradiction (this is the
  cross-arm "Slice 2 sheaf wiring" that was deferred; pure-protocol, byte-identity when no such relation);
  (b) UMBRELLA evaluator: trigger REJECTED+REFUTED → hybrid LLM generator (grounded by B1 `resolve_space`, mirror
  `relation_proposer.py`'s injected-client + `.anthropic` tripwire) → declare-and-charge K e-LOND slots upfront →
  re-test each alternate via the UNCHANGED gate → emit a RESTRICTION_MAP relation claim linking original↔alternate.
  Retain original REJECTED verbatim (residualism); depth-1; synthetic two-space fixtures (real MGMT→TMZ = B4-gated).
  DECOMPOSE across fires: (B3a) protocol suppression hook → (B3b) umbrella evaluator. Confirm suppression-wired
  status from the Explore agent's map before building.
- **NEW follow-up queued:** B2-integration (wire real populate_universe + viewer at the store) — SLOW-pipeline-gated,
  deferred by the loop; see BACKLOG §1.
- Foundations digest DONE → `notes/2026-07-14-foundations-digest-for-loop.md` (read it; it grounds B2/§2).
- **B2 grounding done:** accumulating-store spec read in full (`specs/2026-07-10-accumulating-universe-store-design.md`).
  Store = append-only content-addressed JSONL (source of truth) + DuckDB facet layer; persists the WHOLE Corpus
  incl. `fdr_ledger`; load→propose→dedup→register→license→persist-back; re-run mints 0 claims. Cheapest first move
  (§6): JSONL record (modality on contract) → `populate_universe` appends → census query → viewer facets.
- **B2 next-fire notes:** the registry (B1) is now available — the store's census (Spec 1 §5) can query
  `measurement_space.coverage()`/`available_spaces()`. Real ground truth (from B1's code map): a "space" =
  `(contract_uid, row_prefix)`; `SEContractRef` carries no modality; `Provenance` has NO modality/parameterization
  field (Spec 1 §4's choice-vs-realized split is unimplemented — the store may need to decide how to carry the
  realized-modality facet: cleanest is to derive it from the claim's `data_ref` contract via the registry, not a
  new grammar field). Check DuckDB availability (optional dep) before committing to the SQL layer; a pure-python
  facet layer is an acceptable v1 fallback if DuckDB isn't wanted as a dep. Watch: `populate_universe` today
  starts a FRESH fdr_ledger each run — the store must persist + reload it (the highest-value regression test).

## Test/gate cadence
- Fast gate (per change): `cd grammar && uv run pytest -q` (~0.5s, 602) · `cd protocol && uv run pytest -q` (~2s, 509)
  · targeted umbrella `uv run --project . pytest tests/<file> -q` · `ruff check` touched files.
- Full gate (item close only, SLOW ~13–63 min): `bash scripts/check-all.sh`. Note when skipped.

## Flagged for the user (decisions / blockers I will NOT resolve autonomously)
- **Push to origin** is deferred (25 commits ahead) — needs your coordination (shared checkout). Loop will keep
  accumulating on local main.

## Shipped by the loop (newest first)
- **2026-07-14 — B2 (store primitive): accumulating-universe store** (`feat/accumulating-store` → local main, ff).
  `src/polymer_claims/accumulating_store.py`: `corpus.json` whole-Corpus snapshot (reuses io.py → ledger position
  round-trips) + append-only content-addressed `claims.jsonl`; `accumulate` load→dedup→register(injected)→persist
  mints 0 on re-run; `census()` (subject×modality×status, modality via B1 registry) reports coverage gaps. Pure-python
  (no DuckDB dep). 8 synthetic tests; grammar/protocol untouched; Corpus 4. Live populate/viewer wiring deferred
  (B2-integration, slow-pipeline-gated).
- **2026-07-14 — B1: measurement-space registry** (`feat/measurement-space-registry` → local main, ff).
  Authored the deferred spec (`specs/2026-07-14-measurement-space-registry-design.md`) + umbrella module
  `src/polymer_claims/measurement_space.py`: catalog of 9 real contract spaces keyed `(contract_uid, row_prefix)`,
  each declaring controlled `Modality` + Stevens `ScaleType` + `invariance_group` (the scale/invariance metadata
  that lived nowhere — advances §9). `resolve_space` grounds the reparam evaluator's proposals to contracts that
  actually resolve (never fabricates). 11 tests; grammar/protocol untouched; Corpus 4.
- **2026-07-14 — Phase A: `feat/cross-arm-relations` merged to local main** (`d69c03a`, ff). Restored the real
  1386-node bundle (discarded the 46-node demo), fixed 1 branch-introduced ruff (unused `FDRLedger` import),
  reconfirmed grammar 602 + protocol 509 + relations e2e 3/3 green. Branch deleted. (Not a numbered backlog line —
  closing in-flight work to get a clean main to branch from.)
