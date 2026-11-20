"""Beach recovery after storms.

After a storm the beach usually rebuilds as sand returns from the surf zone.
:func:`storm_recovery` measures how much of the storm erosion came back
within a fixed number of days, and :func:`post_storm_conditions` summarises
the waves during that recovery window.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .impacts import survey_after, survey_before

__all__ = ["storm_recovery", "post_storm_conditions", "iqr_outliers"]


def storm_recovery(response: pd.DataFrame, beach, n_days: float = 10,
                   max_search_days: float = 3, min_loss=None) -> pd.DataFrame:
    """Recovery of each beach indicator ``n_days`` after the post-storm survey.

    Parameters
    ----------
    response : pandas.DataFrame
        Output of :func:`pycoastkit.storm_beach_response` (needs, for each
        indicator ``c``, the columns ``c_post_time``, ``c_post`` and ``c_loss``).
        If it has ``gap_after_h`` (from :func:`pycoastkit.find_storms`), the
        column ``undisturbed`` tells whether the next storm arrived later than
        the recovery window.
    beach : pandas.Series or pandas.DataFrame
        The same time-indexed beach indicators used for the response.
    n_days : float
        Length of the recovery window, counted from the post-storm survey.
    max_search_days : float
        Tolerance for finding a survey near the end of the window (the last
        valid survey on or before ``post_time + n_days``, at most this many
        days earlier).
    min_loss : float or dict, optional
        Smallest erosion for which the recovery *ratio* is computed (per
        indicator if a dict). The ratio is unstable for small erosion; below
        this value it is NaN.

    Returns
    -------
    pandas.DataFrame
        ``response`` plus, for each indicator ``c``:
        ``c_recovery_time`` (survey used), ``c_recovery`` (``c_later - c_post``,
        positive = beach rebuilt) and ``c_recovery_ratio`` (``c_recovery /
        c_loss``: 1 = fully recovered, > 1 = more than recovered, < 0 = erosion
        continued). Also ``undisturbed`` when gaps are available.
    """
    if isinstance(beach, pd.Series):
        beach = beach.to_frame(beach.name or "beach")
    out = response.copy()
    for column in beach.columns:
        if f"{column}_post_time" not in out:
            raise KeyError(f"response has no '{column}_post_time'; run storm_beach_response first")
        series = beach[column]
        later = []
        for post_time in out[f"{column}_post_time"]:
            if pd.isna(post_time):
                later.append((pd.NaT, np.nan))
                continue
            target = pd.Timestamp(post_time) + pd.Timedelta(days=n_days)
            when, value = survey_before(series, target, max_search_days)
            if pd.notna(when) and when <= pd.Timestamp(post_time):
                when, value = pd.NaT, np.nan
            later.append((when, value))
        out[f"{column}_recovery_time"] = [item[0] for item in later]
        out[f"{column}_recovery"] = np.array([item[1] for item in later]) - out[f"{column}_post"]

        threshold = min_loss.get(column) if isinstance(min_loss, dict) else min_loss
        loss = out[f"{column}_loss"].astype(float)
        valid = loss > (0 if threshold is None else threshold)
        out[f"{column}_recovery_ratio"] = np.where(valid, out[f"{column}_recovery"] / loss, np.nan)

    if "gap_after_h" in out:
        out["undisturbed"] = ~(out["gap_after_h"] < n_days * 24)
    return out


def post_storm_conditions(storms: pd.DataFrame, waves: pd.DataFrame, statistics: dict,
                          n_days: float = 10, start: str = "end_time") -> pd.DataFrame:
    """Statistics of wave (or water-level) variables in the window after each storm.

    The window runs from ``start`` (default: the storm's last stormy sample)
    to ``n_days`` later. Columns are named ``post_<stat>_<variable>``.

    Example
    -------
    >>> post_storm_conditions(storms, waves, {"hs": ["mean", "max"], "ts": "mean"})
    """
    out = storms.copy()
    waves = waves.sort_index()
    for column, funcs in statistics.items():
        for func in [funcs] if isinstance(funcs, str) else funcs:
            values = []
            for begin in pd.to_datetime(storms[start]):
                window = waves.loc[begin:begin + pd.Timedelta(days=n_days), column].dropna()
                values.append(float(window.agg(func)) if len(window) else np.nan)
            out[f"post_{func}_{column}"] = values
    return out


def iqr_outliers(values, k: float = 1.5) -> pd.Series:
    """Tukey fences: ``True`` where a value lies outside [Q1 - k·IQR, Q3 + k·IQR].

    Useful for removing extreme recovery ratios before statistics.
    """
    series = pd.Series(values, dtype=float)
    q1, q3 = series.quantile([0.25, 0.75])
    iqr = q3 - q1
    return (series < q1 - k * iqr) | (series > q3 + k * iqr)
