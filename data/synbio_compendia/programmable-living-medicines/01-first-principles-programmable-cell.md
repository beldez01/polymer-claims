# First Principles: The Cell as a Programmable Therapeutic

> **Filed under:** Programmable Living Medicines > Part I
> **Created:** 2026-06-09
> **Last updated:** 2026-06-09
> **Tags:** first-principles, sense-compute-act, central-dogma, information-theory, molecular-recognition, thermodynamics, cell-state, genotype, CAR-T, synthetic-biology, programmable-medicine

## Summary

This chapter establishes the load-bearing abstraction for the entire treatise: a therapeutic cell is best understood not as a biologic drug but as an **information-processing device** that reads cellular information, computes on it, and acts. The argument proceeds in four moves. First, the historically dominant target abstraction — **surface phenotype** — is the wrong one, because the information that distinguishes a diseased cell from a healthy bystander frequently does not reach the surface at useful density; the right abstraction is **genotype and cell-state** (the transcriptome, epigenome, and somatic genome). Second, every engineered living medicine, from a first-generation CD19 CAR-T to a synNotch logic circuit to an in-vivo base editor, decomposes into the same architecture: **sense → compute → act**, wrapped by **deliver** and **measure** and stabilized by **control**. Third, the molecule-to-program paradigm shift (small molecule → biologic → cell → *programmable* cell) is real and quantifiable: we are migrating from drugs whose specificity is a fixed property of a molecule to medicines whose specificity is *computed at runtime* inside the patient. Fourth, the ultimate constraint on all of this is **information-theoretic and thermodynamic** — how many bits of identity distinguish target from bystander, where those bits physically live, and whether a molecular recognition event can resolve them against thermal noise at 310 K (a single Watson-Crick mismatch buys only ~1–3 kcal/mol against a background kT ≈ 0.62 kcal/mol). These four moves define the recurring axes — read, write, compute, act, deliver, measure, control — that every subsequent chapter instantiates.

## Background / First Principles

### The grand thesis, stated precisely

The unit of medicine is shifting from the **molecule** to the **program**. A small molecule's therapeutic logic is frozen at synthesis: aspirin inhibits cyclooxygenase in every cell it reaches, and its "specificity" is whatever differential exposure and target abundance happen to provide. A monoclonal antibody is more selective but still a fixed recognizer — one paratope, one epitope, one decision rule, manufactured once and unchanged in the body. A cell therapy breaks this frozen logic. A living cell carries a genome that can be *rewritten*, a transcriptome that *responds to context*, and protein machinery that can *execute conditional decisions*. The engineered therapeutic cell is therefore a **sense → compute → act device**: it reads genotype, epigenotype, transcriptome, and microenvironment; it computes on that information with synthetic logic (Boolean gates, recombinase memory, thresholded receptors); and it acts by killing, secreting, differentiating, or rewriting genomes. "Genomic methods" are not adjacent to this medicine — they *are* its instruction set (what the cell is programmed to do) and its measurement layer (how we read what the cell did, and what the patient's disease is).

### Why surface phenotype is the wrong abstraction

The entire first generation of cell therapy targets **surface phenotype**: a CAR or TCR recognizes a protein (or a peptide-MHC complex) displayed on the membrane. CD19 CAR-T works because B-lineage malignancies wear CD19, a dispensable lineage protein, on their surface. But this abstraction has a structural flaw that recurs as the dominant failure mode of the field: **the molecular events that define a disease are overwhelmingly intracellular, and many produce no distinctive surface marker at all.** The drivers of clonal hematopoiesis and myeloid malignancy — *TET2*, *DNMT3A*, *TP53*, *JAK2 V617F*, *IDH1/2*, the splicing factors *SF3B1*/*SRSF2* — are nuclear or cytoplasmic. Loss-of-function lesions are the worst case: the cell's "crime" is the *absence* of a functional protein, which displays nothing. Surface phenotype is a low-dimensional, often disease-irrelevant projection of a cell's true state.

The consequences are not academic. Antigen loss — the tumor dropping the dispensable surface protein the CAR sees — drives an estimated ~30–50% of relapses after CD19 CAR-T in B-ALL series (antigen-negative escape is notably more frequent in leukemia than lymphoma; reviewed in Majzner & Mackall, *Cancer Discov*, 2018). The therapy fails precisely because it targets a *correlate* of disease (a lineage marker) rather than the disease's *cause* (a driver mutation). A cell that targeted the driver could only escape by surrendering the driver — and thus the fitness advantage that made it malignant. This is the cash value of "getting beneath the surface phenotype," developed at length in the sibling report [genotype-directed cytotoxicity](../opto-car/seed-report.md): target-loss and fitness-loss become *coupled* when you target genotype rather than surface.

### The right abstraction: genotype and cell-state

The correct target abstraction is the cell's **information content** — its genotype (germline and somatic variants), its **epigenome** (DNA methylation, chromatin state — the cell's heritable *memory* and its position on the Waddington landscape; see [energy-landscape-hematopoiesis](../energy-landscape-hematopoiesis/_overview.md)), and its **transcriptome** (the live, context-dependent readout of which programs are running). These are the axes along which a diseased cell genuinely differs from its neighbors. A myeloid blast and a healthy monocyte may share most surface proteins, but they differ at a defined somatic locus (e.g., *NPM1* insertion, *FLT3*-ITD), in their methylation landscape (TET2-mutant clones carry a characteristic hypermethylation signature; see [chip/02_methylation_biology](../chip/02_methylation_biology.md)), and in their transcriptional program. The thesis of this treatise is that **the measurement layer of genomics now lets us read these axes, and the engineering layer of synthetic biology now lets a cell read them too** — moving the locus of decision-making from the manufacturer's bench into the patient's tissue at runtime.

## Key Findings

### The sense → compute → act decomposition is universal

Every engineered living medicine, however baroque, factors into the same pipeline. This is not a metaphor; it is a literal functional decomposition that the rest of the treatise uses as its coordinate system.

- **SENSE** — the input transduction layer. *What information does the cell read, and through which physical channel?* A CAR senses a surface protein via an scFv binding event. A TCR senses peptide-MHC. A synNotch receptor senses a surface ligand and converts it to a transcriptional event (Morsut et al., *Cell*, 2016; Roybal et al., *Cell*, 2016). An ADAR-based RNA sensor (CellREADR/RADAR-class) senses a specific transcript — including a single-base variant — by Watson-Crick hybridization and converts it to translation of a chosen payload (Qian et al., *Nature*, 2022; Kaseniit et al., *Nat Biotechnol*, 2023; Jiang et al., *Nat Biotechnol*, 2023). The sensing modality determines *which bits of cell identity are legible* — surface, transcript, or peptide — and is the single most consequential design choice.

- **COMPUTE** — the logic layer. *Given the inputs, what decision rule fires the output?* This ranges from a trivial single-input threshold (CAR: "antigen present above density θ → activate") to genuine Boolean and sequential logic. synNotch enables **AND gates** (antigen 1 licenses a CAR against antigen 2), **NOT gates** (the A2 Bio Tmod platform fires only when a normal HLA allele is *absent* — keyed to HLA-A\*02 loss of heterozygosity), and **recombinase-based memory** that latches a transient input into a permanent state change. Computation is where specificity is *manufactured at runtime* from inputs that are individually insufficient.

- **ACT** — the actuation layer. *What does the cell physically do?* Kill (perforin/granzyme, death-receptor engagement, or a payload-expressed executioner such as opto-caspase; Shkarina et al., *J Cell Biol*, 2022); secrete (cytokines, bispecific engagers, antibodies); differentiate (driving a cell down a chosen lineage); or rewrite (Cas-mediated genome or epigenome editing). The actuator converts a decision into a physical, often irreversible, intervention.

Wrapping this core are three further axes that gate whether the device works *in a body* rather than a dish:

- **DELIVER** — getting the program to the right cells. Ex vivo lentiviral transduction of CD34⁺ HSCs or T cells is clinical-grade routine; in-vivo targeted delivery (antibody/nanobody-decorated LNPs, engineered AAV, targeted lentivirus) is the rate-limiting frontier. A CD117/c-Kit antibody-LNP achieved reporter-mRNA delivery to ~90% of long-term HSCs (tdTomato⁺ conversion at the high 1 mg/kg dose; functional editing was lower) with a single IV dose (Breda et al., *Science*, 2023) — a number that defines the current ceiling for marrow-tropic in-vivo programming.

- **MEASURE** — reading what the disease *is* and what the cell *did*. This is the genomics measurement layer: WGS, methylation arrays/EM-seq, single-cell and spatial transcriptomics, cfDNA. It both defines the target (which variant, which methylation state) and validates the intervention. The treatise treats biology as increasingly **machine-readable** (see [precision-medicine/machine-readable-biology](../precision-medicine/machine-readable-biology.md)).

- **CONTROL** — keeping the device safe and stable in a feedback-rich, evolving system. Control theory governs whether a circuit is robust to leak, whether a kill switch can halt it, whether the therapeutic effect persists or exhausts, and whether the target population can evolve around it. A programmable medicine without a control layer is an open-loop intervention in a closed-loop, adversarial biological system.

These seven axes — **read, write, compute, act, deliver, measure, control** — are the spine of the treatise. ("Read" and "write" refine the genomic content of sense and act: reading genotype/epigenotype, writing genome/epigenome.) Each later chapter can be located as an advance along one or more of them.

### The molecule → program paradigm shift, quantified

The migration is legible as a steady increase in the *amount of computation embedded in the therapeutic* and a corresponding shift in where specificity is determined.

| Era | Modality | Specificity locus | Decision rules | Reprogrammable in patient? |
|---|---|---|---|---|
| 1900s–present | Small molecule | Fixed at synthesis | ~1 (target binding) | No |
| 1980s–present | Biologic (mAb) | Fixed at synthesis | 1 (paratope-epitope) | No |
| 2010s–present | Cell therapy (CAR-T) | Fixed at manufacture | 1 (antigen threshold) | No (but cell persists/expands) |
| Now → frontier | **Programmable cell** | **Computed at runtime** | **Boolean/sequential logic, multi-input** | **Yes (sensors respond to live context; editors rewrite)** |

The jump from biologic to cell is the jump from a *molecule* to an *agent*: the cell persists, expands clonally in response to its target (a CAR-T can undergo >1,000-fold in-vivo expansion), traffics, and can be re-stimulated — properties no molecule has. The jump from cell to *programmable* cell is the jump from a fixed decision rule to **conditional logic evaluated against the patient's live cellular information**. This is why the unit becomes the program, not the molecule: the same chassis, loaded with a different instruction set, becomes a different medicine.

### The central dogma as an engineering substrate

The molecular biologist reads DNA → RNA → protein as a description of how cells work. The cell engineer reads it as a **four-layer computer architecture**, each layer with distinct engineering properties:

- **DNA — non-volatile storage.** High information density (~2 bits/bp; a human genome is ~6.4 × 10⁹ bp ≈ 1.6 GB of raw sequence), heritable across divisions, and now *writable* in situ via base editing and prime editing. In-vivo somatic editing reaches up to ~50% indel frequency at favorable liver loci (Singh et al., *Mol Ther*, 2018); base editors achieve precise single-nucleotide writes without double-strand breaks. DNA is the layer for *permanent* reprogramming — and the layer where the genomic methods of this treatise both read disease and write therapy.

- **RNA — transient, addressable instruction.** Volatile (mRNA-LNP payload peaks ~24–48 h and decays over days), non-integrating, and — critically — the layer where a cell's *current state* is legible and where a single-base variant is *expressed* and therefore sensable. RNA is both the safest write medium (transient, no genomic scar) and the richest read medium for cell-state. The ADAR-sensor platforms exploit exactly this: they read the RNA layer because that is where the genotype is *running*.

- **Protein — the actuator.** The layer that does physical work: binds, catalyzes, kills, forms pores, transduces signal. Synthetic receptors (CAR, synNotch, opto-switches) are engineered proteins that import non-native input/output couplings. Protein is where "act" lives, and where the immune synapse — the ~15 nm cleft across which a T cell delivers its lethal hit — is built.

- **Epigenome — state and memory.** DNA methylation and chromatin modifications are the layer that encodes *which programs are on*, heritably, without changing sequence. This is the cell's **memory** and its address on the Waddington landscape. It is read by methylation assays (the basis of epigenetic clocks and CHIP detection; see [chip/03_epigenetic_clocks](../chip/03_epigenetic_clocks.md)) and is increasingly *writable* by dCas9-DNMT/TET fusions. Engineering the epigenome means engineering cell *fate* and *memory* directly — the deepest and least mature write target.

Reframing the dogma this way makes the design space explicit: a programmable medicine is a choice of *which layer to read* (sense), *which layer to compute on*, *which layer to write* (act), and *how persistent* the write should be (RNA = transient, DNA/epigenome = durable).

### The information-theoretic framing of specificity

The deepest question in all of programmable medicine is: **how many bits distinguish the target cell from a bystander, and where do those bits live?** Specificity is, at bottom, an information-retrieval problem against a noisy background.

Consider the channels and their bit budgets:

- **Surface protein.** A lineage antigen like CD19 is roughly a 1-bit discriminator at the lineage level (B-cell or not) but carries *zero* bits about malignancy versus a healthy B cell — which is why CD19 CAR-T ablates the normal B compartment as collateral. Surface antigen density adds a few bits of analog information (tumors often overexpress), but the channel is fundamentally low-dimensional and shared with normal tissue.

- **Transcript abundance / signature.** A transcriptional state — e.g., a multi-gene exhaustion or blast signature — can carry many bits, and single-cell methods now resolve them. But abundance is continuous and noisy; thresholding it costs specificity.

- **Somatic SNV.** A single recurrent driver mutation (JAK2 V617F: a single G→T) is an extraordinarily high-specificity bit — it is present in the malignant clone and *absent from every normal cell in the body*. One base is, in principle, a near-perfect discriminator. The catch is *reading* it (below).

- **Methylation pattern.** A differentially methylated region carries information about cell-of-origin and state that a single SNV cannot — it is a *distributed, multi-CpG* code. TET2-mutant clones carry a diffuse hypermethylation signature spread across thousands of CpGs (see [epigenetics/tet2-macrophage-immunophenotype](../epigenetics/tet2-macrophage-immunophenotype.md)). This is a high-bit channel, but it is currently legible only *ex vivo* by assay, not by an in-cell sensor.

The strategic insight: **the highest-specificity bits (somatic SNVs, methylation patterns) live in the layers that are hardest for a cell to read in vivo, while the easiest-to-read bits (surface proteins) carry the least disease-specific information.** This inverse relationship — specificity is anti-correlated with in-cell legibility — is the central tension the entire field is trying to resolve. RNA-sensing (CellREADR/RADAR/Cas13) is the current best attempt to make the high-specificity SNV bit legible inside a living cell.

### The thermodynamics of molecular recognition — the universal constraint

Every sense event is ultimately a molecular recognition event, and every recognition event is bounded by the same physics: **the free-energy difference between the correct binding configuration and the next-best (single-mismatch) configuration must beat thermal noise at body temperature.** At 310 K, the thermal energy scale is kT ≈ 0.62 kcal/mol (4.28 × 10⁻²¹ J). This number is the universal ruler against which all specificity is measured.

For nucleic-acid recognition — the basis of all variant sensing — a single internal Watson-Crick mismatch destabilizes a duplex by only ~1–3 kcal/mol of ΔG°₃₇, the exact value depending on the mismatch identity and its nearest-neighbor context (e.g., DNA mismatch contributions range from roughly −2.2 to +2.7 kcal/mol across like-with-like mismatches; G·T and G·A mismatches are particularly weakly destabilizing, often <1 kcal/mol; Allawi & SantaLucia and successors, *Biochemistry/NAR*, 1997–1999). A discrimination of, say, 2 kcal/mol corresponds to an equilibrium occupancy ratio of exp(ΔΔG/kT) = exp(2/0.62) ≈ 25-fold between match and mismatch. That is *modest*. It means a sensor designed against a mutant allele will still bind the wild-type allele at a few-percent rate — and since the wild-type transcript is present at ~50% in a heterozygous mutant cell and 100% in every normal cell, even single-digit-percent cross-reactivity can light up the whole population and destroy specificity. This is precisely why single-base discrimination is the *make-or-break* engineering problem for RNA-sensing therapeutics, and why the proof-of-concept experiment in the sibling report turns on whether the sensor *rejects the wild-type transcript* (see [genotype-directed cytotoxicity §12](../opto-car/seed-report.md)).

Three escape routes from this thermodynamic trap recur throughout the treatise, and each is a way of *buying more bits* than equilibrium binding affords:

1. **Enzymatic proofreading / kinetic discrimination.** Cas9, Cas13, and ADAR do not rely on equilibrium binding alone; they couple recognition to a catalytic step (cleavage, editing) whose rate is hypersensitive to mismatch, amplifying a small ΔΔG into a large rate difference — the same kinetic-proofreading trick (Hopfield, 1974) the ribosome and TCR use to beat the equilibrium specificity limit. Cas13 mismatch intolerance can be tuned to silence a point-mutant transcript while sparing wild-type (Tambe et al. and successors, *Sci Adv*, 2024-era work).
2. **AND-gating across independent channels.** If one channel gives ~25-fold discrimination, two independent channels in series give ~625-fold. Requiring *two* coincident inputs (two variants, or variant + contact, or variant + surface marker) multiplies specificity — the engineering rationale for synNotch logic and for contact-gated activation.
3. **Coincidence with a physical constraint** (e.g., cell-cell contact at the immune synapse), which adds a spatial bit that no soluble background can supply.

The recurring lesson: **specificity is never free; it is bought either with extra bits (more channels, AND-logic) or with non-equilibrium machinery (enzymatic proofreading, kinetic gating).** A programmable medicine's specificity ceiling is set by how cleverly it spends this budget against kT.

## Counterintuitive & Groundbreaking Applications

**Specificity should be computed, not manufactured.** The frozen-molecule paradigm forces the manufacturer to *pre-commit* to a specificity that must work across all patients. The programmable paradigm lets specificity be *assembled in situ* from the individual patient's cellular information. The counterintuitive consequence: a medicine can be *more* specific than any of its parts, because the AND of two sloppy recognizers is a precise one. This inverts a century of pharmacology, in which a drug's selectivity was an intrinsic, fixed property to be optimized once.

**The driver-dependence trap as a structural moat.** Because surface-targeting therapies attack disease *correlates*, tumors escape by dropping the correlate. A genotype-targeting therapy attacks the disease *cause*; escape requires surrendering the cause. This is the single most important strategic asymmetry in the field: targeting genotype couples therapeutic escape to de-oncogenesis. It is also a *commercial* moat — a modality structurally harder to evade is a more durable product.

**The methylome as the next addressable layer.** SNVs are point-like, high-specificity but sparse. The methylome is a *distributed, high-dimensional* code that distinguishes cell-of-origin and disease state with thousands of correlated bits — a code already exploited commercially in cfDNA cancer detection and epigenetic clocks. The frontier application is an in-cell *methylation* sensor: a device that reads not one base but a *pattern*, gating therapy on a cell-state fingerprint no single mutation can specify. This is unbuilt and hard (chromatin occlusion, the read-write asymmetry of methylation), but it is where the highest-bit channel and the deepest disease-specificity converge.

**The cell as a clinical-grade measurement instrument.** Flip the architecture: a sensing cell whose payload is a *reporter* rather than a killer becomes a living diagnostic that performs variant- or state-specific "flow cytometry by induced expression" — the cell manufactures a fluorophore *because* of its own genotype, sidestepping the unsolved problem of physically binding a chromophore to a genomic SNV in a live nucleus. This collapses the boundary between the *measure* axis and the *sense* axis: the same device that reads disease for therapy can read it for diagnosis, blurring drug and assay into one programmable object.

## Open Questions

- **How many bits, really, separate a malignant clone from its benign precursor?** For CHIP → AML, the answer determines whether genotype alone suffices or whether an AND with a transformation marker is mandatory. The benign TET2/JAK2 CHIP problem (large, *functional* mutant clones) shows that a single driver bit is often *insufficient* to license killing — the indication, not the platform, is frequently the binding constraint.
- **Can the high-specificity channels (SNV, methylation) be made legible in vivo at therapeutic scale?** RNA-sensing reads SNVs in living cells today, but delivery to a high fraction of target cells in marrow, and rejection of the abundant wild-type transcript, remain unsolved at the precision a clonal-hematopoiesis indication demands.
- **What is the right persistence?** RNA (transient, safe, re-dosable) versus DNA/epigenome (durable, but an irreversible write in a patient). The control-theoretic tradeoff between efficacy (needs persistence) and safety (needs reversibility) has no settled answer.
- **Where is the thermodynamic floor for single-base in-cell discrimination?** Kinetic proofreading and AND-gating extend it, but no one has mapped how far, across sequence contexts, in the chromatinized, ADAR-background-laden interior of a living cell.
- **Is the epigenome writable with enough fidelity and durability to engineer fate as a therapeutic act?** dCas9-effector fusions edit methylation, but heritability and off-target reprogramming are open.

## Connections

- **Within this treatise:** This chapter defines the read/write/compute/act/deliver/measure/control axes that every sibling chapter instantiates — sensing modalities and recognition physics (Part II), synthetic compute and logic circuits (Part III–IV), actuation and the immune synapse (later parts), delivery and the in-vivo programming problem, and the research agenda in ./13-research-agenda-open-problems.md.
- **[../immunology/genotype-directed-cytotoxicity.md](../opto-car/seed-report.md)** — the deep worked example of sense→act applied to intracellular variants (ADAR/Cas13 sensing, trans-cellular BRET coupling, JAK2-V617F MPN as lead indication); this chapter is the first-principles substrate beneath it.
- **[../cell-therapy-qc/](../cell-therapy-qc/)** — the *measure* axis as applied to manufacturing and potency (universal-functional-potency, epigenetic-mitochondrial-trajectory assays); reading what the engineered cell *is* before it is dosed.
- **[../chip/02_methylation_biology.md](../chip/02_methylation_biology.md), [../chip/03_epigenetic_clocks.md](../chip/03_epigenetic_clocks.md)** — the methylation/epigenome channel as a high-bit, distributed identity code.
- **[../energy-landscape-hematopoiesis/_overview.md](../energy-landscape-hematopoiesis/_overview.md)** — cell-state as a position on a quasi-potential landscape; the formal object behind "epigenome = state/memory."
- **[../epigenetics/tet2-macrophage-immunophenotype.md](../epigenetics/tet2-macrophage-immunophenotype.md), [../epigenetics/methylation-gene-regulation.md](../epigenetics/methylation-gene-regulation.md)** — how methylation encodes regulatory state.
- **[../precision-medicine/machine-readable-biology.md](../precision-medicine/machine-readable-biology.md)** — biology as a substrate that genomic methods render machine-readable; the philosophical companion to "genomics as the measurement layer."

## References

1. Morsut L, Roybal KT, Xiong X, et al. Engineering customized cell sensing and response behaviors using synthetic Notch receptors. *Cell*. 2016;164(4):780–791. doi:10.1016/j.cell.2016.01.012
2. Roybal KT, Rupp LJ, Morsut L, et al. Precision tumor recognition by T cells with combinatorial antigen-sensing circuits. *Cell*. 2016;164(4):770–779. doi:10.1016/j.cell.2016.01.011
3. Qian Y, Li J, Zhao S, et al. Programmable RNA sensing for cell monitoring and manipulation (CellREADR). *Nature*. 2022;610(7933):713–721. doi:10.1038/s41586-022-05280-1
4. Kaseniit KE, Katz N, Kolber NS, et al. Modular, programmable RNA sensing using ADAR editing in living cells (RADARS). *Nat Biotechnol*. 2023;41(4):482–487. doi:10.1038/s41587-022-01493-x
5. Jiang K, Koob J, Chen XD, et al. Programmable eukaryotic protein synthesis with RNA sensors by harnessing ADAR (RADAR). *Nat Biotechnol*. 2023;41(5):698–707. doi:10.1038/s41587-022-01534-5
6. Majzner RG, Mackall CL. Tumor antigen escape from CAR T-cell therapy. *Cancer Discov*. 2018;8(10):1219–1226. doi:10.1158/2159-8290.CD-18-0442
7. Allawi HT, SantaLucia J Jr. Thermodynamics and NMR of internal G·T mismatches in DNA. *Biochemistry*. 1997;36(34):10581–10594. doi:10.1021/bi962590c
8. Peyret N, Seneviratne PA, Allawi HT, SantaLucia J Jr. Nearest-neighbor thermodynamics and NMR of DNA sequences with internal A·A, C·C, G·G, and T·T mismatches. *Biochemistry*. 1999;38(12):3468–3477. doi:10.1021/bi9825091
9. Hopfield JJ. Kinetic proofreading: a new mechanism for reducing errors in biosynthetic processes requiring high specificity. *Proc Natl Acad Sci USA*. 1974;71(10):4135–4139. doi:10.1073/pnas.71.10.4135
10. Alexandrov LB, Nik-Zainal S, Wedge DC, et al. Signatures of mutational processes in human cancer. *Nature*. 2013;500(7463):415–421. doi:10.1038/nature12477
11. Shkarina K, Hasel de Carvalho E, Santos JC, et al. Optogenetic activators of apoptosis, necroptosis, and pyroptosis (optoCDE). *J Cell Biol*. 2022;221(6):e202109038. doi:10.1083/jcb.202109038
12. Singh K, Evens H, Nair N, et al. Efficient in vivo liver-directed gene editing using CRISPR/Cas9. *Mol Ther*. 2018;26(5):1241–1254. doi:10.1016/j.ymthe.2018.02.023
13. Breda L, Papp TE, Triebwasser MP, et al. In vivo hematopoietic stem cell modification by mRNA delivery (CD117-targeted LNP). *Science*. 2023;381(6656):436–443. doi:10.1126/science.ade6967
