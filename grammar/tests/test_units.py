from polymer_grammar.units import DIMENSIONLESS, Dimension, compatible

L = Dimension.base("length")
T = Dimension.base("time")
M = Dimension.base("mass")


def test_base_and_dimensionless():
    assert L.exponents == (("length", 1),)
    assert DIMENSIONLESS.is_dimensionless
    assert not L.is_dimensionless


def test_multiplication_adds_exponents():
    area = L * L
    assert area.exponents == (("length", 2),)


def test_division_subtracts_exponents():
    velocity = L / T
    assert velocity == Dimension(exponents=(("length", 1), ("time", -1)))


def test_identity_inverse_associative_commutative():
    assert L * DIMENSIONLESS == L                       # identity
    assert L * (L ** -1) == DIMENSIONLESS               # inverse
    assert (L * T) * M == L * (T * M)                   # associative
    assert L * T == T * L                               # commutative


def test_normalization_drops_zero_and_is_canonical():
    assert Dimension(exponents=(("length", 1), ("length", -1))).is_dimensionless
    assert Dimension(exponents=(("a", 0), ("b", 2))) == Dimension(exponents=(("b", 2),))
    assert Dimension(exponents=(("time", -1), ("length", 1))) == L / T  # order-independent


def test_compatible_is_equality():
    assert compatible(L / T, L / T)
    assert not compatible(L, T)


def test_dimension_is_hashable():
    assert isinstance(hash(L / T), int)
    assert len({L, L, T}) == 2
