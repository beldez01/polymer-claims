# Part XIII — A Research Agenda and the Hard Open Problems

> **Filed under:** Programmable Living Medicines > Part XIII
> **Created:** 2026-06-09
> **Last updated:** 2026-06-09
> **Tags:** research-agenda, open-problems, first-principles, falsifiable-predictions, in-vivo-editing, endosomal-escape, LT-HSC-tropism, potency-assay, kill-switch, sense-compute-act, decisive-experiment

## Summary

This closing chapter converts the treatise's thesis — that the unit of medicine is migrating from the **molecule** to the **program** — into a falsifiable research program. For each layer of the sense → compute → act → deliver → measure → control stack, I state the **first-principles constraint** that bounds what is achievable, the **current best number** drawn from primary literature, the **target number** a deployable programmable medicine requires, and a single **decisive experiment** that would move the field. The picture that emerges is lopsided: the *act* and *write* layers have crossed into clinical relevance (in vivo base editing now reduces a human serum protein by ~60% from a single dose; (Verve, 2025)), while the *read* layer at single-base resolution in live cells, the *deliver* layer into quiescent stem cells, and the *control* layer governing self-amplifying agents remain order-of-magnitude problems. The single highest-leverage unsolved problem is **endosomal escape** — the ~1–5% efficiency bottleneck through which every nucleic-acid program must pass — because it multiplicatively gates read, write, and deliver simultaneously. I end with the falsifiable predictions on which the molecule → program thesis stands or falls.

## Background / First Principles

A programmable living medicine is an information-processing device built from a cell or a delivered genetic payload. Like any such device it can be decomposed into Shannon-style stages, and each stage has a physical cost floor:

- **Read** is a *measurement*. Discriminating two nucleic-acid states that differ by one base is bounded by the free-energy difference ΔΔG between a matched and a single-mismatched duplex. At body temperature (kT ≈ 0.62 kcal/mol at 310 K) a single mismatch contributes only ~1–4 kcal/mol — a few kT — so the signal-to-noise of single-base discrimination is *intrinsically marginal* and must be amplified by an enzymatic proofreading step (Cas, ADAR) or by kinetic toehold competition. This is the thermodynamic reason "variant-specific live-cell flow cytometry" remains unsolved (see [genotype-directed-cytotoxicity.md §4](../opto-car/seed-report.md)).
- **Write** is *work against a repair landscape*. Editing efficiency is the product of payload delivery, target accessibility (chromatin), and the competition between the desired repair outcome and the cell's default pathways. Genotoxicity is the unavoidable tail risk: any double-strand break, and even nick-based edits, sample a distribution of off-target and on-target-but-wrong outcomes.
- **Compute** is *logic against noise*. Biological gene expression is intrinsically stochastic (Poisson-limited transcript counts, ~tens of mRNA per cell for many genes), so deep logic cascades accumulate error like an analog computer without restoration.
- **Act** is *thermodynamically downhill but biologically resisted* — killing, secreting, differentiating are all feasible; the constraint is durability against exhaustion and the physical barrier of the tumor stroma.
- **Deliver** is a *transport problem with a hard membrane barrier*. The endosomal membrane is the single largest information-loss channel in the entire stack.
- **Measure** (potency) is an *observability problem*: can we read out, before dosing, whether the program will execute?
- **Control** is a *reachability/safety problem*: can we drive the system back to a safe state after it acts, especially if it self-amplifies?

The rest of the chapter is this table, made rigorous.

## Key Findings

### READ — Live-cell single-base discrimination at throughput

**First-principles constraint.** A single base mismatch perturbs duplex stability by only ~1–4 kcal/mol (a few kT at 310 K), while the wild-type allele is often present at high copy (≈50% of transcripts in a heterozygous cell, 100% in every normal bystander). Discrimination must therefore beat a thermodynamic margin of a few kT *against an abundant decoy* — the defining difficulty.

**Current best.** RNA-level discrimination is solved in principle: ADAR-recruiting sensors (CellREADR; (Qian et al., Nature, 2022)) and reprogrammable ADAR sensors (RADARS; (Kaseniit et al., Nat Biotechnol, 2023)) convert a single-base target into payload expression in living cells, and Cas13 mismatch intolerance can silence a point-mutated transcript while sparing wild-type. **Genomic-DNA SNV discrimination in live cells at flow-cytometry throughput does not exist** — dCas9 imaging resolves repetitive loci; single-copy/SNV discrimination is demonstrated only in fixed, amplification-dependent assays (reviewed in [genotype-directed-cytotoxicity.md §4](../opto-car/seed-report.md)).

**Target.** ≥99% specificity (mutant-cell fluorescence/payload calls vs. sequencing genotype) with <1% wild-type cross-reactivity at physiological transcript abundance, in primary cells, at >10⁴ cells/s.

**Decisive experiment.** Apply a JAK2-V617F RNA sensor to homozygous (HEL 92.1.7), heterozygous (SET-2), and wild-type (K562) lines; FACS on payload fluorescence; sequence sorted ± fractions. Success = 100% concordance of fluorescence sort with sequencing, ~100% VAF in HEL-sorted-positive, ~0% in K562 despite abundant WT *JAK2* message. If wild-type-transcript rejection fails here, no downstream actuation matters. (This is the §12 staging gate in the sibling report.)

### READ — RNA-sensor specificity against abundant WT transcript

**First-principles constraint.** ADAR sensors fire only when the discriminating base sits at or adjacent to the editing-critical position (the trigger must supply a CCA context at the edited adenosine). Specificity is therefore *per-variant*, not universal, and nonsense-mediated decay destroys the very truncating-mutation transcripts you most want to sense (~76.7% of TET2 lesions are truncating; cBioPortal, per [genotype-directed-cytotoxicity.md §8](../opto-car/seed-report.md)).

**Current best.** Published RADAR sensors discriminate single-base differences (e.g., fire on WT EGFP but not a one-base mutant) but with finite fold-change and measurable basal leak.

**Target.** A design rule predicting, for an arbitrary SNV, whether a sensor with ≥50-fold on/off and <2% leak is buildable — and a Cas13-based (ADAR-independent) fallback for NMD-prone and ADAR-confounded contexts.

**Decisive experiment.** Tile sensors across a panel of recurrent oncogenic SNVs spanning all six trinucleotide contexts; regress on/off ratio against local sequence and ADAR editability to derive a predictive feasibility model.

### WRITE — In vivo editing efficiency without genotoxicity

**First-principles constraint.** Efficiency × precision is a frontier you cannot freely move along: pushing editing rate up (more nuclease, longer exposure) raises off-target and on-target-indel rates. Genotoxicity is the integral of the error distribution over every edited cell.

**Current best.** In vivo base editing is now clinical: VERVE-102 (GalNAc-LNP base editor targeting *PCSK9*) produced a mean LDL-C reduction of ~53% in the top-reported 0.6 mg/kg cohort and a maximum of ~69% from a single infusion in HEART-2, with no treatment-related serious adverse events at the data cut-off ((Verve Therapeutics, 2025); preclinical NHP PCSK9 knockdown ~80%). In vivo prime editing reached up to **46% editing in mouse liver** with optimized dual-AAV PE3 (v3em) ((Davis et al., Nat Biotechnol, 2024)). Genotoxicity surveillance, however, remains coarse-grained — large structural rearrangements and rare integration events are under-sampled by short-read off-target panels.

**Target.** ≥30% therapeutic on-target editing in the relevant tissue with a *validated* off-target/indel/rearrangement ceiling (e.g., <0.1% at any flagged site by long-read whole-genome assessment), durable for the cell's lifetime.

**Decisive experiment.** Pair a clinical-grade in vivo edit (e.g., PCSK9 base edit) with long-read whole-genome sequencing and clonal lineage tracing in treated NHP marrow/liver to bound the *full* spectrum of rearrangements, not just nominated off-targets.

### WRITE — Large-cargo in vivo integration

**First-principles constraint.** Site-specific integration of a multi-kilobase ORF requires recruiting an integrase to a programmed genomic address *and* delivering a large donor — both efficiency-limited, and the donor exceeds AAV's ~4.7 kb single-vector ceiling.

**Current best.** PASTE (Cas9-nickase–RT–serine integrase) integrates payloads as large as **~36 kb** at multiple loci in human cell lines, primary T cells, and non-dividing primary hepatocytes ((Yarnall et al., Nat Biotechnol, 2023)); in vivo demonstrations exist but at far lower, locus-dependent efficiency. PASSIGE / prime-editing-assisted integrase routes are advancing in parallel; engineered Bxb1 variants improve integration activity and fidelity ([Preprint], 2024).

**Target.** ≥10% in vivo integration of a ≥5 kb functional cargo (e.g., a full CAR or clotting-factor transgene) into a safe-harbor or endogenous locus in the target tissue, with controlled copy number.

**Decisive experiment.** Single-dose in vivo delivery of a PASTE/PASSIGE system installing a ≥5 kb reporter at *ACTB* or a safe harbor in NHP liver, quantifying integration efficiency, copy-number distribution, and concatemer/off-target integration by long-read sequencing.

### EPIGENOME — Durable yet reversible state control

**First-principles constraint.** Epigenetic marks are metastable: a written methylation or repressive state must resist dilution by replication and active erasure (TET-mediated demethylation), yet remain reversible on command. Durability and reversibility are in tension because the same machinery that locks a state can lock it irreversibly.

**Current best.** Hit-and-run epigenetic editors (dCas9–DNMT3A/3L–KRAB "CRISPRoff") install heritable silencing that propagates through cell divisions and is reversible by targeted demethylation ((Nuñez et al., Cell, 2021)). Durability in vivo, across the relevant cell's lifespan and through differentiation, is not yet established for most loci.

**Target.** Programmable silencing/activation that persists ≥1 year in vivo *and* can be deliberately reset, with locus-specificity that does not spread to neighbors. (Cross-link: the epigenetic-state durability question is the same one underlying methylation-based clonal tracking in [../chip/02_methylation_biology.md](../chip/02_methylation_biology.md) and quasi-potential well depth in [../energy-landscape-hematopoiesis/_overview.md](../energy-landscape-hematopoiesis/_overview.md).)

**Decisive experiment.** Epigenetically silence a single locus in LT-HSCs, transplant, and measure mark persistence and transcriptional state across serial transplantation and full myeloid/lymphoid differentiation — then demonstrate on-command reactivation.

### COMPUTE — Reliable deep circuit cascades against biological noise

**First-principles constraint.** Transcript copy numbers are small (often tens per cell) so each logic node is Poisson-noisy; serial gates compound error multiplicatively, and there is no native signal-restoration ("digital regeneration") step. Depth is therefore bounded by accumulated analog error.

**Current best.** Robust 2–3-input logic is routine (synNotch AND-gates; ADAR AND/OR; SENTI-style OR-NOT gates on surface markers), and Strand Therapeutics' SignalLock-class mRNA circuits implement multi-state logic — but reliable *deep* (≥4-layer) cascades with bounded error in primary cells in vivo remain unproven.

**Target.** A ≥4-input classifier (e.g., variant AND lineage AND tumor-microenvironment AND a safety NOT-gate) with <5% misclassification across the physiological noise range, in primary human cells.

**Decisive experiment.** Build a 4-input cell classifier with an explicit digital-restoration element (e.g., a toggle/latch that thresholds an analog input to a binary state) and measure misclassification as a function of input transcript abundance across two logs.

### ACT — Exhaustion-proof persistence and solid-tumor penetration

**First-principles constraint.** Chronic antigen drives an epigenetically *fixed* exhaustion program; persistence requires holding cells in a stem-like/memory state against that pressure. Solid-tumor penetration is a transport-plus-suppression problem: physical stroma and an immunosuppressive, hypoxic, nutrient-poor microenvironment.

**Current best.** Epigenetic reprogramming extends persistence: *TET2* disruption in CAR-T blocks the chromatin program that limits memory formation, biasing toward a CCR7⁺CD45RO⁺ TCF1-high memory phenotype and improving persistence and expansion — at the cost of a malignant-transformation tail risk ((Fraietta et al., Nature, 2018, the index TET2-CAR-T patient; reviewed 2024–2025)). Solid-tumor CAR-T responses remain markedly inferior to hematologic ones.

**Target.** Functional persistence ≥1 year with retained killing, and ≥10-fold improvement in intratumoral effective T-cell density in solid tumors — without genotoxic transformation risk.

**Decisive experiment.** Head-to-head, in a solid-tumor model, of epigenetically/transcriptionally armored CAR-T (e.g., regulated *TET2*/*DNMT3A* modulation plus a stroma-degrading or chemokine-receptor module) measuring intratumoral density, durable function, and clonal safety by integration-site/lineage tracking. (See [../cell-therapy-qc/universal-functional-potency-2026.md](../cell-therapy-qc/universal-functional-potency-2026.md).)

### DELIVER — Quiescent-LT-HSC tropism and endosomal escape

**First-principles constraint (tropism).** The cells that *matter most* for durable cure — long-term HSCs — are rare, marrow-sequestered, and transcriptionally near-silent. A fraction of LT-HSCs divides only about once every ~18 years (extrapolated from murine dormant-HSC kinetics; only ~20–30% cycle every ~150–200 days). Low transcription means low target-mRNA *and* low endocytic uptake — the worst case for both sensing and delivery.

**First-principles constraint (escape).** Nucleic-acid cargo internalized into an endosome must cross a lipid bilayer into the cytosol before lysosomal degradation. This is the dominant loss channel in the stack.

**Current best (tropism).** Receptor-targeted LNPs now reach HSCs in vivo: anti-CD117/c-Kit antibody-LNP delivered mRNA to ~90% of LT-HSCs in a single IV dose; a CD45-targeted LNP gave ~7× hematopoietic delivery (per [genotype-directed-cytotoxicity.md §10](../opto-car/seed-report.md)). But these reach *cycling-competent* HSCs; the deeply dormant pool is still under-served. IFN-α priming (Essers et al., Nature, 2009) can wake dormant HSCs into cycle — and does so *preferentially* in JAK2-mutant clones — making "wake-then-deliver" a credible workaround.

**Current best (escape).** For state-of-the-art ionizable lipids, SNAPSwitch-based cytosolic-delivery quantification gives **~10% endosomal escape for SM-102, ~5% for MC3, ~4% for ALC-0315** ((Liu et al., Adv Funct Mater, 2024)); earlier image-based siRNA-LNP estimates put escape at **<2%** of internalized cargo ((Gilleron et al., Nat Biotechnol, 2013; reviewed in Chatterjee et al., PNAS, 2024)). The ~90–95% loss is, today, simply tolerated.

**Target.** Functional payload delivery to ≥50% of the *dormant* LT-HSC pool; endosomal escape ≥25% (a ~5-fold gain over the best current lipid).

**Decisive experiment (escape).** Use the single-molecule RNASCAPE-class assay ([Preprint], 2026) to screen ionizable-lipid / peptide / proton-sponge chemistries against directly counted cytosolic-escape efficiency (not bulk reporter expression), establishing whether the bilayer barrier is chemically movable past ~10% or is a hard physical ceiling.

### MEASURE — A universal potency assay

**First-principles constraint.** Potency is *function*, which is multi-dimensional (kill, secrete, persist, metabolic fitness) and emerges only on engagement — so any single scalar surrogate (e.g., transduction %, IFN-γ release) is an incomplete observable of the deployed program.

**Current best.** Release testing relies on surrogate scalars; functional, single-cell, multi-readout potency assays (killing + metabolic state on the same cells) are an active frontier without a standardized universal assay (see [../cell-therapy-qc/universal-functional-potency-2026.md](../cell-therapy-qc/universal-functional-potency-2026.md) and the trajectory/mitochondrial assay in [../cell-therapy-qc/epigenetic-mitochondrial-trajectory-assay.md](../cell-therapy-qc/epigenetic-mitochondrial-trajectory-assay.md)).

**Target.** A pre-infusion assay whose readout predicts in vivo expansion, persistence, and tumor control with documented correlation (R² to clinical response) — qualified across products.

**Decisive experiment.** Bank pre-infusion functional fingerprints (single-cell killing kinetics + metabolic/epigenetic state) on a clinical CAR-T cohort and retrospectively regress against measured in vivo expansion and response, identifying the minimal predictive feature set.

### CONTROL — Reversibility of in vivo edits and governing self-amplifying agents

**First-principles constraint.** A permanent edit has no "off." A self-amplifying agent (self-replicating RNA, an expanding engineered clone, a gene drive-like circuit) has positive feedback, so error or off-target action can grow exponentially — the reachability of a safe state must be *designed in*, not discovered post hoc.

**Current best.** Suicide switches exist (iCasp9/AP1903 ablates engineered T cells within ~30 min; (Di Stasi et al., NEJM, 2011)); small-molecule on/off CARs and degron/dimerizer control allow titration. But these govern *delivered cells*, not *installed edits*: there is no general method to reverse an in vivo genomic edit, and no validated containment for a self-amplifying genetic agent that has integrated or spread.

**Target.** (a) A "molecular undo" — on-command reversal or silencing of an installed in vivo edit; (b) for self-amplifying agents, a kill-switch with demonstrated containment under selection pressure (i.e., escape mutants cannot outrun it), e.g., via redundant, orthogonal switches and OR-multiplexed dependencies.

**Decisive experiment.** Install a reversible in vivo edit gated by an inducible epigenetic silencer plus an excisable integrase-flanked cassette; demonstrate on-command transcriptional reversal *and* physical excision in vivo, then challenge the kill-switch with a selection screen to measure escape frequency.

## Counterintuitive & Groundbreaking Applications

Several of these constraints, inverted, become the field's most valuable opportunities:

- **Quiescence as the moat, not the bug.** The same dormancy that makes LT-HSCs nearly impossible to read or transduce makes them the durable reservoir of disease. "Wake-then-act" — IFN-α priming to drive the (preferentially mutant) clone into cycle, *then* sense/deliver/kill — converts the hardest delivery target into a *timed* one. This is the rare case where the disease biology hands you a clock.
- **Escape that is coupled to de-oncogenesis.** Targeting the oncogenic *driver* transcript (rather than a dispensable surface antigen) means a tumor can only evade by surrendering its fitness advantage — target-loss and fitness-loss are coupled, the structural advantage developed in [genotype-directed-cytotoxicity.md §11](../opto-car/seed-report.md). No surface-phenotype therapy has this property.
- **Endosomal escape as the universal valuation lever.** Because escape multiplies every downstream layer, a 5-fold escape improvement is worth more than a 5-fold gain in any single layer — a delivery-chemistry breakthrough is the highest-ROI commercial asset in the entire stack, and it is *modality-agnostic* (it lifts siRNA, mRNA, base editors, and sensors simultaneously).
- **The potency assay as the platform's data flywheel.** Whoever owns the predictive pre-infusion functional fingerprint owns the qualification standard — and accumulates a labeled dataset (function → outcome) that compounds. Potency prediction is the regulatory choke point and therefore the durable business.
- **Trans-cellular BRET as a contact-gated kill currency.** The near-field optical coupling worked out in [genotype-directed-cytotoxicity.md §9, §15](../opto-car/seed-report.md) makes "genotype AND physical synapse" an intrinsic logic gate — a control-theoretic safety property achieved by physics rather than by an added circuit.

## Open Questions

1. Is genomic-DNA single-base discrimination in *live* cells physically achievable at throughput, or is it permanently a fixed-cell assay (the ΔΔG-vs-kT wall)?
2. Can endosomal escape be pushed past ~10–25%, or is the bilayer barrier a hard ceiling that forces all programs to over-deliver by 10–100×?
3. Does TET2/DNMT3A epigenetic armoring of CAR-T carry an *acceptable* transformation risk, or does it trade efficacy for a leukemia tail that disqualifies it?
4. Can deep (≥4-layer) synthetic logic be made noise-robust without a native digital-restoration mechanism, or does biological stochasticity cap useful circuit depth?
5. Is there any general method to *reverse* an installed in vivo genomic edit — and can a self-amplifying agent ever be provably contained under selection?
6. Will a universal functional potency assay actually predict in vivo behavior, or is potency irreducibly product- and patient-specific?

## What Must Be True for the Molecule → Program Thesis to Hold (Falsifiable Predictions)

The thesis is not a slogan; it makes testable claims that could be wrong:

- **P1 (Read).** *A live cell can be made to report its own somatic genotype with ≥99% specificity against abundant wild-type transcript.* Falsified if RNA-sensor specificity cannot be driven below ~1% wild-type cross-reactivity at physiological abundance in primary cells. (Test: the JAK2 sort-then-seq gate above.)
- **P2 (Compute).** *Synthetic logic of depth ≥3 outperforms single-input targeting on a clinically meaningful selectivity metric in vivo.* Falsified if added logic layers degrade rather than improve the therapeutic index because noise dominates.
- **P3 (Act).** *Programs that read the driver are harder to escape than programs that read a surface phenotype.* Falsified if driver-targeting therapies relapse at rates indistinguishable from antigen-loss kinetics (i.e., if neutral sensor-footprint mutations escape as readily as antigen down-regulation).
- **P4 (Deliver).** *Targeted delivery can reach a therapeutically sufficient fraction of the disease-reservoir cell (dormant LT-HSC) in vivo.* Falsified if no chemistry delivers functional payload to >~10% of the deeply dormant pool even with priming.
- **P5 (Control).** *Self-amplifying and edit-based programs can be returned to a safe state on command.* Falsified if no in vivo edit-reversal or selection-resistant kill-switch can be demonstrated — in which case programmable medicine is permanently limited to delivered-cell modalities with external suicide switches.

If P1, P4, and P5 all fail, the program-medicine thesis collapses back to the molecule paradigm. If P3 holds even partially, the field has a durable structural advantage that the molecule paradigm can never possess.

## Connections

- **Read/Act/Control frontier, fully worked example:** [../immunology/genotype-directed-cytotoxicity.md](../opto-car/seed-report.md) — the genotype-gated, BRET-coupled, contact-restricted kill architecture that instantiates this agenda end-to-end (its §12 staging *is* the READ decisive experiment here).
- **Sibling chapters:** [./01-first-principles-programmable-cell.md](./01-first-principles-programmable-cell.md) (the sense → compute → act frame this chapter closes), and the read/write/deliver chapters whose open edges this agenda inventories.
- **Potency/measure layer:** [../cell-therapy-qc/universal-functional-potency-2026.md](../cell-therapy-qc/universal-functional-potency-2026.md), [../cell-therapy-qc/epigenetic-mitochondrial-trajectory-assay.md](../cell-therapy-qc/epigenetic-mitochondrial-trajectory-assay.md).
- **Epigenome durability:** [../chip/02_methylation_biology.md](../chip/02_methylation_biology.md), [../epigenetics/methylation-gene-regulation.md](../epigenetics/methylation-gene-regulation.md), [../epigenetics/tet2-macrophage-immunophenotype.md](../epigenetics/tet2-macrophage-immunophenotype.md).
- **State-control landscape:** [../energy-landscape-hematopoiesis/_overview.md](../energy-landscape-hematopoiesis/_overview.md) (quasi-potential well depth = epigenetic durability, formalized).
- **Machine-readable biology (the measurement layer's north star):** [../precision-medicine/machine-readable-biology.md](../precision-medicine/machine-readable-biology.md).

## Synthesis: The Next Decade and the Single Highest-Leverage Problem

The decade's trajectory is asymmetric. The **write** and **act** layers have already crossed the clinical threshold — in vivo base editing now durably lowers a human serum protein from one dose, and epigenetic armoring is extending CAR-T persistence — so the next ten years will be dominated not by *whether* we can edit and act, but by *control and measurement*: reversibility, containment, and a predictive potency standard. The **read** layer will mature at the RNA level (variant-gated sensing reaching the clinic for a first indication, most plausibly JAK2-V617F MPN) while live-cell genomic-DNA discrimination likely remains unsolved — pushing the field, correctly, toward *report-the-variant* rather than *bind-the-variant* architectures.

The single highest-leverage unsolved problem is **endosomal escape**. It is the one term that multiplies *every* nucleic-acid modality — sensor delivery, in vivo editing, LNP-CAR generation, HSC reprogramming — and it currently throws away 90–98% of internalized cargo. A chemistry that moves escape from ~5% to ~25% would, in a single stroke, make in vivo editing safer (lower dose, less off-target exposure), make rare-cell delivery (dormant LT-HSCs) feasible, and make genotype-sensing precise enough to gate killing. Every other problem on this list is bounded by it. The molecule → program transition will be paced not by our cleverness at writing programs, but by our ability to get them across one lipid bilayer.

## References

1. Verve Therapeutics. Positive initial data from the HEART-2 Phase 1b trial of VERVE-102, an in vivo base editing medicine targeting PCSK9. Company release / CGTLive coverage, 2025. (Mean LDL-C reduction ~53–59%, max ~69%; NHP preclinical PCSK9 knockdown ~80%.) https://www.cgtlive.com/view/verve-therapeutics-base-editing-therapy-verve-102-reduces-ldl-c-patients-hefh-cad

2. Qian Y, Li J, Zhao S, et al. Programmable RNA sensing for cell monitoring and manipulation (CellREADR). Nature. 2022;610:713–721. doi:10.1038/s41586-022-05280-1

3. Kaseniit KE, Katz N, Kolber NS, et al. Modular, programmable RNA sensing using ADAR editing in living cells (RADARS). Nat Biotechnol. 2023;41:482–487. doi:10.1038/s41587-022-01493-x

4. Jiang K, Koob J, Chen XD, et al. Programmable eukaryotic protein synthesis with RNA sensors by harnessing ADAR (RADAR). Nat Biotechnol. 2023;41:698–707. doi:10.1038/s41587-022-01534-5

5. Davis JR, Banskota S, Levy JM, et al. Efficient prime editing in mouse brain, liver and heart with dual AAVs. Nat Biotechnol. 2024;42:253–264. (Up to ~46% liver editing with v3em PE3-AAV9.) doi:10.1038/s41587-023-01758-z

6. Yarnall MTN, Ioannidi EI, Schmitt-Ulms C, et al. Drag-and-drop genome insertion of large sequences without double-strand DNA cleavage using CRISPR-directed integrases (PASTE). Nat Biotechnol. 2023;41:500–512. (~36 kb insertions.) doi:10.1038/s41587-022-01527-4

7. Engineered Bxb1 variants improve integrase activity and fidelity. bioRxiv. 2024. [Preprint]. doi:10.1101/2024.10.21.619419

8. Nuñez JK, Chen J, Pommier GC, et al. Genome-wide programmable transcriptional memory by CRISPR-based epigenome editing (CRISPRoff). Cell. 2021;184:2503–2519. doi:10.1016/j.cell.2021.03.025

9. Fraietta JA, Nobles CL, Sammons MA, et al. Disruption of TET2 promotes the therapeutic efficacy of CD19-targeted T cells. Nature. 2018;558:307–312. doi:10.1038/s41586-018-0178-z

10. Chatterjee S, Kon E, Sharma P, Peer D. Endosomal escape: A bottleneck for LNP-mediated therapeutics. Proc Natl Acad Sci USA. 2024;121:e2307800120. (Review; supports the siRNA-LNP <2% cytosolic-escape figure as background.) doi:10.1073/pnas.2307800120

10b. Liu Y, et al. Beyond the Endosomal Bottleneck: Understanding the Efficiency of mRNA/LNP Delivery. Adv Funct Mater. 2024. (Source of the per-lipid SNAPSwitch escape estimates: SM-102 ~10%, MC3 ~5%, ALC-0315 ~4%.) doi:10.1002/adfm.202404510

10c. Gilleron J, Querbes W, Zeigerer A, et al. Image-based analysis of lipid nanoparticle-mediated siRNA delivery, intracellular trafficking and endosomal escape. Nat Biotechnol. 2013;31:638–646. (Direct colloidal-gold quantification: ~1–2% siRNA endosomal escape.) doi:10.1038/nbt.2612

11. Rapid and reliable quantification of cytosolic mRNA escape (RNASCAPE). bioRxiv. 2026. [Preprint]. https://www.biorxiv.org/content/10.64898/2026.04.07.716953v1

12. Essers MAG, Offner S, Blanco-Bose WE, et al. IFNα activates dormant haematopoietic stem cells in vivo. Nature. 2009;458:904–908. doi:10.1038/nature07815

13. Wilson A, Laurenti E, Oser G, et al. Hematopoietic stem cells reversibly switch from dormancy to self-renewal during homeostasis and repair. Cell. 2008;135:1118–1129. (Deeply dormant HSCs; human extrapolation ~once per ~18 years.) doi:10.1016/j.cell.2008.10.048

14. Di Stasi A, Tey SK, Dotti G, et al. Inducible apoptosis as a safety switch for adoptive cell therapy (iCasp9/AP1903). N Engl J Med. 2011;365:1673–1683. doi:10.1056/NEJMoa1106152

15. Belden Z. Genotype-Directed Cytotoxicity: Detecting Intracellular Variants and Painting Them for Immune Attack. Internal library report, 2026. [../immunology/genotype-directed-cytotoxicity.md]
