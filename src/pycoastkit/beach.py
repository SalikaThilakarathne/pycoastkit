"""Beach profiles: smoothing, shoreline-relative coordinates, volumes and slopes.

A *profile table* is a DataFrame with one row per survey (DatetimeIndex) and
one column per cross-shore position. Column labels are positions in metres,
increasing seaward; labels such as ``"-40m"`` are accepted. Values are bed
elevations in metres.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.integrate import simpson
from scipy.ndimage import gaussian_filter1d

__all__ = [
    "cross_shore_positions",
    "smooth_profiles",
    "shoreline_relative_profiles",
    "beach_volume",
    "cut_and_fill",
    "profile_slope",
]


def cross_shore_positions(columns) -> np.ndarray:
    """Convert column labels such as ``"-40m"``, ``"5 m"`` or ``60`` to floats [m]."""
    return np.array([float(str(c).strip().lower().removesuffix("m").strip()) for c in columns])


def _with_numeric_columns(profiles: pd.DataFrame) -> pd.DataFrame:
    x = cross_shore_positions(profiles.columns)
    out = profiles.copy()
    out.columns = x
    out = out.sort_index(axis=1)
    if not isinstance(out.index, pd.DatetimeIndex):
        out.index = pd.to_datetime(out.index)
    return out.astype(float)


def _zone(table: pd.DataFrame, x_min, x_max) -> pd.DataFrame:
    x = table.columns.to_numpy(dtype=float)
    keep = np.ones_like(x, dtype=bool)
    if x_min is not None:
        keep &= x >= x_min
    if x_max is not None:
        keep &= x <= x_max
    zone = table.loc[:, keep]
    if zone.shape[1] < 2:
        raise ValueError("need at least two cross-shore positions inside [x_min, x_max]")
    return zone


def smooth_profiles(profiles: pd.DataFrame, sigma: float = 2.0) -> pd.DataFrame:
    """Gaussian smoothing of each profile along the cross-shore axis.

    ``sigma`` is in grid points (sigma=2 on a 5 m grid = 10 m). Missing values
    are handled by normalised convolution, so a gap does not spread NaN to its
    neighbours; positions that were missing stay missing.
    """
    table = _with_numeric_columns(profiles)
    values = table.to_numpy()
    mask = np.isfinite(values)
    numerator = gaussian_filter1d(np.where(mask, values, 0.0), sigma=sigma, axis=1, mode="reflect")
    denominator = gaussian_filter1d(mask.astype(float), sigma=sigma, axis=1, mode="reflect")
    with np.errstate(invalid="ignore", divide="ignore"):
        smoothed = numerator / denominator
    smoothed[~mask] = np.nan
    return pd.DataFrame(smoothed, index=table.index, columns=table.columns)


def shoreline_relative_profiles(profiles: pd.DataFrame, shoreline: pd.Series,
                                x_relative=None) -> pd.DataFrame:
    """Re-express each profile in coordinates relative to its own shoreline.

    ``x' = x - shoreline``, so ``x' = 0`` is the shoreline of that survey and
    positive ``x'`` is seaward. Elevations are linearly interpolated onto
    ``x_relative`` (default: -80 m to 340 m every 5 m); positions outside the
    surveyed range are NaN. Use this to compare features such as sandbars or
    zone volumes at a fixed distance from the shoreline.
    """
    table = _with_numeric_columns(profiles)
    x = table.columns.to_numpy(dtype=float)
    grid = np.arange(-80.0, 345.0, 5.0) if x_relative is None else np.asarray(x_relative, float)
    shore = shoreline.reindex(table.index)
    rows = []
    for z, s in zip(table.to_numpy(), shore.to_numpy(dtype=float)):
        valid = np.isfinite(z)
        if not np.isfinite(s) or valid.sum() < 2:
            rows.append(np.full(grid.size, np.nan))
            continue
        rows.append(np.interp(grid + s, x[valid], z[valid], left=np.nan, right=np.nan))
    return pd.DataFrame(rows, index=table.index, columns=grid)


def beach_volume(profiles: pd.DataFrame, x_min: float | None = None,
                 x_max: float | None = None, base="min") -> pd.Series:
    """Sand volume per metre of beach [m³/m] between ``x_min`` and ``x_max``.

    Volume = integral of ``elevation - base`` over x (Simpson's rule). Works on
    absolute or shoreline-relative profiles (e.g. inner zone
    ``x_min=20, x_max=170`` and outer zone ``170-340`` m from the shoreline).
    Surveys with a missing value inside the zone get NaN.

    Parameters
    ----------
    profiles : pandas.DataFrame
        Profile table (rows = surveys, columns = cross-shore positions).
    x_min, x_max : float, optional
        Zone limits [m]; the whole profile when omitted.
    base : "min", float or array-like
        Reference surface. ``"min"`` (default) uses, at each position, the
        lowest elevation in the whole record, so the result is the sand stored
        above the most eroded state observed. A number is a fixed level [m].

    Returns
    -------
    pandas.Series
        Volume per survey [m³/m], named ``volume``.
    """
    zone = _zone(_with_numeric_columns(profiles), x_min, x_max)
    reference = zone.min(axis=0).to_numpy() if isinstance(base, str) and base == "min" else base
    heights = zone.to_numpy() - np.asarray(reference, dtype=float)
    volume = simpson(heights, x=zone.columns.to_numpy(dtype=float), axis=1)
    volume[~np.isfinite(heights).all(axis=1)] = np.nan
    return pd.Series(volume, index=zone.index, name="volume")


def cut_and_fill(before, after, x_min: float | None = None, x_max: float | None = None) -> dict:
    """Erosion (cut) and deposition (fill) between two surveys of one profile.

    ``before`` and ``after`` are Series (index = cross-shore position) or rows
    of a profile table. Elevation changes are integrated separately where the
    bed went down (cut) and up (fill), using the trapezoidal rule.

    Returns ``{"cut": m³/m eroded (>= 0), "fill": m³/m deposited (>= 0),
    "net_loss": cut - fill}``.
    """
    pair = _with_numeric_columns(pd.DataFrame([pd.Series(before), pd.Series(after)],
                                              index=pd.to_datetime([0, 1])))
    zone = _zone(pair, x_min, x_max).dropna(axis=1)
    x = zone.columns.to_numpy(dtype=float)
    change = zone.iloc[1].to_numpy() - zone.iloc[0].to_numpy()
    trap = getattr(np, "trapezoid", None) or np.trapz
    cut = float(trap(np.clip(-change, 0, None), x))
    fill = float(trap(np.clip(change, 0, None), x))
    return {"cut": cut, "fill": fill, "net_loss": cut - fill}


def profile_slope(profiles: pd.DataFrame, x1: float, x2: float) -> pd.Series:
    """Mean bed slope between positions ``x1`` and ``x2`` (landward to seaward).

    ``slope = (z(x1) - z(x2)) / (x2 - x1)``, positive when the bed falls
    seaward. Elevations are linearly interpolated, so ``x1``/``x2`` need not be
    grid points. On shoreline-relative profiles, ``x1=0, x2=150`` gives the
    nearshore slope seaward of the shoreline.
    """
    if x2 <= x1:
        raise ValueError("x2 must be seaward of x1")
    table = _with_numeric_columns(profiles)
    x = table.columns.to_numpy(dtype=float)

    def at(row, position):
        valid = np.isfinite(row)
        if valid.sum() < 2:
            return np.nan
        return np.interp(position, x[valid], row[valid], left=np.nan, right=np.nan)

    values = [(at(row, x1) - at(row, x2)) / (x2 - x1) for row in table.to_numpy()]
    return pd.Series(values, index=table.index, name="slope")
