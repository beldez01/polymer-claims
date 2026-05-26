# FormalClaim Domain Ontology Note

Date: 2026-05-19

Core idea:

FormalClaim IR should stay small. Domain ontologies and versioned domain profiles should carry the biological complexity.

The hard problem is not representing claims as JSON. The hard problem is semantic discipline: deciding which dimensions exist, keeping them non-redundant, and forcing agents to map biological language into those dimensions consistently.

## Architecture

Universal FormalClaim IR should remain minimal:

- subject
- context
- premises
- operations
- statistics
- inference
- conclusion
- provenance
- relations

Domain profiles should define the allowed biological semantics:

- legal subject kinds
- legal context fields
- accepted identifier systems
- ontology mappings
- legal predicates
- legal operations
- statistic families
- inference templates

Examples:

- `methylation.v0.1`
- `hla.v0.1`
- `recombination.v0.1`
- `te_surveillance.v0.1`

Each claim should declare its domain profile version so old claims are not silently reinterpreted after ontology revisions.

## Existing Ontologies To Reuse

- Diseases: MONDO / DOID
- Cell types: Cell Ontology
- Anatomy / tissue: UBERON / BTO
- Phenotypes: HPO
- Genes: HGNC / Ensembl
- Variants: GA4GH VRS
- Sequence features: Sequence Ontology
- Assays: OBI / EFO
- Chemicals / drugs: ChEBI, DrugBank where licensing permits
- Pathways: Reactome / GO Biological Process
- Evidence: ECO
- Methods / data operations: EDAM / SWO where useful, plus Polymer-native terms for gaps

Polymer-native vocabularies are likely needed for:

- claim role
- inference rule
- materialization status
- agent provenance
- challenge state
- epistemic verdict
- operation DAG role

## Key Design Principle

Agents should author claims by filling typed semantic slots, not by translating prose directly into arbitrary JSON.

For example, a claim about "TET2-mutant AML vs WT" should not collapse that phrase into a single subject string. It should separate:

- disease: AML
- genotype: TET2 mutation status
- comparator: WT / control
- assay: EPICv2 methylation
- biological material: blood / marrow / sorted cell type
- statistic: differential methylation coefficient, DMR enrichment, clock acceleration, etc.

## First Practical Step

Do not try to solve all of biology at once.

Build one excellent `methylation.v0.1` domain profile with constrained subject kinds and context fields. Use it to author 20-30 real claims, then revise based on failure modes.

Candidate methylation subject kinds:

- CpG probe
- CpG locus
- DMR
- gene promoter
- enhancer
- TE family
- TE insertion
- sample cohort
- cohort contrast
- cell type
- epigenetic clock

Candidate methylation context dimensions:

- organism
- genome build
- platform: EPIC, EPICv2, 450K, WGBS
- assay type: bulk, sorted, single-cell, cfDNA
- tissue
- cell type or estimated composition method
- disease state
- genotype / mutation status
- treatment / exposure
- comparator group
- normalization method
- statistical model
- covariates
- multiple-testing method

The goal is a claim authoring system where agents choose from constrained, ontology-backed slots. This should make claims more consistent, searchable, comparable, and challengeable.

