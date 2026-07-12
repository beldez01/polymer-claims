from polymer_claims.synbio.manifest import ManifestEntry
from polymer_claims.synbio.gap_ledger import aggregate_gaps

def _entry(id, status, constraint=None, cls=None):
    return ManifestEntry.model_validate({
        "id": id, "title": id, "tier": 1, "topic": "computing",
        "leaf": {"kind": "quantity"}, "source": "PLM-VI",
        "schema_fit": {"status": status, "constraint": constraint,
                       "expansion_class": cls, "current_ir_behavior": "x",
                       "candidate_resolution": "y", "purity_cost": "z"},
    })

def test_gaps_deduped_and_numbered_from_5():
    entries = [
        _entry("a", "clean"),
        _entry("b", "gap", "no half-life field", "general"),
        _entry("c", "gap", "no half-life field", "general"),   # dup of b
        _entry("d", "gap", "no ontology slot for chassis", "subject"),
    ]
    gaps = aggregate_gaps(entries, start_index=5)
    assert [g.id for g in gaps] == ["GAP-5", "GAP-6"]           # deduped to 2
    assert gaps[0].constraint == "no half-life field"
