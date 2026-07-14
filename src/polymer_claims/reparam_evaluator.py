"""The re-parameterization evaluator (B3) — reason about measurement-scale artifacts on REFUTED claims.

A claim REJECTED with ``RejectionReason.REFUTED`` may be a genuine forbidden-region negative OR an
artifact of being tested over the wrong measurement space (e.g. MGMT->TMZ refuted over gene-body
methylation, when the mechanism is promoter-localized). This evaluator, on such a claim:

  1. asks an untrusted LLM (hybrid generator) which measurement modality is apt, from the claim's
     asserted mechanism, and GROUNDS that proposal against the B1 measurement-space registry — it can
     only surface spaces that actually have data (never fabricates);
  2. DECLARE-AND-CHARGE: pre-registers ALL K apt-available alternate e-LOND slots upfront
     (non-adaptive) BEFORE any is tested;
  3. re-tests each alternate over its new space via the UNCHANGED gate (injected as ``retest``);
  4. RETAINS the original REFUTED claim verbatim (residualism), and links each alternate to it with a
     ``RESTRICTION_MAP`` relation — which the sheaf (B3a) reads to suppress a spurious contradiction
     between "REJECTED over gene-body" and "LICENSED over promoter".

Depth-1: a rejected alternate is NOT itself re-parameterized. Spec:
docs/superpowers/specs/2026-07-10-reparameterization-evaluator-design.md. The LLM is a pure proposer
(de Bruijn): it only narrows which re-test to run; only the gate confers standing (two-stratum).
Umbrella-side; grammar/protocol unchanged; Corpus stays 4.
"""
from __future__ import annotations

import json
import logging
from collections.abc import Callable
from dataclasses import dataclass

from polymer_grammar import (
    Claim,
    DataHandle,
    GenerationMode,
    PendingReason,
    Provenance,
    RejectionReason,
    RelationKind,
    Status,
    Tier,
    commitment_hash,
    make_relation_claim,
)
from polymer_grammar.fdr import register_test
from polymer_protocol import Corpus

from polymer_claims import measurement_space as ms
from polymer_claims.accumulating_store import contract_uids

_log = logging.getLogger(__name__)

# The injected gate: re-test the alternate claims via the UNCHANGED licensing pipeline. Returns the
# corpus with the alternates' statuses updated. Real callers pass the pharmaco/spine license path;
# tests pass a stub. The evaluator never licenses on its own (two-stratum).
RetestFn = Callable[[Corpus, "tuple[Claim, ...]"], Corpus]


def refuted_claims(corpus: Corpus) -> tuple[Claim, ...]:
    """The trigger set (v1): claims REJECTED specifically because the data REFUTED them."""
    return tuple(
        c for c in corpus.claims
        if c.status == Status.REJECTED and c.rejection_reason == RejectionReason.REFUTED
    )


class ReparamAgent:
    """Untrusted hybrid generator: an LLM proposes apt measurement modalities from a claim's asserted
    mechanism; the registry grounds them. Mirrors ``relation_proposer.LLMRelationAgent``'s
    injected-``complete`` + re-validate + ``.anthropic`` tripwire pattern."""

    def __init__(self, *, complete: Callable[[str], str]):
        self._complete = complete

    def propose_modalities(self, claim: Claim) -> tuple[ms.Modality, ...]:
        """Return the modalities the LLM proposes, each RE-VALIDATED to the controlled vocabulary
        (bogus strings dropped — never fabricated into a space)."""
        try:
            raw = json.loads(self._complete(self._build_prompt(claim)))
        except (ValueError, TypeError):
            return ()
        out: list[ms.Modality] = []
        for name in raw.get("modalities", []) if isinstance(raw, dict) else []:
            try:
                m = ms.Modality(name)
            except ValueError:
                _log.info("reparam: dropped un-vocabulary modality %r", name)
                continue
            if m not in out:
                out.append(m)
        return tuple(out)

    def _build_prompt(self, claim: Claim) -> str:
        mech = (claim.provenance.rationale if claim.provenance else None) or claim.title
        descr = claim.conclusion.descriptor if claim.conclusion is not None else ""
        vocab = ", ".join(m.value for m in ms.Modality)
        return (
            "A claim was REFUTED over its current measurement space. Its asserted mechanism:\n"
            f"  {mech}\n  {descr}\n"
            "Which measurement modality (from this controlled vocabulary) would be the mechanistically "
            f"apt space to re-test it over? Vocabulary: {vocab}.\n"
            'Reply strictly as JSON: {"modalities": ["<modality>", ...]} (empty list to decline).'
        )

    @classmethod
    def anthropic(cls, *, model: str = "claude-sonnet-4-6", max_tokens: int = 256):  # pragma: no cover - real network
        """Live tripwire — builds a real Anthropic client closure. Needs the [llm] extra; exercised
        via CLI, not unit tests."""
        import anthropic

        client = anthropic.Anthropic()

        def _complete(prompt: str) -> str:
            msg = client.messages.create(
                model=model, max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
            return msg.content[0].text

        return cls(complete=_complete)


def _current_space_ids(claim: Claim) -> frozenset[str]:
    """The registry space_ids the claim currently reads (so an alternate must be a DIFFERENT space)."""
    return frozenset(
        sp.space_id for uid in contract_uids(claim) for sp in ms.spaces_for_contract(uid)
    )


def _swap_data_ref(plan, new_ref: str):
    new_nodes = tuple(
        node.model_copy(update={"inputs": tuple(
            inp.model_copy(update={"ref": new_ref}) if isinstance(inp, DataHandle) else inp
            for inp in node.inputs
        )})
        for node in plan.graph.nodes
    )
    return plan.model_copy(update={"graph": plan.graph.model_copy(update={"nodes": new_nodes})})


def reissue_over_space(claim: Claim, space: ms.MeasurementSpace, *, new_id: str) -> Claim:
    """A NEW, distinct PENDING claim identical to ``claim`` except its plan reads ``space``'s contract
    — the re-parameterization act (a new provenance CHOICE of measurement space). The original is
    never mutated."""
    new_ref = f"se:{space.contract_uid}"
    plan = _swap_data_ref(claim.evaluation_plan, new_ref) if claim.evaluation_plan else None
    prov = Provenance(
        generated_by=GenerationMode.AGENT_GENERATED,
        agent_id="polymer_claims.reparam",
        search_cardinality=1,
        rationale=(
            f"re-parameterization of {claim.id}: re-test over {space.modality.value} "
            f"({space.space_id}) — the original was refuted over a different measurement space"
        ),
    )
    return claim.model_copy(update={
        "id": new_id,
        "status": Status.PENDING,
        "pending_reason": PendingReason.UNTESTED,
        "rejection_reason": None,
        "licensing": None,
        "evaluation_plan": plan,
        "provenance": prov,
    })


@dataclass(frozen=True)
class ReparamResult:
    corpus: Corpus
    n_triggered: int
    n_alternates: int
    audit: tuple[str, ...]


def evaluate(corpus: Corpus, agent: ReparamAgent, *, retest: RetestFn, tier: Tier = Tier.BIOLOGICAL) -> ReparamResult:
    """Run the re-parameterization evaluator over ``corpus``'s REFUTED claims (depth-1).

    Declare-and-charge then re-test: ALL alternate slots are pre-registered on the e-LOND ledger
    BEFORE ``retest`` runs (non-adaptive). Originals are retained; a RESTRICTION_MAP relation links
    each original to its alternate.
    """
    triggered = refuted_claims(corpus)
    available_ids = {s.space_id for s in ms.available_spaces()}
    existing_ids = {c.id for c in corpus.claims}  # idempotency: don't re-mint an existing alternate
    new_claims: list[Claim] = []
    relations: list[Claim] = []
    ledger = corpus.fdr_ledger
    audit: list[str] = []

    for orig in triggered:
        current = _current_space_ids(orig)
        alternates: list[ms.MeasurementSpace] = []
        chosen_ids: set[str] = set()
        for modality in agent.propose_modalities(orig):
            for sp in ms.spaces_for_modality(modality):  # deterministic (sorted)
                if sp.space_id in current or sp.space_id in chosen_ids:
                    continue
                if sp.space_id not in available_ids:  # grounded to real data — never fabricate
                    continue
                if f"{orig.id}::reparam::{sp.space_id}" in existing_ids:  # already re-parameterized
                    continue
                alternates.append(sp)
                chosen_ids.add(sp.space_id)
                break  # one apt-available space per proposed modality
        if not alternates:
            audit.append(f"{orig.id}: no apt-available alternate space")
            continue
        alts = [
            reissue_over_space(orig, sp, new_id=f"{orig.id}::reparam::{sp.space_id}")
            for sp in alternates
        ]
        # DECLARE-AND-CHARGE: lock all K e-LOND slots upfront, BEFORE any is re-tested (non-adaptive).
        for ac in alts:
            ledger = register_test(ledger, ac.id, commitment_hash(ac))
        # RESTRICTION_MAP reinterpret edges (retain original; the sheaf reads these to not frustrate).
        for ac, sp in zip(alts, alternates):
            relations.append(make_relation_claim(
                f"reparam-rel::{orig.id}::{sp.space_id}",
                [orig.id], [ac.id], tier, RelationKind.RESTRICTION_MAP, 0.0,
                rationale=f"{ac.id} re-parameterizes {orig.id} over {sp.space_id} (different measurement space)",
            ))
        new_claims.extend(alts)
        audit.append(f"{orig.id}: {len(alts)} alternate(s) over {[s.space_id for s in alternates]}")

    staged = corpus.model_copy(update={
        "claims": corpus.claims + tuple(new_claims) + tuple(relations),
        "fdr_ledger": ledger,
    })
    # Re-test the alternates via the UNCHANGED gate (depth-1: only these; not re-fed).
    final = retest(staged, tuple(new_claims)) if new_claims else staged
    return ReparamResult(
        corpus=final,
        n_triggered=len(triggered),
        n_alternates=len(new_claims),
        audit=tuple(audit),
    )
