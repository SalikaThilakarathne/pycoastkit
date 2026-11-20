"""Link storms to the beach response they cause (erosion of shoreline and volume)."""

from __future__ import annotations

import numpy as np
import pandas as pd

__all__ = ["survey_before", "survey_after", "storm_beach_response"]


def _valid(series: pd.Series) -> pd.Series:
    series = series.dropna().sort_index()
    if not isinstance(series.index, pd.DatetimeIndex):
        series.index = pd.to_datetime(series.index)
    return series


def survey_before(series: pd.Series, when, max_days: float = 7):
    """Last valid survey on or before ``when`` (within ``max_days``).

    Returns ``(survey_time, value)`` or ``(NaT, NaN)`` if none is close enough.
    """
    series = _valid(series)
    when = pd.Timestamp(when)
    window = series.loc[when - pd.Timedelta(days=max_days):when]
    if window.empty:
        return pd.NaT, np.nan
    return window.index[-1], float(window.iloc[-1])


def survey_after(series: pd.Series, when, max_days: float = 7):
    """First valid survey on or after ``when`` (within ``max_days``)."""
    series = _valid(series)
    when = pd.Timestamp(when)
    window = series.loc[when:when + pd.Timedelta(days=max_days)]
    if window.empty:
        return pd.NaT, np.nan
    return window.index[0], float(window.iloc[0])


def storm_beach_response(storms: pd.DataFrame, beach, days_before: float = 1,
                         days_after: float = 1, max_search_days: float = 7) -> pd.DataFrame:
    """Beach change across each storm (or storm cluster).

    For every event the *pre-storm* survey is the last valid survey on or
    before ``start_time - days_before`` (calendar day), and the *post-storm*
    survey is the first valid survey on or after ``end_time + days_after``.
    Using whole days before and after avoids surveys taken during the storm.

    Parameters
    ----------
    storms : pandas.DataFrame
        Output of :func:`~pycoastkit.find_storms` or
        :func:`~pycoastkit.storm_clusters` (needs ``start_time``, ``end_time``).
    beach : pandas.Series or pandas.DataFrame
        Time-indexed beach indicators, e.g. ``shoreline`` [m, positive seaward]
        and ``volume`` [m³/m]. Each column is processed separately.
    days_before, days_after : float
        Offset from the storm start/end to the target survey day.
    max_search_days : float
        How far to search for a valid survey; otherwise the result is NaN.

    Returns
    -------
    pandas.DataFrame
        ``storms`` plus, for each indicator ``c``: ``c_pre_time, c_pre,
        c_post_time, c_post`` and ``c_loss = c_pre - c_post``. A positive loss
        is erosion (shoreline retreat or volume loss); negative is accretion.
    """
    if isinstance(beach, pd.Series):
        beach = beach.to_frame(beach.name or "beach")
    out = storms.copy()
    for column in beach.columns:
        series = _valid(beach[column])
        pre_target = pd.to_datetime(storms["start_time"]).dt.normalize() - pd.Timedelta(days=days_before)
        post_target = pd.to_datetime(storms["end_time"]).dt.normalize() + pd.Timedelta(days=days_after)
        pre = [survey_before(series, t, max_search_days) for t in pre_target]
        post = [survey_after(series, t, max_search_days) for t in post_target]
        out[f"{column}_pre_time"] = [p[0] for p in pre]
        out[f"{column}_pre"] = [p[1] for p in pre]
        out[f"{column}_post_time"] = [p[0] for p in post]
        out[f"{column}_post"] = [p[1] for p in post]
        out[f"{column}_loss"] = out[f"{column}_pre"] - out[f"{column}_post"]
    return out
