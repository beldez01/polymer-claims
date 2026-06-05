"""run_cycle: chain the deterministic assessment stages into one total Corpus transform.

Threads the ephemeral scaffolding/records; emits the post-INTEGRATE unresolved-attack
frontier as the cycle's primary output (the keystone closure). SELECT (the value/pursuit
stage) is now wired in: it ranks eligible PENDING claims on value under a structured cost
and a budget, and only the selected subset is committed and executed; the selection record
travels on the CycleResult. GENERATE (the proposer bus) is now wired in right after REPRESENT:
it runs passed-in proposers + the exogenous injection port through compile_to_IR and folds new
CONJECTURED claims into the corpus (belief-neutral — no defeat edges; inert this cycle, first
act next). A threaded SelectionLedger (passed in via `ledger=` and returned on CycleResult) carries
cross-cycle accumulating belief + per-operator surprise-Goodhart credit; an optional
OracleRegistry caps a licensed claim's empirical strength at VERIFY; SELECT also supports a
quality-diversity portfolio (cell caps) and a heterodox reserve lane (both off by default).
Spec §6.8 + SELECT #3a/#3b + GENERATE #4a + oracle dossier #2.
"""
from __future__ import annotations

from polymer_grammar import Adapter, Claim, MaterializationContext, Status

from .canonicalize import canonicalize
from .commit import commit
from .corpus import Corpus, CycleResult, StageAudit, is_locked
from .cost import CostModel, CostWeights
from .execute import execute_ground
from .generate import Proposer, generate_stage
from .integrate import integrate
from .ledger import ExecutedOutcome, SelectionLedger, operator_of, update_ledger
from .oracle import OracleRegistry
from .represent import represent
from .safety import safety_gate
from .select import ValueWeights, select_stage
from .verify import verify_stage


def _locked_ids(corpus: Corpus) -> set[str]:
    return {c.id for c in corpus.claims if is_locked(c)}


def run_cycle(
    corpus: Corpus,
    adapters: tuple[Adapter, ...],
    ctx: MaterializationContext,
    oracles: OracleRegistry | None = None,
    *,
    cost_model: CostModel | None = None,
    budget: float | None = None,
    value_weights: ValueWeights = ValueWeights(),
    cost_weights: CostWeights = CostWeights(),
    proposers: tuple[Proposer, ...] = (),
    injected: tuple[Claim, ...] = (),
    generation_cap: int | None = None,
    ledger: SelectionLedger | None = None,
    reserve_fraction: float = 0.0,
    cell_cap_fraction: float = 1.0,
    generation_credit_floor: float | None = None,
) -> CycleResult:
    audit: list[StageAudit] = []
    led = ledger if ledger is not None else SelectionLedger()

    scaffolding = represent(corpus)
    audit.append(
        StageAudit(
            stage="represent",
            note=f"{len(scaffolding.grounded_extension)} grounded, {len(scaffolding.frontier)} on frontier",
            count=len(scaffolding.frontier),
        )
    )

    corpus, generation = generate_stage(
        corpus, scaffolding.frontier,
        proposers=proposers, injected=injected, cap=generation_cap,
        ledger=led, credit_floor=generation_credit_floor,
    )
    audit.append(StageAudit(stage="generate_stage",
        note=f"{len(generation.admitted)} admitted, {len(generation.discarded)} discarded",
        count=len(generation.admitted)))
    if generation.admitted:
        # belief-neutral: admitted claims carry no EFFECTIVE defeat edges — any edges the endogenous
        # operators attach are provisional (inert until their source is LICENSED), so recomputing only
        # EXTENDS the grounded extension with them (frontier + the pre-existing grounded set are
        # unchanged). verify_stage needs them in-extension to be able to license this cycle (e.g. an
        # exogenous PENDING-with-plan injection).
        scaffolding = represent(corpus)

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

    corpus, selection = select_stage(
        corpus, cost_model=cost_model or CostModel(), budget=budget,
        value_weights=value_weights, cost_weights=cost_weights,
        ledger=led, reserve_fraction=reserve_fraction, cell_cap_fraction=cell_cap_fraction,
    )
    n_selected = sum(1 for d in selection.decisions if d.selected)
    audit.append(StageAudit(stage="select_stage",
        note=f"{n_selected}/{selection.cardinality} selected", count=n_selected))

    selected_ids = frozenset(d.claim_id for d in selection.decisions if d.selected)
    locked_before = _locked_ids(corpus)
    corpus = commit(corpus, only=selected_ids)
    n_committed = len(_locked_ids(corpus) - locked_before)
    audit.append(StageAudit(stage="commit", note=f"{n_committed} claim(s) committed", count=n_committed))

    corpus, records = execute_ground(corpus, adapters, ctx, only=selected_ids)
    audit.append(StageAudit(stage="execute_ground", note=f"{len(records)} executed", count=len(records)))

    # scaffolding stays valid: canonicalize/safety/commit/execute change neither defeat_edges
    # nor claim ids, and generate only ADDS CONJECTURED claims with no defeat edges (the pure
    # operators are belief-neutral), so the grounded_extension of the executed claims is
    # unchanged since represent().
    executed_ids = {r.claim_id for r in records}
    corpus = verify_stage(corpus, scaffolding, records, oracles)
    n_licensed = sum(1 for c in corpus.claims if c.id in executed_ids and c.status == Status.LICENSED)
    audit.append(StageAudit(stage="verify_stage", note=f"{n_licensed} licensed", count=n_licensed))

    after = corpus.by_id()
    eig_by_id = {d.claim_id: d.value.eig for d in selection.decisions}
    outcomes = tuple(
        ExecutedOutcome(
            claim_id=cid,
            operator_id=operator_of(after[cid]),
            eig=eig_by_id.get(cid, 0.0),
            licensed=after[cid].status == Status.LICENSED,
            rejected=after[cid].status == Status.REJECTED,
        )
        for cid in sorted(executed_ids) if cid in after
    )
    led = update_ledger(led, outcomes)

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
        selection=selection,
        generation=generation,
        ledger=led,
    )
