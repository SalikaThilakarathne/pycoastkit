"""Skill scores for comparing model output (waves, erosion, ...) with observations."""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import pearsonr, spearmanr

__all__ = ["skill_scores", "skill_table", "skill_by_quantile"]


def _pairs(observed, predicted):
    o = np.asarray(observed, dtype=float).ravel()
    p = np.asarray(predicted, dtype=float).ravel()
    if o.shape != p.shape:
        raise ValueError("observed and predicted must have the same length")
    keep = np.isfinite(o) & np.isfinite(p)
    return o[keep], p[keep]


def skill_scores(observed, predicted) -> dict:
    """Standard skill scores over the finite pairs.

    Returns ``n, bias`` (mean of predicted - observed), ``mae``, ``rmse``,
    ``r2`` (1 - SS_res/SS_tot), ``pearson``, ``spearman`` and
    ``scatter_index`` (RMSE / mean observation).
    """
    o, p = _pairs(observed, predicted)
    n = o.size
    if n < 2:
        raise ValueError("need at least two valid pairs")
    error = p - o
    ss_tot = np.sum((o - o.mean()) ** 2)
    rmse = float(np.sqrt(np.mean(error**2)))
    return {
        "n": int(n),
        "bias": float(error.mean()),
        "mae": float(np.abs(error).mean()),
        "rmse": rmse,
        "r2": float(1 - np.sum(error**2) / ss_tot) if ss_tot > 0 else np.nan,
        "pearson": float(pearsonr(o, p)[0]),
        "spearman": float(spearmanr(o, p)[0]),
        "scatter_index": rmse / float(o.mean()) if o.mean() != 0 else np.nan,
    }


def skill_table(observed: pd.DataFrame, predicted: pd.DataFrame) -> pd.DataFrame:
    """:func:`skill_scores` for every column found in both tables (aligned on the index)."""
    rows = {}
    for column in observed.columns.intersection(predicted.columns):
        joined = pd.concat([observed[column], predicted[column]], axis=1, join="inner")
        rows[column] = skill_scores(joined.iloc[:, 0], joined.iloc[:, 1])
    return pd.DataFrame.from_dict(rows, orient="index")


def skill_by_quantile(observed, predicted, q: int = 4) -> pd.DataFrame:
    """Skill per quantile bin of the observations (Q1 = lowest values).

    Shows whether a model is good for calm conditions but poor for storms.
    Returns one row per bin with ``n, bias, mae, rmse, spearman``.
    """
    o, p = _pairs(observed, predicted)
    bins = pd.qcut(o, q=q, duplicates="drop")
    labels = [f"Q{i}" for i in range(1, len(bins.categories) + 1)]
    rows = {}
    for label, category in zip(labels, bins.categories):
        member = np.asarray(bins == category)
        ob, pb = o[member], p[member]
        error = pb - ob
        rows[label] = {
            "range": f"{category.left:.3g} - {category.right:.3g}",
            "n": int(member.sum()),
            "bias": float(error.mean()),
            "mae": float(np.abs(error).mean()),
            "rmse": float(np.sqrt(np.mean(error**2))),
            "spearman": float(spearmanr(ob, pb)[0]) if member.sum() > 2 else np.nan,
        }
    return pd.DataFrame.from_dict(rows, orient="index")
