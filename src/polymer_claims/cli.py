"""`polymer-claims` console-script CLI — a thin shell over the COMPLETE runtime.

Commands:
  version          print the three component versions
  validate FILE    validate a claim JSON through the grammar
  run-cycle FILE   run ONE run_cycle over a corpus with the reference adapters
  loop FILE        drive the #5d budget-governed scheduler until the budget exhausts
  export-topology  emit a TopologyExport for a corpus
  export-timeline  emit a warm-started TopologyTimeline across N run_cycle iterations

The CLI injects the two deterministic reference adapters by default; real
adapters/oracles/red-teamers are a later `--plugin` surface (out of scope for v1).
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _dist_version
from pathlib import Path

from polymer_grammar import (
    Claim,
    IdentityAdapter,
    MaterializationContext,
    ReferenceAdapter,
)
from polymer_protocol import (
    ActionKind,
    Corpus,
    Layout,
    SchedulerConfig,
    SchedulerState,
    export_timeline,
    export_topology,
    next_action,
    run_cycle,
)

from . import __version__ as _claims_version
from .io import dump_corpus, load_corpus
from .node import NodeRunner

# Default reference adapters + materialization context (deterministic, in-package).
_ADAPTERS = (IdentityAdapter(), ReferenceAdapter(identity="reference"))
_CTX = MaterializationContext(id="M1", api_version="v1", data_version="d1")


def _component_version(dist_name: str, fallback: str) -> str:
    try:
        return _dist_version(dist_name)
    except PackageNotFoundError:
        return fallback


def _status_counts(corpus: Corpus) -> Counter:
    return Counter(c.status.value for c in corpus.claims)


def _write_or_print(text: str, out: str | None) -> None:
    if out:
        Path(out).write_text(text)
    else:
        print(text)


# ---------------------------------------------------------------------------
# commands
# ---------------------------------------------------------------------------
def _cmd_version(_args: argparse.Namespace) -> int:
    grammar_v = _component_version("polymer-grammar", _claims_version)
    protocol_v = _component_version("polymer-protocol", _claims_version)
    claims_v = _component_version("polymer-claims", _claims_version)
    print(f"polymer-claims   {claims_v}")
    print(f"polymer-protocol {protocol_v}")
    print(f"polymer-grammar  {grammar_v}")
    return 0


def _cmd_validate(args: argparse.Namespace) -> int:
    text = Path(args.claim).read_text()
    try:
        Claim.model_validate_json(text)
    except Exception as exc:  # noqa: BLE001 — surface any validation error to the user
        print(f"invalid: {exc}", file=sys.stderr)
        return 1
    print("valid")
    return 0


def _build_llm_proposer(model: str):
    """Lazy-build a bridge_proposer over a real Anthropic-backed LLMGenerationAdapter.
    Raises RuntimeError with an install/key hint if the [llm] extra or the API key is missing."""
    import os
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise RuntimeError("set ANTHROPIC_API_KEY to use --llm")
    from polymer_protocol import bridge_proposer  # local import keeps top-level clean
    from .llm_adapter import LLMGenerationAdapter   # safe (no anthropic at import); .anthropic lazy-imports it
    adapter = LLMGenerationAdapter.anthropic(model=model)   # raises RuntimeError if [llm] missing
    return bridge_proposer((adapter,))


def _cmd_run_cycle(args: argparse.Namespace) -> int:
    corpus = load_corpus(args.corpus)
    proposers = ()
    if getattr(args, "llm", False):
        try:
            proposers = (_build_llm_proposer(args.llm_model),)
        except RuntimeError as exc:
            print(str(exc), file=sys.stderr)
            return 1
    result = run_cycle(corpus, _ADAPTERS, _CTX, proposers=proposers) if proposers \
        else run_cycle(corpus, _ADAPTERS, _CTX)
    counts = _status_counts(result.corpus)
    summary = ", ".join(f"{k}={v}" for k, v in sorted(counts.items()))
    print(f"status: {summary or '(none)'}", file=sys.stderr)
    print(f"frontier: {len(result.frontier)}", file=sys.stderr)
    _write_or_print(dump_corpus(result.corpus), args.out)
    return 0


def _cmd_loop(args: argparse.Namespace) -> int:
    corpus = load_corpus(args.corpus)
    config = SchedulerConfig()
    remaining = float(args.budget)
    state = SchedulerState(corpus=corpus)

    trace: list[str] = []
    while True:
        action = next_action(state, budget=remaining, config=config)
        if action is None:
            break
        trace.append(f"{action.kind.value}: {action.rationale}")
        if action.kind is not ActionKind.RUN_CYCLE:
            # v1 loop only drives RUN_CYCLE; a daemon action means we stop and report.
            print(
                f"non-RUN_CYCLE action recommended ({action.kind.value}); stopping.",
                file=sys.stderr,
            )
            break
        if action.estimated_cost > remaining:
            break
        result = run_cycle(corpus, _ADAPTERS, _CTX, ledger=state.ledger)
        corpus = result.corpus
        remaining -= action.estimated_cost
        state = SchedulerState(corpus=corpus, ledger=result.ledger)

    print(f"steps: {len(trace)}", file=sys.stderr)
    for line in trace:
        print(f"  {line}", file=sys.stderr)
    counts = _status_counts(corpus)
    summary = ", ".join(f"{k}={v}" for k, v in sorted(counts.items()))
    print(f"final status: {summary or '(none)'}", file=sys.stderr)
    print(f"budget remaining: {remaining}", file=sys.stderr)
    _write_or_print(dump_corpus(corpus), args.out)
    return 0


def _cmd_export_topology(args: argparse.Namespace) -> int:
    corpus = load_corpus(args.corpus)
    exp = export_topology(corpus, layout=Layout.FORCE_DIRECTED)
    _write_or_print(exp.model_dump_json(), args.out)
    return 0


def _cmd_export_timeline(args: argparse.Namespace) -> int:
    corpus = load_corpus(args.corpus)
    timeline = export_timeline(corpus, _ADAPTERS, _CTX, n_cycles=args.cycles)
    print(
        f"frames: {len(timeline.frames)} (n_cycles={timeline.n_cycles})",
        file=sys.stderr,
    )
    _write_or_print(timeline.model_dump_json(), args.out)
    return 0


def _import_server():
    """Import the optional serve deps; raises ImportError if the [serve] extra isn't installed."""
    import uvicorn

    from .server import create_app
    return uvicorn, create_app


_LOOPBACK = {"127.0.0.1", "localhost", "::1"}


def _cmd_serve(args: argparse.Namespace) -> int:
    try:
        uvicorn, create_app = _import_server()
    except ImportError:
        print(
            "the 'serve' command needs the optional extra: "
            "pip install 'polymer-claims[serve]'",
            file=sys.stderr,
        )
        return 1
    if args.host not in _LOOPBACK and not args.unsafe_remote_control:
        print(
            f"refusing to bind a non-loopback host ({args.host!r}): the live node's "
            "mutating routes (/step,/pause,/resume) are UNAUTHENTICATED. Re-run with "
            "--unsafe-remote-control to override (you accept the exposure).",
            file=sys.stderr,
        )
        return 1
    llm_proposer = None
    if getattr(args, "llm", False):
        try:
            llm_proposer = _build_llm_proposer(args.llm_model)
        except RuntimeError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        from .throttle import every_n_ticks
        # throttle so the live node's GENERATE stage is watchable/affordable
        llm_proposer = every_n_ticks(llm_proposer, n=args.llm_every)
    if args.seed_corpus:
        corpus = load_corpus(args.seed_corpus)
        seed_kwargs = {}
        if llm_proposer is not None:
            seed_kwargs["proposers"] = (llm_proposer,)
        runner = NodeRunner.from_seed(
            corpus,
            scheduler_budget=args.budget,
            max_frames=args.max_frames,
            **seed_kwargs,
        )
    else:
        from .seed import default_seed_corpus
        corpus, kwargs = default_seed_corpus()
        if llm_proposer is not None:
            # run the LLM agent ALONGSIDE the seed's rival/revision proposers.
            kwargs["proposers"] = tuple(kwargs.get("proposers", ())) + (llm_proposer,)
        # `args.budget` is the SCHEDULER budget (gates RUN_CYCLE); the evolving
        # seed's `kwargs["budget"]` is run_cycle's SELECT budget and flows
        # through `**kwargs` to spread licensing progressively across frames.
        runner = NodeRunner.from_seed(
            corpus, scheduler_budget=args.budget, max_frames=args.max_frames, **kwargs
        )
    app = create_app(runner, interval=args.interval, origins=args.origins or None)
    uvicorn.run(app, host=args.host, port=args.port)
    return 0


# ---------------------------------------------------------------------------
# parser
# ---------------------------------------------------------------------------
def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="polymer-claims",
        description="Local knowledge-generation node — grammar + runtime CLI.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_version = sub.add_parser("version", help="print component versions")
    p_version.set_defaults(func=_cmd_version)

    p_validate = sub.add_parser("validate", help="validate a claim JSON")
    p_validate.add_argument("claim", help="path to a claim JSON file")
    p_validate.set_defaults(func=_cmd_validate)

    p_run = sub.add_parser("run-cycle", help="run ONE run_cycle over a corpus")
    p_run.add_argument("corpus", help="path to a corpus JSON file")
    p_run.add_argument("--out", default=None, help="write resulting corpus JSON here")
    p_run.add_argument("--llm", action="store_true", help="generate executable claims via a real LLM (needs the [llm] extra + ANTHROPIC_API_KEY)")
    p_run.add_argument("--llm-model", default="claude-sonnet-4-6", help="model for --llm")
    p_run.set_defaults(func=_cmd_run_cycle)

    p_loop = sub.add_parser("loop", help="drive the budget-governed scheduler")
    p_loop.add_argument("corpus", help="path to a corpus JSON file")
    p_loop.add_argument("--budget", type=float, required=True, help="scheduler budget")
    p_loop.add_argument("--out", default=None, help="write final corpus JSON here")
    p_loop.set_defaults(func=_cmd_loop)

    p_topo = sub.add_parser("export-topology", help="emit a TopologyExport for a corpus")
    p_topo.add_argument("corpus", help="path to a corpus JSON file")
    p_topo.add_argument("--out", default=None, help="write TopologyExport JSON here")
    p_topo.set_defaults(func=_cmd_export_topology)

    p_tl = sub.add_parser(
        "export-timeline", help="emit a warm-started TopologyTimeline across N cycles"
    )
    p_tl.add_argument("corpus", help="path to a corpus JSON file")
    p_tl.add_argument("--cycles", type=int, required=True, help="number of run_cycle iterations")
    p_tl.add_argument("--out", default=None, help="write TopologyTimeline JSON here")
    p_tl.set_defaults(func=_cmd_export_timeline)

    p_serve = sub.add_parser(
        "serve", help="run the live node server (SSE) — needs the [serve] extra"
    )
    p_serve.add_argument(
        "--seed-corpus",
        default=None,
        help="path to a seed corpus JSON (default: built-in evolving seed)",
    )
    p_serve.add_argument("--host", default="127.0.0.1", help="bind host")
    p_serve.add_argument("--port", type=int, default=8000, help="bind port")
    p_serve.add_argument(
        "--unsafe-remote-control",
        action="store_true",
        help="allow binding a non-loopback host despite UNAUTHENTICATED mutating routes",
    )
    p_serve.add_argument(
        "--max-frames",
        type=int,
        default=10000,
        help="max retained frames in the live node (ring cap)",
    )
    p_serve.add_argument(
        "--interval", type=float, default=1.5, help="seconds between auto-ticks"
    )
    p_serve.add_argument(
        "--budget", type=float, default=1e9, help="scheduler budget per tick"
    )
    p_serve.add_argument(
        "--origins", nargs="*", default=None, help="extra CORS origins"
    )
    p_serve.add_argument("--llm", action="store_true", help="drive GENERATE with a real LLM agent (needs the [llm] extra + ANTHROPIC_API_KEY)")
    p_serve.add_argument("--llm-model", default="claude-sonnet-4-6", help="model for --llm")
    p_serve.add_argument("--llm-every", type=int, default=4, help="LLM proposes every Nth tick (throttle)")
    p_serve.set_defaults(func=_cmd_serve)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
