"""Primary-literature citations for the probe claims (the reported stratum).

A `ClaimSource` records where a reported (`LITERATURE_EXTRACTED`) claim comes from. The
`admissibility` firewall tag (Phase 0 spec §4 — the date-cutoff / conclusion-stripping
decision) is populated in Phase 3 when the blinded seed is assembled; in Phase 1 it is None.

Refs point at the treatise chapters in `data/synbio_compendia/programmable-living-medicines/`.
"""
from __future__ import annotations

from dataclasses import dataclass

_TREATISE = "data/synbio_compendia/programmable-living-medicines"


@dataclass(frozen=True)
class ClaimSource:
    ref: str
    title: str
    admissibility: str | None = None


SOURCES: dict[str, ClaimSource] = {
    "PLM-I": ClaimSource(
        ref=f"{_TREATISE}/01-first-principles-programmable-cell.md",
        title="First Principles: The Cell as a Programmable Therapeutic",
    ),
    "PLM-II": ClaimSource(
        ref=f"{_TREATISE}/02-reading-surface-antigen-sensing.md",
        title="Reading I: Surface and Antigen Sensing",
    ),
    "PLM-III": ClaimSource(
        ref=f"{_TREATISE}/03-reading-intracellular-genome-sensing.md",
        title="Reading II: Intracellular Genome, Transcriptome, and Epigenome Sensing",
    ),
    "PLM-VI": ClaimSource(
        ref=f"{_TREATISE}/06-computing-synthetic-circuits.md",
        title="Computing: Synthetic Gene Circuits and Cellular Logic",
    ),
    "PLM-VII": ClaimSource(
        ref=f"{_TREATISE}/07-acting-cellular-effectors.md",
        title="Acting: Cellular Effectors and Payloads",
    ),
    "PLM-VIII": ClaimSource(
        ref=f"{_TREATISE}/08-delivery.md",
        title="Delivery",
    ),
    "PLM-XIII": ClaimSource(
        ref=f"{_TREATISE}/13-research-agenda-open-problems.md",
        title="A Research Agenda and the Hard Open Problems",
    ),
}
