# CES-3 — Content-Address Completeness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Record each licensed claim's full content-address (`dimnames_hash` + `profile_hash` + `semantic_run_id`) on its `Satisfaction.materialization`, and make DRIFT re-open a claim when its data or apparatus content-address moves.

**Architecture:** A pre-stamped per-claim materialization map (umbrella, impure) is passed into `run_cycle`; the pure protocol core does a `dict.get(c.id, ctx)` lookup so the minted Satisfaction carries the per-claim ctx. The drift freshness predicate additionally compares `profile_hash`/`dimnames_hash` when present (back-compat). Grammar untouched; Corpus stays 4.

**Tech Stack:** Python 3.12, Pydantic v2, pytest, uv, ruff. No numpy.

**Spec:** `docs/specs/2026-06-12-ces-3-content-address-completeness-design.md`
**Branch:** `feat/ces-3-content-address-completeness` (already created off `main`).
**Protocol tests:** `cd protocol && uv run pytest -q`. **Umbrella tests:** `uv run --project . pytest tests/ -q` (from repo root).

---

## File Structure

| File | Responsibility | Change |
|---|---|---|
| `protocol/src/polymer_protocol/execute.py` | `execute_ground` | Modify: add `materializations=` param; per-claim ctx lookup |
| `protocol/src/polymer_protocol/cycle.py:40-58,115` | `run_cycle` | Modify: add `materializations=` keyword; thread to `execute_ground` |
| `protocol/src/polymer_protocol/drift.py:33-40` | `_is_fresh` | Modify: tighten predicate (profile_hash/dimnames_hash when present) |
| `protocol/tests/test_execute_materializations.py` | the seam | Create |
| `protocol/tests/test_drift.py` | the tightened predicate | Modify (append) |
| `src/polymer_claims/materialization.py` | the umbrella per-claim content-address map | Create |
| `tests/test_materialization_map.py` | map unit tests | Create |
| `tests/test_ces3_content_address_e2e.py` | end-to-end record + drift | Create |

`grammar/` is untouched.

---

## Task 1: Protocol seam — `materializations=` on `execute_ground` + `run_cycle`

**Files:**
- Modify: `protocol/src/polymer_protocol/execute.py` (the `execute_ground` signature + loop)
- Modify: `protocol/src/polymer_protocol/cycle.py` (`run_cycle` signature + the `execute_ground` call at line 115)
- Test: `protocol/tests/test_execute_materializations.py`

- [ ] **Step 1: Write the failing test**

Create `protocol/tests/test_execute_materializations.py`:

```python
from polymer_grammar import MaterializationContext, Status
from polymer_protocol.corpus import Corpus
from polymer_protocol.execute import execute_ground
from tests.conftest import make_claim, make_plan


def _executable(cid):
    # value 0.01 < threshold 0.05 -> SATISFIED by the reference adapters
    return make_claim(cid, status=Status.PENDING, plan=make_plan(0.01, 0.05))


def test_per_claim_materialization_is_stamped_on_satisfaction(adapters):
    a, b = _executable("a"), _executable("b")
    corpus = Corpus(claims=(a, b))
    base = MaterializationContext(id="M", api_version="v1", data_version="d1")
    mats = {
        "a": MaterializationContext(id="M", api_version="v1", data_version="d1",
                                    dimnames_hash="sha256:aaa", profile_hash="sha256:pa"),
        "b": MaterializationContext(id="M", api_version="v1", data_version="d1",
                                    dimnames_hash="sha256:bbb", profile_hash="sha256:pb"),
    }
    _, records = execute_ground(corpus, adapters, base, materializations=mats)
    by_id = {r.claim_id: r for r in records}
    assert by_id["a"].evaluation.satisfaction.materialization.dimnames_hash == "sha256:aaa"
    assert by_id["b"].evaluation.satisfaction.materialization.dimnames_hash == "sha256:bbb"
    assert by_id["a"].evaluation.satisfaction.materialization.profile_hash == "sha256:pa"


def test_no_map_uses_base_ctx_unchanged(adapters):
    a = _executable("a")
    base = MaterializationContext(id="M", api_version="v1", data_version="d1")
    _, records = execute_ground(Corpus(claims=(a,)), adapters, base)
    m = records[0].evaluation.satisfaction.materialization
    assert m.data_version == "d1" and m.dimnames_hash is None  # byte-identical to today


def test_claim_absent_from_map_falls_back_to_base(adapters):
    a, b = _executable("a"), _executable("b")
    base = MaterializationContext(id="M", api_version="v1", data_version="d1")
    mats = {"a": MaterializationContext(id="M", api_version="v1", data_version="d1",
                                        dimnames_hash="sha256:aaa")}
    _, records = execute_ground(Corpus(claims=(a, b)), adapters, base, materializations=mats)
    by_id = {r.claim_id: r for r in records}
    assert by_id["a"].evaluation.satisfaction.materialization.dimnames_hash == "sha256:aaa"
    assert by_id["b"].evaluation.satisfaction.materialization.dimnames_hash is None  # base ctx
```

- [ ] **Step 2: Run — confirm failure**

Run: `cd protocol && uv run pytest tests/test_execute_materializations.py -q`
Expected: FAIL — `execute_ground() got an unexpected keyword argument 'materializations'`.

- [ ] **Step 3: Add the param to `execute_ground`**

In `protocol/src/polymer_protocol/execute.py`, change `execute_ground`'s signature and the verify call:

```python
def execute_ground(
    corpus: Corpus,
    adapters: tuple[Adapter, ...],
    ctx: MaterializationContext,
    only: frozenset[str] | None = None,
    materializations: dict[str, MaterializationContext] | None = None,
) -> tuple[Corpus, tuple[ExecRecord, ...]]:
    """Run verify() over executable claims, optionally gated to this cycle's selection.

    `materializations` (when supplied) provides a per-claim MaterializationContext (the content-
    addressed ctx, computed by the caller); a claim present in the map is verified against its own
    ctx, a claim absent falls back to the shared `ctx`. None -> every claim uses `ctx` (byte-
    identical to before). The core only reads the dict — no I/O here.
    """
    records = []
    for c in corpus.claims:
        if only is not None and c.id not in only:
            continue
        if not _is_executable(c):
            continue
        ctx_c = materializations.get(c.id, ctx) if materializations else ctx
        evaluation = verify(c.evaluation_plan, ctx_c, adapters, claim_leaves=c.leaves)
        records.append(ExecRecord(claim_id=c.id, evaluation=evaluation))
    return corpus, tuple(records)
```

- [ ] **Step 4: Thread it through `run_cycle`**

In `protocol/src/polymer_protocol/cycle.py`, add a keyword-only param to `run_cycle` (after `generation_credit_floor: float | None = None`, inside the existing `*,` keyword block):

```python
    materializations: dict[str, MaterializationContext] | None = None,
```

and pass it at the `execute_ground` call (line ~115):

```python
    corpus, records = execute_ground(corpus, adapters, ctx, only=selected_ids, materializations=materializations)
```

(`MaterializationContext` is already imported in `cycle.py`; if not, add it to the `polymer_grammar` import.)

- [ ] **Step 5: Run tests**

Run: `cd protocol && uv run pytest tests/test_execute_materializations.py tests/test_execute.py tests/test_cycle.py -q && uv run ruff check src tests`
Expected: PASS — new tests + every existing execute/cycle test (proving the no-map path is unchanged); ruff clean.

- [ ] **Step 6: Commit**

```bash
git add protocol/src/polymer_protocol/execute.py protocol/src/polymer_protocol/cycle.py protocol/tests/test_execute_materializations.py
git commit -m "feat(protocol): per-claim materializations= seam on execute_ground/run_cycle (CES-3)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

## Task 2: Drift predicate — tighten `_is_fresh` (content-address aware)

**Files:**
- Modify: `protocol/src/polymer_protocol/drift.py:33-40`
- Test: `protocol/tests/test_drift.py` (append)

- [ ] **Step 1: Write the failing tests** — append to `protocol/tests/test_drift.py` (reuse that file's existing helper for building a LICENSED claim with a materialization; if it has one like `_licensed(...)`, use it — otherwise mirror its existing LICENSED-claim construction). The tests in full:

```python
from polymer_grammar import (
    Licensing, LicenseRoute, MaterializationContext, RivalSetClosure, Satisfaction,
    SatisfactionVerdict, Status,
)
from polymer_protocol.drift import _is_fresh
from tests.conftest import make_claim, make_plan


def _licensed_with(mat: MaterializationContext):
    lic = Licensing(
        route=LicenseRoute.SEVERE_TEST,
        satisfactions=(Satisfaction(verdict=SatisfactionVerdict.SATISFIED, materialization=mat),),
        rival_set_closure=RivalSetClosure.OPEN_ACKNOWLEDGED,
    )
    return make_claim("c", status=Status.LICENSED, plan=make_plan(0.01, 0.05), licensing=lic)


def test_content_addressed_claim_stale_when_dimnames_hash_moves():
    mat = MaterializationContext(id="M", api_version="v1", data_version="d1",
                                 profile_hash="sha256:p", dimnames_hash="sha256:DATA1")
    c = _licensed_with(mat)
    current = MaterializationContext(id="M", api_version="v1", data_version="d1",
                                     profile_hash="sha256:p", dimnames_hash="sha256:DATA2")
    assert _is_fresh(c, current) is False  # data content-address moved


def test_content_addressed_claim_stale_when_profile_hash_moves():
    mat = MaterializationContext(id="M", api_version="v1", data_version="d1",
                                 profile_hash="sha256:P1", dimnames_hash="sha256:d")
    c = _licensed_with(mat)
    current = MaterializationContext(id="M", api_version="v1", data_version="d1",
                                     profile_hash="sha256:P2", dimnames_hash="sha256:d")
    assert _is_fresh(c, current) is False  # apparatus content-address moved


def test_content_addressed_claim_fresh_when_both_match():
    mat = MaterializationContext(id="M", api_version="v1", data_version="d1",
                                 profile_hash="sha256:p", dimnames_hash="sha256:d")
    c = _licensed_with(mat)
    current = MaterializationContext(id="M", api_version="v1", data_version="d1",
                                     profile_hash="sha256:p", dimnames_hash="sha256:d")
    assert _is_fresh(c, current) is True


def test_legacy_claim_without_hashes_judged_on_versions_only():
    # no content-address fields on the recorded materialization -> today's behavior exactly.
    mat = MaterializationContext(id="M", api_version="v1", data_version="d1")
    c = _licensed_with(mat)
    current = MaterializationContext(id="M", api_version="v1", data_version="d1",
                                     profile_hash="sha256:whatever", dimnames_hash="sha256:whatever")
    assert _is_fresh(c, current) is True  # absent hashes -> not compared
```

- [ ] **Step 2: Run — confirm failure**

Run: `cd protocol && uv run pytest tests/test_drift.py -q`
Expected: the two "stale when X moves" tests FAIL (current `_is_fresh` ignores the hashes, returns True); the "fresh"/"legacy" tests PASS already.

- [ ] **Step 3: Tighten `_is_fresh`**

In `protocol/src/polymer_protocol/drift.py`, replace `_is_fresh` (lines 33-40):

```python
def _is_fresh(claim: Claim, current: MaterializationContext) -> bool:
    """A LICENSED claim is fresh if ANY satisfaction materialization matches `current` on
    api_version AND data_version, AND — when the recorded materialization carries them — on the
    content-address fields profile_hash and dimnames_hash. A materialization without those fields
    (const-plan / pre-CES-3) is judged on versions only (back-compat). Equality match (no semver)."""
    for sat in claim.licensing.satisfactions:
        m = sat.materialization
        if m.api_version != current.api_version or m.data_version != current.data_version:
            continue
        if m.profile_hash is not None and m.profile_hash != current.profile_hash:
            continue
        if m.dimnames_hash is not None and m.dimnames_hash != current.dimnames_hash:
            continue
        return True
    return False
```

- [ ] **Step 4: Run tests**

Run: `cd protocol && uv run pytest tests/test_drift.py -q && uv run ruff check src tests`
Expected: PASS — the new tests + every existing drift test (the legacy/version-only behavior is preserved); ruff clean.

- [ ] **Step 5: Commit**

```bash
git add protocol/src/polymer_protocol/drift.py protocol/tests/test_drift.py
git commit -m "feat(protocol): drift _is_fresh compares profile_hash/dimnames_hash when present (CES-3)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

## Task 3: Umbrella materialization map

**Files:**
- Create: `src/polymer_claims/materialization.py`
- Test: `tests/test_materialization_map.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_materialization_map.py`:

```python
from __future__ import annotations

from polymer_grammar import FDRLedger, MaterializationContext
from polymer_protocol import Corpus

from polymer_claims._hashing import canonical_sha256
from polymer_claims.analysis_profile import content_hash
from polymer_claims.contracts import load_contract
from polymer_claims.materialization import materialization_map
from polymer_claims.methyl_adapters import region_delta_beta_claim
from polymer_claims.profiles import CANONICAL_EPICV2_V1

_BASE = MaterializationContext(id="M", api_version="v1", data_version="d1")


def _corpus(claim):
    return Corpus(claims=(claim,), fdr_ledger=FDRLedger(target_fdr=0.05))


def test_map_records_dimnames_and_profile_hash():
    c = region_delta_beta_claim("c0")
    mats = materialization_map(_corpus(c), _BASE)
    m = mats["c0"]
    assert m.dimnames_hash == load_contract("se:epicv2_casectrl_demo@1").dimnames_hash
    assert m.profile_hash == content_hash(CANONICAL_EPICV2_V1)
    # base fields preserved
    assert m.api_version == "v1" and m.data_version == "d1"


def test_semantic_run_id_is_deterministic_composite():
    c = region_delta_beta_claim("c0")
    m = materialization_map(_corpus(c), _BASE)["c0"]
    assert m.semantic_run_id is not None and m.semantic_run_id.startswith("sha256:")
    # recomputing the map gives the identical id
    m2 = materialization_map(_corpus(c), _BASE)["c0"]
    assert m.semantic_run_id == m2.semantic_run_id


def test_unresolvable_ref_is_skipped():
    c = region_delta_beta_claim("c-bad", ref="se:does_not_exist@1")
    mats = materialization_map(_corpus(c), _BASE)
    assert "c-bad" not in mats  # no enriched entry; caller falls back to base ctx


def test_unmatched_oracle_records_data_but_no_profile_hash():
    c = region_delta_beta_claim("c-noprof", oracle_ref="unknown_apparatus@9")
    m = materialization_map(_corpus(c), _BASE)["c-noprof"]
    assert m.dimnames_hash is not None
    assert m.profile_hash is None
```

- [ ] **Step 2: Run — confirm failure**

Run: `uv run --project . pytest tests/test_materialization_map.py -q` → FAIL (`ModuleNotFoundError: polymer_claims.materialization`).

- [ ] **Step 3: Write the map**

Create `src/polymer_claims/materialization.py`:

```python
"""CES-3: the per-claim content-address map. For each executable claim that references a
content-addressed dataset (a DataHandle) under an apparatus (oracle_ref), compute an enriched
MaterializationContext carrying its dimnames_hash (SE-Contract address, CES-1), profile_hash
(apparatus address, CES-0), and the composite semantic_run_id. Passed to run_cycle(materializations=)
so the minted Satisfaction records the full content-address. Umbrella/impure (load_contract reads the
bundled SE Contract); no numpy. See docs/specs/2026-06-12-ces-3-content-address-completeness-design.md.
"""
from __future__ import annotations

from polymer_grammar import DataHandle, MaterializationContext
from polymer_protocol.corpus import Corpus

from ._hashing import canonical_sha256
from .analysis_profile import content_hash, profile_oracle_id
from .contracts import load_contract
from .profiles import CANONICAL_EPICV2_V1


def _terminal_node(claim):
    plan = claim.evaluation_plan
    if plan is None:
        return None
    g = plan.graph
    return next((n for n in g.nodes if n.id == g.terminal), None)


def materialization_map(
    corpus: Corpus,
    base_ctx: MaterializationContext,
    *,
    profiles: tuple = (CANONICAL_EPICV2_V1,),
) -> dict[str, MaterializationContext]:
    """Per-claim enriched MaterializationContext keyed by claim id. A claim whose terminal node has
    no DataHandle, or whose DataHandle.ref does not resolve to a bundled contract, gets NO entry
    (the caller falls back to base_ctx). An oracle_ref with no matching profile records the dataset
    address but profile_hash=None."""
    by_oracle = {profile_oracle_id(p): p for p in profiles}
    out: dict[str, MaterializationContext] = {}
    for c in corpus.claims:
        node = _terminal_node(c)
        if node is None:
            continue
        handle = next((i for i in node.inputs if isinstance(i, DataHandle)), None)
        if handle is None:
            continue
        try:
            dimnames_hash = load_contract(handle.ref).dimnames_hash
        except FileNotFoundError:
            continue  # unresolvable ref -> skip; caller uses base ctx
        profile = by_oracle.get(node.oracle_ref) if node.oracle_ref else None
        profile_hash = content_hash(profile) if profile is not None else None
        semantic_run_id = canonical_sha256({
            "tool": node.impl,
            "param_signature": [list(p) for p in node.params],
            "input_signature": [dimnames_hash],
            "profile_hash": profile_hash,
        })
        out[c.id] = MaterializationContext(
            id=base_ctx.id,
            api_version=base_ctx.api_version,
            data_version=base_ctx.data_version,
            note=base_ctx.note,
            semantic_run_id=semantic_run_id,
            profile_hash=profile_hash,
            dimnames_hash=dimnames_hash,
        )
    return out
```

- [ ] **Step 4: Run tests**

Run: `uv run --project . pytest tests/test_materialization_map.py -q && uv run --project . ruff check src tests` → PASS, clean.

- [ ] **Step 5: Commit**

```bash
git add src/polymer_claims/materialization.py tests/test_materialization_map.py
git commit -m "feat(umbrella): materialization_map — per-claim content-address (dimnames+profile+semantic_run_id)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

## Task 4: End-to-end — record the content-address, then drift on it

**Files:**
- Create: `tests/test_ces3_content_address_e2e.py`

- [ ] **Step 1: Write the end-to-end tests**

Create `tests/test_ces3_content_address_e2e.py`:

```python
from __future__ import annotations

from polymer_grammar import FDRLedger, MaterializationContext, Status
from polymer_protocol import Corpus, run_cycle
from polymer_protocol.drift import drift_pass, reopen_drifted

from polymer_claims.analysis_profile import content_hash, profile_oracle_registry
from polymer_claims.contracts import load_contract
from polymer_claims.materialization import materialization_map
from polymer_claims.methyl_adapters import (
    RegionLmCoefAdapter, RegionMeanDiffAdapter, methyl_independent_registry, region_delta_beta_claim,
)
from polymer_claims.profiles import CANONICAL_EPICV2_V1

_ADAPTERS = (RegionMeanDiffAdapter(), RegionLmCoefAdapter())
_BASE = MaterializationContext(id="M", api_version="v1", data_version="d1")


def _run(claim):
    corpus = Corpus(claims=(claim,), fdr_ledger=FDRLedger(target_fdr=0.05))
    mats = materialization_map(corpus, _BASE)
    return run_cycle(corpus, _ADAPTERS, _BASE,
                     adapter_registry=methyl_independent_registry(),
                     oracles=profile_oracle_registry((CANONICAL_EPICV2_V1, "recomputable_public")),
                     materializations=mats)


def test_licensed_claim_records_full_content_address():
    result = _run(region_delta_beta_claim("c-true", threshold=0.10))
    c = next(x for x in result.corpus.claims if x.id == "c-true")
    assert c.status == Status.LICENSED
    m = c.licensing.satisfactions[0].materialization
    assert m.dimnames_hash == load_contract("se:epicv2_casectrl_demo@1").dimnames_hash
    assert m.profile_hash == content_hash(CANONICAL_EPICV2_V1)
    assert m.semantic_run_id is not None and m.semantic_run_id.startswith("sha256:")


def test_drift_reopens_on_dimnames_hash_change():
    result = _run(region_delta_beta_claim("c-true", threshold=0.10))
    licensed = result.corpus
    real_dim = load_contract("se:epicv2_casectrl_demo@1").dimnames_hash
    # "the data moved": same versions, a different dimnames_hash
    current = MaterializationContext(id="M", api_version="v1", data_version="d1",
                                     profile_hash=content_hash(CANONICAL_EPICV2_V1),
                                     dimnames_hash="sha256:" + "9" * 64)
    assert current.dimnames_hash != real_dim
    _, record = drift_pass(licensed, current=current)
    assert any(f.claim_id == "c-true" for f in record.drifted)
    reopened = reopen_drifted(licensed, record)
    c = next(x for x in reopened.claims if x.id == "c-true")
    assert c.status == Status.PENDING


def test_no_drift_when_content_address_matches():
    result = _run(region_delta_beta_claim("c-true", threshold=0.10))
    current = MaterializationContext(id="M", api_version="v1", data_version="d1",
                                     profile_hash=content_hash(CANONICAL_EPICV2_V1),
                                     dimnames_hash=load_contract("se:epicv2_casectrl_demo@1").dimnames_hash)
    _, record = drift_pass(result.corpus, current=current)
    assert not record.drifted
```

- [ ] **Step 2: Run**

Run: `uv run --project . pytest tests/test_ces3_content_address_e2e.py -q`
Expected: all PASS. If `test_licensed_claim_records_full_content_address` fails because the claim isn't LICENSED, print `c.status` + the executed value — the CES-2 licensing must still hold with the map supplied (the map only enriches the ctx; it must not change licensing). If the materialization lacks the hashes, the map isn't being threaded — re-check Task 1. Do NOT weaken an assertion to pass.

- [ ] **Step 3: ruff + commit**

```bash
uv run --project . ruff check src tests
git add tests/test_ces3_content_address_e2e.py
git commit -m "test(umbrella): CES-3 e2e — license records full content-address; drift re-opens on a data move

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

## Task 5: Full verification + docs

**Files:** Modify `docs/superpowers/CONTINUE.md`, `docs/superpowers/roadmaps/2026-06-11-credibility-arc-roadmap.md`.

- [ ] **Step 1: Full verification**

Run:
```bash
uv run --project . pytest tests/ -q && uv run --project . ruff check src tests
cd /Users/zbb2/Desktop/polymer-claims && bash scripts/check-all.sh
```
Expected: all umbrella green; ruff clean; `check-all.sh` → `ALL GREEN` (grammar/protocol/umbrella/isolation/viewer). The protocol changes are additive — every existing protocol test must still pass. If check-all fails, STOP and report BLOCKED with the failing output.

- [ ] **Step 2: Confirm numpy containment unchanged**

Run: `uv run --project . python -c "import sys, polymer_claims; assert not any('numpy' in m for m in sys.modules), 'numpy leaked'; print('base import numpy-free OK')"`
Expected: OK (materialization.py imports no numpy).

- [ ] **Step 3: Docs**

Add a dated `✅ CES-3 DONE` entry near the top of `docs/superpowers/CONTINUE.md` (do NOT alter existing entries): the content-address is now RECORDED on a licensed claim's `Satisfaction.materialization` (`dimnames_hash`+`profile_hash`+`semantic_run_id`) via the umbrella `materialization_map` + the additive `run_cycle/execute_ground(materializations=)` seam (protocol pure — dict lookup; grammar untouched; Corpus 4); DRIFT (`_is_fresh`) now re-opens a content-addressed claim when its data or apparatus hash moves (tighten-only-when-present → back-compat); verified end-to-end (the CES-2 methylation claim records the full address, and a changed `dimnames_hash` re-opens it to PENDING). Note the carried caveats (semantic_run_id is the Python digest — validated R parity deferred; addresses synthetic betas until the real-data swap). Update the `▶▶ NEXT ACTION` line — the CES B1→B3 spine is now complete; candidates: real-public-data swap (CES-2 caveat), live-`serve` wiring of the materialization map + drift daemon, or the deferred n-DMPs reduction. Mark CES-3 done in the roadmap §1b.

- [ ] **Step 4: Commit**

```bash
git add docs/superpowers/CONTINUE.md docs/superpowers/roadmaps/2026-06-11-credibility-arc-roadmap.md
git commit -m "docs(ces-3): content-address completeness done — CONTINUE + roadmap

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

## Self-Review

**Spec coverage:**
- §1/§3 protocol seam (`materializations=` on execute_ground + run_cycle, pure lookup, back-compat) → Task 1. ✓
- §2 umbrella `materialization_map` (dimnames/profile/semantic_run_id, unresolvable-skip, unmatched-oracle) → Task 3. ✓
- §4 tightened `_is_fresh` (profile_hash/dimnames_hash when present; legacy fallback) → Task 2. ✓
- §5 tests: seam stamping + back-compat (T1), drift predicate (T2), map units (T3), e2e record+drift (T4), check-all (T5). ✓
- §6 fences (static — no serve wiring; additive protocol; grammar untouched; numpy containment) → no task wires serve; T5 step 2 confirms containment; check-all confirms grammar untouched. ✓

**Placeholder scan:** none — every step has complete code + exact commands. The Task-2 note "reuse test_drift.py's helper if present, else mirror" is paired with the full inline `_licensed_with` helper, so it is self-contained either way.

**Type consistency:** `materializations: dict[str, MaterializationContext] | None` identical across execute_ground (T1) and run_cycle (T1). `materialization_map(corpus, base_ctx, *, profiles=)` signature consistent across T3 definition + T3/T4 calls. `_is_fresh(claim, current)` unchanged signature (T2). The e2e (T4) calls `run_cycle(..., materializations=mats)` matching T1's param, and `drift_pass(corpus, current=)` / `reopen_drifted(corpus, record)` matching the existing drift.py signatures. The minted Satisfaction path `c.licensing.satisfactions[0].materialization` matches the grammar model used in verify.
