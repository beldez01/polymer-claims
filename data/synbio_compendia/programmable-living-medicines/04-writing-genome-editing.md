# Writing I: Editing the Genome in Living Cells

> **Filed under:** Programmable Living Medicines > Part IV
> **Created:** 2026-06-09
> **Last updated:** 2026-06-09
> **Tags:** CRISPR, base-editing, prime-editing, bridge-RNA, integrase, Bxb1, PASTE, TnpB, TRAC, CAR, in-vivo-editing, LNP, Casgevy, NTLA-2001, VERVE-101, multiplex-editing, allogeneic

## Summary

If the earlier chapters of this treatise treat the engineered cell as a computer that **reads** state and **computes** logic, this chapter is about the **write** instruction set — how we change the genomic source code of a living cell, and at what fidelity, scale, and cost. The field has resolved into a hierarchy of writers ordered by precision and by reliance on the cell's own repair machinery: the **double-strand break (DSB) "lottery"** of Cas9/Cas12, the **chemistry-based rewriters** (cytosine and adenine base editors) that change single letters without cutting, the **search-and-replace** of prime editing that installs any small edit with the lowest collateral, and the emerging **large-cargo writers** (serine integrases, PASTE, and the 2024 bridge-RNA recombinases) that move kilobases without an exposed break. The central first-principles lesson is that editing is a **thermodynamic and kinetic competition** — target search, R-loop formation, and above all the *choice of DNA repair pathway* — and that the editor protein is rarely the bottleneck; **delivery determines everything**. The clinical frontier splits cleanly: *ex vivo* editing is now an approved drug (Casgevy/exa-cel, December 2023), while *in vivo* editing of the liver (Intellia's nex-z for ATTR amyloidosis; Verve's base-editing of PCSK9) is the live, partially de-risked, partially scarred frontier. For cell therapy specifically, the write layer is what makes off-the-shelf allogeneic cells and exhaustion-resistant CARs possible — through **multiplex knockouts** and **targeted knock-in at TRAC and safe-harbor loci**.

## Background / First Principles

A genome editor is a molecular machine that must win three sequential races against entropy and against the cell's own indifference.

**Race 1 — target search.** A guide-programmed nuclease must locate one ~20 bp site among ~3.2 × 10⁹ bp. SpCas9 does this by facilitated 3D/1D diffusion gated by **PAM (protospacer-adjacent motif) sampling** — it interrogates the ~10⁸ NGG PAMs in the genome, transiently melting DNA only where a PAM is found, then checking complementarity from the PAM-proximal "seed." This is why specificity is front-loaded into the seed and why off-targets cluster around PAM-adjacent mismatches.

**Race 2 — R-loop formation.** Recognition is the thermodynamic displacement of the non-target DNA strand by the guide RNA, forming an **R-loop**. The free-energy difference between a perfect 20-mer R-loop and one bearing a single distal mismatch is small — often only ~1–3 kcal/mol — which is the physical root of off-target editing. High-fidelity variants (eSpCas9, HiFi Cas9) work by *raising the activation barrier* to cleavage so that imperfect R-loops fall off before the HNH domain commits, trading a little on-target speed for large specificity gains.

**Race 3 — repair-pathway choice (the decisive one).** What happens *after* the molecular event is set by which repair pathway the cell deploys, and this is where the writers diverge:

- A **DSB** is resolved stochastically. Non-homologous end joining (NHEJ) is fast, dominant, and error-prone, producing a distribution of indels — a *knockout lottery*. Homology-directed repair (HDR) can install a precise edit but is restricted to S/G2 phase and is inefficient in the quiescent cells (HSCs, neurons, resting T cells) we most want to edit. So "precise knock-in via DSB+HDR" fights cell-cycle biology.
- **Base and prime editing** sidestep the DSB. They use a **nickase** (single-strand cut) or no cut at all, biasing repair toward copying the edited strand rather than rolling the indel dice.
- **Integrases and recombinases** avoid both DSBs and host repair: they catalyze conservative, break-free strand exchange, joining DNA without ever releasing free ends.

The corollary that dominates translation: **the editor protein is almost never the limiting reagent — delivery is.** A perfect editor that reaches 1% of target cells cures nothing. This is why *ex vivo* (edit cells in a dish where delivery is solved by electroporation, then transplant) reached the clinic years before *in vivo* (edit cells inside the body, where delivery is the unsolved problem). The entire commercial geography of the field is a map of who has solved delivery to which tissue.

## Key Findings

### The DSB lottery: Cas9/Cas12 and the limits of "cut and hope"

SpCas9 (from *Streptococcus pyogenes*, ~1,368 aa, NGG PAM) and Cas12a/Cpf1 (T-rich PAM, staggered cut, processes its own crRNA array) are the workhorse nucleases. For **gene knockout**, the DSB lottery is a *feature*: NHEJ reliably destroys an open reading frame, and this is exactly what allogeneic cell therapy needs (see below). But for **precise correction or insertion**, the DSB is a liability on three axes:

1. **Indel heterogeneity** — the edited population is a mixture of correct, frameshifted, and large-deletion products.
2. **Large unintended deletions and chromothripsis** — DSBs can trigger kilobase-to-megabase deletions, loss of heterozygosity, and even whole-chromosome arm loss (Kosicki et al., 2018; Leibowitz et al., 2021), a genotoxicity concern that scales with the number of simultaneous cuts.
3. **p53 activation** — DSBs invoke a p53 DNA-damage response that selects for p53-deficient (i.e., pre-oncogenic) cells (Haapaniemi et al., 2018; Ihry et al., 2018).

These collateral risks are *the reason the field built the next three writers*.

### Base editing: rewriting one letter by chemistry, not by cutting

Cytosine base editors (CBEs; Komor et al., *Nature* 2016) fuse a **cytidine deaminase** (e.g., APOBEC1) to a catalytically impaired Cas9 (a nickase, nCas9), converting **C•G → T•A**. Adenine base editors (ABEs; Gaudelli et al., *Nature* 2017) use a *laboratory-evolved* tRNA adenosine deaminase (TadA) — an enzyme that did not exist in nature for DNA substrates — to convert **A•T → G•C**. Together CBE and ABE can install all four transition mutations, which cover a large fraction of pathogenic point mutations (and, by introducing stop codons, can knock genes out without a DSB — "CRISPR-STOP").

**First-principles mechanics and the failure modes:**

- The deaminase acts only on the **single-stranded DNA exposed in the R-loop**, defining an **editing window** of roughly **protospacer positions ~4–8** (~5 nt wide) counting from the PAM-distal end. This window is the editor's blessing and curse.
- **Bystander editing**: if more than one editable base sits in the window, all may be converted — a serious problem when the therapeutic intent is one specific letter. Mitigations include narrowing the window via Cas9 mutations (to ~1–2 nt) and engineering deaminase context preference.
- **Off-target editing comes in two flavors**: Cas9-*dependent* (at genomic off-target R-loops) and Cas9-*independent* — the deaminase acts stochastically on transiently single-stranded DNA and **RNA** genome-wide, independent of the guide. Engineered deaminases (e.g., SECURE variants) reduce this RNA/DNA promiscuity.
- ABE8e and related fast deaminases pushed efficiency high enough for therapeutic use; ABEs were initially thought "clean" for adenines, but later work showed they can catalyze low-level **cytosine** conversions, a reminder that no chemistry-based writer is perfectly orthogonal.

Base editing's clinical proof points are concrete: **base-edited allogeneic CAR-T** (Beam, the UCART work) and Verve's *in vivo* liver editing (below). The key advantage is that without a DSB there is no indel lottery, no chromothripsis, and far less p53 stress — enabling **multiplex** editing at many loci at once with acceptable genotoxicity, which is essential for off-the-shelf cells.

### Prime editing: the most precise general-purpose writer

Prime editing (Anzalone et al., *Nature* 2019) is "search-and-replace" without a DSB and without a donor template. The editor is an **nCas9–reverse transcriptase (RT) fusion** guided by a **pegRNA** (prime editing guide RNA) that does double duty: its spacer targets the locus, and its 3′ extension contains both a **primer-binding site (PBS)** and an **RT template (RTT)** encoding the desired edit. After the nickase cuts the PAM-containing strand, the freed 3′ end anneals to the PBS and the RT *writes the new sequence directly into the genome* from the pegRNA template. Prime editing can install **all 12 point substitutions, small insertions, and small deletions** (up to tens of bp), making it the most versatile single-locus writer.

The evolution of the platform is a study in interrogating each kinetic bottleneck:

- **PE1 → PE2**: an engineered, stabilized M-MLV RT raised efficiency ~2.3- to 5.1-fold on average (Anzalone et al., 2019).
- **PE3/PE3b**: a second nick on the non-edited strand biases repair toward the edited strand, at the cost of reintroducing some DSB-like indels (PE3b minimizes this by sequence-dependence).
- **The MMR insight (PE4/PE5/PEmax)**: Chen et al. (*Cell* 2021) showed that the cell's **DNA mismatch-repair (MMR)** machinery actively *erases* prime edits by recognizing the heteroduplex intermediate. Transiently inhibiting MMR (co-expressing dominant-negative MLH1, "PE4/PE5") and an optimized editor architecture ("PEmax") together raised efficiency up to ~threefold and reduced byproducts. This is a beautiful example of editing as a *competition with host surveillance* — the same theme as MMR's role in base editing and as NMD's role in RNA sensing discussed in the [genotype-directed cytotoxicity report](../opto-car/seed-report.md).
- **twinPE**: two pegRNAs nick opposite strands and template complementary new strands, **replacing or recoding sequences of 100+ bp to kilobases** without a DSB — the bridge from single-letter editing to large-cargo writing.

Prime editing's price is **efficiency and delivery**: the editor is large (nCas9-RT plus a long structured pegRNA), straining AAV packaging (~4.7 kb limit) and requiring split/intein or LNP strategies. But on the precision axis it is the field's gold standard, and **Prime Medicine** has advanced it toward the clinic.

### Large-cargo integration: moving kilobases without an exposed break

Point edits cannot deliver a CAR, a full gene, or a synthetic circuit — those require **kilobase-scale, site-specific insertion**. Four approaches, in increasing elegance:

1. **HDR knock-in** (DSB + donor): works *ex vivo* (it is how TRAC-CAR knock-in is done, below), but is DSB-dependent, cell-cycle-restricted, and inefficient in quiescent cells.

2. **Serine integrases (Bxb1, phiC31)**: these phage enzymes catalyze **unidirectional, recombination** between a genomic **attP** and a donor **attB** site (~38–50 bp), joining DNA without host repair and with high cargo capacity. The catch: the genome must *first* contain a landing pad (attP), so integrases alone are not "programmable to anywhere."

3. **PASTE** (Programmable Addition via Site-specific Targeting Elements; Yarnall et al., *Nat Biotechnol* 2023) solves that by fusing a **prime editor to a serine integrase**: prime editing first *writes the attB landing site* anywhere you choose, then **Bxb1** drops the cargo in. PASTE integrated payloads **up to ~36 kb** across cell lines, primary T cells, and **non-dividing primary human hepatocytes** — break-free, cell-cycle-independent insertion of whole genes (~20–30% efficiency at favorable loci). This is the most general programmable large-cargo writer demonstrated in human cells.

4. **Bridge RNAs / IS110 recombinases** (Durrant, Perry et al., *Nature* 2024, Arc Institute, Hsu lab): a conceptual leap. The IS110 family of insertion sequences encodes a recombinase whose specificity is set by a **non-coding "bridge RNA"** that folds into **two independently programmable loops** — one specifying the **target** DNA, one specifying the **donor** DNA. This is the first recombinase that is **programmable on both partners by RNA alone**, enabling RNA-directed **insertion, excision, and inversion** as a unified mechanism. In *E. coli* they showed >60% insertion with >94% target specificity, and the recombinase **joins both strands without releasing free DNA ends** — sidestepping the DSB entirely. As of 2024–2025 this is bacterial/early-stage and not yet efficient in human cells, but it points toward a future "**bridge editing**" modality that could unify all four edit classes (point, insert, delete, invert) under one programmable enzyme. The honest status: **frontier-speculative for therapeutics, foundational for the field.**

5. **TnpB / IS200/IS605 (the hypercompact branch)**: TnpB is the **evolutionary ancestor of Cas12**, a ~400-aa RNA-guided DNA endonuclease (Karvelis et al. and others, 2021). Multiple 2023 efforts (e.g., Xiang et al., *Nat Biotechnol* 2023, screening IS605 TnpBs; ISDra2-TnpB from *Deinococcus radiodurans*) achieved genome editing in human cells with proteins **one-third the size of Cas9** (e.g., ISAam1 ~369 aa, ISYmu1 ~382 aa) at SaCas9-comparable efficiency. The payoff is **deliverability**: a hypercompact editor fits an AAV with room for regulatory elements, which matters enormously for the *in vivo* frontier.

### Reverse-transcriptase and retron-based writers

Prime editing is one member of a broader class of **RT-based writers** that template new DNA from an RNA donor. **Retrons** — bacterial RT–msr/msd systems that produce abundant single-stranded DNA — have been harnessed as in-cell donor-DNA factories ("retron library recombineering," and CRISPR-retron combinations) and as the conceptual seed for "**gene writers**" (a term commercialized by **Tessera Therapeutics**, whose Mobile Gene Writers fuse retroelement RT/integrase chemistry to programmable targeting). The unifying first principle of this class: **carry your own donor as RNA and reverse-transcribe it in situ**, removing the need to deliver a separate DNA template and the need for host HDR. These are earlier in maturity than base/prime editing but represent a credible path to break-free, template-free large writes.

### Scarring vs. scar-free, and the epigenetic alternative

A subtle axis: does the edit leave a **scar**? DSB+NHEJ leaves indel scars; base and prime editing are essentially **scar-free** (they install exactly the intended change). For some therapeutic goals the genome need not be permanently rewritten at all — **epigenetic editing** (dCas9 fused to DNA methyltransferases or KRAB repressors; CRISPRoff, Nuñez et al., *Cell* 2021) can heritably silence a gene **without changing one base**, a reversible "write to the epigenome" that this treatise's [methylation chapters](../epigenetics/methylation-gene-regulation.md) and the [CHIP detection work](../chip/02_methylation_biology.md) treat as a first-class instruction layer. Scar-free permanence (prime/base) and scar-free reversibility (epigenetic) are complementary write modes for different clinical durations.

### Ex vivo: the approved proof — Casgevy/exa-cel

**Exagamglogene autotemcel (exa-cel, Casgevy; Vertex/CRISPR Therapeutics)** is the first approved CRISPR medicine — **FDA approval December 8, 2023** for sickle cell disease, with transfusion-dependent β-thalassemia following (January 16, 2024). Mechanistically it is a masterclass in working *with* the DSB lottery: it does **not** correct the sickle mutation. Instead it makes a Cas9 DSB at the **erythroid-specific enhancer of *BCL11A***, knocking down BCL11A in the red-cell lineage and **de-repressing fetal hemoglobin (HbF)**, which dilutes/abrogates sickling. The edit is performed **ex vivo on autologous CD34⁺ HSCs**, which are then re-infused after myeloablative conditioning. The choice of a *knockout-by-indel* target (an enhancer that only needs to be disrupted, not precisely rewritten) is exactly why a simple nuclease sufficed and why this reached the clinic first. The remaining burdens — busulfan conditioning, apheresis, manufacturing, multi-million-dollar price — are *delivery and process* problems, not editing problems, underscoring the chapter's thesis.

### In vivo: the frontier, and its first scars

Editing cells *inside the body* removes conditioning and manufacturing but reimposes the delivery problem. The liver is the beachhead because **LNPs (lipid nanoparticles)** naturally traffic to hepatocytes via ApoE/LDLR.

- **Intellia NTLA-2001 / nexiguran ziclumeran (nex-z)**: LNP-delivered Cas9 mRNA + guide that knocks out **TTR** in the liver for transthyretin (ATTR) amyloidosis. The first-in-human data (Gillmore et al., *NEJM* 2021) showed **dose-dependent, durable serum TTR reduction (>85–90% at higher doses) from a single IV infusion** — landmark proof that *in vivo* CRISPR knockout works systemically in humans. It advanced into the Phase 3 **MAGNITUDE** program (2024). Sobering caveat for the chapter's "failure modes" discipline: a patient death and safety signals have kept the *in vivo* delivery vehicle (not the editor chemistry per se) under scrutiny.
- **Verve VERVE-101 (base editing of *PCSK9*)**: an LNP-delivered **adenine base editor** that installs a stop-gain/splice-disrupting edit to permanently switch off hepatic *PCSK9* and lower LDL cholesterol — the first *in vivo* **base** editor in humans. It demonstrated dose-dependent LDL lowering, but **enrollment in the Heart-1 trial was paused in April 2024 after a serious adverse event** (transient ALT elevation + thrombocytopenia within ~4 days of dosing), prompting a pivot to a next-generation candidate (VERVE-102) with a different LNP/GalNAc targeting ligand. The lesson is precisely the one this chapter foregrounds: **the editor was fine; the delivery vehicle drove the toxicity.**

These programs convert the abstract "delivery determines everything" into clinical fact: *in vivo* editing's bottleneck is the nanoparticle and its tropism, not the nuclease.

## Counterintuitive & Groundbreaking Applications

**1. The write layer is what makes "off-the-shelf" cell therapy possible — via multiplex *destruction*, not construction.** The commercial holy grail of allogeneic CAR-T is a single manufactured product usable in any patient. This requires *removing* genes: knock out **TRAC** (the TCR α chain, to prevent graft-versus-host disease), **B2M** or **CIITA** (HLA, to evade host rejection), and often **CD52** or **PD-1** (for lymphodepletion resistance / persistence). That is **3–5 simultaneous knockouts** — and here the DSB lottery becomes dangerous, because multiple concurrent Cas9 cuts multiply the risk of **translocations** between cut sites. This is the killer commercial argument for **base editing in allogeneic manufacturing**: multiplex C→T knockouts (introducing stop codons or disrupting splice sites) achieve the same gene disruptions **without DSBs and thus without translocations** (the foundation of Beam's and others' allogeneic programs). *The most precise writer is being used not to write, but to delete more safely.*

**2. Knock-in at TRAC: a two-for-one that the field underappreciated.** Eyquem, Sadelain et al. (*Nature* 2017) showed that inserting the CAR transgene **into the TRAC locus** (rather than randomly via lentivirus) does two things at once: it **disrupts the endogenous TCR** (one of the allogeneic edits) *and* places CAR expression under **endogenous TCR transcriptional control**. The result is **uniform CAR expression**, reduced **tonic signaling**, delayed **exhaustion**, and superior antitumor potency versus retroviral CAR-T in mouse models. This is the counterintuitive finding that *where* you write a CAR matters as much as the CAR's design — placement is a tunable control parameter, linking this chapter to the [functional-potency and exhaustion literature](../cell-therapy-qc/universal-functional-potency-2026.md). Subsequent **non-viral** TRAC knock-in (Cas9 RNP + dsDNA/AAV donor; Roth et al., *Nature* 2018) opened a manufacturing path that avoids viral vectors entirely.

**3. Bridge recombinases could collapse the entire writer hierarchy into one enzyme.** If the IS110 bridge-RNA system (or its descendants) is engineered to human-cell efficiency, a *single* RNA-programmable enzyme could perform insertion, deletion, and inversion — and, by programming both target and donor loops, execute **genome rearrangements** (translocations, large inversions) deliberately and precisely. For cell therapy this raises the prospect of **one-shot, multi-gene "circuit installation"**: drop an entire synthetic logic cassette (sensor + CAR + safety switch) into a chosen safe harbor in one programmable, break-free reaction. The commercial white space is a *general* large-cargo writer that is small enough to deliver *in vivo* — the convergence of the hypercompact (TnpB) and bridge-RNA branches.

**4. In vivo gene-writing of HSCs would obsolete conditioning.** The single largest cost and toxicity in Casgevy is not the editor — it is the **busulfan myeloablation** required to make room for edited cells. An *in vivo* editor that reaches HSCs in the marrow (the CD117/CD45-targeted LNP work referenced in the [genotype-directed cytotoxicity report](../opto-car/seed-report.md) — ~90% of LT-HSCs hit with a single dose, Nano Lett 2023) would let one edit the stem compartment **without transplant**, turning a $2M+ inpatient procedure into an outpatient infusion. This is the highest-value unsolved delivery problem in the field, and whoever solves marrow tropism owns the *in vivo* hematologic editing market.

**5. The "write" and "read" layers are the same molecule run in two directions.** The deepest cross-disciplinary point: ADAR (the RNA-editing enzyme that powers the *sensing* layer in CellREADR/RADARS) and the deaminases that power *base editing* are members of the **same deaminase superfamily**, operating on RNA and DNA respectively. The cell's editing chemistry is simultaneously the substrate for *reading* genotype and for *writing* it — the read/write head of the living computer is one enzyme class pointed at two nucleic acids.

## Open Questions

- **Can prime editing and bridge recombinases be delivered *in vivo* at therapeutic efficiency?** Both are large/early; AAV packaging and LNP tropism remain limiting. The hypercompact-editor race (TnpB, compact Cas12) is partly a bet on solving this.
- **What is the true long-term genotoxicity ceiling of multiplex base editing?** Cas9-independent deaminase activity edits RNA and off-target DNA genome-wide; the oncogenic risk of installing thousands of low-frequency edits across a CAR-T product over years of persistence is unquantified.
- **Does MMR inhibition (PE4/PE5) create a mutational vulnerability?** Transiently disabling mismatch repair to boost prime editing could, in principle, raise the background mutation rate during the editing window — a safety/efficiency tradeoff not fully characterized in primary therapeutic cells.
- **Is there a universal "safe harbor"?** TRAC, AAVS1, CCR5, and ROSA26 are used, but no locus is proven free of insertional perturbation across all lineages and timescales. Bridge/PASTE-class writers make *any* locus addressable, which sharpens rather than resolves the question of *where* to write.
- **Can in vivo editing reach the quiescent LT-HSC** — transcriptionally and metabolically quiet, hard to transfect — at the depth needed for cure rather than transient correction? (This is the same quiescence wall flagged for *sensing* in the [genotype-directed cytotoxicity report](../opto-car/seed-report.md).)
- **5hmC and the editing/methylation confound:** as the [CHIP](../chip/02_methylation_biology.md) and [TET2/epigenetics](../epigenetics/tet2-macrophage-immunophenotype.md) work notes, the methylation state of a locus modulates editor accessibility and repair-pathway choice — chromatin is a hidden variable in every "write" efficiency number.

## Connections

- **Sibling chapters:** the read/sense layer ([01-first-principles-programmable-cell.md](./01-first-principles-programmable-cell.md)); RNA-level reading and synthetic logic that *gate* a write; the delivery chapter (LNP/AAV physics) that this chapter repeatedly defers to; the cell-therapy manufacturing chapter where multiplex editing and TRAC knock-in live.
- **[../immunology/genotype-directed-cytotoxicity.md](../opto-car/seed-report.md)** — the *reading* counterpart: ADAR sensing, NMD-as-host-surveillance (mirror of MMR here), CD117/CD45 LNP HSC delivery (~90% of LT-HSCs), and the quiescence wall. This chapter supplies the *write* effectors (e.g., a knock-in CAR, a base-edited allogeneic chassis) that its architectures presume.
- **[../cell-therapy-qc/universal-functional-potency-2026.md](../cell-therapy-qc/universal-functional-potency-2026.md)** and the QC landscape — TRAC placement, tonic signaling, and exhaustion are the functional readouts of *where/how* you wrote the CAR.
- **[../epigenetics/methylation-gene-regulation.md](../epigenetics/methylation-gene-regulation.md)** and **[../chip/02_methylation_biology.md](../chip/02_methylation_biology.md)** — the scar-free *reversible* write mode (epigenetic editing) and chromatin as a hidden editing variable.
- **[../energy-landscape-hematopoiesis/_overview.md](../energy-landscape-hematopoiesis/_overview.md)** — editing an HSC perturbs the quasi-potential landscape; the "write" is a deformation operator on Waddington's surface.

## References

1. Komor AC, Kim YB, Packer MS, Zuris JA, Liu DR. Programmable editing of a target base in genomic DNA without double-stranded DNA cleavage. *Nature*. 2016;533(7603):420–424. doi:10.1038/nature17946
2. Gaudelli NM, Komor AC, Rees HA, et al. Programmable base editing of A•T to G•C in genomic DNA without DNA cleavage. *Nature*. 2017;551(7681):464–471. doi:10.1038/nature24644
3. Anzalone AV, Randolph PB, Davis JR, et al. Search-and-replace genome editing without double-strand breaks or donor DNA. *Nature*. 2019;576(7785):149–157. doi:10.1038/s41586-019-1711-4
4. Chen PJ, Hussmann JA, Yan J, et al. Enhanced prime editing systems by manipulating cellular determinants of editing outcomes. *Cell*. 2021;184(22):5635–5652.e29. doi:10.1016/j.cell.2021.09.018
5. Anzalone AV, Gao XD, Podracky CJ, et al. Programmable deletion, replacement, integration and inversion of large DNA sequences with twin prime editing. *Nat Biotechnol*. 2022;40(5):731–740. doi:10.1038/s41587-021-01133-w
6. Yarnall MTN, Ioannidi EI, Schmitt-Ulms C, et al. Drag-and-drop genome insertion of large sequences without double-strand DNA cleavage using CRISPR-directed integrases (PASTE). *Nat Biotechnol*. 2023;41(4):500–512. doi:10.1038/s41587-022-01527-4
7. Durrant MG, Perry NT, Pai JJ, et al. Bridge RNAs direct modular and programmable recombination of target and donor DNA. *Nature*. 2024;630(8018):984–993. doi:10.1038/s41586-024-07552-4
8. Xiang G, Li Y, Sun J, et al. Evolutionary mining and functional characterization of TnpB nucleases identify efficient miniature genome editors. *Nat Biotechnol*. 2024;42(5):745–757. doi:10.1038/s41587-023-01857-x
9. Karvelis T, Druteika G, Bigelyte G, et al. Transposon-associated TnpB is a programmable RNA-guided DNA endonuclease. *Nature*. 2021;599(7886):692–696. doi:10.1038/s41586-021-04058-1
10. Eyquem J, Mansilla-Soto J, Giavridis T, et al. Targeting a CAR to the TRAC locus with CRISPR/Cas9 enhances tumour rejection. *Nature*. 2017;543(7643):113–117. doi:10.1038/nature21405
11. Roth TL, Puig-Saus C, Yu R, et al. Reprogramming human T cell function and specificity with non-viral genome targeting. *Nature*. 2018;559(7714):405–409. doi:10.1038/s41586-018-0326-5
12. Frangoul H, Altshuler D, Cappellini MD, et al. CRISPR-Cas9 gene editing for sickle cell disease and β-thalassemia. *N Engl J Med*. 2021;384(3):252–260. doi:10.1056/NEJMoa2031054
13. U.S. Food and Drug Administration. FDA approves first gene therapies (Casgevy/exa-cel) to treat patients with sickle cell disease. News release; December 8, 2023.
14. Gillmore JD, Gane E, Taubel J, et al. CRISPR-Cas9 in vivo gene editing for transthyretin amyloidosis (NTLA-2001). *N Engl J Med*. 2021;385(6):493–502. doi:10.1056/NEJMoa2107454
15. Lee RG, Mazzola AM, Braun MC, et al. Efficacy and safety of an investigational single-course CRISPR base-editing therapy targeting PCSK9 (VERVE-101) in vitro and in vivo. *Circulation*. 2023;147(3):242–253. doi:10.1161/CIRCULATIONAHA.122.062132
16. Verve Therapeutics. Form 8-K: Heart-1 clinical trial update. U.S. SEC filing; April 2024.
17. Kosicki M, Tomberg K, Bradley A. Repair of double-strand breaks induced by CRISPR-Cas9 leads to large deletions and complex rearrangements. *Nat Biotechnol*. 2018;36(8):765–771. doi:10.1038/nbt.4192
18. Leibowitz ML, Papathanasiou S, Doerfler PA, et al. Chromothripsis as an on-target consequence of CRISPR-Cas9 genome editing. *Nat Genet*. 2021;53(6):895–905. doi:10.1038/s41588-021-00838-7
19. Haapaniemi E, Botla S, Persson J, Schmierer B, Taipale J. CRISPR-Cas9 genome editing induces a p53-mediated DNA damage response. *Nat Med*. 2018;24(7):927–930. doi:10.1038/s41591-018-0049-z
20. Ihry RJ, Worringer KA, Salick MR, et al. p53 inhibits CRISPR-Cas9 engineering in human pluripotent stem cells. *Nat Med*. 2018;24(7):939–946. doi:10.1038/s41591-018-0050-6
21. Nuñez JK, Chen J, Pommier GC, et al. Genome-wide programmable transcriptional memory by CRISPR-based epigenome editing (CRISPRoff). *Cell*. 2021;184(9):2503–2519.e17. doi:10.1016/j.cell.2021.03.025
22. Slesarenko YS, Lavrov AV, Smirnikhina SA. Off-target effects of base editors: what we know and how we can reduce it. *Curr Genet*. 2022;68(1):39–48. doi:10.1007/s00294-021-01211-1
23. Anzalone AV, Koblan LW, Liu DR. Genome editing with CRISPR-Cas nucleases, base editors, transposases and prime editors. *Nat Biotechnol*. 2020;38(7):824–844. doi:10.1038/s41587-020-0561-9
