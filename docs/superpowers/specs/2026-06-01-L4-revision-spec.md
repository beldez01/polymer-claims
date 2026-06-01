# Phase 6 — L4: AGM/TMS belief revision — design spec

Date: 2026-06-01
Status: design (feeds `writing-plans`)
Layer: L4 (REVISION) of the v1.3 grammar — see unified spec §3.5
Depends on: Phases 1–5 (`status`, `strength`, `proposition` neighborhood, `claim`, and the Phase-5 `defeat.grounded_extension` + `blame` set-algebra pattern)

## 0. Reading guide (this layer in one paragraph)

L4 is about **change over time**: adding, retracting, and revising claims in a corpus, and recomputing what is still believed. Classical AGM belief revision (Alchourrón–Gärdenfors–Makinson 1985) needs two things we must supply concretely: a **consequence operation** (what follows from what) and an **entrenchment ordering** (what we give up last). We ground the first in the L1 inferential neighborhood we already built (`entails` / `incompatible_with` edges) — so this is **belief-*base* AGM** (Hansson) over a finite corpus, not infinite closed-theory AGM. We derive the second as a **partial** order from the Phase-4 `StrengthVector` + `Status`. Because entrenchment is partial, a revision's retraction choice can be **ambiguous**, which we surface as a robust/underdetermined spread exactly like the Phase-5 Duhem blame-sets. After any edit, the **monotone, PTIME** part — recomputing which claims are IN — is just the Phase-5 `grounded_extension`. The non-monotone part is the edit itself.

## 1. Goal & scope

Add `grammar/revision.py`: a corpus-level module of pure functions implementing AGM expansion / contraction / revision over the claim base, with a partial entrenchment ordering and ambiguity-surfacing retraction. No new `Claim` fields (corpus-level, like `defeat.py` / `blame.py`). Isolation guard holds (no `polymer_formalclaim` import). Frozen `_Model`, tuples/frozensets.

**Out of scope (Phase 7+):** the `representation_revision` meta-tier (claims about the IR itself), the four human-judgment ports, SAFETY-GATE — all protocol-imposed, not grammar. n-ary inconsistency (the L1 grammar currently expresses only binary `incompatible_with`); conjunctive (multi-premise) entailment.

## 2. The consequence operation (our "logic")

AGM revises modulo a consequence operation `Cn`. Ours is the **finite closure over the L1 proposition neighborhood**, identifying each claim with its `conclusion` Proposition (claims with `conclusion is None` are inert for entailment — they carry no asserted content to derive from).

- **`entails_closure(seed_hashes, claims) -> frozenset[str]`** — transitive closure over `ENTAILS` `NeighborEdge`s. Build a directed graph `content_hash -> {entailed content_hashes}` from every claim's `conclusion.neighborhood`, then BFS from `seed_hashes`. Returns all reachable hashes (including the seeds).
- **`corpus_entails(claims, prop_hash) -> bool`** — `prop_hash ∈ entails_closure({c.conclusion.content_hash for c in claims with a conclusion}, claims)`.
- **`is_consistent(claims) -> bool`** — `True` iff no `INCOMPATIBLE_WITH` edge resolves *within* the set: there is no pair of claims `a, b` (both with conclusions) where `a.conclusion` has an `incompatible_with` edge whose `target` equals `b.conclusion.content_hash`. (This is the same incompatibility L3 turns into mutual `rebut` via `derived_rebut_edges`.)

> **Note on entailment shape.** L1 `entails` edges are *single-premise* (one proposition entails another). So "the corpus entails p" reduces to graph reachability, and the only inconsistencies expressible are *binary* (`a` incompatible with `b`). Multi-premise/conjunctive entailment and n-ary conflicts are deferred (§1 out-of-scope). This keeps every operation below polynomial.

## 3. Entrenchment — a partial order from StrengthVector + Status

`compare_entrenchment(a: Claim, b: Claim) -> Entrench` where `Entrench` is an enum `{GREATER, LESS, EQUAL, INCOMPARABLE}` (`a` relative to `b`). More entrenched = given up *last*.

Lexicographic, with a partial inner step:
1. **Status tier** (coarse, total): `LICENSED(4) ≻ PENDING(3) ≻ EXPLORATORY(2) ≻ CONJECTURED(1) ≻ REJECTED(0)`. Different tiers ⇒ the higher tier is `GREATER`.
2. **Same tier ⇒ strength sub-order** (fine, *partial*): compare on the entrenchment-relevant axes `(severity, evidence_against_null)` of `StrengthVector`:
   - both present: `a ≻ b` (GREATER) iff `a` ≥ `b` on **both** axes with **at least one strict**; `LESS` iff the reverse; `EQUAL` iff equal on both; otherwise `INCOMPARABLE` (each higher on a different axis).
   - exactly one has a `strength`: the one **with** strength is `GREATER` (a measured claim resists retraction more than an unmeasured one in the same tier).
   - neither has strength: `EQUAL`.

This is a genuine **partial preorder** (INCOMPARABLE is a first-class outcome), consistent with the no-hidden-scalar discipline. `severity` is primary because the spec keys entrenchment on "evidence_class + severity"; `evidence_against_null` is the closest v1.3 analogue of evidence strength.

## 4. Contraction — kernel/incision, entrenchment-guided, ambiguity-surfacing

To **contract** the corpus so it no longer holds a target claim's content, we use **kernel contraction** (Hansson) — the base-AGM dual of partial-meet, and a near-twin of the Phase-5 blame-set machinery:

- A **kernel** for the contraction is a *minimal subset of claims that produces the offending state*. For the two operations we actually need:
  - **Contracting a claim `t` by identity:** the kernel is `{t}` itself plus any claim whose conclusion `entails t.conclusion` (single-premise ⇒ each is an independent singleton kernel). To stop holding `t`'s content, **all** such entailers are incised (deterministic; entrenchment doesn't reduce it — there is nothing to choose).
  - **Restoring consistency (the case where entrenchment bites):** each **conflict** = a binary inconsistent pair `{a, b}` (an `incompatible_with` edge resolving within the set) is a kernel. The **incision** removes the **least entrenched** member of each conflict.
- **Incision under partial entrenchment** (`incise_conflict(a, b)`):
  - `compare_entrenchment(a,b)` = `GREATER` ⇒ retract `b`; `LESS` ⇒ retract `a`; `EQUAL` or `INCOMPARABLE` ⇒ **either is admissible** ⇒ both enter the *underdetermined* set.
- **`restore_consistency(claims, edges) -> RetractionVerdict`** aggregates over all conflicts, returning (mirroring `blame.BlameVerdict`):
  - `robustly_retracted`: claims retracted under **every** admissible incision (the clearly-least-entrenched culprits),
  - `possibly_retracted`: the union,
  - `underdetermined`: `possibly − robustly` (incomparable/equal culprits — the choice the grammar refuses to fake),
  - `consistent_core`: `{claim ids} − possibly_retracted` (guaranteed-kept under any admissible choice).

> This deliberately parallels `blame.aggregate_blame`: a conflict is to retraction what a Duhem blame-assignment is to blame. Same partial-order honesty, same robust/underdetermined surfacing.

## 5. The three AGM operations

Each is a pure function over a corpus view `(claims: tuple[Claim, ...], edges: tuple[DefeatEdge, ...])`, returning a **`RevisionResult`**:

```
RevisionResult(_Model):
    claims: tuple[Claim, ...]              # the new base (after retractions / additions)
    edges: tuple[DefeatEdge, ...]          # carried-through / updated authored defeat edges
    retraction: RetractionVerdict | None   # present for revise/contract; None for clean expand
    in_set: frozenset[str]                 # grounded_extension(new base) — the monotone recompute
    flipped_in: frozenset[str]             # newly IN vs the prior in_set
    flipped_out: frozenset[str]            # newly OUT vs the prior in_set
```

- **`expand(claims, edges, new_claim, *, prior_in=None) -> RevisionResult`** — add `new_claim` (and re-derive rebut edges via Phase-5 `derived_rebut_edges` merged with authored `edges`), recompute `grounded_extension`. `retraction=None`. *Expansion does not itself restore consistency (AGM expansion may yield an inconsistent set); use `revise` to add while preserving consistency, or `restore_consistency` to consolidate after.*
- **`contract(claims, edges, target_id, *, prior_in=None) -> RevisionResult`** — incise `target` and every claim whose conclusion `entails` `target`'s conclusion, recompute. Deterministic in the single-premise setting (every entailer must go to stop holding the content) ⇒ `retraction` lists them all in `robustly_retracted`, `underdetermined` empty.
- **`revise(claims, edges, new_claim, *, prior_in=None) -> RevisionResult`** — the **Levi identity** `K * p = (K − ¬p) + p`, with `p = new_claim` **privileged** (AGM *success*): (1) identify every claim in `K` incompatible with `new_claim`; (2) retract **all** of them (each independently conflicts with `p`, so all must go — deterministic, all `robustly_retracted`, `new_claim` is never a retraction target); (3) expand by `new_claim`; (4) recompute `grounded_extension`, report flips. *Because `p` wins by construction, `revise`'s retraction is deterministic — entrenchment is **not** consulted here.*
- **`restore_consistency(claims, edges, *, prior_in=None) -> RevisionResult`** — Hansson **consolidation**: take a possibly-inconsistent base with **no privileged claim** and make it consistent by entrenchment-guided incision of each conflict (§4). **This is the locus of the partial-entrenchment ambiguity:** when a conflict's two members are entrenchment-`EQUAL`/`INCOMPARABLE`, both land in `underdetermined`; clear least-entrenched culprits land in `robustly_retracted`. The returned `RevisionResult.claims` is the guaranteed `consistent_core`; `retraction` carries the full `RetractionVerdict` spread.

`prior_in` (the previous grounded extension) lets the caller get accurate `flipped_in/out`; when omitted, it's computed from the input base so flips are relative to the pre-edit state.

## 6. AGM postulate conformance (verified in tests)

For the **total-entrenchment** case (no INCOMPARABLE among the relevant claims), the operations satisfy the core AGM postulates, asserted as tests:
- **Success:** `revise(K, p)` holds `p`; `contract(K, t)` does not entail `t`.
- **Inclusion:** `revise(K,p).claims ⊆ K ∪ {p}`; `contract` removes only.
- **Vacuity:** if `p` is consistent with `K`, `revise(K,p)` = `expand(K,p)` (no retraction).
- **Consistency:** `revise(K,p).claims` is `is_consistent` (given `p` itself consistent).
- **Extensionality:** claims with equal-`content_hash` conclusions are treated identically.
- **Recovery (documented caveat):** base contraction does **not** satisfy recovery in general (Hansson) — we state this explicitly and do **not** fake re-derivation. A test documents the known non-recovery rather than asserting a false postulate.

Under partial entrenchment, success/inclusion/consistency still hold; the *choice* of retraction is what becomes a spread (the `underdetermined` set), which is the intended behavior, not a violation.

## 7. Module boundaries

- `revision.py` — `Entrench` enum + `compare_entrenchment`; `entails_closure` / `corpus_entails` / `is_consistent`; `RetractionVerdict` + `restore_consistency` (the entrenchment-guided consolidation engine); `RevisionResult` + the three AGM ops `expand` / `contract` / `revise`. Pure functions + frozen models; reuses `defeat.grounded_extension`, `defeat.derived_rebut_edges`, and the `proposition` neighborhood. Mutates nothing.
- No changes to `Claim`. `status.py` already has every reason-code needed (no new PENDING reason — retraction is removal, not a status).
- If `revision.py` grows past ~200 lines, the entrenchment comparator may split into `entrenchment.py`; decide during implementation, not preemptively.

## 8. Testing (TDD)

- `compare_entrenchment`: status-tier ordering; same-tier strength dominance; INCOMPARABLE on cross-axis trade-off; strength-present beats strength-absent; EQUAL.
- `entails_closure` / `corpus_entails`: transitive reach; no spurious reach; conclusion-None claims inert.
- `is_consistent`: clean set True; an `incompatible_with` pair within the set False.
- `restore_consistency`: clear least-entrenched culprit → `robustly_retracted`; incomparable culprits → `underdetermined`; multi-conflict aggregation; consistent input → empty verdict.
- `expand` / `contract` / `revise`: success/inclusion/vacuity/consistency postulates; Levi-identity revise drops the least-entrenched conflictor; documented non-recovery; `flipped_in/out` correct against `prior_in`.
- Isolation guard green; all new models frozen + hashable.

## 9. Follow-ups (deferred)

- n-ary `incompatible_with` + conjunctive (multi-premise) `entails` → genuine multi-element kernels (then incision/entrenchment choice bites in contraction too, not only revision).
- `representation_revision` meta-tier (Phase 7).
- Named-audience entrenchment orderings beyond the single StrengthVector-derived order.
- Auxiliary assumptions as first-class retraction targets (the Phase-5 ingestion finding: all 47 v1.2 claims carry `external_assumptions`).
