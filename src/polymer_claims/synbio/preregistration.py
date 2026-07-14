"""Durendal pre-registration MECHANICS (synbio Phase 3 — the sealing machinery, not the science).

Given a blinded seed (assembled + firewall-filtered by `firewall.assemble_blinded_seed`) and a
derivation PLAN, seal a commit-before-data pre-registration: a deterministic `commitment_hash` over
the {sealed admissible-seed claim-ids + their admissibility tags + the plan}, plus a locked e-LOND
α-slot for the derivation (`fdr.register_test`). This is what makes the eventual Durendal
re-derivation (Phase 4) a genuine held-out prediction — the answer is committed to BEFORE the
derivation runs, and the seal records exactly which admissible priors were in scope.

THE MACHINERY ONLY. The blinded-seed CURATION (which real synbio claims go in), the independent
no-leakage review, and the Phase-4 derivation run are the OPERATOR's — this module never curates a
seed, never runs a derivation, and licenses nothing. Two-stratum: the seed is CONJECTURED /
LITERATURE_EXTRACTED priors; the derivation earns standing only through the real gate. Umbrella-side;
Corpus stays 4 (it only charges an e-LOND slot on an existing `FDRLedger`); no fabricated data.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from polymer_grammar import FDRLedger
from polymer_grammar.fdr import register_test

from polymer_claims._hashing import canonical_sha256
from polymer_claims.synbio.firewall import BlindedSeed


@dataclass(frozen=True)
class PreRegistration:
    """An auditable, commit-before-data seal of a blinded seed + derivation plan."""

    commitment_hash: str                 # sha256: over {sealed seed + plan} — deterministic
    derivation_id: str                   # the pre-registered derivation's claim id (the α-slot owner)
    seed_claim_ids: tuple[str, ...]      # the admissible seed claim ids, sorted (what was in scope)
    admissibility: dict[str, str]        # claim_id -> the firewall's deciding rule (audit trail)
    n_excluded: int                      # how many candidates the firewall REFUSED (leak/post-cutoff)
    alpha_allocated: float               # the locked e-LOND α for the derivation (charged here)
    fdr_test_index: int                  # the charged slot's 1-based index in the stream


def seal_preregistration(
    seed: BlindedSeed,
    plan: Any,
    *,
    ledger: FDRLedger,
    derivation_id: str,
) -> tuple[PreRegistration, FDRLedger]:
    """Seal the pre-registration and charge the α-slot. Returns ``(PreRegistration, new_ledger)``.

    ``plan`` is any canonical-JSON-serializable derivation plan (id + spec, a dict, etc.). The
    commitment binds the SEALED admissible seed (the firewall's ``admitted`` set + tags) to the plan,
    so neither can be silently swapped after the fact. The α-slot is locked BEFORE any derivation
    e-value exists (commit-before-data) — the slot is consumed even if the derivation never resolves.
    Only the firewall-ADMITTED seed enters the seal; refused (answer-leaking / post-cutoff) candidates
    are excluded by construction.
    """
    seed_claim_ids = tuple(sorted(seed.admitted))
    payload = {
        "seed": [[cid, seed.admitted[cid]] for cid in seed_claim_ids],  # sorted -> deterministic
        "plan": plan,
    }
    commitment = canonical_sha256(payload)
    new_ledger = register_test(ledger, derivation_id, commitment)
    slot = new_ledger.tests[-1]
    record = PreRegistration(
        commitment_hash=commitment,
        derivation_id=derivation_id,
        seed_claim_ids=seed_claim_ids,
        admissibility=dict(seed.admitted),
        n_excluded=len(seed.rejected),
        alpha_allocated=slot.alpha_allocated,
        fdr_test_index=slot.index,
    )
    return record, new_ledger
