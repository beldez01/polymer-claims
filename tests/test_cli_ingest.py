from __future__ import annotations

from polymer_claims.cli import _build_parser


def test_ingest_tcga_laml_subcommand_parses():
    parser = _build_parser()
    args = parser.parse_args(["ingest", "tcga-laml", "--data-dir", "/tmp/x"])
    assert args.command == "ingest"
    assert args.dataset == "tcga-laml"
    assert args.data_dir == "/tmp/x"
    assert callable(args.func)
