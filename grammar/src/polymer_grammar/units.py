"""Units-of-measure algebra (spec §2; unified spec §3.1).

Dimension as an abelian group over base dimensions (base -> integer exponent;
multiply = add exponents). Makes dimensional reasoning decidable (Kennedy 1997;
Buckingham Π for free). The canonical representation is a sorted tuple of
(base, exponent) pairs with no zero exponents — so the model is frozen, hashable,
and equality is structural. DIMENSIONLESS is the group identity. Enforcement against
quantity arithmetic is the evaluator phase; this module ships the type.
"""
from __future__ import annotations

from pydantic import field_validator

from .base import _Model


class Dimension(_Model):
    # canonical: sorted tuple of (base, exponent) pairs, no zero exponents
    exponents: tuple[tuple[str, int], ...] = ()

    @field_validator("exponents")
    @classmethod
    def _canonicalize(cls, v: tuple[tuple[str, int], ...]) -> tuple[tuple[str, int], ...]:
        acc: dict[str, int] = {}
        for base, exp in v:
            acc[base] = acc.get(base, 0) + exp
        return tuple(sorted((b, e) for b, e in acc.items() if e != 0))

    @classmethod
    def base(cls, name: str) -> Dimension:
        return cls(exponents=((name, 1),))

    @property
    def is_dimensionless(self) -> bool:
        return not self.exponents

    def __mul__(self, other: Dimension) -> Dimension:
        return Dimension(exponents=self.exponents + other.exponents)

    def __truediv__(self, other: Dimension) -> Dimension:
        return self * (other ** -1)

    def __pow__(self, n: int) -> Dimension:
        return Dimension(exponents=tuple((b, e * n) for b, e in self.exponents))


DIMENSIONLESS = Dimension(exponents=())


def compatible(a: Dimension, b: Dimension) -> bool:
    """Two dimensions are compatible (addable/comparable) iff equal."""
    return a == b
