"""
Merchant-level, archetype-stratified train/val/test split.

CRITICAL invariant: a merchant_id appears in exactly one of
{train, val, test}. Splitting happens on the list of merchants, never on
rows — every row for a given merchant goes wherever that merchant went.

Stratified by archetype (via merchants.csv) so no split is accidentally
dominated by one archetype, using the largest-remainder (Hamilton)
apportionment method: exact fractional targets are rounded down, then the
few leftover seats are given to whichever bucket has the largest fractional
remainder — a standard, deterministic way to apportion a small integer
count across buckets without a directional rounding bias.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .config import SEED, SPLIT_FRACTIONS


def _largest_remainder_apportionment(n: int, fractions: dict[str, float]) -> dict[str, int]:
    names = list(fractions.keys())
    raw = {k: n * fractions[k] for k in names}
    base = {k: int(np.floor(raw[k])) for k in names}
    remainder = n - sum(base.values())

    fractional_parts = sorted(names, key=lambda k: (-(raw[k] - base[k]), names.index(k)))
    for i in range(remainder):
        base[fractional_parts[i]] += 1
    return base


def build_merchant_split(merchants: pd.DataFrame, seed: int = SEED) -> pd.DataFrame:
    """Returns a DataFrame [merchant_id, archetype, split] with split in
    {'train','val','test'}, one row per merchant.
    """
    rng = np.random.default_rng(seed)
    rows = []
    for archetype, group in merchants.groupby("archetype", sort=True):
        merchant_ids = group["merchant_id"].to_numpy().copy()
        rng.shuffle(merchant_ids)  # deterministic given seed, independent per archetype group

        counts = _largest_remainder_apportionment(len(merchant_ids), SPLIT_FRACTIONS)
        cursor = 0
        for split_name in ["train", "val", "test"]:
            n = counts[split_name]
            for mid in merchant_ids[cursor : cursor + n]:
                rows.append({"merchant_id": mid, "archetype": archetype, "split": split_name})
            cursor += n

    split_df = pd.DataFrame(rows)
    assert split_df["merchant_id"].nunique() == len(split_df), "a merchant appears more than once in the split"
    assert set(split_df["merchant_id"]) == set(merchants["merchant_id"]), "split does not cover all merchants"
    return split_df


def split_summary(split_df: pd.DataFrame) -> dict:
    overall = split_df["split"].value_counts().to_dict()
    by_archetype = (
        split_df.groupby(["archetype", "split"]).size().unstack(fill_value=0).to_dict(orient="index")
    )
    return {
        "seed": SEED,
        "target_fractions": SPLIT_FRACTIONS,
        "overall_counts": overall,
        "overall_fractions": {k: round(v / len(split_df), 3) for k, v in overall.items()},
        "counts_by_archetype": by_archetype,
    }
