from polymer_claims.synbio.manifest import ManifestEntry, load_manifest
from polymer_claims.synbio.gap_ledger import aggregate_gaps, CANONICAL_GAP_KINDS


def _entry(id, status, constraint=None, cls=None, gap_kind=None):
    return ManifestEntry.model_validate({
        "id": id, "title": id, "tier": 1, "topic": "computing",
        "leaf": {"kind": "quantity"}, "source": "PLM-VI",
        "schema_fit": {"status": status, "constraint": constraint,
                       "expansion_class": cls, "gap_kind": gap_kind,
                       "current_ir_behavior": "x", "candidate_resolution": "y",
                       "purity_cost": "z"},
    })


def test_tagged_kinds_get_canonical_numbers_and_dedup_across_paraphrases():
    entries = [
        _entry("a", "clean"),
        _entry("b", "gap", "worded one way",     "domain",  gap_kind="analytic-basis"),
        _entry("c", "gap", "worded ANOTHER way", "domain",  gap_kind="analytic-basis"),  # same kind, diff prose
        _entry("d", "gap", "x",                  "subject", gap_kind="gene-locus-context"),
    ]
    gaps = aggregate_gaps(entries)
    # b and c collapse (same gap_kind despite different prose); numbers are canonical, not renumbered.
    assert [g.id for g in gaps] == ["GAP-7", "GAP-8"]
    assert gaps[0].gap_kind == "analytic-basis"


def test_untagged_falls_back_to_prose_key_and_non_colliding_numbers():
    entries = [
        _entry("b", "gap", "no half-life field", "general"),
        _entry("c", "gap", "no half-life field", "general"),   # dup of b (prose)
        _entry("d", "gap", "no ontology slot",   "subject"),
    ]
    gaps = aggregate_gaps(entries)
    ids = [g.id for g in gaps]
    assert len(ids) == 2                                        # deduped by prose
    canon_max = max(int(v.split("-", 1)[1]) for v in CANONICAL_GAP_KINDS.values())
    assert all(int(i.split("-", 1)[1]) > canon_max for i in ids)  # never collide with GAP-1..15


def test_unknown_tagged_kind_gets_fresh_number():
    gaps = aggregate_gaps([_entry("z", "gap", "novel", "general", gap_kind="totally-new-kind")])
    assert len(gaps) == 1 and gaps[0].id.startswith("GAP-")
    assert gaps[0].gap_kind == "totally-new-kind"


def test_real_manifests_aggregate_to_canonical_ids():
    from pathlib import Path
    paths = sorted((Path(__file__).resolve().parents[2]
                    / "data/synbio_compendia/manifests").glob("*.json"))
    gaps = aggregate_gaps([e for p in paths for e in load_manifest(p)])
    assert {g.id for g in gaps} == {"GAP-7", "GAP-8", "GAP-11", "GAP-13", "GAP-14", "GAP-15"}
    assert all(g.gap_kind for g in gaps)   # every surviving gap is now tagged
