"""Shoreline position from beach profiles, foreshore slope and shoreline QC.

The shoreline is where a cross-shore profile crosses a chosen water level
(for example mean high water springs, MHWS). Profiles are tables with one
row per survey and one column per cross-shore position [m], increasing
seaward (see :mod:`pycoastkit.beach`).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .beach import _with_numeric_columns, smooth_profiles

__all__ = [
    "shoreline_position",
    "shoreline_positions",
    "foreshore_slope",
    "flag_shoreline_outliers",
]


def shoreline_position(x, elevation, water_level: float, crossing: str = "seaward") -> float:
    """Cross-shore position where one profile crosses ``water_level``.

    The profile is scanned seaward for *down-crossings* (bed going from above
    to below the level); the crossing is interpolated linearly between the
    two survey points around it.

    Parameters
    ----------
    x : array-like
        Cross-shore positions [m], increasing seaward.
    elevation : array-like
        Bed elevation [m] at ``x``; NaN segments are skipped.
    water_level : float
        Shoreline-defining level [m], in the survey datum.
    crossing : {"seaward", "landward"}
        Which down-crossing to return when there are several (an emerged
        bar or a runnel gives more than one). ``"seaward"`` (default) is the
        outermost, as used in the Hasaki studies; ``"landward"`` is the
        first one, at the beach face.

    Returns
    -------
    float
        Shoreline position [m]; NaN if the profile never crosses the level.
    """
    if crossing not in ("landward", "seaward"):
        raise ValueError("crossing must be 'landward' or 'seaward'")
    x = np.asarray(x, dtype=float)
    z = np.asarray(elevation, dtype=float) - water_level
    valid = np.isfinite(z[:-1]) & np.isfinite(z[1:])
    down = np.flatnonzero(valid & (z[:-1] >= 0) & (z[1:] < 0))
    if down.size == 0:
        return np.nan
    i = down[0] if crossing == "landward" else down[-1]
    return float(x[i] + z[i] * (x[i + 1] - x[i]) / (z[i] - z[i + 1]))


def shoreline_positions(profiles: pd.DataFrame, water_level: float, crossing: str = "seaward",
                        smooth_sigma: float | None = None) -> pd.Series:
    """Shoreline position [m] for every survey.

    ``smooth_sigma`` (grid points) smooths the profiles first with
    :func:`pycoastkit.smooth_profiles`; smoothing suppresses false crossings
    caused by survey noise.
    """
    table = _with_numeric_columns(profiles)
    if smooth_sigma:
        table = smooth_profiles(table, sigma=smooth_sigma)
    x = table.columns.to_numpy(dtype=float)
    values = [shoreline_position(x, row, water_level, crossing) for row in table.to_numpy()]
    return pd.Series(values, index=table.index, name="shoreline")


def foreshore_slope(profiles: pd.DataFrame, upper_level: float, lower_level: float,
                    crossing: str = "seaward", smooth_sigma: float | None = None) -> pd.Series:
    """Mean foreshore slope between two water levels (e.g. MHWS and low water).

    ``slope = (upper_level - lower_level) / (x_lower - x_upper)``, positive
    when the beach falls seaward. Both contours use the same ``crossing`` rule.
    At Hasaki: ``upper_level=1.25`` (MHWS), ``lower_level=-0.2`` (low water).
    """
    if upper_level <= lower_level:
        raise ValueError("upper_level must be above lower_level")
    upper = shoreline_positions(profiles, upper_level, crossing, smooth_sigma)
    lower = shoreline_positions(profiles, lower_level, crossing, smooth_sigma)
    width = lower - upper
    return ((upper_level - lower_level) / width.where(width > 0)).rename("foreshore_slope")


def flag_shoreline_outliers(shoreline: pd.Series, window: int = 5,
                            z_threshold: float = 1.73) -> pd.DataFrame:
    """Flag surveys whose shoreline jumps away from their neighbours.

    A centred rolling mean and standard deviation over ``window`` surveys give
    a local z-score; ``|z| > z_threshold`` is flagged. Inspect flagged surveys
    (e.g. with :func:`pycoastkit.plot.plot_profiles`) before removing them -
    real storm erosion can also be abrupt.

    Returns ``shoreline, rolling_mean, rolling_std, z_score, is_outlier``.
    """
    rolling = shoreline.rolling(window=window, center=True)
    mean, std = rolling.mean(), rolling.std()
    z = (shoreline - mean) / std
    return pd.DataFrame({
        "shoreline": shoreline,
        "rolling_mean": mean,
        "rolling_std": std,
        "z_score": z,
        "is_outlier": z.abs() > z_threshold,
    })
