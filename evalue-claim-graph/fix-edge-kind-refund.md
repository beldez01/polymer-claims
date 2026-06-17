# Fix: gate the e-LOND refund by null-bearing defeats

**Polymer Claims · evalue-claim-graph · 2026-06-17 · concrete code change**

> Implements the one real bug from `refund-validity.md` §6: `integrate` (and `drift`) tombstone defeated claims' `FDRTest`s **regardless of edge kind**, so warrant-only defeats refund the ledger and corrupt the effect-null FDR (the §4 counterexample). Fix: only defeats that **entail the effect-null** may tombstone; warrant-only defeats de-license in the graph but leave the test live.
>
> Files touched: `grammar/src/polymer_grammar/defeat.py` (classifier), `protocol/src/polymer_protocol/integrate.py` (the main call site). Plus tests.

---

## 0. STATUS — IMPLEMENTED (2026-06-17)

Shipped and green: grammar 360 / protocol 365 / umbrella 251 / isolation 2, all ruff-clean. (Viewer typecheck+build not run — change is Python-only and the viewer does not import the e-LOND logic.)

**What landed:**
- `defeat.py`: `entails_null: bool | None` on `DefeatEdge`; `NULL_BEARING_KINDS = {REBUT}`; `is_null_bearing(edge)`; `null_bearing_knockout_ids(defeated_ids, edges, strength, in_set, licensed_ids)`. Exported from `__init__.py`.
- `integrate.py`: `retract_ids` now = `null_bearing_knockout_ids(defeated_licensed ∪ removed, merged, strength_map, rr.in_set, licensed_ids)` over the **pre-drop `merged`** edges (so an AGM-removed claim's null-bearing attacker is still visible). All defeated claims still de-license in the graph; only null-bearing knockouts tombstone.
- New tests: grammar `test_defeat.py` (is_null_bearing, null_bearing_knockout_ids, the field default); protocol `test_integrate.py::test_warrant_only_defeat_delicenses_but_keeps_discovery_live` and `::test_reinterpret_defeat_keeps_discovery_live`.

**Three deviations from the spec below, discovered while implementing:**
1. **`rebut`-only, not `rebut`+`undermine`.** `undermine` edges are minted from failed satisfactions (`defeat.py:undermine_edges_from_failed_satisfactions`) where `UNDETERMINED` ≠ null; `undermine` is null-bearing only when explicitly flagged `entails_null=True`. (§1 already argued this; the implementation commits to it.)
2. **`drift.py` left UNCHANGED.** Drift's tombstone is justified by **staleness/re-scoping** — the discovery's materialization is no longer current — and `reopen_drifted` re-pends the claim so VERIFY re-tests it on new data (a *refresh*, not a pure removal). That is distinct from, and does not require, null-entailment. The §4 "gate drift" recommendation is **withdrawn**; drift is safe as-is.
3. **No double-count guard needed (§5.2 was already handled).** `verify.py`'s `already_tested` keys on `not t.retracted` and `_e_ok` reuses a live discovery, so a warrant-defeated claim that keeps its live test gets **no** duplicate on re-verify. Pre-existing; no change required.

---

## 1. The classification — which kinds may refund

The refund is sound only when the retracted claim is a **true null** (`refund-validity.md` Theorem 1, hypothesis 2). So a defeat may tombstone the ledger iff its acceptance **entails** $H_0(c):\ \mu_B-\mu_A\le\tau$.

| Edge kind | Entails effect-null? | May tombstone? |
|---|---|---|
| `rebut` — asserts the contrary conclusion (effect $\le\tau$) | **Yes** | **Yes** |
| `undermine` — attacks the data basis / a premise | **Only sometimes** | Only if flagged (see below) |
| `undercut` — attacks the inferential warrant | No | No |
| `reclassify` — disputes the pattern/profile | No | No |
| `reinterpret` — *"meaning moved, statistics unchanged"* | No (explicitly) | No |
| `evidence_for` — support | n/a | n/a |

**The `undermine` subtlety (found in the code).** `defeat.py:undermine_edges_from_failed_satisfactions` mints `undermine` edges from failed L2 satisfactions — but a `REFUTED` severe-test verdict bears on the null (the effect test went the other way) while an `UNDETERMINED` verdict (insufficient evidence) does **not**. And a generic "the data had a batch effect" undermine removes warrant without establishing the null. So `undermine` is heterogeneous; **kind alone cannot decide it.**

**Decision:** the safe *automatic* rule is **`rebut` only**. Carry an explicit, auditable per-edge flag `entails_null` for the genuine `undermine`-bears-on-null cases (e.g., refuted-satisfaction undermines, sample-swap discoveries). This also discharges the proof's open "typing ≠ entailment" soundness gap (`refund-validity.md` §7 open #2): the ledger refund keys on an explicit entailment claim, not on a coarse type. *This diverges from the reviewer's "rebut/undermine" grouping — deliberately, because the code shows `undermine` is not uniformly null-bearing.*

**Why "too conservative" is safe.** Under-refunding (leaving a true-null discovery live) cannot break the guarantee — the un-refunded process already satisfies $q\le\alpha$ by e-LOND; you only forgo a bonus improvement. **Over**-refunding (tombstoning a true positive via a warrant defeat) is the only thing that breaks it. So defaulting to `rebut`-only is the safe direction.

---

## 2. `grammar/src/polymer_grammar/defeat.py` — classifier + helper

Add the null-bearing set, an optional explicit override on the edge, and a knockout helper:

```python
# Only defeats that ENTAIL the effect-null (H0: effect <= tau) may refund the e-LOND
# ledger. Kind is a coarse proxy; `DefeatEdge.entails_null` carries it explicitly where
# the kind is ambiguous (notably `undermine`). See evalue-claim-graph/refund-validity.md.
NULL_BEARING_KINDS = frozenset({DefeatEdgeKind.REBUT})


def is_null_bearing(edge: DefeatEdge) -> bool:
    """True iff this defeat's acceptance entails the defeated claim's effect-null, so it may
    tombstone the FDRTest. Explicit `entails_null` overrides the kind default."""
    if edge.entails_null is not None:
        return edge.entails_null
    return edge.kind in NULL_BEARING_KINDS


def null_bearing_knockout_ids(
    defeated_ids: frozenset[str],
    edges: Iterable[DefeatEdge],
    strength: Mapping[str, StrengthVector | None],
    in_set: frozenset[str],
    licensed_ids: frozenset[str] = frozenset(),
) -> frozenset[str]:
    """Of the grounded-OUT `defeated_ids`, those knocked out by at least one EFFECTIVE,
    ACCEPTED (grounded-IN source), NULL-BEARING defeat. ONLY these may refund the ledger;
    the rest are de-licensed in the graph but keep their live FDRTest."""
    effective = effective_defeats(edges, strength, licensed_ids)
    out: set[str] = set()
    for e in edges:
        if (
            e.target in defeated_ids
            and is_null_bearing(e)
            and (e.source, e.target) in effective
            and e.source in in_set            # the attacker is itself accepted
        ):
            out.add(e.target)
    return frozenset(out)
```

And add the field to `DefeatEdge` (default `None` ⇒ fall back to kind ⇒ **existing rebut behavior unchanged**; only undermine/undercut/etc. change):

```python
class DefeatEdge(_Model):
    source: str
    target: str
    kind: DefeatEdgeKind
    note: str | None = None
    provisional: bool = False
    entails_null: bool | None = None   # explicit effect-null entailment override (refund gate)
```

Export `NULL_BEARING_KINDS`, `is_null_bearing`, `null_bearing_knockout_ids` from `__init__.py`.

---

## 3. `protocol/src/polymer_protocol/integrate.py` — split the refund

Currently (line 91/98): **every** grounded-OUT licensed claim (plus AGM removals) is tombstoned. Change so only null-bearing knockouts refund; **all** defeated claims still de-license (graph status unchanged).

```python
defeated_licensed = {
    c.id for c in rr.claims if c.id in rr.flipped_out and c.status == Status.LICENSED
}
# ... reinstated, removed as before ...

# NEW: only null-bearing knockouts refund the ledger. Recompute the post-contest IN set
# and the strength map over the reconciled edges.
strength_map = {c.id: c.strength for c in rr.claims}          # confirm Claim.strength field
licensed_now = frozenset(c.id for c in rr.claims if c.status == Status.LICENSED)
new_in = grounded_extension(
    [c.id for c in rr.claims], rr.edges, strength_map, licensed_ids=licensed_now
)
null_bearing = null_bearing_knockout_ids(
    frozenset(defeated_licensed), rr.edges, strength_map, new_in, licensed_ids=licensed_now
)

# de-license ALL defeated (graph); tombstone ONLY the null-bearing subset (+ null-bearing AGM removals, §5)
retract_ids = null_bearing | _null_bearing_removed(removed, rr)   # see §5
new_claims = tuple(
    _reject(c) if c.id in defeated_licensed         # graph de-license unchanged for all
    else _reinstate(c) if c.id in reinstated
    else c
    for c in rr.claims
)
new_ledger = retract_tests(corpus.fdr_ledger, retract_ids)
```

So a warrant-only-defeated claim becomes `REJECTED` (grounded-OUT) **with its `FDRTest` still live** — which is correct: the effect is real, only the interpretation moved.

---

## 4. `protocol/src/polymer_protocol/drift.py` — drift is a *refresh*, not a refund

The reviewer correctly killed "drift is auto-null-bearing." But reading the flow, drift's real safety mechanism is different: **drift tombstones a *stale* test and re-tests on the new materialization.** Its safety comes from the atomic re-test (the denominator is restored if the effect persists on current data), not from null-entailment.

- **Keep tombstoning drift-reopened claims ONLY if the same cycle re-tests them on the new `dimnames_hash`** (reopen → PENDING → VERIFY appends a fresh `FDRTest`). Then the live set is refreshed, not just shrunk.
- **If a drift event drops a claim without re-testing** (no current materialization), that is a tombstone-without-retest = a warrant-only removal = the §4 danger. In that case do **not** tombstone; de-license only.
- **Transient window:** if re-test lands the *next* cycle, there is a between-cycle interval where the denominator is shrunk (mild, transient FDR inflation). Acceptable, but note it; tightening to same-cycle re-test removes it.

Concretely: gate `retract_tests(corpus.fdr_ledger, reopened)` (drift.py:109) on "will be re-tested this/next cycle"; otherwise leave the tests live.

---

## 5. Coupled changes that must land together

1. **AGM removals (`removed`).** `restore_consistency` may remove claims with no defeat edge. Only tombstone an AGM-removed claim if its removal entails the null (a null-bearing contradiction). Default: **don't** tombstone AGM removals (`_null_bearing_removed` returns only those with a null-bearing cause). Conservative = safe.
2. **No double-count on reinstatement.** A warrant-defeated claim keeps its live `FDRTest`. If it is later `REINSTATED` → `PENDING` → re-verified, VERIFY must **not append a second** `FDRTest` for the same `claim_id` while one is live. Either (a) skip re-test when a live discovery already exists, or (b) tombstone-then-retest atomically. Pick (a) for warrant defeats (the effect test still stands; only the graph changed). **This is the highest-risk interaction — verify the VERIFY append path.**
3. **Semantics of `n_discoveries` shifts** from "live *licensed* discoveries" to "live *effect-null* discoveries." A live discovery no longer implies LICENSED (a warrant-defeated claim is grounded-OUT, so not licensed, yet its test is live). The licensing predicate is unaffected (it ANDs grounded-IN with the e-LOND gate), but any code that reads `ledger.discoveries` as "the licensed set" must be audited — use `grounded_extension` for licensing, the ledger for FDR.

---

## 6. Tests to add (mirror `test_fdr.py` / `test_defeat.py`)

- `test_rebut_knockout_tombstones`: licensed claim grounded-OUT by an effective accepted `rebut` ⇒ `FDRTest.retracted` True, `n_discoveries` drops.
- `test_undercut_knockout_keeps_test_live`: licensed claim grounded-OUT by `undercut` ⇒ status `REJECTED` but `FDRTest.retracted` False, `n_discoveries` unchanged. *(This is the regression that proves §4 is fixed.)*
- `test_reinterpret_and_reclassify_keep_test_live`: same as above for those kinds.
- `test_undermine_default_no_tombstone_but_entails_null_flag_tombstones`: `undermine` with `entails_null=None` keeps test live; with `entails_null=True` tombstones.
- `test_mixed_knockout_tombstones_if_any_null_bearing`: claim attacked by both an accepted `undercut` and an accepted `rebut` ⇒ tombstones (a null-bearing reason exists).
- `test_warrant_defeat_no_duplicate_ledger_on_reinstate`: warrant-defeat → reinstate → re-verify appends **no** second live test (the §5.2 guard).
- **Update** any existing test that asserts warrant-kind defeats tombstone — that behavior is the bug being fixed; those assertions invert.

---

## 7. Invariants to assert (property tests)

- **Refund soundness:** every `retracted` `FDRTest` corresponds to a claim with at least one effective, accepted, null-bearing knockout (or null-bearing AGM removal). No warrant-only tombstones.
- **Licensing unchanged:** `LICENSED ⇒ grounded-IN ∧ live discovery` still holds (we only *loosened* the converse).
- **No duplicate live test** per `claim_id`.
- **FDR target:** on randomized corpora with arbitrary warrant defeats, the live false-license rate stays $\le$ `target_fdr` (Theorem 1 made operational).

---

## 8. Back-compat / risk

- `entails_null` defaults to `None` → existing **`rebut`** behavior is byte-identical; only the previously-buggy warrant tombstones change. Existing tests asserting the buggy behavior must flip (§6).
- The change is **isolated to the refund decision** — allocation (`process_test`), the discovery rule, and grounded semantics are untouched.
- Identifiers to confirm against the repo before coding: `Claim.strength` (the per-claim `StrengthVector`); the `rr` (RevisionResult) fields `claims`/`edges`/`flipped_out`/`flipped_in`/`retraction`; and the VERIFY path that appends `FDRTest`s (for §5.2).
