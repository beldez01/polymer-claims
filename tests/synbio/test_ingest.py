from pathlib import Path
from polymer_claims.synbio.manifest import load_manifest
from polymer_claims.synbio.ingest import build_claim, build_manifest_claims
from polymer_grammar.leaf import QuantityLeaf, MeasurementBasis
from polymer_grammar.provenance import GenerationMode
from polymer_grammar.status import Status

_FIX = Path(__file__).parent / "fixtures" / "mini_manifest.json"

def test_build_quantity_claim_is_conjectured_derived():
    entry = next(e for e in load_manifest(_FIX) if e.id == "sb-plm06-toggle-leak")
    c = build_claim(entry)
    leaf = c.leaves[0]
    assert isinstance(leaf, QuantityLeaf)
    assert leaf.measurement_basis is MeasurementBasis.DERIVED
    assert leaf.unit is None and leaf.formula
    assert c.status is Status.CONJECTURED
    assert c.pattern.id == "reported_quantity"
    assert c.provenance.generated_by is GenerationMode.LITERATURE_EXTRACTED

def test_build_manifest_claims_skips_tier3():
    claims, topics = build_manifest_claims([_FIX])
    ids = {c.id for c in claims}
    assert "sb-plm06-toggle-leak" in ids
    assert "sb-plm06-narrative" not in ids           # tier-3 AND skip (conflated)
    assert "sb-plm06-skip-only" not in ids           # skip-only: tier=1 would pass, skip must exclude
    assert "sb-plm06-tier3-only" not in ids          # tier-only: skip=false would pass, tier must exclude
    assert topics["sb-plm06-toggle-leak"] == "computing"
