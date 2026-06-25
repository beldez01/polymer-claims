# scripts/bootstrap_real_kernel_pins.py
"""Capture/compare real_kernel_pins.json content-addresses (spec §6). LOCAL-ONLY: run in a tree that
holds the real Xena matrix + cBioPortal inputs and the trusted local @2 contract.

Two modes, used together to AVOID self-fulfilling parity:
  --from-existing : read the addresses of the ALREADY-TRUSTED @2 contract (no rebuild) -> the ground
                    truth to compare against. Prints the `expected` block only.
  (rebuild)       : rebuild @2 with the NEW builder from the supplied inputs -> the full pins.

Procedure: run BOTH, diff their `expected` blocks; only if identical, write the rebuild output to
src/polymer_claims/ingest/real_kernel_pins.json and commit. Usage:
  .venv/bin/python scripts/bootstrap_real_kernel_pins.py --from-existing \
      --contract-root src/polymer_claims/contracts > trusted_expected.json
  .venv/bin/python scripts/bootstrap_real_kernel_pins.py \
      --xena /path/TCGA-LAML.methylation450.tsv.gz --cbioportal /path/cbio \
      --commit 86690e1ed9752b1dcd50b5657f5f05eafa4b6b78 > rebuilt_pins.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import tempfile
from pathlib import Path

from polymer_claims.contracts import clear_contract_cache, load_contract, using_contract_root
from polymer_claims.ingest.tcga_xena import STEM, build_real_contract, compute_canonical_checksum
from polymer_claims.real_kernel_proof import _build_claim_and_run_gate


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _expected_block(contract_root: Path) -> dict:
    """Compute the `expected` content-addresses from a contract root holding the @2 artifact."""
    manifest = json.loads((contract_root / f"{STEM}.json").read_text())
    meta = manifest["metadata"]
    with using_contract_root(contract_root):
        clear_contract_cache()
        ref = load_contract("se:tcga_laml_idh@2")
        canonical = compute_canonical_checksum(contract_root)
        gate = _build_claim_and_run_gate()
    clear_contract_cache()
    return {
        "contract_uid": ref.contract_uid,
        "contract_checksum": ref.checksums[0].checksum,
        "canonical_checksum": canonical,
        "dimnames_hash": ref.dimnames_hash,
        "group_digest": meta["group_digest"],
        "idh_mut_n": meta["idh_mut_n"], "wt_n": meta["wt_n"], "n_probes": manifest["dim"][0],
        "n_dmps": gate["n_dmps"],
        "e_value": "inf" if math.isinf(gate["e_value"]) else repr(gate["e_value"]),
        "profile_hash": gate["profile_hash"], "semantic_run_id": gate["semantic_run_id"],
        "status": gate["status"], "independence_tier": gate["independence_tier"],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--from-existing", action="store_true",
                    help="read the already-trusted @2 contract (no rebuild); print the expected block")
    ap.add_argument("--contract-root", type=Path, default=Path("src/polymer_claims/contracts"))
    ap.add_argument("--xena", type=Path)
    ap.add_argument("--cbioportal", type=Path)
    ap.add_argument("--commit")
    ap.add_argument("--xena-url", default="https://gdc-hub.s3.us-east-1.amazonaws.com/download/TCGA-LAML.methylation450.tsv.gz")
    ap.add_argument("--api-endpoint", default="https://www.cbioportal.org/api/sample-lists/laml_tcga_pub_sequenced/sample-ids")
    args = ap.parse_args()

    if args.from_existing:
        print(json.dumps({"expected": _expected_block(args.contract_root)}, indent=2))
        return 0

    if not (args.xena and args.cbioportal and args.commit):
        ap.error("rebuild mode needs --xena, --cbioportal, and --commit")
    idh_call_source = f"cbioportal:laml_tcga_pub@{args.commit}"
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        build_real_contract(
            root, args.xena,
            mutations_file=args.cbioportal / "data_mutations.txt",
            sequenced_file=args.cbioportal / "sequenced_samples.json",
            idh_call_source=idh_call_source)
        expected = _expected_block(root)

    pins = {
        "contract_uid": "tcga_laml_idh@2",
        "inputs": {
            "xena": {"filename": "TCGA-LAML.methylation450.tsv.gz", "sha256": _sha(args.xena),
                     "bytes": args.xena.stat().st_size, "url": args.xena_url},
            "cbio_mutations": {"commit": args.commit,
                               "url": f"https://raw.githubusercontent.com/cBioPortal/datahub/{args.commit}/public/laml_tcga_pub/data_mutations.txt",
                               "filename": "data_mutations.txt",
                               "sha256": _sha(args.cbioportal / "data_mutations.txt")},
            "cbio_sequenced": {"api_endpoint": args.api_endpoint, "filename": "sequenced_samples.json",
                               "sha256": _sha(args.cbioportal / "sequenced_samples.json")},
        },
        "expected": expected,
    }
    print(json.dumps(pins, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
