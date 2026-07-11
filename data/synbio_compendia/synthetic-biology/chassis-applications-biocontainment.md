# Chassis Organisms, Engineered Living Systems, and Biocontainment: A Techniques Compendium

> **Filed under:** Synthetic Biology > Chassis, Applications & Biocontainment
> **Created:** 2026-07-04
> **Last updated:** 2026-07-04
> **Tags:** chassis-organisms, engineered-living-materials, biocontainment, kill-switches, living-therapeutics, synNotch, biosensors, biosecurity

## Summary
This report surveys the "applications and safety" layer of synthetic biology: the host organisms (chassis) into which engineered circuits are placed, the living systems built from them (therapeutics, biosensors, materials, consortia), and the biocontainment techniques that keep them from persisting or spreading where they should not. Chassis selection trades growth rate, genetic tractability, post-translational capability, and environmental fit; mammalian chassis have enabled a generation of logic-gated cell therapies, while microbial chassis power living diagnostics, drugs, and materials. Safety has matured from simple auxotrophy to synthetic auxotrophy on non-canonical amino acids and genome-scale recoding that build genetic firewalls resistant to escape. Governance context, from Asilomar through DNA-synthesis screening, frames the whole enterprise.

## Background
A "chassis" is a host cell whose native metabolism, replication, and gene-expression machinery are borrowed to run engineered genetic programs. The field's arc, from the year-2000 toggle switch and repressilator through cellular therapeutics and engineered materials, is charted by Cameron, Bashor, and Collins [1]. Early work concentrated on *Escherichia coli* and *Saccharomyces cerevisiae* because their genetics were deepest, but as ambitions moved from proof-of-concept circuits toward deployed living systems (in patients, in soil, in bioreactors, in the environment), two questions became central: which host best fits the application, and how do we prevent an engineered organism from escaping containment or evolving away from its safeguards. Those two questions define this compendium.

## Key Findings

### Chassis organisms and selection criteria
Choosing a chassis balances doubling time, ease of DNA delivery and genome editing, tolerance to process conditions, secretion and folding capacity, post-translational modification (glycosylation), safety/regulatory status, and environmental niche.

**Microbial workhorses.** *E. coli* remains the default for fast prototyping, high-titer protein expression, and the richest toolkit. *Bacillus subtilis*, a Gram-positive GRAS organism, is favored for secreted enzymes and for its robust sporulating physiology; its synthetic-biology toolbox and genome-reduced chassis strains are reviewed by Liu and colleagues [2]. *S. cerevisiae* is the eukaryotic model of choice: it performs compartmentalization and some post-translational processing, and tolerates industrial fermentation.

**Specialized bacterial chassis.** *Pseudomonas putida* KT2440 is a solvent- and redox-stress-tolerant soil bacterium with an unusually high NADPH regenerating capacity, making it a preferred host for aromatic-compound catabolism and harsh biocatalysis; Nikel and de Lorenzo frame it as a "functional chassis" whose environmental ruggedness is its selling point [3]. Cyanobacteria such as *Synechococcus elongatus* are photosynthetic chassis that fix CO2 using light; the fast-growing strain UTEX 2973 (doubling ~1.9 h) narrowed the growth-rate gap that historically limited photoautotrophic production [4].

**Fast-growing chassis.** *Vibrio natriegens* has the fastest known doubling time of any organism (under 10 minutes); Weinstock et al. developed genetic tools that position it as a potential next-generation *E. coli* for molecular biology and bioproduction [5].

**Mammalian and higher chassis.** Chinese hamster ovary (CHO) cells dominate biologics manufacturing because they perform human-like glycosylation; the CHO-K1 genome sequence provided the reference for rational cell-line engineering [6]. HEK293 cells are the standard mammalian prototyping host for circuits and viral-vector production. Plant chassis (e.g., *Nicotiana benthamiana*) enable molecular farming, and primary/engineered human T cells serve as the chassis for cell therapies discussed below. The selection logic is consistent: match the host's intrinsic biology (glycosylation for antibodies, photoautotrophy for CO2 capture, solvent tolerance for chemistry) to the application, then layer circuitry on top.

### Mammalian synthetic biology and engineered cell therapies
Mammalian gene circuits depend on tunable switches. The tetracycline-controlled Tet-Off/Tet-On systems of Gossen and Bujard remain the foundational small-molecule transcriptional switch, giving reversible on/off control in mammalian cells [7]. For post-translational control, Banaszynski et al. introduced destabilizing domains (a mutant FKBP12 that drives fusion-protein degradation unless a synthetic ligand, Shield-1, is present), providing rapid, reversible, dose-tunable control of protein levels [8].

The most consequential advance is the synthetic Notch (synNotch) receptor from the Lim lab. Morsut, Roybal et al. rebuilt Notch into a modular chassis-independent receptor: a custom extracellular binder senses an arbitrary antigen, and ligand engagement releases an intracellular transcription factor that drives a user-defined program, with orthogonal pathways that do not cross-talk [9]. Roybal et al. then used synNotch to build AND-gate T cells: a synNotch for antigen 1 induces a chimeric antigen receptor (CAR) for antigen 2, so only dual-antigen tumors are killed and single-antigen normal tissue is spared, improving the precision and safety of cell therapy [10]. This logic-gating sits atop conventional CAR design, whose basic principles (signaling domain architecture, costimulation) were codified by Sadelain, Brentjens, and Rivière [11]. Kitada, DiAndreth, Teague, and Weiss reviewed how these building blocks combine into programmable gene and engineered-cell therapies that sense disease biomarkers and activate context-specifically [12].

### Engineered living therapeutics and probiotics
Live bacteria can be engineered into diagnostics and drugs. Danino et al. built programmable probiotics from *E. coli* Nissle 1917 that selectively colonize liver metastases and produce a LacZ reporter yielding a detectable urine signal, a noninvasive diagnostic [13]. Synlogic's synthetic biotic SYNB1618 engineers *E. coli* Nissle to express phenylalanine-metabolizing enzymes under anoxic gut-responsive promoters, lowering blood Phe in PKU mouse and primate models (Isabella et al.) [14]; the strain advanced to a first-in-human phase 1/2a study confirming safety and Phe-metabolite pharmacodynamics [15]. Riglar et al. engineered a commensal *E. coli* with a memory circuit that records tetrathionate exposure, functioning as a living diagnostic of gut inflammation stable for six months in the mouse gut [16]. The Joshi lab's PATCH strategy engineers Nissle to secrete curli fibers displaying therapeutic domains that tether to the mucosa and ameliorate colitis [17]. Cubillos-Ruiz et al. provide the synthesis review of this "engineering living therapeutics" field, including containment and manufacturing considerations [18].

### Whole-cell biosensors
Whole-cell biosensors couple a native or synthetic promoter (responsive to a target analyte) to a reporter output. Van der Meer and Belkin review the design of reporter bacteria for environmental and clinical sensing, including heavy-metal (arsenic, mercury) and toxicity bioreporters, and the challenge of translating lab constructs to field devices [19]. The frontier is integration with electronics: Mimee et al. built an ingestible micro-bio-electronic device pairing heme-sensitive probiotic bacteria with low-power luminescence readout circuitry that wirelessly reports gastrointestinal bleeding to a smartphone [20]. This "bacteria-on-a-chip" pattern (living sensor plus silicon transducer) generalizes to wearable and ingestible diagnostics.

### Microbial consortia and division of labor
Loading an entire multi-step pathway onto one strain imposes metabolic burden and expression trade-offs. Distributing pathway modules across specialized populations, a metabolic division of labor, can reduce per-cell burden and improve overall output; Tsoi et al. analyze when division of labor outperforms a single engineered population and the conditions (coexistence, exchange of intermediates) required for a stable consortium [21]. Synthetic consortia also enable spatial patterning and compartmentalized incompatible chemistries, at the cost of needing engineered stability mechanisms to prevent one member from outcompeting the others.

### Engineered living materials (ELMs)
ELMs use living cells to grow, pattern, or repair a material. The Joshi lab's Biofilm-Integrated Nanofiber Display (BIND) genetically appends peptide domains to CsgA, the curli amyloid subunit of *E. coli* biofilms; the secreted fusions self-assemble into functional nanofiber networks that can template nanoparticles, adhere to surfaces, or immobilize enzymes [22]. Nguyen, Courchesne, Duraj-Thatte, and Joshi review the broader ELM field, framing the design challenge as coupling genetic programmability to material self-assembly, and its prospects for self-healing, responsive, and living materials [23].

### Biocontainment and safety
Containment techniques form a layered defense against escape and horizontal gene transfer.

**Auxotrophy and synthetic auxotrophy.** Classic auxotrophy makes a strain depend on a nutrient absent from the environment, but escape via metabolic cross-feeding or mutation is common. Synthetic auxotrophy raises the barrier by making essential proteins depend on a non-canonical amino acid (ncAA) that does not exist in nature. Mandell et al. computationally redesigned essential enzymes to require a synthetic ncAA in their cores, achieving escape frequencies below detection and resistance to environmental supplementation [24]. In parallel, Rovner et al. recoded organisms so that multiple essential genes require ncAA incorporation, engineering an orthogonal biological barrier between the organism and the environment [25]. These strategies rest on genomically recoded organisms (GROs): Lajoie et al. replaced all UAG stop codons in *E. coli* and deleted release factor 1, freeing a codon for dedicated ncAA incorporation and conferring resistance to some viruses [26].

**Kill switches.** Chan et al. built two synthetic-biology kill switches: "Deadman," which uses unbalanced reciprocal repression so that loss of a survival-signal input triggers a toxin and cell death, and "Passcode," which uses hybrid LacI/GalR transcription factors so that only a specific combination of environmental inputs keeps cells alive [27]. These give programmable, environmentally-conditional containment.

**Genetic firewalls via recoding.** Whole-genome recoding creates a "genetic firewall": a recoded genome mistranslates or cannot express standard genes acquired by horizontal transfer, and can be made resistant to natural viruses. Ostrov et al. designed and began building a 57-codon *E. coli* genome removing seven codons genome-wide [28], and Fredens et al. achieved the total synthesis of a fully recoded, functional *E. coli* (Syn61) using only 61 codons [29]. A firewall of this kind can be combined with ncAA dependence for orthogonal, evolution-resistant containment.

**Gene drives and their containment.** Gene drives bias inheritance to spread a trait through a wild population and are inherently the opposite of contained. Esvelt et al. laid out the capabilities and risks of CRISPR-based RNA-guided gene drives and proposed precautionary containment and reversal strategies [30]. Gantz and Bier demonstrated the "mutagenic chain reaction," a highly efficient CRISPR drive in *Drosophila* [31], underscoring the power and hazard. DiCarlo et al. validated molecular confinement strategies (synthetic target sites, split drives, reversal drives) for CRISPR-Cas9 gene drives in yeast, providing laboratory-safety practices for drive research [32].

**Governance and biosecurity.** The safety ethos traces to the 1975 Asilomar conference, where researchers self-imposed a moratorium and containment guidelines on recombinant DNA; Berg's retrospective reflects on its legacy and limits [33]. Modern dual-use concern centers on commercial DNA synthesis: Diggans and Leproust describe sequence-screening approaches and the policy steps needed to keep synthesis access safe and secure as costs fall [34]. Together these define the governance envelope, self-regulation, screening, and dual-use oversight, within which the technical containment methods operate.

## Open Questions
- How durable is synthetic auxotrophy over long-term, large-population deployments, and can multiple orthogonal barriers be stacked without fitness collapse?
- Can kill switches remain stable against mutational inactivation in the field, where selection favors escape mutants, without continuous engineering maintenance?
- What containment is adequate for gene drives intended for open release, and who decides? Reversal and immunizing drives remain unproven at ecological scale.
- How do we make recoded "firewall" genomes economical enough to become the default chassis for environmental release rather than bespoke research strains?
- For living therapeutics, what regulatory framework governs an evolving, replicating drug, and how is potency defined for an organism that changes in vivo?
- Can DNA-synthesis screening keep pace with foundation-model-assisted design of sequences of concern?

## Connections
- **Genetic circuits:** Chassis performance sets the operating envelope for toggle switches, oscillators, and logic gates; kill switches and Deadman/Passcode are themselves genetic circuits repurposed for safety. See also: [Genetic Circuit Design and Regulatory Parts](genetic-circuits-and-parts.md)
- **Genome editing:** CRISPR underlies both gene drives and the multiplex editing used to build recoded genomes and integrate circuits into mammalian and microbial chassis. See also: [Genome Editing and Targeted Genome Engineering](genome-editing-tools.md)
- **Expanded genetic code:** Synthetic auxotrophy and genetic firewalls depend directly on ncAA incorporation and genomic recoding. See also: [Expanded Genetic Code and Xenobiology](expanded-genetic-code-xenobiology.md)
- **Metabolic engineering:** Chassis choice and microbial division of labor are the substrate on which pathway engineering for chemicals and materials is executed. See also: [Metabolic Engineering and Pathway Optimization](metabolic-engineering.md)
- **Synthetic genomics:** Genetic firewalls are built with the whole-genome recoding techniques of synthetic genomics. See also: [Synthetic Genomics and Minimal Genomes](synthetic-genomics-minimal-genomes.md)

## References
1. Cameron DE, Bashor CJ, Collins JJ. A brief history of synthetic biology. Nat Rev Microbiol. 2014;12(5):381–390. doi:10.1038/nrmicro3239
2. Liu Y, Liu L, Li J, Du G, Chen J. Synthetic biology toolbox and chassis development in Bacillus subtilis. Trends Biotechnol. 2019;37(5):548–562. doi:10.1016/j.tibtech.2018.10.005
3. Nikel PI, de Lorenzo V. Pseudomonas putida as a functional chassis for industrial biocatalysis: from native biochemistry to trans-metabolism. Metab Eng. 2018;50:142–155. doi:10.1016/j.ymben.2018.05.005
4. Yu J, Liberton M, Cliften PF, et al. Synechococcus elongatus UTEX 2973, a fast growing cyanobacterial chassis for biosynthesis using light and CO2. Sci Rep. 2015;5:8132. doi:10.1038/srep08132
5. Weinstock MT, Hesek ED, Wilson CM, Gibson DG. Vibrio natriegens as a fast-growing host for molecular biology. Nat Methods. 2016;13(10):849–851. doi:10.1038/nmeth.3970
6. Xu X, Nagarajan H, Lewis NE, et al. The genomic sequence of the Chinese hamster ovary (CHO)-K1 cell line. Nat Biotechnol. 2011;29(8):735–741. doi:10.1038/nbt.1932
7. Gossen M, Bujard H. Tight control of gene expression in mammalian cells by tetracycline-responsive promoters. Proc Natl Acad Sci USA. 1992;89(12):5547–5551. doi:10.1073/pnas.89.12.5547
8. Banaszynski LA, Chen LC, Maynard-Smith LA, Ooi AGL, Wandless TJ. A rapid, reversible, and tunable method to regulate protein function in living cells using synthetic small molecules. Cell. 2006;126(5):995–1004. doi:10.1016/j.cell.2006.07.025
9. Morsut L, Roybal KT, Xiong X, et al. Engineering customized cell sensing and response behaviors using synthetic Notch receptors. Cell. 2016;164(4):780–791. doi:10.1016/j.cell.2016.01.012
10. Roybal KT, Rupp LJ, Morsut L, et al. Precision tumor recognition by T cells with combinatorial antigen-sensing circuits. Cell. 2016;164(4):770–779. doi:10.1016/j.cell.2016.01.011
11. Sadelain M, Brentjens R, Rivière I. The basic principles of chimeric antigen receptor design. Cancer Discov. 2013;3(4):388–398. doi:10.1158/2159-8290.CD-12-0548
12. Kitada T, DiAndreth B, Teague B, Weiss R. Programming gene and engineered-cell therapies with synthetic biology. Science. 2018;359(6376):eaad1067. doi:10.1126/science.aad1067
13. Danino T, Prindle A, Kwong GA, et al. Programmable probiotics for detection of cancer in urine. Sci Transl Med. 2015;7(289):289ra84. doi:10.1126/scitranslmed.aaa3519
14. Isabella VM, Ha BN, Castillo MJ, et al. Development of a synthetic live bacterial therapeutic for the human metabolic disease phenylketonuria. Nat Biotechnol. 2018;36(9):857–864. doi:10.1038/nbt.4222
15. Puurunen MK, Vockley J, Searle SL, et al. Safety and pharmacodynamics of an engineered E. coli Nissle for the treatment of phenylketonuria: a first-in-human phase 1/2a study. Nat Metab. 2021;3(8):1125–1132. doi:10.1038/s42255-021-00430-7
16. Riglar DT, Giessen TW, Baym M, et al. Engineered bacteria can function in the mammalian gut long-term as live diagnostics of inflammation. Nat Biotechnol. 2017;35(7):653–658. doi:10.1038/nbt.3879
17. Praveschotinunt P, Duraj-Thatte AM, Gelfat I, Bahl F, Chou DB, Joshi NS. Engineered E. coli Nissle 1917 for the delivery of matrix-tethered therapeutic domains to the gut. Nat Commun. 2019;10:5580. doi:10.1038/s41467-019-13336-6
18. Cubillos-Ruiz A, Guo T, Sokolovska A, et al. Engineering living therapeutics with synthetic biology. Nat Rev Drug Discov. 2021;20(12):941–960. doi:10.1038/s41573-021-00285-3
19. van der Meer JR, Belkin S. Where microbiology meets microengineering: design and applications of reporter bacteria. Nat Rev Microbiol. 2010;8(7):511–522. doi:10.1038/nrmicro2392
20. Mimee M, Nadeau P, Hayward A, et al. An ingestible bacterial-electronic system to monitor gastrointestinal health. Science. 2018;360(6391):915–918. doi:10.1126/science.aas9315
21. Tsoi R, Wu F, Zhang C, Bewick S, Karig D, You L. Metabolic division of labor in microbial systems. Proc Natl Acad Sci USA. 2018;115(10):2526–2531. doi:10.1073/pnas.1716888115
22. Nguyen PQ, Botyanszki Z, Tay PKR, Joshi NS. Programmable biofilm-based materials from engineered curli nanofibres. Nat Commun. 2014;5:4945. doi:10.1038/ncomms5945
23. Nguyen PQ, Courchesne NMD, Duraj-Thatte A, Praveschotinunt P, Joshi NS. Engineered living materials: prospects and challenges for using biological systems to direct the assembly of smart materials. Adv Mater. 2018;30(19):1704847. doi:10.1002/adma.201704847
24. Mandell DJ, Lajoie MJ, Mee MT, et al. Biocontainment of genetically modified organisms by synthetic protein design. Nature. 2015;518(7537):55–60. doi:10.1038/nature14121
25. Rovner AJ, Haimovich AD, Katz SR, et al. Recoded organisms engineered to depend on synthetic amino acids. Nature. 2015;518(7537):89–93. doi:10.1038/nature14095
26. Lajoie MJ, Rovner AJ, Goodman DB, et al. Genomically recoded organisms expand biological functions. Science. 2013;342(6156):357–360. doi:10.1126/science.1241459
27. Chan CTY, Lee JW, Cameron DE, Bashor CJ, Collins JJ. 'Deadman' and 'Passcode' microbial kill switches for bacterial containment. Nat Chem Biol. 2016;12(2):82–86. doi:10.1038/nchembio.1979
28. Ostrov N, Landon M, Guell M, et al. Design, synthesis, and testing toward a 57-codon genome. Science. 2016;353(6301):819–822. doi:10.1126/science.aaf3639
29. Fredens J, Wang K, de la Torre D, et al. Total synthesis of Escherichia coli with a recoded genome. Nature. 2019;569(7757):514–518. doi:10.1038/s41586-019-1192-5
30. Esvelt KM, Smidler AL, Catteruccia F, Church GM. Concerning RNA-guided gene drives for the alteration of wild populations. eLife. 2014;3:e03401. doi:10.7554/eLife.03401
31. Gantz VM, Bier E. The mutagenic chain reaction: a method for converting heterozygous to homozygous mutations. Science. 2015;348(6233):442–444. doi:10.1126/science.aaa5945
32. DiCarlo JE, Chavez A, Dietz SL, Esvelt KM, Church GM. Safeguarding CRISPR-Cas9 gene drives in yeast. Nat Biotechnol. 2015;33(12):1250–1255. doi:10.1038/nbt.3412
33. Berg P. Asilomar 1975: DNA modification secured. Nature. 2008;455(7211):290–291. doi:10.1038/455290a
34. Diggans J, Leproust E. Next steps for access to safe, secure DNA synthesis. Front Bioeng Biotechnol. 2019;7:86. doi:10.3389/fbioe.2019.00086
