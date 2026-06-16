# Provisional links — activate-on-license defeat edges (protocol sub-project #4b, slice 1)

> **Status:** design spec, approved 2026-06-04. Scope = the **provisional-defeat-edge mechanism**:
> a defeat edge that is inert until its source claim is LICENSED, then effective. Closes the #4a
> limitation that GENERATE's pure operators could only emit *isolated* CONJECTURED nodes.
> **First slice that touches BOTH packages** (grammar + protocol) — a coordinated, separately
> reviewed change, not the usual protocol-only slice. Builds on #4a GENERATE (merge `5d7899f`).

## 1. Purpose

In #4a, GENERATE's pure operators (`frontier_attack`, `rival_generation`) can only emit **isolated**
CONJECTURED claims, because this spine has two **status-blind** consumers of incompatibility — a
defeat edge is consumed by `effective_defeats` (a strengthless source's attack is not filtered →
defeats immediately) and an `incompatible_with` neighbor is consumed by `restore_consistency._conflicts`
(retracts immediately). So a conjecture cannot encode "I challenge B" without changing beliefs *now*.
This cannot be fixed by globally making conjectured attacks inert: the **existing frontier semantics
(established and tested in #1) depend on conjectured claims attacking and creating frontiers.**

A **provisional defeat edge** is a *distinct, opt-in* edge that is **inert while its source is not
LICENSED, and effective once the source licenses.** It lets GENERATE plant a real-but-inert-until-
validated relationship — "if this defense/rival is ever validated, it defeats its target" — without
disturbing beliefs while it is still a conjecture, and without touching the `_conflicts` path at all
(we use defeat edges, never `incompatible_with`).

## 2. Architecture: a grammar flag (chosen over a protocol registry)

The mechanism is an **additive, back-compat grammar change** honored by the defeat-graph functions —
intrinsic and automatic (no registry, no materialization stage, no hand-managed lifecycle). The
alternative (a threaded protocol registry + an `activate_links` stage) was considered and rejected as
more machinery for the same effect.

## 3. The grammar change (`grammar/`)

### 3.1 `DefeatEdge.provisional`

Add one additive field to `DefeatEdge` (`grammar/src/polymer_grammar/defeat.py`):

```python
class DefeatEdge(_Model):
    source: str
    target: str
    kind: DefeatEdgeKind
    note: str | None = None
    provisional: bool = False   # NEW: inert until `source` is LICENSED (see effective_defeats)
```

Default `False` ⇒ existing edges and all existing tests are unchanged. The `_no_self_loop` validator
is untouched.

### 3.2 `effective_defeats` + `grounded_extension` gain `licensed_ids`

```python
def effective_defeats(edges, strength, licensed_ids=frozenset()) -> frozenset[tuple[str, str]]:
    out = set()
    for e in edges:
        if e.kind not in ATTACK_KINDS:
            continue
        if e.provisional and e.source not in licensed_ids:   # NEW: inert until source licensed
            continue
        s_src = strength.get(e.source)
        s_tgt = strength.get(e.target)
        if s_src is not None and s_tgt is not None and s_tgt.dominates(s_src):
            continue
        out.add((e.source, e.target))
    return frozenset(out)


def grounded_extension(claim_ids, edges, strength, licensed_ids=frozenset()) -> frozenset[str]:
    # ... unchanged except: pass licensed_ids through to the internal effective_defeats(...) call
```

`licensed_ids: frozenset[str]` defaults to empty. **A caller that supplies nothing treats every
provisional edge as inert** (the safe default); non-provisional edges are completely unaffected. So
the change is **fully back-compat** — existing callers pass `licensed_ids` nowhere, every edge in
existing corpora has `provisional=False`, and behavior is byte-identical.

### 3.3 `restore_consistency` passes its own `licensed_ids`

`grammar/src/polymer_grammar/revision.py` (line ~164) recomputes `grounded_extension(...)` inside the
AGM consolidation. It has the claim set, so it computes and passes
`licensed_ids = frozenset(c.id for c in claims if c.status == Status.LICENSED)` — keeping the AGM
recompute consistent with `represent` (a provisional edge from a now-LICENSED source is active in
both). (`Status` is already imported in `revision.py`.)

### 3.4 Activation semantics

A provisional edge `D ⊣ B` is **inert** (skipped by `effective_defeats`) while `D ∉ licensed_ids`.
The moment `D` is LICENSED, the edge is honored and `D` defeats `B` under the normal strength-mediated
rule (now `D` has real strength as a licensed claim). If `D` is later **retracted** (no longer
LICENSED — e.g. an AGM contest removes it), the edge goes inert again *automatically* — there is no
stale materialized edge to clean up. Activation timing: a claim that licenses in VERIFY (cycle N) is
in `licensed_ids` for that cycle's INTEGRATE recompute and every subsequent `represent`, so activation
is effectively immediate and persistent.

## 4. The protocol wiring (`protocol/`)

### 4.1 `represent` supplies `licensed_ids`

`protocol/src/polymer_protocol/represent.py` computes
`licensed_ids = frozenset(c.id for c in corpus.claims if c.status == Status.LICENSED)` and passes it
to **both** `grounded_extension(...)` and `effective_defeats(...)` (both are called there). (`Status`
is added to the grammar import.) This is the one place the cycle's scaffolding/frontier honor
activation.

### 4.2 The two operators emit provisional rebut edges (`proposers.py`)

Both operators switch from #4a's *isolated node* to a node **plus a provisional rebut edge** — keeping
them belief-neutral while a conjecture, but now carrying a link that activates on validation:

- **`frontier_attack`** — for each frontier node `F` and its claim-sourced attacker `B`, emit the
  defense seed `D` **and** `DefeatEdge(source=D.id, target=B, kind=REBUT, provisional=True)`. (Replaces
  #4a's no-edge seed.)
- **`rival_generation`** — for each other-direction rival `R` of a concluded claim `C`, emit `R` (still
  with its flipped-direction conclusion, **empty neighborhood** — no `incompatible_with`) **and**
  `DefeatEdge(source=R.id, target=C.id, kind=REBUT, provisional=True)`. (Replaces #4a's isolated rival.)
  Using a provisional *rebut edge* instead of an `incompatible_with` neighbor is what keeps `_conflicts`
  out of the picture entirely — no premature retraction.

`generate_stage` already folds `proposal.edges` into `corpus.defeat_edges`, and `compile_to_IR` already
validates edge source (= the new claim id) and target (an existing claim) — so the provisional edges
flow through the existing bus unchanged. (The #4a convergence guard / content-addressed ids are
unaffected.)

### 4.3 Belief-neutrality preserved (provable two ways)

A provisional edge whose source is a fresh CONJECTURED claim (`∉ licensed_ids`) is skipped by
`effective_defeats`, so planting it changes **no** grounded membership this cycle — GENERATE stays a
pure proposer. And because the operators use **rebut edges, not `incompatible_with`**, `_conflicts`
(restore_consistency) never sees them → no retraction. The #4a belief-neutrality tests still hold; #4b
adds a test that planting a provisional edge leaves `grounded_extension` of the pre-existing claims
unchanged.

## 5. Honest scope limitation

The pure operators emit **no-plan CONJECTURED** claims, which cannot license on their own (not SELECT
candidates, never executed). So in practice **their specific provisional edges sit dormant until the
seed/rival gains an `evaluation_plan` and licenses** — via the exogenous port or a future
executable-generation operator. #4b delivers the **mechanism** and wires the operators to it; the
activation of the operators' *own* outputs waits on executable generation (deferred, needs the
embedding/LLM operators or richer exogenous augmentation). The mechanism itself is validated end-to-end
with a **planned** claim carrying a provisional edge (§7).

## 6. Files

| File | Pkg | Change |
|---|---|---|
| `grammar/src/polymer_grammar/defeat.py` | grammar | `DefeatEdge.provisional` field; `effective_defeats`/`grounded_extension` gain `licensed_ids` + the inert-skip |
| `grammar/src/polymer_grammar/revision.py` | grammar | `restore_consistency` passes `licensed_ids` to its `grounded_extension` recompute |
| `protocol/src/polymer_protocol/represent.py` | protocol | compute + pass `licensed_ids` to both grammar calls |
| `protocol/src/polymer_protocol/proposers.py` | protocol | both operators emit a provisional rebut edge |
| tests in both packages | both | grammar: flag + activation + back-compat; protocol: operators + belief-neutrality + end-to-end activation |

No new modules. No change to `Corpus` (still 4 collections — provisional edges live in the existing
`defeat_edges`).

## 7. Testing

**Grammar (`defeat.py`):**
- `provisional=False` default ⇒ existing `effective_defeats`/`grounded_extension` results byte-identical
  (back-compat).
- a `provisional=True` edge with `source ∉ licensed_ids` is **inert** (not in `effective_defeats`, does
  not change `grounded_extension`); with `source ∈ licensed_ids` it is **effective** (defeats the
  target under the normal strength rule).
- retraction: removing the source from `licensed_ids` makes the edge inert again.
- a non-provisional edge from a conjectured source is **still effective** (the #1 frontier semantics are
  preserved — this is the load-bearing guard against over-reach).

**Grammar (`revision.py`):** `restore_consistency` activates a provisional edge whose source is LICENSED
in the claim set (consistent with `represent`).

**Protocol (`proposers.py`):** `frontier_attack`/`rival_generation` each emit the expected provisional
rebut edge (`provisional=True`, source=new claim, target=B/C, kind=REBUT); the rival still has an empty
neighborhood (no `incompatible_with`).

**Protocol (end-to-end, `cycle.py`):**
- **belief-neutral:** running an operator through `run_cycle` leaves the pre-existing claims' grounded
  membership unchanged (the provisional edge is inert while its source is CONJECTURED) — and the corpus
  is not emptied (no `_conflicts` retraction).
- **activation:** a corpus with a *planned* claim `D` carrying a `provisional` `D ⊣ B` edge — run the
  cycle(s) until `D` licenses, then assert the edge is now effective (`B` drops out of the grounded
  extension / `D⊣B` appears in `effective_defeats`). This pins the mechanism the operators rely on.

**Isolation:** grammar still imports nothing from protocol; protocol→grammar one-way; neither imports
`v1.2/formalclaim`. (The grammar change is internal to grammar; the protocol change consumes it.)

## 8. Scope boundary

**#4b slice 1 (this spec):** the provisional-defeat-edge flag + activation-on-license + both operators
wired + the mechanism test.

**Deferred:** provisional *incompatibility-on-conclusion* (a `_conflicts`/mutual-rebut analogue — not
needed here since rivals use rebut edges); **executable-generation** that would let the operators' own
no-plan seeds gain plans and license (needs the embedding/LLM operators or richer exogenous
augmentation — the rest of #4b); deactivation hooks beyond the automatic "source no longer LICENSED ⇒
inert" (nothing more is needed).
