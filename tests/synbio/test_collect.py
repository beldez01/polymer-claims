"""collect_all_synbio_claims: the 5 probe claims + every non-skipped manifest claim, with
a merged topic map covering every returned claim id."""
from __future__ import annotations


def test_collect_all_includes_probe_and_manifest_claims():
    from polymer_claims.synbio.ingest import collect_all_synbio_claims
    claims, topics = collect_all_synbio_claims()
    ids = {c.id for c in claims}
    assert "synbio-c1-mismatch-energy" in ids            # probe claim
    assert len(claims) >= 25                             # 5 probe + >=20 manifest
    assert all(c.id in topics for c in claims)
