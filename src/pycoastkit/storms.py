"""Find wave storms in a significant-wave-height record and group them into clusters.

A storm is a period in which Hs stays above a *duration threshold* for long
enough and, at its peak, reaches a higher *peak threshold*. Storms separated by
a short calm spell are not independent: they form a *storm cluster* whose
combined effect on the beach is usually larger than that of a single storm.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

__all__ = [
    "StormCriteria",
    "find_storms",
    "storm_clusters",
    "storm_power",
    "add_storm_wave_statistics",
    "add_storm_energy",
    "storms_per_month",
    "storms_per_year",
]


@dataclass(frozen=True)
class StormCriteria:
    """Thresholds that define a storm.

    The defaults (1.5 m, 2.5 m, 6 h, 48 h) are the storm definition used for
    the Hasaki coast, Japan (Pacific, Kashima-nada).

    Parameters
    ----------
    hs_threshold : float
        Hs [m] above which the sea is "stormy"; sets the storm start and end.
    peak_threshold : float
        Hs [m] the storm must reach at least once to count (impact threshold).
    min_duration_h : float
        Minimum time [h] above ``hs_threshold``.
    min_separation_h : float
        Storms with a calm spell of this many hours or less between them are
        grouped into one cluster (meteorological independence criterion).
    """

    hs_threshold: float = 1.5
    peak_threshold: float = 2.5
    min_duration_h: float = 6.0
    min_separation_h: float = 48.0

    def __post_init__(self):
        if self.peak_threshold < self.hs_threshold:
            raise ValueError("peak_threshold must be >= hs_threshold")
        if self.min_duration_h < 0 or self.min_separation_h < 0:
            raise ValueError("durations must be non-negative")


def storm_power(peak_hs, duration_h):
    """Storm power index ``peak_hs**2 * duration_h`` [m² h] (Dolan & Davis 1992)."""
    return np.asarray(peak_hs, dtype=float) ** 2 * np.asarray(duration_h, dtype=float)


def _steps_h(index: pd.DatetimeIndex) -> np.ndarray:
    """Time between consecutive samples in hours (independent of the datetime unit)."""
    return np.diff(index.to_numpy()) / np.timedelta64(1, "h")


def _sampling_interval_h(index: pd.DatetimeIndex) -> float:
    steps = _steps_h(index)
    steps = steps[steps > 0]
    if steps.size == 0:
        raise ValueError("need at least two distinct timestamps to infer the sampling interval")
    return float(np.median(steps))


def _hours(delta) -> float:
    return pd.Timedelta(delta).total_seconds() / 3600.0


def find_storms(
    waves,
    criteria: StormCriteria | None = None,
    hs_column: str = "hs",
    sampling_interval_h: float | None = None,
) -> pd.DataFrame:
    """Find storms and label them as *individual* or *clustered*.

    How it works
    ------------
    1. Each run of consecutive samples with ``Hs > hs_threshold`` is a candidate.
       Missing values and data gaps longer than 1.5 sampling intervals end a run.
    2. Duration = time from the first exceedance to the first sample back below
       the threshold (= number of samples x sampling interval).
    3. Keep runs with ``duration >= min_duration_h`` and ``peak >= peak_threshold``.
    4. Storms whose calm gap to a neighbour is ``<= min_separation_h`` share a
       ``cluster_id``; a cluster of one storm is an *individual* storm.

    Parameters
    ----------
    waves : pandas.DataFrame or pandas.Series
        Time-indexed significant wave height [m] (column ``hs_column``).
    criteria : StormCriteria, optional
        Storm definition; defaults to ``StormCriteria()``.
    hs_column : str
        Name of the Hs column when ``waves`` is a DataFrame.
    sampling_interval_h : float, optional
        Time between samples [h]; inferred from the index when omitted.

    Returns
    -------
    pandas.DataFrame
        One row per storm: ``storm_id, cluster_id, kind, n_in_cluster,
        start_time, end_time, duration_h, peak_hs, peak_time, mean_hs,
        storm_power, gap_before_h, gap_after_h``. ``start_time`` and
        ``end_time`` are the first and last samples above ``hs_threshold``.
    """
    criteria = criteria or StormCriteria()
    hs = waves if isinstance(waves, pd.Series) else waves[hs_column]
    hs = hs.astype(float).sort_index()
    if not isinstance(hs.index, pd.DatetimeIndex):
        hs.index = pd.to_datetime(hs.index)
    hs = hs[~hs.index.duplicated(keep="last")]

    dt_h = sampling_interval_h or _sampling_interval_h(hs.index)
    times = hs.index
    values = hs.to_numpy()

    above = values > criteria.hs_threshold          # NaN -> False
    # sample i continues into sample i+1 if both exceed and there is no data gap
    linked = above[:-1] & above[1:] & (_steps_h(times) <= 1.5 * dt_h)
    run_first = np.flatnonzero(above & ~np.r_[False, linked])
    run_last = np.flatnonzero(above & ~np.r_[linked, False])

    rows = []
    for first, last in zip(run_first, run_last):
        duration_h = (last - first + 1) * dt_h
        segment = values[first:last + 1]
        peak = float(np.nanmax(segment))
        if duration_h < criteria.min_duration_h or peak < criteria.peak_threshold:
            continue
        rows.append({
            "start_time": times[first],
            "end_time": times[last],
            "duration_h": duration_h,
            "peak_hs": peak,
            "peak_time": times[first + int(np.nanargmax(segment))],
            "mean_hs": float(np.nanmean(segment)),
        })

    columns = ["storm_id", "cluster_id", "kind", "n_in_cluster", "start_time", "end_time",
               "duration_h", "peak_hs", "peak_time", "mean_hs", "storm_power",
               "gap_before_h", "gap_after_h"]
    if not rows:
        return pd.DataFrame(columns=columns)

    storms = pd.DataFrame(rows)
    storms["storm_power"] = storm_power(storms["peak_hs"], storms["duration_h"])
    gaps = (storms["start_time"] - storms["end_time"].shift()).dt.total_seconds() / 3600.0
    storms["gap_before_h"] = gaps
    storms["gap_after_h"] = gaps.shift(-1)
    new_cluster = ~(storms["gap_before_h"] <= criteria.min_separation_h)
    storms["cluster_id"] = new_cluster.cumsum().astype(int)
    storms["n_in_cluster"] = storms.groupby("cluster_id")["cluster_id"].transform("size")
    storms["kind"] = np.where(storms["n_in_cluster"] > 1, "clustered", "individual")
    storms["storm_id"] = np.arange(1, len(storms) + 1)
    return storms[columns]


def storm_clusters(storms: pd.DataFrame) -> pd.DataFrame:
    """Combine the storms of each cluster into one event.

    Returns one row per ``cluster_id``: ``kind, n_storms, start_time, end_time,
    span_h`` (first start to last end), ``duration_h`` (sum of storm
    durations), ``peak_hs, peak_time, mean_hs`` (duration-weighted),
    ``storm_power`` (sum over the storms). Individual storms are returned as
    clusters of one, so the result can be analysed as a single event table.
    Any extra numeric columns starting with ``mean_``/``max_``/``min_`` (for
    example from :func:`add_storm_wave_statistics`) are combined with a
    duration-weighted mean, maximum or minimum.
    """
    if storms.empty:
        return pd.DataFrame()

    rows = []
    for cluster_id, group in storms.groupby("cluster_id", sort=True):
        weights = group["duration_h"].to_numpy(dtype=float)
        peak_row = group.loc[group["peak_hs"].idxmax()]
        row = {
            "cluster_id": cluster_id,
            "kind": "clustered" if len(group) > 1 else "individual",
            "n_storms": len(group),
            "start_time": group["start_time"].iloc[0],
            "end_time": group["end_time"].iloc[-1],
            "span_h": _hours(group["end_time"].iloc[-1] - group["start_time"].iloc[0]),
            "duration_h": float(weights.sum()),
            "peak_hs": float(peak_row["peak_hs"]),
            "peak_time": peak_row["peak_time"],
            "mean_hs": float(np.average(group["mean_hs"], weights=weights)),
            "storm_power": float(group["storm_power"].sum()),
        }
        for column in group.columns:
            if column in row or column in ("mean_hs",):
                continue
            series = pd.to_numeric(group[column], errors="coerce")
            if column.startswith("mean_") and series.notna().any():
                valid = series.notna().to_numpy()
                row[column] = float(np.average(series[valid], weights=weights[valid]))
            elif column.startswith("max_"):
                row[column] = series.max()
            elif column.startswith("min_"):
                row[column] = series.min()
        rows.append(row)
    return pd.DataFrame(rows)


def add_storm_wave_statistics(storms: pd.DataFrame, waves: pd.DataFrame,
                              statistics: dict) -> pd.DataFrame:
    """Add statistics of any wave variable during each storm.

    Example
    -------
    >>> add_storm_wave_statistics(storms, waves, {"t0": ["mean", "max"], "hmax": "max"})
    adds the columns ``mean_t0``, ``max_t0`` and ``max_hmax``.

    Each storm window runs from ``start_time`` to ``end_time`` (inclusive).
    Direction columns should be averaged with a circular mean - use the
    statistic ``"circmean"`` for directions in degrees.
    """
    out = storms.copy()
    waves = waves.sort_index()
    for column, funcs in statistics.items():
        for func in [funcs] if isinstance(funcs, str) else funcs:
            values = []
            for start, end in zip(storms["start_time"], storms["end_time"]):
                window = waves.loc[start:end, column].dropna()
                if window.empty:
                    values.append(np.nan)
                elif func == "circmean":
                    rad = np.radians(window.to_numpy(dtype=float))
                    values.append(float(np.degrees(np.arctan2(np.sin(rad).mean(),
                                                              np.cos(rad).mean())) % 360))
                else:
                    values.append(float(window.agg(func)))
            name = "mean" if func == "circmean" else func
            out[f"{name}_{column}"] = values
    return out


def storms_per_month(storms: pd.DataFrame) -> pd.Series:
    """Number of storms starting in each calendar month (1-12) - seasonality."""
    months = pd.to_datetime(storms["start_time"]).dt.month
    return months.value_counts().reindex(range(1, 13), fill_value=0).rename("storms")


def storms_per_year(storms: pd.DataFrame) -> pd.Series:
    """Number of storms starting in each year."""
    years = pd.to_datetime(storms["start_time"]).dt.year
    counts = years.value_counts().sort_index()
    if counts.empty:
        return counts.rename("storms")
    return counts.reindex(range(counts.index.min(), counts.index.max() + 1),
                          fill_value=0).rename("storms")


def add_storm_energy(storms: pd.DataFrame, waves: pd.DataFrame, hs_column: str = "hs",
                     period_column: str = "ts", depth_m: float | None = None) -> pd.DataFrame:
    """Add the wave energy delivered by each storm, ``energy_mj_per_m`` [MJ/m].

    The wave energy flux (:func:`pycoastkit.wave_energy_flux`, deep water
    unless ``depth_m`` is given) is integrated over time from ``start_time``
    to ``end_time`` with the trapezoidal rule, using the actual time steps,
    so hourly and 2-hourly records give comparable values. Also adds
    ``max_energy_flux_kw_per_m`` [kW/m].
    """
    from .waves import wave_energy_flux

    out = storms.copy()
    totals, peaks = [], []
    trap = getattr(np, "trapezoid", None) or np.trapz
    for start, end in zip(storms["start_time"], storms["end_time"]):
        window = waves.loc[start:end, [hs_column, period_column]].dropna()
        if window.empty:
            totals.append(np.nan)
            peaks.append(np.nan)
            continue
        flux = np.atleast_1d(wave_energy_flux(window[hs_column], window[period_column], depth_m))
        seconds = (window.index - window.index[0]) / pd.Timedelta(seconds=1)
        totals.append(float(trap(flux, seconds)) / 1e6 if len(window) > 1 else 0.0)
        peaks.append(float(flux.max()) / 1e3)
    out["energy_mj_per_m"] = totals
    out["max_energy_flux_kw_per_m"] = peaks
    return out
