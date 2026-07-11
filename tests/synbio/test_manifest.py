from pathlib import Path
from polymer_claims.synbio.manifest import load_manifest, ManifestEntry

_FIX = Path(__file__).parent / "fixtures" / "mini_manifest.json"

def test_load_manifest_parses_entries():
    entries = load_manifest(_FIX)
    assert len(entries) == 2
    assert all(isinstance(e, ManifestEntry) for e in entries)

def test_skip_and_tier_preserved():
    entries = load_manifest(_FIX)
    by_id = {e.id: e for e in entries}
    assert by_id["sb-plm06-toggle-leak"].skip is False
    assert by_id["sb-plm06-narrative"].skip is True
    assert by_id["sb-plm06-narrative"].tier == 3

def test_schema_fit_required():
    entries = load_manifest(_FIX)
    assert entries[0].schema_fit.status == "clean"
