"""Guard the containment boundary: polymer_grammar must not depend on the v1.2 IR OR on the
polymer_protocol runtime (the one-way isolation — protocol depends on grammar, never the reverse)."""
from __future__ import annotations

import pathlib
import re

SRC = pathlib.Path(__file__).resolve().parent.parent / "src" / "polymer_grammar"

# Match actual import statements only — not prose mentions in docstrings/comments.
# Covers:
#   import polymer_formalclaim
#   from polymer_formalclaim import ...
#   import formalclaim
#   from formalclaim import ...  (but NOT "isolated from formalclaim" in prose)
_IMPORT_RE = re.compile(
    r"^\s*(import\s+polymer_formalclaim"
    r"|from\s+polymer_formalclaim"
    r"|import\s+formalclaim\b"
    r"|from\s+formalclaim\s+import)",
    re.MULTILINE,
)

# The one-way boundary: grammar must never import the protocol runtime (an actual import, not prose).
_PROTOCOL_IMPORT_RE = re.compile(
    r"^\s*(import\s+polymer_protocol\b|from\s+polymer_protocol\s+import)",
    re.MULTILINE,
)


def test_no_import_of_formalclaim_anywhere_in_package():
    offenders = []
    for py in SRC.rglob("*.py"):
        text = py.read_text(encoding="utf-8")
        if _IMPORT_RE.search(text):
            offenders.append(py.name)
    assert offenders == [], f"v1.3 grammar must stay isolated; offenders: {offenders}"


def test_no_import_of_protocol_anywhere_in_package():
    offenders = []
    for py in SRC.rglob("*.py"):
        text = py.read_text(encoding="utf-8")
        if _PROTOCOL_IMPORT_RE.search(text):
            offenders.append(py.name)
    assert offenders == [], f"grammar must never import polymer_protocol (one-way isolation); offenders: {offenders}"
