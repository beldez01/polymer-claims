import pytest
from pydantic import TypeAdapter, ValidationError

from polymer_grammar.subject import (
    Cohort,
    CohortDefinition,
    CohortSourceDataset,
    CompositeSubject,
    GenomicRegion,
    GeneOrProtein,
    GeneOrProteinIdentifiers,
    LiteralSubject,
    OntologyTerm,
    PathwayMembers,
    PathwayRef,
    PhenopacketRef,
    PhenopacketRetrieval,
    S4ObjectRef,
    Subject,
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


def test_phenopacket_reference_mode_requires_uri():
    p = PhenopacketRef(
        id="pp1", display="Patient A", phenopacket_version="2.0",
        retrieval=PhenopacketRetrieval(mode="reference", uri="s3://b/pp1.json"),
    )
    assert p.kind == "phenopacket"
    with pytest.raises(ValidationError):
        PhenopacketRef(id="pp", display="bad", phenopacket_version="2.0",
                       retrieval=PhenopacketRetrieval(mode="reference"))   # no uri


def test_phenopacket_inline_mode_requires_inline_json():
    p = PhenopacketRef(
        id="pp2", display="inline", phenopacket_version="2.0",
        retrieval=PhenopacketRetrieval(mode="inline"), inline_json='{"id":"pp2"}',
    )
    assert p.inline_json == '{"id":"pp2"}'
    with pytest.raises(ValidationError):
        PhenopacketRef(id="pp", display="bad", phenopacket_version="2.0",
                       retrieval=PhenopacketRetrieval(mode="inline"))      # no inline_json


def test_pathway_ref_members_inline_is_tuple():
    pw = PathwayRef(id="R-HSA-1", display="Apoptosis", source="Reactome", source_version="88",
                    members=PathwayMembers(retrieval="inline", inline=("TP53", "BAX")))
    assert pw.kind == "pathway"
    assert pw.members.inline == ("TP53", "BAX")


def test_cohort_constructs_with_tuple_predicates():
    c = Cohort(
        id="coh1", display="TET2 cohort", members_hash="blake3-xyz",
        definition=CohortDefinition(
            source_dataset=CohortSourceDataset(name="IDAT", version="v2", tissue="blood"),
            inclusion=("age >= 18", "tissue == blood"),
            cardinality=132,
        ),
    )
    assert c.kind == "cohort"
    assert c.definition.inclusion == ("age >= 18", "tissue == blood")
    assert c.definition.exclusion == ()        # default empty tuple


def test_literal_subject_structured_is_tuple_of_pairs():
    lit = LiteralSubject(id="l1", display="ad hoc", prose="the 2026 winter cohort",
                         structured=(("season", "winter"), ("year", "2026")))
    assert lit.kind == "literal"
    assert lit.structured == (("season", "winter"), ("year", "2026"))
    bare = LiteralSubject(id="l2", display="prose only", prose="something untyped")
    assert bare.structured == ()               # default


def test_composite_nests_two_subjects():
    gene = GeneOrProtein(id="HGNC:11998", display="TP53",
                         identifiers=GeneOrProteinIdentifiers(hgnc="HGNC:11998"), entity_type="gene")
    coh = Cohort(id="coh1", display="cohort", members_hash="h",
                 definition=CohortDefinition())
    comp = CompositeSubject(id="cmp1", display="TP53 in cohort", relation="conditional",
                            parts=(gene, coh))
    assert comp.kind == "composite"
    assert len(comp.parts) == 2


def test_composite_requires_at_least_two_parts():
    gene = GeneOrProtein(id="g", display="g",
                         identifiers=GeneOrProteinIdentifiers(hgnc="HGNC:1"), entity_type="gene")
    with pytest.raises(ValidationError):
        CompositeSubject(id="c", display="bad", relation="conditional", parts=(gene,))


def test_subject_union_dispatches_on_kind():
    adapter = TypeAdapter(Subject)
    obj = adapter.validate_python(
        {"kind": "ontology_term", "id": "GO:0006915", "display": "apoptosis",
         "ontology": "GO", "ontology_release": "2026-01-01", "uri": "http://x/GO_0006915"}
    )
    assert isinstance(obj, OntologyTerm)


def test_subjects_are_hashable():
    gene = GeneOrProtein(id="g", display="g",
                         identifiers=GeneOrProteinIdentifiers(hgnc="HGNC:1"), entity_type="gene")
    comp = CompositeSubject(id="c", display="c", relation="correlational",
                            parts=(gene, gene))
    assert isinstance(hash(gene), int)
    assert isinstance(hash(comp), int)


def test_public_api_exports():
    import polymer_grammar as pg

    for name in [
        "Subject", "GenomicRegion", "VariantVRS", "S4ObjectRef", "PhenopacketRef",
        "OntologyTerm", "GeneOrProtein", "PathwayRef", "Cohort", "LiteralSubject",
        "CompositeSubject", "GeneOrProteinIdentifiers", "CohortDefinition",
        "CohortSourceDataset", "PhenopacketRetrieval", "PathwayMembers",
    ]:
        assert hasattr(pg, name), f"{name} not exported from polymer_grammar"
