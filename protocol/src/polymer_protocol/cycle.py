"""run_cycle: chain the deterministic assessment stages into one total Corpus transform.

Threads the ephemeral scaffolding/records; emits the post-INTEGRATE unresolved-attack
frontier as the cycle's primary output (the keystone closure — the next cycle's
GENERATE/SELECT target). GENERATE and SELECT are not in this sub-project: claims enter
exogenously and every committed, non-gated PENDING claim is executed. Spec §6.8.
"""
from __future__ import annotations

from polymer_grammar import Adapter, MaterializationContext, Status

from .canonicalize import canonicalize
from .commit import commit
from .corpus import Corpus, CycleResult, StageAudit
from .execute import execute_ground
from .integrate import integrate
from .represent import represent
from .safety import safety_gate
from .verify import verify_stage


def _locked_ids(corpus: Corpus) -> set[str]:
    return {
        c.id for c in corpus.claims
        if c.provenance is not None and c.provenance.preregistration_hash is not None
    }


def run_cycle(
    corpus: Corpus,
    adapters: tuple[Adapter, ...],
    ctx: MaterializationContext,
) -> CycleResult:
    audit: list[StageAudit] = []

    scaffolding = represent(corpus)
    audit.append(
        StageAudit(
            stage="represent",
            note=f"{len(scaffolding.grounded_extension)} grounded, {len(scaffolding.frontier)} on frontier",
            count=len(scaffolding.frontier),
        )
    )

    before_eq = len(corpus.equivalences)
    corpus = canonicalize(corpus)
    audit.append(
        StageAudit(
            stage="canonicalize",
            note=f"{len(corpus.equivalences) - before_eq} equivalence edge(s) added",
            count=len(corpus.equivalences) - before_eq,
        )
    )

    corpus, gated = safety_gate(corpus)
    audit.append(StageAudit(stage="safety_gate", note=f"{len(gated)} gated", count=len(gated)))

    locked_before = _locked_ids(corpus)
    corpus = commit(corpus)
    n_committed = len(_locked_ids(corpus) - locked_before)
    audit.append(StageAudit(stage="commit", note=f"{n_committed} claim(s) committed", count=n_committed))

    corpus, records = execute_ground(corpus, adapters, ctx)
    audit.append(StageAudit(stage="execute_ground", note=f"{len(records)} executed", count=len(records)))

    # scaffolding is still valid here: canonicalize/safety/commit/execute change neither
    # defeat_edges nor claim ids, so grounded_extension is unchanged since represent().
    executed_ids = {r.claim_id for r in records}
    corpus = verify_stage(corpus, scaffolding, records)
    n_licensed = sum(1 for c in corpus.claims if c.id in executed_ids and c.status == Status.LICENSED)
    audit.append(StageAudit(stage="verify_stage", note=f"{n_licensed} licensed", count=n_licensed))

    corpus, skipped = integrate(corpus, scaffolding, records)
    n_added = len(records) - len(skipped)
    audit.append(
        StageAudit(
            stage="integrate",
            note=f"{n_added} FDR test(s) added ({corpus.fdr_ledger.n_tests} total); {len(skipped)} skipped",
            count=n_added,
        )
    )

    frontier = represent(corpus).frontier
    # a gated claim can be retracted by INTEGRATE's consistency contest; keep the lane
    # consistent with the returned corpus so gated_lane ⊆ corpus claim ids.
    present = set(corpus.by_id())
    gated_lane = tuple(g for g in gated if g in present)
    return CycleResult(
        corpus=corpus,
        frontier=frontier,
        gated_lane=gated_lane,
        audit=tuple(audit),
    )
