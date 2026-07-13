"""The discrimination e-value for the expression-floor spine: a betting e-value
(evidence.betting_evalue) on the between-group gap, fusion+ vs fusion-, TPM rescaled into [0,1] by a
pre-registered CAP (boundedness is load-bearing for validity). This carries the DISCRIMINATION; the
13 TPM FLOOR is carried separately by the leg criterion (do NOT merge them — see the ACTB control)."""
from __future__ import annotations

from polymer_grammar import Comparator, OperationNode

from .evidence import betting_evalue
from .expression_floor_adapters import _expr_split

FLOOR = 13.0     # criterion floor (used by the claim leaf, not here) — pre-registered
CAP = 100.0      # rescaling constant: TPM/CAP into [0,1] (betting_evalue clips) — pre-registered
NULL_GAP = 0.1   # e-value null discrimination margin in [0,1] units — pre-registered


def _gap_evalue(pos: list[float], neg: list[float], *, cap: float = CAP, null_gap: float = NULL_GAP) -> float:
    """betting_evalue tests E[b-a] > null_gap with a,b in [0,1]. a = fusion_neg/cap, b = fusion_pos/cap,
    so a positive shift = fusion+ expresses higher. Bounded by the /cap + internal clip."""
    a = [v / cap for v in neg]
    b = [v / cap for v in pos]
    return betting_evalue(a, b, threshold=null_gap, comparator=Comparator.GT)


def expression_floor_evalue(node: OperationNode, *, cap: float = CAP, null_gap: float = NULL_GAP) -> float:
    pos, neg = _expr_split(node)
    return _gap_evalue(pos, neg, cap=cap, null_gap=null_gap)
