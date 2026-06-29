"""Offline kernel proof: build the synthetic HM450 fixture, run the REAL n-DMP gate, return the
outcome. Shared by the verify-kernel CLI and the CI guard test. No network; deterministic.
Builds into a TemporaryDirectory scoped by using_contract_root — nothing is written to the source
tree. See docs/superpowers/specs/2026-06-23-offline-kernel-proof-design.md."""
from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path

from polymer_grammar import Status

from polymer_claims._ndmp_gate import run_ndmp_gate
from polymer_claims.contracts import clear_contract_cache, using_contract_root
from polymer_claims.ingest.synthetic import build_synthetic_contract

_REF = "se:tcga_laml_idh_synth@1"
_ALPHA = 0.05
_CLAIM_ID = "synthetic-kernel-ndmp"


@dataclass(frozen=True)
class KernelProofResult:
    status: Status
    independence_tier: object | None   # IndependenceTier | None — kept loose to avoid import coupling
    n_dmps: int
    e_value: float
    n_probes: int
    k: int
    licensed: bool


def run_synthetic_kernel_proof() -> KernelProofResult:
    """Build the synthetic contract into a temp dir, run the real gate scoped to it, return result.
    Writes nothing to the source tree; the temp contract is discarded on exit."""
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        build_synthetic_contract(root)
        with using_contract_root(root):
            clear_contract_cache()   # don't resolve a stale cached entry for this uid
            g = run_ndmp_gate(_REF, _CLAIM_ID, alpha=_ALPHA)
        clear_contract_cache()   # leave no temp-rooted cache entry behind
    return KernelProofResult(
        status=g["status_enum"], independence_tier=g["tier_enum"], n_dmps=g["n_dmps"],
        e_value=g["e_value"], n_probes=g["n_probes"], k=g["k"],
        licensed=(g["status_enum"] is Status.LICENSED),
    )
