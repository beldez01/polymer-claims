"""Pre-register + license the expression-floor spine through run_cycle. Mirrors pharmaco_populate.py:
preregister/check_controls/_terminal_node are copied verbatim (generic over claims); only the
adapters/registry/oracle/evidence and the claim-construction are swapped for the expression-floor
spine. Umbrella/impure ([spine] extra); NOT re-exported from __init__."""
from __future__ import annotations

from polymer_grammar import (
    Claim,
    MaterializationContext,
    Status,
    commitment_hash,
    register_test,
)
from polymer_protocol import Corpus, run_cycle

from .capabilities import CAPABILITY_CELLS
from .contracts import load_contract
from .evidence import _terminal_node
from .expression_floor_adapters import (
    ExpressionFloorHLAdapter,
    ExpressionFloorMeanAdapter,
    expression_floor_claim,
    expression_floor_oracle_registry,
    expression_floor_registry,
)
from .expression_floor_evidence import FLOOR, expression_floor_evalue

__all__ = [
    "ControlCheckFailed",
    "check_controls",
    "license_batch",
    "preregister",
    "propose_spine_claims",
]


def preregister(corpus: Corpus, claims: list[Claim]) -> Corpus:
    """Admit the proposed claims into the corpus (PENDING — no standing yet) and lock an e-LOND
    slot per claim (register_test/commitment_hash) BEFORE any e-value exists. Standing (LICENSED)
    is only conferred later by Task 6's run_cycle.

    Registration order is the LIST order of `claims` — i.e. STRENGTH-rank order, because
    propose_claims builds the list straight from the mechanism scan's DataFrame (sorted by level
    desc, |r_adj| desc). This is the intended use of e-LOND's front-loaded γ_t weights: test the
    most-promising hypotheses first so the strongest signals get the earliest (lowest) discovery
    bars. FDR control is order-INDEPENDENT (the γ_j sum to 1 regardless of order); only power
    changes. NOT protocol's register_hypotheses, which re-sorts claim_ids ALPHABETICALLY and would
    bury a strong-but-late-alphabet signal (e.g. MTAP→Palbociclib) behind a ~10^6 threshold. The
    locked α is honored at verify: pre-registered claims resolve via resolve_test (verify.py
    Phase D) against the α locked HERE, never re-sorted by elond_decisions."""
    admitted = corpus.model_copy(update={"claims": corpus.claims + tuple(claims)})
    ledger = admitted.fdr_ledger
    pending = {t.claim_id for t in ledger.tests if t.e_value is None and not t.retracted}
    for c in claims:
        if c.evaluation_plan is None or c.id in pending:
            continue                              # planless / already-registered -> no double-charge
        ledger = register_test(ledger, c.id, commitment_hash(c))
        pending.add(c.id)
    if ledger == admitted.fdr_ledger:
        return admitted
    return admitted.model_copy(update={"fdr_ledger": ledger})


def propose_spine_claims(ref: str, *, floor: float = FLOOR) -> list[Claim]:
    """floor-RUNX1T1 (the fusion-driven signal) + floor-ACTB (the housekeeping control)."""
    return [
        expression_floor_claim("floor-RUNX1T1", ref=ref, gene="RUNX1T1", floor=floor, tissue="AML",
                               search_cardinality=1),
        expression_floor_claim("floor-ACTB", ref=ref, gene="ACTB", floor=floor, tissue="AML",
                               search_cardinality=1),
    ]


def propose_cbf_family_claims(ref: str, *, floor: float = FLOOR) -> list[Claim]:
    """The CBF-AML 2x2 fusion-marker family + ACTB control (all against a 3-valued Sample_Group
    ∈ {t821, inv16, other}). A/B are over-expression floors (RUNX1T1 in t(8;21), MN1 in inv(16));
    C/D are the cross-fusion specificity claims (comparator = the OTHER fusion)."""
    def _c(cid, gene, la, lb):
        return expression_floor_claim(cid, ref=ref, gene=gene, floor=floor, tissue="AML",
                                      level_a=la, level_b=lb, search_cardinality=1)
    return [
        _c("floor-RUNX1T1-t821-vs-other", "RUNX1T1", "t821", "other"),   # A
        _c("floor-MN1-inv16-vs-other", "MN1", "inv16", "other"),         # B
        _c("floor-RUNX1T1-t821-vs-inv16", "RUNX1T1", "t821", "inv16"),   # C specificity
        _c("floor-MN1-inv16-vs-t821", "MN1", "inv16", "t821"),           # D specificity
        _c("floor-ACTB-inv16-vs-other", "ACTB", "inv16", "other"),       # control (must NOT license)
    ]


def _evidence_for(claims: list[Claim]) -> dict[str, float]:
    """Per-claim e-value from the fusion+/fusion- discrimination gap (expression_floor_evalue).
    Skips claims whose contract read fails."""
    out: dict[str, float] = {}
    for c in claims:
        node = _terminal_node(c)
        if node is None:
            continue
        try:
            out[c.id] = expression_floor_evalue(node)
        except (FileNotFoundError, KeyError, ValueError):
            continue
    return out


def license_batch(
    corpus: Corpus, claims: list[Claim], *, ref: str,
    shared_cause_factors: tuple[str, ...] = ("tcga-laml",),
) -> Corpus:
    """Confer standing on a pre-registered batch: run the two independent legs (mean / Hodges-
    Lehmann) + registry + oracle + per-claim e-values through run_cycle against cohort `ref`. Every
    materialization carries `shared_cause_factors`, so any later cross-cohort replication is gated
    by §E (cohorts_error_independent) rather than silently minting REPLICATED. A single-cohort
    license resolves to IndependenceTier.REPRODUCED; a claim whose e-value never clears the e-LOND
    discovery bar stays PENDING (residue, not rejected).

    UNLIKE pharmaco_populate.license_batch, this runs one run_cycle PER CLAIM (not one shared call
    over the whole batch), sharing only the corpus/fdr_ledger across iterations. Reason: the
    expression-floor capability's criterion is `criterion_target="reference_leaf"` (the floor is a
    per-claim QuantityLeaf, not a literal `criterion.threshold`) — protocol's earned_strength.
    _rel_margin (verify.py's cardinality-scaled selective-inference bar) returns a hard 0.0 margin
    whenever `criterion.threshold is None`, by construction (see its docstring). Pharmaco's claims
    use a literal Comparator.GT threshold, so that bar legitimately discriminates strong-vs-weak
    signal there. Here it CANNOT discriminate (every reference_leaf claim earns evidence_against_
    null=0.0) — worse, run_cycle's own select_stage stamps EVERY pending candidate's provenance.
    search_cardinality to the batch size, so with >=2 claims pending together the BH bar (m=2) ties
    both at pseudo-p=1.0 and permits NEITHER, regardless of the real (e-LOND) discrimination e-value.
    Isolating each claim to its own run_cycle call keeps that bar's cardinality at m=1 (all-permit,
    verify.py `_permitted_by_bar`), leaving the actual, pre-registered per-claim e-value — the real
    discrimination signal computed by `_evidence_for`/expression_floor_evalue — as the sole gate.
    Verified against the real run_cycle (not stubbed): see tests/spine/test_expression_floor_license.py."""
    base = MaterializationContext(id="M", api_version="v1", data_version="d1")
    try:
        dimnames_hash = load_contract(ref).dimnames_hash
    except FileNotFoundError:
        dimnames_hash = None
    factors = tuple(shared_cause_factors)
    ev_map = _evidence_for(claims)
    batch_ids = {c.id for c in claims}
    acc = corpus
    for c in claims:
        if _terminal_node(c) is None:
            continue
        # Isolate this claim: drop its BATCH siblings (still PENDING, so they'd otherwise inflate
        # select_stage's candidate count) from the corpus passed into this iteration's run_cycle;
        # anything outside `claims` (unrelated pre-existing corpus claims) is left untouched.
        solo_claims = tuple(x for x in acc.claims if x.id == c.id or x.id not in batch_ids)
        solo = acc.model_copy(update={"claims": solo_claims})
        mctx = MaterializationContext(
            id=base.id, api_version=base.api_version, data_version=base.data_version,
            dimnames_hash=dimnames_hash, shared_cause_factors=factors)
        result = run_cycle(
            solo, (ExpressionFloorMeanAdapter(), ExpressionFloorHLAdapter()), base,
            adapter_registry=expression_floor_registry(),
            oracles=expression_floor_oracle_registry(),
            materializations={c.id: mctx},
            evidence={c.id: ev_map[c.id]} if c.id in ev_map else None,
            capability_registry=CAPABILITY_CELLS)
        updated = result.corpus.by_id().get(c.id, c)
        acc_claims = tuple(updated if x.id == c.id else x for x in acc.claims)
        acc = acc.model_copy(update={"claims": acc_claims, "fdr_ledger": result.corpus.fdr_ledger})
    return acc


def license_replicated(
    corpus: Corpus, claims: list[Claim], *, ref_a: str, ref_b: str,
    factors_a: tuple[str, ...], factors_b: tuple[str, ...],
) -> Corpus:
    """§2E two-cohort REPLICATED license: cohort A (`ref_a`) + an error-independent cohort B (`ref_b`).
    `build_expr_replication_inputs` computes the product e1*e2 (folded into the SINGLE pre-registered
    e-LOND slot) and cohort-B's Satisfaction (which promotes the tier to REPLICATED via the extra
    distinct-`dimnames_hash` cohort). `factors_a`/`factors_b` MUST be non-empty (empty ⇒ the §E gate is
    inert and over-credits) and should be disjoint (overlap ⇒ silent REPRODUCED cap). Reuses the 2d-ii
    per-claim isolation. A claim whose cohort B does not air-gap falls back to its cohort-A REPRODUCED
    license (its e1 is retained by the builder)."""
    from .expression_floor_replication import build_expr_replication_inputs

    if not factors_a or not factors_b:
        raise ValueError("both cohorts need non-empty shared_cause_factors")
    base = MaterializationContext(id="M", api_version="v1", data_version="d1")
    ri = build_expr_replication_inputs(
        corpus, base,
        bindings={c.id: ref_b for c in claims if _terminal_node(c) is not None},
        factors_a=factors_a, factors_b=factors_b)
    try:
        dimnames_a = load_contract(ref_a).dimnames_hash
    except FileNotFoundError:
        dimnames_a = None
    batch_ids = {c.id for c in claims}
    acc = corpus
    for c in claims:
        if _terminal_node(c) is None:
            continue
        solo_claims = tuple(x for x in acc.claims if x.id == c.id or x.id not in batch_ids)
        solo = acc.model_copy(update={"claims": solo_claims})
        mctx = MaterializationContext(
            id=base.id, api_version=base.api_version, data_version=base.data_version,
            dimnames_hash=dimnames_a, shared_cause_factors=factors_a)
        result = run_cycle(
            solo, (ExpressionFloorMeanAdapter(), ExpressionFloorHLAdapter()), base,
            adapter_registry=expression_floor_registry(),
            oracles=expression_floor_oracle_registry(),
            materializations={c.id: mctx},
            evidence={c.id: ri.evidence[c.id]} if c.id in ri.evidence else None,
            replications={c.id: ri.replications[c.id]} if c.id in ri.replications else None,
            capability_registry=CAPABILITY_CELLS)
        updated = result.corpus.by_id().get(c.id, c)
        acc_claims = tuple(updated if x.id == c.id else x for x in acc.claims)
        acc = acc.model_copy(update={"claims": acc_claims, "fdr_ledger": result.corpus.fdr_ledger})
    return acc


class ControlCheckFailed(RuntimeError):
    """The publish guard: a control behaved wrong (positive did not license, or negative did)."""


def check_controls(
    corpus: Corpus, *,
    positive: str = "floor-RUNX1T1", negative: str = "floor-ACTB",
) -> dict:
    """A read-only instrument, not a gate: reports whether the known-mechanism positive control
    licensed and the known-null negative control did not — never mutates any claim's status.
    The negative condition is "not LICENSED" (robust to the null landing PENDING as a residue OR
    terminal-REJECTED via agreed refutation — either way it is not licensed)."""
    by_id = corpus.by_id()
    pos = by_id.get(positive)
    neg = by_id.get(negative)
    positive_licensed = pos is not None and pos.status == Status.LICENSED
    negative_licensed = neg is not None and neg.status == Status.LICENSED
    return {
        "ok": positive_licensed and not negative_licensed,
        "positive_licensed": positive_licensed,
        "negative_licensed": negative_licensed,
    }
