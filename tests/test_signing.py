from polymer_claims.signing import pae


def test_pae_basic_vector():
    # PAE(type, body) = b"DSSEv1 " + len(type) + " " + type + " " + len(body) + " " + body
    assert pae("X", b"YY") == b"DSSEv1 1 X 2 YY"


def test_pae_lengths_are_byte_counts():
    assert pae("application/vnd.in-toto+json", b"{}") == b"DSSEv1 28 application/vnd.in-toto+json 2 {}"


def test_pae_unicode_type_uses_utf8_byte_length():
    # "é" is 2 UTF-8 bytes, so LEN(type) counts bytes not chars
    assert pae("é", b"") == b"DSSEv1 2 \xc3\xa9 0 "
