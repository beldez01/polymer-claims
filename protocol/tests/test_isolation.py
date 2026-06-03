"""Guard the one-way boundary: polymer_grammar must NOT depend on polymer_protocol."""
from __future__ import annotations

import pathlib
import re

# protocol/tests/ -> protocol/ -> polymer-claims/ -> grammar/src/polymer_grammar
GRAMMAR_SRC = (
    pathlib.Path(__file__).resolve().parent.parent.parent
    / "grammar"
    / "src"
    / "polymer_grammar"
)

_IMPORT_RE = re.compile(
    r"^\s*(import\s+polymer_protocol|from\s+polymer_protocol)",
    re.MULTILINE,
)


def test_grammar_does_not_import_protocol():
    offenders = []
    for py in GRAMMAR_SRC.rglob("*.py"):
        if _IMPORT_RE.search(py.read_text(encoding="utf-8")):
            offenders.append(py.name)
    assert offenders == [], f"grammar must not import polymer_protocol; offenders: {offenders}"


def test_protocol_can_import_grammar():
    import polymer_grammar  # one-way dependency is allowed

    assert polymer_grammar.__version__
