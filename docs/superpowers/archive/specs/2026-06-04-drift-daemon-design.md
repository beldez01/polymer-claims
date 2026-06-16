# #5a DRIFT daemon — design spec

> **Status:** approved design, 2026-06-04. First slice of sub-project #5 (the daemons + loop-economics).
> Roadmap: `docs/superpowers/roadmaps/2026-06-04-sub5-daemons-roadmap.md`. Builds on the COMPLETE
> protocol spine (#1–#4b). Rhythm: this spec → plan (writing-plans) → subagent-driven build → merge no-ff → memory.

## What this builds

The **DRIFT daemon**: a pure, caller-scheduled detector that finds LICENSED claims whose minted
materialization context (the api/data versions they were licensed under) no longer matches the world's
*current* materialization context. The world moved; a claim licensed under the old world may no longer
hold. DRIFT **flags** these claims; it does **not** mutate them. A separate, explicit opt-in action
(`reopen_drifted`) re-opens flagged claims to PENDING for re-pursuit — that action is what makes the new
`MATERIALIZATION_DRIFTED` reason live, and a caller (eventually #5d loop-economics) decides whether to
invoke it.

This separation — **detect (daemon, flag-only) vs. act (explicit helper)** — is the load-bearing design
decision (the two brainstorm forks resolved to: *flag-only, never mutate* + *add a new PendingReason*).

## The seams (already in the codebase)

- **`MaterializationContext`** (`grammar/licensing.py`): `{id, api_version, data_version, note}`. Every
  LICENSED claim carries `licensing.satisfactions[*].materialization` — the exact context(s) it was
  licensed under.
- **`Satisfaction`** (`grammar/licensing.py`): `{verdict, materialization}`; a `Licensing` record holds a
  tuple of these (replication route ⇒ ≥2 across distinct materializations).
- **`Claim` validators** (`grammar/claim.py`): `_licensing_only_when_licensed` (a `licensing` block is
  valid ONLY when `status==LICENSED`) and `_pending_reason_iff_pending` (`status==PENDING` requires a
  `pending_reason`; a non-PENDING claim must NOT carry one). Re-opening a LICENSED claim to PENDING is
  therefore a **three-part atomic mutation**: status LICENSED→PENDING, **drop** the licensing block, **set**
  a pending_reason.
- **`PendingReason`** (`grammar/status.py`): 9 typed reasons today, incl. `ONTOLOGY_TERM_OBSOLETE` — the
  exact precedent for a "world moved underneath the claim" reason. DRIFT adds the 10th.
- Protocol record/ledger precedents (`generate.py` `GenerationRecord`, `ledger.py` `SelectionLedger`):
  protocol-side state lives in threaded records, NEVER in a 5th Corpus collection.

## Component 1 — grammar (additive)

Add one enum member to `grammar/src/polymer_grammar/status.py`:

```python
class PendingReason(str, Enum):
    ...
    MATERIALIZATION_DRIFTED = "materialization_drifted"
```

Export is automatic (PendingReason is already exported). Additive, fully back-compat — no existing claim or
validator changes. First grammar touch since #4b-1.

## Component 2 — `protocol/src/polymer_protocol/drift.py` (the daemon)

### Records

```python
class DriftFinding(_Model):
    claim_id: str
    re_executable: bool                              # claim.evaluation_plan is not None
    licensed_versions: tuple[tuple[str, str], ...]   # (api_version, data_version) pairs it was licensed under

class DriftRecord(_Model):
    current: MaterializationContext                  # echoed for audit
    examined: int                                    # number of LICENSED claims scanned
    drifted: tuple[DriftFinding, ...]
```

Both subclass `_Model` (frozen, `extra="forbid"`, tuples). `licensed_versions` is the audit trail of what
the claim was licensed under (the only place the prior-licensing versions survive after a re-open, since the
grammar forbids `licensing` on a non-LICENSED claim).

### The pass

```python
def drift_pass(corpus: Corpus, *, current: MaterializationContext) -> tuple[Corpus, DriftRecord]:
    ...
```

Behavior:
1. Scan claims with `status == Status.LICENSED` (only these carry a `licensing` block). `examined` counts them.
2. For each, collect its satisfaction materializations:
   `mats = claim.licensing.satisfactions` → each `.materialization`.
3. **Freshness rule (version equality, D3):** a claim is **fresh** if ANY satisfaction's materialization
   matches `current` — `m.api_version == current.api_version AND m.data_version == current.data_version`
   (id/note ignored). It is **drifted** if NO satisfaction matches.
4. For each drifted claim, append a `DriftFinding(claim_id, re_executable=(claim.evaluation_plan is not None),
   licensed_versions=<sorted unique (api,data) pairs from its satisfactions>)`.
5. Return `(corpus, DriftRecord(current=current, examined=<n>, drifted=<sorted by claim_id>))`.

**Flag-only invariant:** the returned Corpus **is the input object** (identity-unchanged). DRIFT writes
nothing to the corpus. The signature keeps the `Corpus→(Corpus, record)` daemon contract so loop-economics
chains every daemon uniformly.

Pure / deterministic: no clock, no randomness, no environment read. `current` is an argument. Findings are
sorted (deterministic order). A claim with no satisfactions cannot be LICENSED (the `Licensing` validator
requires ≥1), so step 3 always has ≥1 materialization to compare.

## Component 3 — `reopen_drifted` (in `drift.py`, the explicit opt-in action)

```python
def reopen_drifted(corpus: Corpus, record: DriftRecord, *, require_plan: bool = True) -> Corpus:
    ...
```

A **separate** pure function the daemon never calls itself (preserving flag-only). For each finding in
`record.drifted`:
- If `require_plan` and not `finding.re_executable`: **skip** (leave the claim LICENSED — a planless claim
  re-opened to PENDING can never self-relicense, so re-opening it would strand it in the PENDING pool; this
  folds the cap-not-bar wisdom into the action).
- Otherwise rebuild the claim with **one atomic** mutation:
  ```python
  claim.model_copy(update={
      "status": Status.PENDING,
      "licensing": None,
      "pending_reason": PendingReason.MATERIALIZATION_DRIFTED,
  })
  ```
  Setting all three fields in one `model_copy` produces a consistent object that satisfies both `Claim`
  validators. (`model_copy(update=...)` bypasses validators — used deliberately; a test re-validates the
  output via `Claim.model_validate` to pin that the produced state is valid.)
- Claims not in `record.drifted` (and skipped planless ones) pass through unchanged.

Returns a new `Corpus` with the rebuilt claims tuple (other 3 collections untouched). Pure / deterministic.
The caller is responsible for passing a `record` produced from the *same* corpus (findings reference claim
ids; a missing id is silently skipped — defensive, never raises).

## Scope fences (explicit non-goals this slice)

- **D3 — version match is equality only.** Semver-style "compatible-version" matching is deferred (YAGNI).
- **D4 — oracle tier is NOT consulted.** DRIFT is materialization-only. Oracle-tier movement weakening
  dependent claims is #5b ORACLE-VALIDATION.
- **No `run_cycle` wiring.** `drift_pass` and `reopen_drifted` ship as standalone pure functions. *When* to
  run DRIFT and *whether* to auto-reopen is loop-economics (#5d). This keeps the slice small and the purity
  airtight; the daemon contract (`Corpus→(Corpus, record)`) is what #5d will schedule.
- **Prior-licensing provenance loss on re-open.** A re-opened claim's licensing proof survives ONLY in the
  DriftRecord's `licensed_versions`, not on the claim (grammar forbids `licensing` on non-LICENSED). A richer
  on-claim prior-licensing history is a noted follow-up, not this slice.

## Invariants preserved

- One-way isolation: `drift.py` imports from `polymer_grammar` (Status, PendingReason, MaterializationContext,
  Claim) and `.corpus`; grammar never imports protocol.
- Corpus stays **4 collections**. Drift state lives in the returned `DriftRecord`, not the Corpus.
- All new models frozen + tuples. Pure / deterministic / synchronous; everything time-like (`current`) passed in.
- Exports: add `DriftFinding`, `DriftRecord`, `drift_pass`, `reopen_drifted` to `protocol/__init__.py`.

## Testing

**Grammar (`grammar/tests/`):**
- `PendingReason.MATERIALIZATION_DRIFTED` exists and round-trips its string value.
- A `Claim` can be constructed with `status=PENDING, pending_reason=MATERIALIZATION_DRIFTED` (validators pass).

**Protocol — `drift_pass`:**
- A LICENSED claim licensed under a stale materialization (versions ≠ current) → appears in `drifted`.
- A LICENSED claim with a satisfaction matching `current` exactly → NOT drifted (fresh).
- A replication claim (M1 + M2, both stale) → drifted; (one of M1/M2 == current) → fresh (any-match rule).
- Non-LICENSED claims (CONJECTURED / PENDING / REJECTED) are never scanned (`examined` counts LICENSED only).
- Returned corpus is the **same object** as the input (`out_corpus is corpus`).
- `re_executable` reflects `evaluation_plan` presence; `licensed_versions` lists the right pairs.
- Deterministic: same inputs → byte-identical record; findings sorted by claim_id.

**Protocol — `reopen_drifted`:**
- A re-opened drifted claim: `status==PENDING`, `licensing is None`, `pending_reason==MATERIALIZATION_DRIFTED`.
- The re-opened claim **round-trips** through `Claim.model_validate` (produced state is valid).
- `require_plan=True` (default): a planless drifted finding is **skipped** (claim stays LICENSED);
  `require_plan=False`: it is re-opened too.
- Non-drifted claims pass through unchanged; the other 3 Corpus collections are untouched.
- A finding whose claim_id is absent from the corpus is silently skipped (no raise).
- Pure: calling twice yields equal corpora.

## Files

- Modify: `grammar/src/polymer_grammar/status.py` (one enum member)
- Test:   `grammar/tests/test_status.py` (or the existing status test file) — enum + claim-construction
- Create: `protocol/src/polymer_protocol/drift.py`
- Modify: `protocol/src/polymer_protocol/__init__.py` (4 exports)
- Test:   `protocol/tests/test_drift.py`
