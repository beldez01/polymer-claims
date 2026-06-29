"""Real-data kernel parity gate. This module's run_real_kernel_proof (Task 4) resolves the three
pinned inputs, rebuilds se:tcga_laml_idh@2 into a temp contract root, asserts content-address parity
vs the committed pins, runs the REAL n-DMP gate, and requires LICENSED @ REPRODUCED. It proves the
pinned real-data computation reproduces — NOT data veracity (spec §0)."""
from __future__ import annotations

import json
import math
import tempfile
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path

from polymer_grammar import Status

from polymer_claims._ndmp_gate import run_ndmp_gate
from polymer_claims.contracts import clear_contract_cache, load_contract, using_contract_root
from polymer_claims.ingest._pinned import resolve_pinned_file
from polymer_claims.ingest.tcga_xena import build_real_contract, compute_canonical_checksum

_REF = "se:tcga_laml_idh@2"
_ALPHA = 0.05
_CLAIM_ID = "tcga-laml-ndmp"


def load_pins() -> dict:
    """Load the committed reference pins (real_kernel_pins.json), via importlib.resources so an
    installed package resolves it cleanly."""
    return json.loads(
        files("polymer_claims.ingest").joinpath("real_kernel_pins.json").read_text())


class ParityError(RuntimeError):
    """A rebuilt content-address did not match its pin (the kernel did not reproduce)."""


@dataclass(frozen=True)
class RealKernelProofResult:
    status: Status
    independence_tier: object | None
    n_dmps: int
    e_value: float
    n_probes: int
    k: int
    licensed: bool


def _assert(name: str, expected, observed) -> None:
    if expected != observed:
        raise ParityError(f"parity mismatch [{name}]: expected {expected!r}, got {observed!r}")


def _assert_evalue(expected, observed: float) -> None:
    if expected == "inf":
        if not (math.isinf(observed) and observed > 0):
            raise ParityError(f"parity mismatch [e_value]: expected +inf, got {observed!r}")
        return
    exp = float(expected)
    if observed != exp and abs(observed - exp) > abs(exp) * 1e-12:
        raise ParityError(f"parity mismatch [e_value]: expected {expected}, got {observed!r}")


def _build_claim_and_run_gate() -> dict:
    """Fixed claim construction (spec §4.4) + the real gate, scoped to the active contract root.
    Returns the observed gate quantities. Probes default to ALL (_all_probe_ids) via probes=None."""
    return run_ndmp_gate(_REF, _CLAIM_ID, alpha=_ALPHA)


def _run_gate_capture() -> dict:
    """Test-only convenience: run the gate under the already-active contract root and return the
    captured quantities (used by tests to build truthful pins for a synthetic fixture)."""
    return _build_claim_and_run_gate()


def run_real_kernel_proof(
    xena_file: Path | None, cbioportal_dir: Path | None, *,
    pins: dict, cache_dir: Path, allow_fetch: bool = False,
    idh_count_band: tuple[int, int] = (20, 50),
    required_idh_mut_controls: frozenset[str] | None = None,
) -> RealKernelProofResult:
    inp = pins["inputs"]
    cache_dir = Path(cache_dir)
    # resolve each input independently and keep the concrete returned paths (audit #1): a local dir
    # missing one file + --fetch retrieving the other must not silently read the wrong directory.
    xena = resolve_pinned_file(
        inp["xena"]["filename"], local=xena_file, url=inp["xena"].get("url"),
        sha256=inp["xena"]["sha256"], cache_dir=cache_dir, allow_fetch=allow_fetch)
    mutations_file = resolve_pinned_file(
        inp["cbio_mutations"]["filename"], local=cbioportal_dir, url=inp["cbio_mutations"].get("url"),
        sha256=inp["cbio_mutations"]["sha256"], cache_dir=cache_dir, allow_fetch=allow_fetch)
    sequenced_file = resolve_pinned_file(
        inp["cbio_sequenced"]["filename"], local=cbioportal_dir,
        url=inp["cbio_sequenced"].get("api_endpoint"), sha256=inp["cbio_sequenced"]["sha256"],
        cache_dir=cache_dir, allow_fetch=allow_fetch)
    idh_call_source = f"cbioportal:laml_tcga_pub@{inp['cbio_mutations']['commit']}"
    exp = pins["expected"]

    build_kw = {"mutations_file": mutations_file, "sequenced_file": sequenced_file,
                "idh_call_source": idh_call_source, "idh_count_band": idh_count_band}
    if required_idh_mut_controls is not None:
        build_kw["required_idh_mut_controls"] = required_idh_mut_controls

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        rbr = build_real_contract(root, xena, **build_kw)
        with using_contract_root(root):
            clear_contract_cache()
            ref = load_contract(_REF)
            # --- version identity first (§4.3) ---
            _assert("contract_uid", exp["contract_uid"], ref.contract_uid)
            # --- byte-level primary gate, with canonical diagnostic branch (§4.1) ---
            if ref.checksums[0].checksum != exp["contract_checksum"]:
                if compute_canonical_checksum(root) == exp["canonical_checksum"]:
                    raise ParityError(
                        "parity mismatch [contract_checksum]: bytes differ but canonical_checksum "
                        "matches — logical content reproduced, serialization differs (builder not "
                        "byte-faithful)")
                raise ParityError(
                    "parity mismatch [contract_checksum]: bytes differ and canonical_checksum "
                    "differs — contract content itself diverged")
            # --- localized diagnostics ---
            _assert("dimnames_hash", exp["dimnames_hash"], ref.dimnames_hash)
            _assert("group_digest", exp["group_digest"], rbr.group_digest)
            _assert("idh_mut_n", exp["idh_mut_n"], rbr.idh_mut_n)
            _assert("wt_n", exp["wt_n"], rbr.wt_n)
            _assert("n_probes", exp["n_probes"], rbr.n_probes)
            # --- gate + gate-result parity ---
            gate = _build_claim_and_run_gate()
            _assert("n_dmps", exp["n_dmps"], gate["n_dmps"])
            _assert_evalue(exp["e_value"], gate["e_value"])
            # Check status/tier first: on a non-licensing rebuild profile_hash/semantic_run_id
            # come back None, so asserting them first masks the actionable status divergence.
            _assert("status", exp["status"], gate["status"])
            _assert("independence_tier", exp["independence_tier"], gate["independence_tier"])
            _assert("profile_hash", exp["profile_hash"], gate["profile_hash"])
            _assert("semantic_run_id", exp["semantic_run_id"], gate["semantic_run_id"])
        clear_contract_cache()

    return RealKernelProofResult(
        status=gate["status_enum"], independence_tier=gate["tier_enum"], n_dmps=gate["n_dmps"],
        e_value=gate["e_value"], n_probes=gate["n_probes"], k=gate["k"],
        licensed=(gate["status_enum"] is Status.LICENSED))
