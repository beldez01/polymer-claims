from polymer_grammar import GenerationMode, Provenance, SeverityProvenance

from polymer_protocol.topology import Layout, export_topology  # the public export entrypoint

from tests.helpers_verify import licensable_corpus, with_dimnames  # from Task 3
from polymer_protocol.verify import verify_stage


def _licensed_confirmatory_corpus():
    corpus, scaff, recs = licensable_corpus()
    corpus, recs = with_dimnames(corpus, recs, "c1", "cohortX")
    claims = tuple(
        c.model_copy(update={"provenance": Provenance(
            generated_by=GenerationMode.LITERATURE_EXTRACTED, search_cardinality=1,
            prior_cohorts=("cohortX",),
        )}) if c.id == "c1" else c
        for c in corpus.claims
    )
    corpus = corpus.model_copy(update={"claims": claims})
    return verify_stage(corpus, scaff, recs)


def test_topology_node_carries_severity_provenance():
    corpus = _licensed_confirmatory_corpus()
    export = export_topology(corpus, layout=Layout.NONE)
    n = next(n for n in export.nodes if n.id == "c1")
    assert n.severity_provenance == SeverityProvenance.CONFIRMATORY.value


def test_topology_node_severity_provenance_none_when_absent():
    from tests.helpers_verify import licensable_corpus as lc
    corpus, scaff, recs = lc()
    out = verify_stage(corpus, scaff, recs)
    export = export_topology(out, layout=Layout.NONE)
    n = next(n for n in export.nodes if n.id == "c1")
    assert n.severity_provenance is None
