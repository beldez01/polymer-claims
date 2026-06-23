import pytest
from polymer_claims.attested_ingest import (
    Resolution, parse_resolutions, validate_against_corpus,
)
from tests.attestation._fixtures import licensed_claim, licensing, corpus_with, mc, sat


@pytest.fixture
def licensing_corpus_fixture():
    # Licensing requires >= 1 Satisfaction; build a minimal one via the fixture helpers.
    return corpus_with(licensed_claim("c1", licensing(sat(mc()))))


def test_parse_minimal_row():
    text = '[{"subject_claim_id": "c1", "verdict": "failed", "attestation_ref": "doi:x"}]'
    rows = parse_resolutions(text)
    assert len(rows) == 1
    r = rows[0]
    assert r.subject_claim_id == "c1" and r.verdict == "failed"
    assert r.resolvability is None and r.license_epoch == 0


def test_parse_rejects_unknown_field():
    text = '[{"subject_claim_id": "c1", "verdict": "failed", "attestation_ref": "x", "bogus": 1}]'
    with pytest.raises(ValueError):
        parse_resolutions(text)


def test_parse_rejects_bad_verdict():
    text = '[{"subject_claim_id": "c1", "verdict": "maybe", "attestation_ref": "x"}]'
    with pytest.raises(ValueError):
        parse_resolutions(text)


def test_parse_rejects_negative_epoch():
    text = ('[{"subject_claim_id": "c1", "verdict": "failed", "attestation_ref": "x",'
            ' "license_epoch": -1}]')
    with pytest.raises(ValueError):
        parse_resolutions(text)


from polymer_grammar import GenerationMode
from polymer_grammar.claim import Status
from polymer_claims.attested_ingest import attested_event_claim, inject_attested_event


def _res(**kw):
    base = dict(subject_claim_id="c1", verdict="failed", attestation_ref="doi:10.1056/x")
    base.update(kw)
    return Resolution(**base)


def test_attested_event_claim_is_conjectured_and_unlicensed():
    c = attested_event_claim(_res())
    assert c.status == Status.CONJECTURED
    assert c.licensing is None
    assert c.provenance.generated_by is GenerationMode.EXTERNAL_ATTESTATION
    assert c.provenance.method == "doi:10.1056/x"
    assert "c1" in c.leaves[0].data and "failed" in c.leaves[0].data


def test_attested_event_claim_id_is_deterministic():
    assert attested_event_claim(_res()).id == attested_event_claim(_res()).id
    assert attested_event_claim(_res()).id != attested_event_claim(_res(verdict="upheld")).id


def test_inject_appends_without_relicensing(licensing_corpus_fixture):
    corpus = licensing_corpus_fixture            # a corpus with >=1 LICENSED claim
    before = {c.id: c.status for c in corpus.claims}
    c = attested_event_claim(_res())
    out = inject_attested_event(corpus, c)
    assert c.id in out.by_id()
    assert out.by_id()[c.id].licensing is None        # forced non-LICENSED
    # no other claim's status changed (instrument, not a gate)
    assert {k: out.by_id()[k].status for k in before} == before
    assert len(out.claims) == len(corpus.claims) + 1


# ── Task 7: build_attested_record + ingest ────────────────────────────────────

from polymer_protocol.calibration import (
    ResolutionKind, CalibrationTarget, ResolutionVerdict, Resolvability,
)
from polymer_claims.calibration_store import load_ledger   # load_ledger lives in the umbrella store
from polymer_claims.attested_ingest import build_attested_record, ingest


def test_record_links_event_claim_and_maps_verdict(licensing_corpus_fixture):
    corpus = licensing_corpus_fixture
    subject = corpus.by_id()["c1"]
    res = _res(verdict="failed")
    event = attested_event_claim(res)
    rec = build_attested_record(res, subject, event, stated_q=corpus.fdr_ledger.target_fdr)
    assert rec.resolution_kind == ResolutionKind.ATTESTED
    assert rec.calibration_target == CalibrationTarget.EXTERNAL_DISAGREEMENT
    assert rec.verdict == ResolutionVerdict.FAILED
    assert rec.source_claim_id == event.id
    assert rec.attestation_ref == "doi:10.1056/x"
    assert rec.feeds_headline_q is False


def test_resolvability_override_beats_prior(licensing_corpus_fixture):
    corpus = licensing_corpus_fixture
    subject = corpus.by_id()["c1"]                       # LICENSED claim, plan may be None
    res = _res(resolvability="resolvable")
    rec = build_attested_record(res, subject, attested_event_claim(res),
                                stated_q=corpus.fdr_ledger.target_fdr)
    assert rec.resolvability is Resolvability.RESOLVABLE  # operator wins regardless of prior


def test_ingest_appends_to_ledger_and_corpus(licensing_corpus_fixture, tmp_path):
    corpus = licensing_corpus_fixture
    ledger_path = tmp_path / "calib.jsonl"
    out = ingest(corpus, [_res()], ledger_path)
    # event claim now in corpus
    assert any(c.id.startswith("attest-") for c in out.claims)
    # one ATTESTED record in the ledger, linked to the event claim
    led = load_ledger(ledger_path)
    assert len(led.records) == 1
    rec = led.records[0]
    assert rec.resolution_kind == ResolutionKind.ATTESTED
    assert rec.source_claim_id in out.by_id()


# ── Task 7, Step 5: multi-source + idempotency (fold-key bug) ─────────────────

def test_two_sources_same_claim_both_survive(licensing_corpus_fixture, tmp_path):
    corpus = licensing_corpus_fixture
    ledger_path = tmp_path / "calib.jsonl"
    # two DIFFERENT external sources assess the same claim/epoch -> two distinct events
    rows = [
        _res(attestation_ref="doi:source-A", verdict="failed"),
        _res(attestation_ref="doi:source-B", verdict="upheld"),
    ]
    ingest(corpus, rows, ledger_path)
    led = load_ledger(ledger_path)
    assert len(led.records) == 2                       # neither folds away
    assert len({r.source_claim_id for r in led.records}) == 2


def test_reingest_same_resolution_is_idempotent(licensing_corpus_fixture, tmp_path):
    corpus = licensing_corpus_fixture
    ledger_path = tmp_path / "calib.jsonl"
    out1 = ingest(corpus, [_res()], ledger_path)
    ingest(out1, [_res()], ledger_path)                # run again, same determination
    led = load_ledger(ledger_path)
    assert len(led.records) == 1                       # content-addressed id folds to one
    assert len({r.source_claim_id for r in led.records}) == 1  # single content-addressed event


# ── Task 7, review fix: both-None discriminator invariant ─────────────────────

from polymer_claims.calibration_store import append_records
from polymer_protocol.calibration import ResolutionRecord


def test_fold_collapses_source_and_ref_less_attested_records(tmp_path):
    """Documents and locks the accepted behavior: ATTESTED records where both
    source_claim_id and attestation_ref are None share a None discriminator and
    therefore collapse to a single ledger entry (latest verdict wins).  This is
    accepted behavior because source-less attestations carry no event identity —
    there is nothing to distinguish them with, so folding is correct."""
    ledger_path = tmp_path / "calib.jsonl"
    rec_failed = ResolutionRecord(
        subject_claim_id="c1",
        license_epoch=0,
        resolution_kind=ResolutionKind.ATTESTED,
        calibration_target=CalibrationTarget.EXTERNAL_DISAGREEMENT,
        verdict=ResolutionVerdict.FAILED,
        stated_q=0.05,
        observed_at_cycle=0,
        source_claim_id=None,
        attestation_ref=None,
    )
    rec_upheld = ResolutionRecord(
        subject_claim_id="c1",
        license_epoch=0,
        resolution_kind=ResolutionKind.ATTESTED,
        calibration_target=CalibrationTarget.EXTERNAL_DISAGREEMENT,
        verdict=ResolutionVerdict.UPHELD,
        stated_q=0.05,
        observed_at_cycle=0,
        source_claim_id=None,
        attestation_ref=None,
    )
    append_records(ledger_path, [rec_failed, rec_upheld])
    led = load_ledger(ledger_path)
    # Both records share discriminator=None → they collapse; latest (UPHELD) wins.
    assert len(led.records) == 1
