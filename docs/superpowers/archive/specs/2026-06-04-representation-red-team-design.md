# #5c REPRESENTATION RED-TEAM daemon — design spec

> **Status:** approved design, 2026-06-04. Third daemon slice of sub-project #5 (the daemons +
> loop-economics). Roadmap: `docs/superpowers/roadmaps/2026-06-04-sub5-daemons-roadmap.md`. Builds on the
> COMPLETE protocol spine (#1–#4b), #5a DRIFT, #5b ORACLE-VALIDATION, and the just-shipped grammar
> `representation_revision` meta-tier. Rhythm: this spec → plan (writing-plans) → subagent-driven build →
> merge no-ff → memory.

## What this builds

The **REPRESENTATION RED-TEAM**: a daemon that adversarially attacks the corpus's *representation* — a
claim whose pattern/subject/leaves mis-frame what it asserts — and **proposes a representation-revision
claim** to fix it. Two protocol-side pieces, both reusing seams that already exist:

1. An in-package **reference adversarial `GenerationAdapter`** (`RepresentationRedTeamAdapter`) that
   proposes CONJECTURED claims carrying a `RepresentationRevision` payload through the EXISTING #4b-3 bus
   (`compile_untrusted` + `bridge_proposer`). Real LLM red-teamers implement the same `GenerationAdapter`
   Protocol and inject the same way; the in-package adapter is the deterministic plumbing reference (the
   `TemplateGenerationAdapter` analog — ships NO intelligence).
2. The **conservative meta-tier gate** in `verify_stage`: a representation-revision claim is NOT auto-
   licensed via the ordinary single-severe-test path; it stays PENDING until replication-grade licensing
   is supplied. This enforces the meta-tier's "schema changes are gated more conservatively" intent (the
   deferred gate from the meta-tier slice).

## Resolved forks (from the brainstorm)

- **Full propose-revisions adapter** (not a flag-only stub): the meta-tier unblocks proposing real
  representation-revision claims.
- **The gate lives in #5c** (a `verify_stage` guard), not deferred to #5d: #5c is the slice that introduces
  representation-revisions into the live cycle, so it is where the conservative gate must bite — making #5c
  a complete unit (proposes AND gates).

## The seams (already in the codebase)

- **`GenerationAdapter` Protocol** (`protocol/generation_adapter.py`): `identity: str` +
  `propose(corpus, frontier) -> tuple[Proposal, ...]`. **`compile_untrusted`** forces AGENT_GENERATED
  provenance + rejects any claim carrying a `licensing` block or a non-{CONJECTURED, PENDING-with-plan}
  status (propose-not-license). **`bridge_proposer(adapters)`** wraps adapters onto the bus as one
  `Proposer` (forces `operator_id=identity`, runs `compile_untrusted`, drops rejected). **No `run_cycle`
  change** is needed — the bridge plugs into the existing `proposers=` port.
- **`TemplateGenerationAdapter`** (same module): the deterministic in-package reference pattern this slice
  mirrors — one CONJECTURED proposal per corpus claim (sorted, content-addressed `gen-tmpl-*` ids), skips
  its own outputs to converge, `operator_id="UNSET"` so the bridge's forcing path is exercised.
- **`RepresentationRevision`** (`grammar/representation.py`): `operation` × discriminated `target` +
  `rationale` (+ optional `proposed_definition`). `Claim.representation_revision` is additive-optional. A
  claim's `pattern` is a `PatternRef`, so `PatternTarget(patterns=(claim.pattern,))` is a ready target for a
  DEPRECATE-of-1.
- **`is_representation_revision(claim)`** + **`meets_meta_tier_bar(licensing)`** (grammar): the gate's two
  predicates. `meets_meta_tier_bar` requires `route==REPLICATION AND closure ∈ {ENUMERATED,
  ONTOLOGY_BOUNDED}`.
- **`verify_stage`** (`protocol/verify.py`): the LICENSED branch assembles
  `Licensing(route=SEVERE_TEST, rival_set_closure=OPEN_ACKNOWLEDGED, ...)` — which FAILS
  `meets_meta_tier_bar`. The else branch keeps a claim PENDING (`new_claims.append(c)`).
- **`_gen_id`** / **`_corpus_fingerprint`** (`protocol/generate.py`): content-addressed proposal ids.

## Component 1 — `protocol/src/polymer_protocol/red_team.py` (new module)

```python
class RepresentationRedTeamAdapter:
    """Deterministic reference REPRESENTATION RED-TEAM as a GenerationAdapter (the
    TemplateGenerationAdapter analog for the meta-tier): for each corpus claim it proposes one CONJECTURED
    claim carrying a RepresentationRevision that flags the claim's pattern for review. Ships NO real
    red-teaming intelligence — real LLM red-teamers implement the same Protocol and inject via
    bridge_proposer. Belief-neutral (isolated CONJECTURED nodes, no edges); converges (skips its own
    outputs and existing representation-revision claims)."""

    identity = "representation-red-team"

    def propose(self, corpus: Corpus, frontier: tuple[str, ...]) -> tuple[Proposal, ...]:
        props: list[Proposal] = []
        for c in sorted(corpus.claims, key=lambda c: c.id):
            if c.id.startswith("gen-rt-"):
                continue  # convergence: don't red-team own outputs
            if c.representation_revision is not None:
                continue  # convergence: don't red-team a representation-revision claim
            cid = _gen_id("rt", c.id)
            revision = RepresentationRevision(
                operation=RevisionOperation.DEPRECATE,
                target=PatternTarget(patterns=(c.pattern,)),
                rationale=f"red-team review of the representation used by {c.id}",
            )
            claim = Claim(
                id=cid,
                title=f"representation review of {c.id}",
                pattern=c.pattern,
                leaves=(CategoricalLeaf(ontology_term=f"red-team-{c.id}"),),
                status=Status.CONJECTURED,
                representation_revision=revision,
            )
            props.append(Proposal(operator_id="UNSET", claim=claim))
        return tuple(props)
```

- `_gen_id("rt", c.id)` yields `gen-rt-<hash>` ids; the `gen-rt-` skip + the `representation_revision is not
  None` skip together guarantee a second cycle adds nothing (convergence).
- `operator_id="UNSET"` (forced to `identity` by `bridge_proposer`) exercises the forcing path, exactly like
  `TemplateGenerationAdapter`.
- Emits NO defeat edges and NO `incompatible_with` — belief-neutral isolated CONJECTURED nodes (the #4a
  lesson: a CONJECTURED claim must encode no incompatibility).
- Pure / deterministic: sorted iteration, content-addressed ids, no clock/random/env.

## Component 2 — the conservative meta-tier gate in `verify_stage`

In `protocol/src/polymer_protocol/verify.py`, the LICENSED branch currently licenses a claim once it has a
minted satisfaction + grounded-extension membership + provenance + clears the BH bar. Add the gate right
after the `licensing` object is built (lines ~89–93):

```python
            licensing = Licensing(
                route=LicenseRoute.SEVERE_TEST,
                satisfactions=(ev.satisfaction,),
                rival_set_closure=RivalSetClosure.OPEN_ACKNOWLEDGED,
            )
            if is_representation_revision(c) and not meets_meta_tier_bar(licensing):
                # a representation-revision is gated MORE conservatively: it cannot ride the ordinary
                # single-severe-test path. Hold it PENDING until replication-grade licensing is supplied.
                new_claims.append(c)
                continue
            new_claims.append(_with_status(c, status=Status.LICENSED, licensing=licensing, ...))
```

Add the import `is_representation_revision, meets_meta_tier_bar` from `polymer_grammar`. Because the auto-
assembled licensing is always `SEVERE_TEST/OPEN_ACKNOWLEDGED` (below the bar), the gate holds EVERY
representation-revision back from auto-licensing — it remains PENDING (it already carries a valid
`pending_reason` since it was a PENDING+plan claim that got executed). A non-revision claim is unaffected
(the guard only fires when `is_representation_revision(c)`).

**`continue` vs the REJECTED branch:** holding PENDING (not REJECTING) is deliberate — the revision is not
refuted, it merely hasn't earned the conservative bar. A future replication path / exogenous port can later
supply REPLICATION+closed licensing and license it.

## Data flow

```
RepresentationRedTeamAdapter (+ injected LLM red-teamers)
   └─ bridge_proposer(adapters)  ──>  run_cycle(proposers=...)
        └─ generate_stage: compile_untrusted forces AGENT_GENERATED provenance, drops forged-licensing
             └─ CONJECTURED representation-revision claims fold into the corpus (belief-neutral)
                  └─ if one later gains a plan + is executed: verify_stage GATE holds it PENDING
                       (needs replication-grade licensing — the cheap severe-test path is refused)
```

The red-team **proposes**; licensing a representation change stays a governed, replication-gated act.

## Scope fences (explicit non-goals)

- **The reference adapter ships no intelligence** — a deterministic placeholder (DEPRECATE the claim's
  pattern); real detection (matching claim content to a pattern's `excluded_applications`, etc.) is the
  injected LLM red-teamer's job via the same Protocol.
- **No replication-licensing path built** — representation-revisions correctly remain PENDING under current
  machinery; the path that *grants* a revision replication-grade licensing (a REPLICATION route across
  independent materializations) is out of scope (future / exogenous / human port).
- **No `run_cycle` signature change** — the adapter plugs in through the existing `proposers=` port; the
  gate is internal to `verify_stage`.
- **Grammar untouched** (the meta-tier shipped last slice); Corpus stays 4 collections.

## Invariants preserved

- One-way isolation: `red_team.py` imports `polymer_grammar` (Claim, CategoricalLeaf, RepresentationRevision,
  RevisionOperation, PatternTarget, Status) + `.corpus` + `.generate` (`_gen_id`); grammar never imports
  protocol. `verify.py` adds a grammar-helpers import only.
- Belief-neutrality verified THROUGH `run_cycle` (operator-level before/after is necessary but not
  sufficient — the #4a lesson).
- All proposals are CONJECTURED isolated nodes (no edges) → the grounded extension of existing claims is
  unchanged. Content-addressed ids + skip-own-output + skip-revision-claims → convergence.
- Pure / deterministic / caller-scheduled; no clock/random/env.
- Exports: add `RepresentationRedTeamAdapter` to `protocol/__init__.py`.

## Testing

**`RepresentationRedTeamAdapter` (`protocol/tests/test_red_team.py`):**
- Proposes one CONJECTURED claim per eligible corpus claim; each carries a valid `RepresentationRevision`
  (operation DEPRECATE, `PatternTarget` of exactly 1 = the claim's pattern); `is_representation_revision`
  is True on each proposed claim.
- Skips its own `gen-rt-*` outputs AND skips claims that already carry a `representation_revision`
  (a second `propose` over a corpus grown with its outputs adds nothing — convergence).
- Deterministic: same corpus → identical proposals; sorted by source claim id.

**Through the bus:**
- `bridge_proposer((RepresentationRedTeamAdapter(),))` returns a usable `Proposer`; `compile_untrusted`
  forces `provenance.agent_id == "representation-red-team"` on each proposed claim and forces the
  `operator_id`.
- A red-team proposal carrying a forged `licensing` block is dropped by `compile_untrusted` (reuse the
  existing guarantee — pin it once for a representation-revision claim).
- `generate_stage(..., proposers=(bridge_proposer((adapter,)),))` admits the CONJECTURED revision claims
  into the corpus.

**Belief-neutrality + convergence through `run_cycle`:**
- A `run_cycle` with the red-team proposer leaves the grounded extension of pre-existing claims unchanged.
- A second `run_cycle` adds no new claims (convergence).

**The gate (`verify_stage`):**
- A representation-revision claim that has a plan, executes, is in the grounded extension, and clears the BH
  bar is NOT licensed — it stays PENDING (its status is unchanged, `licensing is None`).
- A structurally-identical NON-revision claim in the same position IS licensed (the gate is revision-
  specific).
- `meets_meta_tier_bar` on the auto-assembled `Licensing(SEVERE_TEST, OPEN_ACKNOWLEDGED)` is False (pins why
  the gate fires); on a `Licensing(REPLICATION, ENUMERATED, ...)` it is True (a supplied replication-grade
  licensing would pass — unit-level on the predicate, already covered in the grammar tests but re-pinned in
  the gate's context).

**Package:**
- `RepresentationRedTeamAdapter` imports from `polymer_protocol`.

## Files

- Create: `protocol/src/polymer_protocol/red_team.py`
- Modify: `protocol/src/polymer_protocol/verify.py` (the gate + the grammar-helpers import)
- Modify: `protocol/src/polymer_protocol/__init__.py` (export `RepresentationRedTeamAdapter`)
- Test:   `protocol/tests/test_red_team.py` (adapter + bus + belief-neutrality)
- Test:   `protocol/tests/test_verify_meta_tier_gate.py` (the gate) — or add to an existing verify test file if cleaner
