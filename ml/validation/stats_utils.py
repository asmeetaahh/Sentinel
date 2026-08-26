"""
Small, dependency-light statistical helpers used across validation checks.
No sklearn/scipy dependency — AUC is computed directly from the
Mann-Whitney U statistic via rank sums, which is exact (not an
approximation) and handles ties via average ranks.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def auc_from_scores(scores: np.ndarray, labels: np.ndarray) -> float:
    """ROC-AUC of `scores` as a predictor of binary `labels`, via the
    rank-sum form of the Mann-Whitney U statistic. Returns NaN if either
    class is empty.
    """
    scores = np.asarray(scores, dtype=float)
    labels = np.asarray(labels, dtype=int)
    mask = ~np.isnan(scores)
    scores, labels = scores[mask], labels[mask]

    n_pos = int(labels.sum())
    n_neg = len(labels) - n_pos
    if n_pos == 0 or n_neg == 0:
        return float("nan")

    ranks = pd.Series(scores).rank(method="average").to_numpy()
    sum_ranks_pos = ranks[labels == 1].sum()
    u = sum_ranks_pos - n_pos * (n_pos + 1) / 2.0
    return float(u / (n_pos * n_neg))


def robust_summary(series: pd.Series) -> dict:
    s = pd.to_numeric(series, errors="coerce").dropna()
    if s.empty:
        return {"count": 0}
    q = s.quantile([0.0, 0.10, 0.25, 0.50, 0.75, 0.90, 0.99, 1.0])
    return {
        "count": int(s.count()),
        "mean": float(s.mean()),
        "std": float(s.std()),
        "min": float(q.loc[0.0]),
        "p10": float(q.loc[0.10]),
        "p25": float(q.loc[0.25]),
        "median": float(q.loc[0.50]),
        "p75": float(q.loc[0.75]),
        "p90": float(q.loc[0.90]),
        "p99": float(q.loc[0.99]),
        "max": float(q.loc[1.0]),
    }
