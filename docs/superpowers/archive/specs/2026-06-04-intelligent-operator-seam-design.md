# Intelligent-operator seam (protocol sub-project #4b, slice 3)

> **Status:** design spec, approved 2026-06-04. Scope = the **injected-intelligence boundary** for
> GENERATE — a `GenerationAdapter` protocol (real LLM/embedding operators live OUTSIDE the package, a
> deterministic reference adapter proves the seam in-package), a `compile_untrusted` guardrail (external
> generation can **propose but never license**), and a `bridge_proposer` that wraps adapters onto the
> existing bus so slice-2's credit economy governs each one. **Finishes #4b.** Pure protocol, **zero
> grammar changes** (mirrors #3a/#3b/#4a/#4b-1/#4b-2). Builds on #4a GENERATE (`5d7899f`), #4b-1
> provisional links (`64b8042`), #4b-2 executable rivals + credit economy (`8e0bba0`).

## 1. Purpose

#4a/#4b gave GENERATE a pure proposer bus, provisional edges, executable rivals, and a credit economy —
but every operator so far is a **pure, deterministic, in-package** function (`rival_generation`,
`frontier_attack`). The whole point of the bus seam was that **intelligent** operators (LLM hypothesis
generation, embedding-neighborhood analogy) could plug in behind it. They cannot live in this pure,
deterministic, no-network package — so slice-3 establishes the **boundary** where they attach, with the
discipline that makes external generation safe:

- **A typed seam** (`GenerationAdapter`) mirroring the Phase-8 evaluation `Adapter` (identity-tagged,
  injected, real implementations outside; a deterministic reference inside).
- **Guardrails** (`compile_untrusted`) — because an external model's output is **untrusted**: it may be
  malformed, may try to self-license, may impersonate another operator. The load-bearing safety property
  is **external generation can propose but never license** (licensing is minted only by the air-gapped
  `verify`, never asserted by an input).
- **A bridge** (`bridge_proposer`) that wraps adapters onto the existing `proposers=` bus, so **no
  `run_cycle` change is needed** and slice-2's per-operator **credit economy automatically governs each
  external adapter** by its identity.

This **finishes #4b**: "intelligence plugs in here, validated and governed," proven by an in-package
reference adapter. Real LLM/embedding adapters are a **deployment concern**, outside this repo.

## 2. Architecture

One new pure protocol module `generation_adapter.py` + exports. No grammar edits; no `run_cycle` change;
`Corpus` stays at 4 collections.

| Symbol | Kind | Responsibility |
|---|---|---|
| `GenerationAdapter` | Protocol | `identity: str` + `propose(corpus, frontier) -> tuple[Proposal, ...]` — the injected-intelligence boundary |
| `compile_untrusted(claim, identity, *, fingerprint) -> tuple[Claim \| None, str \| None]` | pure fn | the guardrail: clean+stamp an untrusted claim, or reject it with a reason |
| `bridge_proposer(adapters) -> Proposer` | factory | wrap adapters onto the bus: force identity, guardrail, drop rejected |
| `TemplateGenerationAdapter` | class | a deterministic in-package reference adapter (proves the seam) |

Data flow: `run_cycle(proposers=(bridge_proposer(adapters), *pure_ops))` → `generate_stage` runs the
bridge like any proposer → the bridge calls each adapter, guardrails its output, returns clean Proposals
→ `generate_stage`'s existing `compile_to_IR` + credit-economy admission folds them in.

## 3. The seam — `GenerationAdapter`

Mirrors the grammar's evaluation `Adapter` Protocol (identity-tagged, injected, reference impls
in-package):

```python
from typing import Protocol
from polymer_grammar import Claim  # (Proposal/Corpus from .corpus)

class GenerationAdapter(Protocol):
    """The generation boundary. Real LLM/embedding operators implement this OUTSIDE the
    package; a deterministic reference adapter ships in-package. `identity` names the operator
    (it becomes the Proposal's operator_id, so the credit economy governs each adapter)."""

    identity: str

    def propose(self, corpus: Corpus, frontier: tuple[str, ...]) -> tuple[Proposal, ...]:
        """Return raw (untrusted) proposals. The bridge re-stamps operator_id and applies
        compile_untrusted; the adapter need not set provenance or a trustworthy operator_id."""
        ...
```

Notes: no `MaterializationContext` — generation is pre-execution (a proposed claim's *plan* is
materialized later, in EXECUTE). The adapter returns the existing `Proposal` type (claim + edges); the
bridge overrides `operator_id` (untrusted output cannot self-assign an operator).

## 4. The guardrail — `compile_untrusted`

```python
def compile_untrusted(
    claim: Claim, identity: str, *, fingerprint: str
) -> tuple[Claim | None, str | None]:
    """Clean + stamp an untrusted claim from a generation adapter, or reject it.
    Returns (cleaned_claim, None) on accept, or (None, reason) on reject."""
```

Checks, in order (first failure returns its reason; structural id/edge checks are left to
`generate_stage`'s existing `compile_to_IR`):

1. **No self-licensing (the load-bearing safety property).** Reject if `claim.licensing is not None`
   (reason `"untrusted-licensing"`) or `claim.status` is `LICENSED`/`REJECTED`
   (reason `"untrusted-status"`). External generation may only *propose*; licensing/rejection are earned
   through the pipeline, never asserted by an input.
2. **Allowed statuses only.** Permit `CONJECTURED`, or `PENDING` **with** an `evaluation_plan`
   (a real candidate). A `PENDING` claim **without** a plan is rejected (reason `"untrusted-status"`) —
   it could never execute and would just clutter SELECT.
3. **Force provenance (no spoofing).** Overwrite to
   `Provenance(generated_by=AGENT_GENERATED, agent_id=identity,
   method=f"{identity}@{fingerprint}", search_cardinality=max(1, declared))` — an untrusted claim cannot
   self-certify provenance or impersonate another operator. (`declared` = the incoming
   `provenance.search_cardinality` if it had agent provenance, else 1. `AGENT_GENERATED` ⇒ `agent_id`
   is satisfied by construction.)
4. **Preserve governance.** Leave `claim.governance` untouched — a conscientious adapter that flags its
   own output hazardous is honored by the existing `safety_gate` stage (which bars high/dual_use claims
   from autonomous execution corpus-wide). Slice-3 does **not** attempt to *detect* hazard in untrusted
   text (that needs a classifier — out of scope); it ensures declared governance survives to the gate.

Return the `model_copy(update={"provenance": forced})` claim. Because we reject LICENSED status and any
`licensing` block up front, the forced-provenance `model_copy` never collides with the
`LICENSED ⇒ licensing` validator.

## 5. The bridge — `bridge_proposer`

```python
def bridge_proposer(adapters: tuple[GenerationAdapter, ...]) -> Proposer:
    """Wrap injected generation adapters onto the existing bus as one Proposer. Each adapter's
    output is re-stamped with operator_id=adapter.identity and passed through compile_untrusted;
    rejected proposals are dropped. The returned Proposer plugs into run_cycle(proposers=...)."""
    def _proposer(corpus: Corpus, frontier: tuple[str, ...]) -> tuple[Proposal, ...]:
        fp = _corpus_fingerprint(corpus)
        out: list[Proposal] = []
        for a in adapters:
            for p in a.propose(corpus, frontier):
                clean, reason = compile_untrusted(p.claim, a.identity, fingerprint=fp)
                if clean is None:
                    continue  # rejected untrusted output dropped (see §5.1)
                out.append(Proposal(operator_id=a.identity, claim=clean, edges=p.edges))
        return tuple(out)
    return _proposer
```

- `operator_id` is **forced** to `a.identity` (untrusted output cannot impersonate `rival-generation`
  or another operator), so the **slice-2 credit economy governs each external adapter by its identity**
  with zero new wiring — a chronically-Goodhart-failing LLM adapter is throttled to a probation slot like
  any operator.
- Edges ride through unchanged; `generate_stage`'s `compile_to_IR` still validates edge source/target and
  rejects duplicates, and the cap/credit admission still applies. A provisional edge from an untrusted
  adapter is inert until its (conjectured) source licenses — same belief-neutrality as #4b-1.

### 5.1 Honest limitation: bridge-internal rejections aren't in the cycle's `GenerationRecord`

The bus `Proposer` signature returns only `tuple[Proposal, ...]` (no record), so a proposal that
`compile_untrusted` rejects is **dropped silently by the bridge** — it never becomes a `Proposal`, so the
cycle's `GenerationRecord.discarded` (which logs `generate_stage`'s own dup/edge/cap/operator-cap
discards) does not see it. `compile_untrusted` is therefore exposed as a **standalone, fully unit-tested**
function so every rejection path is pinned directly. Threading an untrusted-discard log into the
`GenerationRecord` is a future enhancement (would need the Proposer seam to return a record).

## 6. The reference adapter — `TemplateGenerationAdapter`

A pure, deterministic in-package `GenerationAdapter` (the `IdentityAdapter`/`ReferenceAdapter` analog for
generation) that proves the seam end-to-end without any model:

```python
class TemplateGenerationAdapter:
    """Deterministic reference GenerationAdapter: for each corpus claim (sorted by id), propose
    one CONJECTURED 'elaboration' conjecture with a content-addressed id. Proves the seam +
    guardrails + credit-economy wiring; ships no intelligence."""
    identity = "template-ref"

    def propose(self, corpus: Corpus, frontier: tuple[str, ...]) -> tuple[Proposal, ...]:
        props = []
        for c in sorted(corpus.claims, key=lambda c: c.id):
            cid = _gen_id("tmpl", c.id)
            claim = Claim(
                id=cid, title=f"elaboration of {c.id}", pattern=c.pattern,
                leaves=(CategoricalLeaf(ontology_term=f"template-elaboration-{c.id}"),),
                status=Status.CONJECTURED,
            )  # NO provenance/operator_id -> the bridge forces them (proves the guardrail path)
            props.append(Proposal(operator_id="UNSET", claim=claim))
        return tuple(props)
```

It deliberately emits no provenance and a placeholder `operator_id` so the bridge's identity-forcing and
provenance-stamping are exercised. (A `_is_own_output`-style convergence guard mirroring `proposers.py`
keeps it from re-elaborating its own outputs every cycle — skip claims whose id starts `gen-tmpl-`.)

## 7. Frontier-attack executable-generation: deferred (honest limit shrinks)

A `frontier_attack` seed defends a frontier node against an attacker; making it **executable** means
synthesizing a *new* hypothesis + an evaluation plan whose data refs point at the right materialization —
genuinely creative, domain-specific work that a pure structural transplant cannot do (unlike a rival,
which reuses its source's graph + subject; §slice-2). This is **precisely the injected adapter's job**:
an LLM/embedding `GenerationAdapter` with domain knowledge can propose a planned defense claim, which then
flows through `compile_untrusted` → the bus → SELECT/EXECUTE/VERIFY like any candidate. Slice-3 ships the
**seam that unblocks it**; the structural in-package operators (`frontier_attack`) keep emitting dormant
CONJECTURED seeds. The #4b honest limit shrinks to: *the pure in-package operators' frontier seeds stay
dormant; executable frontier-defense arrives with an injected intelligent adapter.*

## 8. Files & isolation

New module `protocol/src/polymer_protocol/generation_adapter.py` (pure: stdlib + grammar IR + `.corpus` +
`.generate` helpers `_gen_id`/`_corpus_fingerprint` — **no infra, no network, no LLM/embeddings, no
Date/random**). Exports: `GenerationAdapter`, `compile_untrusted`, `bridge_proposer`,
`TemplateGenerationAdapter`. Grammar imports nothing from protocol; protocol→grammar one-way; neither
imports `v1.2/formalclaim`. No `run_cycle` change (the bridge is a `Proposer`).

## 9. Testing

**`compile_untrusted` (standalone — every rejection path):**
- a LICENSED incoming claim → `(None, "untrusted-status")`; a claim carrying a `licensing` block →
  `(None, "untrusted-licensing")`; a REJECTED claim → `(None, "untrusted-status")`.
- a `PENDING` claim with **no** plan → `(None, "untrusted-status")`; a `PENDING` claim **with** a plan →
  accepted (cleaned).
- a CONJECTURED claim → accepted; the returned claim has `provenance.generated_by == AGENT_GENERATED`,
  `agent_id == identity`, `search_cardinality >= 1`, regardless of what provenance the input carried
  (force/overwrite — feed an input with `IMPORTED` provenance and assert it's overwritten).
- governance is preserved (a hazardous incoming claim keeps its `governance`).

**`bridge_proposer`:**
- forces `operator_id` to the adapter identity even if the raw Proposal claimed a different operator_id.
- drops a rejected (self-licensing) raw proposal, keeps the valid ones (mixed batch).
- two adapters with distinct identities → proposals tagged per identity (so the credit economy can tell
  them apart).
- the returned Proposer is a plain callable usable as `generate_stage(proposers=(bridge,))`.

**`TemplateGenerationAdapter`:**
- proposes one CONJECTURED conjecture per corpus claim (deterministic, sorted); ids start `gen-tmpl-`;
  skips its own prior outputs (convergence — a 2nd pass over a corpus containing its outputs adds nothing
  new for those).

**End-to-end through `run_cycle`:**
- `run_cycle(corpus, adapters, ctx, proposers=(bridge_proposer((TemplateGenerationAdapter(),)),))` folds
  in the template conjectures as CONJECTURED claims with `AGENT_GENERATED`/`agent_id="template-ref"`
  provenance — **belief-neutral** (grounded extension of the original claims unchanged), and the
  generation is governed by the credit economy when `generation_credit_floor` is set (the `template-ref`
  operator appears in allocation).
- **untrusted cannot license:** an adapter that tries to inject a LICENSED claim has it dropped — the
  claim never enters the corpus (pin the safety property end-to-end).

**Isolation:** `test_isolation.py` green (grammar↔protocol one-way; no formalclaim import); the new module
imports no infra/LLM.

## 10. Scope boundary

**This slice (#4b-3):** the `GenerationAdapter` seam + `compile_untrusted` guardrail + `bridge_proposer` +
the `TemplateGenerationAdapter` reference + tests. **Finishes #4b.**

**Deferred (later / out of repo):** real LLM/embedding adapters (live OUTSIDE the package, implement the
protocol); executable frontier-attack defense (an injected intelligent adapter's job, §7); an
untrusted-discard log in the `GenerationRecord` (§5.1); hazard *detection* in untrusted text (needs a
classifier); multi-adapter air-gap-style cross-checking of generation (generation isn't licensing, so the
≥2-distinct-identity rule doesn't apply here — that discipline stays on `verify`). Then sub-project **#5**
(the 3 daemons + loop-economics) and the grammar `representation_revision` meta-tier.
