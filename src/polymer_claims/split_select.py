"""Discovery/test sample-splitting + top-k probe selection — the severity (anti-cherry-picking)
machinery for region-Δβ. Umbrella/impure (split_contract + top_k read/write contracts). Selection
happens ONLY on the discovery half; the held-out test half is never read during selection. Deterministic
(sort + even/odd interleave; ties by probe id) so sub-contracts are content-addressable."""
from __future__ import annotations


def stratified_split(sample_groups: dict[str, str]) -> tuple[list[str], list[str]]:
    """Deterministic stratified 50/50 split. Within each group (processed in sorted order), sorted
    sample ids are assigned even-index -> discovery, odd-index -> test. Returns (discovery, test),
    each sorted. Disjoint; union = all ids."""
    by_group: dict[str, list[str]] = {}
    for sid, grp in sample_groups.items():
        by_group.setdefault(grp, []).append(sid)
    disc: list[str] = []
    test: list[str] = []
    for grp in sorted(by_group):
        for i, sid in enumerate(sorted(by_group[grp])):
            (disc if i % 2 == 0 else test).append(sid)
    return sorted(disc), sorted(test)
