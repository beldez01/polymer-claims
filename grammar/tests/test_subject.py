import pytest
from pydantic import ValidationError

from polymer_grammar.subject import GenomicRegion, OntologyTerm


def test_genomic_region_constructs():
    r = GenomicRegion(id="r1", display="chr1:100-200", assembly="GRCh38",
                      chrom="chr1", start=100, end=200)
    assert r.kind == "genomic_region"
    assert r.strand == "."          # default
    assert r.note is None           # shared base default


def test_genomic_region_rejects_start_after_end():
    with pytest.raises(ValidationError):
        GenomicRegion(id="r", display="bad", assembly="GRCh38",
                      chrom="chr1", start=200, end=100)


def test_ontology_term_constructs():
    o = OntologyTerm(id="HP:0001250", display="Seizure", ontology="HPO",
                     ontology_release="2026-01-01", uri="http://purl.obolibrary.org/obo/HP_0001250")
    assert o.kind == "ontology_term"
    assert o.propagation == "self_only"   # default
