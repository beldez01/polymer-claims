"""polymer-formalclaim — FormalClaim IR v1.2 + evaluator + materialization + nanopub.

Ship of the canonical FormalClaim Intermediate Representation: pydantic
models for the 5-tuple ⟨Premises, Operations, Statistics, Inference,
Conclusion⟩ with a v1.2 polymorphic subject slot, the three-valued
inference evaluator, the operation-DAG materialization dispatcher, and a
deterministic TriG Nanopublications projection.

This package is the **canonical source** of the FormalClaim IR. The
PolymerGenomicsAPI monorepo at ``src/polymer_genomics/formal_claims/``
still vendors its own copy (dedup deferred); once this package is on
PyPI, the API will depend on it instead.

Contents:
    * ``schema``     — pydantic models (FormalClaim, SubjectRef, …)
    * ``evaluate``   — inference-tree evaluator, EvaluationResult payload
    * ``materialize`` — dispatch + eligibility + drift reporting
    * ``nanopub``    — FormalClaim → TriG deterministic projection
    * ``cli``        — ``polymer-formalclaim`` CLI entrypoint
    * ``mcp_server`` — ``polymer-formalclaim-mcp`` MCP server entrypoint
"""

from polymer_formalclaim._version import __version__
from polymer_formalclaim.schema import FormalClaim
from polymer_formalclaim.evaluate import evaluate, EvaluationResult

__all__ = ["__version__", "FormalClaim", "evaluate", "EvaluationResult"]
