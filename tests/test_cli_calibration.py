"""CLI tests for the `calibrate` and `certify` subcommands."""
from __future__ import annotations

import subprocess
import sys

from polymer_grammar import CategoricalLeaf, Claim, FDRLedger, PatternRef, Status
from polymer_grammar.licensing import (
    LicenseRoute,
    Licensing,
    MaterializationContext,
    RivalSetClosure,
    Satisfaction,
    SatisfactionVerdict,
)
from polymer_protocol import Corpus


# ---------------------------------------------------------------------------
# helpers — build a tiny licensed corpus on-the-fly and serialise to tmp
# ---------------------------------------------------------------------------
_PATTERN = PatternRef(id="adjusted_effect", version="v1")


def _mc() -> MaterializationContext:
    return MaterializationContext(
        id="M",
        api_version="v1",
        data_version="d1",
        dimnames_hash="sha256:" + "a" * 64,
        profile_hash="sha256:" + "b" * 64,
        semantic_run_id="r1",
    )


def _licensed_claim(cid: str) -> Claim:
    sat = Satisfaction(
        verdict=SatisfactionVerdict.SATISFIED,
        materialization=_mc(),
        credential_ids=(),
    )
    lic = Licensing(
        route=LicenseRoute.SEVERE_TEST,
        satisfactions=(sat,),
        rival_set_closure=RivalSetClosure.ENUMERATED,
        rivals_considered=("self",),
    )
    return Claim(
        id=cid,
        title=f"claim {cid}",
        pattern=_PATTERN,
        leaves=(CategoricalLeaf(ontology_term=f"term-{cid}"),),
        status=Status.LICENSED,
        licensing=lic,
    )


def _licensed_corpus() -> Corpus:
    return Corpus(
        claims=(_licensed_claim("c1"),),
        fdr_ledger=FDRLedger(target_fdr=0.05),
    )


def _run(*args):
    return subprocess.run(
        [sys.executable, "-m", "polymer_claims.cli", *args],
        capture_output=True,
        text=True,
    )


# ---------------------------------------------------------------------------
# test_calibrate_writes_a_ledger
# ---------------------------------------------------------------------------
def test_calibrate_writes_a_ledger(tmp_path):
    out = tmp_path / "ledger.jsonl"
    r = _run(
        "calibrate",
        "--synthetic",
        "--batches", "3",
        "--n", "6",
        "--q", "0.05",
        "--out", str(out),
    )
    assert r.returncode == 0, r.stderr
    assert out.is_file() and out.read_text().strip()  # at least one record line


# ---------------------------------------------------------------------------
# test_certify_text_has_headline
# ---------------------------------------------------------------------------
def test_certify_text_has_headline(tmp_path):
    # build a tiny ledger first
    ledger = tmp_path / "l.jsonl"
    _run(
        "calibrate",
        "--synthetic",
        "--batches", "3",
        "--n", "6",
        "--q", "0.05",
        "--out", str(ledger),
    )

    # write a licensed corpus to a tmp file
    corpus_path = tmp_path / "corpus.json"
    corpus_path.write_text(_licensed_corpus().model_dump_json())

    r = _run(
        "certify", "c1",
        "--corpus", str(corpus_path),
        "--calibration", str(ledger),
        "--q", "0.05",
    )
    assert r.returncode == 0, r.stderr
    assert "Corpus target q" in r.stdout
