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
