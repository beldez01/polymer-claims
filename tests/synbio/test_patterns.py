def test_sense_and_kill_registered_from_umbrella():
    import polymer_claims.synbio.patterns  # noqa: F401 — import registers the pattern
    from polymer_grammar.pattern import get_pattern

    p = get_pattern("sense_and_kill", "v1")
    assert p.excluded_applications


def test_pure_grammar_does_not_know_sense_and_kill():
    # domain pattern must NOT be written into the pure grammar source
    from pathlib import Path

    src = Path(__file__).resolve().parents[2] / "grammar/src/polymer_grammar/pattern.py"
    assert "sense_and_kill" not in src.read_text()


def test_c1_uses_registered_pattern():
    from polymer_claims.synbio.claims import mismatch_energy_claim

    c = mismatch_energy_claim()
    assert c.pattern.id == "reported_quantity" and c.pattern.version == "v1"
