from pathlib import Path

from polymer_claims.synbio.ingest import build_manifest_claims
from polymer_grammar.status import Status

_MANIFESTS = sorted((Path(__file__).resolve().parents[2]
                     / "data/synbio_compendia/manifests").glob("*.json"))


def test_all_manifest_claims_build_and_are_conjectured():
    assert _MANIFESTS, "no manifests found"
    claims, topics = build_manifest_claims(_MANIFESTS)
    assert len(claims) >= 20                     # a real ramp beyond the 5 probe claims
    assert all(c.status is Status.CONJECTURED for c in claims)
    assert all(cid in topics for cid in (c.id for c in claims))


def test_manifest_ids_unique():
    claims, _ = build_manifest_claims(_MANIFESTS)
    ids = [c.id for c in claims]
    assert len(ids) == len(set(ids))
