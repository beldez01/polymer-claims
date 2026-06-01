"""polymer-formalclaim CLI — ``validate`` / ``evaluate`` / ``refresh-corpus``.

Wraps the inference evaluator so harness hooks can invoke it as a
standalone binary without loading the full polymer-genomics API.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from polymer_formalclaim._version import __version__


def _cmd_validate(args: argparse.Namespace) -> int:
    # Imported lazily so `--help` and `--version` don't pay the pydantic cost.
    from polymer_formalclaim.schema import FormalClaim  # type: ignore[import-not-found]
    from polymer_formalclaim.evaluate import evaluate  # type: ignore[import-not-found]

    path = Path(args.path)
    try:
        claim = FormalClaim.model_validate(json.loads(path.read_text()))
    except Exception as exc:
        print(f"REJECTED  {path}: SCHEMA_INVALID — {exc}", file=sys.stderr)
        return 2

    result = evaluate(claim)
    verdict = result.verdict
    conjuncts_true = sum(1 for c in result.conjuncts if c.result is True)
    print(f"{verdict}  {path}  ({conjuncts_true}/{len(result.conjuncts)} conjuncts true)")

    if verdict == "REJECTED" and args.fail_on_rejected:
        return 1
    if verdict == "PENDING" and args.fail_on_pending:
        return 1
    return 0


def _cmd_refresh_corpus(args: argparse.Namespace) -> int:
    pointer = Path(args.pointer)
    if not pointer.exists():
        print(f"pointer not found: {pointer}", file=sys.stderr)
        return 1
    # Placeholder: full refresh downloads the latest corpus snapshot and
    # updates ``snapshot_sha256`` + ``snapshot_date`` in the pointer file.
    # Wired after the ``corpus_rebuild`` GitHub Release pipeline is live.
    print(f"refresh-corpus: no-op (pointer={pointer})")
    return 0


def _cmd_emit_nanopub(args: argparse.Namespace) -> int:
    """FormalClaim → Nanopublication TriG projection."""
    from polymer_formalclaim.schema import FormalClaim  # type: ignore[import-not-found]
    from polymer_formalclaim.nanopub import to_trig  # type: ignore[import-not-found]

    path = Path(args.path)
    claim = FormalClaim.model_validate(json.loads(path.read_text()))
    trig = to_trig(claim)
    out = args.out
    if out:
        Path(out).write_text(trig)
        print(f"wrote {out}")
    else:
        print(trig, end="")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="polymer-formalclaim",
        description="FormalClaim IR v1.2 — validate, evaluate, MCP.",
    )
    parser.add_argument("--version", action="version", version=__version__)

    sub = parser.add_subparsers(dest="cmd", required=True)

    val = sub.add_parser("validate", help="Validate + evaluate a FormalClaim JSON file.")
    val.add_argument("path", help="Path to the claim JSON file.")
    val.add_argument("--fail-on-rejected", action="store_true", help="Exit 1 on REJECTED.")
    val.add_argument("--fail-on-pending", action="store_true", help="Exit 1 on PENDING.")
    val.set_defaults(func=_cmd_validate)

    ref = sub.add_parser("refresh-corpus", help="Refresh the bundled corpus snapshot pointer.")
    ref.add_argument("--pointer", default="corpus/pointer.json")
    ref.set_defaults(func=_cmd_refresh_corpus)

    nano = sub.add_parser(
        "emit-nanopub",
        help="Project a FormalClaim JSON into a deterministic Nanopublication TriG file.",
    )
    nano.add_argument("path", help="Path to the claim JSON file.")
    nano.add_argument("--out", help="Write TriG to this path; default is stdout.")
    nano.set_defaults(func=_cmd_emit_nanopub)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
