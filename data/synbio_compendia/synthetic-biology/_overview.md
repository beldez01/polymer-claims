# Synthetic Biology: A Compendium of Techniques

> **Filed under:** Synthetic Biology (topic overview + sub-index)
> **Created:** 2026-07-04
> **Last updated:** 2026-07-04
> **Tags:** synthetic-biology, engineering-biology, compendium, techniques, DBTL

## Summary
Synthetic biology is the application of engineering principles — standardization, abstraction, and decoupled design/build/test — to living systems. This compendium organizes the field's technique landscape into ten reports spanning ~270 verified primary references. The organizing logic follows the abstraction stack: you **write** DNA (synthesis & assembly), **edit** genomes (genome editing), **compose** regulatory parts into behavior (genetic circuits), **rewire** metabolism (metabolic engineering), **evolve and design** the proteins that do the work (protein engineering), **build genomes whole** (synthetic genomics), **rewrite the chemical alphabet** itself (expanded genetic code / xenobiology), **run it all in a tube** (cell-free systems), **industrialize the loop** (biofoundries & design automation), and **deploy and contain** the result (chassis, applications & biocontainment).

## The Engineering Logic
Modern synthetic biology is unified by the **Design-Build-Test-Learn (DBTL)** cycle and by Endy's 2005 argument that biology can be an engineering discipline if it adopts standardized parts, abstraction hierarchies (parts → devices → systems), and the decoupling of design from fabrication. Almost every technique below is best understood as accelerating, broadening, or de-risking one turn of that cycle:

- **Design** is served by CAD/EDA tools (Cello, RBS Calculator, SBOL) and increasingly by machine-learning recommenders and generative models.
- **Build** rests on DNA synthesis and assembly, genome editing, and whole-genome writing.
- **Test** is transformed by cell-free prototyping, calibrated metrology (MEFL), and high-throughput sequencing readouts.
- **Learn** is where models — genome-scale metabolic models, deep mutational fitness landscapes, ML surrogates — close the loop.

A recurring cross-cutting theme is **biocontainment**: as engineered organisms move toward deployment, expanded-genetic-code auxotrophy, genome recoding firewalls, and kill switches recur across multiple technique areas as the safety substrate.

## Sub-Index (the ten technique reports)

1. **[DNA Synthesis and Assembly](dna-synthesis-and-assembly.md)** — Phosphoramidite and enzymatic (TdT) oligo synthesis, array/chip synthesis, error correction; Gibson, Golden Gate/MoClo/Loop (Type IIS), BioBrick/BASIC, Gateway, LCR, SLIC, CPEC, USER, and yeast TAR assembly; the "gene-writing gap" and cost/throughput frontier. *(25 refs)*

2. **[Genome Editing and Targeted Genome Engineering](genome-editing-tools.md)** — Meganucleases, ZFNs, TALENs; CRISPR-Cas9/Cas12a/Cas13; high-fidelity and PAM-relaxed variants; base editing and prime editing / twinPE / PASTE; CRISPRi/CRISPRa; recombineering and MAGE; integrases, CAST transposons, and retrons; delivery (AAV/LNP/RNP) and off-target assays (GUIDE-seq, CIRCLE-seq, DISCOVER-seq). *(33 refs)*

3. **[Genetic Circuit Design and Regulatory Parts](genetic-circuits-and-parts.md)** — Toggle switch and repressilator; promoters/RBS/terminators/insulators (RiboJ); transcriptional NOR logic and Cello; RNA regulation (toehold switches, ribocomputing, riboswitches); recombinase logic and state machines; antithetic integral feedback control; oscillators, band-pass, edge detection; analog computation; burden, retroactivity, orthogonality. *(28 refs)*

4. **[Metabolic Engineering and Pathway Optimization](metabolic-engineering.md)** — DBTL; flux balancing (TIGRs, promoter/RBS libraries, modular MMME); genome-scale models, FBA, OptKnock, ¹³C-MFA; dynamic biosensor control; enzyme scaffolds; landmark cases (artemisinin, BDO, farnesene, opioids, cannabinoids); chassis selection; ALE; MAGE/CRISPR libraries; ML-guided design and biofoundries. *(27 refs)*

5. **[Directed Evolution and Protein Engineering](protein-engineering-directed-evolution.md)** — epPCR, DNA shuffling, StEP, site-saturation; phage/yeast/ribosome/mRNA display; PACE/PANCE, OrthoRep, eVOLVER; deep mutational scanning; Rosetta and de novo enzyme design; AlphaFold2, RoseTTAFold, ESM, RFdiffusion, ProteinMPNN; ML-guided directed evolution. *(29 refs)*

6. **[Synthetic Genomics and Minimal Genomes](synthetic-genomics-minimal-genomes.md)** — Poliovirus/φX174 synthesis; refactoring (T7, Caulobacter 2.0); Mycoplasma genome synthesis and transplantation (JCVI-syn1.0); minimal cell syn3.0/syn3A; genome recoding (C321.ΔA, 57-codon, Syn61/Syn61Δ3); Sc2.0 and SCRaMbLE; CReATiNG; human artificial chromosomes and the 2025 SynHG Project. *(25 refs)*

7. **[Expanded Genetic Code and Xenobiology](expanded-genetic-code-xenobiology.md)** — Orthogonal aaRS/tRNA pairs and amber suppression; ncAA applications (click, photocrosslinkers, encoded PTMs); orthogonal ribosomes (Ribo-X/Q) and quadruplet codons; codon reassignment; synthetic auxotrophy; unnatural/hachimoji base pairs and semi-synthetic organisms; XNA polymerases and XNAzymes; mirror-image biology and its biosecurity debate. *(28 refs)*

8. **[Cell-Free Synthetic Biology](cell-free-systems.md)** — Crude-extract CFPS (E. coli S30, wheat germ, mammalian) and the PURE reconstituted system; TX-TL circuit breadboarding; cell-free metabolic engineering; freeze-dried paper diagnostics, toehold sensors, SHERLOCK/DETECTR; glyco/membrane/ncAA synthesis; bottom-up synthetic cells; industrial and on-demand biomanufacturing. *(32 refs)*

9. **[Biofoundries and Design Automation](biofoundries-design-automation.md)** — The Global Biofoundry Alliance and lab automation; CAD (Cello, j5/DIVA, Benchling); SBOL and registries (iGEM, Addgene, SynBioHub); RBS/codon tools; calibrated metrology (RPU, MEFL, OD-to-cell-count); ML for design (ART, BioAutomata, ProGen); DNA data storage; NGS clone verification and reproducibility. *(22 refs)*

10. **[Chassis, Applications, and Biocontainment](chassis-applications-biocontainment.md)** — Chassis selection (E. coli, B. subtilis, yeast, P. putida, cyanobacteria, V. natriegens, CHO/HEK, plants); mammalian circuits, synNotch, and logic-gated CAR-T; engineered probiotics/living therapeutics (Nissle, Synlogic); whole-cell and ingestible biosensors; microbial consortia; engineered living materials (BIND); auxotrophy, kill switches, recoding firewalls, gene drives; Asilomar-to-DNA-screening governance. *(34 refs)*

## Capstone Synthesis

- **[Synthesis: Cross-Cutting Insights and Therapeutic Applications](synthesis-insights-and-therapeutics.md)** — Reads the ten reports horizontally: five field-wide insights (recoding as a "master key," the Build→Learn bottleneck migration, "decoupling" as an unnamed recurring design move, continuous-evolution/generative-ML convergence, biocontainment as enabler) plus a tiered therapeutic map from validated human data through emerging trajectories to novel cross-report combinations.

## Cross-Cutting Threads
- **The DBTL cycle** binds reports 1, 4, 8, and 9 into a single accelerating loop.
- **CRISPR/Cas** is a shared substrate across editing (2), circuits (CRISPRi/a, 3), diagnostics (SHERLOCK/DETECTR, 8), and gene drives (10).
- **Genome recoding** links synthetic genomics (6), expanded genetic code (7), and biocontainment (10) — the same technique reappears as a route to expanded chemistry, virus resistance, and a genetic firewall.
- **Machine learning and generative design** now touch protein engineering (5), metabolic design (4), and the foundry layer (9).
- **Biocontainment** is not a niche — it is the safety spine running through 6, 7, and 10.

## Open Frontiers (field-wide)
- Closing the **write gap**: can enzymatic synthesis and genome-scale writing become cheap and routine?
- **Context-independent design**: parts and circuits still behave differently across hosts and genetic contexts.
- **Predictive Learn**: turning multi-omics data into models that predict titer and phenotype, not just correlate.
- **Self-regenerating synthetic cells** and **autonomous** semi-synthetic organisms.
- **Governance keeping pace** with foundation-model-assisted design and decentralized synthesis.

## Connections to the rest of the library
- **Programmable Living Medicines** and **Cell Therapy QC** — the therapeutic deployment of chassis (report 10) and genome editing (report 2).
- **Computational Biology** and **Information Geometry** — genome-scale models, ML-guided design, and fitness-landscape inference (reports 4, 5, 9).
- **Molecular Biology** and **Epigenetics** — foundational mechanisms these techniques manipulate.
- See also the library-wide [MASTER_REFS.md](../../references/MASTER_REFS.md).
