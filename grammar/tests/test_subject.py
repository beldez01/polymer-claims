import pytest
from pydantic import ValidationError

from polymer_grammar.subject import (
    GenomicRegion,
    GeneOrProtein,
    GeneOrProteinIdentifiers,
    OntologyTerm,
    S4ObjectRef,
    VariantVRS,
)


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


def test_variant_vrs_constructs_and_validates_id():
    v = VariantVRS(id="ga4gh:VA.abc123", display="rs1 A>G", vrs_version="2.0", hgvs="NC_000001.11:g.100A>G")
    assert v.kind == "variant_vrs"
    with pytest.raises(ValidationError):
        VariantVRS(id="not-a-vrs-id", display="bad", vrs_version="2.0")


def test_gene_or_protein_requires_a_canonical_id():
    g = GeneOrProtein(
        id="HGNC:11998", display="TP53",
        identifiers=GeneOrProteinIdentifiers(hgnc="HGNC:11998", symbol="TP53"),
        entity_type="gene",
    )
    assert g.kind == "gene_or_protein"
    with pytest.raises(ValidationError):
        GeneOrProtein(
            id="x", display="no ids",
            identifiers=GeneOrProteinIdentifiers(symbol="TP53"),   # none of hgnc/ensembl_gene/uniprot
            entity_type="gene",
        )


def test_s4_object_ref_dims_is_tuple():
    s = S4ObjectRef(id="s1", display="SummarizedExperiment", bioc_class="SummarizedExperiment",
                    bioc_version="1.30", blob_uri="s3://b/x.rds", blob_hash="blake3-abc",
                    dims=(200, 50))
    assert s.kind == "s4_object"
    assert s.dims == (200, 50)
