# L2 — Licensing Bridge (Phase 3 Spec)

Date: 2026-06-01
Status: Phase spec
Refines: `2026-05-31-unified-claim-foundations-spec.md` §3.4 (LICENSING BRIDGE).
Builds on: Phase 1 + L1 (grammar pkg merged). Uses frozen `_Model`, `Status`, `Claim`.

---

## 0. What this phase is

A claim's `status` can currently be set to `LICENSED` by fiat. L2 makes LICENSED something a claim can *earn* and *show its work for* — the bridge from evidence to entitlement. It captures **how** a claim was licensed: in **which materialization(s)** its inference was satisfied, by **which route** (a severe test, or replication across independent materializations), and against **what closure of rival explanations**.

Two forks resolved (user-confirmed 2026-06-01):
- **Additive, not a hard gate.** Add an optional `Claim.licensing`; a `LICENSED` claim without one still builds (consistent with how `conclusion` was introduced). A later "tightening" phase makes `conclusion` + `licensing` required together — that's where "no LICENSED-simpliciter" becomes a hard invariant.
- **Licensing logic only.** This phase models the satisfaction/route/rival-closure logic. The grounding node (produced_by / licensed_by + asserting-agent + role + content-addressed frame) groups with the later protocol-provenance phase.

### Success criterion (inherited)
- **Sensitivity:** the record can express the *difference* between "passed a severe test once" and "replicated across independent runs" — two genuinely different epistemic warrants.
- **Specificity:** a licensing record cannot exist without declaring its **rival-set closure** — so the schema never represents a verdict as unconditionally established. The residual (an open catch-all) is *surfaced*, never hidden.

---

## 1. Primitives (new module `licensing.py`)

```
SatisfactionVerdict = satisfied | refuted | undetermined        # σ, three-valued

MaterializationContext = {                                       # M — never implicit
    id: str,                # stable id of this materialization run/context
    api_version: str,
    data_version: str,
    note: str | None = None,
}

Satisfaction = {                                                 # the (σ, M) pair
    verdict: SatisfactionVerdict,
    materialization: MaterializationContext,
}
# Satisfaction is NEVER a context-free Boolean — it always carries its M.

LicenseRoute     = severe_test | replication
RivalSetClosure  = enumerated | ontology_bounded | open_acknowledged

Licensing = {
    route:              LicenseRoute,
    satisfactions:      tuple[Satisfaction, ...],   # ≥1; replication ⇒ ≥2 distinct M
    rival_set_closure:  RivalSetClosure,            # REQUIRED — no LICENSED-simpliciter
    rivals_considered:  tuple[str, ...] = (),       # CURIEs of rivals weighed
    note:               str | None = None,
}
```

### Licensing invariants (model validators)
1. `satisfactions` non-empty.
2. **A Licensing record represents *successful* licensing** → every satisfaction's `verdict == satisfied`. (A refuted/undetermined satisfaction belongs to a REJECTED/PENDING claim, not a Licensing record.)
3. `route == replication` ⇒ at least **2** satisfactions **with distinct `materialization.id`s** (M1 ∧ M2 across *independent* materializations). `route == severe_test` ⇒ the ≥1 from (1) suffices.
4. `rival_set_closure == enumerated` ⇒ `rivals_considered` non-empty (you claimed to enumerate them, so name them). `ontology_bounded` / `open_acknowledged` may leave it empty.

All models inherit frozen `_Model` (immutable, hashable); tuple fields keep deep immutability.

---

## 2. Wiring into `Claim`

One optional, additive field + one consistency validator:

```
Claim.licensing: Licensing | None = None
```
Validator (mirrors the `pending_reason` pattern): **`licensing` may be present only when `status == LICENSED`.** (A licensing record on a non-licensed claim is incoherent.) The converse — LICENSED *requires* licensing — is **deferred** to the later tightening phase, so all existing `LICENSED`-without-licensing tests stay green.

No other `Claim` change.

---

## 3. Module layout (additive)

```
grammar/src/polymer_grammar/
  licensing.py   # NEW: SatisfactionVerdict, MaterializationContext, Satisfaction,
                 #      LicenseRoute, RivalSetClosure, Licensing (+ invariants)
  claim.py       # MODIFY: add licensing: Licensing | None = None + present-only-when-LICENSED validator
  __init__.py    # MODIFY: export new names
tests/
  test_licensing.py          # NEW
  test_claim_licensing.py     # NEW (wiring + back-compat)
```

Isolation guard (`test_isolation.py`) still applies.

---

## 4. Acceptance criteria

- `Satisfaction` always pairs a verdict with an `M`; no context-free boolean path exists.
- `Licensing` rejects: empty satisfactions; any non-`satisfied` satisfaction; `replication` with <2 or non-distinct M; `enumerated` closure with empty `rivals_considered`.
- `Licensing` with `severe_test` + 1 satisfied M builds; `replication` + 2 distinct satisfied M builds.
- `Claim.licensing` is optional; a `LICENSED` claim without it still builds (back-compat); a non-LICENSED claim **with** licensing is rejected.
- Models immutable + hashable; full suite green; ruff clean; isolation guard passes.

---

## 5. Non-goals (this phase)

- **Not** a hard "LICENSED requires licensing" gate (deferred to the tightening phase).
- **Not** the grounding node / asserting-agent / content-addressed frame (later protocol-provenance phase).
- **Not** the evaluator that *produces* satisfactions by running the DAG (Phase 8) — L2 defines the *schema* these records take; they're authored/supplied for now.
- **Not** Bayesian posterior / likelihood-ratio advisory facets (later; they never license anyway).
- **Not** auto-deriving rivals or closure.

---

## 6. Connections to library

- Realizes unified spec §3.4 + the schema-overview "Licensing bridge" panel (`license_route`, `rival_set_closure`).
- The later evaluator (Phase 8) becomes the producer of `Satisfaction`s; the protocol's VERIFY stage writes `license_route` + `rival_set_closure` (knowledge-generation protocol §Stage 6) — this phase is the schema they target.
- `MaterializationContext` pins `api_version`/`data_version`, aligning with the existing provenance discipline (and the live v1.2 IR's per-layer version metadata).
- Plan: `docs/superpowers/plans/2026-06-01-L2-licensing-bridge.md`.
