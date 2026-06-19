"""Shared builders for shared-cause verify tests.

`licensable_corpus` returns (Corpus, CycleScaffolding, exec_records) for a single claim "c1"
that is agreed, SATISFIED, in the grounded extension, and carries provenance — so it licenses
under verify_stage with no extra arguments.

`with_dimnames` rewrites the exec record's evaluation.satisfaction.materialization to carry
the given dimnames_hash, enabling shared-cause cohort-overlap tests.
"""
from __future__ import annotations

from polymer_grammar import (
    FDRLedger,
    IdentityAdapter,
    MaterializationContext,
    ReferenceAdapter,
    Satisfaction,
    Status,
    StrengthVector,
)

from polymer_protocol.commit import commit
from polymer_protocol.corpus import Corpus, CycleScaffolding, ExecRecord
from polymer_protocol.execute import execute_ground

from tests.conftest import make_claim, make_plan

_ADAPTERS = (IdentityAdapter(), ReferenceAdapter(identity="reference"))
_CTX = MaterializationContext(id="M1", api_version="v1", data_version="d1")

# A StrengthVector with severity well above the CONFIRMATORY_SEVERITY_CEILING (0.2), so
# the cap test can assert severity <= 0.2 after capping.
_STRENGTH = StrengthVector(
    magnitude=0.8,
    certainty=0.8,
    evidence_against_null=0.9,
    severity=0.9,
    world_contact=0.8,
    explanatory_virtue=0.8,
)


def licensable_corpus() -> tuple[Corpus, CycleScaffolding, tuple[ExecRecord, ...]]:
    """Return (corpus, scaffolding, exec_records) for claim 'c1'.

    The claim executes to an agreed SATISFIED numeric result, is in the grounded extension,
    and carries provenance (commit sets search_cardinality). It carries a StrengthVector with
    severity=0.9 so the shared-cause severity cap test can assert severity <= 0.2 after capping.
    Ready to license via verify_stage.
    """
    empty_ledger = FDRLedger(target_fdr=0.05)
    c = make_claim("c1", status=Status.PENDING, plan=make_plan(0.01, 0.05), strength=_STRENGTH)
    corpus = commit(Corpus(claims=(c,), fdr_ledger=empty_ledger))
    corpus, records = execute_ground(corpus, _ADAPTERS, _CTX)
    scaffolding = CycleScaffolding(grounded_extension=("c1",))
    return corpus, scaffolding, records


def with_dimnames(
    corpus: Corpus,
    records: tuple[ExecRecord, ...],
    claim_id: str,
    dimnames_hash: str,
) -> tuple[Corpus, tuple[ExecRecord, ...]]:
    """Stamp dimnames_hash onto the exec record's satisfaction.materialization for claim_id.

    Returns (corpus_unchanged, updated_records). The corpus itself does not need to change —
    only the exec record's evaluation.satisfaction.materialization is updated so that
    _apply_shared_cause sees the test-cohort dimnames_hash when building licensing.satisfactions.
    """
    new_records = []
    for rec in records:
        if rec.claim_id != claim_id:
            new_records.append(rec)
            continue
        ev = rec.evaluation
        if ev.satisfaction is None:
            new_records.append(rec)
            continue
        new_mat = ev.satisfaction.materialization.model_copy(
            update={"dimnames_hash": dimnames_hash}
        )
        new_sat = Satisfaction(
            verdict=ev.satisfaction.verdict,
            materialization=new_mat,
        )
        new_ev = ev.model_copy(update={"satisfaction": new_sat})
        new_records.append(ExecRecord(claim_id=rec.claim_id, evaluation=new_ev))
    return corpus, tuple(new_records)
