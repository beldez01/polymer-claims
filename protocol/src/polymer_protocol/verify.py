"""VERIFY: decide each executed claim's status + assemble Licensing.

LICENSED <=> minted Satisfaction (agreement + SATISFIED) AND grounded-extension membership
AND provenance present (search_cardinality recorded — the selection-aware honesty gate).
REJECTED <=> refuted, or outside the grounded extension. Else PENDING (triage). This is the
Licensing-assembly + status-flip that Phase 8 deliberately left to the protocol. Spec §6.6.
"""
from __future__ import annotations

from polymer_grammar import (
    Claim,
    DataHandle,
    LicenseRoute,
    Licensing,
    PendingReason,
    RejectionReason,
    RivalSetClosure,
    Satisfaction,
    SatisfactionVerdict,
    SeverityProvenance,
    Status,
    StrengthVector,
    cap_severity_for_confirmatory,
    clears_mdl_bar,
    corpus_implied_schema,
    elond_decisions,
    independence_tier_of,
    is_representation_revision,
    max_shared_cause_overlap,
    mdl_delta,
    meets_meta_tier_bar,
    referenced_oracle_ids,
    resolve_test,
    severity_provenance_of,
)
from polymer_grammar.commitment import commitment_hash

from .adapter_registry import AdapterRegistry, pair_is_registry_independent
from .corpus import Corpus, CycleScaffolding, ExecRecord
from .earned_strength import earn_strength
from .oracle import OracleRegistry, cap_earned, oracle_cap

BH_Q = 0.10
_BH_EPS = 1e-9


def _build_earned(
    corpus: Corpus, exec_records: tuple[ExecRecord, ...]
) -> dict[str, StrengthVector]:
    """Earned strengths for executed None-strength + oracle_ref claims with a numeric, agreed,
    SATISFIED result (the spec's D2 scope). Empty for every other claim, which preserves today's
    behavior (None-strength -> exempt; asserted strength -> scored as before)."""
    by_id = corpus.by_id()
    earned: dict[str, StrengthVector] = {}
    for r in exec_records:
        c = by_id.get(r.claim_id)
        if c is None or c.strength is not None or c.evaluation_plan is None:
            continue
        if not referenced_oracle_ids(c.evaluation_plan):
            continue
        ev = r.evaluation
        # ev.satisfaction is non-None only for an agreed SATISFIED result (the air-gap mint).
        if ev.satisfaction is None or not ev.results:
            continue
        val = ev.results[0].terminal.value
        if not isinstance(val, (int, float)) or isinstance(val, bool):
            continue
        has_real_data = any(
            isinstance(i, DataHandle)
            for n in c.evaluation_plan.graph.nodes
            for i in n.inputs
        )
        earned[c.id] = earn_strength(
            float(val), c.evaluation_plan.criterion,
            has_real_data=has_real_data, agreement=ev.agreement,
        )
    return earned


def _permitted_by_bar(
    corpus: Corpus,
    exec_records: tuple[ExecRecord, ...],
    earned: dict[str, StrengthVector],
) -> set[str]:
    """Ids of executed claims permitted to license under the cardinality-scaled BH bar.
    M<=1 -> all permitted (identity). strength=None AND not earned -> exempt (always permitted).
    An earned claim is scored by its RAW earned evidence (the 2c reconciliation: data-evidence
    survives selection on its own merit; the oracle cap is applied to the recorded strength later)."""
    by_id = corpus.by_id()
    executed = [by_id[r.claim_id] for r in exec_records if r.claim_id in by_id]
    if not executed:
        return set()
    permitted = {c.id for c in executed if c.strength is None and c.id not in earned}  # exempt
    scored = []
    for c in executed:
        if c.id in earned:
            scored.append((1.0 - earned[c.id].evidence_against_null, c.id))
        elif c.strength is not None:
            scored.append((1.0 - c.strength.evidence_against_null, c.id))
    m = max(
        (c.provenance.search_cardinality for c in executed if c.provenance is not None),
        default=1,
    )
    # defense-in-depth: the BH denominator must cover EVERY scored claim, else a too-small
    # hand-stamped search_cardinality would let claims ranked beyond M pass on a >1 bar.
    m = max(m, len(scored))
    if m <= 1:
        return {c.id for c in executed}
    scored.sort()  # ascending pseudo-p, ties by id
    k_max = 0
    for k, (p, _) in enumerate(scored, start=1):
        if p <= (k / m) * BH_Q + _BH_EPS:
            k_max = k
    permitted.update(cid for _, cid in scored[:k_max])
    return permitted


def _with_status(claim: Claim, **update) -> Claim:
    """Apply a status/licensing/pending_reason update AND re-run Claim validators
    (model_copy alone skips validation)."""
    return Claim.model_validate(claim.model_copy(update=update).model_dump())


def _apply_shared_cause(
    claim: Claim,
    licensing: Licensing,
    strength: StrengthVector | None,
    strict: bool,
) -> tuple[Licensing, StrengthVector | None, bool]:
    """Annotate the license with its severity-provenance tier and (when CONFIRMATORY) cap the
    `severity` axis. Returns (licensing', strength', withhold). Inert when prior_cohorts is empty."""
    prior = claim.provenance.prior_cohorts if claim.provenance is not None else ()
    if not prior:
        return licensing, strength, False
    test_cohorts = tuple(
        s.materialization.dimnames_hash
        for s in licensing.satisfactions
        if s.materialization.dimnames_hash is not None
    )
    tier = severity_provenance_of(prior, test_cohorts)
    licensing = licensing.model_copy(update={"severity_provenance": tier})
    if tier == SeverityProvenance.CONFIRMATORY:
        if strict:
            return licensing, strength, True
        if strength is not None:
            strength = cap_severity_for_confirmatory(strength)
    return licensing, strength, False


def verify_stage(
    corpus: Corpus,
    scaffolding: CycleScaffolding,
    exec_records: tuple[ExecRecord, ...],
    oracles: OracleRegistry | None = None,
    adapter_registry: AdapterRegistry | None = None,
    evidence: dict[str, float] | None = None,
    replications: dict[str, tuple[Satisfaction, ...]] | None = None,
    strict_shared_cause: bool = False,
) -> Corpus:
    registry = oracles if oracles is not None else OracleRegistry()
    in_ext = set(scaffolding.grounded_extension)
    rec_by_id = {r.claim_id: r for r in exec_records}
    earned = _build_earned(corpus, exec_records)
    permitted = _permitted_by_bar(corpus, exec_records, earned)

    ev_map = evidence or {}
    led = corpus.fdr_ledger

    # --- Phase D: resolve pre-registered claims (match-gate + locked-alpha resolution) ---
    pending = {t.claim_id: t for t in led.tests if t.e_value is None and not t.retracted}
    by_id = {c.id: c for c in corpus.claims}
    altered_ids: set[str] = set()
    reg_decisions: dict[str, bool] = {}
    for rec in exec_records:
        cid = rec.claim_id
        if cid in pending and cid in ev_map:
            claim = by_id.get(cid)
            if claim is None or claim.evaluation_plan is None:
                continue
            if commitment_hash(claim) != pending[cid].commitment_hash:
                altered_ids.add(cid)                      # post-hoc change -> integrity violation
                continue
            led = resolve_test(led, cid, ev_map[cid])
            reg_decisions[cid] = led.tests[next(
                i for i in range(len(led.tests) - 1, -1, -1) if led.tests[i].claim_id == cid
            )].discovery

    # --- existing charge-at-verify path (unchanged) for NON-registered, NON-altered claims ---
    already_tested = {t.claim_id for t in led.tests if not t.retracted}
    executed_with_e = [
        (r.claim_id, ev_map[r.claim_id])
        for r in exec_records
        if r.claim_id in ev_map and r.claim_id not in already_tested and r.claim_id not in altered_ids
    ]
    new_ledger, e_decisions = elond_decisions(led, executed_with_e)

    def _e_ok(cid: str) -> bool:
        if cid in altered_ids:
            return False
        return (cid not in ev_map
                or reg_decisions.get(cid, e_decisions.get(cid, cid in corpus.fdr_ledger.discoveries)))

    def _recorded_strength(claim: Claim) -> StrengthVector | None:
        """Earned claims record cap_earned(earned, tier); everything else keeps oracle_cap."""
        if claim.id in earned:
            return cap_earned(earned[claim.id], claim, registry)
        return oracle_cap(claim, registry)

    new_claims = []
    for c in corpus.claims:
        if c.id in altered_ids:
            new_claims.append(_with_status(
                c, status=Status.REJECTED, pending_reason=None,
                rejection_reason=RejectionReason.HYPOTHESIS_ALTERED,
            ))
            continue
        rec = rec_by_id.get(c.id)
        if rec is None:
            new_claims.append(c)
            continue
        ev = rec.evaluation
        # ev.results is non-empty in the normal pipeline (verify requires >=2 adapters);
        # the truthiness guard is defensive.
        agreed_refuted = (
            ev.agreement
            and ev.results
            and ev.results[0].verdict == SatisfactionVerdict.REFUTED
        )
        # provenance is non-None for anything that passed execute_ground (_is_executable
        # requires the lock); the guard is defensive for direct callers.
        if (ev.satisfaction is not None and c.id in in_ext
                and c.provenance is not None and c.id in permitted
                and _e_ok(c.id)):
            if adapter_registry is not None and not adapter_registry.is_empty:
                identities = tuple(r.adapter_identity for r in ev.results)
                if not pair_is_registry_independent(adapter_registry, identities):
                    new_claims.append(_with_status(
                        c,
                        status=Status.PENDING,
                        pending_reason=PendingReason.ADAPTER_NOT_INDEPENDENT,
                        licensing=None,
                    ))
                    continue
            extra_sats = (replications or {}).get(c.id, ())
            sats = (ev.satisfaction, *extra_sats)
            licensing = Licensing(
                route=LicenseRoute.SEVERE_TEST,
                satisfactions=sats,
                rival_set_closure=RivalSetClosure.OPEN_ACKNOWLEDGED,
                independence_tier=independence_tier_of(sats),
                shared_cause_overlap=max_shared_cause_overlap(sats),
            )
            recorded = _recorded_strength(c)
            licensing, recorded, withhold = _apply_shared_cause(
                c, licensing, recorded, strict_shared_cause
            )
            if withhold:
                new_claims.append(_with_status(
                    c, status=Status.PENDING,
                    pending_reason=PendingReason.SHARED_CAUSE_CONFIRMATORY, licensing=None,
                ))
                continue
            if is_representation_revision(c):
                # meta-tier gate: a representation-revision cannot ride the ordinary single-severe-test
                # path. Try the MDL route first — a revision that COMPRESSES the object corpus earns its
                # license from the corpus's own compressibility (LicenseRoute.MDL_GATE meets the bar).
                object_claims = tuple(
                    x for x in corpus.claims if not is_representation_revision(x)
                )
                schema = corpus_implied_schema(object_claims)
                delta = mdl_delta(object_claims, schema, c.representation_revision)
                if clears_mdl_bar(delta):
                    mdl_licensing = Licensing(
                        route=LicenseRoute.MDL_GATE,
                        satisfactions=(ev.satisfaction,),
                        # the compression evidence (mdl_delta) stands in for rival enumeration —
                        # OPEN_ACKNOWLEDGED keeps the MDL route self-supporting (no rival list required).
                        rival_set_closure=RivalSetClosure.OPEN_ACKNOWLEDGED,
                    )
                    # Stamp the shared-cause tier computed by _apply_shared_cause onto the MDL
                    # licensing so the annotation is not silently dropped (Decision A1: license still
                    # mints, honestly annotated + capped). `licensing` and `recorded` are already
                    # post-_apply_shared_cause (computed before the is_representation_revision block).
                    mdl_licensing = mdl_licensing.model_copy(
                        update={"severity_provenance": licensing.severity_provenance}
                    )
                    new_claims.append(
                        _with_status(
                            c,
                            status=Status.LICENSED,
                            licensing=mdl_licensing,
                            pending_reason=None,
                            strength=recorded,  # capped by _apply_shared_cause when CONFIRMATORY
                        )
                    )
                    continue
                if not meets_meta_tier_bar(licensing):
                    # Non-compressing AND not replication-grade — hold PENDING, exactly as today.
                    new_claims.append(c)
                    continue
            new_claims.append(
                _with_status(
                    c,
                    status=Status.LICENSED,
                    licensing=licensing,
                    pending_reason=None,
                    strength=recorded,  # earned -> cap_earned; else oracle_cap (fallback: empty registry -> unresolved refs UNVALIDATED)
                )
            )
        # Refutation is terminal and takes precedence over the grounded-out (extension boundary) case.
        elif agreed_refuted:
            new_claims.append(_with_status(
                c, status=Status.REJECTED, licensing=None, pending_reason=None,
                rejection_reason=RejectionReason.REFUTED,
            ))
        elif c.id not in in_ext:
            new_claims.append(_with_status(
                c, status=Status.REJECTED, licensing=None, pending_reason=None,
                rejection_reason=RejectionReason.DEFEAT_GROUNDED_OUT,
            ))
        else:
            new_claims.append(c)  # stays PENDING — already carries a valid pending_reason
    return corpus.model_copy(update={"claims": tuple(new_claims), "fdr_ledger": new_ledger})
