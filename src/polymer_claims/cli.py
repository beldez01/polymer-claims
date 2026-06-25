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
import os
import sys
import urllib.error
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


def _cmd_ingest(args: argparse.Namespace) -> int:
    if args.dataset != "tcga-laml":
        print(f"unknown ingest dataset: {args.dataset!r}", file=sys.stderr)
        return 1
    from .ingest.tcga_laml import ingest_tcga_laml
    try:
        print(ingest_tcga_laml(args.data_dir))
    except urllib.error.URLError as exc:
        print(
            "GDC unreachable — could not fetch the real TCGA-LAML data "
            f"({exc.reason if hasattr(exc, 'reason') else exc}).\n"
            "  • For an offline pipeline check, run: polymer-claims verify-kernel\n"
            "  • To reproduce the REAL proof, see docs/superpowers/2026-06-23-kernel-proof-runbook.md",
            file=sys.stderr,
        )
        return 1
    except Exception as exc:  # noqa: BLE001 — surface any other ingest error to the user
        print(f"ingest failed: {exc}", file=sys.stderr)
        return 1
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


def _build_real_data_proposer(model: str):
    """Lazy-build a bridge_proposer over a MeanDiffGenerationAdapter (real-data generation).
    Raises RuntimeError with a key/extra hint if [llm] or ANTHROPIC_API_KEY is missing."""
    import os
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise RuntimeError("set ANTHROPIC_API_KEY to use --real-data")
    from polymer_protocol import bridge_proposer
    from .llm_adapter import MeanDiffGenerationAdapter
    adapter = MeanDiffGenerationAdapter.anthropic(model=model)   # raises RuntimeError if [llm] missing
    return bridge_proposer((adapter,))


def _build_methyl_proposer(model: str):
    """Lazy-build a bridge_proposer over a MethylGenerationAdapter (Phase B).
    Raises RuntimeError with a key/extra hint if [llm] or ANTHROPIC_API_KEY is missing."""
    import os
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise RuntimeError("set ANTHROPIC_API_KEY to use --methyl-data")
    from polymer_protocol import bridge_proposer
    from .llm_adapter import MethylGenerationAdapter
    adapter = MethylGenerationAdapter.anthropic(model=model)
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


def _cmd_export_consistency(args: argparse.Namespace) -> int:
    corpus = load_corpus(args.corpus)
    from polymer_protocol import extract_sheaf  # pure
    try:
        from .sheaf_spectrum import consistency_report  # lazy: base import stays numpy-free
    except ImportError:
        print(
            "export-consistency needs the [embed] extra (numpy). "
            "Install: pip install 'polymer-claims[embed]'",
            file=sys.stderr,
        )
        return 1
    report = consistency_report(extract_sheaf(corpus))
    _write_or_print(report.model_dump_json(), args.out)
    return 0


def _cmd_export_attestation(args: argparse.Namespace) -> int:
    if args.key and args.format != "dsse":
        print("export-attestation: --key applies only to --format dsse", file=sys.stderr)
        return 1
    from .attestation import (
        build_attestation_bundle, build_attestation_statements, dsse_envelope, resolve_contract_index,
    )
    corpus = load_corpus(args.corpus)
    index = resolve_contract_index(corpus)
    if args.format == "dsse":
        envelopes = [dsse_envelope(s) for s in build_attestation_statements(corpus, contract_index=index)]
        if args.key:
            try:
                from .signing import load_private_key, sign_envelope
            except ModuleNotFoundError as exc:
                return _sign_dep_error(exc)
            try:
                priv = load_private_key(Path(args.key).read_bytes())
            except ModuleNotFoundError as exc:
                return _sign_dep_error(exc)
            except (OSError, ValueError) as exc:        # unreadable / malformed PEM -> rc 1, no traceback
                print(f"export-attestation: cannot load private key {args.key}: {exc}", file=sys.stderr)
                return 1
            envelopes = [sign_envelope(e, priv) for e in envelopes]
        output = "".join(e.model_dump_json(by_alias=True, exclude_none=True) + "\n" for e in envelopes)
        if args.out:
            Path(args.out).write_text(output)
        else:
            sys.stdout.write(output)        # exact string — NOT print() (no extra newline; empty => nothing)
        return 0
    bundle = build_attestation_bundle(corpus, contract_index=index)
    _write_or_print(bundle.model_dump_json(by_alias=True, exclude_none=True), args.out)
    return 0


def _cmd_calibrate(args: argparse.Namespace) -> int:
    from .calibration_harness import run_calibration
    from .calibration_store import append_records, dump_models
    from polymer_protocol.calibration import GeneratingModelParams
    model = GeneratingModelParams(
        model_id="cli",
        n_per_group=args.n_per_group,
        n_probes_per_region=args.probes,
        effect_size=args.effect_size,
        dispersion=args.dispersion,
        fraction_true=args.fraction_true,
        tau=args.tau,
        target_fdr=args.q,
        n_generated=args.n,
        seed_set=(args.seed,),
    )
    ledger = run_calibration(model=model, n_batches=args.batches, base_seed=args.seed)
    if args.out:
        append_records(args.out, ledger.records)
        dump_models(args.out, ledger.generating_models)
    else:
        for r in ledger.records:
            sys.stdout.write(r.model_dump_json(exclude_none=True) + "\n")
    return 0


def _cmd_ingest_attested(args: argparse.Namespace) -> int:
    from .attested_ingest import ingest, parse_resolutions

    corpus = load_corpus(args.corpus)
    try:
        resolutions = parse_resolutions(Path(args.resolutions).read_text())
        out_corpus = ingest(corpus, resolutions, args.calibration)
    except ValueError as exc:
        print(f"ingest-attested failed: {exc}", file=sys.stderr)
        return 1
    _write_or_print(dump_corpus(out_corpus), args.out)
    print(f"ingested {len(resolutions)} attestation(s)", file=sys.stderr)
    return 0


def _cmd_verify_kernel(args: argparse.Namespace) -> int:
    if getattr(args, "real", False):
        return _verify_kernel_real(args)
    try:
        from .kernel_proof import run_synthetic_kernel_proof
    except ModuleNotFoundError as exc:
        if exc.name == "numpy":  # base install may lack numpy (the n-DMP gate adapters use it)
            print("verify-kernel needs numpy (the n-DMP gate adapters): install it with "
                  "`pip install 'polymer-claims[calibrate]'`", file=sys.stderr)
        else:  # a real internal import bug — don't mislabel it as a missing optional dep
            print(f"verify-kernel import failed: {exc}", file=sys.stderr)
        return 1
    r = run_synthetic_kernel_proof()
    tier = r.independence_tier.name if r.independence_tier is not None else "NONE"
    ok = r.licensed and tier == "REPRODUCED"
    print(f"kernel proof (synthetic, offline): {'LICENSED @ ' + tier if r.licensed else 'NOT LICENSED'}")
    print(f"  n_probes={r.n_probes}  null-floor k={r.k}  n_dmps={r.n_dmps}  e_value={r.e_value:.3e}")
    print("  (synthetic fixture — proves pipeline integrity, NOT the real biology; "
          "see docs/superpowers/2026-06-23-kernel-proof-runbook.md for the real proof)")
    return 0 if ok else 1


def _verify_kernel_real(args: argparse.Namespace) -> int:
    import os
    from pathlib import Path
    try:
        from .ingest._pinned import PinnedInputError
        from .real_kernel_proof import ParityError, load_pins, run_real_kernel_proof
    except ModuleNotFoundError as exc:
        if exc.name == "numpy":
            print("verify-kernel --real needs numpy (the n-DMP gate adapters): install it with "
                  "`pip install 'polymer-claims[calibrate]'`", file=sys.stderr)
        else:
            print(f"verify-kernel --real import failed: {exc}", file=sys.stderr)
        return 1
    pins = load_pins()
    cache_dir = Path(args.cache_dir) if args.cache_dir else (
        Path(os.environ.get("XDG_CACHE_HOME", str(Path.home() / ".cache")))
        / "polymer-claims" / "tcga_laml")
    try:
        r = run_real_kernel_proof(
            Path(args.xena) if args.xena else None,
            Path(args.cbioportal) if args.cbioportal else None,
            pins=pins, cache_dir=cache_dir, allow_fetch=args.fetch)
    except (PinnedInputError, ParityError, ValueError) as exc:
        # PinnedInputError: input resolution/checksum; ParityError: a pin mismatch;
        # ValueError: a builder self-check (controls / count-band / accounting) — all are clean failures.
        print(f"verify-kernel --real FAILED: {exc}", file=sys.stderr)
        return 1
    tier = r.independence_tier.name if r.independence_tier is not None else "NONE"
    ok = r.licensed and tier == "REPRODUCED"
    print(f"kernel proof (REAL @2): {'LICENSED @ ' + tier if r.licensed else 'NOT LICENSED'}")
    print(f"  n_probes={r.n_probes}  null-floor k={r.k}  n_dmps={r.n_dmps}  e_value={r.e_value:.3e}")
    print("  proves the pinned real-data computation reproduces — NOT data veracity / independence "
          "(that is roadmap H1.A2). See docs/superpowers/2026-06-23-kernel-proof-runbook.md")
    return 0 if ok else 1


def _sign_dep_error(exc: ModuleNotFoundError) -> int:
    if getattr(exc, "name", None) == "cryptography":
        print("signing needs the [sign] extra: pip install 'polymer-claims[sign]'", file=sys.stderr)
    else:
        print(f"signing import failed: {exc}", file=sys.stderr)
    return 1


def _parse_dsse_envelopes(text: str):
    """Parse a single DSSE-envelope JSON (compact OR pretty-printed) or an NDJSON of envelopes.
    Returns a list of DsseEnvelope, or None if the input is not parseable as either."""
    from pydantic import ValidationError

    from .attestation import DsseEnvelope
    stripped = text.strip()
    if not stripped:
        return []
    try:                                            # whole text = one envelope (handles pretty JSON)
        return [DsseEnvelope.model_validate_json(stripped)]
    except ValidationError:
        pass
    out = []                                        # else NDJSON: one compact envelope per line
    for ln in stripped.splitlines():
        if not ln.strip():
            continue
        try:
            out.append(DsseEnvelope.model_validate_json(ln))
        except ValidationError:
            return None
    return out


def _atomic_write(path: Path, data: bytes, *, mode: int) -> None:
    """Write `data` to `path` atomically at `mode`: a temp file in the same dir (chmod `mode`) then
    os.replace. Guarantees the final mode even when overwriting a differently-permissioned file
    (os.replace swaps in the temp's inode) and never writes through a symlink at `path`."""
    import tempfile
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp-", suffix=".tmp")
    try:
        os.fchmod(fd, mode)
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
        os.replace(tmp, str(path))
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _cmd_keygen(args: argparse.Namespace) -> int:
    try:
        from .signing import generate_keypair, serialize_private_pem, serialize_public_pem
        priv_k, pub_k = generate_keypair()
    except ModuleNotFoundError as exc:
        return _sign_dep_error(exc)
    key, pub = Path(args.key), Path(args.pub_key)
    # best-effort pre-check (NOT a concurrency-safe lock; a racing writer between here and the
    # writes below is possible — acceptable for a local CLI). --force skips it.
    if (key.exists() or pub.exists()) and not args.force:
        print(f"refusing to overwrite existing {key} / {pub} — use --force", file=sys.stderr)
        return 1
    try:
        _atomic_write(key, serialize_private_pem(priv_k), mode=0o600)
        _atomic_write(pub, serialize_public_pem(pub_k), mode=0o644)
    except OSError as exc:
        print(f"keygen: failed to write key files ({exc}); the key pair may be incomplete", file=sys.stderr)
        return 1
    print(f"wrote {key} (private, 0600) + {pub} (public)", file=sys.stderr)
    return 0


def _cmd_verify_dsse(args: argparse.Namespace) -> int:
    try:
        from .signing import load_public_key, verify_envelope
    except ModuleNotFoundError as exc:
        return _sign_dep_error(exc)
    try:
        public_key = load_public_key(Path(args.pub_key).read_bytes())
    except ModuleNotFoundError as exc:
        return _sign_dep_error(exc)
    except (ValueError, OSError) as exc:            # malformed PEM / unreadable file -> rc 1, no traceback
        print(f"verify-dsse: cannot load public key: {exc}", file=sys.stderr)
        return 1
    try:
        text = Path(args.path).read_text()
    except OSError as exc:
        print(f"verify-dsse: cannot read {args.path}: {exc}", file=sys.stderr)
        return 1
    envelopes = _parse_dsse_envelopes(text)
    if envelopes is None:
        print("verify-dsse: input is not a valid DSSE envelope or NDJSON of envelopes", file=sys.stderr)
        return 1
    if not envelopes:
        print("verify-dsse: no DSSE envelopes to verify", file=sys.stderr)
        return 1
    all_ok = True
    for i, env in enumerate(envelopes):
        ok = verify_envelope(env, public_key)
        all_ok = all_ok and ok
        print(f"  envelope[{i}]: {'VALID' if ok else 'INVALID'}", file=sys.stderr)
    print(f"verify-dsse: {'all signatures valid' if all_ok else 'INVALID signature(s)'}", file=sys.stderr)
    return 0 if all_ok else 1


def _cmd_certify(args: argparse.Namespace) -> int:
    if (args.key or args.keyid) and args.format != "dsse":
        print("certify: --key/--keyid apply only to --format dsse", file=sys.stderr)
        return 1
    from .attestation import build_certificate, render_certificate_text, certificate_dsse_envelope
    corpus = load_corpus(args.corpus)
    ledger = None
    if args.calibration:
        from .calibration_store import load_ledger
        ledger = load_ledger(args.calibration)
    cert = build_certificate(corpus, args.claim_id, ledger=ledger, target_q=args.q)
    if args.format == "json":
        out = cert.model_dump_json(by_alias=True, exclude_none=True)
    elif args.format == "dsse":
        env = certificate_dsse_envelope(cert)
        if args.key:
            try:
                from .signing import load_private_key, sign_envelope
            except ModuleNotFoundError as exc:
                return _sign_dep_error(exc)
            try:
                priv = load_private_key(Path(args.key).read_bytes())
            except ModuleNotFoundError as exc:
                return _sign_dep_error(exc)
            except (OSError, ValueError) as exc:        # unreadable / malformed PEM -> rc 1, no traceback
                print(f"certify: cannot load private key {args.key}: {exc}", file=sys.stderr)
                return 1
            env = sign_envelope(env, priv, keyid=args.keyid)
        out = env.model_dump_json(by_alias=True, exclude_none=True)
    else:
        out = render_certificate_text(cert)
    sys.stdout.write(out + "\n")
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
    # Calibration accrual (off by default → byte-identical): when --calibration is set, forward
    # the ledger path into the runner so each tick records ANCHORED warrant-survival resolutions.
    cal_kwargs: dict = {}
    if getattr(args, "calibration", None):
        cal_kwargs["calibration_path"] = args.calibration
        if getattr(args, "calibration_epoch", None):
            cal_kwargs["calibration_epoch_path"] = args.calibration_epoch
    if getattr(args, "tcga_laml", False):
        from .methyl_ndmp import NDmpOlsCoefAdapter, NDmpTTestAdapter, ndmp_independent_registry
        from .analysis_profile import profile_oracle_registry
        from .evidence import evidence_map
        from .materialization import materialization_map
        from .profiles import CANONICAL_HM450_V1
        from .exec_adapters import real_ndmp_seed_corpus
        corpus, seed_kwargs = real_ndmp_seed_corpus()
        runner = NodeRunner.from_seed(
            corpus,
            adapters=(NDmpTTestAdapter(), NDmpOlsCoefAdapter()),
            ctx=_CTX,
            scheduler_budget=args.budget,
            max_frames=args.max_frames,
            adapter_registry=ndmp_independent_registry(),
            oracles=profile_oracle_registry((CANONICAL_HM450_V1, "recomputable_public")),
            materializations=materialization_map(corpus, _CTX, profiles=(CANONICAL_HM450_V1,)),
            evidence=evidence_map(corpus),
            layout=args.layout,
            **seed_kwargs,
            **cal_kwargs,
        )
        app = create_app(runner, interval=args.interval, origins=args.origins or None)
        uvicorn.run(app, host=args.host, port=args.port)
        return 0
    if getattr(args, "real_data", False):
        try:
            proposer = _build_real_data_proposer(args.llm_model)
        except RuntimeError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        from .throttle import every_n_ticks
        from .exec_adapters import (
            StatsPureAdapter,
            StatsStdlibAdapter,
            apparatus_oracle_registry,
            independent_registry,
            real_data_seed_corpus,
        )
        proposer = every_n_ticks(proposer, n=args.llm_every)
        corpus, seed_kwargs = real_data_seed_corpus()
        runner = NodeRunner.from_seed(
            corpus,
            adapters=(StatsPureAdapter(), StatsStdlibAdapter()),
            ctx=_CTX,
            scheduler_budget=args.budget,
            max_frames=args.max_frames,
            adapter_registry=independent_registry(),
            oracles=apparatus_oracle_registry(),
            proposers=(proposer,),
            layout=args.layout,
            **seed_kwargs,
            **cal_kwargs,
        )
        app = create_app(runner, interval=args.interval, origins=args.origins or None)
        uvicorn.run(app, host=args.host, port=args.port)
        return 0
    if getattr(args, "methyl_data", False):
        try:
            proposer = _build_methyl_proposer(args.llm_model)
        except RuntimeError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        from polymer_grammar import FDRLedger
        from .analysis_profile import profile_oracle_registry
        from .methyl_adapters import (
            RegionLmCoefAdapter,
            RegionMeanDiffAdapter,
            methyl_independent_registry,
        )
        from .methyl_ndmp import NDmpOlsCoefAdapter, NDmpTTestAdapter, ndmp_independent_registry
        from .profiles import CANONICAL_EPICV2_V1, CANONICAL_HM450_V1
        from .throttle import every_n_ticks

        reg_a = methyl_independent_registry()
        reg_b = ndmp_independent_registry()
        from polymer_protocol import AdapterRegistry
        adapter_registry = AdapterRegistry(credentials=reg_a.credentials + reg_b.credentials)
        proposer = every_n_ticks(proposer, n=args.llm_every)
        corpus = Corpus(fdr_ledger=FDRLedger(target_fdr=0.05))
        runner = NodeRunner.from_seed(
            corpus,
            adapters=(
                RegionMeanDiffAdapter(),
                RegionLmCoefAdapter(),
                NDmpTTestAdapter(),
                NDmpOlsCoefAdapter(),
            ),
            ctx=_CTX,
            scheduler_budget=args.budget,
            max_frames=args.max_frames,
            adapter_registry=adapter_registry,
            oracles=profile_oracle_registry(
                (CANONICAL_EPICV2_V1, "recomputable_public"),
                (CANONICAL_HM450_V1, "recomputable_public"),
            ),
            proposers=(proposer,),
            content_address=True,
            evalue_gate=True,
            profiles=(CANONICAL_EPICV2_V1, CANONICAL_HM450_V1),
            layout=args.layout,
            budget=2.5,
            **cal_kwargs,
        )
        app = create_app(runner, interval=args.interval, origins=args.origins or None)
        uvicorn.run(app, host=args.host, port=args.port)
        return 0
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
            layout=args.layout,
            **seed_kwargs,
            **cal_kwargs,
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
            corpus, scheduler_budget=args.budget, max_frames=args.max_frames, layout=args.layout,
            **kwargs, **cal_kwargs,
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

    p_ingest = sub.add_parser("ingest", help="fetch + transform a real dataset into a local SE-Contract")
    p_ingest.add_argument("dataset", choices=("tcga-laml",), help="which dataset to ingest")
    p_ingest.add_argument("--data-dir", default="./data/tcga_laml", help="local cache dir for raw GDC files (gitignored)")
    p_ingest.set_defaults(func=_cmd_ingest)

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

    p_cons = sub.add_parser("export-consistency", help="emit a ConsistencyReport (sheaf gauge) — needs [embed]")
    p_cons.add_argument("corpus", help="path to a corpus JSON file")
    p_cons.add_argument("--out", default=None, help="write ConsistencyReport JSON here")
    p_cons.set_defaults(func=_cmd_export_consistency)

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
    p_serve.add_argument(
        "--calibration",
        default=None,
        help="write a calibration ledger here (append-only JSONL of ANCHORED warrant-survival "
        "records) — enables live calibration accrual on the running node; off by default",
    )
    p_serve.add_argument(
        "--calibration-epoch",
        default=None,
        help="epoch-state JSON path (default: epoch_state.json beside --calibration)",
    )
    p_serve.add_argument("--llm", action="store_true", help="drive GENERATE with a real LLM agent (needs the [llm] extra + ANTHROPIC_API_KEY)")
    p_serve.add_argument("--real-data", action="store_true", help="LLM proposes REAL-DATA mean_diff plans; node runs the local execution adapters + apparatus oracle (needs [llm] + ANTHROPIC_API_KEY)")
    p_serve.add_argument("--methyl-data", action="store_true", help="LLM proposes executable methylation claims over SE-Contracts; node runs methylation adapters + e-value gate (needs [llm] + ANTHROPIC_API_KEY)")
    p_serve.add_argument("--tcga-laml", action="store_true", help="seed the live node with the REAL TCGA-LAML genome-wide n-DMP claim (ingest first; one-shot compute, then displays)")
    p_serve.add_argument("--llm-model", default="claude-sonnet-4-6", help="model for --llm")
    p_serve.add_argument("--llm-every", type=int, default=4, help="LLM proposes every Nth tick (throttle)")
    p_serve.add_argument(
        "--layout",
        choices=("spectral", "force"),
        default="spectral",
        help="live layout: spectral (signed-Laplacian eigenmap, Procrustes-aligned; default) or force (Fruchterman-Reingold)",
    )
    p_serve.set_defaults(func=_cmd_serve)

    p_att = sub.add_parser(
        "export-attestation",
        help="emit an in-toto/SLSA attestation bundle (+ DRS objects) for a corpus's LICENSED claims",
    )
    p_att.add_argument("corpus", help="path to a corpus JSON file")
    p_att.add_argument("--out", default=None, help="write the attestation bundle JSON here")
    p_att.add_argument("--format", choices=("bundle", "dsse"), default="bundle",
                       help="bundle (default) or dsse (NDJSON of DSSE envelopes; unsigned by default, use --key to sign)")
    p_att.add_argument("--key", default=None, help="ed25519 private key PEM; sign each DSSE envelope (dsse format only)")
    p_att.set_defaults(func=_cmd_export_attestation)

    p_cal = sub.add_parser("calibrate", help="run the synthetic DEFINITIONAL calibration harness")
    p_cal.add_argument("--synthetic", action="store_true", help="(only mode this slice)")
    p_cal.add_argument("--batches", type=int, default=30,
                       help="number of mixed synthetic batches (more → a tighter, more reliable CI)")
    p_cal.add_argument("--n", type=int, default=40, help="regions (claims) per batch")
    p_cal.add_argument("--q", type=float, default=0.05)
    p_cal.add_argument("--fraction-true", dest="fraction_true", type=float, default=0.6)
    p_cal.add_argument("--effect-size", dest="effect_size", type=float, default=0.30)
    p_cal.add_argument("--dispersion", type=float, default=25.0)
    p_cal.add_argument("--tau", type=float, default=0.10)
    p_cal.add_argument("--n-per-group", dest="n_per_group", type=int, default=40)
    p_cal.add_argument("--probes", type=int, default=6)
    p_cal.add_argument("--seed", type=int, default=0)
    p_cal.add_argument("--out", default=None, help="write the ledger JSONL here (else stdout)")
    p_cal.set_defaults(func=_cmd_calibrate)

    p_ing = sub.add_parser("ingest-attested",
                           help="ingest external determinations as ATTESTED calibration records")
    p_ing.add_argument("--corpus", required=True, help="path to the corpus JSON")
    p_ing.add_argument("--resolutions", required=True, help="path to the resolutions JSON array")
    p_ing.add_argument("--calibration", required=True, help="path to the calibration JSONL ledger")
    p_ing.add_argument("--out", help="write updated corpus here (default: stdout)")
    p_ing.set_defaults(func=_cmd_ingest_attested)

    p_cert = sub.add_parser("certify", help="emit a single-claim certificate (standing + calibrated q)")
    p_cert.add_argument("claim_id")
    p_cert.add_argument("--corpus", required=True, help="path to a corpus JSON file")
    p_cert.add_argument("--calibration", default=None, help="path to a calibration ledger JSONL")
    p_cert.add_argument("--q", type=float, default=0.05)
    p_cert.add_argument("--format", choices=("text", "json", "dsse"), default="text")
    p_cert.add_argument("--key", default=None, help="ed25519 private key PEM; sign the DSSE envelope (dsse format only)")
    p_cert.add_argument("--keyid", default=None, help="override the DSSE signature keyid")
    p_cert.set_defaults(func=_cmd_certify)

    p_vk = sub.add_parser("verify-kernel",
                          help="run the n-DMP kernel proof (synthetic offline by default; --real for the @2 parity gate)")
    p_vk.add_argument("--real", action="store_true",
                      help="run the REAL se:tcga_laml_idh@2 parity gate (needs the pinned Xena matrix + cBioPortal inputs)")
    p_vk.add_argument("--xena", default=None,
                      help="TCGA-LAML.methylation450.tsv.gz (file path, or a dir containing it)")
    p_vk.add_argument("--cbioportal", default=None,
                      help="dir holding data_mutations.txt + sequenced_samples.json")
    p_vk.add_argument("--cache-dir", default=None, help="cache dir for resolved pinned inputs")
    p_vk.add_argument("--fetch", action="store_true",
                      help="opt-in: allow network download of pinned inputs (off by default)")
    p_vk.set_defaults(func=_cmd_verify_kernel)

    p_kg = sub.add_parser("keygen", help="generate an ed25519 keypair (PEM) for DSSE signing")
    p_kg.add_argument("--key", required=True, help="output path for the private key PEM")
    p_kg.add_argument("--pub-key", required=True, help="output path for the public key PEM")
    p_kg.add_argument("--force", action="store_true", help="overwrite existing key files")
    p_kg.set_defaults(func=_cmd_keygen)

    p_vd = sub.add_parser("verify-dsse", help="verify a signed DSSE envelope (or NDJSON) against a public key")
    p_vd.add_argument("path", help="path to a DSSE envelope JSON or NDJSON of envelopes")
    p_vd.add_argument("--pub-key", required=True, help="path to the signer's public key PEM")
    p_vd.set_defaults(func=_cmd_verify_dsse)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
