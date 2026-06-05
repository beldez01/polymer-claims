"""Polymer Claims umbrella — a thin CLI over the `polymer_grammar` IR and the
`polymer_protocol` runtime. `pip install polymer-claims` pulls both transitively.

Convenience re-exports keep the umbrella import surface small but useful for a
local-node embedder: the grammar `Claim`, the protocol `Corpus`, and the headline
runtime entry points.
"""
from __future__ import annotations

__version__ = "0.1.0"

# Convenience re-exports (optional; the heavy lifting lives in the two component
# packages). Kept lazy-free — both deps are declared, so the imports always resolve.
from polymer_grammar import Claim
from polymer_protocol import Corpus, next_action, run_cycle

__all__ = [
    "Claim",
    "Corpus",
    "__version__",
    "next_action",
    "run_cycle",
]
