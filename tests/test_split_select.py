from __future__ import annotations

from polymer_claims.split_select import stratified_split


def test_stratified_split_disjoint_covers_all_and_stratified():
    groups = {f"s{i:02d}": ("IDH_mut" if i < 4 else "WT") for i in range(12)}  # 4 IDH_mut, 8 WT
    disc, test = stratified_split(groups)
    assert set(disc).isdisjoint(test)
    assert set(disc) | set(test) == set(groups)
    # each group split ~evenly: 4 IDH_mut -> 2/2, 8 WT -> 4/4
    idh = {s for s, g in groups.items() if g == "IDH_mut"}
    assert len(idh & set(disc)) == 2 and len(idh & set(test)) == 2


def test_stratified_split_is_deterministic():
    groups = {f"s{i:02d}": ("A" if i % 3 == 0 else "B") for i in range(10)}
    assert stratified_split(groups) == stratified_split(groups)
    assert stratified_split(groups)[0] == sorted(stratified_split(groups)[0])  # sorted output
