"""The native e-value for a marker->drug association: a Waudby-Smith & Ramdas betting e-value
(evidence.betting_evalue) over leg A's within-tissue methylation split of the drug AUCs. Tests the
severe null that high-meth lines are NOT more sensitive by more than `threshold`. One leg only —
the rank leg is a corroborating gate, never a factor in the e-value (mirrors n-DMP)."""
from __future__ import annotations

from polymer_grammar import Comparator, OperationNode

from .evidence import betting_evalue
from .pharmaco_adapters import _pharmaco_split


def pharmaco_evalue(node: OperationNode, *, threshold: float, comparator: Comparator = Comparator.GT) -> float:
    """betting_evalue tests mu_b - mu_a > threshold. a = high-meth AUCs, b = low-meth AUCs, so
    a positive shift (low-meth AUC higher) = high-meth more sensitive. Bounded [0,1] AUCs."""
    hi, lo = _pharmaco_split(node)
    return betting_evalue(hi, lo, threshold=threshold, comparator=comparator)
