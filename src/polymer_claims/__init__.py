"""Polymer Claims umbrella — a thin CLI over the `polymer_grammar` IR and the
`polymer_protocol` runtime. `pip install polymer-claims` pulls both transitively.

Convenience re-exports keep the umbrella import surface small but useful for a
local-node embedder: the grammar `Claim`, the protocol `Corpus`, and the headline
runtime entry points.
"""
from __future__ import annotations

__version__ = "0.1.0"

# Convenience re-exports (optional; the heavy lifting lives in the two component
# packages). Kept lazy-free — both deps are declared, so the imports always resolve.
from polymer_grammar import Claim
from polymer_protocol import Corpus, next_action, run_cycle

from polymer_claims.analysis_profile import (
    AnalysisProfile,
    content_hash,
    profile_oracle_id,
    profile_oracle_registry,
    substrate_tier,
)
from polymer_claims.profiles import load_profile
from polymer_claims.contracts import (
    AccessMethod,
    Checksum,
    SEContractRef,
    load_contract,
)
from polymer_claims.attestation import (
    AttestationBundle,
    build_attestation_bundle,
    resolve_contract_index,
)

__all__ = [
    "AccessMethod",
    "AnalysisProfile",
    "AttestationBundle",
    "Checksum",
    "Claim",
    "Corpus",
    "SEContractRef",
    "__version__",
    "build_attestation_bundle",
    "content_hash",
    "load_contract",
    "load_profile",
    "next_action",
    "profile_oracle_id",
    "profile_oracle_registry",
    "resolve_contract_index",
    "run_cycle",
    "substrate_tier",
]
