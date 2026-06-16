# Intelligent-Operator Seam (#4b slice-3) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Establish the injected-intelligence boundary for GENERATE — a `GenerationAdapter` protocol (real LLM/embedding operators live OUTSIDE the package), a `compile_untrusted` guardrail (external generation can **propose but never license**), a `bridge_proposer` that wraps adapters onto the existing bus (so slice-2's credit economy governs each one), and a deterministic in-package reference adapter that proves the seam. Finishes #4b.

**Architecture:** One new pure protocol module `generation_adapter.py`. Mirrors the Phase-8 evaluation `Adapter` pattern (identity-tagged, injected, reference impl in-package). No grammar changes; no `run_cycle` change (the bridge is a `Proposer`, plugged via the existing `proposers=`). `Corpus` stays 4 collections.

**Tech Stack:** Python 3.14, Pydantic v2 (frozen models), `uv`, `pytest`. Package `protocol/` (`polymer_protocol`), one-way dep on `grammar/` (`polymer_grammar`).

**Spec:** `docs/superpowers/specs/2026-06-04-intelligent-operator-seam-design.md`

---

## Conventions

- All tasks run in `protocol/`: `cd /Users/zbb2/Desktop/polymer-claims/protocol && uv run pytest -q`. Lint with `uv run ruff check src tests` from that dir.
- Commit after each task with the message shown. Commits are LOCAL only. Every commit message ends with the `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>` line.
- Tasks are sequential: Task 1 (protocol + guardrail) → Task 2 (bridge) → Task 3 (reference adapter) → Task 4 (end-to-end + exports + docs). All four live in one new module `generation_adapter.py`.

## File Structure

| File | Pkg | Responsibility |
|---|---|---|
| `protocol/src/polymer_protocol/generation_adapter.py` | protocol | **NEW** — `GenerationAdapter` Protocol, `compile_untrusted`, `bridge_proposer`, `TemplateGenerationAdapter` |
| `protocol/src/polymer_protocol/__init__.py` | protocol | export the four new symbols |
| `protocol/tests/test_generation_adapter.py` | protocol | **NEW** — guardrail + bridge + reference adapter unit tests |
| `protocol/tests/test_cycle.py` | protocol | end-to-end seam tests |
| `README.md`, `docs/superpowers/CONTINUE.md` | repo | record slice-3 |

No grammar edits. `Corpus` unchanged (4 collections).

---

### Task 1: `GenerationAdapter` protocol + `compile_untrusted` guardrail

**Files:**
- Create: `protocol/src/polymer_protocol/generation_adapter.py`
- Test: `protocol/tests/test_generation_adapter.py`

- [ ] **Step 1: Write the failing tests** — create `protocol/tests/test_generation_adapter.py`:

```python
from __future__ import annotations

from polymer_grammar import (
    CategoricalLeaf,
    Claim,
    GenerationMode,
    Governance,
    HazardClass,
    Licensing,
    PatternRef,
    PendingReason,
    Provenance,
    RivalSetClosure,
    Status,
)

from polymer_protocol.generation_adapter import compile_untrusted

_PAT = PatternRef(id="adjusted_effect", version="v1")


def _claim(cid, status=Status.CONJECTURED, **extra):
    return Claim(
        id=cid,
        title=f"c {cid}",
        pattern=_PAT,
        leaves=(CategoricalLeaf(ontology_term=f"t-{cid}"),),
        status=status,
        **extra,
    )


def test_conjectured_claim_is_accepted_and_provenance_forced():
    raw = _claim("x")  # no provenance
    clean, reason = compile_untrusted(raw, "llm-7", fingerprint="fp")
    assert reason is None and clean is not None
    assert clean.provenance.generated_by == GenerationMode.AGENT_GENERATED
    assert clean.provenance.agent_id == "llm-7"
    assert clean.provenance.method == "llm-7@fp"
    assert clean.provenance.search_cardinality >= 1


def test_incoming_provenance_is_overwritten_not_trusted():
    raw = _claim("x", provenance=Provenance(generated_by=GenerationMode.IMPORTED, search_cardinality=1))
    clean, reason = compile_untrusted(raw, "llm-7", fingerprint="fp")
    assert reason is None
    assert clean.provenance.generated_by == GenerationMode.AGENT_GENERATED
    assert clean.provenance.agent_id == "llm-7"  # cannot keep an IMPORTED/forged provenance


def test_licensed_status_is_rejected():
    # an external generator must never inject a licensed claim (no self-licensing)
    lic = Licensing(route="severe_test", rival_set_closure=RivalSetClosure.OPEN_ACKNOWLEDGED,
                    rivals_considered=())
    raw = _claim("x", status=Status.LICENSED, licensing=lic)
    clean, reason = compile_untrusted(raw, "llm-7", fingerprint="fp")
    assert clean is None and reason == "untrusted-licensing"


def test_licensing_block_without_licensed_status_is_rejected():
    lic = Licensing(route="severe_test", rival_set_closure=RivalSetClosure.OPEN_ACKNOWLEDGED,
                    rivals_considered=())
    # construct a claim that carries a licensing block (force via model_construct if validators block it)
    raw = _claim("x").model_copy(update={"licensing": lic})
    clean, reason = compile_untrusted(raw, "llm-7", fingerprint="fp")
    assert clean is None and reason == "untrusted-licensing"


def test_rejected_status_is_rejected():
    raw = _claim("x", status=Status.REJECTED)
    clean, reason = compile_untrusted(raw, "llm-7", fingerprint="fp")
    assert clean is None and reason == "untrusted-status"


def test_pending_without_plan_is_rejected():
    raw = _claim("x", status=Status.PENDING, pending_reason=PendingReason.UNTESTED)
    clean, reason = compile_untrusted(raw, "llm-7", fingerprint="fp")
    assert clean is None and reason == "untrusted-status"


def test_governance_is_preserved():
    gov = Governance(hazard_class=HazardClass.DUAL_USE)
    raw = _claim("x", governance=gov)
    clean, reason = compile_untrusted(raw, "llm-7", fingerprint="fp")
    assert reason is None and clean.governance == gov  # safety_gate stage will route it
```

IMPORTANT: before running, confirm the grammar symbols import (`Governance`, `HazardClass`, `Licensing`, `RivalSetClosure`, `PendingReason`). Read `grammar/src/polymer_grammar/governance.py` + `licensing.py` for the REAL constructor kwargs (e.g. `Governance(hazard_class=...)`, `Licensing(route=..., rival_set_closure=..., rivals_considered=...)`) and ADAPT the test constructors to the real API — note any adaptation. `test_licensing_block_without_licensed_status_is_rejected` builds a claim carrying a `licensing` block while status is CONJECTURED; if the `Claim` validator forbids `licensing` on a non-LICENSED claim, use `raw.model_copy(update={"licensing": lic})` (model_copy bypasses validators) as shown — the point is to prove `compile_untrusted` rejects a stray licensing block regardless of status.

- [ ] **Step 2: Run to verify they fail**

Run: `cd /Users/zbb2/Desktop/polymer-claims/protocol && uv run pytest tests/test_generation_adapter.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'polymer_protocol.generation_adapter'`.

- [ ] **Step 3: Implement** — create `protocol/src/polymer_protocol/generation_adapter.py`:

```python
"""The intelligent-operator seam for GENERATE (#4b slice-3, spec §3-§6).

GenerationAdapter is the injected-intelligence boundary (real LLM/embedding operators implement
it OUTSIDE the package; a deterministic reference ships here). compile_untrusted is the guardrail:
external generation may PROPOSE but never LICENSE — licensing is minted only by the air-gapped
verify, never asserted by an input. bridge_proposer wraps adapters onto the existing bus so the
slice-2 credit economy governs each adapter by its identity. Pure, deterministic.
"""
from __future__ import annotations

from typing import Protocol

from polymer_grammar import Claim, GenerationMode, Provenance, Status

from .corpus import Corpus, Proposal

_ALLOWED = (Status.CONJECTURED, Status.PENDING)


class GenerationAdapter(Protocol):
    """The generation boundary. `identity` becomes the Proposal operator_id (credit-governed)."""

    identity: str

    def propose(self, corpus: Corpus, frontier: tuple[str, ...]) -> tuple[Proposal, ...]:
        ...


def compile_untrusted(
    claim: Claim, identity: str, *, fingerprint: str
) -> tuple[Claim | None, str | None]:
    """Clean+stamp an untrusted claim, or reject it. (cleaned, None) | (None, reason)."""
    if claim.licensing is not None:
        return None, "untrusted-licensing"
    if claim.status not in _ALLOWED:
        return None, "untrusted-status"
    if claim.status == Status.PENDING and claim.evaluation_plan is None:
        return None, "untrusted-status"
    declared = 1
    prov = claim.provenance
    if (
        prov is not None
        and prov.generated_by == GenerationMode.AGENT_GENERATED
        and prov.search_cardinality >= 1
    ):
        declared = prov.search_cardinality
    forced = Provenance(
        generated_by=GenerationMode.AGENT_GENERATED,
        agent_id=identity,
        method=f"{identity}@{fingerprint}",
        search_cardinality=max(1, declared),
    )
    return claim.model_copy(update={"provenance": forced}), None
```

Task 1 imports ONLY what it uses (shown above) — `bridge_proposer` (Task 2) and `TemplateGenerationAdapter` (Task 3) add their extra imports (`_corpus_fingerprint`, `Proposer`, `_gen_id`, `CategoricalLeaf`) when they land, so ruff stays clean at every step.

- [ ] **Step 4: Run to verify they pass**

Run: `cd /Users/zbb2/Desktop/polymer-claims/protocol && uv run pytest tests/test_generation_adapter.py -v`
Expected: all 7 PASS. Then `uv run ruff check src tests` — clean. Then full suite `uv run pytest -q` — green.

- [ ] **Step 5: Commit**

```bash
cd /Users/zbb2/Desktop/polymer-claims
git add protocol/src/polymer_protocol/generation_adapter.py protocol/tests/test_generation_adapter.py
git commit -m "feat(protocol): GenerationAdapter protocol + compile_untrusted guardrail (propose-not-license)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: `bridge_proposer`

**Files:**
- Modify: `protocol/src/polymer_protocol/generation_adapter.py`
- Test: `protocol/tests/test_generation_adapter.py`

- [ ] **Step 1: Write the failing tests** — append to `protocol/tests/test_generation_adapter.py`:

```python
def _corpus(claims=()):
    from polymer_grammar import FDRLedger
    from polymer_protocol.corpus import Corpus
    return Corpus(claims=tuple(claims), fdr_ledger=FDRLedger(target_fdr=0.05))


class _StubAdapter:
    def __init__(self, identity, proposals):
        self.identity = identity
        self._proposals = proposals

    def propose(self, corpus, frontier):
        return tuple(self._proposals)


def test_bridge_forces_operator_id_to_adapter_identity():
    from polymer_protocol.corpus import Proposal
    from polymer_protocol.generation_adapter import bridge_proposer
    raw = Proposal(operator_id="IMPERSONATING-rival-generation", claim=_claim("x"))
    proposer = bridge_proposer((_StubAdapter("llm-7", [raw]),))
    out = proposer(_corpus(), ())
    assert len(out) == 1 and out[0].operator_id == "llm-7"
    assert out[0].claim.provenance.agent_id == "llm-7"


def test_bridge_drops_rejected_keeps_valid():
    from polymer_protocol.corpus import Proposal
    from polymer_protocol.generation_adapter import bridge_proposer
    good = Proposal(operator_id="x", claim=_claim("good"))
    bad = Proposal(operator_id="x", claim=_claim("bad", status=Status.REJECTED))
    proposer = bridge_proposer((_StubAdapter("llm-7", [good, bad]),))
    out = proposer(_corpus(), ())
    assert [p.claim.id for p in out] == ["good"]  # the REJECTED one was dropped


def test_bridge_tags_each_adapter_distinctly():
    from polymer_protocol.corpus import Proposal
    from polymer_protocol.generation_adapter import bridge_proposer
    a = _StubAdapter("emb-A", [Proposal(operator_id="z", claim=_claim("a1"))])
    b = _StubAdapter("llm-B", [Proposal(operator_id="z", claim=_claim("b1"))])
    out = bridge_proposer((a, b))(_corpus(), ())
    tagged = {p.claim.id: p.operator_id for p in out}
    assert tagged == {"a1": "emb-A", "b1": "llm-B"}


def test_bridge_result_is_a_usable_proposer():
    from polymer_protocol.corpus import Proposal
    from polymer_protocol.generate import generate_stage
    from polymer_protocol.generation_adapter import bridge_proposer
    proposer = bridge_proposer((_StubAdapter("llm-7", [Proposal(operator_id="x", claim=_claim("x"))]),))
    corp, rec = generate_stage(_corpus(), (), proposers=(proposer,))
    assert "x" in [c.id for c in corp.claims]
    assert "x" in rec.admitted
```

- [ ] **Step 2: Run to verify they fail**

Run: `cd /Users/zbb2/Desktop/polymer-claims/protocol && uv run pytest tests/test_generation_adapter.py::test_bridge_forces_operator_id_to_adapter_identity -v`
Expected: FAIL — `cannot import name 'bridge_proposer'`.

- [ ] **Step 3: Implement** — in `generation_adapter.py`, add `Proposer` and `_corpus_fingerprint` to the imports (from `.generate`), then add:

```python
def bridge_proposer(adapters: tuple[GenerationAdapter, ...]) -> Proposer:
    """Wrap injected generation adapters onto the bus as one Proposer: force operator_id to
    each adapter's identity, run compile_untrusted, drop rejected. Plugs into
    run_cycle(proposers=...). Bridge-internal rejections are dropped (not in GenerationRecord;
    see spec §5.1) — compile_untrusted is independently unit-tested."""
    def _proposer(corpus: Corpus, frontier: tuple[str, ...]) -> tuple[Proposal, ...]:
        fp = _corpus_fingerprint(corpus)
        out: list[Proposal] = []
        for a in adapters:
            for p in a.propose(corpus, frontier):
                clean, _reason = compile_untrusted(p.claim, a.identity, fingerprint=fp)
                if clean is None:
                    continue
                out.append(Proposal(operator_id=a.identity, claim=clean, edges=p.edges))
        return tuple(out)

    return _proposer
```

The `.generate` import line becomes: `from .generate import Proposer, _corpus_fingerprint, _gen_id` — keep `_gen_id` only if Task 3 lands in the same edit; otherwise add `_gen_id` in Task 3 and import just `Proposer, _corpus_fingerprint` here.

- [ ] **Step 4: Run to verify they pass**

Run: `cd /Users/zbb2/Desktop/polymer-claims/protocol && uv run pytest tests/test_generation_adapter.py -v` (Task 1 + Task 2 tests PASS). Then `uv run pytest -q` (full suite green) and `uv run ruff check src tests` (clean).

- [ ] **Step 5: Commit**

```bash
cd /Users/zbb2/Desktop/polymer-claims
git add protocol/src/polymer_protocol/generation_adapter.py protocol/tests/test_generation_adapter.py
git commit -m "feat(protocol): bridge_proposer — wrap generation adapters onto the bus (identity-forced, guardrailed)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: `TemplateGenerationAdapter` (deterministic reference)

**Files:**
- Modify: `protocol/src/polymer_protocol/generation_adapter.py`
- Test: `protocol/tests/test_generation_adapter.py`

- [ ] **Step 1: Write the failing tests** — append:

```python
def test_template_adapter_proposes_one_conjecture_per_claim():
    from polymer_protocol.generation_adapter import TemplateGenerationAdapter
    corp = _corpus([_claim("a"), _claim("b")])
    props = TemplateGenerationAdapter().propose(corp, ())
    assert len(props) == 2
    for p in props:
        assert p.claim.status == Status.CONJECTURED
        assert p.claim.id.startswith("gen-tmpl-")
        assert p.claim.conclusion is None and p.edges == ()


def test_template_adapter_is_deterministic():
    from polymer_protocol.generation_adapter import TemplateGenerationAdapter
    corp = _corpus([_claim("b"), _claim("a")])
    a1 = TemplateGenerationAdapter().propose(corp, ())
    a2 = TemplateGenerationAdapter().propose(corp, ())
    assert [p.claim.id for p in a1] == [p.claim.id for p in a2]


def test_template_adapter_skips_its_own_outputs():
    from polymer_protocol.generation_adapter import TemplateGenerationAdapter
    adapter = TemplateGenerationAdapter()
    corp = _corpus([_claim("a")])
    first = adapter.propose(corp, ())
    # fold its output into the corpus, propose again: it must NOT re-elaborate gen-tmpl-* claims
    grown = _corpus([_claim("a"), first[0].claim])
    second = adapter.propose(grown, ())
    assert [p.claim.id for p in second] == [p.claim.id for p in first]  # only "a" elaborated, converges


def test_template_adapter_identity():
    from polymer_protocol.generation_adapter import TemplateGenerationAdapter
    assert TemplateGenerationAdapter().identity == "template-ref"
```

Note: `test_template_adapter_skips_its_own_outputs` relies on the adapter skipping claims whose id starts `gen-tmpl-`. Confirm the proposed claim from `propose` carries an id starting `gen-tmpl-` (from `_gen_id("tmpl", c.id)`).

- [ ] **Step 2: Run to verify they fail**

Run: `cd /Users/zbb2/Desktop/polymer-claims/protocol && uv run pytest tests/test_generation_adapter.py::test_template_adapter_identity -v`
Expected: FAIL — `cannot import name 'TemplateGenerationAdapter'`.

- [ ] **Step 3: Implement** — in `generation_adapter.py`, ensure `CategoricalLeaf` and `_gen_id` are imported (add to the grammar import and the `.generate` import), then add:

```python
class TemplateGenerationAdapter:
    """Deterministic reference GenerationAdapter (the IdentityAdapter analog for generation):
    one CONJECTURED 'elaboration' conjecture per corpus claim (sorted by id, content-addressed).
    Emits no provenance and a placeholder operator_id so the bridge's forcing path is exercised;
    skips its own gen-tmpl-* outputs so the corpus converges. Ships no intelligence."""

    identity = "template-ref"

    def propose(self, corpus: Corpus, frontier: tuple[str, ...]) -> tuple[Proposal, ...]:
        props: list[Proposal] = []
        for c in sorted(corpus.claims, key=lambda c: c.id):
            if c.id.startswith("gen-tmpl-"):
                continue  # convergence guard: don't re-elaborate own outputs
            cid = _gen_id("tmpl", c.id)
            claim = Claim(
                id=cid,
                title=f"elaboration of {c.id}",
                pattern=c.pattern,
                leaves=(CategoricalLeaf(ontology_term=f"template-elaboration-{c.id}"),),
                status=Status.CONJECTURED,
            )
            props.append(Proposal(operator_id="UNSET", claim=claim))
        return tuple(props)
```

- [ ] **Step 4: Run to verify they pass**

Run: `cd /Users/zbb2/Desktop/polymer-claims/protocol && uv run pytest tests/test_generation_adapter.py -v` (all PASS). Then `uv run pytest -q` (full suite green), `uv run ruff check src tests` (clean).

- [ ] **Step 5: Commit**

```bash
cd /Users/zbb2/Desktop/polymer-claims
git add protocol/src/polymer_protocol/generation_adapter.py protocol/tests/test_generation_adapter.py
git commit -m "feat(protocol): TemplateGenerationAdapter — deterministic in-package reference adapter

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: end-to-end through `run_cycle` + exports + docs

**Files:**
- Modify: `protocol/src/polymer_protocol/__init__.py`, `protocol/tests/test_cycle.py`, `README.md`, `docs/superpowers/CONTINUE.md`

- [ ] **Step 1: Write the end-to-end tests** — append to `protocol/tests/test_cycle.py`:

```python
def test_seam_folds_in_governed_conjectures(empty_ledger, ctx, adapters):
    from polymer_protocol.generation_adapter import TemplateGenerationAdapter, bridge_proposer
    from polymer_protocol.represent import represent
    a = make_claim("a")
    b = make_claim("b")
    corp = Corpus(claims=(a, b), defeat_edges=(), fdr_ledger=empty_ledger)
    bridge = bridge_proposer((TemplateGenerationAdapter(),))
    g0 = represent(corp).grounded_extension
    r1 = run_cycle(corp, adapters, ctx, proposers=(bridge,))
    by = r1.corpus.by_id()
    tmpl = [cid for cid in by if cid.startswith("gen-tmpl-")]
    assert len(tmpl) == 2  # one elaboration per original claim
    for cid in tmpl:
        assert by[cid].provenance.generated_by.value == "agent_generated"
        assert by[cid].provenance.agent_id == "template-ref"  # identity forced by the bridge
    # belief-neutral: the original claims' grounded membership is unchanged
    assert {"a", "b"} & set(represent(r1.corpus).grounded_extension) == {"a", "b"} & set(g0)


def test_seam_untrusted_claim_cannot_license(empty_ledger, ctx, adapters):
    from polymer_grammar import CategoricalLeaf, Claim, Licensing, PatternRef, RivalSetClosure, Status
    from polymer_protocol.corpus import Proposal
    from polymer_protocol.generation_adapter import bridge_proposer

    class _CheatingAdapter:
        identity = "cheater"
        def propose(self, corpus, frontier):
            lic = Licensing(route="severe_test", rival_set_closure=RivalSetClosure.OPEN_ACKNOWLEDGED,
                            rivals_considered=())
            forged = Claim(
                id="forged", title="forged", pattern=PatternRef(id="adjusted_effect", version="v1"),
                leaves=(CategoricalLeaf(ontology_term="t"),), status=Status.LICENSED, licensing=lic,
            )
            return (Proposal(operator_id="cheater", claim=forged),)

    corp = Corpus(claims=(make_claim("a"),), fdr_ledger=empty_ledger)
    r1 = run_cycle(corp, adapters, ctx, proposers=(bridge_proposer((_CheatingAdapter(),)),))
    assert "forged" not in r1.corpus.by_id()  # compile_untrusted dropped it; it never entered the corpus
```

Adapt the `Licensing(...)` constructor to the REAL grammar API (read `licensing.py`) — the assertion (forged LICENSED claim never enters the corpus) is what must stand. Confirm `make_claim`, `run_cycle`, `Corpus`, `represent` usage matches the file's existing patterns.

- [ ] **Step 2: Run to verify**

Run: `cd /Users/zbb2/Desktop/polymer-claims/protocol && uv run pytest tests/test_cycle.py::test_seam_folds_in_governed_conjectures tests/test_cycle.py::test_seam_untrusted_claim_cannot_license -v`
Expected: PASS. If the cheating-adapter claim DOES enter the corpus, that's a real guardrail gap — STOP and report.

- [ ] **Step 3: Export the new symbols** — in `protocol/src/polymer_protocol/__init__.py`, add an import (alphabetical, near `from .generate ...`):
```python
from .generation_adapter import (
    GenerationAdapter,
    TemplateGenerationAdapter,
    bridge_proposer,
    compile_untrusted,
)
```
and add `"GenerationAdapter"`, `"TemplateGenerationAdapter"`, `"bridge_proposer"`, `"compile_untrusted"` to `__all__`. Verify: `cd /Users/zbb2/Desktop/polymer-claims/protocol && uv run python -c "import polymer_protocol as p; print(p.GenerationAdapter, p.bridge_proposer, p.compile_untrusted, p.TemplateGenerationAdapter)"` — no error.

- [ ] **Step 4: Get the test count + update `README.md`**

Run: `cd /Users/zbb2/Desktop/polymer-claims/protocol && uv run pytest -q 2>&1 | tail -1` (protocol count `<P>`). Grammar unchanged at 268. Update the protocol status-table row to append `+ intelligent-operator seam` and the new count, and after the slice-2 paragraph add:

> The bus is now open to **injected intelligence** (#4b slice-3): a `GenerationAdapter` (real LLM/embedding
> operators implement it *outside* the package; `TemplateGenerationAdapter` is the in-package reference)
> plugs in via `bridge_proposer`, and `compile_untrusted` enforces the load-bearing rule that **external
> generation can propose but never license** — a claim arriving pre-licensed is dropped; provenance is
> forced to `AGENT_GENERATED` with the adapter's identity (which the slice-2 credit economy then governs).
> This finishes #4b. (Executable frontier-attack defense and real model adapters live behind the seam.)

- [ ] **Step 5: Update `docs/superpowers/CONTINUE.md`** — add a Current-state paragraph for #4b slice-3 (DONE, branch `feat/intelligent-operator-seam-4b`, merge SHA `<pending>`): the `GenerationAdapter` seam (Phase-8 mirror), `compile_untrusted` (propose-not-license: reject LICENSED/REJECTED/licensing-block, force AGENT_GENERATED+agent_id, preserve governance for the safety gate), `bridge_proposer` (identity-forced, credit-economy-governed, no run_cycle change), `TemplateGenerationAdapter` reference. Note zero grammar changes, `<P>` protocol tests, **#4b COMPLETE**. Record the load-bearing decisions: (1) generic GenerationAdapter seam (one boundary for embedding AND LLM); (2) full compile_untrusted guardrail with the propose-not-license safety property; (3) frontier-attack executable-gen deferred to injected adapters (honest limit shrinks). Repoint NEXT at **#5 daemons** (the user's stated arc: finish #4b → #5) and the grammar `representation_revision` meta-tier. Keep the existing CONTINUE format.

- [ ] **Step 6: Commit**

```bash
cd /Users/zbb2/Desktop/polymer-claims
git add protocol/src/polymer_protocol/__init__.py protocol/tests/test_cycle.py README.md docs/superpowers/CONTINUE.md
git commit -m "feat(protocol): end-to-end intelligent-operator seam + exports + docs (#4b complete)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Final review

After Task 4, dispatch the whole-package Opus review (per subagent-driven-development) — protocol-only (grammar untouched; still confirm grammar↔protocol isolation holds and the new module has no infra/LLM/Date/random imports). Pay special attention to the propose-not-license safety property (untrusted output can never enter as LICENSED, and provenance can't be spoofed) and belief-neutrality of the folded-in conjectures. Then `superpowers:finishing-a-development-branch` (merge no-ff to main, verify protocol + grammar suites on the merged result, delete the branch). Backfill the merge SHA into CONTINUE.md. Update memory (`project_polymer_claims_knowledge_protocol.md` + `MEMORY.md`) with the merge SHA + decisions + that **#4b is COMPLETE**.

## Progress Log

- (fill in per task: commit SHA + any decisions/deviations)
