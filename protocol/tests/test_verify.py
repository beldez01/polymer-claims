from polymer_grammar import (
    FDRLedger,
    LicenseRoute,
    SatisfactionVerdict,
    Status,
    StrengthVector,
)

from polymer_protocol.commit import commit
from polymer_protocol.corpus import Corpus, CycleScaffolding
from polymer_protocol.cost import CostModel, CostWeights
from polymer_protocol.execute import execute_ground
from polymer_protocol.represent import represent
from polymer_protocol.select import ValueWeights, select_stage
from polymer_protocol.verify import verify_stage
from tests.conftest import make_claim, make_plan


def _run_to_records(claim, empty_ledger, ctx, adapters):
    corpus = commit(Corpus(claims=(claim,), fdr_ledger=empty_ledger))
    return execute_ground(corpus, adapters, ctx)


def test_satisfied_in_extension_becomes_licensed(empty_ledger, ctx, adapters):
    c = make_claim("a", status=Status.PENDING, plan=make_plan(0.01, 0.05))
    corpus, records = _run_to_records(c, empty_ledger, ctx, adapters)
    scaffolding = CycleScaffolding(grounded_extension=("a",))
    out = verify_stage(corpus, scaffolding, records)
    graded = out.by_id()["a"]
    assert graded.status == Status.LICENSED
    assert graded.pending_reason is None
    assert graded.licensing is not None
    assert graded.licensing.route == LicenseRoute.SEVERE_TEST
    assert graded.licensing.satisfactions[0].verdict == SatisfactionVerdict.SATISFIED


def test_satisfied_but_outside_extension_is_rejected(empty_ledger, ctx, adapters):
    c = make_claim("a", status=Status.PENDING, plan=make_plan(0.01, 0.05))
    corpus, records = _run_to_records(c, empty_ledger, ctx, adapters)
    scaffolding = CycleScaffolding(grounded_extension=())  # a is OUT
    out = verify_stage(corpus, scaffolding, records)
    assert out.by_id()["a"].status == Status.REJECTED


def test_refuted_claim_is_rejected(empty_ledger, ctx, adapters):
    c = make_claim("a", status=Status.PENDING, plan=make_plan(0.99, 0.05))
    corpus, records = _run_to_records(c, empty_ledger, ctx, adapters)
    scaffolding = CycleScaffolding(grounded_extension=("a",))
    out = verify_stage(corpus, scaffolding, records)
    graded = out.by_id()["a"]
    assert graded.status == Status.REJECTED
    assert graded.licensing is None


def test_two_impl_disagreement_stays_pending(empty_ledger, ctx):
    from polymer_grammar import IdentityAdapter, ReferenceAdapter

    c = make_claim("a", status=Status.PENDING, plan=make_plan(0.01, 0.05))
    corpus = commit(Corpus(claims=(c,), fdr_ledger=empty_ledger))
    # perturbed reference adapter -> terminal values disagree -> no mint, disagreement set
    disagreeing = (IdentityAdapter(), ReferenceAdapter(identity="reference", perturb=10.0))
    corpus, records = execute_ground(corpus, disagreeing, ctx)
    assert records[0].evaluation.agreement is False
    scaffolding = CycleScaffolding(grounded_extension=("a",))
    out = verify_stage(corpus, scaffolding, records)
    assert out.by_id()["a"].status == Status.PENDING


def test_claim_without_record_is_untouched(empty_ledger, ctx, adapters):
    executed = make_claim("a", status=Status.PENDING, plan=make_plan(0.01, 0.05))
    bystander = make_claim("b", status=Status.CONJECTURED)
    corpus = commit(Corpus(claims=(executed, bystander), fdr_ledger=empty_ledger))
    corpus, records = execute_ground(corpus, adapters, ctx)
    scaffolding = CycleScaffolding(grounded_extension=("a", "b"))
    out = verify_stage(corpus, scaffolding, records)
    assert out.by_id()["b"].status == Status.CONJECTURED


def test_satisfied_in_ext_but_no_provenance_stays_pending(empty_ledger, ctx):
    # A minted satisfaction without provenance must stay PENDING (selection-aware honesty gate).
    from polymer_grammar import (
        EvaluationResult, ExecValue, Satisfaction, SatisfactionVerdict, VerifiedEvaluation,
    )
    from polymer_protocol.corpus import ExecRecord

    c = make_claim("a", status=Status.PENDING, plan=make_plan(0.01, 0.05))
    assert c.provenance is None  # not committed -> no provenance
    sat = Satisfaction(verdict=SatisfactionVerdict.SATISFIED, materialization=ctx)
    result = EvaluationResult(
        verdict=SatisfactionVerdict.SATISFIED, terminal=ExecValue(value=0.01),
        nodes=(), adapter_identity="identity", status="complete",
    )
    ev = VerifiedEvaluation(results=(result, result), agreement=True, satisfaction=sat)
    corpus = Corpus(claims=(c,), fdr_ledger=empty_ledger)
    scaffolding = CycleScaffolding(grounded_extension=("a",))
    out = verify_stage(corpus, scaffolding, (ExecRecord(claim_id="a", evaluation=ev),))
    assert out.by_id()["a"].status == Status.PENDING


def test_agreed_undetermined_in_ext_stays_pending(empty_ledger, ctx):
    # Agreed UNDETERMINED (e.g. a data handle returned None) is neither licensed nor rejected.
    from polymer_grammar import EvaluationResult, ExecValue, SatisfactionVerdict, VerifiedEvaluation
    from polymer_protocol.corpus import ExecRecord

    c = make_claim("a", status=Status.PENDING, plan=make_plan(0.01, 0.05))
    corpus = commit(Corpus(claims=(c,), fdr_ledger=empty_ledger))
    r1 = EvaluationResult(verdict=SatisfactionVerdict.UNDETERMINED, terminal=ExecValue(value=None),
                          nodes=(), adapter_identity="identity", status="error")
    r2 = EvaluationResult(verdict=SatisfactionVerdict.UNDETERMINED, terminal=ExecValue(value=None),
                          nodes=(), adapter_identity="reference", status="error")
    ev = VerifiedEvaluation(results=(r1, r2), agreement=True, satisfaction=None)
    scaffolding = CycleScaffolding(grounded_extension=("a",))
    out = verify_stage(corpus, scaffolding, (ExecRecord(claim_id="a", evaluation=ev),))
    assert out.by_id()["a"].status == Status.PENDING


def test_oracle_grounded_license_caps_strength(empty_ledger, ctx, adapters):
    from polymer_grammar import OracleDossier, StrengthVector, ValidationTier
    from polymer_protocol import OracleRegistry

    sv = StrengthVector(magnitude=0.9, certainty=0.1, evidence_against_null=0.9,
                        severity=0.9, world_contact=0.9, explanatory_virtue=0.9)
    c = make_claim("a", status=Status.PENDING, plan=make_plan(0.01, 0.05, oracle_ref="api"), strength=sv)
    corpus = commit(Corpus(claims=(c,), fdr_ledger=empty_ledger))
    corpus, records = execute_ground(corpus, adapters, ctx)
    scaffolding = CycleScaffolding(grounded_extension=("a",))
    reg = OracleRegistry(dossiers=(OracleDossier(oracle_id="api", validation_tier=ValidationTier.INDIRECT),))
    out = verify_stage(corpus, scaffolding, records, reg)
    graded = out.by_id()["a"]
    assert graded.status == Status.LICENSED
    assert graded.strength.magnitude == 0.4         # capped by INDIRECT
    assert graded.strength.severity == 0.9          # theory axis untouched


def test_builtin_only_claim_uncapped_without_registry(empty_ledger, ctx, adapters):
    # No oracle_ref -> no oracle dependency -> strength untouched even with no registry (real back-compat).
    from polymer_grammar import StrengthVector
    sv = StrengthVector(magnitude=0.9, certainty=0.1, evidence_against_null=0.9,
                        severity=0.9, world_contact=0.9, explanatory_virtue=0.9)
    c = make_claim("a", status=Status.PENDING, plan=make_plan(0.01, 0.05), strength=sv)  # no oracle_ref
    corpus = commit(Corpus(claims=(c,), fdr_ledger=empty_ledger))
    corpus, records = execute_ground(corpus, adapters, ctx)
    scaffolding = CycleScaffolding(grounded_extension=("a",))
    out = verify_stage(corpus, scaffolding, records)  # no oracles arg
    assert out.by_id()["a"].strength == sv  # unchanged — no oracle dependency


def test_oracle_grounded_claim_capped_without_registry(empty_ledger, ctx, adapters):
    # An oracle_ref with no dossier (no registry) is UNVALIDATED -> empirical strength caps to 0.
    # The guarantee holds whether or not a registry was passed.
    from polymer_grammar import StrengthVector
    sv = StrengthVector(magnitude=0.9, certainty=0.1, evidence_against_null=0.9,
                        severity=0.9, world_contact=0.9, explanatory_virtue=0.9)
    c = make_claim("a", status=Status.PENDING, plan=make_plan(0.01, 0.05, oracle_ref="api"), strength=sv)
    corpus = commit(Corpus(claims=(c,), fdr_ledger=empty_ledger))
    corpus, records = execute_ground(corpus, adapters, ctx)
    scaffolding = CycleScaffolding(grounded_extension=("a",))
    out = verify_stage(corpus, scaffolding, records)  # no oracles -> empty -> unresolved -> UNVALIDATED
    graded = out.by_id()["a"]
    assert graded.status == Status.LICENSED
    assert graded.strength.magnitude == 0.0   # capped: unvalidated oracle
    assert graded.strength.severity == 0.9    # theory axis untouched


def test_gold_oracle_with_registry_leaves_strength_unchanged(empty_ledger, ctx, adapters):
    from polymer_grammar import OracleDossier, StrengthVector, ValidationTier
    from polymer_protocol import OracleRegistry

    sv = StrengthVector(magnitude=0.9, certainty=0.1, evidence_against_null=0.9,
                        severity=0.9, world_contact=0.9, explanatory_virtue=0.9)
    c = make_claim("a", status=Status.PENDING, plan=make_plan(0.01, 0.05, oracle_ref="api"), strength=sv)
    corpus = commit(Corpus(claims=(c,), fdr_ledger=empty_ledger))
    corpus, records = execute_ground(corpus, adapters, ctx)
    scaffolding = CycleScaffolding(grounded_extension=("a",))
    reg = OracleRegistry(dossiers=(OracleDossier(oracle_id="api", validation_tier=ValidationTier.GOLD),))
    out = verify_stage(corpus, scaffolding, records, reg)
    assert out.by_id()["a"].status == Status.LICENSED
    assert out.by_id()["a"].strength == sv  # GOLD ceiling is all-1.0 -> no cap, vector survives round-trip


def test_out_of_domain_oracle_caps_through_verify_stage(empty_ledger, ctx, adapters):
    from polymer_grammar import (
        ApplicabilityDomain, GenomicRegion, OracleDossier, StrengthVector, ValidationTier,
    )
    from polymer_protocol import OracleRegistry

    sv = StrengthVector(magnitude=0.9, certainty=0.1, evidence_against_null=0.9,
                        severity=0.9, world_contact=0.9, explanatory_virtue=0.9)
    region = GenomicRegion(id="r1", display="d", assembly="GRCh38", chrom="chr1", start=1, end=9)
    c = make_claim("a", status=Status.PENDING, plan=make_plan(0.01, 0.05, oracle_ref="api"),
                   strength=sv, subject=region)
    corpus = commit(Corpus(claims=(c,), fdr_ledger=empty_ledger))
    corpus, records = execute_ground(corpus, adapters, ctx)
    scaffolding = CycleScaffolding(grounded_extension=("a",))
    # oracle qualified only for variant_vrs; our subject is genomic_region -> out of domain -> UNVALIDATED
    reg = OracleRegistry(dossiers=(OracleDossier(
        oracle_id="api", validation_tier=ValidationTier.GOLD,
        applicability_domain=ApplicabilityDomain(subject_kinds=("variant_vrs",)),
    ),))
    out = verify_stage(corpus, scaffolding, records, reg)
    assert out.by_id()["a"].strength.magnitude == 0.0   # out-of-domain -> capped
    assert out.by_id()["a"].strength.severity == 0.9    # theory axis untouched


def _sv_bar(ean):
    return StrengthVector(magnitude=0.5, certainty=0.8, evidence_against_null=ean,
                          severity=0.5, world_contact=0.5, explanatory_virtue=0.5)


def _verify_through_select(claims, adapters, ctx):
    corp = Corpus(claims=tuple(claims), fdr_ledger=FDRLedger(target_fdr=0.05))
    scaffolding = represent(corp)
    corp, rec = select_stage(corp, budget=None, cost_model=CostModel(),
                             value_weights=ValueWeights(), cost_weights=CostWeights())
    corp = commit(corp, only=frozenset(d.claim_id for d in rec.decisions if d.selected))
    corp, records = execute_ground(corp, adapters, ctx)
    return verify_stage(corp, scaffolding, records)


def test_bar_is_identity_at_cardinality_one(ctx, adapters):
    # single strong claim, M=1 -> licenses regardless of evidence value
    c = make_claim("a", status=Status.PENDING, plan=make_plan(0.01, 0.05), strength=_sv_bar(0.2))
    out = _verify_through_select([c], adapters, ctx)
    assert out.by_id()["a"].status == Status.LICENSED


def test_none_strength_claim_is_exempt_in_a_pool(ctx, adapters):
    # two None-strength satisfied claims, M=2 -> both still license (exempt)
    a = make_claim("a", status=Status.PENDING, plan=make_plan(0.01, 0.05))
    b = make_claim("b", status=Status.PENDING, plan=make_plan(0.02, 0.05))
    out = _verify_through_select([a, b], adapters, ctx)
    assert out.by_id()["a"].status == Status.LICENSED
    assert out.by_id()["b"].status == Status.LICENSED


def test_weak_evidence_claim_fails_bar_in_a_large_pool(ctx, adapters):
    # weak claim competes in a pool of 5 -> BH bar rejects it.
    # p_weak = 1 - 0.10 = 0.90; BH crit (1/5)*0.10 = 0.02; 0.90 > 0.02 -> fail.
    weak = make_claim("weak", status=Status.PENDING, plan=make_plan(0.01, 0.05), strength=_sv_bar(0.10))
    others = [make_claim(f"o{i}", status=Status.PENDING, plan=make_plan(0.01 + i * 0.001, 0.5))
              for i in range(4)]
    out = _verify_through_select([weak, *others], adapters, ctx)
    assert out.by_id()["weak"].status == Status.PENDING  # non-exempt, fails bar -> stays PENDING


def test_strong_evidence_claim_passes_bar_in_a_pool(ctx, adapters):
    # strong claim in a pool of 2 -> p = 0.05; BH crit (1/2)*0.10 = 0.05; passes.
    strong = make_claim("s", status=Status.PENDING, plan=make_plan(0.01, 0.05), strength=_sv_bar(0.95))
    other = make_claim("o", status=Status.PENDING, plan=make_plan(0.02, 0.05))
    out = _verify_through_select([strong, other], adapters, ctx)
    assert out.by_id()["s"].status == Status.LICENSED
    assert out.by_id()["o"].status == Status.LICENSED


def test_earned_strength_licenses_and_is_tier_capped(empty_ledger, ctx, adapters):
    # None-strength + oracle_ref claim that clears the threshold strongly -> earns strength,
    # licenses (single claim, M small), and the recorded goodness axes are tier-capped (BENCHMARKED).
    from polymer_grammar import OracleDossier, ValidationTier
    from polymer_protocol import OracleRegistry
    # make_plan default comparator LT: value 0.01 clears threshold 0.05 by 0.04/0.05 = 0.8 -> strong.
    c = make_claim("a", status=Status.PENDING, plan=make_plan(0.01, 0.05, oracle_ref="api"))
    assert c.strength is None
    corpus = commit(Corpus(claims=(c,), fdr_ledger=empty_ledger))
    corpus, records = execute_ground(corpus, adapters, ctx)
    scaffolding = CycleScaffolding(grounded_extension=("a",))
    reg = OracleRegistry(dossiers=(OracleDossier(oracle_id="api",
                                                 validation_tier=ValidationTier.BENCHMARKED),))
    out = verify_stage(corpus, scaffolding, records, reg)
    graded = out.by_id()["a"]
    assert graded.status == Status.LICENSED
    assert graded.strength is not None                       # earned (was None)
    assert graded.strength.evidence_against_null <= 0.6      # capped by BENCHMARKED
    assert graded.strength.magnitude <= 0.6
    assert graded.strength.severity == 0.7                   # theory axis uncapped


def test_earned_path_leaves_const_none_strength_claim_exempt(empty_ledger, ctx, adapters):
    # No oracle_ref -> NOT earned -> stays exempt, strength stays None (byte-unchanged behavior).
    c = make_claim("a", status=Status.PENDING, plan=make_plan(0.01, 0.05))
    corpus = commit(Corpus(claims=(c,), fdr_ledger=empty_ledger))
    corpus, records = execute_ground(corpus, adapters, ctx)
    scaffolding = CycleScaffolding(grounded_extension=("a",))
    out = verify_stage(corpus, scaffolding, records)
    graded = out.by_id()["a"]
    assert graded.status == Status.LICENSED
    assert graded.strength is None


def test_earned_evidence_prices_the_search(ctx, adapters):
    # Reconciliation: among competing None-strength + oracle_ref claims, the strongly-supported
    # one licenses while a thin-margin rival is held PENDING by the selective-inference bar.
    # strong: LT value 0.01 vs threshold 0.05 -> rel 0.8 -> evidence ~1.0
    # thin:   LT value 0.049 vs threshold 0.05 -> rel 0.02 -> evidence ~0.15
    strong = make_claim("strong", status=Status.PENDING,
                        plan=make_plan(0.01, 0.05, oracle_ref="api"))
    thin = make_claim("thin", status=Status.PENDING,
                      plan=make_plan(0.049, 0.05, oracle_ref="api"))
    out = _verify_through_select([strong, thin], adapters, ctx)
    assert out.by_id()["strong"].status == Status.LICENSED
    assert out.by_id()["thin"].status == Status.PENDING
