import ast
import subprocess
import sys
from pathlib import Path
import polymer_grammar.capability as cap

def test_no_numpy_after_import():
    code = "import sys, polymer_grammar.capability; assert 'numpy' not in sys.modules"
    assert subprocess.run([sys.executable, "-c", code]).returncode == 0

def test_no_forbidden_dependencies():
    # Forbidden-dependency check (not a complete stdlib allowlist): capability.py must not import the
    # umbrella, the protocol, the legacy IR, or numpy.
    tree = ast.parse(Path(cap.__file__).read_text())
    mods = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            mods.append(node.module)
        elif isinstance(node, ast.Import):
            mods.extend(a.name for a in node.names)
    for m in mods:
        assert not m.startswith("polymer_claims"), m
        assert not m.startswith("polymer_protocol"), m
        assert not m.startswith("polymer_formalclaim"), m
        assert m != "numpy" and not m.startswith("numpy."), m
