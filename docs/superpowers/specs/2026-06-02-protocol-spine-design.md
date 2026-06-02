# Protocol Runtime — Sub-project #1: Corpus + the Assessment Spine

> Design spec. Status: **approved** (brainstorm 2026-06-02). First sub-project of the
> protocol runtime (the 8-stage flywheel + 3 daemons from the unified spec §4 and the
> keystone `_FINAL_knowledge_generation_protocol.md`). Builds the **deterministic backbone**:
> a `Corpus` container + the assessment stages wired as total `corpus → corpus` transforms,
> over the grammar machinery that already exists. The smart ports (GENERATE, SELECT) and the
> daemons are later sub-projects.

## 0. Context — where this sits

The v1.3 grammar (`polymer_grammar`) is structurally complete (8 layer-phases). The protocol
runtime is the *runtime* half of the compiler/runtime split — the generative flywheel that
reads/writes the grammar IR. It is too large for one spec, so it is decomposed into ~5
sub-projects:

1. **Corpus + assessment spine** ← *this spec* (no new external deps; fully deterministic)
2. Oracle dossier (unified spec §5 #2; binds to `OperationNode.oracle_ref`)
3. SELECT — the pursuit/value engine (posterior, EIG, Pareto, cost, quality-diversity)
4. GENERATE — the proposer bus (5 operators + representation-revision lane)
5. The 3 daemons (DRIFT, ORACLE-VALIDATION, REPRESENTATION RED-TEAM) + loop-economics

This sub-project is the foundation every other piece writes through. It makes the protocol
**run end-to-end on a corpus** with dumb generation/value ports, so #3 and #4 can make those
ports smart later without changing the spine.

## 1. Success criterion

Given a `Corpus` of grammar `Claim`s (some CONJECTURED/PENDING, carrying `evaluation_plan`s
injected exogenously — GENERATE is a later sub-project), a single `run_cycle(corpus, adapters,
ctx)` executes the deterministic assessment stages and returns a **new** `Corpus` plus the
cycle's ephemeral outputs (the unresolved-attack frontier, the human-gated lane, an audit).
Status transitions, licensing, and the online-FDR ledger advance correctly and
**deterministically** (same inputs → same outputs). The runtime **writes only grammar IR** and
imports `polymer_grammar` one-way (isolation-tested).

- **Sensitivity:** the spine expresses every *deterministic* stage of the keystone cycle
  (REPRESENT, CANONICALIZE, SAFETY-GATE, DESIGN/COMMIT, EXECUTE/GROUND, VERIFY, INTEGRATE).
- **Specificity:** no smart-port logic leaks in (no value scalar, no embeddings, no LLM); the
  air-gap from Phase 8 is preserved (EXECUTE runs `verify()`, never self-licenses).

## 2. Design principles

- **Compiler/runtime split.** `polymer_grammar` is the declarative IR; `polymer_protocol` is
  the runtime. **One-way dependency** (protocol → grammar), enforced by an isolation test
  mirroring the grammar's own `test_isolation.py`.
- **Writes only grammar IR (load-bearing).** Stages produce new frozen `Claim`s (status flips,
  `Licensing` attached, `provenance.preregistration_hash` set) + updated
  `defeat_edges`/`equivalences`/`fdr_ledger`. **No new grammar fields; no protocol-private
  per-claim wrapper.** Per-claim stage outputs map onto existing IR (see §1 of the brainstorm,
  reproduced in §4 below). Ephemeral per-cycle products (VAF extension, frontier, execution
  diagnostics) are returned in the `CycleResult`, never stored in the `Corpus` — keeping the
  cycle reversible.
- **Total, pure, frozen.** Every stage is a deterministic total function returning a new value.
  Protocol models subclass a frozen base (`extra="forbid"`, tuples-only), mirroring the grammar.
- **Single pip install (end-state).** The eventual `pip install polymer-claims` bundles
  `polymer_grammar` + `polymer_protocol` + a harness/CLI into one distribution. That packaging
  step belongs to the later harness/CLI sub-project; this spec only fixes the import boundary
  (a separate `polymer_protocol` import package) so it stays compatible.
- TDD; `cd protocol && uv run pytest -q` + `uv run ruff check src tests`.

## 3. Package & layout

```
polymer-claims/
  grammar/                      # existing — polymer_grammar (unchanged)
  protocol/                     # NEW
    pyproject.toml              # package polymer_protocol; path-dep on polymer_grammar
    src/polymer_protocol/
      __init__.py
      base.py                   # frozen _Model (mirrors grammar.base; or re-exports it)
      corpus.py                 # Corpus + CycleScaffolding + CycleResult
      represent.py              # represent()
      canonicalize.py           # canonicalize()
      safety.py                 # safety_gate()
      commit.py                 # commit()
      execute.py                # execute_ground()
      verify.py                 # verify_stage()
      integrate.py              # integrate()
      cycle.py                  # run_cycle() — chains the stages
    tests/
      test_isolation.py         # grammar must NOT import polymer_protocol
      test_corpus.py
      test_<each stage>.py
      test_cycle.py             # full-cycle integration + determinism
```

`base.py`: prefer re-using the grammar's frozen-model discipline. Either import
`polymer_grammar.base._Model` or define a local `_Model` with the identical `ConfigDict`
(`extra="forbid", frozen=True, populate_by_name=True`). Decide in the plan; re-export is fine.

## 4. The `Corpus` (persistent state)

```python
class Corpus(_Model):
    claims: tuple[Claim, ...] = ()
    defeat_edges: tuple[DefeatEdge, ...] = ()
    equivalences: tuple[EquivalenceClaim, ...] = ()
    fdr_ledger: FDRLedger                      # the corpus error budget
```

- Indexed by `Claim.id` (a derived `by_id` mapping helper; not a stored field).
- All four are existing grammar types — `Corpus` is a pure bundle of grammar IR.
- Validators: `Claim.id`s unique; `defeat_edges`/`equivalences` endpoints resolve to claim ids
  (referential integrity at the corpus level — something the grammar couldn't enforce without
  corpus context, noted as an L1/L3 follow-up).

**Why these four and nothing else** — the per-claim stage outputs map onto existing IR, so no
wrapper is needed:

| keystone stage output | home in v1.3 grammar IR |
|---|---|
| equivalence_class_id | derived from `equivalences` via `equivalence_class()` |
| requires_human_gate | derived predicate `governance.requires_safety_review(claim)` |
| commit_hash / hash-lock | `provenance.preregistration_hash` |
| statistics + Satisfaction | Phase-8 `verify()` mints `Satisfaction`; diagnostics → `CycleResult.audit` |
| status + license_route + rival_set_closure | `Claim.status` + `Licensing` |
| online-FDR ledger update | `Corpus.fdr_ledger` via `fdr.process_test` |

## 5. Ephemeral cycle values

```python
class CycleScaffolding(_Model):
    grounded_extension: tuple[str, ...]        # claim ids IN the grounded extension (defeat.grounded_extension)
    frontier: tuple[str, ...]                  # unresolved-attack frontier (claim ids with unresolved incident attacks)

class ExecRecord(_Model):
    claim_id: str
    evaluation: VerifiedEvaluation             # Phase-8 result: minted Satisfaction | None + agreement + disagreement

class CycleResult(_Model):
    corpus: Corpus                             # the new corpus
    frontier: tuple[str, ...]                  # = next cycle's GENERATE/SELECT target (keystone closure)
    gated_lane: tuple[str, ...]                # claim ids barred from autonomous execution (SAFETY)
    audit: tuple[StageAudit, ...]              # per-stage record (counts, status flips, execution diagnostics)
```

`ExecRecord` is the bridge from EXECUTE to VERIFY/INTEGRATE: it pairs a claim id with its
Phase-8 `VerifiedEvaluation` (the minted `Satisfaction` or the disagreement detail, plus the
terminal value used as the FDR p-value). `ExecRecord`s are ephemeral cycle values, not stored in
`Corpus`.

`StageAudit` is a small frozen record (`stage: str`, `note: str`, plus counts) — the cycle's
human-readable trace. Execution diagnostics (Phase-8 `EvaluationResult`/`Drift`/disagreement)
are summarized here, not persisted in `Corpus`.

## 6. The stages (each pure; signatures fixed)

### 6.1 `represent(corpus) -> CycleScaffolding`
Build the ephemeral scaffolding; **write nothing**. Compute the VAF grounded extension via
`defeat.grounded_extension(claims, defeat_edges)`; compute the unresolved-attack frontier (claim
ids that are targets of an effective defeat and are *not* in the grounded extension, plus
LICENSED claims with a newly-incident attack). *Spine boundary: the two-axis calibrated
posterior needs embeddings + an exogenous benchmark → deferred to SELECT (#3). REPRESENT here
yields argumentation scaffolding + frontier only.*

### 6.2 `canonicalize(corpus) -> Corpus`
Compute a **structural canonical key** per claim from existing content hashes
(`subject` + `Proposition.content_hash` + `evaluation_plan.graph.content_hash` + `pattern`).
Collapse structurally-identical claims into one canonical node, recording the collapse as
`EquivalenceClaim` edges (added to `equivalences`) and merging provenance. *Spine boundary: the
semantic/embedding-based equivalence + EIG dedup-correlation is deferred to #3; this stage does
structural-key + asserted-equivalence collapse only.*

### 6.3 `safety_gate(corpus) -> tuple[Corpus, tuple[str, ...]]`
Partition claims using the grammar's governance predicates
(`governance.requires_safety_review`, `HazardClass`). Hazard-flagged claims are **barred from
autonomous execution regardless of value** and returned as the `gated_lane` (the human-review
lane). Writes nothing to claims (uses existing `governance`); returns the surviving corpus + the
gated id list. An auditable record is added to `CycleResult.audit`.

### 6.4 `commit(corpus) -> Corpus`
For claims ready to test (PENDING, carrying an `evaluation_plan`, not already locked),
**hash-lock** the test — compute a stable hash over
`<evaluation_plan.graph.content_hash, evaluation_plan.criterion>` and write it to
`provenance.preregistration_hash` (creating a minimal `Provenance` if absent). Post-hoc
divergence on the locked plan is what VERIFY checks (anti-HARKing, C9); the lock is idempotent
(re-committing an already-locked, unchanged plan is a no-op). *Spine boundary: there is no OOD
field in v1.3 grammar yet, so the lock covers the executable plan only; the OOD-set / OOD-
environment machinery is a later sub-project.*

### 6.5 `execute_ground(corpus, adapters, ctx) -> tuple[Corpus, tuple[ExecRecord, ...]]`
For each committed PENDING claim with an `evaluation_plan`, run the **Phase-8 air-gapped gate**
`verify(plan, ctx, adapters, claim_leaves=claim.leaves)`. Collect the `VerifiedEvaluation`
(minted `Satisfaction` on agreement+SATISFIED, else `None` + disagreement detail). Attach the
result to an `ExecRecord` (claim id + the `VerifiedEvaluation`); partial/failed/UNDETERMINED →
the claim stays PENDING. **Writes no status yet** — EXECUTE produces evidence; VERIFY decides
status. `ExecRecord`s flow to VERIFY and are summarized in the audit. *Spine boundary: model-
adequacy diagnostics beyond Phase-8 drift, blind canaries, and the serendipity EXPLORATORY pool
are deferred.*

### 6.6 `verify_stage(corpus, scaffolding, exec_records) -> Corpus`
Decide each executed claim's `status`:
- **LICENSED** requires *all* of: a minted `Satisfaction` (agreement + SATISFIED from EXECUTE)
  **and** grounded-extension membership (`scaffolding.grounded_extension`) **and** the
  **selection-aware honesty gate** — `provenance.search_cardinality` must be recorded (the
  implicit search was priced). On LICENSED, assemble the `Licensing` record
  (route ∈ {severe_test, replication}, `rival_set_closure`) from the claim's existing licensing
  inputs and the execution. *Spine boundary: the actual cardinality-**scaled** significance
  threshold (a stricter OOD/invariance bar as search_cardinality grows) needs the p-value /
  EIG machinery and is deferred to SELECT (#3); the spine enforces only that the cardinality is
  present, not yet a scaled bar.*
- **REJECTED** if the Satisfaction is refuted or the claim is outside the grounded extension.
- **PENDING** otherwise (undetermined / partial / two-impl disagreement → PENDING triage).

Produces new frozen `Claim`s with updated `status` (+ `Licensing` when LICENSED). *This is
exactly the Licensing-assembly + status-flip Phase 8 deliberately left to the protocol.*

### 6.7 `integrate(corpus, scaffolding, exec_records) -> Corpus`
Admit graded claims and run the corpus revision machinery:
- recompute authored defeat edges incident to newly-LICENSED/REJECTED claims
  (`defeat.derived_rebut_edges`, `defeat.undermine_edges_from_failed_satisfactions`);
- run the **entrenchment contest** on any introduced inconsistency
  (`revision.restore_consistency` / `revise`) — newcomer yields per the grammar's AGM rules;
- surface **Duhem blame** on contradictions (`blame.aggregate_blame` → `duhem_status`);
- advance the **online-FDR ledger** via `fdr.process_test` on `corpus.fdr_ledger`, one test per
  newly-executed claim. The p-value is the executed **terminal value** carried in that claim's
  `ExecRecord` (the value the criterion tested, e.g. a `< 0.05` significance plan); claims whose
  terminal value is non-numeric are skipped and logged in the audit. *(The grammar computes the
  LOND allocation; the protocol supplies the p-value — the division Phase-8/FDR established.)*
*Spine boundary: library-learning/compression fold, full units commensuration, and the
empirical-null-per-pattern calibration are deferred to later sub-projects.*

### 6.8 `run_cycle(corpus, adapters, ctx) -> CycleResult`
Chain the stages, threading the ephemeral values:
```
scaffolding      = represent(corpus)
corpus           = canonicalize(corpus)
corpus, gated    = safety_gate(corpus)
corpus           = commit(corpus)
corpus, records  = execute_ground(corpus, adapters, ctx)   # only non-gated claims
corpus           = verify_stage(corpus, scaffolding, records)
corpus           = integrate(corpus, scaffolding, records)
frontier         = represent(corpus).frontier              # recompute on the post-INTEGRATE corpus
```
Return `CycleResult{corpus, frontier, gated_lane=gated, audit}`. **Keystone closure:** the
emitted `frontier` (unresolved-attack nodes *after* INTEGRATE) is identically the next cycle's
GENERATE/SELECT target list — the spine exposes it as the cycle's primary output so the open
ports (#3, #4) can consume it later. (REPRESENT is called twice: once at the head for the
scaffolding VERIFY/INTEGRATE consume, once at the tail to compute the post-cycle frontier — it
writes nothing, so this is free and keeps the cycle reversible.) GENERATE and SELECT are **not**
in this sub-project: claims enter exogenously, and the dumb driver executes every committed,
non-gated PENDING claim.

## 7. Scope fence — explicitly OUT (later sub-projects / deferred)

- **GENERATE** (#4) and **SELECT / value / EIG / Pareto / cost / quality-diversity** (#3) — the
  open ports; stubbed as exogenous claim injection + execute-all-committed.
- **The two-axis calibrated posterior + calibration + embeddings + external KG** — REPRESENT
  yields argumentation scaffolding + frontier only.
- **Oracle dossier + strength-capping** (#2; the `oracle_ref` slot already exists).
- **Real oracle adapters** (PolymerGenomicsAPI / R / scipy) — reference adapters only; real
  adapters live outside `polymer_protocol`.
- **The 3 daemons** (DRIFT, ORACLE-VALIDATION, REPRESENTATION RED-TEAM) + loop-economics /
  termination / anomaly-importation (#5).
- **Library-learning / compression fold, full commensuration, blind canaries, serendipity
  EXPLORATORY pool, empirical-null-per-pattern, PPV health metric.**
- **Single-distribution packaging + CLI** — the later harness sub-project.

## 8. Testing

`cd protocol && uv run pytest -q` + `uv run ruff check src tests`. TDD throughout.

- **`test_isolation.py`** — `polymer_grammar` imports nothing from `polymer_protocol` (one-way).
- **`test_corpus.py`** — Corpus validators (unique ids, edge/equivalence endpoints resolve),
  frozen/tuple discipline, `by_id` helper.
- **per-stage tests** — each stage as a pure function on a small hand-built corpus:
  represent (extension + frontier correct on a tiny defeat graph); canonicalize (two structurally
  identical claims collapse to one equivalence class); safety_gate (a hazard-flagged claim lands
  in the gated lane, a clean one survives); commit (hash-lock written to provenance; idempotent);
  execute_ground (a committed claim with a plan runs `verify` and yields a Satisfaction via two
  reference adapters; a same-identity pair would raise — but the spine supplies distinct
  adapters); verify_stage (LICENSED only when Satisfaction + extension-membership + cardinality
  bar all hold; refuted → REJECTED; disagreement → PENDING); integrate (status persists, defeat
  edges recomputed, FDR ledger advances by one test).
- **`test_cycle.py`** — a full `run_cycle` on a tiny corpus (2–3 claims with evaluation_plans):
  assert the expected status flips, the frontier is emitted, the gated lane is correct, and the
  FDR ledger advanced. **Determinism:** the same `(corpus, adapters, ctx)` yields an identical
  `CycleResult`.

## 9. Connections

- Consumes Phase-8 `evaluate`/`verify` (EXECUTE), L3 `defeat`/`blame` (REPRESENT/INTEGRATE), L4
  `revision` (INTEGRATE), `equivalence` (CANONICALIZE), `governance` (SAFETY), `provenance`
  (COMMIT), `fdr` (INTEGRATE) — the whole grammar surface finally driven as one loop.
- Emits the unresolved-attack frontier that SELECT (#3) and GENERATE (#4) will consume — the
  flywheel's closure, stubbed-but-shaped here.
- The first step toward the `pip install polymer-claims` local node + the federated claims
  universe ([[project_polymer_claims_platform_vision]]).
