"""OptoCART Ch4 recurrence table — materialized reported claims from the curated screen docs."""
from __future__ import annotations

from polymer_grammar.provenance import GenerationMode
from polymer_grammar.status import Status

from polymer_claims.optocart_tables import ch4_recurrence_claims


def test_ch4_recurrence_is_two_stratum_and_cited():
    claims = ch4_recurrence_claims()
    by_id = {c.id: c for c in claims}
    assert "ch4-asxl1-dupg" in by_id and "ch4-jak2-v617f-pv" in by_id
    for c in claims:
        assert c.status is Status.CONJECTURED                              # two-stratum reported
        assert c.provenance.generated_by is GenerationMode.LITERATURE_EXTRACTED
        assert c.provenance.method                                          # a source doc is recorded
        assert 0.0 <= c.leaves[0].value <= 1.0                              # a recurrence fraction


def test_ch4_values_and_ranges_match_the_docs():
    by_id = {c.id: c for c in ch4_recurrence_claims()}
    assert by_id["ch4-asxl1-dupg"].leaves[0].value == 0.40
    assert by_id["ch4-jak2-v617f-pv"].leaves[0].value == 0.95
    npm1 = by_id["ch4-npm1-typea"].leaves[0]
    assert npm1.low == 0.30 and npm1.high == 0.35                           # 30–35% range carried honestly
    # disease context is attached, not fabricated into the value.
    assert by_id["ch4-asxl1-dupg"].leaves[0].context.condition == "ASXL1 CHIP"
